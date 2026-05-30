"""
运动指令打包（对齐 C++ ``CodroidController::packInstruction`` / update1 §2）。

协议 ``Robot/move`` 的 ``targetPoint`` / ``middlePoint`` 须经 ``pack_move_point`` 序列化，
以保证 jp 优先、笛卡尔缺省 rj 等规则与 C++/C# 一致。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .define import MotionType, MovePoint

# 与 C++ 默认参考关节一致（度）
DEFAULT_RJ: List[float] = [20.0, 20.0, 20.0, 20.0, 20.0, 20.0]


def _non_empty(seq: Optional[Sequence[float]]) -> bool:
    return seq is not None and len(seq) > 0


def pack_move_point(point: MovePoint) -> Dict[str, Any]:
    """
    将 ``MovePoint`` 打包为 JSON ``targetPoint`` / ``middlePoint`` 字段。

    规则（与 update1 §2、C++ ``packInstruction`` 一致）：

    1. ``jp`` 非空 → 仅输出 ``jp``（忽略 ``cp`` / ``rj``）
    2. 否则 ``cp`` 非空 → 输出 ``cp``；``rj`` 为空时填入 ``DEFAULT_RJ``
    3. ``ep`` 非空时附加（与历史 Python 行为一致）
    4. ``jp`` 与 ``cp`` 均为空 → ``ValueError``
    """
    if _non_empty(point.jp):
        out: Dict[str, Any] = {"jp": [float(x) for x in point.jp]}  # type: ignore[union-attr]
    elif _non_empty(point.cp):
        out = {"cp": [float(x) for x in point.cp]}  # type: ignore[union-attr]
        if _non_empty(point.rj):
            out["rj"] = [float(x) for x in point.rj]  # type: ignore[union-attr]
        else:
            out["rj"] = list(DEFAULT_RJ)
    else:
        raise ValueError(
            "MovePoint must have non-empty jp or cp for Robot/move targetPoint/middlePoint"
        )

    if _non_empty(point.ep):
        out["ep"] = [float(x) for x in point.ep]  # type: ignore[union-attr]

    return out


def pack_instruction(
    m_type: MotionType,
    target: MovePoint,
    speed: float,
    acc: float,
    blend: Optional[float] = None,
    relative_blend: Optional[float] = None,
    middle: Optional[MovePoint] = None,
    circle_num: Optional[int] = None,
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """
    打包单条 ``Robot/move`` 指令（与 ``MotionPath._add_item`` / C# 形态一致）。
    """
    item: Dict[str, Any] = {
        "type": m_type.value,
        "speed": speed,
        "acc": acc,
        "targetPoint": pack_move_point(target),
    }
    if blend is not None:
        item["blend"] = blend
    if relative_blend is not None:
        item["relativeBlend"] = relative_blend

    if middle is not None:
        item["middlePoint"] = pack_move_point(middle)
    if circle_num is not None:
        item["circleNum"] = circle_num
    if coor is not None and len(coor) > 0:
        item["coor"] = [float(x) for x in coor]
    if tool is not None and len(tool) > 0:
        item["tool"] = [float(x) for x in tool]

    return item
