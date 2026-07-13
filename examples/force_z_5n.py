#!/usr/bin/env python3
"""
Z 轴 2N 恒力 + 正方形环绕示例

启动后给 Z 轴一个 2N 恒力，然后用 runScript 执行正方形环绕运动。

【运行】
  PYTHONPATH=src python3 examples/force_z_5n.py
  PYTHONPATH=src python3 examples/force_z_5n.py 192.168.1.136
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
        # 清错 → 自动 → 远程 → 上电
        robot.ClearSystemError()
        robot.EnterRemoteModeViaAuto()
        robot.SwitchOn()
        time.sleep(5)  # 等待机器人进入 Ready

        # 停止可能残留的工程
        try:
            robot._send_command('project/stop', '')
        except Exception:
            pass
        time.sleep(1)

        # 零力校准（清零传感器，避免虚假外力）
        print("零力校准中...")
        robot.ZeroForceCalibration()
        print("✓ 零力校准完成\n")

        # 以初始点为中心，边长 100mm 正方形（XY 平面，Z 不动）
        cx, cy, cz, crx, cry, crz = 494.141, 190.096, 397.696, 179.999, 0, -90
        half = 250

        # 四个角点（协议格式）
        pp1 = {"cp":[494.10972061020817,190.07513680424233,397.66482228773134,179.99347696577624,0.0007243437385977956,-89.99519356582975]}  # 左下
        pp2 = {"cp":[587.7420594897396,190.09530085256662,397.7008310420421,-179.99622344258242,0.0007234385681332798,-89.99965662970091]}  # 右下
        pp3 = {"cp":[587.7488339035018,51.530526041243064,397.64336953362044,179.99016923113925,0.003156388398125734,-90.00309023933376]}  # 右上
        pp4 = {"cp":[434.1802437365524,51.528578104899765,397.72901467031187,-179.99327215865438,-0.0015516914737670271,-90.0010300155903]}  # 左上

        # 第二步：配参并启动力控
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
                # 期望力/力矩：[Fx, Fy, Fz, Mx, My, Mz]，单位 N / N·m
                "desiredForce": [0, 0, 20, 0, 0, 0],
                # 阻尼 D：抑制振荡，单位 N·s/m、N·m·s/rad
                "damping": [250, 250, 250, 7.5, 7.5, 7.5],
                # 质量 M：导纳算法须 >0，单位 kg、kg·m²
                "mass": [2.5, 2.5, 2.5, 0.15, 0.15, 0.15],
            },
        )
        robot.StartForceControl()
        print("✓ 力控已启动（Z 轴 2N）")

        # 第三步：用 runScript 执行正方形环绕（两圈回起点）
        script = """
            movL(pp1, {v=50, a=500})
            movL(pp2, {v=50, a=500})
            movL(pp3, {v=50, a=500})
            movL(pp4, {v=50, a=500})
            movL(pp1, {v=50, a=500})
        """
        robot._send_command("project/runScript", {
            "scripts": {"main": script},
            "vars": {"pp1": pp1, "pp2": pp2, "pp3": pp3, "pp4": pp4},
        })
        print("✓ 环绕脚本已下发")

        try:
            print("Ctrl+C 退出...")
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
