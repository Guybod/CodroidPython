# Codroid 多语言 SDK 对齐修改方案（update1）

> **基准**：C++ 仓库 `CodroidCPP`，自提交 **`6c89d45`** 起至 **`24af47c`**（含）的全部运动 API 相关改动。  
> **目标读者**：Python SDK、C# SDK 维护者。  
> **原则**：控制器 TCP/JSON **协议不变**；变的是各语言 **如何表达 jp/cp** 以及 **如何拼装路径段**。

**C++ 参考提交**：

| 提交 | 说明 |
|------|------|
| `6c89d45` | 引入 `JointPoint` / `CartesianPoint`，废除裸数组作运动目标 |
| `5f664d7` | 路径段静态工厂、`Move()`、`MovePoint`/`MoveInstruction` 文档与注释 |
| `24af47c` | 示例与 README；**三语言均须**提供并调用 `InitConsoleUtf8`（见 §5.5） |

**不在本方案范围**（C++ 独有，另案处理）：`build_mingw.bat` 修复（`619d581`、`7954fa1`）。

---

## 1. 背景与动机

### 1.1 问题

原 API 用 `double[]` / `List<double>` 同时表示：

- 六轴关节角（度）
- TCP 位姿 `[x,y,z,rx,ry,rz]`（mm + 度）

编译器/运行时 **无法区分**，易出现：

- 把 TCP 传给 `MovJ` 却未填 `rj` → 逆解跳解
- 把关节角传给 `MovL` → 控制器行为异常

### 1.2 C++ 解决思路（Python/C# 应对齐）

| 层级 | 类型 | 职责 |
|------|------|------|
| 业务点位 | `JointPoint` / `CartesianPoint` | 声明「这是关节还是 TCP」 |
| 协议路点 | `MovePoint` | 对应 JSON `targetPoint` / `middlePoint` 的 `{jp}` 或 `{cp,rj}` |
| 路径段 | `MoveInstruction` | 一段 `Robot/move`：`type` + 速度 + 目标（+ 圆弧中间点） |
| 门面 | `MovJ` / `MovL` / `Move` | 对外 API |

**协议层 JSON 形状未改**，仍见 `CodroidController::packInstruction`（C++ `src/CodroidController.cpp`）。

---

## 2. 协议打包规则（三语言必须一致）

下发 `Robot/move` 时，每段 `targetPoint` 规则：

1. 若 `jp` 非空 → 只发 `jp`（**优先**，即使有 `cp` 也忽略 `cp`）
2. 否则若 `cp` 非空 → 发 `cp`；若 `rj` 为空 → 发默认 **`[20,20,20,20,20,20]`**（度）
3. `movC` / `movCircle` 的 `middlePoint`：发 `cp`；`rj` 为空时同样默认 20

**禁止**业务层同时填 `jp` 与 `cp` 到同一路点；工厂方法应保证只填一侧。

---

## 3. 新增类型定义（建议命名）

### 3.1 C++（已实现，作对照）

```text
JointPoint          { jp: vector<double> }           // 6 轴，度
CartesianPoint      { cp: vector<double>, rj: vector<double> }  // cp 必填；rj 可选
MovePoint           { jp, cp, rj, ep }              // 协议 DTO
MoveInstruction     { type, speed, acc, blend, targetPoint, middlePoint, ... }
```

工厂（C++）：

| 类型 | 工厂 |
|------|------|
| `JointPoint` | `Degrees(joints_deg)` |
| `CartesianPoint` | `MmDeg(pose_mm_deg)`、`MmDegWithRef(pose, ref_joints_deg)` |
| `MovePoint` | `Joint(JointPoint)`、`Cartesian(CartesianPoint)` |
| `MoveInstruction` | `MovJ(jp\|cp, speed, acc)`、`MovL(cp\|jp, ...)`、`MovC`、`MovCircle` |

### 3.2 C# 建议（对齐 `CodroidSDK` 现有命名风格）

