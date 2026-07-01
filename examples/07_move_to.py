#!/usr/bin/env python3
"""
示例 07 — MoveTo（RunTo）与心跳 + StopMoveTo

【目的】
  演示 ``Robot/moveTo`` 三类场景：回 Home、关节规划、直线规划。
  MoveTo 与 Robot/move 不同：启动后须周期 ``MoveToHeartbeat``（约 500ms）。
  演示 ``StopMoveTo`` 中途停止 MoveTo 运动。

【前置条件】
  - 已使能；Home/安全位等已在示教器配置
  - 关节/直线目标在可达范围内

【涉及协议】
  - Robot/moveTo：db.type + 可选 db.target（jp 或 cp）
  - Robot/moveToHeartbeat
  - StopMoveTo：发送 type=-1 停止 MoveTo

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/07_move_to.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/07_move_to.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\07_move_to.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/07_move_to.py --robot 192.168.8.136

【注意】
  - 目标请用 ``MoveToTarget.Joint`` / ``MoveToTarget.Cartesian``，勿裸填数组
  - moveTo 的 target 不走 movL 的默认 rj 逻辑
"""
from __future__ import annotations

import argparse
import sys
import threading
import time

from codroid import (
    CartesianPoint,
    CodroidControlInterface,
    InitConsoleUtf8,
    JointPoint,
    MoveToTarget,
    MoveToType,
    PrintBanner,
)


def heartbeat_worker(robot: CodroidControlInterface, stop_event: threading.Event) -> None:
    """MoveTo 运动保持期间必须周期心跳，否则控制器中止运动。"""
    print("[心跳] 启动 / heartbeat start (~400ms)")
    while not stop_event.is_set():
        try:
            robot.MoveToHeartbeat()
            time.sleep(0.4)
        except Exception as e:
            print(f"[心跳] 异常 / error: {e}")
            break
    print("[心跳] 已停止 / heartbeat stop")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="MoveTo + heartbeat")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("07 — MoveTo", subtitle=args.robot)

    stop_event = threading.Event()

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()
            robot.SwitchOn()

            # --- 场景 1：预设 Home，无需 target ---
            PrintBanner("Scene 1 — HOME", subtitle="MoveToType.HOME")
            robot.MoveTo(MoveToType.HOME)
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            time.sleep(3)
            stop_event.set()
            t.join(timeout=2.0)

            # --- 场景 2：关节空间规划到指定六轴角 ---
            PrintBanner("Scene 2 — JOINT (Type 4)", subtitle="关节规划")
            target_joints = MoveToTarget.Joint(JointPoint.Degrees([0.0] * 6))
            robot.MoveTo(MoveToType.JOINT, target=target_joints)
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            time.sleep(5)
            stop_event.set()
            t.join(timeout=2.0)

            # --- 场景 3：笛卡尔直线到 TCP 位姿（mm + 度）---
            PrintBanner("Scene 3 — LINEAR (Type 5)", subtitle="直线规划")
            target_pose = MoveToTarget.Cartesian(
                CartesianPoint.MmDeg([350.0, 100.0, 400.0, 180.0, 0.0, 90.0]),
            )
            robot.MoveTo(MoveToType.LINEAR, target=target_pose)
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            time.sleep(4)
            stop_event.set()
            t.join(timeout=2.0)

            # --- 场景 4：StopMoveTo 中途停止 ---
            PrintBanner("Scene 4 — StopMoveTo", subtitle="启动后 2 秒停止")
            robot.MoveTo(MoveToType.LINEAR, target=target_pose)
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            time.sleep(2)
            print("  调用 StopMoveTo() / Calling StopMoveTo()...")
            robot.StopMoveTo()
            stop_event.set()
            t.join(timeout=2.0)
            print("  ✓ MoveTo 已停止")

        PrintBanner("07 — Done", subtitle="所有场景结束")
    except KeyboardInterrupt:
        stop_event.set()
        return 130
    except Exception as e:
        stop_event.set()
        print(f"错误 / Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
