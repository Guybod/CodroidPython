import socket
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class JsonStreamClient:
    """处理以 {} 为边界的 TCP JSON 流"""
    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._buffer = "" # 接收缓冲区

    def connect(self):
        if self._sock is None:
            try:
                self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
                logger.info(f"Connected to {self.host}:{self.port}")
            except Exception as e:
                from .exceptions import CodroidNetworkError
                raise CodroidNetworkError(f"连接失败: {e}")

    def send(self, data: Dict[str, Any]):
        """序列化并发送数据"""
        if self._sock is None:
            self.connect()
        
        # 此时显式检查以消除类型警告
        if self._sock:
            msg = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self._sock.sendall(msg)

    def receive_one(self) -> Dict[str, Any]:
        """通过大括号计数法切分出第一个完整的 JSON 对象"""
        if self._sock is None:
            self.connect()

        while True:
            # 1. 检查缓冲区是否已经包含一个完整的 JSON
            if self._buffer:
                full_json, remaining = self._extract_json(self._buffer)
                if full_json:
                    self._buffer = remaining
                    return json.loads(full_json)

            # 2. 如果缓冲区没有完整包，从网络读取更多数据
            if self._sock:
                chunk = self._sock.recv(4096).decode('utf-8')
                if not chunk:
                    self.close()
                    from .exceptions import CodroidNetworkError
                    raise CodroidNetworkError("服务端关闭了连接")
                self._buffer += chunk

    def _extract_json(self, text: str):
        """核心逻辑：大括号匹配算法"""
        start = text.find('{')
        if start == -1: return None, ""
        
        count = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                count += 1
            elif text[i] == '}':
                count -= 1
                
            if count == 0: # 找到匹配的闭合大括号
                return text[start:i+1], text[i+1:]
        return None, text

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None
            self._buffer = ""