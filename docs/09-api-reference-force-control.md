# 力控 API 参考

## 概述

力控工艺包提供导纳力控算法与三类功能原语（恒力、柔顺、力限幅），支持逐自由度配置位控/力控/柔顺。

- **算法**：固定为导纳（Admittance）
- **坐标系**：TCP / 用户系 / 世界系
- **轴模式**：位控（Position）/ 力控（Force）/ 柔顺（Compliant）

### 前置条件

1. 机器人处于 Ready 状态（无其他运动占用）
2. 进入瞬间 TCP 速度 ≈ 0（>1e-3 m/s 会被拒绝）
3. 至少配置一个力控或柔顺自由度
4. 建议先做带载去皮/零力校准

### 单位约定

| 量 | 单位 |
|---|---|
| 力/力矩 | N / N·m |
| 刚度 K | N/m, N·m/rad |
| 阻尼 D | N·s/m, N·m·s/rad |
| 质量 M | kg, kg·m² |
| 长度 | m |
| 角度（仅 userFrameRpy） | deg |
| 时间 | ms |

> 六维顺序统一为 [X, Y, Z, RX, RY, RZ]。

---

## 枚举类型

### ForceFrame

力控坐标系。

```python
class ForceFrame(IntEnum):
    TCP = 0    # 工具系
    USER = 1   # 用户系
    WORLD = 2  # 世界系
```

### ForceAxisMode

力控轴模式。

```python
class ForceAxisMode(IntEnum):
    POSITION = 0   # 位控: 跟踪规划轨迹
    FORCE = 1      # 力控: 跟踪期望力 F_des
    COMPLIANT = 2  # 柔顺: 导纳/阻抗顺从
```

### ForceHealth

力控数据健康状态。

```python
class ForceHealth(IntEnum):
    OK = 0          # 正常
    INVALID = 1     # 数值无效 (NaN/Inf)
    TIMEOUT = 2     # 超时
    SATURATED = 3   # 饱和
    PACKET_LOSS = 4 # 丢包超限
```

---

## 数据类型

### ForceControlState

力控实时状态（由 `GetForceState()` 返回）。

```python
@dataclass
class ForceControlState:
    enabled: bool = False               # 已进入力控
    pending: bool = False               # 已受理请求、尚未进入
    algo: int = 0                       # 当前算法（固定为 1=导纳）
    valid: bool = False                 # 外力数据有效性
    is_contact: bool = False            # 接触判据
    is_overforce: bool = False          # 过力判据
    health: int = 0                     # 数据健康状态 (ForceHealth)
    wrench_tcp: List[float]             # TCP 系外力 [Fx,Fy,Fz,Mx,My,Mz] (N/N·m)
    wrench_base: List[float]            # 基座系外力
    desired_wrench: List[float]         # 期望力 F_des
    track_error: List[float]            # 力跟踪误差
    axis_mode: List[int]                # 选择矩阵 S 快照
```

---

## API 方法

### FTSensorDriftCalibration

六维力传感器零力校准/去皮（阻塞，约 2500ms）。建议在每次进入力控前执行，以保证外力计算准确。

```python
def FTSensorDriftCalibration(self, timeout_ms: int = 3000) -> CommonResponse
```

**参数**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `timeout_ms` | `int` | `3000` | 超时时间 (ms)，超时抛出 `CodroidTimeoutError` |

**异常**

- `CodroidTimeoutError`: 超时未响应，请检查传感器连接。

**示例**

```python
# 进入力控前执行零力校准
session.FTSensorDriftCalibration()  # 默认 3000ms 超时

# 自定义超时
session.FTSensorDriftCalibration(timeout_ms=5000)

# 然后进入力控
session.InitForceControl(...)
session.StartForceControl()
```

---

### InitForceControl

进入力控前一次性配参（导纳算法/坐标系/S矩阵/原语/M·D·K，无斜坡）。

```python
def InitForceControl(
    self,
    frame: int,
    axis_mode: List[int],
    compliance: Optional[Dict[str, Any]] = None,
    constant_force: Optional[Dict[str, Any]] = None,
    user_frame_rpy: Optional[List[float]] = None,
    desired_wrench: Optional[List[float]] = None,
    force_limit: Optional[Dict[str, Any]] = None,
) -> CommonResponse
```

**参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `frame` | `int` | 力控坐标系 (`ForceFrame`): 0=TCP, 1=用户系, 2=世界系 |
| `axis_mode` | `List[int]` | 选择矩阵 S，6 个元素 (`ForceAxisMode`): 0=位控, 1=力控, 2=柔顺 |
| `compliance` | `Dict` | 柔顺原语配置（可选） |
| `constant_force` | `Dict` | 恒力原语配置（可选） |
| `user_frame_rpy` | `List[float]` | 用户系姿态 [rx,ry,rz] (deg)，frame=1 时生效（可选） |
| `desired_wrench` | `List[float]` | 期望力简写 [Fx,Fy,Fz,Mx,My,Mz] (N/N·m)，仅当未给 constant_force 时生效（可选） |
| `force_limit` | `Dict` | 工艺级力限幅: `{"wrenchLimit": float[6]}`（可选） |

