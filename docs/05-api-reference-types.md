# 数据类型与枚举

## 通讯模型

### CommonResponse

```python
@dataclass
class CommonResponse:
    id: Union[int, str]
    ty: str
    db: Optional[Any] = None
    err: Optional[Any] = None

    @property
    def is_success(self) -> bool:
        return self.err is None
```

TCP JSON 通用响应。所有 TCP 指令返回此类型。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int / str` | 请求 ID |
| `ty` | `str` | 响应类型 |
| `db` | `Any` | 响应数据 |
| `err` | `Any` | 错误信息（`None` 表示成功） |

历史别名：`CodroidResponse = CommonResponse`

---

### CodroidRequest

```python
@dataclass
class CodroidRequest:
    id: Union[int, str]
    ty: str
    db: Optional[Any] = None
```

SDK 通用请求结构。内部使用。

---

## CRI 实时数据

### CriRealTimeData

```python
@dataclass
class CriRealTimeData:
    timestamp: int = 0
    status: CriStatus = field(default_factory=CriStatus)
    joint_pos: List[float] = field(default_factory=list)
    joint_vel: List[float] = field(default_factory=list)
    cartesian_pos: List[float] = field(default_factory=list)
    cartesian_vel: List[float] = field(default_factory=list)
    tcp_speed: float = 0.0
    joint_torque: List[float] = field(default_factory=list)
    external_torque: List[float] = field(default_factory=list)
    extra_axis_pos: List[float] = field(default_factory=list)
```

CRI 解析后实时数据。所有值已转换为 mm + 度。

| 字段 | 属性别名 | 类型 | 单位 | 说明 |
|------|----------|------|------|------|
| `timestamp` | `timestamp_ms` | `int` | ms | 时间戳 |
| `status` | — | `CriStatus` | — | 状态位 |
| `joint_pos` | `joint_position` | `List[float]` | deg | 6 轴关节角 |
| `joint_vel` | `joint_velocity` | `List[float]` | deg/s | 6 轴关节速度 |
| `cartesian_pos` | `tcp_pose` | `List[float]` | mm, deg | TCP 位姿 [x,y,z,rx,ry,rz] |
| `cartesian_vel` | `tcp_velocity` | `List[float]` | mm/s, deg/s | TCP 速度 |
| `tcp_speed` | `tcp_linear_velocity` | `float` | mm/s | TCP 线速度 |
| `joint_torque` | `joint_output_torque` | `List[float]` | Nm | 关节输出力矩 |
| `external_torque` | `joint_external_force` | `List[float]` | Nm | 外部力矩 |
| `extra_axis_pos` | `external_axis_position` | `List[float]` | — | 外部轴位置 |

历史别名：`CRIData = CriRealTimeData`

---

### CriStatus

```python
@dataclass
class CriStatus:
    status1_raw: int = 0
    status2_raw: int = 0
    project_running: bool = False
    project_stopped: bool = False
    project_paused: bool = False
    is_enabling: bool = False
    is_disabled: bool = False
    is_manual: bool = False
    is_dragging: bool = False
    is_moving: bool = False
    collision_stop: bool = False
    is_at_safe_pos: bool = False
    has_alarm: bool = False
    is_simulation: bool = False
    is_emergency_stop: bool = False
    is_rescue: bool = False
    is_auto: bool = False
    is_remote: bool = False
    rt_control_mode: bool = False
    error_code: int = 0
```

CRI 状态位解析。

| 字段 | 说明 |
|------|------|
| `project_running` | 工程运行中 |
| `project_stopped` | 工程已停止 |
| `project_paused` | 工程已暂停 |
| `is_enabling` | 已使能 |
| `is_disabled` | 未使能 |
| `is_manual` | 手动模式 |
| `is_dragging` | 拖拽模式 |
| `is_moving` | 运动中 |
| `collision_stop` | 碰撞停止 |
| `is_at_safe_pos` | 在安全位置 |
| `has_alarm` | 有报警 |
| `is_simulation` | 仿真模式 |
| `is_emergency_stop` | 急停按下 |
| `is_rescue` | 救援模式 |
| `is_auto` | 自动模式 |
| `is_remote` | 远程模式 |
| `rt_control_mode` | 实时控制模式 |
| `error_code` | 错误码（高 8 位） |

历史别名：`CRIStatus = CriStatus`

---

## 机器人设置

### RobotFrame

```python
@dataclass
class RobotFrame:
    id: int
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0
```

工具 / 用户坐标系单帧。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 槽位 ID（0~15，0 为保留项） |
| `x, y, z` | `float` | 位置（mm） |
| `a, b, c` | `float` | 姿态（度） |

```python
frame = RobotFrame(id=1, x=100, y=0, z=50, a=0, b=0, c=0)
```

---

### RobotPayloadFrame

```python
@dataclass
class RobotPayloadFrame:
    id: int
    m: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0
