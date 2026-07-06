# 运动 API 参考

## 运动目标类型

### JointPoint

```python
@dataclass
class JointPoint:
    jp: List[float]  # 6 个关节角（度）
```

关节目标。业务层用于声明「这是六轴关节角」，避免与 TCP 位姿混淆。

#### 工厂方法

```python
JointPoint.Degrees(joints_deg: Sequence[float]) -> JointPoint
```

由六轴关节角（度）构造。

```python
jp = JointPoint.Degrees([0, 0, 90, 0, 90, 0])
```

---

### CartesianPoint

```python
@dataclass
class CartesianPoint:
    cp: List[float]                    # TCP 位姿 [x,y,z,rx,ry,rz]（mm + 度）
    rj: Optional[List[float]] = None   # 逆解参考关节角（度）
```

笛卡尔目标。`cp` 必填；`rj` 可选（打包时缺省为控制器默认参考关节）。

#### 工厂方法

```python
CartesianPoint.MmDeg(pose_mm_deg: Sequence[float]) -> CartesianPoint
```

TCP 位姿 `[x,y,z,rx,ry,rz]`（mm + 度），无参考关节。

```python
CartesianPoint.MmDegWithRef(
    pose_mm_deg: Sequence[float],
    ref_joints_deg: Sequence[float],
) -> CartesianPoint
```

TCP 位姿 + 逆解参考关节（度）。当 movJ/movL 到 TCP 且在意姿态解时推荐使用。

```python
cp = CartesianPoint.MmDeg([400, 200, 500, 180, 0, 90])
cp_with_ref = CartesianPoint.MmDegWithRef(
    [400, 200, 500, 180, 0, 90],
    [0, 0, 90, 0, 90, 0],
)
```

---

### MovePoint

```python
@dataclass
class MovePoint:
    jp: Optional[Sequence[float]] = None
    cp: Optional[Sequence[float]] = None
    rj: Optional[Sequence[float]] = None
    ep: Optional[Sequence[float]] = None
```

通用运动点位定义。通常不直接使用，而是通过 `JointPoint` / `CartesianPoint` 构造。

#### 工厂方法

```python
MovePoint.FromJoint(joint: JointPoint) -> MovePoint
MovePoint.FromCartesian(cart: CartesianPoint) -> MovePoint
```

---

## 运动指令

### MoveInstruction

```python
@dataclass
class MoveInstruction:
    motion_type: MotionType
    target: MovePoint
    speed: float
    acc: float
    blend: Optional[float] = None
    relative_blend: Optional[float] = None
    middle: Optional[MovePoint] = None
    circle_num: Optional[int] = None
    coor: Optional[Sequence[float]] = None
    tool: Optional[Sequence[float]] = None
```

单段 `Robot/move` 指令。请用类方法构建，勿手写 `type` + 裸 `MovePoint`。

#### 工厂方法

##### MoveInstruction.MovJ

```python
MoveInstruction.MovJ(
    target: Union[JointPoint, CartesianPoint],
    speed: float,
    acc: float,
    blend: Optional[float] = None,
    relative_blend: Optional[float] = None,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> MoveInstruction
```

关节运动 movJ。目标可为关节或 TCP。

##### MoveInstruction.MovL

```python
MoveInstruction.MovL(
    target: Union[CartesianPoint, JointPoint],
    speed: float,
    acc: float,
    blend: Optional[float] = None,
    relative_blend: Optional[float] = None,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> MoveInstruction
```

直线运动 movL。目标可为 TCP 或关节。

##### MoveInstruction.MovC

```python
MoveInstruction.MovC(
    middle: CartesianPoint,
    target: CartesianPoint,
    speed: float,
    acc: float,
    blend: Optional[float] = None,
    relative_blend: Optional[float] = None,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> MoveInstruction
```

圆弧运动 movC。中间点与目标均为 TCP。

##### MoveInstruction.MovCircle

```python
MoveInstruction.MovCircle(
    middle: CartesianPoint,
    target: CartesianPoint,
    circle_num: int,
    speed: float,
    acc: float,
    blend: Optional[float] = None,
    relative_blend: Optional[float] = None,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> MoveInstruction
```

整圆运动 movCircle。

---

### MotionType

```python
class MotionType(str, Enum):
    MOVJ = "movJ"
    MOVL = "movL"
    MOVC = "movC"
    MOVCIRCLE = "movCircle"
```

---

## MoveTo 目标

### MoveToTarget

```python
@dataclass
class MoveToTarget:
    cp: Optional[Sequence[float]] = None
    jp: Optional[Sequence[float]] = None
    ep: Sequence[float] = field(default_factory=list)
```

MoveTo 专用目标结构。

#### 工厂方法

```python
MoveToTarget.Joint(joint: JointPoint) -> MoveToTarget
MoveToTarget.Cartesian(cart: CartesianPoint) -> MoveToTarget
```

### MoveToType

