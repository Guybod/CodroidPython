# Codroid 机器人 Python SDK

面向 Codroid 控制器的 Python 软件开发工具包：支持 TCP 指令、实时数据（CRI）与轨迹规划等能力，API 与 C# 官方 SDK 及契约文档对齐。

**日常使用请直接通过 PyPI 安装**；本仓库中的源码与 `AGENTS.md` 等文档主要供查阅实现细节、协议约定与二次开发参考。

[![PyPI - Version](https://img.shields.io/pypi/v/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)

---

## 目录

- [安装与使用（推荐）](#安装与使用推荐)
- [进阶：CodroidClient](#进阶codroidclient)
- [源码与开发](#源码与开发)
- [测试与检查](#测试与检查)
- [Hatch 工作流](#hatch-工作流)
- [项目结构](#项目结构)
- [许可证](#许可证)

## 安装与使用（推荐）

### 安装

需要 **Python 3.7+**（建议 3.8+）。在任意虚拟环境或系统环境中执行：

```bash
pip install codroid-robot-sdk
```

可选：彩色终端横幅依赖：

```bash
pip install "codroid-robot-sdk[color]"
```

安装完成后**不必克隆本仓库**，在任意目录编写脚本即可 `import codroid`。

### 确认安装成功

```bash
python3 -c "import codroid; print(codroid.__version__)"
```

若系统只有 `python` 命令，将上面命令中的 `python3` 换成 `python` 即可。

### 最小示例

将 `192.168.1.136` 换成你的**控制器 IP**。以下使用默认会话类 `CodroidControlInterface`（同步 TCP，适合常见「发请求—收响应」用法）：

```python
from codroid import CodroidControlInterface

robot_ip = "192.168.1.136"

with CodroidControlInterface(host=robot_ip) as robot:
    robot.to_remote()
    robot.switch_on()
    # 在此处继续调用其他 API，例如 IO、运动、工程等
```

保存为例如 `demo.py` 后执行：`python3 demo.py`（需网络可达机器人且控制器已按文档就绪）。

## 进阶：CodroidClient

当需要 **后台持续收 TCP、按整数 `id` 配对响应、Publish 按 `ty` 分发**（与 C# `FutureTcpClient` 语义一致）时，请使用 `CodroidClient`：

```python
from codroid import CodroidClient

with CodroidClient(host="192.168.1.136") as robot:
    robot.to_remote()
    robot.switch_on()
```

更多场景可参考 PyPI 包内说明或本仓库 `examples/` 目录下的脚本（需自行克隆仓库后运行）。

## 源码与开发

以下适用于需要**浏览源码、跑仓库内示例或参与构建**的开发者；终端客户仅用 pip 安装时可忽略。

### 环境（可选）

使用 **Hatch** 可统一虚拟环境与构建命令：

```bash
pipx install hatch
# 或: pip install hatch
```

### 克隆仓库（仅供阅读与示例）

```bash
git clone <你的仓库地址>
cd CodroidPython
```

### 不安装包、直接跑源码（可选）

在仓库根目录（含 `src/` 的一层）：

```bash
PYTHONPATH=src python3 -c "import codroid; print(codroid.__version__)"
PYTHONPATH=src python3 examples/codroid_test.py --help
```

或先 `export PYTHONPATH=/你的路径/CodroidPython/src`，再运行 `examples/` 下脚本。要点：`PYTHONPATH` 必须包含 **`.../CodroidPython/src`**，以便解析到 `src/codroid/`。

### 用 Hatch 跑仓库内示例

```bash
hatch run python examples/01_basic_usage.py
```

## 测试与检查

- 正式 **pytest** 套件仍在完善中；连机验证可使用本仓库 `examples/`。
- 本地冒烟（已 `pip install` 时无需 `PYTHONPATH`）：

  ```bash
  python3 -c "import codroid; print(codroid.__version__)"
  ```

- 类型检查（克隆仓库并安装 Hatch 后）：

  ```bash
  hatch run types:check
  ```

## Hatch 工作流

### 进入开发 Shell

```bash
hatch shell
python examples/01_basic_usage.py
```

### 构建发行物

```bash
hatch build
```

产物位于 `dist/`（wheel 与 sdist）。

### 文档站点（MkDocs）

```bash
hatch run docs:serve
```

## 项目结构

源码模块与 C# `CodroidSDK/*.cs` **同名一一对应**（Python 侧为 snake_case + `.py`）。演进路线见仓库根目录 **`plan.md`**。

```text
src/codroid/
├── __init__.py                     # 公开 API 导出（含 __version__）
├── __about__.py                    # 版本号（Hatch 动态读取）
├── Codroid.py                      # CodroidSession；CodroidControlInterface 别名
├── client.py                       # CodroidClient
├── async_tcp_client.py             # JsonStreamClient、TransportClient / FutureTcpClient
├── define.py                       # DTO / 常量（对齐 Define.cs）
├── types.py                        # DTO 再导出
├── exceptions.py
├── utils.py
├── console.py
├── publish.py
├── trajectory.py
├── cri_realtime_packet_parser.py   # 308 字节 CRI；CriStreamHandler
└── cri_realtime_dispatcher.py      # 64 字节实时控制 UDP
```

计划在 2.0 中从 `Codroid.py` 拆出、与 C# 对齐的模块（可能尚未落盘）：`global_variables.py`、`io.py`、`register.py`、`robot_kinematics.py`、`robot_motion.py`。

其他重要路径：

- **`examples/`**：示例脚本（需克隆仓库）。
- **`pyproject.toml`**：Hatch / 构建配置。
- **契约与算法**：`AGENTS.md`、`SDK_API_AND_DESIGN.md`、`PROTOCOL_LINE_BY_LINE.md`、`TRAJECTORY_ALGORITHM.md`。

## 许可证

本项目以 [MIT](https://spdx.org/licenses/MIT.html) 许可证分发。
