# CodroidSession / CodroidClient API 参考

`CodroidSession`（别名 `CodroidControlInterface`）是主会话类，封装了全部 TCP 指令。`CodroidClient` 继承它并替换传输层，增加 publish/subscribe 能力。

---

## 构造函数

### CodroidSession

```python
CodroidSession(
    host: str = "192.168.1.136",
    port: int = 9001,
    local_ip: str = "192.168.1.150",
    udp_port: int = 10086,
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | `str` | `"192.168.1.136"` | 控制器 IP 地址 |
| `port` | `int` | `9001` | TCP 端口 |
| `local_ip` | `str` | `"192.168.1.150"` | 本机 IP（CRI UDP 推送用） |
| `udp_port` | `int` | `10086` | 本机 UDP 监听端口 |

### CodroidClient

```python
CodroidClient(
    host: str = "192.168.1.136",
    port: int = 9001,
    local_ip: str = "192.168.1.150",
    udp_port: int = 10086,
    timeout: float = 10.0,
)
```

额外参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `timeout` | `float` | `10.0` | TCP 请求超时（秒） |

---

## 属性

### CriData

```python
@property
def CriData(self) -> Optional[CriRealTimeData]
```

最新的 CRI 实时数据快照。需要先调用 `StartListenUdp()` 或 `StartCriDataPush()` 开始接收 UDP 数据。

```python
robot.StartListenUdp()
robot.WaitForCriData()
data = robot.CriData
print(f"关节角: {data.joint_position}")
print(f"TCP 位姿: {data.tcp_pose}")
print(f"是否运动中: {data.status.is_moving}")
```

---

## 连接管理

### Connect

```python
def Connect(self) -> CodroidSession
```

建立 TCP 连接。返回自身以支持链式调用。使用 `with` 语句时自动调用。

### Disconnect

```python
def Disconnect(self) -> None
```

断开 TCP 连接并停止 CRI 接收。使用 `with` 语句时自动调用。

---

## 便捷连接

### ConnectRemoteAndSwitchOn

```python
def ConnectRemoteAndSwitchOn(self) -> CommonResponse
```

组合操作：`EnterRemoteModeViaAuto()` → `SwitchOn()`。须先 `Connect()` 或在 `with` 块内。

```python
with CodroidClient(host="192.168.1.136") as robot:
    robot.ConnectRemoteAndSwitchOn()
