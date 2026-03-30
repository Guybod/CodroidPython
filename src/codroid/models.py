# src/codroid/models.py
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
class CodroidResponse:
    """
    SDK 通用响应对象 / Universal SDK Response Object.

    Attributes:
        id (Union[int, str]): 请求的唯一标识 ID / Unique request ID.
        ty (str): 接口类型名称 / Interface type name.
        db (Optional[Any]): 接口返回的具体数据内容 / Data returned by the interface.
        err (Optional[Any]): 错误信息。若为 None 则表示操作成功 / Error message, None if successful.
    """
    id: Union[int, str]
    ty: str
    db: Optional[Any] = None
    err: Optional[Any] = None

    @property
    def is_success(self) -> bool:
        """
        判断请求是否成功 / Check if the request was successful.
        """
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
# 4. 运动控制模型 / Motion Control Models
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
    HOME = 0      # Home 点
    SAFE = 1      # 安全位
    CANDLE = 2    # 蜡烛位
    PACK = 3      # 打包位
    JOINT = 4     # 关节规划
    LINEAR = 5    # 直线规划
    RESUME = 6    # 程序恢复点


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

    def to_dict(self) -> Dict[str, Any]:
        """过滤空字段，防止后端崩溃 / Filter None to prevent server crash."""
        d = {}
        if self.jp is not None: d["jp"] = list(self.jp)
        if self.cp is not None: d["cp"] = list(self.cp)
        if self.rj is not None: d["rj"] = list(self.rj)
        if self.ep is not None: d["ep"] = list(self.ep)
        return d


@dataclass
class MoveTarget:
    """
    MoveTo 专用目标结构 / MoveTo Target Structure.
    """
    cp: Optional[Sequence[float]] = None
    jp: Optional[Sequence[float]] = None
    ep: Sequence[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"ep": list(self.ep)}
        if self.cp is not None: d["cp"] = list(self.cp)
        if self.jp is not None: d["jp"] = list(self.jp)
        return d

# =============================================================================
# 5. CRI 实时接口模型 / CRI Real-time Models
# =============================================================================

class CRIMask(IntFlag):
    """
    CRI 推送掩码 (位操作) / CRI Push Mask (Bitmask).
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


class CRIFilterType(IntEnum):
    """CRI 实时控制滤波类型 / CRI Filter Type."""
    NONE = 0
    AVERAGE = 1
    LOW_PASS = 2
    ELLIPTIC = 3


@dataclass
class CRIStatus:
    """
    详细的机器人系统状态解析结果 / Detailed Robot System Status.
    """
    # 状态数据 1 - 系统标志
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

    # 状态数据 2 - 实时控制相关
    rt_control_mode: bool = False
    error_code: int = 0


@dataclass
class CRIData:
    """
    CRI 完整实时数据包 / CRI Full Real-time Data Packet.
    """
    timestamp: int = 0
    status: CRIStatus = field(default_factory=CRIStatus)
    joint_pos: List[float] = field(default_factory=list)
    joint_vel: List[float] = field(default_factory=list)
    cartesian_pos: List[float] = field(default_factory=list)
    cartesian_vel: List[float] = field(default_factory=list)
    tcp_speed: float = 0.0
    joint_torque: List[float] = field(default_factory=list)
    external_torque: List[float] = field(default_factory=list)
    extra_axis_pos: List[float] = field(default_factory=list)


class MotionPath:
    """
    运动路径构建器 / Motion Path Builder.
    用于组合多个运动指令（movJ, movL, movC等）并一次性发送。
    """
    def __init__(self):
        self._commands: List[Dict[str, Any]] = []

    def _add_item(
        self, 
        m_type: MotionType,
        target: MovePoint,
        speed: float,
        acc: float,
        blend: float = 0.0,
        relative_blend: int = 0,
        middle: Optional[MovePoint] = None,
        circle_num: Optional[int] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None
    ) -> MotionPath:
        """核心构建逻辑，处理字段过滤防止后端崩溃"""
        item: Dict[str, Any] = {
            "type": m_type.value,
            "speed": speed,
            "acc": acc,
            "blend": blend,
            "relativeBlend": relative_blend,
            "targetPoint": target.to_dict()
        }
        
        if middle:
            item["middlePoint"] = middle.to_dict()
        if circle_num is not None:
            item["circleNum"] = circle_num
            
        # ⚠️ 修复后端 Bug：如果 coor/tool 为空或 None，不发送该字段
        if coor and len(coor) > 0:
            item["coor"] = list(coor)
        if tool and len(tool) > 0:
            item["tool"] = list(tool)
            
        self._commands.append(item)
        return self # 支持链式调用

    def mov_j(self, target: MovePoint, speed: float, acc: float, blend: float = 0.0) -> MotionPath:
        """添加关节运动 / Add joint motion."""
        return self._add_item(MotionType.MOVJ, target, speed, acc, blend)

    def mov_l(self, target: MovePoint, speed: float, acc: float, blend: float = 0.0) -> MotionPath:
        """添加直线运动 / Add linear motion."""
        return self._add_item(MotionType.MOVL, target, speed, acc, blend)

    def mov_c(self, target_cp: Sequence[float], middle_cp: Sequence[float], speed: float, acc: float, blend: float = 0.0) -> MotionPath:
        """添加圆弧运动 / Add circular arc motion."""
        return self._add_item(
            MotionType.MOVC, 
            MovePoint(cp=list(target_cp)), 
            speed, acc, blend, 
            middle=MovePoint(cp=list(middle_cp))
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