#!/usr/bin/env python3
"""
示例 09 — 连续路径一次下发（MoveInstruction + Move）

【目的】
  演示多段 movJ/movL 拼成列表后 ``robot.Move(path)``，控制器按序执行。
  对比示例 08：此处为「折线+混合」演示点位，非 S20 标定常量。

【前置条件】
  - 远程、使能；点位在机器人工作空间内（示例为通用演示坐标）

【涉及协议】
  - Robot/move：指令数组；movL 段可设 blend 过渡半径

【运行】
  PYTHONPATH=src python examples/09_move_path.py --robot <IP>

【注意】
  - blend>0 时相邻段在拐角处平滑，末段 blend=0 表示精确停到点
  - 笛卡尔段使用 ``CartesianPoint.MmDeg``，单位 mm + 度
"""
from __future__ import annotations

import argparse
import sys

from codroid import (
    CartesianPoint,
    CodroidControlInterface,
    InitConsoleUtf8,
    JointPoint,
    MoveInstruction,
    PrintBanner,
)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Move(path) with MoveInstruction")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("09 — Move path", subtitle=args.robot)

    # 预先构建路径：勿手写 type/targetPoint，用工厂保证 jp/cp 互斥
    path = [
        MoveInstruction.MovJ(JointPoint.Degrees([0, 0, 90, 0, 90, 0]), speed=60, acc=150),
        MoveInstruction.MovL(
            CartesianPoint.MmDeg([927.51,214.488,486.526,179.999,0,-89.999]),
            speed=500,
            acc=1500,
            blend=30,
        ),
        MoveInstruction.MovL(
            CartesianPoint.MmDeg([927.51,214.488,886.526,179.999,0,-89.999]),
            speed=500,
            acc=1500,
            blend=30,
        ),
        MoveInstruction.MovL(
            CartesianPoint.MmDeg([927.51,214.488,486.526,179.999,0,-89.999]),
            speed=500,
            acc=1500,
            blend=30,
        ),
        MoveInstruction.MovL(
            CartesianPoint.MmDeg([927.51,214.488,886.526,179.999,0,-89.999]),
            speed=500,
            acc=1500,
            blend=30,
        ),
        MoveInstruction.MovJ(
            JointPoint.Degrees([0, 0, 90, 0, 90, 0]),
            speed=60,
            acc=150,
            relative_blend=80,
        ),
    ]

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()
            robot.SwitchOn()
            print("发送连续路径 / Sending path...")
            res = robot.Move(path)
            if res.is_success:
                print("路径已送达 / Path accepted")
            else:
                print(f"失败 / Failed: {res.err}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