**compliance 子字段**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `stiffness` | `float[6]` | 见配置 | 柔顺方向刚度 K (N/m, N·m/rad) |
| `damping` | `float[6]` | 见配置 | 柔顺方向阻尼 D (N·s/m, N·m·s/rad) |
| `mass` | `float[6]` | 见配置 | 柔顺方向质量 M (kg, kg·m²)，导纳须 >0 |
| `activate` | `bool` | `True` | 是否激活该原语 |

**constant_force 子字段**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `desiredForce` | `float[6]` | `0` | 各方向期望力/力矩 (N/N·m) |
| `stiffness` | `float[6]` | 见配置 | 力控方向刚度 K（纯力跟踪取 0） |
| `damping` | `float[6]` | 见配置 | 力控方向阻尼 D |
| `mass` | `float[6]` | 见配置 | 力控方向质量 M，导纳须 >0 |
| `rampTimeMs` | `float` | `200` | 期望力斜坡加载时间 (ms) |
| `modulationFreqHz` | `float` | `0` | 力调制频率（0=恒定） |
| `modulationAmplitude` | `float` | `0` | 力调制幅值 (N/N·m) |
| `activate` | `bool` | `True` | 是否激活该原语 |

**示例**

```python
from codroid import CodroidSession, ForceFrame, ForceAxisMode

session = CodroidSession("192.168.1.136", 9001)
session.Connect()

# Z 向 2N 恒力，XY 柔顺
session.InitForceControl(
    frame=ForceFrame.TCP,
    axis_mode=[
        ForceAxisMode.COMPLIANT,  # X: 柔顺
        ForceAxisMode.COMPLIANT,  # Y: 柔顺
        ForceAxisMode.FORCE,      # Z: 力控
        ForceAxisMode.POSITION,   # RX: 位控
        ForceAxisMode.POSITION,   # RY: 位控
        ForceAxisMode.POSITION,   # RZ: 位控
    ],
    constant_force={
        "desiredForce": [0, 0, 2, 0, 0, 0],
        "stiffness": [0, 0, 0, 0, 0, 0],
        "damping": [250, 250, 250, 7.5, 7.5, 7.5],
        "mass": [2.5, 2.5, 2.5, 0.15, 0.15, 0.15],
    },
    compliance={
        "stiffness": [800, 800, 800, 50, 50, 50],
        "damping": [250, 250, 250, 7.5, 7.5, 7.5],
        "mass": [2.5, 2.5, 2.5, 0.15, 0.15, 0.15],
    },
)
```

---

### StartForceControl

触发进入力控（参数须已由 `InitForceControl` 配好）。

```python
def StartForceControl(self) -> CommonResponse
```

**返回**

- 成功：`{ "success": true }`
- 已激活或请求中：`{ "success": false, "msg": "force control already active or pending" }`

**示例**

```python
session.StartForceControl()
time.sleep(2)  # 等待状态机 Ready 时正式进入
```

---

### StopForceControl

平滑退出力控（算法斜坡衰减 → 释放权限 → 切回保位）。

```python
def StopForceControl(self, smooth_time_ms: int = 300) -> CommonResponse
```

**参数**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `smooth_time_ms` | `int` | `300` | 平滑退出斜坡时长 (ms) |

**示例**

```python
session.StopForceControl(smooth_time_ms=500)
```

---

### TuneForceParams

在线调参（运行中调整 M/D/K、期望力，经算法斜坡平滑生效）。

```python
def TuneForceParams(
    self,
    stiffness: Optional[List[float]] = None,
    damping: Optional[List[float]] = None,
    mass: Optional[List[float]] = None,
    desired_force: Optional[List[float]] = None,
    kp: Optional[List[float]] = None,
    kd: Optional[List[float]] = None,
) -> CommonResponse
```

**参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `stiffness` | `float[6]` | 刚度 K (N/m, N·m/rad)（可选） |
| `damping` | `float[6]` | 阻尼 D (N·s/m, N·m·s/rad)（可选） |
| `mass` | `float[6]` | 质量 M (kg, kg·m²)，导纳须 >0（可选） |
| `desired_force` | `float[6]` | 期望力 (N/N·m)，恒力原语斜坡加载（可选） |
| `kp` | `float[6]` | PD 力控 kp 增益（可选，仅 PD 力控） |
| `kd` | `float[6]` | PD 力控 kd 增益（可选，仅 PD 力控） |

**示例**

```python
# 在线提升目标压力到 30N
session.TuneForceParams(desired_force=[0, 0, -30, 0, 0, 0])

# 调整刚度和阻尼
session.TuneForceParams(
    stiffness=[0, 0, 100, 0, 0, 0],
    damping=[0, 0, 50, 0, 0, 0],
)
```

---

### GetForceState

查询力控实时状态。

```python
def GetForceState(self) -> ForceControlState
```

