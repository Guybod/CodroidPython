# src/codroid/define.py — DTO / 常量（对齐 C# Define.cs）
from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import Enum, IntEnum, IntFlag
from struct import Struct
from typing import Any, Dict, List, Optional, Sequence, Union

# =============================================================================
# 1. 基础通讯模型 / Base Communication Models
# =============================================================================

@dataclass
class CommonResponse:
    """
    TCP JSON 通用响应（C# ``CommonResponse`` / Define.cs）。
    """

    id: Union[int, str]
    ty: str
    db: Optional[Any] = None
    err: Optional[Any] = None

    @property
    def is_success(self) -> bool:
        return self.err is None


@dataclass
class CodroidRequest:
    """
    SDK 通用请求结构 / Universal SDK Request Structure.
    """
    id: Union[int, str]
    ty: str
    db: Optional[Any] = None

# =============================================================================
# 2. 变量与配置模型 / Variables & Configuration Models
# =============================================================================

class CoordinateType(str, Enum):
    """
    坐标系类型枚举 / Coordinate System Type Enum.
    
    Attributes:
        USER: 用户坐标系 / User coordinate system.
        TOOL: 工具坐标系 / Tool coordinate system.
    """
    USER = "user"
    TOOL = "tool"


class IOType(str, Enum):
    """
    IO 类型枚举 / IO Type Enum.
    """
    DI = "DI"  # 数字输入 / Digital Input
    DO = "DO"  # 数字输出 / Digital Output
    AI = "AI"  # 模拟输入 / Analog Input
    AO = "AO"  # 模拟输出 / Analog Output


class ExtendArrayType(str, Enum):
    """
    扩展数组数据类型 / Extended Array Data Type.
    """
    BOOL = "Bool"
    UINT8 = "UInt8"
    INT8 = "Int8"
    UINT16 = "UInt16"
    INT16 = "Int16"
    UINT32 = "UInt32"
    INT32 = "Int32"
    FLOAT32 = "Float32"


@dataclass
class GlobalVariable:
    """
    全局变量数据模型 / Global Variable Data Model.

    Attributes:
        value (Any): 变量值 (支持 int, float, str, list, dict) / Variable value.
        note (Optional[str]): 变量备注 (nm) / Variable note.
    """
    value: Any
    note: Optional[str] = None

    def to_robot_format(self) -> Dict[str, Any]:
        """
        将 Python 对象转换为机器人协议要求的格式化字典。
        Convert Python object to formatted dict required by robot protocol.
        """
        # 处理字符串转义逻辑：机器人要求字符串带转义双引号
        if isinstance(self.value, str):
            formatted_val = f'"{self.value}"'
        else:
            formatted_val = json.dumps(self.value, ensure_ascii=False)
        
        data = {"val": formatted_val}
        if self.note is not None:
            data["nm"] = self.note
        return data

# =============================================================================
# 3. RS485 通讯模型 / RS485 Communication Models
# =============================================================================

class RS485BaudRate(IntEnum):
    """末端 485 波特率枚举 / RS485 Baud Rate."""
    B110 = 110
    B300 = 300
    B600 = 600
    B1200 = 1200
    B2400 = 2400
    B4800 = 4800
    B9600 = 9600
    B14400 = 14400
    B19200 = 19200
    B38400 = 38400
    B56000 = 56000
    B57600 = 57600
    B115200 = 115200
    B128000 = 128000
    B230400 = 230400


class RS485StopBits(IntEnum):
    """RS485 停止位 / RS485 Stop Bits."""
    ONE = 1
    TWO = 2


class RS485Parity(IntEnum):
    """RS485 校验位 / RS485 Parity."""
    NONE = 0
    ODD = 1
    EVEN = 2

# =============================================================================
# 4. 力控模型 / Force Control Models
# =============================================================================

class ForceFrame(IntEnum):
    """力控坐标系 / Force control coordinate frame."""

    TCP = 0    # 工具系
    USER = 1   # 用户系
    WORLD = 2  # 世界系


class ForceAxisMode(IntEnum):
    """力控轴模式 / Force control axis mode."""

    POSITION = 0   # 位控: 跟踪规划轨迹
    FORCE = 1      # 力控: 跟踪期望力 F_des
    COMPLIANT = 2  # 柔顺: 导纳/阻抗顺从


class ForceHealth(IntEnum):
    """力控数据健康状态 / Force control data health status."""

    OK = 0          # 正常
    INVALID = 1     # 数值无效 (NaN/Inf)
    TIMEOUT = 2     # 超时
    SATURATED = 3   # 饱和
    PACKET_LOSS = 4 # 丢包超限


