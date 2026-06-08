# Codroid Python SDK 版本说明

## 2.1.7 — 补齐 CposToCpos + 跨语言对齐修复

### 新增

- **`CposToCpos` / `CposToCposPose`**：坐标系转换（协议 `Robot/cpostocpos`），将 TCP 位姿从坐标系1+工具1 转换到坐标系2+工具2，与 C# 对齐

### Bug Fixes

- **修复 `blend`/`relativeBlend` 互斥逻辑**：同时传入时只发 `blend`
- **修复 publish handler 阻塞接收线程**：改为 `threading.Thread(daemon=True)` 后台调用

### 改进

- **新增接收缓冲区溢出保护**：512KB 缓冲区上限，超限后清空并断开
- **新增 publish 订阅去重**：同一 topic 只发送一次订阅帧

---

## 2.1.5 — 隐患修复

### Bug Fixes

- **修复 `RunStep` 发错指令**：发送 `"project/run"` 改为 `"project/runStep"`，之前会导致单步调试变成完整运行
- **修复 `CriData` 返回可变引用**：改为返回深拷贝，与 C# 行为一致，避免 UDP 线程更新时主线程读到不一致数据
- **修复 `_id_counter` 竞态**：加 `threading.Lock` 保护，避免多线程并发发指令时 ID 冲突
- **修复 `GetDi`/`GetDo` 缺少端口校验**：与 `SetDo`/`SetAo` 一致，传入非法端口时抛出 `CodroidError`
- **修复 `_dispatch_publish` 静默吞异常**：publish handler 的异常现在会输出到日志

### 改进

- **`StartCriControl` 参数校验**：新增 `filter_type`（0-3）、`duration`（1-16 且整除 1000）、`start_buffer`（1-100）校验
- **便捷运动方法补 `relative_blend` 参数**：`MovJ`、`MovL`、`MovC`、`MovCircle` 及其 `*Sync` 变体、`MotionPath` 构建方法全部支持 `relative_blend`，与 C# 对齐
- **`CposToApos` 默认参考关节改为当前关节角度**：`rj=None` 时优先使用 `CriData.JointPosition`，CRI 未启动时兜底 `[20,20,20,20,20,20]`，与 C# 行为一致
- **`CriStreamHandler.parse_packet()` 舍位方式修正**：从银行家舍位改为四舍五入（AwayFromZero），与 C# `Math.Round` 行为一致

---

## 2.1.4 — blend 参数改为可选 + 欧拉角判定修复

### Bug Fixes

- **修复阻塞运动欧拉角到达判定**：`180°` 和 `-180°` 是同一姿态，但之前直接算差值 `|180-(-180)|=360°`，导致判定永远不通过。现在归一化到 `[-180, 180]` 后再比较

### Breaking Changes

- **`blend` 参数类型变更**：`float`（默认 `0.0`）→ `Optional[float]`（默认 `None`）
  - 之前不传 `blend` 会发送 `0.0` 到控制器，现在不传表示**无过渡**
  - 如需保持旧行为，请显式传入 `blend=0`
- **`relative_blend` 参数类型变更**：`int`（默认 `0`）→ `Optional[float]`（默认 `None`）
  - 之前不传会发送 `0` 到控制器，现在不传表示**不使用相对平滑**
  - 如需保持旧行为，请显式传入 `relative_blend=0`
- **`blend` 与 `relative_blend` 互斥**：同时传入时 `relative_blend` 无效
- **`coor`/`tool` 语义明确**：`None` 表示指令中不包含该字段

### 涉及方法

- `MoveInstruction` 工厂方法：`MovJ`、`MovL`、`MovC`、`MovCircle`
- `MotionPath`：`MovJ`、`MovL`、`MovC`
- `CodroidClient`：`MovJ`、`MovL`、`MovC`、`MovCircle` 及其 `*Sync` 变体

---

## 2.1.2 — 阻塞式运动 API / RunScript 完整参数 / StopMoveTo

### Added

- **阻塞式运动 API**（对齐 C# `*Sync` 方法）：
  - `MoveSync`、`MovJSync`、`MovLSync`、`MovCSync`、`MovCircleSync`
  - `MotionWaitOptions`：可配置超时、轮询间隔、CRI 过期判定、稳定采样数、关节/笛卡尔容差
  - 内部 CRI 新鲜度追踪（`_last_cri_received_utc`）
