#!/usr/bin/env python3
"""
CRI UDP 原始流：本机 ``CriStreamHandler`` 绑定端口，控制器 ``StartCriDataPush`` 后 recv 解析。

数据布局与掩码须与控制器一致；固定 308 字节布局见 AGENTS.md §2.3。

用法:
  PYTHONPATH=src python examples/13_cri_realtime.py
  PYTHONPATH=src python examples/13_cri_realtime.py --robot 192.168.8.136 --local-ip 192.168.8.150

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import (
    CodroidControlInterface,
    CriMask,
    CriStreamHandler,
    PrintBanner,
)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="CRI UDP stream parse demo")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机绑定/推送目标 IP")
    p.add_argument("--local-port", type=int, default=18888, help="本机 UDP 端口")
    p.add_argument("--frames", type=int, default=10, help="接收并打印的帧数")
    p.add_argument("--duration", type=int, default=10, help="StartDataPush duration（协议字段）")
    args = p.parse_args(argv)

    PrintBanner(
        "13 — CRI realtime (UDP)",
        subtitle=f"{args.robot} → {args.local_ip}:{args.local_port}",
    )

    my_mask = CriMask.TIMESTAMP | CriMask.STATUS_1 | CriMask.JOINT_POS
    handler = CriStreamHandler(high_precision=False, mask=my_mask)
    try:
        handler.bind(args.local_port)
    except OSError as e:
        print(f"绑定端口失败 / bind failed: {e}", file=sys.stderr)
        return 2

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()
            res = robot.start_cri_data_push(
                ip=args.local_ip,
                port=args.local_port,
                duration=args.duration,
                mask=my_mask,
            )
            print("start_cri_data_push:", res)
            print("接收实时数据 / Receiving...")

            try:
                for _ in range(args.frames):
                    try:
                        data, _addr = handler._sock.recvfrom(2048)
                    except OSError as e:
                        print(f"recv: {e}", file=sys.stderr)
                        break
                    parsed = handler.parse_packet(data)
                    print("-" * 72)
                    print(
                        f"时间戳 / ts: {parsed.timestamp}, "
                        f"末端线速度 / tcp_speed: {parsed.tcp_speed}"
                    )
                    print(
                        f"关节位置 / joint_pos: {parsed.joint_pos}, "
                        f"关节速度 / joint_vel: {parsed.joint_vel}"
                    )
                    print(f"末端位姿 / cartesian_pos: {parsed.cartesian_pos}")
                    st = parsed.status
                    flags = []
                    if st.project_running:
                        flags.append("工程运行")
                    if st.project_paused:
                        flags.append("暂停")
                    if st.project_stopped:
                        flags.append("停止")
                    if st.is_enabling:
                        flags.append("使能中")
                    if st.is_disabled:
                        flags.append("未使能")
                    if st.is_manual:
                        flags.append("手动")
                    if st.is_dragging:
                        flags.append("拖动")
                    if st.is_moving:
                        flags.append("运动中")
                    if st.collision_stop:
                        flags.append("碰撞停")
                    if st.is_at_safe_pos:
                        flags.append("安全位")
                    if st.has_alarm:
                        flags.append("报警")
                    if st.is_simulation:
                        flags.append("仿真")
                    if st.is_emergency_stop:
                        flags.append("急停")
                    if st.is_rescue:
                        flags.append("救援")
                    if st.is_auto:
                        flags.append("自动")
                    if st.is_remote:
                        flags.append("远程")
                    if st.rt_control_mode:
                        flags.append("实时控制")
                    if flags:
                        print("状态 / status:", ", ".join(flags))
                    time.sleep(0.05)
            finally:
                robot.stop_cri_data_push(ip=args.local_ip, port=args.local_port)
    except KeyboardInterrupt:
        return 130
    finally:
        try:
            handler._sock.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