@dataclass
class ForceControlState:
    """力控实时状态 / Force control real-time state (returned by GetForceState).

    六维顺序: [X, Y, Z, RX, RY, RZ]
    力/力矩: N / N·m
    """

    enabled: bool = False               # 已进入力控
    pending: bool = False               # 已受理请求、尚未进入
    algo: int = 0                       # 当前算法 (ForceControlAlgo)
    valid: bool = False                 # 外力数据有效性
    is_contact: bool = False            # 接触判据
    is_overforce: bool = False          # 过力判据
    health: int = 0                     # 数据健康状态 (ForceHealth)
    wrench_tcp: List[float] = field(default_factory=lambda: [0.0] * 6)    # TCP 系外力 [Fx,Fy,Fz,Mx,My,Mz]
    wrench_base: List[float] = field(default_factory=lambda: [0.0] * 6)   # 基座系外力
    desired_wrench: List[float] = field(default_factory=lambda: [0.0] * 6) # 期望力 F_des
    track_error: List[float] = field(default_factory=lambda: [0.0] * 6)   # 力跟踪误差
    axis_mode: List[int] = field(default_factory=lambda: [0] * 6)         # 选择矩阵 S 快照

    @classmethod
    def from_db(cls, db: dict) -> 'ForceControlState':
        """从协议响应 db 构造 / Construct from protocol response db."""
        return cls(
            enabled=db.get('enabled', False),
            pending=db.get('pending', False),
            algo=db.get('algo', 0),
            valid=db.get('valid', False),
            is_contact=db.get('isContact', False),
            is_overforce=db.get('isOverforce', False),
            health=db.get('health', 0),
            wrench_tcp=db.get('wrenchTcp', [0.0] * 6),
            wrench_base=db.get('wrenchBase', [0.0] * 6),
            desired_wrench=db.get('desiredWrench', [0.0] * 6),
            track_error=db.get('trackError', [0.0] * 6),
            axis_mode=db.get('axisMode', [0] * 6),
        )


# =============================================================================
# 5. 运动控制模型 / Motion Control Models
# =============================================================================

class MotionType(str, Enum):
    """高级运动指令类型 / Advanced Motion Type."""
    MOVJ = "movJ"
    MOVL = "movL"
    MOVC = "movC"
    MOVCIRCLE = "movCircle"


class JogMode(IntEnum):
    """点动模式 / Jog Mode."""
    JOINT = 1   # 关节点动 / Joint jog
    LINEAR = 2  # 直线点动 / Linear jog


class JogCoorType(IntEnum):
    """点动坐标系 / Jog Coordinate Type."""
    USER = 0
    TOOL = 1


class MoveToType(IntEnum):
    """MoveTo 预设运动类型 / MoveTo Type."""
    STOP = -1     # 停止 MoveTo
    HOME = 0      # Home 点
    SAFE = 1      # 安全位
    CANDLE = 2    # 蜡烛位
    PACK = 3      # 打包位
    JOINT = 4     # 关节规划
    LINEAR = 5    # 直线规划
    RESUME = 6    # 程序恢复点


@dataclass
class JointPoint:
    """
    关节目标（度）。业务层用于声明「这是六轴关节角」，避免与 TCP 位姿混淆。
    """

    jp: List[float]

    @classmethod
    def Degrees(cls, joints_deg: Sequence[float]) -> JointPoint:
        """由六轴关节角（度）构造。"""
        return cls(jp=[float(x) for x in joints_deg])


@dataclass
class CartesianPoint:
    """
    笛卡尔目标（mm + 度）。``cp`` 必填；``rj`` 可选（打包时缺省为控制器默认参考关节）。
    """

    cp: List[float]
    rj: Optional[List[float]] = None

    @classmethod
    def MmDeg(cls, pose_mm_deg: Sequence[float]) -> CartesianPoint:
        """TCP 位姿 [x,y,z,rx,ry,rz]（mm + 度），无参考关节。"""
        return cls(cp=[float(x) for x in pose_mm_deg])

    @classmethod
    def MmDegWithRef(
        cls,
        pose_mm_deg: Sequence[float],
        ref_joints_deg: Sequence[float],
    ) -> CartesianPoint:
        """TCP 位姿 + 逆解参考关节（度）；movJ/movL 到 TCP 且在意姿态解时推荐。"""
        return cls(
            cp=[float(x) for x in pose_mm_deg],
            rj=[float(x) for x in ref_joints_deg],
        )


