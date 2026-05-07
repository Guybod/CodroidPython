"""
Fixed-layout CRI UDP packet parser (308 bytes).

Aligned with AGENTS.md section 2.3: 6-axis, no extra axis, mask 0xFFFF,
high precision (Float64), little-endian.
"""
from __future__ import annotations

import math
import socket
import struct
from typing import List, Optional

from .define import CriRealTimeData, CriStatus
from .exceptions import CodroidError

CRI_PACKET_SIZE = 308
# timestamp(8) + status1(2) + status2(2) + jp(48) + jv(48) + tcp pose(48) +
# tcp vel(48) + tcp linear(8) + torque(48) + external(48)
_STRUCT_FMT = "<qHH" + "6d" + "6d" + "6d" + "6d" + "d" + "6d" + "6d"


def _round_away_from_zero(x: float, ndigits: int = 3) -> float:
    """Match C# Math.Round(x, ndigits, MidpointRounding.AwayFromZero)."""
    if math.isnan(x) or math.isinf(x):
        return x
    if x == 0.0:
        return 0.0
    sign = 1.0 if x > 0 else -1.0
    factor = 10 ** ndigits
    return sign * math.floor(abs(x) * factor + 0.5) / factor


def _parse_status_bits(s1: int, s2: int, out: CriStatus) -> None:
    out.status1_raw = s1 & 0xFFFF
    out.status2_raw = s2 & 0xFFFF
    out.project_running = bool(s1 & (1 << 0))
    out.project_stopped = bool(s1 & (1 << 1))
    out.project_paused = bool(s1 & (1 << 2))
    out.is_enabling = bool(s1 & (1 << 3))
    out.is_disabled = bool(s1 & (1 << 4))
    out.is_manual = bool(s1 & (1 << 5))
    out.is_dragging = bool(s1 & (1 << 6))
    out.is_moving = bool(s1 & (1 << 7))
    out.collision_stop = bool(s1 & (1 << 8))
    out.is_at_safe_pos = bool(s1 & (1 << 9))
    out.has_alarm = bool(s1 & (1 << 10))
    out.is_simulation = bool(s1 & (1 << 11))
    out.is_emergency_stop = bool(s1 & (1 << 12))
    out.is_rescue = bool(s1 & (1 << 13))
    out.is_auto = bool(s1 & (1 << 14))
    out.is_remote = bool(s1 & (1 << 15))
    out.rt_control_mode = bool(s2 & (1 << 0))
    out.error_code = (s2 >> 8) & 0xFF


class CriRealtimePacketParser:
    """
    Parse 308-byte CRI UDP payloads into CriRealTimeData (mm + deg after conversion).
    """

    @staticmethod
    def parse(data: bytes) -> Optional[CriRealTimeData]:
        if len(data) != CRI_PACKET_SIZE:
            return None
        try:
            unpacked = struct.unpack_from(_STRUCT_FMT, data, 0)
        except struct.error:
            return None

        ts = int(unpacked[0])
        s1 = int(unpacked[1])
        s2 = int(unpacked[2])
        jp = unpacked[3:9]
        jv = unpacked[9:15]
        tcp_pose = unpacked[15:21]
        tcp_vel = unpacked[21:27]
        tcp_linear = float(unpacked[27])
        joint_torque = unpacked[28:34]
        joint_ext = unpacked[34:40]

        status = CriStatus()
        _parse_status_bits(s1, s2, status)

        joint_pos: List[float] = [_round_away_from_zero(math.degrees(q)) for q in jp]
        joint_vel: List[float] = [_round_away_from_zero(math.degrees(q)) for q in jv]

        cartesian_pos: List[float] = [
            _round_away_from_zero(tcp_pose[0] * 1000.0),
            _round_away_from_zero(tcp_pose[1] * 1000.0),
            _round_away_from_zero(tcp_pose[2] * 1000.0),
            _round_away_from_zero(math.degrees(tcp_pose[3])),
            _round_away_from_zero(math.degrees(tcp_pose[4])),
            _round_away_from_zero(math.degrees(tcp_pose[5])),
        ]

        cartesian_vel: List[float] = [
            _round_away_from_zero(tcp_vel[0] * 1000.0),
            _round_away_from_zero(tcp_vel[1] * 1000.0),
            _round_away_from_zero(tcp_vel[2] * 1000.0),
            _round_away_from_zero(math.degrees(tcp_vel[3])),
            _round_away_from_zero(math.degrees(tcp_vel[4])),
            _round_away_from_zero(math.degrees(tcp_vel[5])),
        ]

        tcp_speed = _round_away_from_zero(tcp_linear * 1000.0)

        jt_list: List[float] = [_round_away_from_zero(float(t)) for t in joint_torque]
        je_list: List[float] = [_round_away_from_zero(float(t)) for t in joint_ext]

        return CriRealTimeData(
            timestamp=ts,
            status=status,
            joint_pos=joint_pos,
            joint_vel=joint_vel,
            cartesian_pos=cartesian_pos,
            cartesian_vel=cartesian_vel,
            tcp_speed=tcp_speed,
            joint_torque=jt_list,
            external_torque=je_list,
            extra_axis_pos=[],
        )


