#!/usr/bin/env python3
"""
示例 12 — 寄存器与扩展数组

【目的】
  演示单个寄存器读写、扩展数组类型声明与删除。

【前置条件】
  - 远程模式；地址与控制器内存映射一致（浮点示例 49300）

【涉及协议】
  - RegisterManager/setRegisterValue、getRegister
  - setExtendArrayType、removeExtendArray

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/12_register_demo.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/12_register_demo.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\12_register_demo.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/12_register_demo.py --robot 192.168.8.136

【注意】
  - 批量联调常量见 AGENTS.md §5.1 与 ``codroid_test.py register`` 子命令
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, ExtendArrayType, InitConsoleUtf8, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Register + extend array")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("12 — Register demo", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()

            # 浮点寄存器写读（地址因机型/配置而异）
            print("寄存器 49300 = 123.45 / set_register_value")
            robot.SetRegisterValue(49300, 123.45)
            val = robot.GetRegisterValue(49300)
            print(f"读回 / read: {val}")

            # 将逻辑扩展数组 ID 绑定为 Float32 元素类型
            print("扩展数组 999 → Float32 / set_extend_array_type")
            robot.SetExtendArrayType(999, ExtendArrayType.FLOAT32)

            print("重置扩展数组 999 / remove_extend_array")
            robot.RemoveExtendArray(999)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
