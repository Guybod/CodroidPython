"""
TCP JSON 流与带 ``id`` 配对的异步风格传输（对齐 C# ``AsyncTcpClient.cs`` / ``FutureTcpClient``）。
"""
from __future__ import annotations

import json
import logging
import socket
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .exceptions import CodroidNetworkError, CodroidTimeoutError

logger = logging.getLogger(__name__)

PublishCallback = Callable[[str, Any, str], None]


class JsonStreamClient:
    """处理以 ``{}`` 为边界的 TCP JSON 流（同步读一条响应）。"""

    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._buffer = ""

    def connect(self):
        if self._sock is None:
            try:
                self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
                logger.info(f"Connected to {self.host}:{self.port}")
            except Exception as e:
                raise CodroidNetworkError(f"连接失败: {e}")

    def send(self, data: Dict[str, Any]):
        if self._sock is None:
            self.connect()
        if self._sock:
            msg = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self._sock.sendall(msg)

    def receive_one(self) -> Dict[str, Any]:
        if self._sock is None:
            self.connect()
        while True:
            if self._buffer:
                full_json, remaining = self._extract_json(self._buffer)
                if full_json:
                    self._buffer = remaining
                    return json.loads(full_json)
            if self._sock:
                chunk = self._sock.recv(4096).decode("utf-8")
                if not chunk:
                    self.close()
                    raise CodroidNetworkError("服务端关闭了连接")
                self._buffer += chunk

    def _extract_json(self, text: str):
        start = text.find("{")
        if start == -1:
            return None, ""
        count = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                count += 1
            elif text[i] == "}":
                count -= 1
            if count == 0:
                return text[start : i + 1], text[i + 1 :]
        return None, text

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None
            self._buffer = ""


@dataclass
class _PendingRequest:
    event: threading.Event = field(default_factory=threading.Event)
    response: Optional[Dict[str, Any]] = None
    error: Optional[BaseException] = None


class TransportClient(JsonStreamClient):
    """
    后台收包、按整数 ``id`` 配对响应；无 ``id`` 时按 ``ty`` 分发 publish（对齐 C# ``FutureTcpClient``）。
    """

    def __init__(self, host: str, port: int, timeout: float = 10.0):
        super().__init__(host, port, timeout=timeout)
        self._write_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._publish_lock = threading.Lock()
        self._pending: Dict[int, _PendingRequest] = {}
        self._publish_handlers: Dict[str, List[PublishCallback]] = {}
        self._recv_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self):
        super().connect()
        if self._sock:
            self._sock.settimeout(0.5)
        self._start_receiver()

    def close(self):
        self._stop_event.set()
        super().close()
        self._fail_all_pending(CodroidNetworkError("连接已关闭 / Transport closed"))

    def send_request(self, payload: Dict[str, Any], request_id: int, timeout: float = 10.0) -> Dict[str, Any]:
        pending = _PendingRequest()
        with self._pending_lock:
            self._pending[request_id] = pending
        try:
            with self._write_lock:
                self.send(payload)
        except BaseException:
            with self._pending_lock:
                self._pending.pop(request_id, None)
            raise
        if not pending.event.wait(timeout):
            with self._pending_lock:
                self._pending.pop(request_id, None)
            raise CodroidTimeoutError(
                f"请求超时 / Request timeout: id={request_id}, timeout={timeout}s"
            )
        if pending.error is not None:
            raise pending.error
        if pending.response is None:
            raise CodroidNetworkError(f"请求失败 / Request failed without response: id={request_id}")
        return pending.response

    def send_publish_subscription(self, topic_ty: str, tc_ms: int = 100):
        payload = {"ty": topic_ty, "tc": tc_ms}
        with self._write_lock:
            self.send(payload)

    def add_publish_handler(self, ty: str, callback: PublishCallback):
        with self._publish_lock:
            handlers = self._publish_handlers.setdefault(ty, [])
            handlers.append(callback)

    def remove_publish_handler(self, ty: str, callback: PublishCallback):
        with self._publish_lock:
            handlers = self._publish_handlers.get(ty, [])
            if callback in handlers:
                handlers.remove(callback)
            if not handlers and ty in self._publish_handlers:
                self._publish_handlers.pop(ty, None)

    def _start_receiver(self):
        if self._recv_thread and self._recv_thread.is_alive():
            return
        self._stop_event.clear()
        self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._recv_thread.start()

    def _receive_loop(self):
        try:
            while not self._stop_event.is_set():
                if not self._sock:
                    break
                try:
                    chunk = self._sock.recv(4096).decode("utf-8")
                except socket.timeout:
                    continue
                except OSError as e:
                    if self._stop_event.is_set():
                        return
                    self._fail_all_pending(CodroidNetworkError(f"网络接收失败 / Receive failed: {e}"))
                    return
                if not chunk:
                    self._fail_all_pending(CodroidNetworkError("服务端关闭连接 / Server closed connection"))
                    return
                self._buffer += chunk
                self._consume_buffer_messages()
        except BaseException as e:
            self._fail_all_pending(CodroidNetworkError(f"接收线程异常 / Receiver crashed: {e}"))

    def _consume_buffer_messages(self):
        while self._buffer:
            full_json, remaining = self._extract_json(self._buffer)
            if not full_json:
                return
            self._buffer = remaining
            try:
                message = json.loads(full_json)
            except json.JSONDecodeError:
                continue
            message_id = message.get("id")
            if isinstance(message_id, int):
                self._resolve_pending(message_id, message)
                continue
            message_ty = message.get("ty")
            if isinstance(message_ty, str):
                self._dispatch_publish(message_ty, message.get("db"), full_json)

    def _resolve_pending(self, request_id: int, response: Dict[str, Any]):
        with self._pending_lock:
            pending = self._pending.pop(request_id, None)
        if pending is None:
            return
        pending.response = response
        pending.event.set()

    def _dispatch_publish(self, ty: str, db: Any, raw_json: str):
        with self._publish_lock:
            handlers = list(self._publish_handlers.get(ty, []))
        for handler in handlers:
            try:
                handler(ty, db, raw_json)
            except Exception as e:
                logger.warning("publish handler error [%s]: %s", ty, e)
                continue

    def _fail_all_pending(self, exc: BaseException):
        with self._pending_lock:
            pendings = list(self._pending.values())
            self._pending.clear()
        for pending in pendings:
            pending.error = exc
            pending.event.set()


FutureTcpClient = TransportClient
