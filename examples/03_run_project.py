#!/usr/bin/env python3
"""
工程控制：运行、暂停、恢复、停止、按索引启动。

用法:
  PYTHONPATH=src python examples/03_run_project.py
  PYTHONPATH=src python examples/03_run_project.py --robot 192.168.8.136

彩色横幅（可选）: pip install codroid-robot-sdk[color] 或 pip install colorama
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import CodroidControlInterface, PrintBanner


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

            res = robot.run_project_by_index(args.index)
            print("按索引启动 / by_index:", "ok" if res.is_success else res.err)
            time.sleep(args.step_sleep)

            res = robot.stop_project()
            print("再次停止 / stop:", "ok" if res.is_success else res.err)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
