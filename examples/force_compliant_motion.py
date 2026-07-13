#!/usr/bin/env python3
"""
柔顺模式 + 运动指令示例

先关节运动到 [0,0,90,0,90,0]，进入柔顺模式后，按四个角点跑七圈
（点位与 force_z_5n.py 相同，每圈 pp1→pp2→pp3→pp4 共四段）。

【运行】
  PYTHONPATH=src python3 examples/force_compliant_motion.py
  PYTHONPATH=src python3 examples/force_compliant_motion.py 192.168.1.136
"""
from __future__ import annotations

import sys
import time

from codroid import (
    CartesianPoint,
    CodroidControlInterface,
    ForceAxisMode,
    ForceFrame,
    ForceHealth,
    InitConsoleUtf8,
    JointPoint,
    MoveInstruction,
)

# 与 force_z_5n.py 相同的四个角点（mm + 度）
PP1 = [541.767,369.358,397.581,179.98,0.006,-89.999]
PP2 = [541.762,-250.604,397.523,179.976,0.013,-89.996]
PP3 = [342.515,-250.599,397.52,179.976,0.014,-89.997]
PP4 = [342.54,455.995,397.531,179.977,0.012,-89.994]

JOINT_HOME = [0, 0, 90, 0, 90, 0]
CORNER_POINTS = [PP1, PP2, PP3, PP4]
LAPS = 7
MOV_SPEED = 50
MOV_ACC = 500


def build_square_path(laps: int = LAPS) -> list:
    """构造多圈矩形路径：每圈四角四段，圈与圈之间 pp4→pp1 由下一圈首段衔接。"""
    path = []
    for _ in range(laps):
        for p in CORNER_POINTS:
            path.append(
                MoveInstruction.MovL(
                    CartesianPoint.MmDeg(p), speed=MOV_SPEED, acc=MOV_ACC
                )
            )
    return path


def fmt6(arr, prec=2):
    v = list(arr) + [0.0] * 6
    return (
        f"[{v[0]:7.{prec}f}, {v[1]:7.{prec}f}, {v[2]:7.{prec}f}, "
        f"{v[3]:7.{prec}f}, {v[4]:7.{prec}f}, {v[5]:7.{prec}f}]"
    )


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.136"

    with CodroidControlInterface(host=host) as robot:
        print("进入远程模式...")
        robot.EnterRemoteModeViaAuto()
        time.sleep(2)
        print("清除系统错误...")
        robot.ClearSystemError()
        time.sleep(2)
        print("使能机器人...")
        robot.SwitchOn()
        time.sleep(2)

        print("零力校准中...")
        robot.ZeroForceCalibration()
        print("✓ 零力校准完成\n")

        # 力控进入前须静止，先关节运动到起始姿态
        # print(f"关节运动到起始点 {JOINT_HOME} ...")
        # robot.MovJ(JointPoint.Degrees(JOINT_HOME), MOV_SPEED/10, MOV_ACC/10)
        # time.sleep(8)
        # print("✓ 已到达起始姿态\n")

        # Z 轴柔顺，其余位控（与 force_compliant_drag.py 一致）
        robot.InitForceControl(
            frame=ForceFrame.TCP,
            axis_mode=[
                ForceAxisMode.COMPLIANT,
                ForceAxisMode.COMPLIANT,
                ForceAxisMode.COMPLIANT,
                ForceAxisMode.COMPLIANT,
                ForceAxisMode.COMPLIANT,
                ForceAxisMode.COMPLIANT,
            ],
            compliance={
                "stiffness": [0, 0, 0, 0, 0, 0],
                "damping": [250, 250, 50, 7.5, 7.5, 7.5],
                "mass": [2.5, 2.5, 1.5, 0.15, 0.15, 0.15],
            },
        )
        robot.StartForceControl()
        print(f"✓ 已进入柔顺模式，下发 {LAPS} 圈矩形路径（共 {LAPS * 4} 段 movL）\n")
        time.sleep(2)

        path = build_square_path(LAPS)
        robot.Move(path)
        print("✓ 运动指令已下发，运动中可手动施力测试，Ctrl+C 退出\n")

        try:
            while True:
                try:
                    state = robot.GetForceState()
                    print(
                        f"外力: {fmt6(state.wrench_tcp)}  |  "
                        f"健康: {ForceHealth(state.health).name}"
                    )
                except Exception as e:
                    print(f"读取力控状态失败: {e}")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n正在退出柔顺模式...")
        finally:
            robot.StopForceControl(smooth_time_ms=500)
            time.sleep(1)
            robot.SwitchOff()
            print("✓ 已退出")


if __name__ == "__main__":
    InitConsoleUtf8()
    main()
