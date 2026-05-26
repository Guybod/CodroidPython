"""
DTO 再导出：名称与 C# ``Define.cs`` / AGENTS.md §3「共享 DTO」一致。
"""
from __future__ import annotations

from typing import Any, Callable

from .exceptions import CodroidCommandException
from .define import (
    CartesianPoint,
    CodroidRequest,
    CommonResponse,
    CodroidResponse,
    CriFilterType,
    CRIFilterType,
    CriMask,
    CRIMask,
    CriRealTimeData,
    CRIData,
    CriStatus,
    CRIStatus,
    JointPoint,
    MoveInstruction,
    MovePoint,
)

PublishHandler = Callable[[str, Any], None]

__all__ = [
    "JointPoint",
    "CartesianPoint",
    "MovePoint",
    "MoveInstruction",
    "CodroidRequest",
    "CommonResponse",
    "CodroidResponse",
    "CriRealTimeData",
    "CRIData",
    "CriStatus",
    "CRIStatus",
    "CriMask",
    "CRIMask",
    "CriFilterType",
    "CRIFilterType",
    "CodroidCommandException",
    "PublishHandler",
]
