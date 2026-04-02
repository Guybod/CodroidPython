import math
import socket
import struct
from typing import Any, Dict, List, Optional
from .models import CRIData, CRIStatus

class CRIStreamHandler:
    def __init__(self, high_precision: bool = True, mask: int = 0xFFFF, joint_count: int = 6, extra_axis_count: int = 0):
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

    def _parse_status1(self, val: int, status_obj: CRIStatus):
        status_obj.project_running   = bool(val & (1 << 0))
        status_obj.project_stopped   = bool(val & (1 << 1))
        status_obj.project_paused    = bool(val & (1 << 2))
        status_obj.is_enabling       = bool(val & (1 << 3))
        status_obj.is_disabled       = bool(val & (1 << 4))
        status_obj.is_manual         = bool(val & (1 << 5))
        status_obj.is_dragging       = bool(val & (1 << 6))
        status_obj.is_moving         = bool(val & (1 << 7))
        status_obj.collision_stop    = bool(val & (1 << 8))
        status_obj.is_at_safe_pos    = bool(val & (1 << 9))
        status_obj.has_alarm         = bool(val & (1 << 10))
        status_obj.is_simulation     = bool(val & (1 << 11))
        status_obj.is_emergency_stop = bool(val & (1 << 12))
        status_obj.is_rescue         = bool(val & (1 << 13))
        status_obj.is_auto           = bool(val & (1 << 14))
        status_obj.is_remote         = bool(val & (1 << 15))

    def _parse_status2(self, val: int, status_obj: CRIStatus):
        status_obj.rt_control_mode = bool(val & (1 << 0))
        status_obj.error_code = (val >> 8) & 0xFF

    def parse_packet(self, data: bytes) -> CRIData:
        offset = 0
        res = CRIData()
        
        try:
            # Bit 0: 时间戳
            if self.mask & (1 << 0):
                res.timestamp = struct.unpack_from("<q", data, offset)[0]
                offset += 8

            # Bit 1: 状态数据 1
            if self.mask & (1 << 1):
                s1_raw = struct.unpack_from("<H", data, offset)[0]
                self._parse_status1(s1_raw, res.status)
                offset += 2

            # Bit 2: 状态数据 2
            if self.mask & (1 << 2):
                s2_raw = struct.unpack_from("<H", data, offset)[0]
                self._parse_status2(s2_raw, res.status)
                offset += 2

            # Bit 8: 关节位置 (rad -> deg, round 3)
            if self.mask & (1 << 8):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_jp = struct.unpack_from(fmt, data, offset)
                res.joint_pos = [round(math.degrees(q), 3) for q in raw_jp]
                offset += self.joint_count * self.float_size

            # Bit 9: 关节速度 (rad/s -> deg/s, round 3)
            if self.mask & (1 << 9):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_jv = struct.unpack_from(fmt, data, offset)
                res.joint_vel = [round(math.degrees(q), 3) for q in raw_jv]
                offset += self.joint_count * self.float_size

            # Bit 10: 末端位置 (m->mm, rad->deg, round 3)
            if self.mask & (1 << 10):
                count = 7 if self.joint_count == 7 else 6
                fmt = f"<{count}{self.float_fmt}"
                raw_cp = struct.unpack_from(fmt, data, offset)
                
                # x, y, z (mm)
                converted_cp = [round(raw_cp[0] * 1000.0, 3), 
                                round(raw_cp[1] * 1000.0, 3), 
                                round(raw_cp[2] * 1000.0, 3)]
                # rx, ry, rz (deg)
                converted_cp.extend([round(math.degrees(a), 3) for a in raw_cp[3:6]])
                # 7轴 e (deg)
                if count == 7:
                    converted_cp.append(round(math.degrees(raw_cp[6]), 3))
                    
                res.cartesian_pos = converted_cp
                offset += count * self.float_size

            # Bit 11: 末端速度 (m/s->mm/s, rad/s->deg/s, round 3)
            if self.mask & (1 << 11):
                fmt = f"<{6}{self.float_fmt}"
                raw_cv = struct.unpack_from(fmt, data, offset)
                res.cartesian_vel = [
                    round(raw_cv[0] * 1000.0, 3), round(raw_cv[1] * 1000.0, 3), round(raw_cv[2] * 1000.0, 3),
                    round(math.degrees(raw_cv[3]), 3), round(math.degrees(raw_cv[4]), 3), round(math.degrees(raw_cv[5]), 3)
                ]
                offset += 6 * self.float_size

            # Bit 12: 末端线速度 (m/s -> mm/s, round 3)
            if self.mask & (1 << 12):
                raw_tcp = struct.unpack_from(f"<{self.float_fmt}", data, offset)[0]
                res.tcp_speed = round(raw_tcp * 1000.0, 3)
                offset += self.float_size

            # Bit 13: 关节输出力矩 (Nm, round 3)
            if self.mask & (1 << 13):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_jt = struct.unpack_from(fmt, data, offset)
                res.joint_torque = [round(q, 3) for q in raw_jt]
                offset += self.joint_count * self.float_size

            # Bit 14: 关节受到外力 (Nm, round 3)
            if self.mask & (1 << 14):
                fmt = f"<{self.joint_count}{self.float_fmt}"
                raw_et = struct.unpack_from(fmt, data, offset)
                res.external_torque = [round(q, 3) for q in raw_et]
                offset += self.joint_count * self.float_size

            # Bit 15: 外部轴位置 (round 3)
            if self.mask & (1 << 15):
                if self.extra_axis_count > 0:
                    fmt = f"<{self.extra_axis_count}{self.float_fmt}"
                    raw_ep = struct.unpack_from(fmt, data, offset)
                    res.extra_axis_pos = [round(q, 3) for q in raw_ep]
                    offset += self.extra_axis_count * self.float_size

        except struct.error as e:
            from .exceptions import CodroidError
            raise CodroidError(f"CRI 数据包解析失败: {e}")

        return res