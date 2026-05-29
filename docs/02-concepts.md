# 核心概念

## 客户端生命周期

`CodroidSession`（别名 `CodroidControlInterface`）和 `CodroidClient` 的典型生命周期：

```python
from codroid import CodroidClient

# 方式一：with 语句（推荐）
with CodroidClient(host="192.168.1.136") as robot:
    robot.EnterRemoteModeViaAuto()
    robot.SwitchOn()
    # ... 使用 API ...
# 自动调用 Disconnect()

# 方式二：手动管理
robot = CodroidClient(host="192.168.1.136")
robot.Connect()
try:
    robot.EnterRemoteModeViaAuto()
    robot.SwitchOn()
    # ... 使用 API ...
finally:
    robot.Disconnect()
```

### CodroidSession vs CodroidClient

| 特性 | CodroidSession | CodroidClient |
|------|---------------|---------------|
| 传输层 | `JsonStreamClient`（同步阻塞） | `TransportClient`（后台线程） |
| 请求/响应匹配 | 同步发送-接收 | 异步 ID 匹配 |
| Publish/Subscribe | 不支持 | 支持 |
| 适用场景 | 简单脚本、一次性操作 | 持续收包、事件驱动 |

---

## TCP 命令模型

SDK 通过 TCP JSON 与控制器通信。每条指令的流程：

1. SDK 分配自增 `id`
2. 发送请求：`{"id": N, "ty": "command/path", "db": {...}}`
3. 控制器响应：`{"id": N, "ty": "...", "db": {...}, "err": ...}`
4. SDK 按 `id` 匹配请求与响应

```python
# SDK 内部自动处理 id 分配和匹配
response = robot._send_command("Robot/switchOn", "")
# response = CommonResponse(id=1, ty="Robot/switchOn", db=None, err=None)
```

### CommonResponse

所有 TCP 指令返回 `CommonResponse`：

```python
@dataclass
class CommonResponse:
    id: Union[int, str]   # 请求 ID
    ty: str               # 响应类型
    db: Optional[Any]     # 响应数据
    err: Optional[Any]    # 错误信息（None 表示成功）

    @property
    def is_success(self) -> bool:
        return self.err is None
```

---

## 单位约定

| 层级 | 线性 | 角度 |
|------|------|------|
| SDK 公共 API | **mm** | **deg（度）** |
| TCP JSON 协议 | **mm** | **deg** |
| CRI UDP 二进制（线路层） | **m** | **rad（弧度）** |
| `CriRealTimeData`（已解析） | **mm** | **deg** |

`CriRealtimePacketParser.parse()` 自动将线路层的 m/rad 转换为 mm/deg。

---

## API 命名约定

所有公共方法使用 **PascalCase**，与 C# / C++ SDK 保持一致：

```python
robot.Connect()
robot.SwitchOn()
robot.GetDi(0)
robot.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=40, acceleration=100)
robot.SetToolFrame(1, RobotFrame(id=1, x=100, y=0, z=0, a=0, b=0, c=0))
```

> **Breaking（2.1.1）**：`move_j`、`switch_on` 等 snake_case 别名已移除。

---

## 异常处理

SDK 定义了四种异常类型：

| 异常 | 触发条件 |
|------|----------|
| `CodroidError` | 基础异常类；参数校验失败、非法操作 |
| `CodroidCommandException` | 控制器返回 `err` 字段（协议层错误） |
| `CodroidNetworkError` | TCP 连接失败、通信中断 |
| `CodroidTimeoutError` | 操作超时（连接、CRI 等待、阻塞运动） |

```python
from codroid import (
    CodroidError,
    CodroidCommandException,
    CodroidNetworkError,
    CodroidTimeoutError,
)

try:
    with CodroidClient(host="192.168.1.136") as robot:
        robot.ConnectRemoteAndSwitchOn()
except CodroidNetworkError:
    print("无法连接控制器")
except CodroidTimeoutError:
    print("连接超时")
except CodroidCommandException as e:
    print(f"控制器错误: {e}")
except CodroidError as e:
    print(f"SDK 错误: {e}")
```

---

## 线程安全

- `CriData` 属性返回当前缓存的 CRI 快照，可从任意线程读取。
- TCP 方法（`GetDi`、`MovJ` 等）可从任意线程调用，但同一客户端实例不支持并发调用。
- `CriRealtimeDispatcher` 的 `SendCommand` / `SendTrajectory` 是线程安全的（UDP 无状态）。

---

## Publish / Subscribe

`CodroidClient` 支持订阅控制器推送的事件主题：

```python
from codroid import CodroidClient, PublishTopics

def on_robot_status(notification):
    print(f"收到 {notification.ty}: {notification.db}")

with CodroidClient(host="192.168.1.136") as robot:
    sub = robot.SubscribePublishTopic(PublishTopics.ROBOT_STATUS, on_robot_status)
    # ... 运行 ...
    sub.dispose()  # 取消订阅
```

可用主题见 `PublishTopics` 常量：
- `PROJECT_STATE` — 工程状态变更
- `VAR_UPDATE` — 变量更新
- `ROBOT_STATUS` — 机器人状态
- `ROBOT_POSTURE` — 机器人姿态
- `ROBOT_COORDINATE` — 机器人坐标
- `LOG` — 日志
- `ERROR` — 错误
