#!/usr/bin/env python3
"""
点动：设置倍率、关节点动、后台 jog 心跳、停止。

用法:
  PYTHONPATH=src python examples/06_jog_mode.py
  PYTHONPATH=src python examples/06_jog_mode.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys
import threading
import time

from codroid import CodroidControlInterface, JogMode, PrintBanner


def start_heartbeat(robot: CodroidControlInterface, stop_event: threading.Event, interval: float = 0.4) -> None:
    while not stop_event.is_set():
        try:
            robot.jog_heartbeat()
            time.sleep(interval)
        except Exception:
            break


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Jog mode + heartbeat thread")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--duration", type=float, default=2.0, help="点动持续时间（秒）")
    args = p.parse_args(argv)

    PrintBanner("06 — Jog mode", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            robot.switch_on()
            robot.set_manual_move_rate(50)

            stop_heartbeat = threading.Event()
            heartbeat_thread = threading.Thread(
                target=start_heartbeat,
                args=(robot, stop_heartbeat),
                daemon=True,
            )

            print("关节 1 点动（示例速度）/ Jog joint 1...")
            robot.start_jog(mode=JogMode.JOINT, index=1, speed=-0.5)
            heartbeat_thread.start()
            time.sleep(args.duration)

            print("停止点动 / Stop jog")
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=2.0)
            robot.stop_jog()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