class CriStreamHandler:
    """可变 mask / 精度的 CRI UDP 包解析（对齐 C# 侧灵活布局）。"""

    def __init__(
        self,
        high_precision: bool = True,
        mask: int = 0xFFFF,
        joint_count: int = 6,
        extra_axis_count: int = 0,
    ):
        self.high_precision = high_precision
        self.mask = int(mask)
        self.joint_count = joint_count
        self.extra_axis_count = extra_axis_count

        self.float_fmt = "d" if high_precision else "f"
        self.float_size = 8 if high_precision else 4
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def bind(self, port: int):
        self._sock.bind(("0.0.0.0", port))
        self._sock.settimeout(2.0)

    def _parse_status1(self, val: int, status_obj: CriStatus):
        status_obj.project_running = bool(val & (1 << 0))
        status_obj.project_stopped = bool(val & (1 << 1))
        status_obj.project_paused = bool(val & (1 << 2))
        status_obj.is_enabling = bool(val & (1 << 3))
        status_obj.is_disabled = bool(val & (1 << 4))
        status_obj.is_manual = bool(val & (1 << 5))
        status_obj.is_dragging = bool(val & (1 << 6))
        status_obj.is_moving = bool(val & (1 << 7))
        status_obj.collision_stop = bool(val & (1 << 8))
        status_obj.is_at_safe_pos = bool(val & (1 << 9))
        status_obj.has_alarm = bool(val & (1 << 10))
        status_obj.is_simulation = bool(val & (1 << 11))
        status_obj.is_emergency_stop = bool(val & (1 << 12))
        status_obj.is_rescue = bool(val & (1 << 13))
        status_obj.is_auto = bool(val & (1 << 14))
        status_obj.is_remote = bool(val & (1 << 15))

    def _parse_status2(self, val: int, status_obj: CriStatus):
        status_obj.rt_control_mode = bool(val & (1 << 0))
        status_obj.error_code = (val >> 8) & 0xFF

    def parse_packet(self, data: bytes) -> CriRealTimeData:
        offset = 0
        res = CriRealTimeData()

        try:
            if self.mask & (1 << 0):
                res.timestamp = struct.unpack_from("<q", data, offset)[0]
                offset += 8

            if self.mask & (1 << 1):
                s1_raw = struct.unpack_from("<H", data, offset)[0]
                self._parse_status1(s1_raw, res.status)
                offset += 2

            if self.mask & (1 << 2):
                s2_raw = struct.unpack_from("<H", data, offset)[0]
                self._parse_status2(s2_raw, res.status)
                offset += 2

            if self.mask & (1 << 8):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_jp = struct.unpack_from(fmt, data, offset)
                res.joint_pos = [round(math.degrees(q), 3) for q in raw_jp]
                offset += self.joint_count * self.float_size

            if self.mask & (1 << 9):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_jv = struct.unpack_from(fmt, data, offset)
                res.joint_vel = [round(math.degrees(q), 3) for q in raw_jv]
                offset += self.joint_count * self.float_size

            if self.mask & (1 << 10):
                count = 7 if self.joint_count == 7 else 6
                fmt = f"<{count}{self.float_fmt}"
                raw_cp = struct.unpack_from(fmt, data, offset)

                converted_cp = [
                    round(raw_cp[0] * 1000.0, 3),
                    round(raw_cp[1] * 1000.0, 3),
                    round(raw_cp[2] * 1000.0, 3),
                ]
                converted_cp.extend([round(math.degrees(a), 3) for a in raw_cp[3:6]])
                if count == 7:
                    converted_cp.append(round(math.degrees(raw_cp[6]), 3))

                res.cartesian_pos = converted_cp
                offset += count * self.float_size

            if self.mask & (1 << 11):
                fmt = f"<{6}{self.float_fmt}"
                raw_cv = struct.unpack_from(fmt, data, offset)
                res.cartesian_vel = [
                    round(raw_cv[0] * 1000.0, 3),
                    round(raw_cv[1] * 1000.0, 3),
                    round(raw_cv[2] * 1000.0, 3),
                    round(math.degrees(raw_cv[3]), 3),
                    round(math.degrees(raw_cv[4]), 3),
                    round(math.degrees(raw_cv[5]), 3),
                ]
                offset += 6 * self.float_size

            if self.mask & (1 << 12):
                raw_tcp = struct.unpack_from(f"<{self.float_fmt}", data, offset)[0]
                res.tcp_speed = round(raw_tcp * 1000.0, 3)
                offset += self.float_size

            if self.mask & (1 << 13):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_jt = struct.unpack_from(fmt, data, offset)
                res.joint_torque = [round(q, 3) for q in raw_jt]
                offset += self.joint_count * self.float_size

            if self.mask & (1 << 14):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_et = struct.unpack_from(fmt, data, offset)
                res.external_torque = [round(q, 3) for q in raw_et]
                offset += self.joint_count * self.float_size

            if self.mask & (1 << 15):
                if self.extra_axis_count > 0:
                    fmt = f"<{self.extra_axis_count}{self.float_fmt}"
                    raw_ep = struct.unpack_from(fmt, data, offset)
                    res.extra_axis_pos = [round(q, 3) for q in raw_ep]
                    offset += self.extra_axis_count * self.float_size

        except struct.error as e:
            raise CodroidError(f"CRI 数据包解析失败: {e}")

        return res


CRIStreamHandler = CriStreamHandler
