# Codroid 机器人 Python SDK

Codroid 控制器 Python SDK，提供 TCP 控制、实时数据（CRI）与轨迹相关能力。

[![PyPI - Version](https://img.shields.io/pypi/v/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)

---

## 教程：5 分钟跑通

### 1) 环境准备

- Python 3.7 及以上（建议 3.8+）
- 机器人控制器与运行脚本的电脑网络互通

### 2) 安装 SDK

```bash
pip install codroid-robot-sdk
```

可选彩色终端输出：

```bash
pip install "codroid-robot-sdk[color]"
```

### 3) 验证安装

```bash
python3 -c "import codroid; print(codroid.__version__)"
```

### 4) 第一个控制脚本

新建 `demo.py`：

```python
from codroid import CodroidControlInterface, InitConsoleUtf8

InitConsoleUtf8()  # Windows cmd 下中文日志不乱码；Linux 上为 no-op

ROBOT_IP = "192.168.1.136"  # 改成实际控制器 IP

with CodroidControlInterface(host=ROBOT_IP) as robot:
    robot.to_remote()
    robot.switch_on()
```

运行：

```bash
python3 demo.py
```

### 5) 常见下一步

- 进入远程模式后，继续调用运动、IO、寄存器等 API。
- 需要持续收包和 publish 分发时，改用 `CodroidClient`。
- 运动示例见 `examples/08_move.py`（四组合路径）与 `examples/codroid_test.py motion`。

## 运动 API（2.1+）

协议 JSON 未变；业务层须用类型区分关节与 TCP，避免把位姿当关节角下发。

| 业务类型 | 工厂 | 用于 |
|----------|------|------|
| `JointPoint` | `Degrees([j1..j6])` | 六轴角（度） |
| `CartesianPoint` | `MmDeg([x,y,z,rx,ry,rz])` | TCP（mm + 度） |
| | `MmDegWithRef(pose, ref_joints)` | TCP + 逆解参考关节（推荐） |

| 门面 API | 说明 |
|----------|------|
| `MovJ(target, speed, acceleration)` | 目标：`JointPoint` 或 `CartesianPoint` |
| `MovL(target, speed, acceleration)` | 目标：`CartesianPoint` 或 `JointPoint` |
| `Move([MoveInstruction.MovJ(...), ...])` | 多段路径 |

四组合路径示例（与 C++ `04_move` 一致）：

```python
from codroid import (
    CodroidClient,
    JointPoint,
    CartesianPoint,
    MoveInstruction,
    InitConsoleUtf8,
)

InitConsoleUtf8()

path = [
    MoveInstruction.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=40, acc=100),
    MoveInstruction.MovJ(CartesianPoint.MmDeg([...]), speed=40, acc=100),
    MoveInstruction.MovL(CartesianPoint.MmDeg([...]), speed=150, acc=500),
    MoveInstruction.MovL(JointPoint.Degrees([0, 0, 0, 0, 0, 0]), speed=150, acc=500),
]
robot.Move(path)
```

打包规则：`jp` 优先；仅 `cp` 时若未提供 `rj`，JSON 中带默认 `[20,20,20,20,20,20]`（度）。

**Breaking（2.1.0）**：请勿再用 `MovePoint(jp=...)` 作业务入口；`move_j` / `move_l` 已废弃，见 [CHANGELOG.md](CHANGELOG.md)。

## Windows 控制台 UTF-8

在 `cmd`（非 Windows Terminal）下运行含中文的示例时，请在入口调用：

```python
from codroid import InitConsoleUtf8

InitConsoleUtf8()
```

所有 `examples/*.py` 已在 `if __name__ == "__main__"` 首行调用。自建 CLI 请同样处理；`chcp 65001` 不能替代此调用。

## 教程：进阶连接方式

`CodroidClient` 适用于后台持续接收、请求 `id` 配对、publish 分发：

```python
from codroid import CodroidClient, InitConsoleUtf8

InitConsoleUtf8()

with CodroidClient(host="192.168.1.136") as robot:
    robot.to_remote()
    robot.switch_on()
```

## 示例

```bash
PYTHONPATH=src python examples/08_move.py --robot 192.168.8.136
PYTHONPATH=src python examples/codroid_test.py motion
PYTHONPATH=src python examples/codroid_test.py s20
```

寄存器与 S20 运动常量见仓库根目录 `AGENTS.md` §5.1。

## 常见问题

### `ModuleNotFoundError: No module named codroid`

未在当前 Python 环境安装 SDK。重新执行：

```bash
pip install codroid-robot-sdk
```

### 脚本无响应或连接失败

- 检查控制器 IP 与端口配置。
- 检查本机与控制器网络连通性、防火墙策略。
- 确认控制器处于可远程控制状态。

## 项目架构

```text
src/codroid/
├── __init__.py                     # 公开 API 导出（含 __version__）
├── __about__.py                    # 版本号
├── Codroid.py                      # CodroidSession / CodroidControlInterface
├── client.py                       # CodroidClient
├── async_tcp_client.py             # JsonStreamClient、TransportClient
├── define.py                       # DTO / 常量（JointPoint、MoveInstruction 等）
├── robot_motion.py                 # pack_move_point / pack_instruction
├── types.py                        # DTO 再导出
├── exceptions.py                   # 异常定义
├── publish.py                      # 发布订阅模型
├── trajectory.py                   # 轨迹生成
├── cri_realtime_packet_parser.py   # CRI UDP 数据解析
├── cri_realtime_dispatcher.py      # CRI 实时控制下发
├── console.py                      # PrintBanner
├── console_utf8.py                 # InitConsoleUtf8
└── utils.py                        # 通用工具
```

## 许可证

本项目采用 [MIT](https://spdx.org/licenses/MIT.html) 许可证。
