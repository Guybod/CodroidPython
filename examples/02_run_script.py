#!/usr/bin/env python3
"""
示例 02 — 远程 Lua 脚本（project/runScript）

【目的】
  向控制器下发一段 Lua 源码及可选全局变量字典，由控制器解释执行。
  演示 RunScript 的完整参数：main_script、sub_threads、sub_programs、interrupts、vars。

【前置条件】
  - 已进入远程模式（本示例调用 enter_remote_mode_via_auto）
  - Lua 语法与控制器内置 API 匹配（如 movej 等）

【涉及协议】
  - TCP ``project/runScript``：db 含脚本文本与 vars

【运行】
  PYTHONPATH=src python examples/02_run_script.py --robot <IP>

【注意】
  - 示例脚本含 movej，会运动；请按现场修改 lua_code
  - vars 键名须符合控制器变量命名规则
  - sub_threads / sub_programs / interrupts 为可选的 Lua 代码字典
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, InitConsoleUtf8, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Run remote Lua script")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("02 — Run script", subtitle=args.robot)

    # 下发到控制器的 Lua 源码（字符串）；换行用 \\n
    lua_code = "print('Hello Codroid')\nmovej([0,0,0,0,0,0])"
    # 与脚本一起传入的共享变量（控制器侧可见）
    vars_data = {"v1": 100, "v2": "test"}

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()

            # --- 基本用法：主脚本 + 共享变量 ---
            print("发送脚本 / Sending script...")
            res = robot.RunScript(lua_code, vars=vars_data)
            if res.is_success:
                print("脚本请求已发送 / Script request sent")
            else:
                print(f"失败 / Failed: {res.err}", file=sys.stderr)
                return 1

            time.sleep(1)

            # --- 进阶用法：带子线程、子程序、中断 ---
            print("\n发送带子线程的脚本 / Sending script with sub_threads...")
            res2 = robot.RunScript(
                main_script="print('main thread')\nmovej([0,0,0,0,0,0])",
                sub_threads={
                    "thread1": "while true do print('sub thread 1') sleep(1) end",
                },
                sub_programs={
                    "myFunc": "function myFunc() print('sub program') end",
                },
                interrupts={
                    "int1": "function int1() print('interrupted') end",
                },
                vars={"speed": 50},
            )
            if res2.is_success:
                print("带子线程的脚本已发送 / Script with sub_threads sent")
            else:
                print(f"失败 / Failed: {res2.err}", file=sys.stderr)
                return 1

    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
