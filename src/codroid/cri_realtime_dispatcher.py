"""
UDP real-time command dispatcher (64-byte CommandData), AGENTS.md §6.3.
"""
from __future__ import annotations

import math
import socket
import time
from typing import Iterable, List, Sequence

from .define import CRI_COMMAND_STRUCT
from .trajectory import TrajectoryPoint, TrajectorySpace


class CriRealtimeDispatcher:
    def __init__(
        self,
        controller_ip: str,
        controller_udp_port: int = 9030,
        convert_to_si: bool = True,
    ):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._controller_ip = controller_ip
        self._controller_port = controller_udp_port
        self.convert_to_si = convert_to_si

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass

    def __enter__(self) -> "CriRealtimeDispatcher":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _to_wire(self, position6: Sequence[float], space: TrajectorySpace) -> List[float]:
        p = [float(x) for x in position6]
        if not self.convert_to_si:
            return p
        if space == TrajectorySpace.JOINT:
            return [math.radians(p[i]) for i in range(6)]
        return [
            p[0] / 1000.0,
            p[1] / 1000.0,
            p[2] / 1000.0,
            math.radians(p[3]),
            math.radians(p[4]),
            math.radians(p[5]),
        ]

    def send_command(self, position6: Sequence[float], space: TrajectorySpace) -> None:
        data = self._to_wire(position6, space)
        type_byte = 0 if space == TrajectorySpace.JOINT else 1
        nc = (0, 0, 0, 0, 0, 0, 0)
        packet = CRI_COMMAND_STRUCT.pack(
            0,
            data[0],
            data[1],
            data[2],
            data[3],
            data[4],
            data[5],
            type_byte,
            *nc,
        )
        self._sock.sendto(packet, (self._controller_ip, self._controller_port))

    def send_trajectory(
        self,
        trajectory: Iterable[TrajectoryPoint],
        space: TrajectorySpace,
        period_ms: int,
    ) -> None:
        if not (0 < period_ms <= 1000):
            raise ValueError("period_ms must be in (0, 1000]")
        traj_list = list(trajectory)
        for i, pt in enumerate(traj_list):
            self.send_command(pt.position, space)
            if i < len(traj_list) - 1:
                time.sleep(period_ms / 1000.0)

    # C# ``CriRealtimeDispatcher.SendCommand`` / ``SendTrajectory``
    SendCommand = send_command
    SendTrajectory = send_trajectory
