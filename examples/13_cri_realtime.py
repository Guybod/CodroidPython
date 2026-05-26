#!/usr/bin/env python3
"""
示例 13 — CRI UDP 底层收包与解析（CriStreamHandler）

【目的】
  不依赖 CodroidSession 内置 CRI 线程，直接绑定 UDP、收包、``parse_packet``。
  便于理解 308 字节布局与掩码字段。

【前置条件】
  - TCP 可连；本机端口可 bind
  - StartCriDataPush 的 mask/duration 与 handler 配置一致

【数据格式】
  - 固定 308 字节（六轴、mask=0xFFFF、高精度策略见 AGENTS.md §2.3）
  - 解析后 joint_pos 等为 **mm + 度**（非线上 m/rad）

【运行】
  PYTHONPATH=src python examples/13_cri_realtime.py --robot <IP> --local-ip <IP>

【注意】
  - 示例直接访问 handler._sock，仅用于演示；生产环境可用公开 API 封装
  - high_precision=False 时须与 start_cri_data_push 参数一致
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import (
    CodroidControlInterface,
    CriMask,
    CriStreamHandler,
    InitConsoleUtf8,
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

    # 订阅字段掩码：决定 UDP 包内包含哪些段（与 push 请求 mask 一致）
    my_mask = CriMask.TIMESTAMP | CriMask.STATUS_1 | CriMask.JOINT_POS
    handler = CriStreamHandler(high_precision=False, mask=my_mask)
    try:
        handler.bind(args.local_port)
    except OSError as e:
        print(f"绑定端口失败 / bind failed: {e}", file=sys.stderr)
        return 2

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()
            res = robot.StartCriDataPush(
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
                robot.StopCriDataPush(ip=args.local_ip, port=args.local_port)
    except KeyboardInterrupt:
        return 130
    finally:
        try:
            handler._sock.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
