from dataclasses import dataclass
from typing import Any, Callable


class PublishTopics:
    PROJECT_STATE = "publish/ProjectState"
    VAR_UPDATE = "publish/VarUpdate"
    ROBOT_STATUS = "publish/RobotStatus"
    ROBOT_POSTURE = "publish/RobotPosture"
    ROBOT_COORDINATE = "publish/RobotCoordinate"
    LOG = "publish/Log"
    ERROR = "publish/Error"


@dataclass
class PublishNotification:
    ty: str
    db: Any
    raw_json: str = ""


class PublishTopicSubscription:
    """
    Local subscription handle.

    Dispose only removes local callback; it does not send unsubscribe to controller.
    """

    def __init__(self, dispose_callback: Callable[[], None]):
        self._dispose_callback = dispose_callback
        self._disposed = False

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self._dispose_callback()

    def Dispose(self) -> None:
        """C# ``Dispose`` 别名。"""
        self.dispose()

