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
from codroid import CodroidControlInterface

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

## 教程：进阶连接方式

`CodroidClient` 适用于后台持续接收、请求 `id` 配对、publish 分发：

```python
from codroid import CodroidClient

with CodroidClient(host="192.168.1.136") as robot:
    robot.to_remote()
    robot.switch_on()
```

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
├── define.py                       # DTO / 常量
├── types.py                        # DTO 再导出
├── exceptions.py                   # 异常定义
├── publish.py                      # 发布订阅模型
├── trajectory.py                   # 轨迹生成
├── cri_realtime_packet_parser.py   # CRI UDP 数据解析
├── cri_realtime_dispatcher.py      # CRI 实时控制下发
├── console.py                      # 控制台输出
└── utils.py                        # 通用工具
```

## 许可证

本项目采用 [MIT](https://spdx.org/licenses/MIT.html) 许可证。
