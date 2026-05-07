#!/usr/bin/env python3
"""
基础示例：连接、远程、上使能、关节运动，并打印 CRI 缓存中的关节角。

用法:
  PYTHONPATH=src python examples/01_basic_usage.py
  PYTHONPATH=src python examples/01_basic_usage.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, MovePoint, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Basic connect, moveJ, CRI cache")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机 IP（CRI 推送）")
    p.add_argument(
        "--udp-port",
        type=int,
        default=18888,
        help="本机 UDP 端口（建议 10000–65534）",
    )
    args = p.parse_args(argv)

    PrintBanner("01 — Basic usage", subtitle=f"{args.robot}  CRI → {args.local_ip}:{args.udp_port}")

    with CodroidControlInterface(
        host=args.robot,
        local_ip=args.local_ip,
        udp_port=args.udp_port,
    ) as robot:
        robot.enter_remote_mode_via_auto()
        robot.switch_on()
        robot._start_cri_receiver()
        robot.start_cri_data_push(ip=args.local_ip, port=args.udp_port)

        try:
            p1 = MovePoint(jp=[0, 0, 90, 0, 90, 0])
            p2 = MovePoint(jp=[0, 0, 0, 0, 0, 0])
            for _ in range(3):
                robot.move_j(p1, 60, 120)
                robot.move_j(p2, 60, 120)

            PrintBanner("CRI cache loop", subtitle="Ctrl+C 退出")
            while True:
                data = robot.cri_cache
                if data:
                    print(f"关节角 / joint_pos: {data.joint_pos}")
                    print(f"运动中 / is_moving: {data.status.is_moving}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("已中断 / Interrupted", file=sys.stderr)
            return 130
        finally:
            robot.stop_cri_data_push(ip=args.local_ip, port=args.udp_port)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
