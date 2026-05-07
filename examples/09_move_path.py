#!/usr/bin/env python3
"""
连续路径：``MotionPath`` 链式 movJ / movL，一次性 ``execute_path``。

用法:
  PYTHONPATH=src python examples/09_move_path.py
  PYTHONPATH=src python examples/09_move_path.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, MotionPath, MovePoint, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="MotionPath execute_path")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("09 — Move path", subtitle=args.robot)

    path = (
        MotionPath()
        .mov_j(MovePoint(jp=[0, 0, 90, 0, 90, 0]), speed=60, acc=150)
        .mov_l(
            MovePoint(cp=[494, 191, 444, -180, 0, -90]),
            speed=500,
            acc=1500,
            blend=30,
        )
        .mov_l(
            MovePoint(cp=[294, 191, 444, -180, 0, -90]),
            speed=500,
            acc=1500,
            blend=30,
        )
        .mov_l(
            MovePoint(cp=[494, 391, 444, -180, 0, -90]),
            speed=500,
            acc=1500,
            blend=30,
        )
        .mov_l(
            MovePoint(cp=[494, 191, 644, -180, 0, -90]),
            speed=500,
            acc=1500,
            blend=30,
        )
        .mov_j(MovePoint(jp=[0, 0, 90, 0, 90, 0]), speed=60, acc=150, blend=0)
    )

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            robot.switch_on()
            print("发送连续路径 / Sending path...")
            res = robot.execute_path(path)
            if res.is_success:
                print("路径已送达 / Path accepted")
            else:
                print(f"失败 / Failed: {res.err}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
