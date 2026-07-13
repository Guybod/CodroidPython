# 力控 API 参考

## 概述

Python SDK 当前固定使用导纳算法进入力控：`InitForceControl()` 内部固定下发 `algo=1`。SDK 已提供 `ForceControlAlgo` 枚举用于对齐协议值，但当前版本不开放 `algo` 入参。

力控支持逐自由度配置位控 / 力控 / 柔顺，进入前建议先执行零力校准。

## 枚举类型

```python
class ForceControlAlgo(IntEnum):
    IMPEDANCE = 0
    ADMITTANCE = 1
    PD_FORCE = 2

class ForceFrame(IntEnum):
    TCP = 0
    USER = 1
    WORLD = 2

class ForceAxisMode(IntEnum):
    POSITION = 0
    FORCE = 1
    COMPLIANT = 2

class ForceHealth(IntEnum):
    OK = 0
    INVALID = 1
    TIMEOUT = 2
    SATURATED = 3
    PACKET_LOSS = 4
```

## ZeroForceCalibration

六维力传感器零力校准 / 带载去皮。

```python
def ZeroForceCalibration(
    self,
    calibration_time_ms: int = 1000,
    timeout_ms: int = 5000,
) -> CommonResponse
```

`calibration_time_ms` 会下发为协议字段 `calibrationTimeMs`；`timeout_ms` 只控制 Python SDK 等待响应的本地超时时间，不会写入请求 `db`。

## InitForceControl

进入力控前一次性配参。当前 SDK 不允许传 `algo`，内部固定为导纳 `algo=1`。

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

`axis_mode` 是 6 元素列表：`0` 位控，`1` 力控，`2` 柔顺。`constant_force` 是否激活由 `axis_mode` 中的 `FORCE` 轴决定，`compliance` 是否激活由 `COMPLIANT` 轴决定。

`constant_force` 子字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `desiredForce` | `float[6]` | 期望力 / 力矩；当 `axis_mode` 含 `FORCE` 轴时必须提供 |
| `damping` | `float[6]` | 力控方向阻尼 |
| `mass` | `float[6]` | 力控方向质量，导纳须 >0 |
| `rampTimeMs` | `float` | 期望力斜坡加载时间 |
| `modulationFreqHz` | `float` | 力调制频率，0=恒定 |
| `modulationAmplitude` | `float` | 力调制幅值 |

`compliance` 子字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `stiffness` | `float[6]` | 柔顺方向刚度 |
| `damping` | `float[6]` | 柔顺方向阻尼 |
| `mass` | `float[6]` | 柔顺方向质量，导纳须 >0 |
| `rampTimeMs` | `float` | 兼容字段 |

示例：

```python
session.InitForceControl(
    frame=ForceFrame.TCP,
    axis_mode=[
        ForceAxisMode.POSITION,
        ForceAxisMode.POSITION,
        ForceAxisMode.FORCE,
        ForceAxisMode.POSITION,
        ForceAxisMode.POSITION,
        ForceAxisMode.POSITION,
    ],
    constant_force={
        "desiredForce": [0, 0, 2, 0, 0, 0],
        "damping": [250, 250, 250, 7.5, 7.5, 7.5],
        "mass": [2.5, 2.5, 2.5, 0.15, 0.15, 0.15],
        "rampTimeMs": 500,
    },
)
```

## StartForceControl / StopForceControl

```python
def StartForceControl(self) -> CommonResponse
def StopForceControl(self, smooth_time_ms: int = 500) -> CommonResponse
```

`StopForceControl` 在运动指令执行期间可能被控制器拒绝；推荐先停止运动，或使用程序级 stop 联动力控平滑退出。

## TuneForceParams

```python
def TuneForceParams(
    self,
    stiffness: Optional[List[float]] = None,
    damping: Optional[List[float]] = None,
    mass: Optional[List[float]] = None,
    desired_force: Optional[List[float]] = None,
    kp: Optional[List[float]] = None,
    kd: Optional[List[float]] = None,
    ramp_time: Optional[float] = None,
) -> CommonResponse
```

`ramp_time` 会下发为协议字段 `rampTime`，单位 ms；`0` 表示立即生效。

## StartContactDetection

```python
def StartContactDetection(
    self,
    direction: List[float],
    feed_velocity: Optional[float] = None,
    contact_force_threshold: Optional[float] = None,
    vel_drop_ratio: Optional[float] = None,
    max_travel: Optional[float] = None,
    timeout_ms: Optional[float] = None,
) -> CommonResponse
```

`direction` 必须是 6 元素列表；`max_travel` 建议显式传入并大于 0。

## SetOverforceProtection

```python
def SetOverforceProtection(
    self,
    enable: Optional[bool] = None,
    force_threshold: Optional[List[float]] = None,
    hold_ms: Optional[float] = None,
) -> CommonResponse
```

只更新传入字段。`force_threshold` 是 `[Fx,Fy,Fz,Mx,My,Mz]`，0 表示该方向不监测。

## SetForceDataHealth

```python
def SetForceDataHealth(
    self,
    enable: Optional[bool] = None,
    timeout_ms: Optional[float] = None,
    max_packet_loss_ratio: Optional[float] = None,
    packet_loss_window: Optional[int] = None,
    force_saturation: Optional[float] = None,
    torque_saturation: Optional[float] = None,
) -> CommonResponse
```

只更新传入字段。

## GetForceState

```python
def GetForceState(self) -> ForceControlState
```

返回完整 `ForceControlState`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `enabled` | `bool` | 已进入力控 |
| `pending` | `bool` | 已受理请求、尚未进入 |
| `algo` | `int` | 当前算法，当前固定为 1 |
| `valid` | `bool` | 外力数据有效性 |
| `is_contact` | `bool` | 接触判据 |
| `is_overforce` | `bool` | 过力判据 |
| `health` | `int` | 数据健康状态 |
| `wrench_tcp` | `List[float]` | TCP 系外力 |
| `wrench_base` | `List[float]` | 基座系外力 |
| `desired_wrench` | `List[float]` | 期望力 |
| `track_error` | `List[float]` | 力跟踪误差 |
| `axis_mode` | `List[int]` | 选择矩阵快照 |

也可以按字段单独读取：

```python
session.GetForceStateEnabled()       # bool
session.GetForceStatePending()       # bool
session.GetForceStateAlgo()          # int
session.GetForceStateValid()         # bool
session.GetForceStateIsContact()     # bool
session.GetForceStateIsOverforce()   # bool
session.GetForceStateHealth()        # int
session.GetForceStateWrenchTcp()     # List[float]
session.GetForceStateWrenchBase()    # List[float]
session.GetForceStateDesiredWrench() # List[float]
session.GetForceStateTrackError()    # List[float]
session.GetForceStateAxisMode()      # List[int]
```