| C++ | C# 建议类型 / 成员 | 说明 |
|-----|-------------------|------|
| `JointPoint` | `JointPoint` 或复用现有 `MovePoint` 子类/记录 | 仅含 `double[] Jp` 或 `JointAngles` |
| `CartesianPoint` | `CartesianPoint` | `double[] Cp`，`double[] Rj` 可选 |
| `MovePoint` | 保持现有 `MovePoint` | `Jp` / `Cp` / `Rj` 字段；提供 `FromJoint` / `FromCartesian` |
| `MoveInstruction` | 保持现有 `MoveInstruction` | 增加 **静态工厂** 见 §5.3 |
| `MoveToTarget` | 保持 | `Joint(JointPoint)` / `Cartesian(CartesianPoint)`，勿再收裸数组 |

### 3.3 Python 建议（snake_case 模块 + PascalCase 公开 API 按 AGENTS.md）

| C++ | Python 建议 |
|-----|-------------|
| `JointPoint` | `@dataclass class JointPoint: jp: list[float]` + `JointPoint.degrees(...)` |
| `CartesianPoint` | `CartesianPoint` + `mm_deg(...)` / `mm_deg_with_ref(pose, ref_joints)` |
| `MovePoint` | `MovePoint` + `from_joint` / `from_cartesian` |
| `MoveInstruction` | `MoveInstruction` + 类方法 `mov_j` / `mov_l` / `mov_c` / `mov_circle` |
| `CodroidClient` | `MovJ` / `MovL` / `Move` 签名改用上述类型 |

公开函数名仍按 **AGENTS.md §4.1**：`MovJ`、`MovL`、`Move`（PascalCase），内部模块可用 snake_case。

---

## 4. 破坏性变更（Breaking Changes）

### 4.1 删除或标记废弃的签名

以下 **不再提供**「仅 `double[]` / `List<double>` 作目标」的便捷重载（可保留 `[Obsolete]` 包装一层，内部转工厂）：

| 原用法（废弃） | 新用法 |
|----------------|--------|
| `MovJ(double[] jp, ...)` | `MovJ(JointPoint, ...)` |
| `MovL(double[] cp, ...)` | `MovL(CartesianPoint, ...)` |
| `MovePoint.Joint(double[])` 若存在裸数组版 | `MovePoint.FromJoint(JointPoint)` |
| 路径列表里手写 `target.jp`/`target.cp` 混用 | `MoveInstruction.MovJ(cp)` 等工厂 |

### 4.2 新增能力（原 C++ 做不到或易错）

| 能力 | 说明 |
|------|------|
| `MovJ(CartesianPoint)` | 关节运动到 TCP（控制器逆解） |
| `MovL(JointPoint)` | 直线运动到关节目标 |
| 路径段同样四种组合 | 见 §5.3 |
| `Move(path)` 显式命名 | 与 C# `Move` 一致；Python 可 `move()` 或 `Move()` 二选一+别名 |

### 4.3 非破坏性

- `Robot/move`、`Robot/moveTo` 的 JSON 字段名、单位（mm/deg）不变
- CRI、IO、寄存器、机器人参数（v2.1.0）不变
- `packInstruction` 默认 `rj` 逻辑不变

---

## 5. API 修改清单（按模块）

### 5.1 单点运动 — `CodroidClient` / `CodroidClient`

| API | 参数 | 运动类型 | 协议 target |
|-----|------|----------|-------------|
| `MovJ(JointPoint, speed, acc, id?)` | 关节 | movJ | `jp` |
| `MovJ(CartesianPoint, speed, acc, id?)` | TCP | movJ | `cp` + `rj` |
| `MovL(CartesianPoint, speed, acc, coor?, tool?, id?)` | TCP | movL | `cp` + `rj` |
| `MovL(JointPoint, speed, acc, coor?, tool?, id?)` | 关节 | movL | `jp` |
| `MovC(CartesianPoint middle, CartesianPoint target, ...)` | TCP | movC | `middlePoint`/`targetPoint` 均为 `cp` |
| `MovCircle(CartesianPoint middle, CartesianPoint target, circleNum, ...)` | TCP | movCircle | 同上 |

**可选保留**（低层/兼容）：

- `MovJ(MovePoint, ...)` / `MovL(MovePoint, ...)`：供已构建协议 DTO 的高级用户
- `movJ(MoveInstruction)` / `move(List<MoveInstruction>)`：底层控制器 API 保持

### 5.2 `CartesianPoint` 与 `MmDegWithRef`

| 工厂 | 行为 |
|------|------|
| `MmDeg(pose)` | 只设 `cp`；打包时 `rj` 空 → 默认 `[20,20,20,20,20,20]` |
| `MmDegWithRef(pose, ref_joints)` | 设 `cp` + `rj`；**强烈建议** movJ→TCP、movL→TCP 且在意姿态解时使用 |

