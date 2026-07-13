#!/usr/bin/env python3
"""
Force control API test runner.

Run from CodroidPython:
  PYTHONPATH=src python3 examples/force_test/force_api_test.py --robot 192.168.1.136 --case state
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable, List

from codroid import (
    CodroidControlInterface,
    ForceAxisMode,
    ForceFrame,
    ForceHealth,
    InitConsoleUtf8,
    PrintBanner,
)


WRENCH_ZERO = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
DEFAULT_DAMPING = [250.0, 250.0, 250.0, 7.5, 7.5, 7.5]
DEFAULT_MASS = [2.5, 2.5, 2.5, 0.15, 0.15, 0.15]


def fmt6(values: Iterable[float], precision: int = 3) -> str:
    data = list(values)[:6]
    data.extend([0.0] * (6 - len(data)))
    return "[" + ", ".join(f"{v:.{precision}f}" for v in data) + "]"


def print_response(label: str, response) -> None:
    print(f"{label}: err={response.err!r}, db={response.db!r}")


def print_state(robot) -> None:
    state = robot.GetForceState()
    print("完整状态 / GetForceState():")
    print(f"  enabled={state.enabled}, pending={state.pending}, algo={state.algo}, valid={state.valid}")
    print(f"  is_contact={state.is_contact}, is_overforce={state.is_overforce}, health={state.health}")
    print(f"  wrench_tcp={fmt6(state.wrench_tcp)}")
    print(f"  wrench_base={fmt6(state.wrench_base)}")
    print(f"  desired_wrench={fmt6(state.desired_wrench)}")
    print(f"  track_error={fmt6(state.track_error)}")
    print(f"  axis_mode={state.axis_mode}")
    print("单字段 getter:")
    print(f"  GetForceStateEnabled() -> {robot.GetForceStateEnabled()!r}")
    print(f"  GetForceStatePending() -> {robot.GetForceStatePending()!r}")
    print(f"  GetForceStateAlgo() -> {robot.GetForceStateAlgo()!r}")
    print(f"  GetForceStateValid() -> {robot.GetForceStateValid()!r}")
    print(f"  GetForceStateIsContact() -> {robot.GetForceStateIsContact()!r}")
    print(f"  GetForceStateIsOverforce() -> {robot.GetForceStateIsOverforce()!r}")
    health = robot.GetForceStateHealth()
    try:
        health_name = ForceHealth(health).name
    except ValueError:
        health_name = "UNKNOWN"
    print(f"  GetForceStateHealth() -> {health!r} ({health_name})")
    print(f"  GetForceStateWrenchTcp() -> {fmt6(robot.GetForceStateWrenchTcp())}")
    print(f"  GetForceStateWrenchBase() -> {fmt6(robot.GetForceStateWrenchBase())}")
    print(f"  GetForceStateDesiredWrench() -> {fmt6(robot.GetForceStateDesiredWrench())}")
    print(f"  GetForceStateTrackError() -> {fmt6(robot.GetForceStateTrackError())}")
    print(f"  GetForceStateAxisMode() -> {robot.GetForceStateAxisMode()!r}")


def prepare_robot(robot, skip_power: bool) -> None:
    if skip_power:
        print("跳过清错/切远程/上电流程")
        return
    print("清除错误...")
    robot.ClearSystemError()
    time.sleep(1.0)
    print("切换远程模式...")
    robot.EnterRemoteModeViaAuto()
    time.sleep(1.0)
    print("上电...")
    robot.SwitchOn()
    time.sleep(2.0)


def stop_and_power_off(robot, skip_power: bool) -> None:
    try:
        print("尝试停止力控...")
        print_response("StopForceControl", robot.StopForceControl(smooth_time_ms=300))
    except Exception as exc:
        print(f"StopForceControl ignored: {exc}")
    if skip_power:
        return
    try:
        robot.ToAuto()
        robot.ToManual()
        time.sleep(0.5)
        robot.SwitchOff()
        print("已下电")
    except Exception as exc:
        print(f"power-off cleanup ignored: {exc}")


def run_state(robot, _args) -> None:
    print_state(robot)


def run_calibration(robot, args) -> None:
    print("执行 ZeroForceCalibration...")
    response = robot.ZeroForceCalibration(
        calibration_time_ms=args.calibration_ms,
        timeout_ms=args.command_timeout_ms,
    )
    print_response("ZeroForceCalibration", response)


def run_safety_config(robot, args) -> None:
    print("设置过力保护参数...")
    response = robot.SetOverforceProtection(
        enable=not args.disable_overforce,
        force_threshold=args.force_threshold,
        hold_ms=args.overforce_hold_ms,
    )
    print_response("SetOverforceProtection", response)

    print("设置力数据健康监控参数...")
    response = robot.SetForceDataHealth(
        enable=not args.disable_health,
        timeout_ms=args.health_timeout_ms,
        max_packet_loss_ratio=args.max_packet_loss_ratio,
        packet_loss_window=args.packet_loss_window,
        force_saturation=args.force_saturation,
        torque_saturation=args.torque_saturation,
    )
    print_response("SetForceDataHealth", response)


def run_compliance(robot, args) -> None:
    print("初始化柔顺力控参数...")
    response = robot.InitForceControl(
        frame=ForceFrame.TCP,
        axis_mode=[
            ForceAxisMode.POSITION,
            ForceAxisMode.POSITION,
            ForceAxisMode.COMPLIANT,
            ForceAxisMode.POSITION,
            ForceAxisMode.POSITION,
            ForceAxisMode.POSITION,
        ],
        compliance={
            "stiffness": args.compliance_stiffness,
            "damping": args.compliance_damping,
            "mass": args.compliance_mass,
        },
    )
    print_response("InitForceControl", response)
    print_response("StartForceControl", robot.StartForceControl())
    poll_state(robot, args.hold)
    print_response("StopForceControl", robot.StopForceControl(smooth_time_ms=args.stop_smooth_ms))


def run_constant_force(robot, args) -> None:
    desired = [0.0, 0.0, args.force_z, 0.0, 0.0, 0.0]
    tuned = [0.0, 0.0, args.tune_force_z, 0.0, 0.0, 0.0]
    print("初始化恒力力控参数...")
    response = robot.InitForceControl(
        frame=ForceFrame.TCP,
        axis_mode=[
            ForceAxisMode.POSITION,
            ForceAxisMode.POSITION,
            ForceAxisMode.FORCE,
            ForceAxisMode.POSITION,
            ForceAxisMode.POSITION,
            ForceAxisMode.POSITION,
        ],
        constant_force={
            "desiredForce": desired,
            "damping": args.constant_damping,
            "mass": args.constant_mass,
            "rampTimeMs": args.ramp_time_ms,
        },
    )
    print_response("InitForceControl", response)
    print_response("StartForceControl", robot.StartForceControl())
    poll_state(robot, args.hold)
    print(f"在线调参 desired_force={fmt6(tuned)}, ramp_time={args.ramp_time_ms}ms")
    print_response(
        "TuneForceParams",
        robot.TuneForceParams(desired_force=tuned, ramp_time=args.ramp_time_ms),
    )
    poll_state(robot, args.hold)
    print_response("StopForceControl", robot.StopForceControl(smooth_time_ms=args.stop_smooth_ms))


def run_contact_detection(robot, args) -> None:
    if not args.allow_motion:
        raise RuntimeError("contact-detection 会驱动机器人进给，必须添加 --allow-motion")

    desired = WRENCH_ZERO[:]
    print("初始化接触检测前的力控参数...")
    response = robot.InitForceControl(
        frame=ForceFrame.TCP,
        axis_mode=[
            ForceAxisMode.COMPLIANT,
            ForceAxisMode.COMPLIANT,
            ForceAxisMode.FORCE,
            ForceAxisMode.COMPLIANT,
            ForceAxisMode.COMPLIANT,
            ForceAxisMode.COMPLIANT,
        ],
        constant_force={
            "desiredForce": desired,
            "damping": args.constant_damping,
            "mass": args.constant_mass,
            "rampTimeMs": args.ramp_time_ms,
        },
        compliance={
            "stiffness": args.compliance_stiffness,
            "damping": args.compliance_damping,
            "mass": args.compliance_mass,
        },
    )
    print_response("InitForceControl", response)
    print_response("StartForceControl", robot.StartForceControl())
    time.sleep(1.0)
    print("启动接触检测...")
    response = robot.StartContactDetection(
        direction=args.contact_direction,
        feed_velocity=args.feed_velocity,
        contact_force_threshold=args.contact_threshold,
        vel_drop_ratio=args.vel_drop_ratio,
        max_travel=args.max_travel,
        timeout_ms=args.contact_timeout_ms,
    )
    print_response("StartContactDetection", response)
    poll_state(robot, args.hold)
    print_response("StopForceControl", robot.StopForceControl(smooth_time_ms=args.stop_smooth_ms))


def poll_state(robot, seconds: float) -> None:
    end = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < end:
        enabled = robot.GetForceStateEnabled()
        contact = robot.GetForceStateIsContact()
        overforce = robot.GetForceStateIsOverforce()
        health = robot.GetForceStateHealth()
        wrench = robot.GetForceStateWrenchTcp()
        print(
            f"  enabled={enabled} contact={contact} overforce={overforce} "
            f"health={health} wrenchTcp={fmt6(wrench, 2)}"
        )
        time.sleep(0.5)


def parse_wrench(values: List[float], name: str) -> List[float]:
    if len(values) != 6:
        raise argparse.ArgumentTypeError(f"{name} must contain exactly 6 numbers")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codroid force control API test runner")
    parser.add_argument("--robot", default="192.168.1.136", help="robot controller IP")
    parser.add_argument(
        "--case",
        choices=[
            "state",
            "calibration",
            "safety-config",
            "compliance",
            "constant-force",
            "contact-detection",
            "all-safe",
        ],
        default="state",
        help="test case to run",
    )
    parser.add_argument("--skip-power", action="store_true", help="do not clear errors, switch mode, power on/off")
    parser.add_argument("--allow-motion", action="store_true", help="required for contact-detection")
    parser.add_argument("--hold", type=float, default=5.0, help="state polling duration for active tests")
    parser.add_argument("--stop-smooth-ms", type=int, default=500, help="StopForceControl smooth time")
    parser.add_argument("--command-timeout-ms", type=int, default=5000, help="SDK socket timeout for calibration")
    parser.add_argument("--calibration-ms", type=int, default=1000, help="ZeroForceCalibration sample time")

    parser.add_argument("--force-z", type=float, default=2.0, help="initial Z desired force for constant-force")
    parser.add_argument("--tune-force-z", type=float, default=5.0, help="tuned Z desired force")
    parser.add_argument("--ramp-time-ms", type=float, default=500.0, help="force/tuning ramp time")

    parser.add_argument("--feed-velocity", type=float, default=0.002, help="contact detection feed velocity m/s")
    parser.add_argument("--contact-threshold", type=float, default=3.0, help="contact force threshold N")
    parser.add_argument("--vel-drop-ratio", type=float, default=0.0, help="velocity drop ratio, 0 disables")
    parser.add_argument("--max-travel", type=float, default=0.01, help="contact detection max travel m")
    parser.add_argument("--contact-timeout-ms", type=float, default=5000.0, help="contact detection timeout ms")
    parser.add_argument(
        "--contact-direction",
        type=float,
        nargs=6,
        default=[0.0, 0.0, -1.0, 0.0, 0.0, 0.0],
        metavar=("Fx", "Fy", "Fz", "Mx", "My", "Mz"),
        help="contact feed direction in force frame",
    )

    parser.add_argument(
        "--force-threshold",
        type=float,
        nargs=6,
        default=[150.0, 150.0, 20.0, 40.0, 40.0, 40.0],
        metavar=("Fx", "Fy", "Fz", "Mx", "My", "Mz"),
        help="overforce threshold; 0 disables an axis",
    )
    parser.add_argument("--disable-overforce", action="store_true", help="send enable=false to SetOverforceProtection")
    parser.add_argument("--overforce-hold-ms", type=float, default=20.0)
    parser.add_argument("--disable-health", action="store_true", help="send enable=false to SetForceDataHealth")
    parser.add_argument("--health-timeout-ms", type=float, default=200.0)
    parser.add_argument("--max-packet-loss-ratio", type=float, default=0.9)
    parser.add_argument("--packet-loss-window", type=int, default=None)
    parser.add_argument("--force-saturation", type=float, default=None)
    parser.add_argument("--torque-saturation", type=float, default=None)

    parser.add_argument(
        "--compliance-stiffness",
        type=float,
        nargs=6,
        default=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        metavar=("Kx", "Ky", "Kz", "Krx", "Kry", "Krz"),
    )
    parser.add_argument(
        "--compliance-damping",
        type=float,
        nargs=6,
        default=[250.0, 250.0, 50.0, 7.5, 7.5, 7.5],
        metavar=("Dx", "Dy", "Dz", "Drx", "Dry", "Drz"),
    )
    parser.add_argument(
        "--compliance-mass",
        type=float,
        nargs=6,
        default=[2.5, 2.5, 1.5, 0.15, 0.15, 0.15],
        metavar=("Mx", "My", "Mz", "Mrx", "Mry", "Mrz"),
    )
    parser.add_argument(
        "--constant-damping",
        type=float,
        nargs=6,
        default=DEFAULT_DAMPING,
        metavar=("Dx", "Dy", "Dz", "Drx", "Dry", "Drz"),
    )
    parser.add_argument(
        "--constant-mass",
        type=float,
        nargs=6,
        default=DEFAULT_MASS,
        metavar=("Mx", "My", "Mz", "Mrx", "Mry", "Mrz"),
    )
    return parser


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.contact_direction = parse_wrench(args.contact_direction, "contact_direction")
    args.force_threshold = parse_wrench(args.force_threshold, "force_threshold")

    PrintBanner("Force API Test", subtitle=f"{args.robot}  case={args.case}")

    active_cases = {"calibration", "compliance", "constant-force", "contact-detection", "all-safe"}
    needs_prepare = args.case in active_cases

    with CodroidControlInterface(host=args.robot) as robot:
        if needs_prepare:
            prepare_robot(robot, args.skip_power)
        try:
            if args.case == "state":
                run_state(robot, args)
            elif args.case == "calibration":
                run_calibration(robot, args)
            elif args.case == "safety-config":
                run_safety_config(robot, args)
            elif args.case == "compliance":
                run_compliance(robot, args)
            elif args.case == "constant-force":
                run_constant_force(robot, args)
            elif args.case == "contact-detection":
                run_contact_detection(robot, args)
            elif args.case == "all-safe":
                run_state(robot, args)
                run_calibration(robot, args)
                run_safety_config(robot, args)
                run_compliance(robot, args)
            else:
                raise RuntimeError(f"unsupported case: {args.case}")
        except KeyboardInterrupt:
            print("\n用户中断，执行收尾...")
            return 130
        except Exception:
            print("\n测试异常，执行收尾...")
            raise
        finally:
            if needs_prepare and args.case not in {"state", "safety-config"}:
                stop_and_power_off(robot, args.skip_power)

    print("测试完成")
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
