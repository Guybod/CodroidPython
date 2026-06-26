#!/usr/bin/env python3
"""
示例 16 — 力控工艺包演示（导纳柔顺 + 恒力跟踪）

【目的】
  演示力控工艺包的两个典型场景：
  1. 导纳柔顺：Z 轴柔顺，其余方向位控保持
  2. 恒力跟踪：Z 方向保持恒定压力，运行中在线调参

【前置条件】
  - 控制器与 PC 同网段，TCP 9001 可达
  - 机器人已安装六维力传感器且已完成零力校准
  - 机器人可远程控制、允许上使能
  - 安全空间内运行（力控可能产生位移）

【涉及协议】
  - TCP：Robot/initForceControl, startForceControl, stopForceControl,
         tuneForceParams, getForceState

【运行】
  PYTHONPATH=src python examples/16_force_control.py
  PYTHONPATH=src python examples/16_force_control.py --robot 192.168.1.136
  PYTHONPATH=src python examples/16_force_control.py --demo compliance
  PYTHONPATH=src python examples/16_force_control.py --demo constant_force

【注意】
  - 力控进入前须确保 TCP 速度 ≈ 0（>1e-3 m/s 会被拒绝）
  - 过力保护为内置安全机制，无法通过 API 关闭
  - 六维顺序统一为 [X, Y, Z, RX, RY, RZ]，力/力矩单位 N / N·m
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import List

from codroid import (
    CodroidControlInterface,
    ForceFrame,
    ForceAxisMode,
    ForceHealth,
    InitConsoleUtf8,
    JointPoint,
    CartesianPoint,
    PrintBanner,
)


# =============================================================================
# 辅助函数：构造柔顺/恒力配置块
# =============================================================================

def make_compliance(
    stiffness: List[float],
    damping: List[float],
    axis_enable: List[bool],
    mass: List[float] = None,
    activate: bool = True,
) -> dict:
    """
    构造柔顺原语配置块。

    Args:
        stiffness: 刚度 K [Kx, Ky, Kz, Krx, Kry, Krz] (N/m, N·m/rad)
        damping: 阻尼 D [Dx, Dy, Dz, Drx, Dry, Drz] (N·s/m, N·m·s/rad)
        axis_enable: 各轴是否启用柔顺 [bool x 6]
        mass: 质量 M [Mx, My, Mz, Mrx, Mry, Mrz] (kg, kg·m²)，导纳须 >0
        activate: 是否激活该原语
    """
    block = {
        "stiffness": stiffness,
        "damping": damping,
        "axisEnable": axis_enable,
        "activate": activate,
    }
    if mass is not None:
        block["mass"] = mass
    return block


def make_constant_force(
    stiffness: List[float],
    damping: List[float],
    desired_force: List[float],
    axis_enable: List[bool],
    mass: List[float] = None,
    ramp_time_ms: float = 500.0,
    activate: bool = True,
) -> dict:
    """
    构造恒力原语配置块。

    Args:
        stiffness: 刚度 K（纯力跟踪取 0）
        damping: 阻尼 D
        desired_force: 期望力 [Fx, Fy, Fz, Mx, My, Mz] (N / N·m)
        axis_enable: 各轴是否启用恒力 [bool x 6]
        mass: 质量 M，导纳须 >0
        ramp_time_ms: 期望力从 0 斜坡到目标的时长 (ms)
        activate: 是否激活该原语
    """
    block = {
        "stiffness": stiffness,
        "damping": damping,
        "desiredForce": desired_force,
        "axisEnable": axis_enable,
        "rampTimeMs": ramp_time_ms,
        "activate": activate,
    }
    if mass is not None:
        block["mass"] = mass
    return block


def print_force_state(robot) -> None:
    """打印当前力控状态。"""
    state = robot.GetForceState()
    print(f"  力控已启用: {state.enabled}")
    print(f"  外力数据有效: {state.valid}")
    print(f"  TCP 外力: {[f'{v:.1f}' for v in state.wrench_tcp]}")
    print(f"  期望力: {[f'{v:.1f}' for v in state.desired_wrench]}")
    print(f"  力跟踪误差: {[f'{v:.2f}' for v in state.track_error]}")
    print(f"  接触判定: {state.is_contact}, 过力判定: {state.is_overforce}")
    print(f"  健康状态: {ForceHealth(state.health).name}")
    print()


# =============================================================================
# 演示一：导纳柔顺（Z 轴柔顺，其余位控）
# =============================================================================

def demo_admittance_compliance(robot) -> None:
    """
    导纳柔顺演示：
    - Z 平动方向柔顺（外力推动即顺从）
    - 其余方向位控保持
    - 配合脚本运动，在运动过程中保持柔顺
    """
    print("\n===== 演示一：导纳-柔顺 =====")
    print("场景：Z 轴柔顺，XY 位控，配合直线运动\n")

    # --- 第一步：配参 ---
    # 柔顺参数说明：
    #   - stiffness 越低 → 越容易顺从（Z=500 N/m 较低）
    #   - damping 适当 → 抑制振荡（Z=25 N·s/m）
    #   - mass 导纳算法须 >0（期望惯量）
    stiffness = [0.0, 0.0, 500.0, 0.0, 0.0, 0.0]   # N/m
    damping   = [0.0, 0.0,  25.0, 0.0, 0.0, 0.0]   # N·s/m
    mass      = [0.5, 0.5,   0.5, 0.02, 0.02, 0.02]  # kg
    axis_enable = [False, False, True, False, False, False]

    compliance = make_compliance(stiffness, damping, axis_enable, mass=mass)

    # 选择矩阵 S：Z=柔顺，其余=位控
    axis_mode = [
        ForceAxisMode.POSITION,  # X: 位控
        ForceAxisMode.POSITION,  # Y: 位控
        ForceAxisMode.COMPLIANT, # Z: 柔顺
        ForceAxisMode.POSITION,  # RX: 位控
        ForceAxisMode.POSITION,  # RY: 位控
        ForceAxisMode.POSITION,  # RZ: 位控
    ]

    # initForceControl: 一次性配参（无斜坡，立即下发）
    robot.InitForceControl(
        frame=ForceFrame.TCP,
        axis_mode=axis_mode,
        compliance=compliance,
    )
    print("✓ 配参完成（导纳 + TCP 系 + Z 柔顺）")

    # --- 第二步：进入力控 ---
    robot.StartForceControl()
    print("✓ 已触发进入力控（等待状态机 Ready 时正式进入）")
    time.sleep(2)  # 等待力控正式生效

    # --- 第三步：运动 + 轮询状态 ---
    print("\n开始运动（Z 轴柔顺中，外力可推动）...")
    p1 = JointPoint.Degrees([0, 0, 90, 0, 90, 0])
    p2 = JointPoint.Degrees([0, 0, 0, 0, 0, 0])

    for i in range(3):
        print(f"\n--- 第 {i+1} 轮运动 ---")
        robot.MovJ(p1, 30, 100)
        time.sleep(3)
        print_force_state(robot)

        robot.MovJ(p2, 30, 100)
        time.sleep(3)
        print_force_state(robot)

    # --- 第四步：平滑退出 ---
    robot.StopForceControl(smooth_time_ms=500)
    print("✓ 力控已平滑退出")
    time.sleep(1)


# =============================================================================
# 演示二：导纳恒力跟踪（Z 方向保持恒定压力）
# =============================================================================

def demo_admittance_constant_force(robot) -> None:
    """
    导纳恒力跟踪演示：
    - Z 方向保持 -20N 向下压力
    - 运行中通过 tuneForceParams 在线调整期望力
    - 展示斜坡平滑加载效果
    """
    print("\n===== 演示二：导纳-恒力跟踪 =====")
    print("场景：Z 方向恒力跟踪，在线调参\n")

    # --- 第一步：配参 ---
    # 纯力跟踪参数说明：
    #   - stiffness = 0 → 纯力跟踪（无弹性回复）
    #   - damping / mass → 决定跟踪柔度和响应速度
    #   - desired_force Z = -20N → 向下压 20 牛顿
    #   - ramp_time_ms = 500 → 期望力 500ms 斜坡加载，避免冲击
    stiffness     = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]    # N/m（纯力跟踪取 0）
    damping       = [0.0, 0.0, 25.0, 0.0, 0.0, 0.0]   # N·s/m
    mass          = [0.5, 0.5, 0.5, 0.02, 0.02, 0.02]  # kg
    desired_force = [0.0, 0.0, -20.0, 0.0, 0.0, 0.0]   # N（Z 向下 20N）
    force_enable  = [False, False, True, False, False, False]

    constant_force = make_constant_force(
        stiffness, damping, desired_force, force_enable,
        mass=mass, ramp_time_ms=500.0,
    )

    # 选择矩阵 S：Z=力控，其余=位控
    axis_mode = [
        ForceAxisMode.POSITION, # X: 位控
        ForceAxisMode.POSITION, # Y: 位控
        ForceAxisMode.FORCE,    # Z: 力控
        ForceAxisMode.POSITION, # RX: 位控
        ForceAxisMode.POSITION, # RY: 位控
        ForceAxisMode.POSITION, # RZ: 位控
    ]

    robot.InitForceControl(
        frame=ForceFrame.TCP,
        axis_mode=axis_mode,
        constant_force=constant_force,
    )
    print("✓ 配参完成（导纳 + TCP 系 + Z 恒力 -20N）")

    # --- 第二步：进入力控 ---
    robot.StartForceControl()
    print("✓ 已触发进入力控")
    time.sleep(2)

    # --- 第三步：等待力稳定后在线调参 ---
    print("\n等待力稳定（2N 初始压力）...")
    time.sleep(3)
    print_force_state(robot)

    # 在线提升目标压力到 10N
    print("-- 在线提升目标压力到 -10N --")
    robot.TuneForceParams(desired_force=[0.0, 0.0, -10.0, 0.0, 0.0, 0.0])
    time.sleep(3)
    print_force_state(robot)

    # 在线提升目标压力到 30N
    print("-- 在线提升目标压力到 -30N --")
    robot.TuneForceParams(desired_force=[0.0, 0.0, -30.0, 0.0, 0.0, 0.0])
    time.sleep(3)
    print_force_state(robot)

    # 在线降低目标压力到 5N
    print("-- 在线降低目标压力到 -5N --")
    robot.TuneForceParams(desired_force=[0.0, 0.0, -5.0, 0.0, 0.0, 0.0])
    time.sleep(3)
    print_force_state(robot)

    # --- 第四步：平滑退出 ---
    robot.StopForceControl(smooth_time_ms=800)
    print("✓ 力控已平滑退出")
    time.sleep(1)


# =============================================================================
# 主流程
# =============================================================================

def main(argv: list[str]) -> int:
    # ---------- 命令行参数 ----------
    p = argparse.ArgumentParser(description="力控工艺包演示")
    p.add_argument("--robot", default="192.168.1.136", help="控制器 IP")
    p.add_argument("--demo", choices=["compliance", "constant_force", "all"],
                   default="all", help="选择演示场景")
    args = p.parse_args(argv)

    PrintBanner("16 — Force Control Demo", subtitle=f"{args.robot}  Demo: {args.demo}")

    # ---------- 连接机器人 ----------
    with CodroidControlInterface(host=args.robot) as robot:
        # 上电流程：自动 → 远程 → 使能
        print("正在连接机器人...")
        robot.EnterRemoteModeViaAuto()
        robot.SwitchOn()
        time.sleep(3)  # 等待机器人进入 Ready
        print("✓ 机器人已就绪\n")

        try:
            # 建议：进入力控前执行零力校准
            robot.FTSensorDriftCalibration()
            time.sleep(1)

            if args.demo in ("compliance", "all"):
                demo_admittance_compliance(robot)

            if args.demo in ("constant_force", "all"):
                demo_admittance_constant_force(robot)

        except KeyboardInterrupt:
            print("\n已中断，正在安全退出力控...")
            try:
                robot.StopForceControl(smooth_time_ms=300)
            except Exception:
                pass
            print("已退出", file=sys.stderr)
            return 130

        except Exception as e:
            print(f"\n异常：{e}")
            print("正在安全退出力控...")
            try:
                robot.StopForceControl(smooth_time_ms=300)
            except Exception:
                pass
            raise

        finally:
            # 下电流程
            print("\n正在下电...")
            robot.ToAuto()
            robot.ToManual()
            time.sleep(1)
            robot.SwitchOff()
            print("✓ 已下电")

    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
