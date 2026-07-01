#!/usr/bin/env python3
"""
示例 04 — 全局变量增量保存（globalVar/save）

【目的】
  演示 ``GlobalVariable`` 包装不同类型（int/str/list/dict）并批量写入控制器。

【前置条件】
  - 远程模式
  - 变量名合法（字母数字下划线等，见 SDK 校验）

【涉及协议】
  - TCP globalVar/save：每个变量含 val（JSON 字符串）与可选 nm（备注）

【运行】
  均在项目根目录 CodroidPython/ 执行。

  临时启动（未安装 SDK，直接使用 src 源码）：
    Linux / macOS:   PYTHONPATH=src python examples/04_global_value.py [参数...]
    Windows PS:      $env:PYTHONPATH="src"; python examples/04_global_value.py [参数...]
    Windows cmd:     set PYTHONPATH=src && python examples\04_global_value.py [参数...]

  本地安装启动（pip install -e . 后）：
    python examples/04_global_value.py --robot 192.168.8.136

【注意】
  - save_global_vars 为增量保存，不会删除未出现在字典中的其它全局变量
"""
from __future__ import annotations

import argparse
import sys

from codroid import CodroidControlInterface, GlobalVariable, InitConsoleUtf8, PrintBanner


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Save global variables")
    p.add_argument("--robot", default="192.168.8.136", help="控制器 IP")
    args = p.parse_args(argv)

    PrintBanner("04 — Global variables", subtitle=args.robot)

    # 键为控制器侧全局变量名；value 为 GlobalVariable(value=..., note=...)
    vars_to_save = {
        "v_int": GlobalVariable(value=1024, note="整数示例"),
        "v_str": GlobalVariable(value="Codroid", note="字符串示例"),
        "v_list": GlobalVariable(value=[1.1, 2.2, 3.3], note="数组示例"),
        "v_map": GlobalVariable(
            value={"power": 100, "status": "on"},
            note="Map 示例",
        ),
    }

    try:
        with CodroidControlInterface(host=args.robot) as robot:
            robot.EnterRemoteModeViaAuto()
            print("增量保存全局变量 / Saving globals...")
            res = robot.SaveGlobalVars(vars_to_save)
            if res.is_success:
                print("保存成功 / Saved")
            else:
                print(f"失败 / Failed: {res.err}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    InitConsoleUtf8()
    raise SystemExit(main(sys.argv[1:]))
