#!/usr/bin/env python3
"""
聚合联调脚本 — 对齐 C# ``CodroidTest/Program.cs``

【子命令】
  global      全局变量读/写
  kin         正逆解（aposToCpos / cposToApos）
  io          读 DI0
  register    寄存器三组读写（地址与数值见 AGENTS.md §5.1）
  robotstatus 订阅 publish/RobotStatus
  cri         CRI 收首帧烟测
  motion      三段 movJ（关节）
  s20         S20 movJ 三点 + movL 四点（需 CRI 快照作 MmDegWithRef）

【运行】
  PYTHONPATH=src python examples/codroid_test.py              # 等同 all，依次全跑
  PYTHONPATH=src python examples/codroid_test.py motion
  PYTHONPATH=src python examples/codroid_test.py s20 --robot 192.168.8.136

【注意】
  - ``all`` 会运动机器人且耗时 long，建议分项调试
  - s20 / motion 使用 2.1+ ``JointPoint`` / ``CartesianPoint`` / ``MovJ`` / ``MovL``
"""
from __future__ import annotations

import argparse
import sys
import time

from codroid import (
    CartesianPoint,
    CodroidClient,
    GlobalVariable,
    InitConsoleUtf8,
    JointPoint,
    PrintBanner,
    PublishNotification,
    PublishTopics,
)

# 与 C# CodroidTest 子例顺序一致
ALL_CMDS = (
    "global",
    "kin",
    "io",
    "register",
    "robotstatus",
    "cri",
    "motion",
    "s20",
)


def cmd_global(robot_ip: str) -> None:
    """globalVar：读全表 → 写入 sdk_demo_py → 再读验证。"""
    with CodroidClient(host=robot_ip) as robot:
        robot.enter_remote_mode_via_auto()
        res = robot.get_global_vars()
        print("get_global_vars:", res.db)
        robot.save_global_vars(
            {"sdk_demo_py": GlobalVariable(value=42, note="codroid_test")}
        )
        res2 = robot.get_global_vars()
        print("after save:", res2.db)


def cmd_kin(robot_ip: str) -> None:
    """运动学：关节角 → TCP；TCP+参考关节 → 关节角。"""
    with CodroidClient(host=robot_ip) as robot:
        robot.enter_remote_mode_via_auto()
        fk = robot.apos_to_cpos([0, 0, 90, 0, 90, 0])
        print("FK:", fk.db)
        ik = robot.cpos_to_apos(
            [500.0, 200.0, 400.0, 180.0, 0.0, -90.0],
            rj=[0, 0, 90, 0, 90, 0],
        )
        print("IK:", ik.db)


def cmd_io(robot_ip: str) -> None:
    """读数字输入 DI0。"""
    with CodroidClient(host=robot_ip) as robot:
        robot.enter_remote_mode_via_auto()
        try:
            v = robot.get_di(0)
            print("DI0:", v)
        except Exception as e:
            print("get_di:", e)


def _register_group_a(robot: CodroidClient) -> None:
    """§5.1 组 A：9032–9035 写 1 再清零。"""
    addrs = [9032, 9033, 9034, 9035]
    print("A read:", robot.get_register_values(addrs).db)
    for a in addrs:
        robot.set_register_value(a, 1)
    for a in addrs:
        print("A after write", a, robot.get_register(a))
    for a in addrs:
        robot.set_register_value(a, 0)


def _register_group_b(robot: CodroidClient) -> None:
    """§5.1 组 B：整型寄存器写 520。"""
    addrs = [49100, 49102, 49104]
    print("B read:", robot.get_register_values(addrs).db)
    for a in addrs:
        robot.set_register_value(a, 520)
    for a in addrs:
        print("B after write", a, robot.get_register(a))
    for a in addrs:
        robot.set_register_value(a, 0)


def _register_group_c(robot: CodroidClient) -> None:
    """§5.1 组 C：浮点寄存器写 520.52。"""
    addrs = [49300, 49302, 49304]
    print("C read:", robot.get_register_values(addrs).db)
    for a in addrs:
        robot.set_register_value(a, 520.52)
    for a in addrs:
        print("C after write", a, robot.get_register(a))
    for a in addrs:
        robot.set_register_value(a, 0.0)


def cmd_register(robot_ip: str) -> None:
    with CodroidClient(host=robot_ip) as robot:
        robot.enter_remote_mode_via_auto()
        _register_group_a(robot)
        _register_group_b(robot)
        _register_group_c(robot)


def cmd_robotstatus(robot_ip: str) -> None:
    """主题推送：首次订阅时向控制器发送 {ty, tc}。"""
    with CodroidClient(host=robot_ip) as robot:
        robot.enter_remote_mode_via_auto()

        def on_msg(n: PublishNotification) -> None:
            print("[RobotStatus]", n.ty, n.db)

        sub = robot.SubscribePublishTopic(
            PublishTopics.ROBOT_STATUS, on_msg, tc_milliseconds=100
        )
        try:
            time.sleep(3.0)
        finally:
            sub.dispose()  # 本地退订；不向控制器发退订帧


