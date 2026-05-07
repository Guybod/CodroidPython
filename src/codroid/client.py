import threading
from collections import defaultdict
from typing import Any, Callable, Dict

from .Codroid import CodroidSession
from .exceptions import CodroidError
from .define import CodroidRequest, CommonResponse
from .publish import PublishNotification, PublishTopicSubscription
from .async_tcp_client import TransportClient


class CodroidClient(CodroidSession):
    """
    2.0 facade entry (compatibility stage).

    Current behavior reuses ``CodroidSession`` (``CodroidControlInterface`` 别名) 实现。
    Domain-module delegation will be introduced incrementally.
    """

    def __init__(
        self,
        host: str = "192.168.1.136",
        port: int = 9001,
        local_ip: str = "192.168.1.150",
        udp_port: int = 10086,
        timeout: float = 10.0,
    ):
        # Keep the same attributes as CodroidSession for compatibility.
        super().__init__(host=host, port=port, local_ip=local_ip, udp_port=udp_port)
        self._net = TransportClient(host, port, timeout=timeout)
        self._publish_lock = threading.Lock()
        self._publish_local_counts: Dict[str, int] = defaultdict(int)

    def _send_command(self, ty: str, db: Any = None) -> CommonResponse:
        self._id_counter += 1
        request = CodroidRequest(id=self._id_counter, ty=ty, db=db)

        payload: Dict[str, Any] = {
            "id": request.id,
            "ty": request.ty,
        }
        if request.db is not None:
            payload["db"] = request.db

        if self.debug:
            print(payload)

        raw_res = self._net.send_request(payload, int(request.id), timeout=10.0)

        if self.debug:
            print(f"[recv]: {raw_res}")

        response = CommonResponse(
            id=raw_res.get("id", 0),
            ty=raw_res.get("ty", ""),
            db=raw_res.get("db"),
            err=raw_res.get("err"),
        )

        if not response.is_success:
            raise CodroidError(f"API Error [{response.ty}]: {response.err}")

        return response

    def SubscribePublishTopic(
        self,
        topic_ty: str,
        handler: Callable[[PublishNotification], None],
        tc_milliseconds: int = 100,
    ) -> PublishTopicSubscription:
        """
        Subscribe publish topic.

        On first local subscriber for this topic, sends {ty, tc} to controller.
        """

        def _wrapped_callback(ty: str, db: Any, raw_json: str):
            handler(PublishNotification(ty=ty, db=db, raw_json=raw_json))

        with self._publish_lock:
            first_subscriber = self._publish_local_counts[topic_ty] == 0
            self._publish_local_counts[topic_ty] += 1

        self._net.add_publish_handler(topic_ty, _wrapped_callback)

        if first_subscriber:
            self._net.send_publish_subscription(topic_ty, tc_ms=tc_milliseconds)

        def _dispose():
            self._net.remove_publish_handler(topic_ty, _wrapped_callback)
            with self._publish_lock:
                count = self._publish_local_counts.get(topic_ty, 0)
                if count <= 1:
                    self._publish_local_counts.pop(topic_ty, None)
                else:
                    self._publish_local_counts[topic_ty] = count - 1

        return PublishTopicSubscription(_dispose)

    def subscribe_publish_topic(
        self,
        topic_ty: str,
        handler: Callable[[PublishNotification], None],
        tc_milliseconds: int = 100,
    ) -> PublishTopicSubscription:
        # Temporary pythonic alias during migration.
        return self.SubscribePublishTopic(topic_ty, handler, tc_milliseconds=tc_milliseconds)

