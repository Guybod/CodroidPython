#!/usr/bin/env python3
"""
控制类指令：清错、上使能、仿真、拖拽（示例时长）、下使能。

用法:
  PYTHONPATH=src python examples/10_control_commands.py
  PYTHONPATH=src python examples/10_control_commands.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, CodroidError, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="clear_system_error, switch, simulation, drag")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--drag-seconds", type=float, default=5.0, help="拖拽保持时间（秒）")
    args = p.parse_args(argv)

    PrintBanner("10 — Control commands", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            try:
                print("清错 / clear_system_error")
                robot.clear_system_error()
                time.sleep(0.5)

                print("上使能 / switch_on")
                robot.switch_on()
                time.sleep(1)

                print("仿真模式 / to_simulation")
                robot.to_simulation()

                print("拖拽开始 / start_drag")
                robot.start_drag()
                time.sleep(args.drag_seconds)

                print("拖拽结束 / stop_drag")
                robot.stop_drag()

                print("下使能 / switch_off")
                robot.switch_off()
            except CodroidError as e:
                print(f"CodroidError: {e}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
