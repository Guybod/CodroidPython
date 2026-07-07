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

        # 以初始点为中心，边长 100mm 正方形（XY 平面，Z 不动）
        cx, cy, cz, crx, cry, crz = 494.141, 190.096, 397.696, 179.999, 0, -90
        half = 50

        # 四个角点（协议格式）
        bl = {"cp": [cx - half, cy - half, cz, crx, cry, crz]}  # 左下(XY最小)
        br = {"cp": [cx + half, cy - half, cz, crx, cry, crz]}  # 右下
        tr = {"cp": [cx + half, cy + half, cz, crx, cry, crz]}  # 右上
        tl = {"cp": [cx - half, cy + half, cz, crx, cry, crz]}  # 左上
        st = {"cp": [cx, cy, cz, crx, cry, crz]}                # 起点

        # 第一步：用 runScript 移动到左下（不启动力控）
        print("移动到左下起点...")
        robot._send_command("project/runScript", {
            "scripts": {"main": "movL(bl, {v=100, a=500})"},
            "vars": {"bl": bl},
        })
        time.sleep(3)

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
                "desiredForce": [0, 0, 2, 0, 0, 0],
                # 刚度 K：纯力跟踪取 0，单位 N/m、N·m/rad
                "stiffness": [0, 0, 0, 0, 0, 0],
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
            movL(br, {v=50, a=500})
            movL(tr, {v=50, a=500})
            movL(tl, {v=50, a=500})
            movL(bl, {v=50, a=500})
            movL(br, {v=50, a=500})
            movL(tr, {v=50, a=500})
            movL(tl, {v=50, a=500})
            movL(bl, {v=50, a=500})
            movL(st, {v=50, a=500})
        """
        robot._send_command("project/runScript", {
            "scripts": {"main": script},
            "vars": {"bl": bl, "br": br, "tr": tr, "tl": tl, "st": st},
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
