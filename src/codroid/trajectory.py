"""
Offline trajectory generation per TRAJECTORY_ALGORITHM.md (C# baseline).
Units: joint deg, Cartesian mm + deg (fixed Euler XYZ extrinsic).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

# Quaternion (w, x, y, z), all double-precision internally


class TrajectorySpace(Enum):
    JOINT = "Joint"
    CARTESIAN = "Cartesian"


class TrajectoryProfile(Enum):
    CUBIC = "Cubic"
    TRAPEZOIDAL = "Trapezoidal"


@dataclass
class TrajectoryRequest:
    space: TrajectorySpace
    frequency_hz: float
    profile: TrajectoryProfile
    acceleration: float
    speed: Optional[float] = None
    duration_seconds: Optional[float] = None


@dataclass
class TrajectoryPoint:
    t: float
    position: List[float]


class CubicProfile:
    def __init__(self, T: float):
        self.T = T

    def scale_at(self, t: float) -> float:
        if t <= 0:
            return 0.0
        if t >= self.T:
            return 1.0
        tau = t / self.T
        return 3.0 * tau * tau - 2.0 * tau * tau * tau


class TrapezoidalProfile:
    def __init__(self, T: float, D: float, V: float, A: float, Ta: float):
        self.T = T
        self.D = D
        self.V = V
        self.A = A
        self.Ta = Ta

    @classmethod
    def from_speed(cls, D: float, v: float, a: float) -> "TrapezoidalProfile":
        ta = v / a
        da = 0.5 * v * ta
        if 2.0 * da >= D:
            vp = math.sqrt(a * D)
            ta = vp / a
            return cls(T=2.0 * ta, D=D, V=vp, A=a, Ta=ta)
        tc = (D - 2.0 * da) / v
        return cls(T=2.0 * ta + tc, D=D, V=v, A=a, Ta=ta)

    @classmethod
    def from_duration(cls, D: float, T: float, a: float) -> "TrapezoidalProfile":
        disc = a * a * T * T - 4.0 * a * D
        if disc < 0.0:
            vp = 2.0 * D / T
            a_eff = 4.0 * D / (T * T)
            return cls(T=T, D=D, V=vp, A=a_eff, Ta=T / 2.0)
        v = (a * T - math.sqrt(disc)) / 2.0
        ta = v / a
        return cls(T=T, D=D, V=v, A=a, Ta=ta)

    def scale_at(self, t: float) -> float:
        if t <= 0:
            return 0.0
        if t >= self.T:
            return 1.0
        T = self.T
        D = self.D
        A = self.A
        Ta = self.Ta
        if t < Ta:
            arc = 0.5 * A * t * t
        elif t > T - Ta:
            tt = T - t
            arc = D - 0.5 * A * tt * tt
        else:
            arc = 0.5 * A * Ta * Ta + self.V * (t - Ta)
        s = arc / D if D > 0 else 1.0
        return max(0.0, min(1.0, s))


class EulerXyz:
    LERP_THRESHOLD = 0.9995
    GIMBAL_EPS = 0.999999

    @staticmethod
    def to_quaternion(rx_deg: float, ry_deg: float, rz_deg: float) -> Tuple[float, float, float, float]:
        a = rx_deg * math.pi / 180.0 / 2.0
        b = ry_deg * math.pi / 180.0 / 2.0
        c = rz_deg * math.pi / 180.0 / 2.0
        cx, sx = math.cos(a), math.sin(a)
        cy, sy = math.cos(b), math.sin(b)
        cz, sz = math.cos(c), math.sin(c)
        w = cz * cy * cx + sz * sy * sx
        x = cz * cy * sx - sz * sy * cx
        y = cz * sy * cx + sz * cy * sx
        z = sz * cy * cx - cz * sy * sx
        return (w, x, y, z)

    @staticmethod
    def from_quaternion(q: Tuple[float, float, float, float]) -> Tuple[float, float, float]:
        w, x, y, z = q
        sb = max(-1.0, min(1.0, 2.0 * (w * y - x * z)))
        ry = math.asin(sb)
        if abs(sb) < EulerXyz.GIMBAL_EPS:
            rx = math.atan2(2.0 * (y * z + w * x), 1.0 - 2.0 * (x * x + y * y))
            rz = math.atan2(2.0 * (x * y + w * z), 1.0 - 2.0 * (y * y + z * z))
        else:
            rx = math.atan2(-2.0 * (y * z - w * x), 1.0 - 2.0 * (x * x + z * z))
            rz = 0.0
        return (rx * 180.0 / math.pi, ry * 180.0 / math.pi, rz * 180.0 / math.pi)

    @staticmethod
    def _normalize(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        w, x, y, z = q
        n = math.sqrt(w * w + x * x + y * y + z * z)
        if n <= 0.0:
            return (1.0, 0.0, 0.0, 0.0)
        return (w / n, x / n, y / n, z / n)

    @staticmethod
    def slerp(
        q0: Tuple[float, float, float, float],
        q1: Tuple[float, float, float, float],
        t: float,
    ) -> Tuple[float, float, float, float]:
        w0, x0, y0, z0 = q0
        w1, x1, y1, z1 = q1
        dot = w0 * w1 + x0 * x1 + y0 * y1 + z0 * z1
        if dot < 0.0:
            w1, x1, y1, z1 = -w1, -x1, -y1, -z1
            dot = -dot
        if dot > EulerXyz.LERP_THRESHOLD:
            w = (1.0 - t) * w0 + t * w1
            x = (1.0 - t) * x0 + t * x1
            y = (1.0 - t) * y0 + t * y1
            z = (1.0 - t) * z0 + t * z1
            return EulerXyz._normalize((w, x, y, z))
        theta0 = math.acos(max(-1.0, min(1.0, dot)))
        theta = theta0 * t
        sin_theta = math.sin(theta)
        sin_theta0 = math.sin(theta0)
        s0 = math.cos(theta) - dot * sin_theta / sin_theta0
        s1 = sin_theta / sin_theta0
        w = s0 * w0 + s1 * w1
        x = s0 * x0 + s1 * x1
        y = s0 * y0 + s1 * y1
        z = s0 * z0 + s1 * z1
        return (w, x, y, z)


def _validate_inputs(start: Sequence[float], target: Sequence[float], request: TrajectoryRequest) -> None:
    if len(start) != 6 or len(target) != 6:
        raise ValueError("start and target must have length 6")
    if request.frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    has_speed = request.speed is not None
    has_dur = request.duration_seconds is not None
    if has_speed == has_dur:
        raise ValueError("Exactly one of speed and duration_seconds must be set")
    if has_speed and request.speed is not None and request.speed <= 0:
        raise ValueError("speed must be > 0")
    if has_dur and request.duration_seconds is not None and request.duration_seconds <= 0:
        raise ValueError("duration_seconds must be > 0")
    if request.acceleration <= 0:
        raise ValueError("acceleration must be > 0")


def _compute_profile(D: float, request: TrajectoryRequest) -> object:
    if request.profile == TrajectoryProfile.CUBIC:
        if request.duration_seconds is not None:
            T = request.duration_seconds
        else:
            T = D / float(request.speed)
        return CubicProfile(T)
    if request.duration_seconds is not None:
        return TrapezoidalProfile.from_duration(D, request.duration_seconds, request.acceleration)
    return TrapezoidalProfile.from_speed(D, float(request.speed), request.acceleration)


def _generate_joint(start: Sequence[float], target: Sequence[float], request: TrajectoryRequest) -> List[TrajectoryPoint]:
    q0 = [float(x) for x in start]
    qf = [float(x) for x in target]
    max_delta = max(abs(qf[i] - q0[i]) for i in range(6))
    if max_delta < 1e-9:
        return [TrajectoryPoint(t=0.0, position=list(q0))]

    profile = _compute_profile(max_delta, request)
    dt = 1.0 / request.frequency_hz
    T = getattr(profile, "T")
    n = max(2, int(math.ceil(T / dt)) + 1)
    out: List[TrajectoryPoint] = []
    for k in range(n):
        t = min(k * dt, T)
        s = profile.scale_at(t)
        pos = [q0[i] + s * (qf[i] - q0[i]) for i in range(6)]
        out.append(TrajectoryPoint(t=t, position=pos))
    return out


def _quat_dot(
    a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]


def _generate_cartesian(start: Sequence[float], target: Sequence[float], request: TrajectoryRequest) -> List[TrajectoryPoint]:
    p0 = [float(x) for x in start]
    pf = [float(x) for x in target]
    dx = pf[0] - p0[0]
    dy = pf[1] - p0[1]
    dz = pf[2] - p0[2]
    D = math.sqrt(dx * dx + dy * dy + dz * dz)

    q0 = EulerXyz.to_quaternion(p0[3], p0[4], p0[5])
    qf = EulerXyz.to_quaternion(pf[3], pf[4], pf[5])

    if D < 1e-9:
        q0n = EulerXyz._normalize(q0)
        qfn = EulerXyz._normalize(qf)
        if abs(_quat_dot(q0n, qfn)) >= 1.0 - 1e-9:
            return [TrajectoryPoint(t=0.0, position=list(p0))]
        if request.speed is not None:
            raise ValueError("纯姿态运动请改用 duration_seconds / Pure rotation requires duration_seconds")
        profile = _compute_profile(1.0, request)
    else:
        profile = _compute_profile(D, request)

    dt = 1.0 / request.frequency_hz
    T = getattr(profile, "T")
    n = max(2, int(math.ceil(T / dt)) + 1)
    out: List[TrajectoryPoint] = []
    for k in range(n):
        t = min(k * dt, T)
        s = profile.scale_at(t)
        x = p0[0] + s * dx
        y = p0[1] + s * dy
        z = p0[2] + s * dz
        q = EulerXyz.slerp(q0, qf, s)
        rx, ry, rz = EulerXyz.from_quaternion(q)
        out.append(TrajectoryPoint(t=t, position=[x, y, z, rx, ry, rz]))
    return out


class TrajectoryGenerator:
    """Static API aligned with C# TrajectoryGenerator.Generate."""

    @staticmethod
    def generate(
        start: Sequence[float],
        target: Sequence[float],
        request: TrajectoryRequest,
    ) -> List[TrajectoryPoint]:
        _validate_inputs(start, target, request)
        if request.space == TrajectorySpace.JOINT:
            return _generate_joint(start, target, request)
        if request.space == TrajectorySpace.CARTESIAN:
            return _generate_cartesian(start, target, request)
        raise ValueError("Unknown TrajectorySpace")

    @staticmethod
    def generate_multi_segment(
        waypoints: Sequence[Sequence[float]],
        request: TrajectoryRequest,
    ) -> List[TrajectoryPoint]:
        if len(waypoints) < 2:
            raise ValueError("waypoints must contain at least 2 poses")
        result: List[TrajectoryPoint] = []
        t_base = 0.0
        for i in range(len(waypoints) - 1):
            seg = TrajectoryGenerator.generate(waypoints[i], waypoints[i + 1], request)
            for k, pt in enumerate(seg):
                if i > 0 and k == 0:
                    continue
                result.append(TrajectoryPoint(t=t_base + pt.t, position=list(pt.position)))
            t_base += seg[-1].t
        return result

    # C# ``TrajectoryGenerator.Generate`` 同名别名（Python 侧仍以 ``generate`` 为主）。
    Generate = generate
