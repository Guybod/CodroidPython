# 力控 API 测试说明

本目录用于测试 Python SDK 的力控接口。测试脚本默认只读取状态；任何会进入力控或驱动机器人位移的测试都需要显式选择。

## 前置条件

- 机器人与电脑网络连通，默认 TCP 端口按 SDK 配置连接。
- 机器人安装并配置六维力传感器。
- 机器人处于安全空间内，末端周围无人和障碍物。
- 进入力控前 TCP 速度接近 0，机器人无其他运动占用。
- 做恒力或接触检测前，确认力方向、阈值、最大行程适合现场工装。

## 运行方式

在 `CodroidPython` 目录执行：

```bash
PYTHONPATH=src python3 examples/force_test/force_api_test.py --robot 192.168.1.136 --case state
```

如果已安装本地包，也可以不设置 `PYTHONPATH`：

```bash
python3 examples/force_test/force_api_test.py --robot 192.168.1.136 --case state
```

## 测试项

| case | 说明 | 是否进入力控 | 是否可能产生位移 |
|---|---|---:|---:|
| `state` | 读取 `GetForceState()` 和所有单字段 getter | 否 | 否 |
| `calibration` | 执行 `ZeroForceCalibration()` | 否 | 否 |
| `safety-config` | 设置过力保护和力数据健康监控参数 | 否 | 否 |
| `compliance` | 初始化柔顺原语，启动并停止力控 | 是 | 可能因外力/重力补偿产生轻微位移 |
| `constant-force` | 初始化 Z 向恒力，启动、在线调参、停止 | 是 | 可能 |
| `contact-detection` | 启动接触检测原语 | 是 | 是，必须加 `--allow-motion` |
| `all-safe` | 依次执行 `state`、`calibration`、`safety-config`、`compliance` | 部分 | 可能轻微 |

## 常用命令

只读状态：

```bash
PYTHONPATH=src python3 examples/force_test/force_api_test.py --robot 192.168.1.136 --case state
```

零力校准：

```bash
PYTHONPATH=src python3 examples/force_test/force_api_test.py --robot 192.168.1.136 --case calibration --calibration-ms 1000
```

柔顺启停测试：

```bash
PYTHONPATH=src python3 examples/force_test/force_api_test.py --robot 192.168.1.136 --case compliance --hold 5
```

Z 向恒力与在线调参测试：

```bash
PYTHONPATH=src python3 examples/force_test/force_api_test.py --robot 192.168.1.136 --case constant-force --force-z 2 --tune-force-z 5 --hold 5
```

接触检测测试。该测试会沿方向进给，必须明确允许运动：

```bash
PYTHONPATH=src python3 examples/force_test/force_api_test.py \
  --robot 192.168.1.136 \
  --case contact-detection \
  --allow-motion \
  --contact-direction 0 0 -1 0 0 0 \
  --feed-velocity 0.002 \
  --contact-threshold 3 \
  --max-travel 0.01 \
  --contact-timeout-ms 5000
```

## 验收点

- `state` 能打印完整状态和每个字段的单独返回值。
- `calibration` 返回 `success=true`，无外部接触时 `extWrenchAfterTare` 接近 0。
- `compliance` / `constant-force` 能成功进入力控，`enabled` 变为 `True`，停止后 `enabled` 变为 `False`。
- `TuneForceParams(..., ramp_time=...)` 能正常返回。
- `SetOverforceProtection()`、`SetForceDataHealth()` 返回成功。
- `contact-detection` 能通过 `isContact` 或超时/行程结果体现检测状态。

## 注意事项

- 当前 SDK 的 `InitForceControl()` 固定导纳算法，不能传 `algo` 参数。
- 恒力原语不配置 `stiffness`，只配置 `desiredForce`、`damping`、`mass` 等字段。
- `ZeroForceCalibration(timeout_ms=...)` 中的 `timeout_ms` 是 SDK 本地等待响应超时，不是控制器 API 参数。
- 如测试中断，脚本会尝试 `StopForceControl()`、`ToAuto()`、`ToManual()`、`SwitchOff()` 做收尾。
