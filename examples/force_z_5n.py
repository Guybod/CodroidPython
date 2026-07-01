#!/usr/bin/env python3
"""
Z 轴恒力 + 运动示例

进入 Z 轴恒力跟踪后，配合 MovJ / MovL 运动（适合按摩等恒压走线场景）。
X/Y 位控走轨迹，Z 方向维持恒定压力。

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/force_z_5n.py
    Windows PS:      $env:PYTHONPATH="src"; python examples/force_z_5n.py
    Windows cmd:     set PYTHONPATH=src && python examples\force_z_5n.py

  本地安装启动（pip install -e . 后）：
    python examples/force_z_5n.py

  使用前：改配置区 ROBOT_IP 等，在 main() 里取消注释需要的功能。
"""
from __future__ import annotations

import time

from codroid import (
    CodroidControlInterface,
    ForceFrame,
    ForceAxisMode,
    InitConsoleUtf8,
    JointPoint,
    PrintBanner,
)

# =============================================================================
# 配置区 — 按需修改
# =============================================================================

ROBOT_IP = "192.168.1.136"       # 控制器 IP
TARGET_FORCE_N = 5.0             # Z 方向目标力 (N)，向下为负，脚本内会自动取 -abs()
FORCE_RAMP_MS = 500.0            # 期望力斜坡加载时间 (ms)，避免刚接触时冲击

# 运动速度（力控下宜慢）
MOVJ_SPEED = 30
MOVJ_ACC = 100
MOVL_SPEED = 80
MOVL_ACC = 200
MOVE_LOOPS = 2                   # 往返循环次数
WAIT_AFTER_MOVE_S = 3.0          # 每次运动后等待秒数（等到位 + 力稳定）

# MovJ 路径点位（20 个，单位：度 [J1,J2,J3,J4,J5,J6]）
# 轨迹示意：起点 → 向右扫一条线 → 折返 → 向左扫 → 回到起点
# ⚠ 请按实际机型、工具长度、工作空间修改，避免碰撞
MOVJ_WAYPOINTS_DEG: list[list[float]] = [
    [0, 0, 90, 0, 90, 0],       # 01 起点 / 安全位
    [3, 0, 90, 0, 90, 0],       # 02 右移起步
    [6, -2, 89, 0, 89, 2],      # 03
    [9, -2, 89, 0, 89, 2],      # 04
    [12, -2, 89, 0, 89, 2],     # 05
    [15, -2, 89, 0, 89, 2],     # 06
    [18, -2, 89, 0, 89, 2],     # 07
    [21, -2, 89, 0, 89, 2],     # 08 右扫末端
    [24, 0, 90, 0, 90, 0],      # 09 折返过渡
    [21, 0, 90, 0, 90, 0],      # 10
    [18, 0, 90, 0, 90, 0],      # 11
    [15, 0, 90, 0, 90, 0],      # 12
    [12, 0, 90, 0, 90, 0],      # 13
    [9, 0, 90, 0, 90, 0],       # 14
    [6, 2, 91, 0, 88, -2],      # 15 换行向左
    [3, 2, 91, 0, 88, -2],      # 16
    [0, 2, 91, 0, 88, -2],      # 17
    [-3, 2, 91, 0, 88, -2],     # 18
    [-6, 2, 91, 0, 88, -2],     # 19 左扫末端
    [0, 0, 90, 0, 90, 0],       # 20 回起点
]
MOVJ_WAYPOINTS = [JointPoint.Degrees(p) for p in MOVJ_WAYPOINTS_DEG]

# MovL 路径点位（20 个，单位：度）— 与 MovJ 独立的一条路径
# 轨迹示意：小幅 S 形走线，J1/J2 交替变化，适合模拟贴面推揉
# ⚠ MovL(JointPoint) 是关节空间直线，非 TCP 笛卡尔直线；按摩 TCP 走线见 08_move.py
MOVL_WAYPOINTS_DEG: list[list[float]] = [
    [0, 0, 90, 0, 90, 0],       # 01 起点
    [2, -1, 89, 0, 89, 1],      # 02
    [4, -2, 88, 0, 88, 2],      # 03
    [6, -2, 88, 0, 88, 2],      # 04
    [8, -1, 89, 0, 89, 1],      # 05 S 形上弧
    [10, 0, 90, 0, 90, 0],      # 06
    [12, 1, 91, 0, 91, -1],     # 07
    [14, 2, 92, 0, 92, -2],     # 08
    [16, 2, 92, 0, 92, -2],     # 09
    [18, 1, 91, 0, 91, -1],     # 10 S 形下弧
    [20, 0, 90, 0, 90, 0],      # 11 最远点
    [18, -1, 89, 0, 89, 1],     # 12 折返
    [16, -2, 88, 0, 88, 2],     # 13
    [14, -2, 88, 0, 88, 2],     # 14
    [12, -1, 89, 0, 89, 1],     # 15
    [10, 0, 90, 0, 90, 0],      # 16
    [8, 1, 91, 0, 91, -1],      # 17
    [6, 2, 92, 0, 92, -2],      # 18
    [3, 1, 91, 0, 91, -1],      # 19 回到近端
    [0, 0, 90, 0, 90, 0],       # 20 回起点
]
MOVL_WAYPOINTS = [JointPoint.Degrees(p) for p in MOVL_WAYPOINTS_DEG]