**推荐写法**（与 C++ `examples_client/04_move.cpp` 一致）：

```text
ref = client.GetRobotRealtimeState().JointPosition   # C#
ref = robot.get_robot_realtime_state().joint_position  # Python
target = CartesianPoint.MmDegWithRef(pose, ref)
client.MovJ(target, speed, acc)
```

### 5.3 多段路径 — `Move` / `move`

**C++ 门面**：

```cpp
CommandResult Move(const std::vector<ClientMoveInstruction>& path, int id = 1);
// MovePath 为别名
```

**每段用静态工厂构建**（勿手写 `type` + 裸 `MovePoint`）：

```cpp
// C++ 示例
path = {
    ClientMoveInstruction::MovJ(joint_p1, 40, 100),   // movJ + jp
    ClientMoveInstruction::MovJ(cart_p1, 40, 100),    // movJ + cp
    ClientMoveInstruction::MovL(cart_p2, 150, 500),   // movL + cp
    ClientMoveInstruction::MovL(joint_p2, 150, 500),  // movL + jp
    ClientMoveInstruction::MovC(mid, end, 120, 400),
};
robot.Move(path, id);
```

**C# 建议**（`RobotMotion.cs` 或等价处）：

```csharp
var path = new List<MoveInstruction> {
    MoveInstruction.MovJ(jointP1, speed: 40, acc: 100),
    MoveInstruction.MovJ(cartP1, speed: 40, acc: 100),
    MoveInstruction.MovL(cartP2, speed: 150, acc: 500),
    MoveInstruction.MovL(jointP2, speed: 150, acc: 500),
    MoveInstruction.MovC(mid, end, speed: 120, acc: 400),
};
await client.Move(path);
```

**Python 建议**：

```python
path = [
    MoveInstruction.mov_j(joint_p1, speed=40, acceleration=100),
    MoveInstruction.mov_j(cart_p1, speed=40, acceleration=100),
    MoveInstruction.mov_l(cart_p2, speed=150, acceleration=500),
    MoveInstruction.mov_l(joint_p2, speed=150, acceleration=500),
    MoveInstruction.mov_c(mid, end, speed=120, acceleration=400),
]
robot.Move(path)
```

### 5.4 `MoveTo` / `MoveToTarget`（RunTo，非 `Robot/move`）

C++ 已改为仅通过类型化目标构造：

```cpp
MoveToTarget::Joint(JointPoint)
MoveToTarget::Cartesian(CartesianPoint)
MoveToParams(MoveToType::Joint | Line, target)
// 仍需 moveToHeartbeat() 每 500ms
```

Python/C# 若原先 `MoveToTarget.Joint(double[])`，改为接收 `JointPoint` / `CartesianPoint`，内部写入 `jp`/`cp` 字段。

### 5.5 Windows 控制台 UTF-8（三语言强制）

在 Ubuntu 编写、Windows `cmd` 运行示例时，中文日志/注释输出易因控制台默认 **GBK（936）** 与程序 **UTF-8** 不一致而乱码。**C++ / C# / Python 必须统一处理**，避免集成商误以为 SDK 异常。

| 项 | 约定 |
|----|------|
| 公共 API 名 | **`InitConsoleUtf8`**（与 C++ 一致；Python 模块内可用 `init_console_utf8` 别名导出为 `InitConsoleUtf8`） |
| 调用时机 | **所有官方示例 / CLI** 的 `main` / `Program.Main` **第一行**调用一次 |
| 非 Windows | **空操作**（no-op），不报错 |
| 文档 | README 写明：示例已内置；自建程序建议在入口同样调用 |
| 可选补充 | 批处理 `chcp 65001`、Windows Terminal — **不能替代** SDK 调用，仅作环境说明 |

#### C++（已实现，作对照）

- 头文件：`include/Codroid/console_utf8.hpp`
- 实现：`SetConsoleOutputCP(CP_UTF8)` + `SetConsoleCP(CP_UTF8)`（仅 `_WIN32`）
- 状态：`examples/`、`examples_client/` 已调用（`05_rs485` 空 main 可省略）

#### C#（必须新增）

新建 `ConsoleUtf8.cs`（或并入 `Define.cs`），命名空间与 `CodroidClient` 一致：

