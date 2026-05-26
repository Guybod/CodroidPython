#!/usr/bin/env python3
"""
示例 01 — 最简联调流程（连接 → 远程 → 使能 → movJ → CRI 打印）

【目的】
  演示 SDK 2.1+ 最小闭环：TCP 控制 + CRI 实时缓存读取。

【前置条件】
  - 控制器与 PC 同网段，TCP 9001 可达
  - 本机 UDP 端口（默认 18888）未被占用，且防火墙放行
  - 机器人可远程控制、允许上使能

【涉及协议】
  - TCP：模式切换、使能、Robot/move（movJ）、CRI/StartDataPush / StopDataPush
  - UDP：308 字节 CRI 推送（解析后为 mm + 度，见 AGENTS.md §2.3）

【运行】
  PYTHONPATH=src python examples/01_basic_usage.py
  PYTHONPATH=src python examples/01_basic_usage.py --robot 192.168.8.136

【注意】
  - 会实际运动机器人，请在安全空间内运行
  - ``JointPoint.Degrees`` 表示六轴关节角（度），勿与 TCP 位姿混用
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, InitConsoleUtf8, JointPoint, PrintBanner


def main(argv: list[str]) -> int:
    # ---------- 命令行：现场改 IP / 本机 CRI 绑定 ----------
    p = argparse.ArgumentParser(description="Basic connect, moveJ, CRI cache")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="本机 IP（CRI 推送目标）")
    p.add_argument(
        "--udp-port",
        type=int,
        default=18888,
        help="本机 UDP 端口（建议 10000–65534）",
    )
    args = p.parse_args(argv)

    PrintBanner("01 — Basic usage", subtitle=f"{args.robot}  CRI → {args.local_ip}:{args.udp_port}")

    # with 退出时自动 Disconnect，避免 TCP/UDP 泄漏
    with CodroidControlInterface(
        host=args.robot,
        local_ip=args.local_ip,
        udp_port=args.udp_port,
    ) as robot:
        # 典型上电顺序：先自动再远程（与 C# ConnectRemoteAndSwitchOn 子步骤一致）
        robot.enter_remote_mode_via_auto()
        robot.switch_on()

        # 后台线程收 CRI UDP，结果写入 robot.cri_cache（线程安全快照）
        robot._start_cri_receiver()
        robot.start_cri_data_push(ip=args.local_ip, port=args.udp_port)

        try:
            # 类型化目标：明确是「关节角」而非 TCP
            p1 = JointPoint.Degrees([0, 0, 90, 0, 90, 0])
            p2 = JointPoint.Degrees([0, 0, 0, 0, 0, 0])
            for _ in range(3):
                # MovJ(target, speed, acceleration)；单位：度、%/s 等按控制器约定
                robot.MovJ(p1, 60, 120)
                robot.MovJ(p2, 60, 120)

            PrintBanner("CRI cache loop", subtitle="Ctrl+C 退出")
            while True:
                data = robot.cri_cache
                if data:
                    # joint_pos / is_moving 来自 CRI 解析（已是度、mm 等对外单位）
                    print(f"关节角 / joint_pos: {data.joint_pos}")
                    print(f"运动中 / is_moving: {data.status.is_moving}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("已中断 / Interrupted", file=sys.stderr)
            return 130
        finally:
            # 停止推送，释放控制器侧推送任务
            robot.stop_cri_data_push(ip=args.local_ip, port=args.udp_port)

    return 0


if __name__ == "__main__":
    # Windows cmd 下中文不乱码；Linux 为 no-op
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
