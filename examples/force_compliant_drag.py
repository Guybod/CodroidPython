#!/usr/bin/env python3
"""
柔顺拖拽示例

启动后进入柔顺模式，所有轴低刚度，可手动拖拽机器人，Ctrl+C 退出。

【运行】
  PYTHONPATH=src python3 examples/force_compliant_drag.py
  PYTHONPATH=src python3 examples/force_compliant_drag.py 192.168.1.136
"""
from __future__ import annotations

import sys
import time

from codroid import (
    CodroidControlInterface,
    ForceFrame,
    ForceAxisMode,
    ForceHealth,
    InitConsoleUtf8,
)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.136"

    with CodroidControlInterface(host=host) as robot:
        # 清错 → 自动 → 远程 → 上电
        robot.ClearSystemError()
        time.sleep(2)
        robot.EnterRemoteModeViaAuto()
        time.sleep(2)
        robot.SwitchOn()
        time.sleep(2)

        # 零力校准（清零传感器，避免虚假外力）
        print("零力校准中...")
        robot.FTSensorDriftCalibration()
        print("✓ 零力校准完成\n")

        # 配参：Z 轴柔顺，其余位控
        robot.InitForceControl(
            frame=ForceFrame.TCP,       # 工具坐标系
            axis_mode=[
                ForceAxisMode.POSITION,  # X: 位控
                ForceAxisMode.POSITION,  # Y: 位控
                ForceAxisMode.COMPLIANT, # Z: 柔顺
                ForceAxisMode.POSITION,  # RX: 位控
                ForceAxisMode.POSITION,  # RY: 位控
                ForceAxisMode.POSITION,  # RZ: 位控
            ],
            compliance={
                # 刚度 K：越低越容易拖动（N/m, N·m/rad）
                "stiffness": [0, 0, 0, 0, 0, 0],
                # 阻尼 D：越低越省力（N·s/m, N·m·s/rad）
                "damping": [250, 250, 50, 7.5, 7.5, 7.5],
                # 质量 M：导纳算法须 >0（kg, kg·m²）
                "mass": [2.5, 2.5, 1.5, 0.15, 0.15, 0.15],
            },
        )

        # 进入力控
        robot.StartForceControl()
        print("✓ 已进入柔顺模式，可手动拖拽机器人，Ctrl+C 退出\n")

        try:
            while True:
                state = robot.GetForceState()

                def fmt6(arr, prec=2):
                    v = list(arr) + [0.0] * 6
                    return f"[{v[0]:7.{prec}f}, {v[1]:7.{prec}f}, {v[2]:7.{prec}f}, {v[3]:7.{prec}f}, {v[4]:7.{prec}f}, {v[5]:7.{prec}f}]"

                print(f"外力: {fmt6(state.wrench_tcp)}  |  健康: {ForceHealth(state.health).name}")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n正在退出柔顺模式...")
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
