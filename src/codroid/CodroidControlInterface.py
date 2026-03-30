from typing import Any, Dict, List, Literal, Union, Sequence
from .network import JsonStreamClient
from .exceptions import CodroidError
from .models import *
from .utils import is_valid_variable_name

class CodroidControlInterface:
    """
    Codroid 机器人控制接口 / Codroid Robot Control Interface.
    """
    
    def __init__(self, host: str = "192.168.1.136", port: int = 9001):
        """
        初始化控制接口 / Initialize the control interface.

        Args:
            host (str): 机器人 IP 地址 / Robot IP address.
            port (int): 端口号 (默认 9001) / Port number (default 9001).
        """
        self._net = JsonStreamClient(host, port)
        self._id_counter = 1
        self.debug = False

    def _send_command(self, ty: str, db: Any = None) -> CodroidResponse:
        """
        内部指令发送逻辑 / Internal command transmission logic.

        Args:
            ty (str): 请求类型 / Request type.
            db (Any): 请求数据 / Request data.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        self._id_counter += 1
        # 构造请求模型
        request = CodroidRequest(id=self._id_counter, ty=ty, db=db)
        
        # 转换为字典并发送 (排除 db 为 None 的情况可根据具体接口微调)
        payload: Dict[str, Any] = {
            "id": request.id,
            "ty": request.ty
        }
        # 只有当 db 确实有值时，才放入 payload
        if request.db is not None:
            payload["db"] = request.db

        if self.debug:
            print(payload)
        self._net.send(payload)
        raw_res = self._net.receive_one()
        
        # 将原始字典映射到 CodroidResponse 模型
        response = CodroidResponse(
            id=raw_res.get("id", 0),
            ty=raw_res.get("ty", ""),
            db=raw_res.get("db"),
            err=raw_res.get("err")
        )

        # 协议要求：检查响应中的 err 字段处理错误
        if not response.is_success:
            # 你可以选择抛出异常，或者让用户自己判断 is_success
            # 为了 SDK 的易用性，建议捕获到 err 就抛出异常
            raise CodroidError(f"API Error [{response.ty}]: {response.err}")
        
        return response

    # --- 连接管理 / Connection Management ---

    def connect(self) -> "CodroidControlInterface":
        """
        建立 TCP 连接 / Establish TCP connection.

        Returns:
            CodroidControlInterface: 返回自身以支持链式调用 / Returns self for chaining.
        """
        self._net.connect()
        return self

    def close(self):
        """
        关闭连接 / Close connection.
        """
        self._net.close()

    def disconnect(self):
        """
        断开连接 (close 的别名) / Disconnect (alias for close).
        """
        self.close()

    # --- 接口实现 ---

    def __run_script(self, main_script: str, vars: Dict[str, Any] | None = None) -> CodroidResponse:
        """
        2.1 运行脚本 / Run script.

        Args:
            main_script (str): Lua 脚本代码 / Lua script code.
            vars (Dict[str, Any] | None): 脚本共享变量 / Shared variables for the script.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        db = {
            "scripts": {"main": main_script},
            "vars": vars or {}
        }
        return self._send_command("project/runScript", db)

    def enter_remote_script_mode(self) -> CodroidResponse:
        """
        2.2 进入远程脚本模式 / Enter remote script mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/enterRemoteScriptMode")

    def run_project(self, project_id: str) -> CodroidResponse:
        """
        2.3 运行指定工程 / Run specified project.

        Args:
            project_id (str): 工程唯一标识 ID / Unique project ID.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/run", {"id": project_id})

    def run_project_by_index(self, index: int) -> CodroidResponse:
        """
        2.4 通过索引号运行工程 / Run project by index.

        Args:
            index (int): 工程映射索引号 / Project mapping index.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/runByIndex", index)

    def run_step(self,projectID: str) -> CodroidResponse:
        """
        2.5 单步运行 / run project with step.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        db = {"id":projectID}
        return self._send_command("project/run",db)

    def pause_project(self) -> CodroidResponse:
        """
        2.6 暂停工程 / Pause project.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/pause")

    def resume_project(self) -> CodroidResponse:
        """
        2.7 恢复运行 / Resume project.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/resume")

    def stop_project(self) -> CodroidResponse:
        """
        2.8 停止运行 / Stop project.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/stop")

    def set_start_line(self, line: int) -> CodroidResponse:
        """
        2.13 设置启动行 / Set start line.

        Args:
            line (int): 主程序开始执行的行号 / Starting line number.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/setStartLine", line)

    def clear_start_line(self) -> CodroidResponse:
        """
        2.14 清除启动行设置 / Clear start line setting.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("project/clearStartLine")

    def get_global_vars(self):
        """
        3.2 获取全局变量 / Get global variables.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("globalVar/getVars")

    def save_global_variables(self, variables: Dict[str, GlobalVariable]) -> CodroidResponse:
        """
        3.3 保存全局变量 / Save global variables.

        Args:
            variables (Dict[str, GlobalVariable]): 变量名与变量对象的映射 / Map of variable names to GlobalVariable objects.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        db_payload = {}
        
        for var_name, var_obj in variables.items():
            # 1. 校验变量名是否合法
            if not is_valid_variable_name(var_name):
                raise CodroidError(f"非法变量名 / Illegal variable name: '{var_name}'")
            
            # 2. 转换数据格式
            db_payload[var_name] = var_obj.to_robot_format()
            
        return self._send_command("globalVar/saveVars", db_payload)
    
    def remove_global_variables(self, names: List[str]) -> CodroidResponse:
        """
        3.4 删除全局变量 / Remove global variables.

        Args:
            names (List[str]): 要删除的变量名列表 / List of variable names to remove.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        # 校验变量名合法性
        for name in names:
            if not is_valid_variable_name(name):
                raise CodroidError(f"试图删除非法的变量名 / Illegal variable name: '{name}'")
                
        return self._send_command("globalVar/removeVars", names)

    def get_project_var(self):
        """
        4.1 获取当前所有工程变量值(仅在工程运行中有效) / Get the values of all current project variables (only valid when the project is running)

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("globalVar/GetProjectVarUpdate")

    def rs485_init(
        self, baudrate: Union[RS485BaudRate, int], 
        stop_bit: RS485StopBits = RS485StopBits.ONE, 
        parity: RS485Parity = RS485Parity.NONE
    ) -> CodroidResponse:
        """
        5.1 初始化末端 485 / Initialize RS485.

        Args:
            baudrate (int): 波特率 / Baud rate.
            stop_bit (RS485StopBits): 停止位 (1或2) / Stop bits (1 or 2).
            parity (RS485Parity): 校验位 / Parity mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        db = {
            "baudrate": int(baudrate),
            "stopBit": int(stop_bit),  # 确保转为整数
            "dataBit": 8,
            "parity": int(parity)      # 确保转为整数
        }
        return self._send_command("EC2RS485/init", db)

    def rs485_flush(self) -> CodroidResponse:
        """
        5.2 清空 485 读取缓存 / Flush RS485 read buffer.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("EC2RS485/flushReadBuffer")

    def rs485_read(self, length: int, timeout: int = 3000) -> CodroidResponse:
        """
        5.3 读取 485 数据 / Read RS485 data.

        Args:
            length (int): 读取字节数 (max 128) / Bytes to read (max 128).
            timeout (int): 超时时间 ms (max 3000) / Timeout in ms (max 3000).

        Returns:
            CodroidResponse: 响应对象，db 字段为字节数组 / Response object, 'db' field is a list of bytes.
        """
        if length > 128:
            raise CodroidError("单次读取长度不能超过 128 字节")
        if timeout > 3000:
            timeout = 3000
            
        db = {
            "length": length,
            "timeout": timeout
        }
        return self._send_command("EC2RS485/read", db)

    def rs485_write(self, data: Union[List[int], bytes]) -> CodroidResponse:
        """
        5.4 发送 485 数据 / Write RS485 data.

        Args:
            data (Union[List[int], bytes]): 要发送的数据 / Data to send.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        # 如果用户传的是 bytes，转换成 list[int]
        if isinstance(data, bytes):
            send_data = list(data)
        else:
            send_data = data

        if len(send_data) > 127:
            raise CodroidError("单次发送数据长度不能超过 127 字节 / Write length cannot exceed 127 bytes")
            
        return self._send_command("EC2RS485/write", send_data)

    # --- 10. 机器人计算接口 / Robot Calculation ---

    def forward_kinematics(
        self, 
        jp: Sequence[float], 
        coor: Optional[Sequence[float]] = None, 
        tool: Optional[Sequence[float]] = None, 
        ep: Sequence[float] = []
    ) -> CodroidResponse:
        """
        10.1 正解计算 (关节空间 -> 笛卡尔空间) / Forward Kinematics.

        Args:
            jp (Sequence[float]): 6个关节角 [j1...j6], 单位: deg / 6 joint angles in deg.
            coor (Optional[Sequence[float]]): 用户坐标系 [x,y,z,a,b,c]，不传则不发送 / User coordinate system.
            tool (Optional[Sequence[float]]): 工具坐标系 [x,y,z,a,b,c]，不传则不发送 / Tool coordinate system.
            ep (Sequence[float]): 附加轴位置 / Additional axis positions.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        db: Dict[str, Any] = {
            "jp": jp,
            "ep": ep
        }
        # 动态字段处理：只有传了参数才发送对应字段
        if coor is not None:
            db["coor"] = coor
        if tool is not None:
            db["tool"] = tool
            
        return self._send_command("Robot/apostocpos", db)

    def inverse_kinematics(
        self, 
        cp: Sequence[float], 
        rj: Optional[Sequence[float]] = None, 
        ep: Sequence[float] = []
    ) -> CodroidResponse:
        """
        10.2 逆解计算 (笛卡尔空间 -> 关节空间) / Inverse Kinematics.

        Args:
            cp (Sequence[float]): 末端位置 [x,y,z,a,b,c] / TCP pose.
            rj (Optional[Sequence[float]]): 参考关节角，默认 [20,20,20,20,20,20] / Reference joint angles.
            ep (Sequence[float]): 附加轴位置 / Additional axis positions.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        # 处理默认参考关节角
        if rj is None:
            rj = [20.0, 20.0, 20.0, 20.0, 20.0, 20.0]
            
        db = {
            "cp": cp, 
            "rj": rj, 
            "ep": ep
        }
        return self._send_command("Robot/cpostoapos", db)

    def calculate_relative_pose(
        self,
        pos: Sequence[float],
        offset: Sequence[float],
        coor_type: CoordinateType = CoordinateType.TOOL,
        pos_coor: Optional[Sequence[float]] = None,
        coor: Optional[Sequence[float]] = None
    ) -> CodroidResponse:
        """
        10.3 笛卡尔坐标偏移计算 / Calculate relative pose.

        Args:
            pos (Sequence[float]): 当前末端TCP坐标 / Current TCP pose.
            offset (Sequence[float]): 偏移量 / Offset values.
            coor_type (CoordinateType): 坐标系类型 (USER 或 TOOL) / Coordinate type.
            pos_coor (Optional[Sequence[float]]): 当前末端TCP坐标系 / Current TCP coordinate system.
            coor (Optional[Sequence[float]]): 偏移坐标系 / Offset coordinate system.
        """
        db = {
            "pos": pos,
            "offset": offset,
            "coorType": coor_type.value  # 获取枚举对应的字符串 "user" 或 "tool"
        }
        if pos_coor is not None:
            db["posCoor"] = pos_coor
        if coor is not None:
            db["coor"] = coor
            
        return self._send_command("Robot/calculateRelativePose", db)

    # --- 11. 机器人运动控制接口 / Robot Motion Control ---

    def jog(
        self, 
        mode: JogMode, 
        index: int, 
        speed: float, 
        coor_type: JogCoorType = JogCoorType.USER, 
        coor_id: int = 1
    ) -> CodroidResponse:
        """
        11.1 启动机器人点动 / Start robot jogging.
        注意：需要每 500ms 调用一次 jog_heartbeat() 维持运动。

        Args:
            mode (JogMode): 点动模式 (JOINT/LINEAR).
            index (int): 关节序号(1-6) 或 直线轴序号(1-6对应xyzabc).
            speed (float): 速度 (-1.0 ~ 1.0).
            coor_type (JogCoorType): 坐标系类型 (USER/TOOL).
            coor_id (int): 用户坐标系 ID.
        """
        db = {
            "mode": int(mode),
            "speed": max(min(speed, 1.0), -1.0),
            "index": index,
            "coorType": int(coor_type),
            "coorId": coor_id
        }
        return self._send_command("Robot/jog", db)

    def stop_jog(self) -> CodroidResponse:
        """
        11.2 停止点动 / Stop robot jogging.
        """
        return self._send_command("Robot/stopJog", "")

    def jog_heartbeat(self) -> CodroidResponse:
        """
        11.3 点动心跳 / Jog heartbeat.
        需在点动期间每隔 0.5s 发送一次。
        """
        return self._send_command("Robot/jogHeartbeat", "")

    def move_to(
        self, 
        move_type: MoveToType, 
        target: Optional[MoveTarget] = None
    ) -> CodroidResponse:
        """
        11.4 运动到指定位置 / Move to specified position.
        注意：启动后需每隔 0.5s 调用 move_to_heartbeat() 维持运动。

        Args:
            move_type (MoveToType): 预设位置类型或规划类型.
            target (Optional[MoveTarget]): 目标位置 (仅在类型为 JOINT 或 LINEAR 时需要).
        """
        db: Dict[str, Any] = {"type": int(move_type)}
        if target is not None:
            db["target"] = target.to_dict()
            
        return self._send_command("Robot/moveTo", db)

    def move_to_heartbeat(self) -> CodroidResponse:
        """
        11.5 moveTo 心跳 / MoveTo heartbeat.
        """
        return self._send_command("Robot/moveToHeartbeat")

    def set_manual_move_rate(self, rate: int) -> CodroidResponse:
        """
        11.6 设置手动运动倍率 / Set manual move rate.

        Args:
            rate (int): 速度百分比 / magnification range (1 ~ 100).
        """
        if not (1 <= rate <= 100):
            raise CodroidError("倍率范围必须在 1~100 之间 / The magnification range must be between 1 and 100")
        return self._send_command("Robot/setManualMoveRate", rate)

    def set_auto_move_rate(self, rate: int) -> CodroidResponse:
        """
        11.7 设置自动运动倍率 / Set auto move rate.

        Args:
            rate (int): 速度百分比 / magnification range (1 ~ 100).
        """
        if not (1 <= rate <= 100):
            raise CodroidError("倍率范围必须在 1~100 之间 / The magnification range must be between 1 and 100")
        return self._send_command("Robot/setAutoMoveRate", rate)

    def _send_move_commands(self, commands: List[Dict[str, Any]]) -> CodroidResponse:
        """内部通用方法：发送运动指令列表"""
        return self._send_command("Robot/move", commands)

    def _build_move_item(
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
    ) -> Dict[str, Any]:
        """构建单个运动指令字典，处理字段过滤逻辑"""
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
            
        # ⚠️ 关键 Bug 修复：仅当 coor/tool 有值时才发送字段
        if coor:
            item["coor"] = coor
        if tool:
            item["tool"] = tool
            
        return item

    # --- 11.8 拆分后的运动指令 ---

    def move_j(
        self, 
        target: MovePoint, 
        speed: float, 
        acc: float, 
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None
    ) -> CodroidResponse:
        """
        关节运动 (movJ)。
        """
        item = self._build_move_item(MotionType.MOVJ, target, speed, acc, blend, coor=coor, tool=tool)
        return self._send_move_commands([item])

    def move_l(
        self, 
        target: MovePoint, 
        speed: float, 
        acc: float, 
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None
    ) -> CodroidResponse:
        """
        直线运动 (movL)。
        """
        item = self._build_move_item(MotionType.MOVL, target, speed, acc, blend, coor=coor, tool=tool)
        return self._send_move_commands([item])

    def move_c(
        self, 
        target_cp: Sequence[float], 
        middle_cp: Sequence[float], 
        speed: float, 
        acc: float, 
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None
    ) -> CodroidResponse:
        """
        圆弧运动 (movC)。
        注意：必须传入笛卡尔坐标点 (cp)。
        """
        target = MovePoint(cp=target_cp)
        middle = MovePoint(cp=middle_cp)
        item = self._build_move_item(MotionType.MOVC, target, speed, acc, blend, middle=middle, coor=coor, tool=tool)
        return self._send_move_commands([item])

    def move_circle(
        self, 
        target_cp: Sequence[float], 
        middle_cp: Sequence[float], 
        speed: float, 
        acc: float, 
        circle_num: int = 1,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None
    ) -> CodroidResponse:
        """
        圆周运动 (movCircle)。
        """
        target = MovePoint(cp=target_cp)
        middle = MovePoint(cp=middle_cp)
        item = self._build_move_item(
            MotionType.MOVCIRCLE, target, speed, acc, 
            middle=middle, circle_num=circle_num, coor=coor, tool=tool
        )
        return self._send_move_commands([item])

    def execute_path(self, path: MotionPath) -> CodroidResponse:
        """
        11.8 执行运动路径 / Execute a motion path.

        Args:
            path (MotionPath): 构建好的路径对象 / Pre-built MotionPath object.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        commands = path.get_commands()
        if not commands:
            raise CodroidError("路径不能为空 / Path cannot be empty")
        return self._send_command("Robot/move", commands)

    # --- 11.9 - 11.11 运动控制 ---

    def pause_move(self) -> CodroidResponse:
        """11.9 暂停运动 / pause move"""
        return self._send_command("Robot/pause", "")

    def resume_move(self) -> CodroidResponse:
        """11.10 恢复运动 / resume move"""
        return self._send_command("Robot/resume", "")

    def stop_move(self) -> CodroidResponse:
        """11.11 停止运动 / stop move"""
        return self._send_command("Robot/stopMove", "")

    # --- 12. 机器人控制命令 / Robot Control Commands ---

    def switch_on(self) -> CodroidResponse:
        """
        12.1 上使能 / Enable the robot.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/switchOn", "")

    def switch_off(self) -> CodroidResponse:
        """
        12.2 下使能 / Disable the robot.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/switchOff", "")

    def to_manual(self) -> CodroidResponse:
        """
        12.3 进入手动模式 / Switch to manual mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        self.to_auto()
        return self._send_command("Robot/toManual", "")

    def to_auto(self) -> CodroidResponse:
        """
        12.4 进入自动模式 / Switch to auto mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toAuto", "")

    def to_remote(self) -> CodroidResponse:
        """
        12.5 进入远程模式 / Switch to remote mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        self.to_auto()
        return self._send_command("Robot/toRemote", "")

    def to_simulation(self) -> CodroidResponse:
        """
        12.7 进入仿真模式 / Switch to simulation mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toSimulation", "")

    def to_actual(self) -> CodroidResponse:
        """
        12.8 进入实机模式 / Switch to actual mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toActual", "")

    def start_drag(self) -> CodroidResponse:
        """
        12.9 进入拖拽模式 / Enable drag-and-teach mode.
        注意：只可在远程模式和手动模式下使用 / Note: Only available in remote or manual mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/startDrag", "")

    def stop_drag(self) -> CodroidResponse:
        """
        12.10 退出拖拽模式 / Disable drag-and-teach mode.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/stopDrag", "")

    def clear_error(self) -> CodroidResponse:
        """
        12.11 清除错误 / Clear system errors.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("System/clearError", "")

    # --- 13. 辅助校验方法 / Internal Validation ---

    def _validate_io(self, io_type: IOType, port: int):
        """校验端口范围 / Validate IO port range."""
        if io_type in (IOType.DI, IOType.DO):
            if not (0 <= port <= 15):
                raise CodroidError(f"数字 IO 端口范围错误: {port} (应为 0~15) / Digital IO port error.")
        elif io_type in (IOType.AI, IOType.AO):
            if not (0 <= port <= 3):
                raise CodroidError(f"模拟 IO 端口范围错误: {port} (应为 0~3) / Analog IO port error.")

    # --- 13.1 获取 IO 相关接口 / Get IO Interface ---

    def get_io_values(self, io_requests: List[Dict[str, Any]]) -> CodroidResponse:
        """
        13.1 获取多个 IO 的当前值 / Get multiple IO values.
        
        Args:
            io_requests: 包含 type 和 port 的列表，如 [{"type": "DI", "port": 0}]
        """
        for req in io_requests:
            self._validate_io(req["type"], req["port"])
        return self._send_command("IOManager/GetIOValue", io_requests)

    def get_di(self, port: int) -> int:
        """
        获取数字输入 (DI) 值 / Get Digital Input value.

        Args:
            port (int): 端口号 (0~15).

        Returns:
            int: 0 或 1 / 0 or 1.
        """
        res = self.get_io_values([{"type": IOType.DI, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return int(res.db[0]["value"])
        
        raise CodroidError(f"无法获取 DI{port} 的值，响应数据为空 / Failed to get DI value.")

    def get_do(self, port: int) -> int:
        """
        获取数字输出 (DO) 值 / Get Digital Output value.

        Args:
            port (int): 端口号 (0~15).

        Returns:
            int: 0 或 1 / 0 or 1.
        """
        res = self.get_io_values([{"type": IOType.DO, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return int(res.db[0]["value"])
            
        raise CodroidError(f"无法获取 DO{port} 的值 / Failed to get DO value.")

    def get_ai(self, port: int) -> float:
        """
        获取模拟输入 (AI) 值 / Get Analog Input value.

        Args:
            port (int): 端口号 (0~3).

        Returns:
            float: 模拟量值 / Analog value (double).
        """
        res = self.get_io_values([{"type": IOType.AI, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return float(res.db[0]["value"])
            
        raise CodroidError(f"无法获取 AI{port} 的值 / Failed to get AI value.")
    
    def get_ao(self, port: int) -> float:
        """
        获取模拟输出 (AO) 值 / Get Analog Output value.

        Args:
            port (int): 端口号 (0~3).

        Returns:
            float: 模拟量值 / Analog value (double).
        """
        res = self.get_io_values([{"type": IOType.AO, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return float(res.db[0]["value"])
            
        raise CodroidError(f"无法获取 AO{port} 的值 / Failed to get AO value.")

    # --- 13.2 写入 IO 相关接口 / Set IO Interface ---

    def set_do(self, port: int, value: int) -> CodroidResponse:
        """
        设置数字输出 (DO) 值 / Set Digital Output value.

        Args:
            port (int): 端口号 (0~15).
            value (int): 0 或 1.
        """
        self._validate_io(IOType.DO, port)
        if value not in (0, 1):
            raise CodroidError("数字输出值必须为 0 或 1 / Digital output value must be 0 or 1.")
        
        db = {"type": IOType.DO, "port": port, "value": value}
        return self._send_command("IOManager/SetIOValue", db)

    def set_ao(self, port: int, value: float) -> CodroidResponse:
        """
        设置模拟输出 (AO) 值 / Set Analog Output value.

        Args:
            port (int): 端口号 (0~3).
            value (float): 模拟输出值.
        """
        self._validate_io(IOType.AO, port)
        db = {"type": IOType.AO, "port": port, "value": value}
        return self._send_command("IOManager/SetIOValue", db)

    def set_io_values(self, io_list: List[Dict[str, Any]]) -> List[CodroidResponse]:
        """
        批量设置 IO 值 / Bulk set IO values.
        注：由于协议 13.2 是单点设置，此处通过循环调用实现。

        Args:
            io_list: 包含 type, port, value 的字典列表.
        """
        results = []
        for item in io_list:
            if item["type"] in (IOType.DO, IOType.DI): # 协议通常只写 DO/AO
                results.append(self.set_do(item["port"], item["value"]))
            else:
                results.append(self.set_ao(item["port"], item["value"]))
        return results

    # --- 14. 寄存器相关接口 / Register Interface ---

    def get_register_values(self, addresses: List[int]) -> CodroidResponse:
        """
        14.1 获取多个寄存器值 / Get multiple register values.

        Args:
            addresses (List[int]): 寄存器地址列表 / List of register addresses.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        return self._send_command("RegisterManager/GetRegisterValue", addresses)

    def get_register(self, address: int) -> Any:
        """
        快捷方法：获取单个寄存器值 / Get a single register value.

        Args:
            address (int): 寄存器地址 / Register address.

        Returns:
            Any: 寄存器的值 / The value of the register.
        """
        res = self.get_register_values([address])
        if res.db is not None and len(res.db) > 0:
            return res.db[0]["value"]
        raise CodroidError(f"无法获取寄存器 {address} 的值 / Failed to get register value.")

    def set_register_value(self, address: int, value: Any) -> CodroidResponse:
        """
        14.2 写入寄存器值 / Set a single register value.

        Args:
            address (int): 寄存器地址 / Register address.
            value (Any): 要写入的值 / Value to write.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        db = {"address": address, "value": value}
        return self._send_command("RegisterManager/SetRegisterValue", db)

    def set_extend_array_type(self, index: int, data_type: ExtendArrayType) -> CodroidResponse:
        """
        14.3 设置扩展数组数据类型 / Set extended array data type.

        Args:
            index (int): 数组索引 (0-999) / Array index (0-999).
            data_type (ExtendArrayType): 数据类型枚举 / Data type enum.

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        if not (0 <= index <= 999):
            raise CodroidError(f"扩展数组索引范围错误: {index} (应为 0~999) / Invalid index.")
        
        db = {
            "index": index,
            "type": data_type.value
        }
        return self._send_command("RegisterManager/setExtendArrayType", db)

    def remove_extend_array(self, index: int) -> CodroidResponse:
        """
        14.4 删除扩展数组索引 (重置数据) / Remove extended array index.

        Args:
            index (int): 数组索引 (0-999) / Array index (0-999).

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        if not (0 <= index <= 999):
            raise CodroidError(f"扩展数组索引范围错误: {index} (应为 0~999)")
            
        return self._send_command("RegisterManager/removeExtendArray", {"index": index})

    # --- 17. CRI 实时控制接口 / Codroid RealTime Interface ---

    def start_data_push(
        self, 
        ip: str, 
        port: int, 
        duration: int = 1, 
        high_precision: bool = False, 
        mask: CRIMask = CRIMask.TIMESTAMP | CRIMask.STATUS_1 | CRIMask.JOINT_POS | CRIMask.CARTESIAN_POS
    ) -> CodroidResponse:
        """
        17.2/17.4 开启数据流推送 / Start CRI data push.
        支持自动识别版本切换参数格式。

        Args:
            ip (str): 接收推送的本地 IP / Local IP to receive data.
            port (int): 接收端口 (1000-65534) / Port (1000-65534).
            duration (int): 推送周期 (ms) / Push interval in ms.
            high_precision (bool): 是否使用双精度浮点数 (8字节) / Use Float64 (8 bytes).
            mask (CRIMask): 数据推送掩码 / Data push mask.
        """
        if port<10000 or port>65535:
            raise CodroidError(f"接收端口 (1000-65534) / Port must in (1000-65534)")
        # 针对新版本（2.3.3.23+）构建 db
        db = {
            "ip": ip,
            "port": port,
            "duration": duration,
            "highPercision": high_precision,
            "mask": int(mask)
        }
        return self._send_command("CRI/StartDataPush", db)

    def stop_data_push(self, ip: Optional[str] = None, port: Optional[int] = None) -> CodroidResponse:
        """
        17.3/17.5 停止数据流推送 / Stop CRI data push.
        """
        db = {}
        if ip and port:
            db = {"ip": ip, "port": port}
        return self._send_command("CRI/StopDataPush", db if db else "")

    def start_realtime_control(
        self, 
        filter_type: CRIFilterType = CRIFilterType.NONE, 
        duration: int = 1, 
        start_buffer: int = 3
    ) -> CodroidResponse:
        """
        17.6 开启实时控制模式 / Start real-time control mode.

        Args:
            filter_type (CRIFilterType): 滤波类型 / Filter type.
            duration (int): 指令间隔 (1-16ms) / Command interval.
            start_buffer (int): 启动缓冲点数 (1-100) / Start buffer points.
        """
        db = {
            "filterType": int(filter_type),
            "duration": duration,
            "startBuffer": start_buffer
        }
        return self._send_command("CRI/StartControl", db)

    def stop_realtime_control(self) -> CodroidResponse:
        """
        17.7 关闭实时控制模式 / Stop real-time control mode.
        """
        return self._send_command("CRI/StopControl", "")

    # --- 19. 机器人设置相关接口 / Robot Settings ---

    def set_collision_sensitivity(self, sensitivity: int) -> CodroidResponse:
        """
        19.1 设置碰撞检测灵敏度 / Set collision detection sensitivity.
        仅 2.3.2.10 以上版本可用 / Only available in version 2.3.2.10+.

        Args:
            sensitivity (int): 灵敏度 (0-100)，数值越大越灵敏 / Sensitivity value (0-100).

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        if not (0 <= sensitivity <= 100):
            from .exceptions import CodroidError
            raise CodroidError("灵敏度范围必须在 0~100 之间 / Sensitivity must be between 0 and 100.")
            
        return self._send_command("Robot/setCollisionSensitivity", sensitivity)

    def set_payload(self, payload_id: int) -> CodroidResponse:
        """
        19.2 设置负载 / Set robot payload.
        仅 2.3.2.10 以上版本可用 / Only available in version 2.3.2.10+.

        Args:
            payload_id (int): 负载 ID (0-15) / Payload ID (0-15).

        Returns:
            CodroidResponse: 响应对象 / Response object.
        """
        if not (0 <= payload_id <= 15):
            from .exceptions import CodroidError
            raise CodroidError("负载 ID 范围必须在 0~15 之间 / Payload ID must be between 0 and 15.")
            
        return self._send_command("Robot/setPayload", payload_id)

    # 支持 with 语句
    def __enter__(self):
        self._net.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()