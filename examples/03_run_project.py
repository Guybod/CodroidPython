#!/usr/bin/env python3
"""
示例 03 — 工程运行控制（运行 / 暂停 / 恢复 / 停止 / 按索引启动）

【目的】
  演示与示教器工程相关的 TCP 指令序列，便于集成 MES/上位机调度。

【前置条件】
  - 控制器内存在对应工程（--project-id 默认 projectluademo）
  - 远程模式

【涉及协议】
  - project/run、pause、resume、stop、runByIndex 等（见 PROTOCOL_LINE_BY_LINE.md）

【运行】
  PYTHONPATH=src python examples/03_run_project.py --robot <IP>

【注意】
  - 每步之间有 --step-sleep 间隔，便于观察示教器状态
  - 不传工程名时 run_project 可能失败，请按现场修改 --project-id
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, InitConsoleUtf8, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Run / pause / resume / stop project")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument(
        "--project-id",
        default="projectluademo",
        help="工程 ID（run_project）",
    )
    p.add_argument("--index", type=int, default=0, help="run_project_by_index 索引")
    p.add_argument("--step-sleep", type=float, default=5.0, help="每步间隔（秒）")
    args = p.parse_args(argv)

    PrintBanner("03 — Run project", subtitle=f"{args.robot}  proj={args.project_id}")

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.enter_remote_mode_via_auto()

            # 按工程名启动
            res = robot.run_project(args.project_id)
            print("运行 / run:", "ok" if res.is_success else res.err)
            time.sleep(args.step_sleep)

            res = robot.pause_project()
            print("暂停 / pause:", "ok" if res.is_success else res.err)
            time.sleep(args.step_sleep)

            res = robot.resume_project()
            print("恢复 / resume:", "ok" if res.is_success else res.err)
            time.sleep(args.step_sleep)

            res = robot.stop_project()
            print("停止 / stop:", "ok" if res.is_success else res.err)
            time.sleep(args.step_sleep)

            # 按索引启动（与示教器工程列表顺序相关）
            res = robot.run_project_by_index(args.index)
            print("按索引启动 / by_index:", "ok" if res.is_success else res.err)
            time.sleep(args.step_sleep)

            res = robot.stop_project()
            print("再次停止 / stop:", "ok" if res.is_success else res.err)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
