#!/usr/bin/env python3
"""
示例 14 — 机器人设置参数（协议 19.2~19.7）

【目的】
  演示与 C# ``CodroidTest robotparam``、C++ ``06_robot_parameters.cpp`` 对齐的 API：
  - ``GetRobotParameters``（19.7）
  - ``SetToolFrame`` / ``SetPayloadFrame`` / ``SetUserCoordinateFrame``（先 Get 再 patch，仅 1~15）
  - ``SetDefaultToolId`` 等仅改默认编号（0~15，无需先 Get）
  - 校验 id=0 不可通过 ``Set*Frame`` 写入

【前置条件】
  - TCP 已连控制器（端口 9001）
  - 固件建议 ≥ 2.3.3.43（与 C++ SDK 说明一致）
  - 确认现场无其它程序占用 Tool[2] 等演示槽位

【涉及协议】
  - ``Robot/GetRobotParameter`` → ``RobotParameters``
  - ``Robot/SaveRobotParameter``（默认编号、整表或单槽合并后下发）
  - 本示例**不**调用 ``SetCollisionSensitivity`` / ``SetPayload``，避免改变碰撞灵敏度与当前负载编号

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/14_robot_parameters.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/14_robot_parameters.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\14_robot_parameters.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/14_robot_parameters.py --robot 192.168.8.136
    python examples/14_robot_parameters.py --robot 192.168.8.136 --no-restore

【注意】
  - ``SetPayload``（``Robot/setPayload``）与 ``SetPayloadFrame``（负载表）不同，勿混淆
  - Tool[0] / Payload[0] / Coordinate[0] 在控制器侧为只读全零，SDK 拒绝 ``Set*Frame(0, ...)``
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from codroid import (
    CodroidControlInterface,
    InitConsoleUtf8,
    PrintBanner,
    RobotFrame,
    RobotParameters,
)
from codroid.exceptions import CodroidError


def _find_tool(frames: Sequence[RobotFrame], frame_id: int) -> Optional[RobotFrame]:
    for f in frames:
        if f.id == frame_id:
            return f
    return None


def _print_summary(label: str, p: RobotParameters) -> None:
    """打印默认编号与表长度；若有 Tool[2] 则打印其位姿。"""
    print(f"--- {label} ---")
    print(
        f"  defaultToolId={p.default_tool_id}, "
        f"defaultPayloadId={p.default_payload_id}, "
        f"defaultCoordinateId={p.default_coordinate_id}, "
        f"maxPayload={p.max_payload}"
    )
    print(
        f"  Tool={len(p.tool)}, Payload={len(p.payload)}, "
        f"Coordinate={len(p.coordinate)}"
    )
    t0 = _find_tool(p.tool, 0)
    if t0 is not None:
        print(f"  Tool[0]（只读基准）: x={t0.x}, y={t0.y}, z={t0.z}")
    t2 = _find_tool(p.tool, 2)
    if t2 is not None:
        print(
            f"  Tool[2]: x={t2.x}, y={t2.y}, z={t2.z}, "
            f"a={t2.a}, b={t2.b}, c={t2.c}"
        )


def run_robot_parameters_demo(
    robot: CodroidControlInterface,
    *,
    demo_tool_id: int = 2,
    restore: bool = True,
) -> None:
    """
    与 C# ``RunRobotParameterTest`` 相同步骤；``restore=True`` 时恢复 Tool 槽位原值。
    """
    # --- 步骤 1：读取完整设置界面快照（19.7）---
    print("\n[1] GetRobotParameters")
    before = robot.GetRobotParameters()
    _print_summary("初始参数", before)

    orig_tool = _find_tool(before.tool, demo_tool_id)
    if orig_tool is None:
        raise CodroidError(f"控制器 Tool 表中未找到 id={demo_tool_id}。")

    # --- 步骤 2：id=0 不可写（19.4 约束）---
    print(f"\n[2] SetToolFrame(0) 应被 SDK 拒绝")
    try:
        robot.SetToolFrame(
            0,
            RobotFrame(id=0, x=1, y=0, z=0, a=0, b=0, c=0),
        )
        print("  错误：SetToolFrame(0) 未抛异常。", file=sys.stderr)
        raise SystemExit(1)
    except CodroidError as ex:
        print(f"  已拒绝（符合预期）: {ex}")

    # --- 步骤 3：修改单个工具坐标系（协议文档示例 x=15, y=20）---
    print(f"\n[3] SetToolFrame({demo_tool_id}) — 与 C# CodroidTest 一致")
    demo_frame = RobotFrame(
        id=demo_tool_id,
        x=15.0,
        y=20.0,
        z=orig_tool.z,
        a=orig_tool.a,
        b=orig_tool.b,
        c=orig_tool.c,
    )
    res = robot.SetToolFrame(demo_tool_id, demo_frame)
    if not res.is_success:
        raise CodroidError(f"SetToolFrame 失败: {res.err}")
    print("  已下发 Tool[2] x=15 y=20")

    after_tool = robot.GetRobotParameters()
    t2 = _find_tool(after_tool.tool, demo_tool_id)
    if t2:
        print(f"  读回 Tool[{demo_tool_id}]: x={t2.x}, y={t2.y}, z={t2.z}")
    t0 = _find_tool(after_tool.tool, 0)
    if t0:
        print(f"  Tool[0] 仍为: x={t0.x}, y={t0.y}（须保持全零）")

    # --- 步骤 4：仅改默认工具编号（19.3，0~15，无需先 Get）---
    print(f"\n[4] SetDefaultToolId({demo_tool_id})")
    res_def = robot.SetDefaultToolId(demo_tool_id)
    if not res_def.is_success:
        raise CodroidError(f"SetDefaultToolId 失败: {res_def.err}")
    p_def = robot.GetRobotParameters()
    print(f"  读回 defaultToolId={p_def.default_tool_id}")

    if restore:
        print(f"\n[恢复] SetToolFrame({demo_tool_id}) 写回原值")
        robot.SetToolFrame(demo_tool_id, orig_tool)
        # 默认编号是否恢复由现场决定；此处仅恢复 Tool 数值
        print("  Tool 槽位已恢复；defaultToolId 未自动改回，请按需手动设置。")

    print("\n提示: 未调用 SetCollisionSensitivity / SetPayload，避免影响现场运行。")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        description="Robot settings 19.x demo (Get/SaveRobotParameter)"
    )
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument(
        "--demo-tool-id",
        type=int,
        default=2,
        help="演示修改的工具坐标系编号（1~15）",
    )
    p.add_argument(
        "--no-restore",
        action="store_true",
        help="演示结束后不恢复 Tool 槽位原值",
    )
    p.add_argument("--debug", action="store_true", help="打印 JSON 请求/响应")
    args = p.parse_args(argv)

    if not (1 <= args.demo_tool_id <= 15):
        print("--demo-tool-id 须在 1~15", file=sys.stderr)
        return 2

    PrintBanner("14 — Robot parameters (19.x)", subtitle=args.robot)
    print(
        "  将修改 Tool[{}] 并 SetDefaultToolId({})；"
        "确认无冲突后再跑。".format(args.demo_tool_id, args.demo_tool_id)
    )

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.debug = args.debug
            # 机器人设置接口不强制远程/使能，但多数现场习惯先切远程
            robot.EnterRemoteModeViaAuto()
            run_robot_parameters_demo(
                robot,
                demo_tool_id=args.demo_tool_id,
                restore=not args.no_restore,
            )
    except KeyboardInterrupt:
        return 130
    except CodroidError as ex:
        print(f"失败: {ex}", file=sys.stderr)
        return 1
    except Exception as ex:
        print(f"异常: {ex}", file=sys.stderr)
        return 1

    PrintBanner("14 — 完成", subtitle="robot parameters demo")
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