```

### EnterRemoteModeViaAuto

```python
def EnterRemoteModeViaAuto(self) -> CommonResponse
```

先 `ToAuto()` 再 `ToRemote()`。

### EnterManualModeViaAuto

```python
def EnterManualModeViaAuto(self) -> CommonResponse
```

先 `ToAuto()` 再 `ToManual()`。

---

## 模式切换

### SwitchOn / SwitchOff

```python
def SwitchOn(self) -> CommonResponse
def SwitchOff(self) -> CommonResponse
```

上使能 / 下使能。

### ToRemote / ToManual / ToAuto

```python
def ToRemote(self) -> CommonResponse
def ToManual(self) -> CommonResponse
def ToAuto(self) -> CommonResponse
```

切换到远程 / 手动 / 自动模式。

### ToSimulation / ToActual

```python
def ToSimulation(self) -> CommonResponse
def ToActual(self) -> CommonResponse
```

切换到仿真 / 实机模式。

### StartDrag / StopDrag

```python
def StartDrag(self) -> CommonResponse
def StopDrag(self) -> CommonResponse
```

进入 / 退出拖拽示教模式。仅在远程模式和手动模式下可用。

### ClearSystemError

```python
def ClearSystemError(self) -> CommonResponse
```

清除系统错误。

---

## 非阻塞运动指令

### MovJ

```python
def MovJ(
    self,
    target: Union[JointPoint, CartesianPoint, MovePoint],
    speed: float,
    acceleration: float,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> CommonResponse
```

关节插补运动。目标可为 `JointPoint`（发 jp）或 `CartesianPoint`（发 cp+rj）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `target` | `JointPoint` / `CartesianPoint` | 运动目标 |
| `speed` | `float` | 速度 |
| `acceleration` | `float` | 加速度 |
| `blend` | `float` | 平滑半径，默认 0（精确到达） |
| `coor` | `Sequence[float]` | 用户坐标系 `[x,y,z,a,b,c]` |
| `tool` | `Sequence[float]` | 工具坐标系 `[x,y,z,a,b,c]` |

```python
robot.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=40, acceleration=100)
robot.MovJ(CartesianPoint.MmDeg([400, 200, 500, 180, 0, 90]), speed=40, acceleration=100)
```

### MovL

```python
def MovL(
    self,
    target: Union[CartesianPoint, JointPoint, MovePoint],
    speed: float,
    acceleration: float,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> CommonResponse
```

直线插补运动。目标可为 `CartesianPoint` 或 `JointPoint`。

### MovC

```python
def MovC(
    self,
    middle: CartesianPoint,
    target: CartesianPoint,
    speed: float,
    acceleration: float,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> CommonResponse
```

圆弧运动。中间点与目标均为 `CartesianPoint`。

### MovCircle

```python
def MovCircle(
    self,
    middle: CartesianPoint,
    target: CartesianPoint,
    circle_num: int,
    speed: float,
    acceleration: float,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> CommonResponse
```

整圆运动。`circle_num` 为圈数。

### Move

```python
def Move(
    self,
    path: Union[MotionPath, List[MoveInstruction], List[Dict[str, Any]]],
) -> CommonResponse
```

多段路径执行。推荐使用 `List[MoveInstruction]`。

```python
path = [
    MoveInstruction.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=40, acc=100),
    MoveInstruction.MovL(CartesianPoint.MmDeg([400, 200, 500, 180, 0, 90]), speed=150, acc=500),
    MoveInstruction.MovL(JointPoint.Degrees([0, 0, 0, 0, 0, 0]), speed=150, acc=500),
]
robot.Move(path)
```

---

## 阻塞式运动指令

`*Sync` 方法发送运动指令后自动轮询 CRI 数据，直到机器人稳定到达目标。需要先启动 CRI 数据推送。

### MovJSync

```python
def MovJSync(
    self,
    target: Union[JointPoint, CartesianPoint],
    speed: float,
    acceleration: float,
    wait: Optional[MotionWaitOptions] = None,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> bool
```

阻塞式关节运动。到达目标返回 `True`。

```python
robot.StartListenUdp()
robot.WaitForCriData()
robot.MovJSync(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=40, acceleration=100)
```

### MovLSync

```python
def MovLSync(
    self,
    target: Union[CartesianPoint, JointPoint],
    speed: float,
    acceleration: float,
    wait: Optional[MotionWaitOptions] = None,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> bool
```

阻塞式直线运动。

### MovCSync

```python
def MovCSync(
    self,
    middle: CartesianPoint,
    target: CartesianPoint,
    speed: float,
    acceleration: float,
    wait: Optional[MotionWaitOptions] = None,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> bool
```

阻塞式圆弧运动。

### MovCircleSync

```python
def MovCircleSync(
    self,
    middle: CartesianPoint,
    target: CartesianPoint,
    circle_num: int,
    speed: float,
    acceleration: float,
    wait: Optional[MotionWaitOptions] = None,
    blend: float = 0.0,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> bool
```

阻塞式整圆运动。

### MoveSync

```python
def MoveSync(
    self,
    path: Union[MotionPath, List[MoveInstruction], List[Dict[str, Any]]],
    wait: Optional[MotionWaitOptions] = None,
) -> bool
```

阻塞式路径执行。等待 CRI 确认最后一段到达目标。

### MotionWaitOptions

控制阻塞运动的等待行为：

```python
@dataclass
class MotionWaitOptions:
    timeout: float = 60.0                           # 整体超时（秒）
    poll_interval: float = 0.05                     # 轮询间隔（秒）
    cri_stale_timeout: float = 0.5                  # CRI 数据过期判定（秒）
    settled_samples: int = 3                        # 连续稳定采样数
    joint_tolerance_deg: float = 0.2                # 关节容差（度）
    cartesian_position_tolerance_mm: float = 1.0    # 笛卡尔位置容差（mm）
    cartesian_orientation_tolerance_deg: float = 1.0 # 笛卡尔姿态容差（度）
```

```python
from codroid import MotionWaitOptions

opts = MotionWaitOptions(timeout=30.0, joint_tolerance_deg=0.5)
robot.MovJSync(JointPoint.Degrees([0, 0, 90, 0, 90, 0]),
               speed=40, acceleration=100, wait=opts)
```

---

## 运动控制

### PauseRobotMotion / ResumeRobotMotion

```python
def PauseRobotMotion(self) -> CommonResponse
def ResumeRobotMotion(self) -> CommonResponse
```

暂停 / 恢复当前运动。

### StopRobotMove

```python
def StopRobotMove(self) -> CommonResponse
```

停止当前运动。

---

## MoveTo 指令

### MoveTo

```python
def MoveTo(
    self,
    move_type: MoveToType,
    target: Optional[MoveToTarget] = None,
) -> CommonResponse
```

运动到预设位置。`MoveToType` 枚举值：

| 值 | 说明 |
|----|------|
| `STOP` (-1) | 停止 MoveTo |
| `HOME` (0) | Home 点 |
| `SAFE` (1) | 安全位 |
| `CANDLE` (2) | 蜡烛位 |
| `PACK` (3) | 打包位 |
| `JOINT` (4) | 关节规划到指定目标 |
| `LINEAR` (5) | 直线规划到指定目标 |
| `RESUME` (6) | 程序恢复点 |

```python
from codroid import MoveToType

robot.MoveTo(MoveToType.HOME)  # 回 Home
robot.MoveTo(MoveToType.SAFE)  # 回安全位
```

启动后须每 0.5s 调用 `MoveToHeartbeat()`。

### MoveToHeartbeat

```python
def MoveToHeartbeat(self) -> CommonResponse
```

MoveTo 心跳。须在 MoveTo 运动期间每隔 0.5s 调用一次。

### StopMoveTo

```python
def StopMoveTo(self) -> CommonResponse
```

停止当前 MoveTo 运动。

---

## Jog 指令

### StartJog

```python
def StartJog(
    self,
    mode: JogMode,
    index: int,
    speed: float,
    coor_type: JogCoorType = JogCoorType.USER,
    coor_id: int = 1,
) -> CommonResponse
```

启动点动。

| 参数 | 类型 | 说明 |
|------|------|------|
| `mode` | `JogMode` | `JOINT`(1) 关节点动 / `LINEAR`(2) 直线点动 |
| `index` | `int` | 关节序号(1-6) 或直线轴序号(1-6 对应 xyzabc) |
| `speed` | `float` | 速度 (-1.0 ~ 1.0) |
| `coor_type` | `JogCoorType` | `USER`(0) / `TOOL`(1) |
| `coor_id` | `int` | 用户坐标系 ID |

```python
from codroid import JogMode

robot.StartJog(JogMode.JOINT, index=1, speed=0.5)  # 关节 1 正向点动
```

### StopJog

```python
def StopJog(self) -> CommonResponse
```

停止点动。

### JogHeartbeat

```python
def JogHeartbeat(self) -> CommonResponse
```

点动心跳。须在点动期间每隔 0.5s 调用一次。

---

## 速度倍率

### SetManualMoveRate / SetAutoMoveRate

```python
def SetManualMoveRate(self, rate: int) -> CommonResponse
def SetAutoMoveRate(self, rate: int) -> CommonResponse
```

设置手动 / 自动运动倍率。`rate` 范围 1~100。

---

## CRI 数据推送

### StartListenUdp

```python
def StartListenUdp(self) -> None
```

一键启动 CRI 数据接收：先停止旧推送 → 启动本地 UDP 监听 → 通知控制器开始推送。

```python
robot.StartListenUdp()
robot.WaitForCriData()
data = robot.CriData
```

### WaitForCriData

```python
def WaitForCriData(self, timeout: float = 5.0) -> CriRealTimeData
```

等待第一个 CRI 数据包到达。超时抛出 `CodroidTimeoutError`。

### StartCriDataPush

```python
def StartCriDataPush(
    self,
    ip: str,
    port: int,
    duration: int = 100,
    high_percision: bool = True,
    mask: int = 0xFFFF,
) -> CommonResponse
```

手动开启 CRI UDP 推送。`port` 范围 10000–65534。`duration` 为推送周期（ms）。

### StopCriDataPush

```python
def StopCriDataPush(self, ip: Optional[str] = None, port: Optional[int] = None) -> CommonResponse
```

停止 CRI 推送。

### StartCriControl

```python
def StartCriControl(
    self,
    filter_type: CriFilterType = CriFilterType.NONE,
    duration: int = 1,
    start_buffer: int = 3,
) -> CommonResponse
```

开启 CRI 实时控制模式。`duration` 为指令间隔（ms，1–16，且可整除 1000）。

### StopCriControl

```python
def StopCriControl(self) -> CommonResponse
```

关闭 CRI 实时控制。

---

## IO 操作

### GetDi / GetDo / GetAi / GetAo

```python
def GetDi(self, port: int) -> int       # 数字输入，端口 0~15，返回 0 或 1
def GetDo(self, port: int) -> int       # 数字输出，端口 0~15，返回 0 或 1
def GetAi(self, port: int) -> float     # 模拟输入，端口 0~3
def GetAo(self, port: int) -> float     # 模拟输出，端口 0~3
```

```python
di0 = robot.GetDi(0)
do5 = robot.GetDo(5)
ai0 = robot.GetAi(0)
```

### SetDo / SetAo

```python
def SetDo(self, port: int, value: int) -> CommonResponse     # value: 0 或 1
def SetAo(self, port: int, value: float) -> CommonResponse
```

```python
robot.SetDo(10, 1)
robot.SetAo(0, 3.14)
```

### GetIoValues

```python
def GetIoValues(self, io_requests: List[Dict[str, Any]]) -> CommonResponse
```

批量读取 IO。`io_requests` 格式：`[{"type": "DI", "port": 0}, ...]`。

---

## 寄存器操作

### GetRegisterValue / GetRegisterValues

```python
def GetRegisterValue(self, address: int) -> Any
def GetRegisterValues(self, addresses: List[int]) -> CommonResponse
```

```python
val = robot.GetRegisterValue(0)
vals = robot.GetRegisterValues([0, 1, 2])
```

### SetRegisterValue

```python
def SetRegisterValue(self, address: int, value: Any) -> CommonResponse
```

```python
robot.SetRegisterValue(0, 42)
```

### SetExtendArrayType / RemoveExtendArray

```python
def SetExtendArrayType(self, index: int, data_type: ExtendArrayType) -> CommonResponse
def RemoveExtendArray(self, index: int) -> CommonResponse
```

设置 / 删除扩展数组数据类型。`index` 范围 0~999。

---

## 机器人设置

### GetRobotParameters

```python
def GetRobotParameters(self) -> RobotParameters
```

获取设置界面参数快照。返回 `RobotParameters`，包含工具坐标系表、负载坐标系表、用户坐标系表及默认 ID。

```python
params = robot.GetRobotParameters()
print(f"默认工具: {params.default_tool_id}")
print(f"默认负载: {params.default_payload_id}")
for frame in params.tool:
    print(f"  Tool[{frame.id}]: x={frame.x}, y={frame.y}, z={frame.z}")
```

### SetToolFrame / SaveToolFrames

```python
def SetToolFrame(self, frame_id: int, frame) -> CommonResponse
def SaveToolFrames(self, frames) -> CommonResponse
```

`SetToolFrame` 修改单个工具坐标系（先读后改再保存，`frame_id` 仅允许 1~15）。`SaveToolFrames` 下发完整表（16 项，id=0 须全零）。

```python
from codroid import RobotFrame

robot.SetToolFrame(1, RobotFrame(id=1, x=100, y=0, z=50, a=0, b=0, c=0))
```

### SetPayloadFrame / SavePayloadFrames

```python
def SetPayloadFrame(self, frame_id: int, frame) -> CommonResponse
def SavePayloadFrames(self, frames) -> CommonResponse
```

`SetPayloadFrame` 修改单个负载坐标系（`frame_id` 仅允许 1~15）。`SavePayloadFrames` 下发完整表。

```python
from codroid import RobotPayloadFrame

robot.SetPayloadFrame(1, RobotPayloadFrame(id=1, m=2.5, mx=0, my=0, mz=50))
```

### SetUserCoordinateFrame / SaveUserCoordinateFrames

```python
def SetUserCoordinateFrame(self, frame_id: int, frame) -> CommonResponse
def SaveUserCoordinateFrames(self, frames) -> CommonResponse
```

修改单个 / 下发完整用户坐标系表。

### SetDefaultToolId / SetDefaultPayloadId / SetDefaultUserCoordinateId

```python
def SetDefaultToolId(self, tool_id: int) -> CommonResponse
def SetDefaultPayloadId(self, payload_id: int) -> CommonResponse
def SetDefaultUserCoordinateId(self, coordinate_id: int) -> CommonResponse
```

设置默认工具 / 负载 / 用户坐标系编号。范围 0~15。

### SetCollisionSensitivity

```python
def SetCollisionSensitivity(self, sensitivity: int) -> CommonResponse
```

设置碰撞检测灵敏度。范围 0~100。仅固件 2.3.2.10+ 可用。

### SetPayload

```python
def SetPayload(self, payload_id: int) -> CommonResponse
```

设置当前负载编号。仅固件 2.3.2.10+ 可用。

---

## 项目与脚本

### RunScript

```python
def RunScript(
    self,
    main_script: str,
    sub_threads: Optional[Dict[str, str]] = None,
    sub_programs: Optional[Dict[str, str]] = None,
    interrupts: Optional[Dict[str, str]] = None,
    vars: Optional[Dict[str, Any]] = None,
) -> CommonResponse
```

运行 Lua 脚本。

```python
robot.RunScript('print("hello")', vars={"speed": 100})
```

### Run / RunByIndex / RunStep

```python
def Run(self, project_id: str) -> CommonResponse
def RunByIndex(self, index: int) -> CommonResponse
def RunStep(self, project_id: str) -> CommonResponse
```

运行 / 单步运行工程。

### PauseProject / ResumeProject / StopProject

```python
def PauseProject(self) -> CommonResponse
def ResumeProject(self) -> CommonResponse
def StopProject(self) -> CommonResponse
```

暂停 / 恢复 / 停止工程。

### EnterRemoteScriptMode

```python
def EnterRemoteScriptMode(self) -> CommonResponse
```

进入远程脚本模式。

### SetStartLine / ClearStartLine

```python
def SetStartLine(self, line: int) -> CommonResponse
def ClearStartLine(self) -> CommonResponse
```

设置 / 清除启动行。

---

## RS485 通信

### Rs485Init

```python
def Rs485Init(
    self,
    baudrate: Union[RS485BaudRate, int],
    stop_bit: RS485StopBits = RS485StopBits.ONE,
    parity: RS485Parity = RS485Parity.NONE,
) -> CommonResponse
```

初始化末端 RS485。

```python
from codroid import RS485BaudRate

robot.Rs485Init(RS485BaudRate.B115200)
```

### Rs485Flush

```python
def Rs485Flush(self) -> CommonResponse
```

清空 RS485 读取缓存。

### Rs485Read

```python
def Rs485Read(self, length: int, timeout: int = 3000) -> CommonResponse
```

读取 RS485 数据。`length` 最大 128 字节，`timeout` 最大 3000ms。

### Rs485Write

```python
def Rs485Write(self, data: Union[List[int], bytes]) -> CommonResponse
```

发送 RS485 数据。最大 127 字节。

---

## 运动学

### AposToCpos

```python
def AposToCpos(
    self,
    jp: Sequence[float],
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
    ep: Sequence[float] = [],
) -> CommonResponse
```

正解（关节 → 笛卡尔）。`jp` 为 6 个关节角（度）。

### CposToApos

```python
def CposToApos(
    self,
    cp: Sequence[float],
    rj: Optional[Sequence[float]] = None,
    ep: Sequence[float] = [],
) -> CommonResponse
```

逆解（笛卡尔 → 关节）。`cp` 为 `[x,y,z,a,b,c]`，`rj` 为参考关节角（默认 `[20,20,20,20,20,20]`）。

### CalculateRelativePose

```python
def CalculateRelativePose(
    self,
    pos: Sequence[float],
    offset: Sequence[float],
    coor_type: CoordinateType = CoordinateType.TOOL,
    pos_coor: Optional[Sequence[float]] = None,
    coor: Optional[Sequence[float]] = None,
) -> CommonResponse
```

笛卡尔坐标偏移计算。

---

## Publish / Subscribe（仅 CodroidClient）

### SubscribePublishTopic

```python
def SubscribePublishTopic(
    self,
    topic_ty: str,
    handler: Callable[[PublishNotification], None],
    tc_milliseconds: int = 100,
) -> PublishTopicSubscription
```

订阅控制器推送主题。返回 `PublishTopicSubscription`，调用 `.dispose()` 取消订阅。

```python
from codroid import CodroidClient, PublishTopics

def on_status(notification):
    print(f"{notification.ty}: {notification.db}")

with CodroidClient(host="192.168.1.136") as robot:
    sub = robot.SubscribePublishTopic(PublishTopics.ROBOT_STATUS, on_status)
    # ... 运行 ...
    sub.dispose()
```

---

## 调试

```python
robot.debug = True  # 打印发送/接收的原始 JSON
```