```csharp
using System.Runtime.InteropServices;
using System.Text;

namespace Codroid; // 与现有 SDK 命名空间对齐

public static class ConsoleUtf8
{
    public static void InitConsoleUtf8()
    {
        if (!OperatingSystem.IsWindows())
            return;

        Console.OutputEncoding = Encoding.UTF8;
        Console.InputEncoding = Encoding.UTF8;
        SetConsoleOutputCP(65001);
        SetConsoleCP(65001);
    }

    const uint CP_UTF8 = 65001;

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool SetConsoleOutputCP(uint wCodePageID);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool SetConsoleCP(uint wCodePageID);
}
```

- `CodroidTest/Program.cs`、`CodroidCRITest/Program.cs` 及所有示例：**首行** `ConsoleUtf8.InitConsoleUtf8();`
- 若已有 `Main`，不得遗漏；新建示例模板默认包含

#### Python（必须新增）

新建 `src/codroid/console_utf8.py`（并在 `__init__.py` 导出 `InitConsoleUtf8`）：

```python
import sys

def init_console_utf8() -> None:
    """Windows: 控制台与 stdout/stderr 统一 UTF-8；其它平台 no-op。"""
    if sys.platform != "win32":
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    try:
        import ctypes
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        k32.SetConsoleOutputCP(65001)
        k32.SetConsoleCP(65001)
    except OSError:
        pass

# 与 C# / C++ 公开名对齐（AGENTS.md PascalCase）
InitConsoleUtf8 = init_console_utf8
```

- `examples/codroid_test.py`、`examples/codroid_cri_test.py` 等：**`if __name__ == "__main__"` 块内第一行** `InitConsoleUtf8()`
- 不要求库内每次 `Connect` 自动调用（避免污染 GUI/服务进程）；**示例与文档强制**，集成商自建 CLI 照抄

#### 验收（§7.4）

- [ ] Windows `cmd`（非 Terminal）运行示例，打印中文无乱码
- [ ] Linux 调用 `InitConsoleUtf8()` 无副作用

---

## 6. 文件级实施建议

### 6.1 C#（`CodroidSDK`）

| 序号 | 文件/区域 | 动作 |
|------|-----------|------|
| 1 | `Define.cs` 或 `RobotMotion.cs` | 新增 `JointPoint`、`CartesianPoint` 记录/类 |
| 2 | `MovePoint` | 增加 `FromJoint` / `FromCartesian`；文档注明 jp/cp 互斥 |
| 3 | `MoveInstruction` | 增加静态方法 `MovJ(JointPoint)`、`MovJ(CartesianPoint)`、`MovL(...)`、`MovC`、`MovCircle` |
| 4 | `RobotMotion.cs` / `CodroidClient` | 更新 `MovJ`/`MovL` 重载；新增 `Move(List<MoveInstruction>)` 若尚未与 C++ 对齐 |
| 5 | `MoveToTarget` | 工厂改为 `Joint(JointPoint)` / `Cartesian(CartesianPoint)` |
| 6 | 打包逻辑 | 对照 C++ `packInstruction`：**jp 优先**，cp 时默认 rj |
| 7 | `CodroidTest` / 示例 | 更新 §5.1 运动常量调用；增加 movJ+cp、movL+jp 路径段用例 |
| 8 | `ConsoleUtf8.cs` | 实现 `InitConsoleUtf8`；**所有** `Program.Main` 首行调用 |
| 9 | 文档 | README / RELEASE_NOTES 同步 `UPDATE_ANNOUNCEMENT.md` 要点 |

**兼容策略（可选）**：

```csharp
[Obsolete("Use MovJ(JointPoint.Degrees(jp), ...)")]
public Task MovJ(double[] jp, ...) => MovJ(JointPoint.Degrees(jp), ...);
```

### 6.2 Python（`codroid-python` 建议结构）