def cmd_cri(robot_ip: str, local_ip: str, local_port: int) -> None:
    """CRI：启动推送，等待 timestamp>0 的首帧。"""
    with CodroidClient(host=robot_ip, local_ip=local_ip, udp_port=local_port) as robot:
        robot.enter_remote_mode_via_auto()
        robot.switch_on()
        robot._start_cri_receiver()
        robot.start_cri_data_push(ip=local_ip, port=local_port)
        deadline = time.time() + 10.0
        while time.time() < deadline:
            d = robot.cri_cache
            if d and d.timestamp > 0:
                print("CRI timestamp", d.timestamp, "joint", d.joint_pos[:3], "...")
                break
            time.sleep(0.1)
        else:
            print("No CRI frame within timeout")
        robot.stop_cri_data_push(ip=local_ip, port=local_port)


def cmd_motion(robot_ip: str) -> None:
    """§5.1 movJ 三段关节目标（度）。"""
    with CodroidClient(host=robot_ip) as robot:
        robot.enter_remote_mode_via_auto()
        robot.switch_on()
        p1 = JointPoint.Degrees([0, 0, 90, 0, 90, 0])
        p2 = JointPoint.Degrees([0, 0, 0, 0, 0, 0])
        robot.MovJ(p1, 40, 100, blend=25)
        robot.MovJ(p2, 40, 100, blend=25)
        robot.MovJ(p1, 40, 100, blend=25)


def cmd_s20(robot_ip: str, local_ip: str, local_port: int) -> None:
    """
    §5.1 S20 联调：movJ 三点 + movL 四点。
    movL 每点前从 cri_cache 取关节作 MmDegWithRef，与 C# 同一时刻快照语义一致。
    """
    jp_targets = [
        [0, 0, 90, 0, 90, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 90, 0, 90, 0],
    ]
    cp_points = [
        [927.511, 214.489, 486.524, 179.999, 0.0, -89.999],
        [927.516, -160.239, 486.534, 180.0, 0.0, -89.999],
        [927.515, -160.238, 1111.244, -179.999, 0.0, -89.999],
        [927.512, 351.971, 1111.249, -179.998, 0.0, -89.999],
    ]

    with CodroidClient(host=robot_ip, local_ip=local_ip, udp_port=local_port) as robot:
        robot.enter_remote_mode_via_auto()
        robot.switch_on()
        robot._start_cri_receiver()
        robot.start_cri_data_push(ip=local_ip, port=local_port)

        for jp in jp_targets:
            robot.MovJ(JointPoint.Degrees(jp), 40, 100, blend=25)

        for cp in cp_points:
            d = robot.cri_cache
            if not d or len(d.joint_pos) < 6:
                raise RuntimeError(
                    "需要 CRI 关节快照作为 movL 的 rj / need CRI joint snapshot for rj"
                )
            rj = list(d.joint_pos)
            robot.MovL(CartesianPoint.MmDegWithRef(cp, rj), 150, 500, blend=25)

        robot.stop_cri_data_push(ip=local_ip, port=local_port)


def _run_one(
    cmd: str,
    robot_ip: str,
    local_ip: str,
    local_port: int,
) -> None:
    PrintBanner(f"codroid_test — {cmd}")
    if cmd == "global":
        cmd_global(robot_ip)
    elif cmd == "kin":
        cmd_kin(robot_ip)
    elif cmd == "io":
        cmd_io(robot_ip)
    elif cmd == "register":
        cmd_register(robot_ip)
    elif cmd == "robotstatus":
        cmd_robotstatus(robot_ip)
    elif cmd == "cri":
        cmd_cri(robot_ip, local_ip, local_port)
    elif cmd == "motion":
        cmd_motion(robot_ip)
    elif cmd == "s20":
        cmd_s20(robot_ip, local_ip, local_port)
    else:
        raise ValueError(f"unknown cmd: {cmd}")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Codroid aggregate test examples")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    p.add_argument("--local-ip", default="192.168.8.150", help="CRI 本机 IP")
    p.add_argument("--local-port", type=int, default=18888, help="CRI UDP 端口")
    sub = p.add_subparsers(dest="cmd", required=False)
    sub.add_parser("all", help="依次运行全部子命令")
    sub.add_parser("global", help="全局变量读写")
    sub.add_parser("kin", help="正逆解")
    sub.add_parser("io", help="读 DI0")
    sub.add_parser("register", help="寄存器 §5.1")
    sub.add_parser("robotstatus", help="订阅 RobotStatus")
    sub.add_parser("cri", help="CRI 收包烟测")
    sub.add_parser("motion", help="movJ 三段")
    sub.add_parser("s20", help="S20 movJ + movL + CRI")

    args = p.parse_args(argv)
    cmds = ALL_CMDS if args.cmd in (None, "all") else (args.cmd,)

    if not (10000 <= args.local_port <= 65534):
        print("local-port 须在 10000–65534", file=sys.stderr)
        return 2

    try:
        for c in cmds:
            _run_one(c, args.robot, args.local_ip, args.local_port)
    except KeyboardInterrupt:
        print("已中断 / Interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print("失败:", e, file=sys.stderr)
        return 1
    PrintBanner("codroid_test — done", subtitle="全部子命令结束" if len(cmds) > 1 else None)
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
