#!/usr/bin/env python3
"""
CRI 实时控制联调 — 对齐 C# ``CodroidCRITest``（AGENTS.md §5.2 / §6）

【模式】
  joint  关节空间 Cubic 轨迹，三点（度）
  cart   笛卡尔 YZ 矩形平移，姿态保持，Trapezoidal
  path   四点位姿 + 回 home，Trapezoidal
  all    依次执行 joint → cart → path

【标准流程（每段）】
  1. Connect → 远程 → 使能
  2. StartCriDataPush → 等首帧 CRI（起点）
  3. 离线 TrajectoryGenerator 生成轨迹（mm+deg）
  4. StartCriControl（filter=1, duration=4ms, buffer=5）
  5. 等 RealTimeControlMode
  6. CriRealtimeDispatcher 按 period_ms 发 64 字节 CommandData（线上 m/rad）
  7. finally：StopCriControl、StopCriDataPush

【运行】
  PYTHONPATH=src python examples/codroid_cri_test.py --mode joint
  PYTHONPATH=src python examples/codroid_cri_test.py --robot 192.168.8.136

【注意】
  - 每段前有 3 秒倒计时，Ctrl+C 仍会走 finally 停控
  - 现场务必修改 --robot / --local-ip / --local-port
  - 本示例不走 Robot/move，与 08_move 的 TCP 运动 API 不同
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import (
    CriFilterType,
    CodroidClient,
    CriRealtimeDispatcher,
    InitConsoleUtf8,
    PrintBanner,
    TrajectoryGenerator,
    TrajectoryProfile,
    TrajectoryRequest,
    TrajectorySpace,
)


def _countdown(seconds: int = 3) -> None:
    """段开始前倒计时，便于现场撤离示教空间。"""
    for i in range(seconds, 0, -1):
        print(f"倒计时 {i} 秒… / Countdown {i}s…", flush=True)
        time.sleep(1.0)


def _wait_cri(robot: CodroidClient, timeout: float = 15.0):
    """等待首帧有效 CRI（timestamp>0），作为轨迹起点。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        d = robot.cri_cache
        if d is not None and getattr(d, "timestamp", 0) > 0:
            return d
        time.sleep(0.05)
    raise TimeoutError("等待首帧 CRI 超时 / Timeout waiting for first CRI frame")


