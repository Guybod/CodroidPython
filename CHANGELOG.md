# Changelog

## 2.1.0 — 运动 API 类型化（Breaking）

与 C++ SDK v2.1.1 / `update1.md` 对齐。

### Added

- `JointPoint`、`CartesianPoint`、`MoveInstruction` 及工厂（`Degrees`、`MmDeg`、`MmDegWithRef`、`MovJ`/`MovL`/…）
- `pack_move_point` / `pack_instruction`（`jp` 优先；笛卡尔缺省 `rj=[20,…,20]`）
- 门面 API：`MovJ`、`MovL`、`MovC`、`MovCircle`、`Move`、`MoveTo`、`MoveToHeartbeat`
- `MoveTarget.Joint` / `MoveTarget.Cartesian`（别名 `MoveToTarget`）
- `InitConsoleUtf8()`（Windows 控制台 UTF-8）

### Changed

- `MovePoint.to_dict()` 经统一打包逻辑，仅 `cp` 时 JSON 会带默认 `rj`
- 示例与 `codroid_test` 运动段改用类型化 API

### Deprecated

- `move_j` / `move_l` / `move_c` / `move_circle` / `execute_path`（请改用 PascalCase 门面）
- 直接 `MovePoint(jp=…)` 作业务目标（请改用 `JointPoint` / `CartesianPoint`）

### Migration

1. 程序入口首行：`InitConsoleUtf8()`
2. 关节目标 → `JointPoint.Degrees([...])` + `MovJ` / `MoveInstruction.MovJ`
3. TCP 目标 → `CartesianPoint.MmDeg` 或 `MmDegWithRef(pose, cri_joint)`
4. 多段路径 → `Move([MoveInstruction.MovJ(...), ...])`
