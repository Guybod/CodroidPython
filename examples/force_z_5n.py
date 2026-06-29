#!/usr/bin/env python3
"""
Z 轴 5N 恒力示例

启动后给 Z 轴一个向下的 5N 恒力，Ctrl+C 退出。

【运行】
  PYTHONPATH=src python examples/force_z_5n.py
  PYTHONPATH=src python examples/force_z_5n.py 192.168.1.136
"""
from __future__ import annotations

import sys
import time

from codroid import (
    CodroidControlInterface,
    ForceFrame,
    ForceAxisMode,
    InitConsoleUtf8,
)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.136"

    with CodroidControlInterface(host=host) as robot:
        # 上电
        robot.EnterRemoteModeViaAuto()
        robot.SwitchOn()
        time.sleep(3)

        # 零力校准
        robot.FTSensorDriftCalibration()
        time.sleep(1)

        # 配参：Z 轴 5N 恒力（导纳算法）
        robot.InitForceControl(
            frame=ForceFrame.TCP,
            axis_mode=[
                ForceAxisMode.POSITION,  # X: 位控
                ForceAxisMode.POSITION,  # Y: 位控
                ForceAxisMode.FORCE,     # Z: 力控
                ForceAxisMode.POSITION,  # RX: 位控
                ForceAxisMode.POSITION,  # RY: 位控
                ForceAxisMode.POSITION,  # RZ: 位控
            ],
            constant_force={
                "axisEnable": [False, False, True, False, False, False],
                "desiredForce": [0, 0, -5, 0, 0, 0],   # Z 向下 5N
                "stiffness": [0, 0, 0, 0, 0, 0],
                "damping": [0, 0, 25, 0, 0, 0],
                "mass": [0.5, 0.5, 0.5, 0.02, 0.02, 0.02],
            },
        )

        # 进入力控
        robot.StartForceControl()
        print("✓ 已进入力控，Z 轴 5N 恒力，Ctrl+C 退出")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在退出力控...")
        finally:
            robot.StopForceControl(smooth_time_ms=500)
            robot.ToAuto()
            robot.ToManual()
            time.sleep(1)
            robot.SwitchOff()
            print("✓ 已退出")


if __name__ == "__main__":
    InitConsoleUtf8()
    main()