| 序号 | 模块 | 动作 |
|------|------|------|
| 1 | `types.py` / `models.py` | `@dataclass` `JointPoint`、`CartesianPoint` |
| 2 | `types.py` | `MovePoint.from_joint` / `from_cartesian` |
| 3 | `motion.py` | `MoveInstruction` 类方法 `mov_j` / `mov_l` / `mov_c` / `mov_circle` |
| 4 | `client.py` | `MovJ`/`MovL`/`MovC`/`Move` 签名；移除或废弃裸 `list` 目标 |
| 5 | `motion.py` | `pack_instruction()` 与 C++ 行为一致（jp 优先、默认 rj） |
| 6 | `examples/codroid_test.py` | 对齐 C++ `04_move` 四组合路径 |
| 7 | `console_utf8.py` | `InitConsoleUtf8`；**所有** 示例入口首行调用 |
| 8 | `tests/test_motion_pack.py` | 快照测试 JSON：jp/cp/rj 组合 |

**类型提示**：

```python
def MovJ(
    target: JointPoint | CartesianPoint,
    speed: float,
    acceleration: float,
    id: int = 1,
) -> CommandResult: ...
```

避免 `Union[list[float], JointPoint]` 以免再次混淆。

---

## 7. 验收标准（三语言一致）

### 7.1 单元 / 快照

- [ ] `MovJ(JointPoint)` → JSON `targetPoint.jp` 长度 6，无 `cp`
- [ ] `MovJ(CartesianPoint)` 无 rj → JSON `rj == [20,20,20,20,20,20]`
- [ ] `MovJ(CartesianPoint)` 带 rj → JSON `rj` 与输入一致
- [ ] `MovL(JointPoint)` → 仅 `jp`
- [ ] `Move` 两段：movJ+cp 后 movL+jp，控制器接受且运动合理

### 7.2 集成（S20 或现场机型）

- [ ] 与 C++ `examples_client/04_move` 同参数：movJ 三点关节、movL 三点 TCP、Move 路径含四组合
- [ ] movJ 到 TCP 时，对比 `MmDeg` vs `MmDegWithRef(ref=当前关节)` 是否减少跳解

### 7.3 文档

- [ ] README 运动章节含四组合表与 `MmDegWithRef` 说明
- [ ] CHANGELOG 标明 **Breaking**：裸数组目标已移除
- [ ] README 含「Windows 控制台 UTF-8」：`InitConsoleUtf8` 用法（三语言同名）

### 7.4 控制台 UTF-8（强制）

- [ ] C# / Python 提供 `InitConsoleUtf8`，行为与 C++ `console_utf8.hpp` 对齐
- [ ] 官方示例 `Main` / `__main__` 首行已调用
- [ ] Windows `cmd` 下中文输出可读（见 §5.5）

---

## 8. 迁移指南（给集成商）

```text
0. 示例/CLI 入口首行 InitConsoleUtf8()（Windows 防中文乱码）
1. 全局搜索 MovJ( / MovL( / MovePoint. 构造
2. 关节目标 → JointPoint.Degrees([...])
3. TCP 目标 → CartesianPoint.MmDeg([...]) 或 MmDegWithRef(pose, cri_joint)
4. 多段路径 → 用 MoveInstruction.MovJ/MovL/... 工厂，最后 client.Move(path)
5. 不要同时给 MovePoint 填 jp 和 cp
```

---

## 9. C++ 参考索引

| 内容 | 路径 |
|------|------|
| 类型定义 | `include/Codroid/CodroidDefine.h` |
| 客户 API | `include/Codroid/client.hpp` |
| 打包 | `src/CodroidController.cpp` → `packInstruction` |
| 客户示例 | `examples_client/04_move.cpp` |
| 控制台 UTF-8 | `include/Codroid/console_utf8.hpp` |
| 用户公告 | `UPDATE_ANNOUNCEMENT.md` |
| 版本说明 | `RELEASE_NOTES.md` § v2.1.1 |

---

## 10. 版本建议

| 语言 | 建议版本号 | 说明 |
|------|------------|------|
| C++ | v2.1.1（文档已写，tag 待定） | 运动 API + `InitConsoleUtf8`（已有） |
| C# | 次 minor 升级并 **Breaking** | 运动 API + **新增** `InitConsoleUtf8` + 示例首行调用 |
| Python | 次 minor 升级并 **Breaking** | 运动 API + **新增** `InitConsoleUtf8` + 示例首行调用 |

三语言对齐完成后，在根目录 `AGENTS.md` §5.1 运动示例常量与 §6 CRI 流程保持不变，仅更新调用写法。

---

*文档版本：update1.1 | 生成自 C++ `6c89d45..24af47c`；含三语言强制 `InitConsoleUtf8`*