- **`RunScript` 完整参数**：新增 `sub_threads`、`sub_programs`、`interrupts` 可选字典参数（对齐 C# `RunScript(main, subThreads, subPrograms, interrupts, vars)`）
- **`StopMoveTo()`**：发送 `type=-1` 停止 MoveTo 运动
- `MoveToType.STOP = -1` 枚举值
- 更新示例：`08_move.py` 增加 Sync 阻塞运动演示；`02_run_script.py` 增加子线程/子程序/中断演示；`07_move_to.py` 增加 StopMoveTo 演示

## 2.1.1 — 机器人设置 API（协议 19.x）

### Added

- `robot_settings.py`：`RobotFrame`、`RobotPayloadFrame`、`RobotParameters`
- `SetCollisionSensitivity`、`GetRobotParameters`
- 仅改默认编号：`SetDefaultPayloadId`、`SetDefaultToolId`、`SetDefaultUserCoordinateId`
- 先读后改：`SetToolFrame`、`SetPayloadFrame`、`SetUserCoordinateFrame`
- 整表下发：`SaveToolFrames`、`SavePayloadFrames`、`SaveUserCoordinateFrames`
- 示例：`examples/14_robot_parameters.py`；`codroid_test.py robotparam`；`examples/08_move.py` 四组合 + MovC

### Changed / Breaking

- 运动门面仅保留 C# 同名：`MovJ`、`MovL`、`MovC`、`MovCircle`、`Move`、`MoveTo`、`MoveToHeartbeat`
- 移除 `move_j` / `move_l` / `move_c` / `move_circle` / `execute_path` / `move` / `move_to` / `move_to_heartbeat`
- `MoveTarget` 更名为 `MoveToTarget`（与 C# 一致）；`MotionPath.mov_*` 更名为 `MovJ` / `MovL` / `MovC`
- **`CodroidSession` / `CodroidClient` 全部公开方法改为 PascalCase**（`Connect`、`SwitchOn`、`GetDi`、`StartCriDataPush` 等）；移除文件末尾历史 snake_case 别名
- `get_cri_data()` 改为属性 **`CriData`**（对齐 C#）
- `close` / `disconnect` 合并为 **`Disconnect`**
- `CriRealtimeDispatcher.send_command` → **`SendCommand`**，`send_trajectory` → **`SendTrajectory`**
- 移除 `subscribe_publish_topic` 别名

## 2.1.0 — 运动 API 类型化（Breaking）

与 C++ SDK v2.1.1 / `update1.md` 对齐。

### Added

- `JointPoint`、`CartesianPoint`、`MoveInstruction` 及工厂（`Degrees`、`MmDeg`、`MmDegWithRef`、`MovJ`/`MovL`/…）
- `pack_move_point` / `pack_instruction`（`jp` 优先；笛卡尔缺省 `rj=[20,…,20]`）
- 门面 API：`MovJ`、`MovL`、`MovC`、`MovCircle`、`Move`、`MoveTo`、`MoveToHeartbeat`
- `MoveToTarget.Joint` / `MoveToTarget.Cartesian`
- `InitConsoleUtf8()`（Windows 控制台 UTF-8）

### Changed

- `MovePoint.to_dict()` 经统一打包逻辑，仅 `cp` 时 JSON 会带默认 `rj`
- 示例与 `codroid_test` 运动段改用类型化 API

### Deprecated

- 旧版 snake_case 运动方法（2.1.1 起已删除，见 2.1.1 Breaking）
- 直接 `MovePoint(jp=…)` 作业务目标（请改用 `JointPoint` / `CartesianPoint`）

### Migration

1. 程序入口首行：`InitConsoleUtf8()`
2. 关节目标 → `JointPoint.Degrees([...])` + `MovJ` / `MoveInstruction.MovJ`
3. TCP 目标 → `CartesianPoint.MmDeg` 或 `MmDegWithRef(pose, cri_joint)`
4. 多段路径 → `Move([MoveInstruction.MovJ(...), ...])`
