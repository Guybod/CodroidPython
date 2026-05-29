# 快速上手

## 安装

### 通过 pip 安装

```bash
pip install codroid-robot-sdk
```

可选彩色终端输出：

```bash
pip install "codroid-robot-sdk[color]"
```

### 从源码安装

```bash
git clone https://github.com/guybod/CodroidSDK.git
cd CodroidSDK/CodroidPython
pip install -e .
```

---

## 最小示例

连接控制器，进入远程模式，上使能。

```python
from codroid import CodroidControlInterface, InitConsoleUtf8

InitConsoleUtf8()  # Windows cmd 下中文日志不乱码；Linux 上为 no-op

ROBOT_IP = "192.168.1.136"

with CodroidControlInterface(host=ROBOT_IP) as robot:
    robot.EnterRemoteModeViaAuto()
    robot.SwitchOn()
```

运行：

```bash
python3 demo.py
```

---

## 完整工作流示例

```python
from codroid import (
    CodroidControlInterface,
    JointPoint,
    CartesianPoint,
    MoveInstruction,
    InitConsoleUtf8,
)

InitConsoleUtf8()

ROBOT_IP = "192.168.1.136"

with CodroidControlInterface(host=ROBOT_IP) as robot:
    # 1. 连接并上电
    robot.EnterRemoteModeViaAuto()
    robot.SwitchOn()

    # 2. IO 操作
    di0 = robot.GetDi(0)
    robot.SetDo(10, di0)

    # 3. 寄存器
    reg_val = robot.GetRegisterValue(0)
    robot.SetRegisterValue(0, reg_val + 1)

    # 4. 关节运动
    robot.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=40, acceleration=100)

    # 5. 直线运动
    robot.MovL(CartesianPoint.MmDeg([400, 200, 500, 180, 0, 90]),
               speed=150, acceleration=500)
```

---

## 使用 CodroidClient

`CodroidClient` 继承自 `CodroidSession`，使用后台线程接收数据，支持 publish/subscribe 事件分发。适用于需要持续收包的场景。

```python
from codroid import CodroidClient, InitConsoleUtf8

InitConsoleUtf8()

with CodroidClient(host="192.168.1.136") as robot:
    robot.EnterRemoteModeViaAuto()
    robot.SwitchOn()
```

---

## 运行示例项目

```bash
# 基本用法
PYTHONPATH=src python examples/01_basic_usage.py --robot 192.168.8.136

# 运动示例
PYTHONPATH=src python examples/08_move.py --robot 192.168.8.136

# 阻塞式运动
PYTHONPATH=src python examples/15_sync_motion.py --robot 192.168.8.136

# 机器人设置
PYTHONPATH=src python examples/14_robot_parameters.py --robot 192.168.8.136
```

---

## 错误处理

所有 TCP 指令在失败时抛出异常：

| 异常 | 条件 |
|------|------|
| `CodroidError` | 基础异常类 |
| `CodroidCommandException` | 控制器返回 `err` 字段 |
| `CodroidNetworkError` | TCP 连接或通信失败 |
| `CodroidTimeoutError` | 操作超时 |

```python
from codroid import CodroidControlInterface, CodroidError, CodroidTimeoutError

try:
    with CodroidControlInterface(host="192.168.1.136") as robot:
        robot.EnterRemoteModeViaAuto()
        robot.SwitchOn()
        robot.MovJ([0, 0, 90, 0, 90, 0], speed=40, acceleration=100)
except CodroidTimeoutError:
    print("操作超时")
except CodroidError as e:
    print(f"SDK 错误: {e}")
```

---

## Windows 控制台 UTF-8

在 `cmd`（非 Windows Terminal）下运行含中文的示例时，请在入口调用：

```python
from codroid import InitConsoleUtf8

InitConsoleUtf8()
```

所有 `examples/*.py` 已在 `if __name__ == "__main__"` 首行调用。自建 CLI 请同样处理；`chcp 65001` 不能替代此调用。Linux / macOS 上为 no-op。