**返回**

`ForceControlState` 数据类，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | `bool` | 已进入力控 |
| `pending` | `bool` | 已受理请求、尚未进入 |
| `algo` | `int` | 当前算法（固定为 1=导纳） |
| `valid` | `bool` | 外力数据有效性 |
| `is_contact` | `bool` | 接触判据 |
| `is_overforce` | `bool` | 过力判据 |
| `health` | `int` | 数据健康状态 (`ForceHealth`) |
| `wrench_tcp` | `float[6]` | TCP 系外力 (N/N·m) |
| `wrench_base` | `float[6]` | 基座系外力 (N/N·m) |
| `desired_wrench` | `float[6]` | 期望力 F_des |
| `track_error` | `float[6]` | 力跟踪误差 |
| `axis_mode` | `int[6]` | 选择矩阵 S 快照 |

**示例**

```python
state = session.GetForceState()
print(f"力控已启用: {state.enabled}")
print(f"TCP 外力: {state.wrench_tcp}")
print(f"期望力: {state.desired_wrench}")
print(f"力跟踪误差: {state.track_error}")
print(f"健康状态: {ForceHealth(state.health).name}")
```

---

## 典型使用流程

```
FTSensorDriftCalibration  // (建议) 零力校准/去皮
        │
        ▼
InitForceControl          // 配参: 坐标系 + S矩阵 + 原语 + M/D/K
        │
        ▼
StartForceControl         // 进入(置请求位; 状态机在 Ready 时完成进入)
        │
        ▼
[ 运行中 ]
  ├─ TuneForceParams      // (可选) 在线调 M/D/K、期望力(斜坡平滑)
  └─ GetForceState        // (可选) 轮询实时状态
        │
        ▼
StopForceControl          // 平滑退出
```

---

## 典型场景

### 场景一：导纳柔顺（全轴柔顺）

```python
# 配参：全轴柔顺，适中刚度
session.InitForceControl(
    frame=ForceFrame.TCP,
    axis_mode=[
        ForceAxisMode.COMPLIANT,  # X: 柔顺
        ForceAxisMode.COMPLIANT,  # Y: 柔顺
        ForceAxisMode.COMPLIANT,  # Z: 柔顺
        ForceAxisMode.COMPLIANT,  # RX: 柔顺
        ForceAxisMode.COMPLIANT,  # RY: 柔顺
        ForceAxisMode.COMPLIANT,  # RZ: 柔顺
    ],
    compliance={
        "stiffness": [800, 800, 800, 50, 50, 50],
        "damping": [250, 250, 250, 7.5, 7.5, 7.5],
        "mass": [2.5, 2.5, 2.5, 0.15, 0.15, 0.15],
    },
)

session.StartForceControl()
time.sleep(2)

# 运动过程中全轴柔顺，外力可推动
session.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), 30, 100)

session.StopForceControl(smooth_time_ms=500)
```

### 场景二：导纳恒力跟踪（Z 方向恒定压力）

```python
# 配参：Z 方向 2N 恒力，纯力跟踪 K=0
session.InitForceControl(
    frame=ForceFrame.TCP,
    axis_mode=[
        ForceAxisMode.POSITION, # X: 位控
        ForceAxisMode.POSITION, # Y: 位控
        ForceAxisMode.FORCE,    # Z: 力控
        ForceAxisMode.POSITION, # RX: 位控
        ForceAxisMode.POSITION, # RY: 位控
        ForceAxisMode.POSITION, # RZ: 位控
    ],
    constant_force={
        "desiredForce": [0, 0, 2, 0, 0, 0],
        "stiffness": [0, 0, 0, 0, 0, 0],
        "damping": [250, 250, 250, 7.5, 7.5, 7.5],
        "mass": [2.5, 2.5, 2.5, 0.15, 0.15, 0.15],
        "rampTimeMs": 500,
    },
)

session.StartForceControl()
time.sleep(2)

# 在线提升目标压力到 5N
session.TuneForceParams(desired_force=[0, 0, 5, 0, 0, 0])
time.sleep(3)

session.StopForceControl(smooth_time_ms=800)
```

---

## 安全机制

力控内置常驻安全红线，**无法通过 API 关闭**：

- **过力保护**：进入力控即激活，任一方向 |F| 超阈触发停止/退让
- **力控级安全**：任务空间输出力限幅、最大行程、力跟踪误差发散判据
- **数据健康监控**：超时/饱和/丢包/数值无效任一异常 → 退出力控保位

---

## 错误/事件码

| 事件码 | 含义 |
|--------|------|
| 16102 | 未初始化即调用 |
| 16103 | 参数非法 |
| 16104 | 模型/雅可比不可用 |
| 16105 | IK/雅可比求解失败 |
| 16106 | 外力数据失效 |
| 16107 | 控制发散 |
| 16108 | 超出最大行程 |
| 16109 | 过力 |
| 16110 | 进入失败（如无力控/柔顺轴） |
| 16111 | 带速度进入力控（TCP 速度未归零） |
