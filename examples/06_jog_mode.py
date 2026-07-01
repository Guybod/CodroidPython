#!/usr/bin/env python3
"""
示例 06 — 点动（Jog）与心跳线程

【目的】
  演示手动点动：设置倍率 → 启动关节点动 → 周期 jogHeartbeat → stopJog。

【前置条件】
  - 已使能、手动/远程模式允许点动
  - 点动期间必须持续发心跳，否则控制器会超时停止

【涉及协议】
  - Robot/setManualMoveRate、Robot/jog、Robot/jogHeartbeat、Robot/stopJog

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/06_jog_mode.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/06_jog_mode.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\06_jog_mode.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/06_jog_mode.py --robot 192.168.8.136

【注意】
  - speed 为 -1.0~1.0 的比例，负值表示反向
  - index 为关节索引（示例为关节 1）
  - 心跳间隔建议 ≤500ms，本示例约 400ms
"""
from __future__ import annotations

import argparse
import sys
import threading
import time

from codroid import CodroidControlInterface, InitConsoleUtf8, JogMode, PrintBanner


def start_heartbeat(
    robot: CodroidControlInterface,
    stop_event: threading.Event,
    interval: float = 0.4,
) -> None:
    """后台线程：在点动保持期间周期调用 jog_heartbeat。"""
    while not stop_event.is_set():
        try:
            robot.JogHeartbeat()
            time.sleep(interval)
        except Exception:
            # 连接断开或已 stop 时退出线程
            break


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Jog mode + heartbeat thread")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--duration", type=float, default=2.0, help="点动持续时间（秒）")
    args = p.parse_args(argv)

    PrintBanner("06 — Jog mode", subtitle=args.robot)

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()
            robot.SwitchOn()
            # 手动模式运动倍率 1~100（百分比）
            robot.SetManualMoveRate(50)

            stop_heartbeat = threading.Event()
            heartbeat_thread = threading.Thread(
                target=start_heartbeat,
                args=(robot, stop_heartbeat),
                daemon=True,
            )

            print("关节 1 点动（示例速度）/ Jog joint 1...")
            # JogMode.JOINT + index + speed（比例）
            robot.StartJog(mode=JogMode.JOINT, index=1, speed=-0.5)
            heartbeat_thread.start()
            time.sleep(args.duration)

            print("停止点动 / Stop jog")
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=2.0)
            robot.StopJog()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
