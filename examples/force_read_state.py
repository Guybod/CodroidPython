#!/usr/bin/env python3
"""
力控状态轮询示例

只获取传感器状态并打印，每秒轮询一次，Ctrl+C 退出。

【运行】
  PYTHONPATH=src python3 examples/force_read_state.py
  PYTHONPATH=src python3 examples/force_read_state.py 192.168.1.136
"""
from __future__ import annotations

import sys
import time

from codroid import (
    CodroidControlInterface,
    ForceHealth,
    InitConsoleUtf8,
)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.136"

    with CodroidControlInterface(host=host) as robot:
        print(f"已连接 {host}，每秒轮询力控状态，Ctrl+C 退出\n")

        try:
            while True:
                state = robot.GetForceState()

                def fmt6(arr, prec=2):
                    """安全格式化 6 元素列表，不足补零。"""
                    v = list(arr) + [0.0] * 6
                    return f"[{v[0]:7.{prec}f}, {v[1]:7.{prec}f}, {v[2]:7.{prec}f}, {v[3]:7.{prec}f}, {v[4]:7.{prec}f}, {v[5]:7.{prec}f}]"

                print(f"力控启用: {state.enabled}  |  数据有效: {state.valid}  |  健康: {ForceHealth(state.health).name}")
                print(f"  TCP 外力:  {fmt6(state.wrench_tcp)}")
                print(f"  基座外力:  {fmt6(state.wrench_base)}")
                print(f"  期望力:    {fmt6(state.desired_wrench)}")
                print(f"  跟踪误差:  {fmt6(state.track_error, 4)}")
                print(f"  接触: {state.is_contact}  |  过力: {state.is_overforce}")
                print()

                time.sleep(1)
        except KeyboardInterrupt:
            print("\n已退出")


if __name__ == "__main__":
    InitConsoleUtf8()
    main()