def _target_to_move_point(target: Union[JointPoint, CartesianPoint]) -> MovePoint:
    if isinstance(target, JointPoint):
        return MovePoint.FromJoint(target)
    if isinstance(target, CartesianPoint):
        return MovePoint.FromCartesian(target)
    raise TypeError(
        f"expected JointPoint or CartesianPoint, got {type(target).__name__}"
    )


def _resolve_move_point(
    point: Union[MovePoint, JointPoint, CartesianPoint],
) -> MovePoint:
    if isinstance(point, MovePoint):
        return point
    return _target_to_move_point(point)


@dataclass
class MovePoint:
    """
    通用运动点位定义 / General Motion Point Definition.

    Attributes:
        jp (Optional[Sequence[float]]): 关节角列表 [j1...j6] / Joint angles.
        cp (Optional[Sequence[float]]): 笛卡尔坐标 [x,y,z,a,b,c] / Cartesian pose.
        rj (Optional[Sequence[float]]): 逆解参考关节角 / Reference joint angles for IK.
        ep (Optional[Sequence[float]]): 外部轴位置 / External axis positions.
    """
    jp: Optional[Sequence[float]] = None
    cp: Optional[Sequence[float]] = None
    rj: Optional[Sequence[float]] = None
    ep: Optional[Sequence[float]] = None

    @classmethod
    def FromJoint(cls, joint: JointPoint) -> MovePoint:
        """由 ``JointPoint`` 构造协议路点（仅 ``jp``）。"""
        return cls(jp=list(joint.jp))

    @classmethod
    def FromCartesian(cls, cart: CartesianPoint) -> MovePoint:
        """由 ``CartesianPoint`` 构造协议路点（``cp`` / 可选 ``rj``）。"""
        return cls(
            cp=list(cart.cp),
            rj=list(cart.rj) if cart.rj is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        序列化为 ``Robot/move`` 路点字典（经 ``pack_move_point``，与 C++ 一致）。

        须满足 jp 优先、笛卡尔缺省 rj 等规则；勿绕过本方法手写 targetPoint 字段。
        """
        from .robot_motion import pack_move_point

        return pack_move_point(self)


@dataclass
class MoveInstruction:
    """
    单段 ``Robot/move`` 指令（C# ``MoveInstruction`` / C++ ``ClientMoveInstruction``）。

    请用类方法 ``MovJ`` / ``MovL`` / ``MovC`` / ``MovCircle`` 构建，勿手写 ``type`` + 裸 ``MovePoint``。
    """

    motion_type: MotionType
    target: MovePoint
    speed: float
    acc: float
    blend: Optional[float] = None
    relative_blend: Optional[float] = None
    middle: Optional[MovePoint] = None
    circle_num: Optional[int] = None
    coor: Optional[Sequence[float]] = None
    tool: Optional[Sequence[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        from .robot_motion import pack_instruction

        return pack_instruction(
            self.motion_type,
            self.target,
            self.speed,
            self.acc,
            blend=self.blend,
            relative_blend=self.relative_blend,
            middle=self.middle,
            circle_num=self.circle_num,
            coor=self.coor,
            tool=self.tool,
        )

    @classmethod
    def MovJ(
        cls,
        target: Union[JointPoint, CartesianPoint],
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> MoveInstruction:
        """关节运动 movJ；目标可为关节或 TCP。"""
        return cls(
            MotionType.MOVJ,
            _target_to_move_point(target),
            speed,
            acc,
            blend=blend,
            relative_blend=relative_blend,
            coor=coor,
            tool=tool,
        )

    @classmethod
    def MovL(
        cls,
        target: Union[CartesianPoint, JointPoint],
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> MoveInstruction:
        """直线运动 movL；目标可为 TCP 或关节。"""
        return cls(
            MotionType.MOVL,
            _target_to_move_point(target),
            speed,
            acc,
            blend=blend,
            relative_blend=relative_blend,
            coor=coor,
            tool=tool,
        )

    @classmethod
    def MovC(
        cls,
        middle: CartesianPoint,
        target: CartesianPoint,
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> MoveInstruction:
        """圆弧运动 movC（中间点与目标均为 TCP）。"""
        return cls(
            MotionType.MOVC,
            MovePoint.FromCartesian(target),
            speed,
            acc,
            blend=blend,
            relative_blend=relative_blend,
            middle=MovePoint.FromCartesian(middle),
            coor=coor,
            tool=tool,
        )

    @classmethod
    def MovCircle(
        cls,
        middle: CartesianPoint,
        target: CartesianPoint,
        circle_num: int,
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> MoveInstruction:
        """整圆运动 movCircle。"""
        return cls(
            MotionType.MOVCIRCLE,
            MovePoint.FromCartesian(target),
            speed,
            acc,
            blend=blend,
            relative_blend=relative_blend,
            middle=MovePoint.FromCartesian(middle),
            circle_num=circle_num,
            coor=coor,
            tool=tool,
        )


@dataclass
class MoveToTarget:
    """
    MoveTo 专用目标结构（C# ``MoveToTarget`` / ``Robot/moveTo`` 的 target 字段）。
    """

    cp: Optional[Sequence[float]] = None
    jp: Optional[Sequence[float]] = None
    ep: Sequence[float] = field(default_factory=list)

    @classmethod
    def Joint(cls, joint: JointPoint) -> MoveToTarget:
        """关节目标（度）。"""
        return cls(jp=list(joint.jp))

    @classmethod
    def Cartesian(cls, cart: CartesianPoint) -> MoveToTarget:
        """笛卡尔目标（mm + 度）；``moveTo`` 协议不使用 ``rj``。"""
        return cls(cp=list(cart.cp))

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"ep": list(self.ep)}
        if self.cp is not None:
            d["cp"] = list(self.cp)
        if self.jp is not None:
            d["jp"] = list(self.jp)
        return d


@dataclass
class MotionWaitOptions:
    """
    阻塞运动等待参数（C# ``MotionWaitOptions``）。

    用于 ``MoveSync`` / ``MovJSync`` / ``MovLSync`` / ``MovCSync`` / ``MovCircleSync``
    控制 CRI 轮询行为。

    v2.1.8：完成判定仅依据 CRI ``InMotion`` 标志，已移除容差字段。

    Attributes:
        timeout: 整体等待超时（秒），默认 60。
        poll_interval: 轮询间隔（秒），默认 0.05。
        cri_stale_timeout: CRI 数据过期判定（秒），默认 0.5。
        settled_samples: ``InMotion=False`` 连续稳定采样数，默认 3。
    """
    timeout: float = 60.0
    poll_interval: float = 0.05
    cri_stale_timeout: float = 0.5
    settled_samples: int = 3


# =============================================================================
# 5. CRI 实时接口模型 / CRI Real-time Models
# =============================================================================

class CriMask(IntFlag):
    """
    CRI 推送位掩码（与 C# CRI mask 语义一致）。
    """
    TIMESTAMP = 1 << 0
    STATUS_1 = 1 << 1
    STATUS_2 = 1 << 2
    JOINT_POS = 1 << 8
    JOINT_VEL = 1 << 9
    CARTESIAN_POS = 1 << 10
    CARTESIAN_VEL = 1 << 11
    TCP_SPEED = 1 << 12
    JOINT_TORQUE = 1 << 13
    EXTERNAL_TORQUE = 1 << 14
    EXTRA_AXIS_POS = 1 << 15


class CriFilterType(IntEnum):
    """CRI 实时控制滤波类型（C# 同名枚举语义）。"""
    NONE = 0
    AVERAGE = 1
    LOW_PASS = 2
    ELLIPTIC = 3


@dataclass
class CriStatus:
    """
    CRI 状态位解析（C# 侧 status 结构；原始字见 ``status1_raw`` / ``status2_raw``）。
    """

    status1_raw: int = 0
    status2_raw: int = 0
    project_running: bool = False
    project_stopped: bool = False
    project_paused: bool = False
    is_enabling: bool = False
    is_disabled: bool = False
    is_manual: bool = False
    is_dragging: bool = False
    is_moving: bool = False
    collision_stop: bool = False
    is_at_safe_pos: bool = False
    has_alarm: bool = False
    is_simulation: bool = False
    is_emergency_stop: bool = False
    is_rescue: bool = False
    is_auto: bool = False
    is_remote: bool = False

    rt_control_mode: bool = False
    error_code: int = 0

    @property
    def real_time_control_mode(self) -> bool:
        """C# ``RealTimeControlMode`` 位语义（同 ``rt_control_mode``）。"""
        return self.rt_control_mode

    @property
    def cri_error_code(self) -> int:
        """C# ``CriErrorCode``（高 8 位解析，同 ``error_code``）。"""
        return self.error_code


@dataclass
class CriRealTimeData:
    """
    CRI 解析后实时数据（C# ``CriRealTimeData``，毫米 + 度；与 AGENTS.md §2.3.4 对齐）。

    存储字段沿用历史 Python 名；文档属性（``TimestampMs`` 等）通过只读 property 暴露。
    """

    timestamp: int = 0
    status: CriStatus = field(default_factory=CriStatus)
    joint_pos: List[float] = field(default_factory=list)
    joint_vel: List[float] = field(default_factory=list)
    cartesian_pos: List[float] = field(default_factory=list)
    cartesian_vel: List[float] = field(default_factory=list)
    tcp_speed: float = 0.0
    joint_torque: List[float] = field(default_factory=list)
    external_torque: List[float] = field(default_factory=list)
    extra_axis_pos: List[float] = field(default_factory=list)

    @property
    def timestamp_ms(self) -> int:
        return self.timestamp

    @property
    def joint_position(self) -> List[float]:
        return self.joint_pos

    @property
    def joint_velocity(self) -> List[float]:
        return self.joint_vel

    @property
    def tcp_pose(self) -> List[float]:
        return self.cartesian_pos

    @property
    def tcp_velocity(self) -> List[float]:
        return self.cartesian_vel

    @property
    def tcp_linear_velocity(self) -> float:
        return self.tcp_speed

    @property
    def joint_output_torque(self) -> List[float]:
        return self.joint_torque

    @property
    def joint_external_force(self) -> List[float]:
        return self.external_torque

    @property
    def external_axis_position(self) -> List[float]:
        return self.extra_axis_pos


# --- 历史别名（旧代码/示例）；新代码请用 CommonResponse / CriRealTimeData / Cri* ---
CodroidResponse = CommonResponse
CRIStatus = CriStatus
CRIData = CriRealTimeData
CRIMask = CriMask
CRIFilterType = CriFilterType


class MotionPath:
    """
    运动路径构建器（过渡 API；新代码优先 ``list[MoveInstruction]`` + ``Move()``）。

    接受 ``MovePoint`` / ``JointPoint`` / ``CartesianPoint``，内部统一经 ``pack_instruction`` 打包。
    """

    def __init__(self):
        self._commands: List[Dict[str, Any]] = []

    def add(self, instruction: MoveInstruction) -> MotionPath:
        """追加由 ``MoveInstruction`` 工厂构建的一段指令。"""
        self._commands.append(instruction.to_dict())
        return self

    def _add_item(
        self,
        m_type: MotionType,
        target: Union[MovePoint, JointPoint, CartesianPoint],
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
        middle: Optional[Union[MovePoint, JointPoint, CartesianPoint]] = None,
        circle_num: Optional[int] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> MotionPath:
        from .robot_motion import pack_instruction

        resolved_middle = (
            _resolve_move_point(middle) if middle is not None else None
        )
        item = pack_instruction(
            m_type,
            _resolve_move_point(target),
            speed,
            acc,
            blend=blend,
            relative_blend=relative_blend,
            middle=resolved_middle,
            circle_num=circle_num,
            coor=coor,
            tool=tool,
        )
        self._commands.append(item)
        return self

    def MovJ(
        self,
        target: Union[MovePoint, JointPoint, CartesianPoint],
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
    ) -> MotionPath:
        """添加关节运动 movJ。"""
        return self._add_item(MotionType.MOVJ, target, speed, acc, blend, relative_blend=relative_blend)

    def MovL(
        self,
        target: Union[MovePoint, JointPoint, CartesianPoint],
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
    ) -> MotionPath:
        """添加直线运动 movL。"""
        return self._add_item(MotionType.MOVL, target, speed, acc, blend, relative_blend=relative_blend)

    def MovC(
        self,
        target: Union[CartesianPoint, Sequence[float]],
        middle: Union[CartesianPoint, Sequence[float]],
        speed: float,
        acc: float,
        blend: Optional[float] = None,
        relative_blend: Optional[float] = None,
    ) -> MotionPath:
        """添加圆弧运动 movC（目标与中间点均为 TCP）。"""
        target_mp = (
            MovePoint.FromCartesian(target)
            if isinstance(target, CartesianPoint)
            else MovePoint(cp=list(target))
        )
        middle_mp = (
            MovePoint.FromCartesian(middle)
            if isinstance(middle, CartesianPoint)
            else MovePoint(cp=list(middle))
        )
        return self._add_item(
            MotionType.MOVC,
            target_mp,
            speed,
            acc,
            blend,
            relative_blend=relative_blend,
            middle=middle_mp,
        )

    def clear(self):
        """清空所有路径点 / Clear all points."""
        self._commands = []

    def get_commands(self) -> List[Dict[str, Any]]:
        """获取构建好的指令列表 / Get the built command list."""
        return self._commands

# 实时控制指令结构 (64字节)
# struct CommandData { Int64, Float64[6], UInt8, UInt8[7] }
CRI_COMMAND_STRUCT = Struct("<q6dB7B")