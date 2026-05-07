#!/usr/bin/env python3
"""
MoveTo：Home、关节规划（Type 4）、直线规划（Type 5），配合 move_to_heartbeat 后台线程。

用法:
  PYTHONPATH=src python examples/07_move_to.py
  PYTHONPATH=src python examples/07_move_to.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys
import threading
import time

from codroid import CodroidControlInterface, MoveToType, MoveTarget, PrintBanner


def heartbeat_worker(robot: CodroidControlInterface, stop_event: threading.Event) -> None:
    print("[心跳] 启动 / heartbeat start (~400ms)")
    while not stop_event.is_set():
        try:
            robot.move_to_heartbeat()
            time.sleep(0.4)
        except Exception as e:
            print(f"[心跳] 异常 / error: {e}")
            break
    print("[心跳] 已停止 / heartbeat stop")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="moveTo + heartbeat")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("07 — MoveTo", subtitle=args.robot)

    stop_event = threading.Event()

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            robot.switch_on()

            PrintBanner("Scene 1 — HOME", subtitle="MoveToType.HOME")
            robot.move_to(MoveToType.HOME)
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            time.sleep(3)
            stop_event.set()
            t.join(timeout=2.0)

            PrintBanner("Scene 2 — JOINT (Type 4)", subtitle="关节规划")
            target_joints = MoveTarget(jp=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            robot.move_to(MoveToType.JOINT, target=target_joints)
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            time.sleep(5)
            stop_event.set()
            t.join(timeout=2.0)

            PrintBanner("Scene 3 — LINEAR (Type 5)", subtitle="直线规划")
            target_pose = MoveTarget(cp=[350.0, 100.0, 400.0, 180.0, 0.0, 90.0])
            robot.move_to(MoveToType.LINEAR, target=target_pose)
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            time.sleep(4)
            stop_event.set()
            t.join(timeout=2.0)

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
    raise SystemExit(main(sys.argv[1:]))
