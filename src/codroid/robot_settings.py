"""
机器人设置界面参数（协议 19.1~19.7，对齐 C# ``RobotSettings.cs``）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exceptions import CodroidError

MIN_SLOT_ID = 0
MAX_SLOT_ID = 15
WRITABLE_MIN_SLOT_ID = 1
_ZERO_EPSILON = 1e-9


@dataclass
class RobotFrame:
    """工具 / 用户坐标系单帧（x,y,z,a,b,c，单位与控制器设置界面一致）。"""

    id: int
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": int(self.id),
            "x": float(self.x),
            "y": float(self.y),
            "z": float(self.z),
            "a": float(self.a),
            "b": float(self.b),
            "c": float(self.c),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> RobotFrame:
        return cls(
            id=int(data["id"]),
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            z=float(data.get("z", 0)),
            a=float(data.get("a", 0)),
            b=float(data.get("b", 0)),
            c=float(data.get("c", 0)),
        )


@dataclass
class RobotPayloadFrame:
    """负载坐标系单帧（m, mx, my, mz）。"""

    id: int
    m: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": int(self.id),
            "m": float(self.m),
            "mx": float(self.mx),
            "my": float(self.my),
            "mz": float(self.mz),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> RobotPayloadFrame:
        return cls(
            id=int(data["id"]),
            m=float(data.get("m", 0)),
            mx=float(data.get("mx", 0)),
            my=float(data.get("my", 0)),
            mz=float(data.get("mz", 0)),
        )


@dataclass
class RobotParameters:
    """``Robot/GetRobotParameter`` 返回的设置界面参数快照。"""

    default_tool_id: int = 0
    default_payload_id: int = 0
    default_coordinate_id: int = 0
    max_payload: float = 0.0
    tool: List[RobotFrame] = field(default_factory=list)
    payload: List[RobotPayloadFrame] = field(default_factory=list)
    coordinate: List[RobotFrame] = field(default_factory=list)

    @classmethod
    def from_db(cls, db: Any) -> RobotParameters:
        if db is None:
            raise CodroidError("GetRobotParameter 响应 db 为空。")
        if not isinstance(db, dict):
            raise CodroidError("GetRobotParameter 响应 db 须为对象。")
        return cls(
            default_tool_id=int(db.get("defaultToolId", 0)),
            default_payload_id=int(db.get("defaultPayloadId", 0)),
            default_coordinate_id=int(db.get("defaultCoordinateId", 0)),
            max_payload=float(db.get("maxPayload", 0)),
            tool=[RobotFrame.from_mapping(x) for x in db.get("Tool") or []],
            payload=[RobotPayloadFrame.from_mapping(x) for x in db.get("Payload") or []],
            coordinate=[RobotFrame.from_mapping(x) for x in db.get("Coordinate") or []],
        )


def validate_collision_sensitivity(sensitivity: int) -> None:
    if not (0 <= sensitivity <= 100):
        raise CodroidError("灵敏度范围必须在 0~100 之间。")


def validate_default_slot_id(slot_id: int, param_name: str = "id") -> None:
    if not (MIN_SLOT_ID <= slot_id <= MAX_SLOT_ID):
        raise CodroidError(f"{param_name} 须在 {MIN_SLOT_ID}~{MAX_SLOT_ID}。")


def validate_writable_frame_id(frame_id: int, param_name: str = "frame_id") -> None:
    if not (WRITABLE_MIN_SLOT_ID <= frame_id <= MAX_SLOT_ID):
        raise CodroidError(
            f"{param_name} 须为 {WRITABLE_MIN_SLOT_ID}~{MAX_SLOT_ID}；"
            "id=0 为保留项不可修改。"
        )


def _is_zero(value: float) -> bool:
    return abs(value) <= _ZERO_EPSILON


def _ensure_reserved_tool_zero(frame: RobotFrame) -> None:
    if frame.id != 0:
        return
    if not all(_is_zero(v) for v in (frame.x, frame.y, frame.z, frame.a, frame.b, frame.c)):
        raise CodroidError("id=0 的工具/用户坐标系项必须保持全零，不可修改。")


def _ensure_reserved_payload_zero(frame: RobotPayloadFrame) -> None:
    if frame.id != 0:
        return
    if not all(_is_zero(v) for v in (frame.m, frame.mx, frame.my, frame.mz)):
        raise CodroidError("id=0 的负载坐标系项必须保持全零，不可修改。")


def validate_tool_frames_for_save(frames: Sequence[RobotFrame]) -> None:
    _validate_full_slot_list(frames, _ensure_reserved_tool_zero)


def validate_payload_frames_for_save(frames: Sequence[RobotPayloadFrame]) -> None:
    _validate_full_slot_list(frames, _ensure_reserved_payload_zero)


def _validate_full_slot_list(frames: Sequence[Any], validate_reserved) -> None:
    if len(frames) != MAX_SLOT_ID + 1:
        raise CodroidError(f"须提供 {MAX_SLOT_ID + 1} 项（id {MIN_SLOT_ID}~{MAX_SLOT_ID}）。")
    seen = set()
    for frame in frames:
        fid = int(frame.id)
        if not (MIN_SLOT_ID <= fid <= MAX_SLOT_ID):
            raise CodroidError(f"列表中存在非法 id={fid}。")
        if fid in seen:
            raise CodroidError(f"列表中 id={fid} 重复。")
        seen.add(fid)
        if fid == 0:
            validate_reserved(frame)
    for i in range(MIN_SLOT_ID, MAX_SLOT_ID + 1):
        if i not in seen:
            raise CodroidError(f"缺少 id={i} 的项。")


def merge_tool_frame(
    current: Sequence[RobotFrame], frame_id: int, updated: RobotFrame
) -> List[RobotFrame]:
    merged = list(current)
    index = next((i for i, f in enumerate(merged) if f.id == frame_id), -1)
    if index < 0:
        raise CodroidError(f"当前参数中不存在 Tool id={frame_id}。")
    merged[index] = updated
    return merged


def merge_payload_frame(
    current: Sequence[RobotPayloadFrame], frame_id: int, updated: RobotPayloadFrame
) -> List[RobotPayloadFrame]:
    merged = list(current)
    index = next((i for i, f in enumerate(merged) if f.id == frame_id), -1)
    if index < 0:
        raise CodroidError(f"当前参数中不存在 Payload id={frame_id}。")
    merged[index] = updated
    return merged


def merge_coordinate_frame(
    current: Sequence[RobotFrame], frame_id: int, updated: RobotFrame
) -> List[RobotFrame]:
    merged = list(current)
    index = next((i for i, f in enumerate(merged) if f.id == frame_id), -1)
    if index < 0:
        raise CodroidError(f"当前参数中不存在 Coordinate id={frame_id}。")
    merged[index] = updated
    return merged


def build_default_payload_id_db(payload_id: int) -> Dict[str, int]:
    return {"defaultPayloadId": payload_id}


def build_default_tool_id_db(tool_id: int) -> Dict[str, int]:
    return {"defaultToolId": tool_id}


def build_default_coordinate_id_db(coordinate_id: int) -> Dict[str, int]:
    return {"defaultCoordinateId": coordinate_id}


def build_tool_db(frames: Sequence[RobotFrame]) -> Dict[str, List[Dict[str, Any]]]:
    ordered = sorted(frames, key=lambda f: f.id)
    return {"Tool": [f.to_dict() for f in ordered]}


def build_payload_db(
    frames: Sequence[RobotPayloadFrame],
) -> Dict[str, List[Dict[str, Any]]]:
    ordered = sorted(frames, key=lambda f: f.id)
    return {"Payload": [f.to_dict() for f in ordered]}


def build_coordinate_db(frames: Sequence[RobotFrame]) -> Dict[str, List[Dict[str, Any]]]:
    ordered = sorted(frames, key=lambda f: f.id)
    return {"Coordinate": [f.to_dict() for f in ordered]}


def validate_frame_id_matches(frame_id: int, frame: RobotFrame) -> None:
    if frame.id != frame_id:
        raise CodroidError(f"frame.id（{frame.id}）须与 frame_id（{frame_id}）一致。")


def validate_payload_frame_id_matches(frame_id: int, frame: RobotPayloadFrame) -> None:
    if frame.id != frame_id:
        raise CodroidError(f"frame.id（{frame.id}）须与 frame_id（{frame_id}）一致。")
