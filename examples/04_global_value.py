#!/usr/bin/env python3
"""
增量保存全局变量（整数、字符串、列表、字典）。

用法:
  PYTHONPATH=src python examples/04_global_value.py
  PYTHONPATH=src python examples/04_global_value.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, GlobalVariable, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Save global variables")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("04 — Global variables", subtitle=args.robot)

    vars_to_save = {
        "v_int": GlobalVariable(value=1024, note="整数示例"),
        "v_str": GlobalVariable(value="Codroid", note="字符串示例"),
        "v_list": GlobalVariable(value=[1.1, 2.2, 3.3], note="数组示例"),
        "v_map": GlobalVariable(
            value={"power": 100, "status": "on"},
            note="Map 示例",
        ),
    }

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            print("增量保存全局变量 / Saving globals...")
            res = robot.save_global_vars(vars_to_save)
            if res.is_success:
                print("保存成功 / Saved")
            else:
                print(f"失败 / Failed: {res.err}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