def _wait_rt_control(robot: CodroidClient, timeout: float = 5.0) -> None:
    """StartCriControl 后须 status.rt_control_mode == True 再发 UDP 指令。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        d = robot.cri_cache
        if d is not None and d.status.rt_control_mode:
            return
        time.sleep(0.05)
    raise TimeoutError("等待 RealTimeControlMode 超时 / Timeout waiting for rt_control_mode")


def run_joint(robot_ip: str, local_ip: str, local_port: int) -> None:
    """
    §5.2 joint 段：30 deg/s Cubic，路点含当前关节 + P1/P2/P3。
    """
    freq = 250.0  # 1000 / durationMs(4)
    period_ms = 4
    req = TrajectoryRequest(
        space=TrajectorySpace.JOINT,
        frequency_hz=freq,
        profile=TrajectoryProfile.CUBIC,
        acceleration=120.0,
        speed=30.0,
    )
    p1 = [0.0, 0.0, 90.0, 0.0, 90.0, 0.0]
    p2 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    p3 = [0.0, 0.0, 90.0, 0.0, 90.0, 0.0]

    with CodroidClient(host=robot_ip, local_ip=local_ip, udp_port=local_port) as robot:
        robot.EnterRemoteModeViaAuto()
        robot.SwitchOn()
        robot._start_cri_receiver()
        robot.StartCriDataPush(ip=local_ip, port=local_port)
        cri = _wait_cri(robot)
        start_j = list(cri.joint_pos)
        waypoints = [start_j, p1, p2, p3]
        traj = []
        for i in range(len(waypoints) - 1):
            seg = TrajectoryGenerator.generate(waypoints[i], waypoints[i + 1], req)
            for k, pt in enumerate(seg):
                if i > 0 and k == 0:
                    continue  # 多段拼接跳过重复点
                traj.append(pt)

        _countdown(3)
        robot.StartCriControl(
            filter_type=CriFilterType.AVERAGE,
            duration=period_ms,
            start_buffer=5,
        )
        _wait_rt_control(robot)
        try:
            with CriRealtimeDispatcher(robot_ip) as disp:
                disp.SendTrajectory(traj, TrajectorySpace.JOINT, period_ms)
        finally:
            robot.StopCriControl()
            robot.StopCriDataPush(ip=local_ip, port=local_port)


def run_cart(robot_ip: str, local_ip: str, local_port: int) -> None:
    """
    §5.2 cart 段：相对 TCP 偏移矩形，rx/ry/rz 保持起点，80 mm/s Trapezoidal。
    """
    freq = 250.0
    period_ms = 4
    req = TrajectoryRequest(
        space=TrajectorySpace.CARTESIAN,
        frequency_hz=freq,
        profile=TrajectoryProfile.TRAPEZOIDAL,
        acceleration=400.0,
        speed=80.0,
    )

    with CodroidClient(host=robot_ip, local_ip=local_ip, udp_port=local_port) as robot:
        robot.EnterRemoteModeViaAuto()
        robot.SwitchOn()
        robot._start_cri_receiver()
        robot.StartCriDataPush(ip=local_ip, port=local_port)
        cri = _wait_cri(robot)
        tcp = list(cri.cartesian_pos)
        if len(tcp) < 6:
            raise RuntimeError("CRI TcpPose 无效 / invalid cartesian_pos")

        def add_xyz(base, dx, dy, dz):
            return [
                base[0] + dx,
                base[1] + dy,
                base[2] + dz,
                base[3],
                base[4],
                base[5],
            ]

        p0 = tcp
        p1 = add_xyz(p0, 0, 0, -200)
        p2 = add_xyz(p1, 0, -200, 0)
        p3 = add_xyz(p2, 0, 0, 200)
        p4 = add_xyz(p3, 0, 200, 0)

        traj = TrajectoryGenerator.generate_multi_segment([p0, p1, p2, p3, p4], req)

        _countdown(3)
        robot.StartCriControl(
            filter_type=CriFilterType.AVERAGE,
            duration=period_ms,
            start_buffer=5,
        )
        _wait_rt_control(robot)
        try:
            with CriRealtimeDispatcher(robot_ip) as disp:
                disp.SendTrajectory(traj, TrajectorySpace.CARTESIAN, period_ms)
        finally:
            robot.StopCriControl()
            robot.StopCriDataPush(ip=local_ip, port=local_port)


def run_path(robot_ip: str, local_ip: str, local_port: int) -> None:
    """
    §5.2 path 段：固定四点位姿（mm+deg）+ 回 home，起点为当前 TCP。
    """
    freq = 250.0
    period_ms = 4
    req = TrajectoryRequest(
        space=TrajectorySpace.CARTESIAN,
        frequency_hz=freq,
        profile=TrajectoryProfile.TRAPEZOIDAL,
        acceleration=400.0,
        speed=80.0,
    )
    p1 = [1139.996, 214.490, 899.010, -91.506, -0.001, -89.999]
    p2 = [1139.994, -222.730, 899.022, -91.506, -0.002, -136.466]
    p3 = [915.480, -73.000, 599.316, 166.910, -5.170, -90.726]
    p4 = [927.505, 214.495, 898.994, 180.000, 0.000, -90.000]

    with CodroidClient(host=robot_ip, local_ip=local_ip, udp_port=local_port) as robot:
        robot.EnterRemoteModeViaAuto()
        robot.SwitchOn()
        robot._start_cri_receiver()
        robot.StartCriDataPush(ip=local_ip, port=local_port)
        cri = _wait_cri(robot)
        start_tcp = list(cri.cartesian_pos)
        if len(start_tcp) < 6:
            raise RuntimeError("CRI TcpPose 无效 / invalid cartesian_pos")

        traj = TrajectoryGenerator.generate_multi_segment(
            [start_tcp, p1, p2, p3, p4], req
        )

        _countdown(3)
        robot.StartCriControl(
            filter_type=CriFilterType.AVERAGE,
            duration=period_ms,
            start_buffer=5,
        )
        _wait_rt_control(robot)
        try:
            with CriRealtimeDispatcher(robot_ip) as disp:
                disp.SendTrajectory(traj, TrajectorySpace.CARTESIAN, period_ms)
        finally:
            robot.StopCriControl()
            robot.StopCriDataPush(ip=local_ip, port=local_port)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Codroid CRI realtime test (AGENTS.md §5.2)")
    p.add_argument(
        "--mode",
        choices=("all", "joint", "cart", "path"),
        default="all",
        help="测试段；默认 all 依次执行 joint、cart、path / segment; default runs all",
    )
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP / robot IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机 IP（StartCriDataPush）")
    p.add_argument(
        "--local-port",
        type=int,
        default=18888,
        help="本机 UDP 端口（须 10000–65534）",
    )
    args = p.parse_args(argv)

    if not (10000 <= args.local_port <= 65534):
        print("local-port 须在 10000–65534", file=sys.stderr)
        return 2

    modes = (
        ("joint", "cart", "path")
        if args.mode == "all"
        else (args.mode,)
    )
    try:
        for name in modes:
            PrintBanner(f"CRI test: {name}")
            if name == "joint":
                run_joint(args.robot, args.local_ip, args.local_port)
            elif name == "cart":
                run_cart(args.robot, args.local_ip, args.local_port)
            else:
                run_path(args.robot, args.local_ip, args.local_port)
            PrintBanner(f"CRI test done: {name}")
            print(flush=True)
    except KeyboardInterrupt:
        print("已中断 / Interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"失败 / Failed: {e}", file=sys.stderr)
        return 1
    print("全部完成 / All done")
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
