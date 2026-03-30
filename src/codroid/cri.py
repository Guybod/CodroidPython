import socket
import struct
from typing import Any, Dict, List, Optional
from .models import CRIData, CRIMask, CRIStatus, CRI_COMMAND_STRUCT

class CRIStreamHandler:
    def __init__(self, high_precision: bool = False, mask: CRIMask = CRIMask(0xFFFF), joint_count: int = 6, extra_axis_count: int = 0):
        """
        Args:
            high_precision: 是否使用 Float64 (8字节)
            mask: 需要解析的字段掩码
            joint_count: 机器人关节数量
            extra_axis_count: 外部轴数量
        """
        self.high_precision = high_precision
        self.mask = mask
        self.joint_count = joint_count
        self.extra_axis_count = extra_axis_count
        
        # 确定浮点数格式和大小
        self.float_fmt = "d" if high_precision else "f"
        self.float_size = 8 if high_precision else 4
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def bind(self, port: int):
        self._sock.bind(("0.0.0.0", port))
        self._sock.settimeout(2.0)

    def _parse_status1(self, val: int, status_obj: CRIStatus):
        """解析状态数据 1 (16位位域)"""
        status_obj.project_running = bool(val & (1 << 0))
        status_obj.project_stopped = bool(val & (1 << 1))
        status_obj.project_paused  = bool(val & (1 << 2))
        status_obj.is_enabling     = bool(val & (1 << 3))
        status_obj.is_disabled     = bool(val & (1 << 4))
        status_obj.is_manual       = bool(val & (1 << 5))
        status_obj.is_dragging     = bool(val & (1 << 6))
        status_obj.is_moving       = bool(val & (1 << 7))
        status_obj.collision_stop  = bool(val & (1 << 8))
        status_obj.is_at_safe_pos  = bool(val & (1 << 9))
        status_obj.has_alarm       = bool(val & (1 << 10))
        status_obj.is_simulation   = bool(val & (1 << 11))
        status_obj.is_emergency_stop = bool(val & (1 << 12))
        status_obj.is_rescue       = bool(val & (1 << 13))
        status_obj.is_auto         = bool(val & (1 << 14))
        status_obj.is_remote       = bool(val & (1 << 15))

    def _parse_status2(self, val: int, status_obj: CRIStatus):
        """解析状态数据 2 (高8位错误码，低8位模式标志)"""
        status_obj.rt_control_mode = bool((val & 0xFF) & (1 << 0))
        status_obj.error_code = (val >> 8) & 0xFF

    def parse_packet(self, data: bytes) -> CRIData:
        """
        根据掩码动态解析二进制数据包并返回结构化的 CRIData 对象。
        Parse the binary packet dynamically based on the mask and return a CRIData object.
        """
        offset = 0
        res = CRIData()
        
        try:
            # Bit 0: 时间戳 (Int64 - 8字节)
            if self.mask & CRIMask.TIMESTAMP:
                res.timestamp = struct.unpack_from("<q", data, offset)[0]
                offset += 8

            # Bit 1: 状态数据 1 (UInt16 - 2字节)
            if self.mask & CRIMask.STATUS_1:
                s1_raw = struct.unpack_from("<H", data, offset)[0]
                self._parse_status1(s1_raw, res.status)
                offset += 2

            # Bit 2: 状态数据 2 (UInt16 - 2字节)
            if self.mask & CRIMask.STATUS_2:
                s2_raw = struct.unpack_from("<H", data, offset)[0]
                self._parse_status2(s2_raw, res.status)
                offset += 2

            # Bit 3 ~ 7: 保留位 (协议规定如果有数据则顺序拼接，目前直接跳过)
            for bit in range(3, 8):
                if self.mask & (1 << bit):
                    # 如果未来版本定义了这些位的数据大小，在此处增加 offset
                    pass

            # Bit 8: 关节位置 (N个浮点数)
            if self.mask & CRIMask.JOINT_POS:
                fmt = f"<{self.joint_count}{self.float_fmt}"
                res.joint_pos = list(struct.unpack_from(fmt, data, offset))
                offset += self.joint_count * self.float_size

            # Bit 9: 关节速度 (N个浮点数)
            if self.mask & CRIMask.JOINT_VEL:
                fmt = f"<{self.joint_count}{self.float_fmt}"
                res.joint_vel = list(struct.unpack_from(fmt, data, offset))
                offset += self.joint_count * self.float_size

            # Bit 10: 末端位置 (6或7个浮点数)
            if self.mask & CRIMask.CARTESIAN_POS:
                # 检查是否为7轴机器人
                count = 7 if self.joint_count == 7 else 6
                fmt = f"<{count}{self.float_fmt}"
                res.cartesian_pos = list(struct.unpack_from(fmt, data, offset))
                offset += count * self.float_size

            # Bit 11: 末端速度 (6个浮点数)
            if self.mask & CRIMask.CARTESIAN_VEL:
                fmt = f"<{6}{self.float_fmt}"
                res.cartesian_vel = list(struct.unpack_from(fmt, data, offset))
                offset += 6 * self.float_size

            # Bit 12: 末端线速度 (1个浮点数)
            if self.mask & CRIMask.TCP_SPEED:
                res.tcp_speed = struct.unpack_from(f"<{self.float_fmt}", data, offset)[0]
                offset += self.float_size

            # Bit 13: 关节输出力矩 (N个浮点数)
            if self.mask & CRIMask.JOINT_TORQUE:
                fmt = f"<{self.joint_count}{self.float_fmt}"
                res.joint_torque = list(struct.unpack_from(fmt, data, offset))
                offset += self.joint_count * self.float_size

            # Bit 14: 关节受到外力 (N个浮点数)
            if self.mask & CRIMask.EXTERNAL_TORQUE:
                fmt = f"<{self.joint_count}{self.float_fmt}"
                res.external_torque = list(struct.unpack_from(fmt, data, offset))
                offset += self.joint_count * self.float_size

            # Bit 15: 外部轴位置 (M个浮点数)
            if self.mask & CRIMask.EXTRA_AXIS_POS:
                if self.extra_axis_count > 0:
                    fmt = f"<{self.extra_axis_count}{self.float_fmt}"
                    res.extra_axis_pos = list(struct.unpack_from(fmt, data, offset))
                    offset += self.extra_axis_count * self.float_size

        except (struct.error, IndexError) as e:
            # 如果接收到的字节长度与掩码配置不符，抛出清晰的错误
            from .exceptions import CodroidError
            raise CodroidError(f"CRI 数据包解析失败，可能是掩码配置与实际推送不符: {e}")

        return res
    
