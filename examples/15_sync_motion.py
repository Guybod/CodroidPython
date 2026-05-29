#!/usr/bin/env python3
"""
示例 15 — 阻塞式运动 API（*Sync）

【目的】
  演示 ``MovJSync`` / ``MovLSync`` / ``MovCSync`` / ``MoveSync`` 阻塞式运动。
  发送运动指令后自动轮询 CRI 数据，直到机器人稳定到达目标，无需手动 ``wait_idle``。

【前置条件】
  - 已使能；CRI 推送已启动（``StartListenUdp``）
  - 目标点位在可达范围内

【运行】
  PYTHONPATH=src python examples/15_sync_motion.py --robot <IP> --local-ip <本机IP>

【注意】
  - ``*Sync`` 方法内部会阻塞当前线程直到到达目标或超时
  - 可通过 ``MotionWaitOptions`` 调整超时、容差等参数
  - 若发生碰撞、急停或报警，会抛出 ``CodroidError``
"""
from __future__ import annotations

import argparse
import sys

from codroid import (
    CartesianPoint,
    CodroidControlInterface,
    InitConsoleUtf8,
    JointPoint,
    MotionWaitOptions,
    MoveInstruction,
    PrintBanner,
)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Sync (blocking) motion demo")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机 IP（CRI）")
    p.add_argument("--udp-port", type=int, default=18888, help="本机 UDP 端口")
    p.add_argument("--debug", action="store_true", help="打印 JSON")
    args = p.parse_args(argv)

    PrintBanner("15 — Sync Motion", subtitle=args.robot)

    joint_home = JointPoint.Degrees([0, 0, 0, 0, 0, 0])
    joint_pose = JointPoint.Degrees([0, 0, 90, 0, 90, 0])
    cart_p1 = CartesianPoint.MmDeg([927.511, 214.489, 486.524, 179.999, 0.0, -89.999])

    try:
        with CodroidControlInterface(
            host=args.robot,
            local_ip=args.local_ip,
            udp_port=args.udp_port,
        ) as robot:
            robot.debug = args.debug
            robot.EnterRemoteModeViaAuto()
            robot.SwitchOn()

            # 必须启动 CRI 数据推送，*Sync 方法依赖 CRI 判断到达
            robot.StartListenUdp()
            print("等待 CRI 数据... / Waiting for CRI data...")
            robot.WaitForCriData(timeout=5.0)
            print("CRI 数据已就绪 / CRI data ready\n")

            # -----------------------------------------------------------------
            # 1. MovJSync — 阻塞式关节运动
            # -----------------------------------------------------------------
            PrintBanner("[1] MovJSync + JointPoint")
            robot.MovJSync(joint_pose, speed=40, acceleration=100)
            print("  ✓ 到达目标\n")

            # -----------------------------------------------------------------
            # 2. MovLSync — 阻塞式直线运动
            # -----------------------------------------------------------------
            PrintBanner("[2] MovLSync + CartesianPoint")
            robot.MovLSync(cart_p1, speed=150, acceleration=500)
            print("  ✓ 到达目标\n")

            # -----------------------------------------------------------------
            # 3. MovJSync + CartesianPoint — 关节插补到 TCP
            # -----------------------------------------------------------------
            PrintBanner("[3] MovJSync + CartesianPoint")
            cart_ref = CartesianPoint.MmDegWithRef(
                [927.516, 214.489, 900.0, 180.0, 0.0, -89.999],
                list(robot.CriData.joint_position) if robot.CriData else [0] * 6,
            )
            robot.MovJSync(cart_ref, speed=40, acceleration=100)
            print("  ✓ 到达目标\n")

            # -----------------------------------------------------------------
            # 4. MovCSync — 阻塞式圆弧运动
            # -----------------------------------------------------------------
            PrintBanner("[4] MovCSync")
            middle = CartesianPoint.MmDeg([927.515, 27.23, 738.722, -180.0, 0.0, -89.999])
            end = CartesianPoint.MmDeg([927.511, 214.489, 486.524, 179.999, 0.0, -89.999])
            robot.MovCSync(middle, end, speed=120, acceleration=400)
            print("  ✓ 到达目标\n")

            # -----------------------------------------------------------------
            # 5. MoveSync — 阻塞式多段路径
            # -----------------------------------------------------------------
            PrintBanner("[5] MoveSync (多段路径)")
            path = [
                MoveInstruction.MovJ(joint_pose, speed=40, acc=100),
                MoveInstruction.MovL(cart_p1, speed=150, acc=500, blend=25),
                MoveInstruction.MovL(joint_home, speed=150, acc=500, blend=25),
            ]
            robot.MoveSync(path)
            print("  ✓ 全部到达\n")

            # -----------------------------------------------------------------
            # 6. 自定义 MotionWaitOptions
            # -----------------------------------------------------------------
            PrintBanner("[6] 自定义 MotionWaitOptions")
            opts = MotionWaitOptions(
                timeout=30.0,           # 30 秒超时
                joint_tolerance_deg=0.5, # 关节容差放宽到 0.5 度
                settled_samples=2,       # 连续 2 次稳定即可
            )
            robot.MovJSync(joint_pose, speed=40, acceleration=100, wait=opts)
            print("  ✓ 到达目标（自定义容差）\n")

            # 回 Home
            robot.MovJSync(joint_home, speed=40, acceleration=100)

            PrintBanner("15 — 完成", subtitle="阻塞式运动演示结束")

    except KeyboardInterrupt:
        return 130

    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
