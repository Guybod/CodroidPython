#!/usr/bin/env python3
"""
示例 08 — 类型化运动 API（MovJ / MovL / Move 四组合）

【目的】
  对齐 C++ ``examples_client/04_move.cpp``：
  - 单点 MovJ（关节）
  - 多段路径：movJ+jp → movJ+cp → movL+cp → movL+jp

【前置条件】
  - 已使能；CRI 推送正常（用于等待停稳、MmDegWithRef）
  - S20 等机型请核对笛卡尔点位是否可达（常量来自 AGENTS.md §5.1）

【涉及协议】
  - Robot/move：每段含 type、speed、acc、targetPoint（经 pack_move_point 打包）
  - CRI/StartDataPush：status.is_moving 判断停稳

【运行】
  PYTHONPATH=src python examples/08_move.py --robot <IP> --local-ip <本机IP>

【注意】
  - movJ 到 TCP 时建议 ``MmDegWithRef(pose, cri.joint_pos)`` 减少逆解跳解
  - 仅 cp 且无 rj 时，SDK 自动填默认 rj=[20,…,20]（度）
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import (
    CartesianPoint,
    CodroidControlInterface,
    InitConsoleUtf8,
    JointPoint,
    MoveInstruction,
    PrintBanner,
)


def wait_idle(robot: CodroidControlInterface, poll_s: float = 0.05) -> None:
    """轮询 CRI 直到 is_moving 为 False；无 CRI 时仅 sleep 提示。"""
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
    p = argparse.ArgumentParser(description="MovJ/MovL/Move four-combination demo")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机 IP（状态推送）")
    p.add_argument("--udp-port", type=int, default=18888, help="本机 UDP 端口")
    p.add_argument("--debug", action="store_true", help="打印 JSON 请求/响应")
    args = p.parse_args(argv)

    PrintBanner("08 — Move (typed API)", subtitle=args.robot)

    joint_home = JointPoint.Degrees([0, 0, 0, 0, 0, 0])
    joint_pose = JointPoint.Degrees([0, 0, 90, 0, 90, 0])
    # AGENTS.md §5.1 S20 movL 第一点（mm + 度）
    cart_pose = CartesianPoint.MmDeg(
        [927.511, 214.489, 486.524, 179.999, 0.0, -89.999],
    )

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

            # ---------- 单点 movJ（关节）----------
            print("单点 movJ → 关节 home")
            robot.MovJ(joint_home, speed=10, acceleration=40)
            wait_idle(robot)

            print("单点 movJ → 关节 pose")
            robot.MovJ(joint_pose, speed=10, acceleration=40)
            wait_idle(robot)

            # movJ 到 TCP：用当前关节作逆解参考
            cri = robot.cri_cache
            if cri and len(cri.joint_pos) >= 6:
                cart_with_ref = CartesianPoint.MmDegWithRef(
                    cart_pose.cp,
                    list(cri.joint_pos),
                )
            else:
                cart_with_ref = cart_pose
                print("警告: 无 CRI 关节快照，movJ→TCP 使用 MmDeg（无参考关节）")

            # ---------- 四组合路径，一次 Robot/move ----------
            path = [
                MoveInstruction.MovJ(joint_pose, speed=40, acc=100),       # movJ + jp
                MoveInstruction.MovJ(cart_with_ref, speed=40, acc=100),    # movJ + cp (+rj)
                MoveInstruction.MovL(cart_pose, speed=150, acc=500),       # movL + cp
                MoveInstruction.MovL(joint_home, speed=150, acc=500),      # movL + jp
            ]
            print("Move 路径: movJ+jp → movJ+cp → movL+cp → movL+jp")
            robot.Move(path)
            wait_idle(robot)

            PrintBanner("08 — Motion finished", subtitle="四组合路径完成")
            time.sleep(1)
    except KeyboardInterrupt:
        return 130

    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
