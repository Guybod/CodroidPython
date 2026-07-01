#!/usr/bin/env python3
"""
示例 11 — 数字量 / 模拟量 IO

【目的】
  演示单点读写 DO/DI/AO/AI 及批量 ``get_io_values``。

【前置条件】
  - 远程模式；IO 端口号与硬件接线一致

【涉及协议】
  - IOManager/setDo、getDi、setAo、getAi、getIoValues（ty 见 PROTOCOL_LINE_BY_LINE.md）

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/11_io_demo.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/11_io_demo.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\11_io_demo.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/11_io_demo.py --robot 192.168.8.136

【注意】
  - set_do(10, 1) 会改变输出，确认端口未驱动关键安全设备
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, InitConsoleUtf8, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Digital / analog IO demo")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("11 — I/O demo", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()

            print("DO 10 = 1 / set_do(10, 1)")
            robot.SetDo(10, 1)

            di_val = robot.GetDi(0)
            print(f"DI 0 = {di_val}")

            print("AO 2 = 4.44 / set_ao")
            robot.SetAo(2, 4.44)

            ai_val = robot.GetAi(1)
            print(f"AI 1 = {ai_val}")

            # 批量读：每项为 {type, port}，type 为 DI/DO/AI/AO 字符串
            res = robot.GetIoValues(
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
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
