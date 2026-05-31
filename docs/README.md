# CodroidPython SDK 手册

**版本:** 2.1.5 | **包名:** `codroid-robot-sdk` | **Python:** 3.7+

---

## 目录

| # | 章节 | 说明 |
|---|------|------|
| 1 | [快速上手](01-quick-start.md) | 安装、连接并运行第一个程序 |
| 2 | [核心概念](02-concepts.md) | 生命周期、TCP 模型、单位约定、异常处理 |
| 3 | [CodroidSession / CodroidClient API](03-api-reference-codroidclient.md) | 主客户端完整 API 参考 |
| 4 | [运动 API](04-api-reference-motion.md) | JointPoint、CartesianPoint、MoveInstruction、MotionWaitOptions |
| 5 | [数据类型与枚举](05-api-reference-types.md) | CommonResponse、CriRealTimeData、RobotFrame、GlobalVariable |
| 6 | [CRI 实时数据与控制](06-api-reference-cri.md) | CriRealtimeDispatcher、TrajectoryGenerator、PacketParser |
| 7 | [IO 与寄存器](07-api-reference-io-register.md) | DI/DO/AI/AO 操作、寄存器读写 |
| 8 | [辅助工具](08-api-reference-utilities.md) | 发布/订阅、全局变量、运动学、ConsoleUtf8 |

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.7+（CPython / PyPy，3.7 ~ 3.14） |
| 操作系统 | Linux、Windows、macOS |
| 运行时依赖 | 无（可选 `colorama` 用于彩色终端输出） |

### 安装

```bash
pip install codroid-robot-sdk
```

可选彩色终端输出：

```bash
pip install "codroid-robot-sdk[color]"
```

### 验证安装

```bash
python3 -c "import codroid; print(codroid.__version__)"
```

---

## API 命名约定

所有公共方法使用 **PascalCase**（与 C# / C++ SDK 一致）。

```python
# 正确
robot.ConnectRemoteAndSwitchOn()
di = robot.GetDi(0)

# 错误 — snake_case 已在 2.1.1 移除
robot.connect_remote_and_switch_on()  # 不存在
```

---

## 单位约定

| 层级 | 线性 | 角度 |
|------|------|------|
| SDK 公共 API | **mm** | **deg（度）** |
| TCP JSON 协议 | **mm** | **deg** |
| CRI UDP 二进制（线路层） | **m** | **rad（弧度）** |
| `CriRealTimeData`（已解析） | **mm** | **deg** |

`CriRealtimePacketParser.parse()` 和 `CriRealtimeDispatcher`（`convert_to_si=True`）会自动处理 m 与 mm、rad 与 deg 的换算。