# =============================================================================
# 基础流程
# =============================================================================

def power_on(robot: CodroidControlInterface) -> None:
    """上电：远程模式 → 使能 → 等待 Ready。"""
    print("正在连接机器人...")
    robot.EnterRemoteModeViaAuto()
    robot.SwitchOn()
    time.sleep(3)
    print("✓ 机器人已就绪")


def calibrate_force_sensor(robot: CodroidControlInterface) -> None:
    """六维力传感器零力校准（进入力控前建议执行）。"""
    print("正在零力校准...")
    robot.FTSensorDriftCalibration()
    time.sleep(1)
    print("✓ 零力校准完成")


def init_constant_force_z(robot: CodroidControlInterface, force_n: float) -> None:
    """
    配参：Z 轴恒力跟踪（导纳算法）。

    轴分工：
      X, Y, RX, RY, RZ → 位控（走轨迹 / 保持姿态）
      Z                → 力控（维持恒定压力）
    """
    target_z = -abs(force_n)
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
            "desiredForce": [0, 0, target_z, 0, 0, 0],
            "stiffness": [0, 0, 0, 0, 0, 0],           # 纯力跟踪取 0
            "damping": [0, 0, 25, 0, 0, 0],            # 阻尼，影响响应柔度
            "mass": [0.5, 0.5, 0.5, 0.02, 0.02, 0.02], # 导纳算法须 >0
            "rampTimeMs": FORCE_RAMP_MS,
        },
    )
    print(f"✓ 配参完成，Z 轴目标力 {target_z} N")


def start_force_control(robot: CodroidControlInterface) -> None:
    """触发进入力控，等待状态机 Ready。"""
    robot.StartForceControl()
    print("✓ 已触发进入力控")
    time.sleep(2)


def stop_force_control(robot: CodroidControlInterface) -> None:
    """平滑退出力控。"""
    robot.StopForceControl(smooth_time_ms=500)
    print("✓ 力控已退出")


def power_off(robot: CodroidControlInterface) -> None:
    """下电：自动 → 手动 → 断使能。"""
    print("正在下电...")
    robot.ToAuto()
    robot.ToManual()
    time.sleep(1)
    robot.SwitchOff()
    print("✓ 已下电")


# =============================================================================
# 状态查询
# =============================================================================

def print_force_state(robot: CodroidControlInterface) -> None:
    """打印当前力控状态（Z 轴为主）。"""
    state = robot.GetForceState()
    print(f"  力控已启用: {state.enabled}, 接触: {state.is_contact}, 过力: {state.is_overforce}")
    print(f"  TCP 外力 Z: {state.wrench_tcp[2]:.1f} N, 期望 Z: {state.desired_wrench[2]:.1f} N")
    print(f"  跟踪误差 Z: {state.track_error[2]:.2f} N")


def run_joint_waypoints(
    robot: CodroidControlInterface,
    waypoints_deg: list[list[float]],
    waypoints: list[JointPoint],
    move,
    *,
    speed: float,
    acceleration: float,
    label: str,
) -> None:
    """
    依次经过路径上每个关节点。

    Args:
        waypoints_deg: 原始角度列表（仅用于日志打印）
        waypoints: JointPoint 列表
        move: robot.MovJ 或 robot.MovL
        speed: 速度
        acceleration: 加速度
        label: 日志前缀（MovJ / MovL）
    """
    total = len(waypoints)
    for idx, (deg, pt) in enumerate(zip(waypoints_deg, waypoints), start=1):
        print(f"  → [{idx:02d}/{total}] {label} {deg}")
        move(pt, speed=speed, acceleration=acceleration)
        time.sleep(WAIT_AFTER_MOVE_S)
        print_force_state(robot)


# =============================================================================
# 功能演示 — 在 main() 里取消注释即可调用
# =============================================================================

