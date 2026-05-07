#!/usr/bin/env python3
"""
movJ 与 ``get_cri_data``（``cri_cache``）轮询等待运动结束（调试时可开 ``debug=True``）。

用法:
  PYTHONPATH=src python examples/08_move.py
  PYTHONPATH=src python examples/08_move.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, MovePoint, PrintBanner


def wait_idle(robot: CodroidControlInterface, poll_s: float = 0.05) -> None:
    while True:
        data = robot.get_cri_data()
        if data is not None and not data.status.is_moving:
            return
        if data is not None:
            print(f"运动中 / moving, joint_pos={data.joint_pos}")
        else:
            print("等待实时数据 / waiting for status...")
        time.sleep(poll_s)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="moveJ + poll get_cri_data")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机 IP（状态推送）")
    p.add_argument("--udp-port", type=int, default=18888, help="本机 UDP 端口")
    p.add_argument("--debug", action="store_true", help="打印 JSON 请求/响应")
    args = p.parse_args(argv)

    PrintBanner("08 — Move (movJ + poll)", subtitle=args.robot)

    try:
        with CodroidControlInterface(
            host=args.robot,
            local_ip=args.local_ip,
            udp_port=args.udp_port,
        ) as robot:
            robot.debug = args.debug
            robot.enter_remote_mode_via_auto()
            robot.switch_on()
            robot._start_cri_receiver()
            robot.start_cri_data_push(ip=args.local_ip, port=args.udp_port)

            p1_j = MovePoint(jp=[0, 0, 90, 0, 90, 0])
            p2_j = MovePoint(jp=[0, 0, 0, 0, 0, 0])

            robot.move_j(p2_j, speed=10, acc=40)
            wait_idle(robot)
            robot.move_j(p1_j, speed=10, acc=40)
            wait_idle(robot)

            PrintBanner("08 — Motion finished", subtitle="movJ 完成")
            time.sleep(1)
    except KeyboardInterrupt:
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