```

负载坐标系单帧。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 槽位 ID（0~15，0 为保留项） |
| `m` | `float` | 质量（kg） |
| `mx, my, mz` | `float` | 质心位置（mm） |

```python
payload = RobotPayloadFrame(id=1, m=2.5, mx=0, my=0, mz=50)
```

---

### RobotParameters

```python
@dataclass
class RobotParameters:
    default_tool_id: int = 0
    default_payload_id: int = 0
    default_coordinate_id: int = 0
    max_payload: float = 0.0
    tool: List[RobotFrame] = field(default_factory=list)
    payload: List[RobotPayloadFrame] = field(default_factory=list)
    coordinate: List[RobotFrame] = field(default_factory=list)
```

`GetRobotParameters()` 返回的设置界面参数快照。

| 字段 | 类型 | 说明 |
|------|------|------|
| `default_tool_id` | `int` | 默认工具坐标系编号 |
| `default_payload_id` | `int` | 默认负载编号 |
| `default_coordinate_id` | `int` | 默认用户坐标系编号 |
| `max_payload` | `float` | 最大负载（kg） |
| `tool` | `List[RobotFrame]` | 工具坐标系表（16 项） |
| `payload` | `List[RobotPayloadFrame]` | 负载坐标系表（16 项） |
| `coordinate` | `List[RobotFrame]` | 用户坐标系表（16 项） |

---

## 全局变量

### GlobalVariable

```python
@dataclass
class GlobalVariable:
    value: Any
    note: Optional[str] = None
```

全局变量数据模型。

| 字段 | 类型 | 说明 |
|------|------|------|
| `value` | `Any` | 变量值（支持 int, float, str, list, dict） |
| `note` | `str` | 变量备注 |

```python
var = GlobalVariable(value=42, note="计数器")
robot.SaveGlobalVar("counter", var)
```

---

## 枚举类型

### CoordinateType

```python
class CoordinateType(str, Enum):
    USER = "user"
    TOOL = "tool"
```

坐标系类型。

### IOType

```python
class IOType(str, Enum):
    DI = "DI"   # 数字输入
    DO = "DO"   # 数字输出
    AI = "AI"   # 模拟输入
    AO = "AO"   # 模拟输出
```

### ExtendArrayType

```python
class ExtendArrayType(str, Enum):
    BOOL = "Bool"
    UINT8 = "UInt8"
    INT8 = "Int8"
    UINT16 = "UInt16"
    INT16 = "Int16"
    UINT32 = "UInt32"
    INT32 = "Int32"
    FLOAT32 = "Float32"
```

扩展数组数据类型。

### RS485BaudRate

```python
class RS485BaudRate(IntEnum):
    B110 = 110
    B300 = 300
    B600 = 600
    B1200 = 1200
    B2400 = 2400
    B4800 = 4800
    B9600 = 9600
    B14400 = 14400
    B19200 = 19200
    B38400 = 38400
    B56000 = 56000
    B57600 = 57600
    B115200 = 115200
    B128000 = 128000
    B230400 = 230400
```

### RS485StopBits

```python
class RS485StopBits(IntEnum):
    ONE = 1
    TWO = 2
```

### RS485Parity

```python
class RS485Parity(IntEnum):
    NONE = 0
    ODD = 1
    EVEN = 2
```

### CriMask

```python
class CriMask(IntFlag):
    TIMESTAMP = 1 << 0
    STATUS_1 = 1 << 1
    STATUS_2 = 1 << 2
    JOINT_POS = 1 << 8
    JOINT_VEL = 1 << 9
    CARTESIAN_POS = 1 << 10
    CARTESIAN_VEL = 1 << 11
    TCP_SPEED = 1 << 12
    JOINT_TORQUE = 1 << 13
    EXTERNAL_TORQUE = 1 << 14
    EXTRA_AXIS_POS = 1 << 15
```

CRI 推送位掩码。

历史别名：`CRIMask = CriMask`

### CriFilterType

```python
class CriFilterType(IntEnum):
    NONE = 0
    AVERAGE = 1
    LOW_PASS = 2
    ELLIPTIC = 3
```

CRI 实时控制滤波类型。

历史别名：`CRIFilterType = CriFilterType`

---

## 异常

### CodroidError

```python
class CodroidError(Exception):
    pass
```

基础异常类。参数校验失败、非法操作等。

### CodroidCommandException

```python
class CodroidCommandException(CodroidError):
    pass
```

控制器返回 `err` 字段。

### CodroidNetworkError

```python
class CodroidNetworkError(CodroidError):
    pass
```

TCP 连接或通信失败。

### CodroidTimeoutError

```python
class CodroidTimeoutError(CodroidError):
    pass
```

操作超时。
