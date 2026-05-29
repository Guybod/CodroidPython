# CRI 实时数据与控制 API 参考

## CriRealtimePacketParser

```python
class CriRealtimePacketParser:
    @staticmethod
    def parse(data: bytes) -> Optional[CriRealTimeData]
```

解析 308 字节 CRI UDP 包为 `CriRealTimeData`（mm + 度）。非 308 字节的包返回 `None`。

自动完成线路层单位转换：
- 关节角：rad → deg
- TCP 位置：m → mm
- TCP 姿态：rad → deg
- 速度：m/s → mm/s, rad/s → deg/s

```python
from codroid import CriRealtimePacketParser

data = CriRealtimePacketParser.parse(raw_bytes)
if data is not None:
    print(f"关节角: {data.joint_position}")
    print(f"TCP 位姿: {data.tcp_pose}")
    print(f"运动中: {data.status.is_moving}")
```

---

## CriStreamHandler

```python
class CriStreamHandler:
    def __init__(
        self,
        high_precision: bool = True,
        mask: int = 0xFFFF,
        joint_count: int = 6,
        extra_axis_count: int = 0,
    )
```

可变 mask / 精度的 CRI UDP 包解析。支持灵活的位掩码和精度配置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `high_precision` | `bool` | `True` | 双精度（Float64）/ 单精度（Float32） |
| `mask` | `int` | `0xFFFF` | 位掩码，控制解析哪些字段 |
| `joint_count` | `int` | `6` | 关节数 |
| `extra_axis_count` | `int` | `0` | 外部轴数 |

### bind

```python
def bind(self, port: int) -> None
```

绑定 UDP 端口。

### parse_packet

```python
def parse_packet(self, data: bytes) -> CriRealTimeData
```

解析单个 CRI 数据包。

```python
from codroid import CriStreamHandler

handler = CriStreamHandler(high_precision=True, mask=0xFFFF, joint_count=6)
handler.bind(10086)

try:
    while True:
        data, addr = handler._sock.recvfrom(2048)
        parsed = handler.parse_packet(data)
        print(f"关节角: {parsed.joint_position}")
finally:
    handler._sock.close()
```

---

## CriRealtimeDispatcher

```python
class CriRealtimeDispatcher:
    def __init__(
        self,
        controller_ip: str,
        controller_udp_port: int = 9030,
        convert_to_si: bool = True,
    )
```

UDP 实时命令下发器。发送 64 字节控制指令到控制器。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `controller_ip` | `str` | — | 控制器 IP |
| `controller_udp_port` | `int` | `9030` | 控制器 UDP 端口 |
| `convert_to_si` | `bool` | `True` | 自动将 mm/deg 转换为 m/rad |

支持 `with` 语句。

### SendCommand

```python
def SendCommand(self, position6: Sequence[float], space: TrajectorySpace) -> None
```

发送单帧实时控制指令。

| 参数 | 类型 | 说明 |
|------|------|------|
| `position6` | `Sequence[float]` | 6 个位置值（mm+deg 或 deg） |
| `space` | `TrajectorySpace` | `JOINT` 或 `CARTESIAN` |

### SendTrajectory

```python
def SendTrajectory(
    self,
    trajectory: Iterable[TrajectoryPoint],
    space: TrajectorySpace,
    period_ms: int,
) -> None
```

发送完整轨迹。按 `period_ms` 间隔逐帧发送。

```python
from codroid import CriRealtimeDispatcher, TrajectorySpace

with CriRealtimeDispatcher("192.168.1.136") as dispatcher:
    dispatcher.SendCommand([0, 0, 90, 0, 90, 0], TrajectorySpace.JOINT)
```

---

## TrajectoryGenerator

```python
class TrajectoryGenerator:
    @staticmethod
    def generate(
        start: Sequence[float],
        target: Sequence[float],
        request: TrajectoryRequest,
    ) -> List[TrajectoryPoint]

    @staticmethod
    def generate_multi_segment(
        waypoints: Sequence[Sequence[float]],
        request: TrajectoryRequest,
    ) -> List[TrajectoryPoint]
```

离线轨迹生成。

### generate

