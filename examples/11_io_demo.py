#!/usr/bin/env python3
"""
数字量 / 模拟量：set_do、get_di、set_ao、get_ai、批量 get_io_values。

用法:
  PYTHONPATH=src python examples/11_io_demo.py
  PYTHONPATH=src python examples/11_io_demo.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Digital / analog IO demo")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("11 — I/O demo", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            print("DO 10 = 1 / set_do(10, 1)")
            robot.set_do(10, 1)

            di_val = robot.get_di(0)
            print(f"DI 0 = {di_val}")

            print("AO 2 = 4.44 / set_ao")
            robot.set_ao(2, 4.44)

            ai_val = robot.get_ai(1)
            print(f"AI 1 = {ai_val}")

            res = robot.get_io_values(
                [
                    {"type": "DI", "port": 0},
                    {"type": "AI", "port": 1},
                ]
            )
            print(f"批量读取 / batch: {res.db}")
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
