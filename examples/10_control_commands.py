#!/usr/bin/env python3
"""
示例 10 — 系统控制（清错 / 使能 / 仿真 / 拖拽）

【目的】
  演示与运动无关但常用的机器人状态切换 API。

【前置条件】
  - 远程模式；拖拽前通常需已使能

【涉及协议】
  - Robot/clearSystemError、switchOn、switchOff
  - Robot/toSimulation、startDrag、stopDrag

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/10_control_commands.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/10_control_commands.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\10_control_commands.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/10_control_commands.py --robot 192.168.8.136

【注意】
  - 仿真模式与真机行为不同，现场谨慎切换
  - 拖拽结束后建议 stop_drag 再 switch_off
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, CodroidError, InitConsoleUtf8, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="clear_system_error, switch, simulation, drag")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--drag-seconds", type=float, default=5.0, help="拖拽保持时间（秒）")
    args = p.parse_args(argv)

    PrintBanner("10 — Control commands", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()
            try:
                print("清错 / clear_system_error")
                robot.ClearSystemError()
                time.sleep(0.5)

                print("上使能 / switch_on")
                robot.SwitchOn()
                time.sleep(1)

                print("仿真模式 / to_simulation")
                robot.ToSimulation()

                print("拖拽开始 / start_drag")
                robot.StartDrag()
                time.sleep(args.drag_seconds)

                print("拖拽结束 / stop_drag")
                robot.StopDrag()

                print("下使能 / switch_off")
                robot.SwitchOff()
            except CodroidError as e:
                # 控制器 err 字段映射为 CodroidError
                print(f"CodroidError: {e}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
