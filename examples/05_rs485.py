#!/usr/bin/env python3
"""
RS485：初始化、清空、写入、按长度超时读取（示例 Modbus 帧）。

用法:
  PYTHONPATH=src python examples/05_rs485.py
  PYTHONPATH=src python examples/05_rs485.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, RS485BaudRate, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="RS485 init / flush / write / read")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("05 — RS485", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            print("初始化 115200 N 8 1 / RS485 init")
            robot.rs485_init(baudrate=RS485BaudRate.B115200)
            robot.rs485_flush()

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
    raise SystemExit(main(sys.argv[1:]))