def hold_force_only(robot: CodroidControlInterface) -> None:
    """
    仅保力，不运动。

    进入力控后原地维持 Z 轴恒力，Ctrl+C 结束。
    适合：先验证力控是否正常、观察恒压效果。
    """
    print(f"✓ Z 轴 {-abs(TARGET_FORCE_N)} N 恒力保持中，Ctrl+C 退出")
    while True:
        time.sleep(1)


def demo_movj_with_force(robot: CodroidControlInterface) -> None:
    """
    恒力 + MovJ 关节运动。

    依次经过 MOVJ_WAYPOINTS 全部 20 个点，Z 轴恒力全程保持。
    适合：验证力控与关节插补运动兼容、模拟扫压走线。
    """
    print(f"\n===== MovJ 恒力路径（{len(MOVJ_WAYPOINTS)} 点）× {MOVE_LOOPS} 轮 =====")
    for loop in range(MOVE_LOOPS):
        print(f"\n--- 第 {loop + 1} 轮 MovJ ---")
        run_joint_waypoints(
            robot,
            MOVJ_WAYPOINTS_DEG,
            MOVJ_WAYPOINTS,
            robot.MovJ,
            speed=MOVJ_SPEED,
            acceleration=MOVJ_ACC,
            label="MovJ",
        )
    print("\n✓ MovJ 路径完成")


def demo_movl_with_force(robot: CodroidControlInterface) -> None:
    """
    恒力 + MovL 直线运动（关节目标）。

    依次经过 MOVL_WAYPOINTS 全部 20 个点。
    注意：MovL(JointPoint) 是关节空间直线，不是 TCP 笛卡尔直线。
    按摩走线若需 TCP 沿 XY 平面推，请改用 CartesianPoint（见 08_move.py）。
    """
    print(f"\n===== MovL 恒力路径（{len(MOVL_WAYPOINTS)} 点）× {MOVE_LOOPS} 轮 =====")
    for loop in range(MOVE_LOOPS):
        print(f"\n--- 第 {loop + 1} 轮 MovL ---")
        run_joint_waypoints(
            robot,
            MOVL_WAYPOINTS_DEG,
            MOVL_WAYPOINTS,
            robot.MovL,
            speed=MOVL_SPEED,
            acceleration=MOVL_ACC,
            label="MovL",
        )
    print("\n✓ MovL 路径完成")


def demo_tune_force_online(robot: CodroidControlInterface) -> None:
    """
    运行中在线调整 Z 轴目标力。

    演示压力从 5N → 10N → 30N → 5N 阶梯变化。
    适合：测试不同按摩力度、找合适压力值。
    """
    steps = [
        ("初始 5N", -5.0),
        ("提升到 10N", -10.0),
        ("提升到 30N", -30.0),
        ("降回 5N", -5.0),
    ]
    print("\n===== 在线调力 =====")
    for label, force_z in steps:
        print(f"\n-- {label} --")
        robot.TuneForceParams(desired_force=[0, 0, force_z, 0, 0, 0])
        time.sleep(3)
        print_force_state(robot)


def poll_force_state_loop(robot: CodroidControlInterface, interval_s: float = 1.0) -> None:
    """
    周期性打印力控状态。

    适合：配合其他功能调试，或单独观察力数据。
    Ctrl+C 结束。
    """
    print(f"力控状态轮询（每 {interval_s}s），Ctrl+C 退出")
    while True:
        print_force_state(robot)
        time.sleep(interval_s)


# =============================================================================
# 主流程
# =============================================================================

def main() -> None:
    PrintBanner(
        "Force Z + Motion",
        subtitle=f"{ROBOT_IP}  Z={-abs(TARGET_FORCE_N)}N",
    )

    with CodroidControlInterface(host=ROBOT_IP) as robot:
        # --- 固定流程：上电 → 校准 → 配参 → 进入力控 ---
        power_on(robot)
        calibrate_force_sensor(robot)
        init_constant_force_z(robot, TARGET_FORCE_N)
        start_force_control(robot)

        try:
            # =============================================================
            # 在下面取消注释你需要跑的功能（可组合，按顺序执行）
            # =============================================================

            # hold_force_only(robot)              # 仅保力，不运动
            demo_movj_with_force(robot)           # 恒力 + MovJ
            # demo_movl_with_force(robot)         # 恒力 + MovL
            # demo_tune_force_online(robot)       # 在线调力
            # poll_force_state_loop(robot)        # 持续打印力控状态

        except KeyboardInterrupt:
            print("\n已中断")
        finally:
            stop_force_control(robot)
            power_off(robot)


if __name__ == "__main__":
    InitConsoleUtf8()
    main()
