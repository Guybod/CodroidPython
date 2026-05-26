#!/usr/bin/env python3
"""
示例 05 — 末端 RS485（初始化 / 清空 / 写 / 按长度读）

【目的】
  演示通过 TCP 转发的末端 485 收发，示例帧为 Modbus 读保持寄存器（仅作格式参考）。

【前置条件】
  - 末端 485 硬件与从站已连接
  - 波特率与从站一致（示例 115200 8N1）

【涉及协议】
  - TCP Robot/rs485Init、rs485Flush、rs485Write、rs485Read

【运行】
  PYTHONPATH=src python examples/05_rs485.py --robot <IP>

【注意】
  - timeout 单位为毫秒（示例 1000）
  - 无响应时 read 可能失败或 db 为空，属正常现象
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, InitConsoleUtf8, RS485BaudRate, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="RS485 init / flush / write / read")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("05 — RS485", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()

            # 配置末端 485 参数（枚举与 C# RS485BaudRate 对齐）
            print("初始化 115200 N 8 1 / RS485 init")
            robot.rs485_init(baudrate=RS485BaudRate.B115200)
            robot.rs485_flush()

            # 示例 Modbus RTU：站号 1，功能码 03，读 2 个寄存器（CRC 已含在帧内）
            cmd = b"\x01\x03\x00\x00\x00\x02\xC4\x0B"
            print(f"发送 / TX: {cmd.hex()}")
            robot.rs485_write(cmd)

            print("读取响应（7 字节，1s 超时）/ Read...")
            res = robot.rs485_read(length=7, timeout=1000)
            if res.is_success and res.db:
                received = bytes(res.db)
                print(f"收到 / RX (hex): {received.hex()}")
            else:
                print("未收到或失败 / No data or read failed")
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
