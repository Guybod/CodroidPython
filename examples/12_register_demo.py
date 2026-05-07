#!/usr/bin/env python3
"""
寄存器与扩展数组：读写寄存器、配置扩展数组类型、删除扩展数组项。

用法:
  PYTHONPATH=src python examples/12_register_demo.py
  PYTHONPATH=src python examples/12_register_demo.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, ExtendArrayType, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Register + extend array")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("12 — Register demo", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            print("寄存器 49300 = 123.45 / set_register_value")
            robot.set_register_value(49300, 123.45)
            val = robot.get_register(49300)
            print(f"读回 / read: {val}")

            print("扩展数组 999 → Float32 / set_extend_array_type")
            robot.set_extend_array_type(999, ExtendArrayType.FLOAT32)

            print("重置扩展数组 999 / remove_extend_array")
            robot.remove_extend_array(999)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