单段轨迹生成。`start` 和 `target` 均为 6 元素数组。

### generate_multi_segment

多段轨迹生成。`waypoints` 至少包含 2 个路径点。

```python
from codroid import (
    TrajectoryGenerator,
    TrajectoryRequest,
    TrajectorySpace,
    TrajectoryProfile,
)

request = TrajectoryRequest(
    space=TrajectorySpace.JOINT,
    frequency_hz=100,
    profile=TrajectoryProfile.CUBIC,
    acceleration=100,
    speed=40,
)

trajectory = TrajectoryGenerator.generate(
    [0, 0, 0, 0, 0, 0],
    [0, 0, 90, 0, 90, 0],
    request,
)

for point in trajectory:
    print(f"t={point.t:.3f}s, pos={point.position}")
```

---

## TrajectoryRequest

```python
@dataclass
class TrajectoryRequest:
    space: TrajectorySpace
    frequency_hz: float
    profile: TrajectoryProfile
    acceleration: float
    speed: Optional[float] = None
    duration_seconds: Optional[float] = None
```

轨迹生成请求参数。

| 参数 | 类型 | 说明 |
|------|------|------|
| `space` | `TrajectorySpace` | `JOINT`（关节空间）或 `CARTESIAN`（笛卡尔空间） |
| `frequency_hz` | `float` | 采样频率（Hz） |
| `profile` | `TrajectoryProfile` | `CUBIC`（三次多项式）或 `TRAPEZOIDAL`（梯形） |
| `acceleration` | `float` | 加速度 |
| `speed` | `float` | 速度（与 `duration_seconds` 二选一） |
| `duration_seconds` | `float` | 总时长（与 `speed` 二选一） |

> **注意**：`speed` 和 `duration_seconds` 必须且只能设置其中一个。

---

## TrajectorySpace

```python
class TrajectorySpace(Enum):
    JOINT = "Joint"
    CARTESIAN = "Cartesian"
```

---

## TrajectoryProfile

```python
class TrajectoryProfile(Enum):
    CUBIC = "Cubic"
    TRAPEZOIDAL = "Trapezoidal"
```

---

## TrajectoryPoint

```python
@dataclass
class TrajectoryPoint:
    t: float           # 时间（秒）
    position: List[float]  # 6 个位置值
```

---

## 完整 CRI 控制流程示例

```python
from codroid import (
    CodroidClient,
    CriRealtimeDispatcher,
    TrajectoryGenerator,
    TrajectoryRequest,
    TrajectorySpace,
    TrajectoryProfile,
    InitConsoleUtf8,
)

InitConsoleUtf8()

ROBOT_IP = "192.168.8.136"

with CodroidClient(host=ROBOT_IP) as robot:
    robot.ConnectRemoteAndSwitchOn()

    # 1. 开启 CRI 实时控制
    robot.StartCriControl()

    # 2. 生成轨迹
    request = TrajectoryRequest(
        space=TrajectorySpace.JOINT,
        frequency_hz=250,
        profile=TrajectoryProfile.TRAPEZOIDAL,
        acceleration=100,
        speed=40,
    )
    trajectory = TrajectoryGenerator.generate(
        [0, 0, 0, 0, 0, 0],
        [0, 0, 90, 0, 90, 0],
        request,
    )

    # 3. 下发轨迹
    with CriRealtimeDispatcher(ROBOT_IP) as dispatcher:
        dispatcher.SendTrajectory(trajectory, TrajectorySpace.JOINT, period_ms=4)

    # 4. 关闭实时控制
    robot.StopCriControl()
```

### 工作流程图

```
┌─────────────┐     TCP JSON      ┌──────────────┐
│  Python SDK  │ ──────────────── │  控制器       │
│              │  CRI/StartControl │              │
│              │ ──────────────── │              │
│              │                   │              │
│  CriRealtime │     UDP 64B       │              │
│  Dispatcher  │ ──────────────── │  实时控制接收 │
│              │  每 4ms 一帧      │              │
└─────────────┘                   └──────────────┘
       ▲
       │ UDP 308B（100ms 周期）
       │
┌─────────────┐
│  CRI 数据推送 │
└─────────────┘
```
