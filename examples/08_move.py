#!/usr/bin/env python3
"""
示例 08 — 类型化运动 API（MovJ / MovL / Move 四组合 + Sync 阻塞运动）

【目的】
  对齐 C++ ``examples_client/04_move.cpp``，演示「运动方式 × 点位类型」四种合法组合：

  | API / 工厂       | 参数类型         | 协议字段   |
  |------------------|------------------|------------|
  | MovJ             | JointPoint       | movJ + jp  |
  | MovJ             | CartesianPoint   | movJ + cp  |
  | MovL             | CartesianPoint   | movL + cp  |
  | MovL             | JointPoint       | movL + jp  |
  | MovC             | CartesianPoint×2 | movC 中间点+终点 |

  流程：先逐条单点下发（含 ``MovC``），再一次 ``Move(path)`` 下发多段（末段为圆弧），
  最后演示 ``MovJSync`` / ``MovLSync`` 阻塞式运动。

【前置条件】
  - 已使能；CRI 推送正常（movJ→TCP 建议 ``MmDegWithRef``）
  - S20 等机型请核对笛卡尔点位（常量来自 AGENTS.md §5.1）

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/08_move.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/08_move.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\08_move.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/08_move.py --robot 192.168.8.136 --local-ip 192.168.8.150

【注意】
  - ``MovJ(CartesianPoint)``：关节插补到 TCP，控制器逆解；有 CRI 时用当前关节作 ``rj``
  - ``MovL(JointPoint)``：直线到关节目标（非 TCP 直线），协议仍带 ``jp``
  - 仅 ``cp`` 且无 ``rj`` 时，打包默认 ``rj=[20,…,20]``（度）
  - ``MovC`` 仅接受两个 ``CartesianPoint``（中间点、终点），与 C++ ``04_move.cpp`` 圆弧常量一致
  - ``*Sync`` 方法需先启动 CRI 推送（``StartListenUdp``），发送后自动等待到达
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from codroid import (
    CartesianPoint,
    CodroidControlInterface,
    CriRealTimeData,
    InitConsoleUtf8,
    JointPoint,
    MoveInstruction,
    MotionWaitOptions,
    PrintBanner,
)


def wait_idle(robot: CodroidControlInterface, poll_s: float = 0.05) -> None:
    """轮询 CRI 直到 is_moving 为 False。"""
    while True:
        data = robot.CriData
        if data is not None and not data.status.is_moving:
            return
        if data is not None:
            print(f"  运动中 joint_pos={data.joint_pos}")
        else:
            print("  等待 CRI / waiting for status...")
        time.sleep(poll_s)


def cartesian_with_cri_ref(
    robot: CodroidControlInterface,
    pose_mm_deg: list[float],
    label: str,
) -> CartesianPoint:
    """
    有 CRI 时用 ``MmDegWithRef``，减少 movJ/movL 到 TCP 时的逆解跳解。
  无 CRI 时退回 ``MmDeg`` 并打印警告。
    """
    cri: Optional[CriRealTimeData] = robot.CriData
    if cri is not None and len(cri.joint_pos) >= 6:
        return CartesianPoint.MmDegWithRef(pose_mm_deg, list(cri.joint_pos))
    print(f"  警告 [{label}]: 无 CRI 关节快照，使用 MmDeg（无 rj）")
    return CartesianPoint.MmDeg(pose_mm_deg)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="MovJ/MovL four-combination demo")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机 IP（CRI）")
    p.add_argument("--udp-port", type=int, default=18888, help="本机 UDP 端口")
    p.add_argument("--debug", action="store_true", help="打印 JSON")
    args = p.parse_args(argv)

    PrintBanner("08 — Move (typed API)", subtitle=args.robot)

    # AGENTS.md §5.1 S20 常用测试点（度 / mm+度）
    joint_home = JointPoint.Degrees([0, 0, 0, 0, 0, 0])
    joint_pose = JointPoint.Degrees([0, 0, 90, 0, 90, 0])
    cart_p1 = [927.51,214.488,486.526,179.999,0,-89.999]
    cart_p2 = [927.516, 214.489, 900.0, 180.0, 0.0, -89.999]
    # C++ 04_move.cpp 圆弧：中间点 → 终点 line_p1
    circle_middle = CartesianPoint.MmDeg(
        [927.515, 27.23, 738.722, -180.0, 0.0, -89.999]
    )
    circle_end = CartesianPoint.MmDeg(cart_p1)

    try:
        with CodroidControlInterface(
            host=args.robot,
            local_ip=args.local_ip,
            udp_port=args.udp_port,
        ) as robot:
            robot.debug = args.debug
            robot.EnterRemoteModeViaAuto()
            robot.SwitchOn()
            robot._start_cri_receiver()
            robot.StartCriDataPush(ip=args.local_ip, port=args.udp_port)
            time.sleep(0.3)

            # -----------------------------------------------------------------
            # 一、单条指令（每种组合各调用一次 MovJ / MovL）
            # -----------------------------------------------------------------

            print("\n[1] MovJ + JointPoint  (movJ + jp)")
            robot.MovJ(joint_pose, speed=40, acceleration=100)
            wait_idle(robot)

            print("\n[2] MovL + CartesianPoint  (movL + cp)")
            line_p1 = cartesian_with_cri_ref(robot, cart_p1, "MovL(cp)")
            robot.MovL(line_p1, speed=150, acceleration=500)
            wait_idle(robot)

            print("\n[3] MovJ + CartesianPoint  (movJ + cp，控制器逆解到 TCP)")
            line_p2 = cartesian_with_cri_ref(robot, cart_p2, "MovJ(cp)")
            robot.MovJ(line_p2, speed=40, acceleration=100)
            wait_idle(robot)

            print("\n[4] MovL + JointPoint  (movL + jp，直线到关节角而非 TCP 直线)")
            robot.MovL(joint_home, speed=150, acceleration=500)
            wait_idle(robot)

            print("\n[5] MovC + CartesianPoint×2  (movC，中间点 → 终点)")
            robot.MovC(circle_middle, circle_end, speed=120, acceleration=400)
            wait_idle(robot)

            # -----------------------------------------------------------------
            # 二、多段路径 Move(path) — 四组合 + 末段 MovC（与 C++ path 一致）
            # -----------------------------------------------------------------
            print(
                "\n[6] Move(path): "
                "movJ+jp → movJ+cp → movL+cp → movL+jp → movC"
            )
            path = [
                MoveInstruction.MovJ(joint_pose, speed=40, acc=100),
                MoveInstruction.MovJ(line_p2, speed=40, acc=100),
                MoveInstruction.MovL(line_p1, speed=150, acc=500, blend=25),
                MoveInstruction.MovL(joint_pose, speed=150, acc=500, blend=25),
                MoveInstruction.MovC(
                    circle_middle, circle_end, speed=120, acc=400, blend=25
                ),
            ]
            robot.Move(path)
            wait_idle(robot)

            # -----------------------------------------------------------------
            # 三、阻塞式运动（*Sync）— 发送后自动等待 CRI 确认到达
            # -----------------------------------------------------------------
            print("\n[7] MovJSync + JointPoint  (阻塞式关节运动)")
            robot.MovJSync(joint_pose, speed=40, acceleration=100)
            print("  ✓ 到达目标")

            print("\n[8] MovLSync + CartesianPoint  (阻塞式直线运动)")
            robot.MovLSync(line_p1, speed=150, acceleration=500)
            print("  ✓ 到达目标")

            print("\n[9] MovJSync + 自定义 MotionWaitOptions")
            opts = MotionWaitOptions(timeout=30.0, joint_tolerance_deg=0.5)
            robot.MovJSync(joint_home, speed=40, acceleration=100, wait=opts)
            print("  ✓ 到达目标")

            # -----------------------------------------------------------------
            # 四、blend / relative_blend 演示
            # -----------------------------------------------------------------
            print("\n[10] MovL + blend=10  (平滑过渡，不停留)")
            robot.MovL(line_p1, speed=150, acceleration=500, blend=10)
            wait_idle(robot)

            print("\n[11] MovL + blend=None  (无过渡，精确到达)")
            robot.MovL(line_p2, speed=150, acceleration=500)
            wait_idle(robot)

            print("\n[12] MovJ + relative_blend=0.5  (相对平滑)")
            robot.MovJ(joint_pose, speed=40, acceleration=100, relative_blend=0.5)
            wait_idle(robot)

            print("\n[13] Move(path) + blend/relative_blend 混合")
            path_blend = [
                MoveInstruction.MovJ(joint_pose, speed=40, acc=100),
                MoveInstruction.MovL(line_p1, speed=150, acc=500, blend=15),
                MoveInstruction.MovL(line_p2, speed=150, acc=500, relative_blend=0.3),
                MoveInstruction.MovL(joint_home, speed=150, acc=500),  # 精确到达
            ]
            robot.Move(path_blend)
            wait_idle(robot)

            PrintBanner("08 — 完成", subtitle="四组合 + MovC + Sync + blend 演示")
            time.sleep(1)
    except KeyboardInterrupt:
        return 130

    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
