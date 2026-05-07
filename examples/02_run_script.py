#!/usr/bin/env python3
"""
通过 ``project/runScript`` 下发 Lua 与共享变量。

用法:
  PYTHONPATH=src python examples/02_run_script.py
  PYTHONPATH=src python examples/02_run_script.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Run remote Lua script")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("02 — Run script", subtitle=args.robot)

    lua_code = "print('Hello Codroid')\nmovej([0,0,0,0,0,0])"
    vars_data = {"v1": 100, "v2": "test"}

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            print("发送脚本 / Sending script...")
            res = robot.run_script(lua_code, vars=vars_data)
            if res.is_success:
                print("脚本请求已发送 / Script request sent")
            else:
                print(f"失败 / Failed: {res.err}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