```python
class MoveToType(IntEnum):
    STOP = -1      # 停止 MoveTo
    HOME = 0       # Home 点
    SAFE = 1       # 安全位
    CANDLE = 2     # 蜡烛位
    PACK = 3       # 打包位
    JOINT = 4      # 关节规划
    LINEAR = 5     # 直线规划
    RESUME = 6     # 程序恢复点
```

---

## 点动参数

### JogMode

```python
class JogMode(IntEnum):
    JOINT = 1    # 关节点动
    LINEAR = 2   # 直线点动
```

### JogCoorType

```python
class JogCoorType(IntEnum):
    USER = 0     # 用户坐标系
    TOOL = 1     # 工具坐标系
```

---

## MotionPath（过渡 API）

```python
class MotionPath:
    def add(self, instruction: MoveInstruction) -> MotionPath
    def MovJ(self, target, speed, acc, blend=None) -> MotionPath
    def MovL(self, target, speed, acc, blend=None) -> MotionPath
    def MovC(self, target, middle, speed, acc, blend=None) -> MotionPath
    def clear(self) -> None
    def get_commands(self) -> List[Dict[str, Any]]
```

运动路径构建器。新代码优先使用 `List[MoveInstruction]` + `Move()`。

```python
path = MotionPath()
path.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=40, acc=100)
path.MovL(CartesianPoint.MmDeg([400, 200, 500, 180, 0, 90]), speed=150, acc=500)
robot.Move(path)
```

---

## 完整多段路径示例

```python
from codroid import (
    CodroidClient,
    JointPoint,
    CartesianPoint,
    MoveInstruction,
    MotionWaitOptions,
    InitConsoleUtf8,
)

InitConsoleUtf8()

with CodroidClient(host="192.168.8.136") as robot:
    robot.ConnectRemoteAndSwitchOn()

    # 四组合路径
    path = [
        MoveInstruction.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]),
                             speed=40, acc=100),
        MoveInstruction.MovJ(CartesianPoint.MmDeg([400, 200, 500, 180, 0, 90]),
                             speed=40, acc=100),
        MoveInstruction.MovL(CartesianPoint.MmDeg([400, -200, 500, 180, 0, 90]),
                             speed=150, acc=500),
        MoveInstruction.MovL(JointPoint.Degrees([0, 0, 0, 0, 0, 0]),
                             speed=150, acc=500),
    ]
    robot.Move(path)

    # 阻塞式路径执行
    robot.StartListenUdp()
    robot.WaitForCriData()
    robot.MoveSync(path, wait=MotionWaitOptions(timeout=120.0))
```

---

## 运动参数说明

### speed / acceleration

- `speed`：速度值，具体单位取决于运动类型和控制器配置。
- `acceleration`：加速度值。

### blend

平滑半径。默认 `0.0`（精确到达目标点）。设置大于 0 的值时，机器人在接近目标点时平滑过渡，不停留。

### coor / tool

可选的用户坐标系和工具坐标系，格式为 `[x, y, z, a, b, c]`（mm + 度）。

---

## MotionWaitOptions（阻塞运动等待参数）

```python
@dataclass
class MotionWaitOptions:
    timeout: float = 60.0
    poll_interval: float = 0.05
    cri_stale_timeout: float = 0.5
    settled_samples: int = 3
    use_tolerance: bool = False
    joint_tolerance_deg: float = 0.5
    cartesian_position_tolerance_mm: float = 1.0
    cartesian_orientation_tolerance_deg: float = 1.0
```

用于 `MoveSync` / `MovJSync` / `MovLSync` / `MovCSync` / `MovCircleSync` 控制 CRI 轮询行为。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `timeout` | `float` | `60.0` | 整体等待超时（秒） |
| `poll_interval` | `float` | `0.05` | 轮询间隔（秒） |
| `cri_stale_timeout` | `float` | `0.5` | CRI 数据过期判定（秒） |
| `settled_samples` | `int` | `3` | `InMotion=False` 连续稳定采样数 |
| `use_tolerance` | `bool` | `False` | 是否启用容差前置判断 |
| `joint_tolerance_deg` | `float` | `0.5` | 关节容差（度） |
| `cartesian_position_tolerance_mm` | `float` | `1.0` | 笛卡尔位置容差（mm） |
| `cartesian_orientation_tolerance_deg` | `float` | `1.0` | 姿态容差（度） |
| `motion_start_timeout` | `float` | `1.0` | 等待 InMotion 变为 true 的超时（秒） |

### 容差前置判断

当 `use_tolerance=True` 时：
1. 收到目标后，先比较当前位置和目标位置
2. 如果误差在容差范围内，直接返回 `true`，不等待 `InMotion`
3. 如果超出容差，才走 `InMotion` 轮询逻辑
4. 如果整个超时期间 `InMotion` 从未变为 `true`，抛出 `CodroidError`

适用场景：目标和当前位置非常接近（如微调），避免因机器人不运动而超时。

```python
# 启用容差前置判断
opts = MotionWaitOptions(
    use_tolerance=True,
    joint_tolerance_deg=0.5,
    cartesian_position_tolerance_mm=1.0,
)
robot.MovJSync(target, speed=50, acc=500, wait=opts)
```
