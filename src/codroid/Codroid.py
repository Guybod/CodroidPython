"""
协议会话与指令实现（原 ``CodroidControlInterface`` 模块；与 C# ``CodroidClient`` 能力对应）。

对外类：``CodroidSession``；``CodroidControlInterface`` 为兼容别名。
"""
from __future__ import annotations

import threading
import socket
import time
import warnings
from typing import Any, Dict, List, Literal, Optional, Union, Sequence, cast
from .async_tcp_client import JsonStreamClient
from .exceptions import CodroidError
from .define import *
from .utils import is_valid_variable_name
from .cri_realtime_packet_parser import CriRealtimePacketParser, CriStreamHandler


class CodroidSession:
    """
    TCP/UDP 协议会话与指令封装。

    C# 侧等价能力内聚于 ``CodroidClient``；Python 中 ``CodroidClient`` 继承本类并替换传输层。
    对外请优先使用 ``CodroidClient``；方法名与 AGENTS.md §4.1 词序一致（snake_case）。
    """
    
    def __init__(self, host: str = "192.168.1.136", port: int = 9001,
                 local_ip: str = "192.168.1.150", udp_port: int = 10086):
        """
        初始化控制接口 / Initialize the control interface.

        Args:
            host (str): 机器人 IP 地址 / Robot IP address.
            port (int): 端口号 (默认 9001) / Port number (default 9001).
        """
        self._net = JsonStreamClient(host, port)
        self._id_counter = 1
        self.debug = False
        # --- 新增属性 ---
        self.local_ip = local_ip
        self.udp_port = udp_port
        self.cri_cache: Optional[CriRealTimeData] = None  # 实时数据缓存
        self._cri_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _send_command(self, ty: str, db: Any = None) -> CommonResponse:
        """
        内部指令发送逻辑 / Internal command transmission logic.

        Args:
            ty (str): 请求类型 / Request type.
            db (Any): 请求数据 / Request data.

        Returns:
            CommonResponse: 响应对象 / Response object.
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
        if self.debug:
            print(f"[recv]: {raw_res}")

        # 将原始字典映射到 CommonResponse 模型
        response = CommonResponse(
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

    def connect(self) -> "CodroidSession":
        """
        建立 TCP 连接 / Establish TCP connection.

        Returns:
            CodroidSession: 返回自身以支持链式调用 / Returns self for chaining.
        """
        self._net.connect()

        return self

    def _stop_cri_receiver(self) -> None:
        """停止 CRI UDP 接收线程并释放绑定端口（避免 Address already in use）。"""
        self._stop_event.set()
        t = self._cri_thread
        self._cri_thread = None
        if t is not None and t.is_alive():
            t.join(timeout=5.0)

    def _start_cri_receiver(self, mask: int = 0xFFFF):
        """启动 UDP 接收线程"""
        self._stop_cri_receiver()
        self._stop_event.clear()
        self._cri_thread = threading.Thread(
            target=self._cri_receiver_loop, 
            daemon=True
        )
        self._cri_thread.start()

    def _cri_receiver_loop(self):
        """UDP 接收循环 (固定 308 字节布局，见 AGENTS.md §2.3)"""
        handler = CriStreamHandler(
            high_precision=True,
            mask=0xFFFF,
            joint_count=6,
            extra_axis_count=0,
        )

        try:
            handler.bind(self.udp_port)
            handler._sock.settimeout(1.0)
            print(f"UDP 监听已启动: {self.local_ip}:{self.udp_port}")  # 调试信息

            while not self._stop_event.is_set():
                try:
                    data, addr = handler._sock.recvfrom(2048)
                    if self.debug:
                        print(f"收到来自 {addr} 的数据，长度: {len(data)} 字节")
                    parsed = CriRealtimePacketParser.parse(data)
                    if parsed is None:
                        if self.debug:
                            print(f"跳过非 308 字节 CRI 包: {len(data)} 字节")
                        continue
                    self.cri_cache = parsed
                except socket.timeout:
                    continue
                except Exception as e:
                    if not self._stop_event.is_set():
                        print(f"CRI 数据接收或解析错误: {e}")
        finally:
            handler._sock.close()


    def close(self):
        """
        关闭连接 / Close connection.
        """
        try:
            self.stop_cri_data_push()
        finally:
            self._stop_cri_receiver()
            self._net.close()

    def disconnect(self):
        """
        断开连接 (close 的别名) / Disconnect (alias for close).
        """
        self.close()

    def get_cri_data(self) -> Optional[CriRealTimeData]:
        """最新 CRI 快照，等价 C# 侧 ``CriData`` 缓存（``cri_cache``）。"""
        return self.cri_cache

    def start_listen_udp(self): 
        try:            
            # 1. 先停止旧的推送
            self.stop_cri_data_push()
            time.sleep(0.1)
            
            # 2. 先在本地打开 UDP 监听端口
            self._start_cri_receiver() 
            
            # 3. 再通知机器人开始推送数据
            self.start_cri_data_push(ip=self.local_ip, port=self.udp_port)
            
            if self.debug:
                print(f"实时数据同步已开启，监听端口: {self.udp_port}")
                
        except Exception as e:
            # 二进制环境下，务必捕获并打印具体的异常
            print(f"UDP 监听启动失败: {type(e).__name__}: {e}")
            raise e

    # --- 接口实现 ---

    def run_script(self, main_script: str, vars: Optional[Dict[str, Any]] = None) -> CommonResponse:
        """
        2.1 运行脚本 / Run script（C# ``RunScript``）。

        Args:
            main_script (str): Lua 脚本代码 / Lua script code.
            vars: 脚本共享变量 / Shared variables for the script.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        db = {
            "scripts": {"main": main_script},
            "vars": vars or {}
        }
        return self._send_command("project/runScript", db)

    def __run_script(self, main_script: str, vars: Optional[Dict[str, Any]] = None) -> CommonResponse:
        """兼容旧代码调用 ``__run_script``。"""
        return self.run_script(main_script, vars)

    def enter_remote_script_mode(self) -> CommonResponse:
        """
        2.2 进入远程脚本模式 / Enter remote script mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/enterRemoteScriptMode")

    def run_project(self, project_id: str) -> CommonResponse:
        """
        2.3 运行指定工程 / Run specified project.

        Args:
            project_id (str): 工程唯一标识 ID / Unique project ID.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/run", {"id": project_id})

    def run_project_by_index(self, index: int) -> CommonResponse:
        """
        2.4 通过索引号运行工程 / Run project by index（C# ``RunByIndex``）。

        Args:
            index (int): 工程映射索引号 / Project mapping index.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/runByIndex", index)

    def run_step(self, project_id: str) -> CommonResponse:
        """
        2.5 单步运行（C# ``RunStep``）。
        """
        return self._send_command("project/run", {"id": project_id})

    def pause_project(self) -> CommonResponse:
        """
        2.6 暂停工程 / Pause project.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/pause")

    def resume_project(self) -> CommonResponse:
        """
        2.7 恢复运行 / Resume project.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/resume")

    def stop_project(self) -> CommonResponse:
        """
        2.8 停止运行 / Stop project.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/stop")

    def set_start_line(self, line: int) -> CommonResponse:
        """
        2.13 设置启动行 / Set start line.

        Args:
            line (int): 主程序开始执行的行号 / Starting line number.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/setStartLine", line)

    def clear_start_line(self) -> CommonResponse:
        """
        2.14 清除启动行设置 / Clear start line setting.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/clearStartLine")

    def get_global_vars(self):
        """
        3.2 获取全局变量 / Get global variables（C# ``GetGlobalVars``）。

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("globalVar/getVars")

    def get_global_vars_catalog(self):
        """
        C# ``GetGlobalVarsCatalog``：与 ``get_global_vars`` 相同 TCP 请求（``globalVar/getVars``）；
        C# 侧再经 ``GlobalVarCatalogParser`` 解析；Python 当前直接返回原始 ``CommonResponse``。
        """
        return self.get_global_vars()

    def save_global_vars(self, variables: Dict[str, GlobalVariable]) -> CommonResponse:
        """
        3.3 保存全局变量 / Save global variables（C# ``SaveGlobalVars``）。

        Args:
            variables (Dict[str, GlobalVariable]): 变量名与变量对象的映射 / Map of variable names to GlobalVariable objects.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        db_payload = {}
        
        for var_name, var_obj in variables.items():
            # 1. 校验变量名是否合法
            if not is_valid_variable_name(var_name):
                raise CodroidError(f"非法变量名 / Illegal variable name: '{var_name}'")
            
            # 2. 转换数据格式
            db_payload[var_name] = var_obj.to_robot_format()
            
        return self._send_command("globalVar/saveVars", db_payload)

    def save_global_var(self, name: str, variable: GlobalVariable) -> CommonResponse:
        """C# ``SaveGlobalVar``：单变量增量保存。"""
        return self.save_global_vars({name: variable})
    
    def remove_global_vars(self, names: List[str]) -> CommonResponse:
        """
        3.4 删除全局变量 / Remove global variables（C# ``RemoveGlobalVars``）。

        Args:
            names (List[str]): 要删除的变量名列表 / List of variable names to remove.

        Returns:
            CommonResponse: 响应对象 / Response object.
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
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("globalVar/GetProjectVarUpdate")

    def rs485_init(
        self, baudrate: Union[RS485BaudRate, int], 
        stop_bit: RS485StopBits = RS485StopBits.ONE, 
        parity: RS485Parity = RS485Parity.NONE
    ) -> CommonResponse:
        """
        5.1 初始化末端 485 / Initialize RS485.

        Args:
            baudrate (int): 波特率 / Baud rate.
            stop_bit (RS485StopBits): 停止位 (1或2) / Stop bits (1 or 2).
            parity (RS485Parity): 校验位 / Parity mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        db = {
            "baudrate": int(baudrate),
            "stopBit": int(stop_bit),  # 确保转为整数
            "dataBit": 8,
            "parity": int(parity)      # 确保转为整数
        }
        return self._send_command("EC2RS485/init", db)

    def rs485_flush(self) -> CommonResponse:
        """
        5.2 清空 485 读取缓存 / Flush RS485 read buffer.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("EC2RS485/flushReadBuffer")

    def rs485_read(self, length: int, timeout: int = 3000) -> CommonResponse:
        """
        5.3 读取 485 数据 / Read RS485 data.

        Args:
            length (int): 读取字节数 (max 128) / Bytes to read (max 128).
            timeout (int): 超时时间 ms (max 3000) / Timeout in ms (max 3000).

        Returns:
            CommonResponse: 响应对象，db 字段为字节数组 / Response object, 'db' field is a list of bytes.
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

    def rs485_write(self, data: Union[List[int], bytes]) -> CommonResponse:
        """
        5.4 发送 485 数据 / Write RS485 data.

        Args:
            data (Union[List[int], bytes]): 要发送的数据 / Data to send.

        Returns:
            CommonResponse: 响应对象 / Response object.
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

    def apos_to_cpos(
        self, 
        jp: Sequence[float], 
        coor: Optional[Sequence[float]] = None, 
        tool: Optional[Sequence[float]] = None, 
        ep: Sequence[float] = []
    ) -> CommonResponse:
        """
        10.1 正解 (关节 → 笛卡尔) / Forward kinematics（C# ``AposToCpos`` / ``AposToCposPose``）。

        Args:
            jp (Sequence[float]): 6个关节角 [j1...j6], 单位: deg / 6 joint angles in deg.
            coor (Optional[Sequence[float]]): 用户坐标系 [x,y,z,a,b,c]，不传则不发送 / User coordinate system.
            tool (Optional[Sequence[float]]): 工具坐标系 [x,y,z,a,b,c]，不传则不发送 / Tool coordinate system.
            ep (Sequence[float]): 附加轴位置 / Additional axis positions.

        Returns:
            CommonResponse: 响应对象 / Response object.
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

    def cpos_to_apos(
        self, 
        cp: Sequence[float], 
        rj: Optional[Sequence[float]] = None, 
        ep: Sequence[float] = []
    ) -> CommonResponse:
        """
        10.2 逆解 (笛卡尔 → 关节) / Inverse kinematics（C# ``CposToApos`` / ``CposToAposJoints``）。

        Args:
            cp (Sequence[float]): 末端位置 [x,y,z,a,b,c] / TCP pose.
            rj (Optional[Sequence[float]]): 参考关节角，默认 [20,20,20,20,20,20] / Reference joint angles.
            ep (Sequence[float]): 附加轴位置 / Additional axis positions.

        Returns:
            CommonResponse: 响应对象 / Response object.
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
    ) -> CommonResponse:
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

    def start_jog(
        self, 
        mode: JogMode, 
        index: int, 
        speed: float, 
        coor_type: JogCoorType = JogCoorType.USER, 
        coor_id: int = 1
    ) -> CommonResponse:
        """
        11.1 启动点动 / Start jog（C# ``StartJog``）。
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

    def stop_jog(self) -> CommonResponse:
        """
        11.2 停止点动 / Stop robot jogging.
        """
        return self._send_command("Robot/stopJog", "")

    def jog_heartbeat(self) -> CommonResponse:
        """
        11.3 点动心跳 / Jog heartbeat.
        需在点动期间每隔 0.5s 发送一次。
        """
        return self._send_command("Robot/jogHeartbeat", "")

    def MoveTo(
        self,
        move_type: MoveToType,
        target: Optional[MoveTarget] = None,
    ) -> CommonResponse:
        """
        11.4 运动到指定位置（C# ``MoveTo`` / ``Robot/moveTo``）。

        关节/直线目标请用 ``MoveTarget.Joint`` / ``MoveTarget.Cartesian`` 构造。
        启动后须每 0.5s 调用 ``MoveToHeartbeat()``。
        """
        db: Dict[str, Any] = {"type": int(move_type)}
        if target is not None:
            db["target"] = target.to_dict()
        return self._send_command("Robot/moveTo", db)

    def move_to(
        self,
        move_type: MoveToType,
        target: Optional[MoveTarget] = None,
    ) -> CommonResponse:
        """兼容别名，请改用 ``MoveTo``。"""
        return self.MoveTo(move_type, target)

    def MoveToHeartbeat(self) -> CommonResponse:
        """11.5 moveTo 心跳（C# ``MoveToHeartbeat``）。"""
        return self._send_command("Robot/moveToHeartbeat")

    def move_to_heartbeat(self) -> CommonResponse:
        """兼容别名，请改用 ``MoveToHeartbeat``。"""
        return self.MoveToHeartbeat()

    def set_manual_move_rate(self, rate: int) -> CommonResponse:
        """
        11.6 设置手动运动倍率 / Set manual move rate.

        Args:
            rate (int): 速度百分比 / magnification range (1 ~ 100).
        """
        if not (1 <= rate <= 100):
            raise CodroidError("倍率范围必须在 1~100 之间 / The magnification range must be between 1 and 100")
        return self._send_command("Robot/setManualMoveRate", rate)

    def set_auto_move_rate(self, rate: int) -> CommonResponse:
        """
        11.7 设置自动运动倍率 / Set auto move rate.

        Args:
            rate (int): 速度百分比 / magnification range (1 ~ 100).
        """
        if not (1 <= rate <= 100):
            raise CodroidError("倍率范围必须在 1~100 之间 / The magnification range must be between 1 and 100")
        return self._send_command("Robot/setAutoMoveRate", rate)

    def _send_move_commands(self, commands: List[Dict[str, Any]]) -> CommonResponse:
        """内部：发送 ``Robot/move`` 指令列表。"""
        return self._send_command("Robot/move", commands)

    def _motion_instruction_item(
        self,
        instruction: MoveInstruction,
    ) -> Dict[str, Any]:
        return instruction.to_dict()

    def Move(
        self,
        path: Union[
            MotionPath,
            List[MoveInstruction],
            List[Dict[str, Any]],
        ],
    ) -> CommonResponse:
        """
        11.8 运动指令列表（C# ``Move`` / ``Robot/move``）。

        推荐 ``List[MoveInstruction]``（``MoveInstruction.MovJ`` / ``MovL`` 等工厂构建）。
        亦兼容 ``MotionPath`` 与已序列化的 dict 列表。
        """
        if isinstance(path, MotionPath):
            cmds = path.get_commands()
        elif isinstance(path, list):
            if path and isinstance(path[0], MoveInstruction):
                cmds = [inst.to_dict() for inst in cast(List[MoveInstruction], path)]
            else:
                cmds = cast(List[Dict[str, Any]], path)
        else:
            raise CodroidError(
                f"Move 需要 MotionPath 或 list，收到 {type(path).__name__}"
            )
        if not cmds:
            raise CodroidError("运动指令列表不能为空 / Move command list cannot be empty")
        return self._send_move_commands(cmds)

    def move(
        self,
        path: Union[MotionPath, List[MoveInstruction], List[Dict[str, Any]]],
    ) -> CommonResponse:
        """兼容别名，请改用 ``Move``。"""
        return self.Move(path)

    def MovJ(
        self,
        target: Union[JointPoint, CartesianPoint, MovePoint],
        speed: float,
        acceleration: float,
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """
        关节运动 movJ。目标为 ``JointPoint``（发 jp）或 ``CartesianPoint``（发 cp+rj）。
        高级用法可传已构建的 ``MovePoint``。
        """
        if isinstance(target, MovePoint):
            from .robot_motion import pack_instruction

            item = pack_instruction(
                MotionType.MOVJ,
                target,
                speed,
                acceleration,
                blend=blend,
                coor=coor,
                tool=tool,
            )
            return self._send_move_commands([item])
        inst = MoveInstruction.MovJ(
            target,
            speed,
            acceleration,
            blend=blend,
            coor=coor,
            tool=tool,
        )
        return self._send_move_commands([self._motion_instruction_item(inst)])

    def MovL(
        self,
        target: Union[CartesianPoint, JointPoint, MovePoint],
        speed: float,
        acceleration: float,
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """
        直线运动 movL。目标为 ``CartesianPoint`` 或 ``JointPoint``。
        """
        if isinstance(target, MovePoint):
            from .robot_motion import pack_instruction

            item = pack_instruction(
                MotionType.MOVL,
                target,
                speed,
                acceleration,
                blend=blend,
                coor=coor,
                tool=tool,
            )
            return self._send_move_commands([item])
        inst = MoveInstruction.MovL(
            target,
            speed,
            acceleration,
            blend=blend,
            coor=coor,
            tool=tool,
        )
        return self._send_move_commands([self._motion_instruction_item(inst)])

    def MovC(
        self,
        middle: CartesianPoint,
        target: CartesianPoint,
        speed: float,
        acceleration: float,
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """圆弧运动 movC（中间点与目标均为 TCP）。"""
        inst = MoveInstruction.MovC(
            middle,
            target,
            speed,
            acceleration,
            blend=blend,
            coor=coor,
            tool=tool,
        )
        return self._send_move_commands([self._motion_instruction_item(inst)])

    def MovCircle(
        self,
        middle: CartesianPoint,
        target: CartesianPoint,
        circle_num: int,
        speed: float,
        acceleration: float,
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """整圆运动 movCircle。"""
        inst = MoveInstruction.MovCircle(
            middle,
            target,
            circle_num,
            speed,
            acceleration,
            blend=blend,
            coor=coor,
            tool=tool,
        )
        return self._send_move_commands([self._motion_instruction_item(inst)])

    def move_j(
        self,
        target: MovePoint,
        speed: float,
        acc: float,
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """已废弃：请改用 ``MovJ(JointPoint.Degrees(...))`` 或 ``MovJ(CartesianPoint.MmDeg(...))``。"""
        warnings.warn(
            "move_j(MovePoint, ...) is deprecated; use MovJ(JointPoint|CartesianPoint, ...)",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.MovJ(target, speed, acc, blend=blend, coor=coor, tool=tool)

    def move_l(
        self,
        target: MovePoint,
        speed: float,
        acc: float,
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """已废弃：请改用 ``MovL(CartesianPoint|JointPoint, ...)``。"""
        warnings.warn(
            "move_l(MovePoint, ...) is deprecated; use MovL(CartesianPoint|JointPoint, ...)",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.MovL(target, speed, acc, blend=blend, coor=coor, tool=tool)

    def move_c(
        self,
        target_cp: Sequence[float],
        middle_cp: Sequence[float],
        speed: float,
        acc: float,
        blend: float = 0.0,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """已废弃：请改用 ``MovC(CartesianPoint, CartesianPoint, ...)``。"""
        warnings.warn(
            "move_c is deprecated; use MovC with CartesianPoint.MmDeg(...)",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.MovC(
            CartesianPoint.MmDeg(middle_cp),
            CartesianPoint.MmDeg(target_cp),
            speed,
            acc,
            blend=blend,
            coor=coor,
            tool=tool,
        )

    def move_circle(
        self,
        target_cp: Sequence[float],
        middle_cp: Sequence[float],
        speed: float,
        acc: float,
        circle_num: int = 1,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> CommonResponse:
        """已废弃：请改用 ``MovCircle``。"""
        warnings.warn(
            "move_circle is deprecated; use MovCircle with CartesianPoint.MmDeg(...)",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.MovCircle(
            CartesianPoint.MmDeg(middle_cp),
            CartesianPoint.MmDeg(target_cp),
            circle_num,
            speed,
            acc,
            blend=blend,
            coor=coor,
            tool=tool,
        )

    def execute_path(self, path: MotionPath) -> CommonResponse:
        """已废弃：请改用 ``Move(path)``。"""
        warnings.warn(
            "execute_path is deprecated; use Move(path)",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.Move(path)

    # --- 11.9 - 11.11 运动控制 ---

    def pause_robot_motion(self) -> CommonResponse:
        """11.9 暂停运动 / Pause robot motion（C# ``PauseRobotMotion``）。"""
        return self._send_command("Robot/pause", "")

    def resume_robot_motion(self) -> CommonResponse:
        """11.10 恢复运动 / Resume robot motion（C# ``ResumeRobotMotion``）。"""
        return self._send_command("Robot/resume", "")

    def stop_robot_move(self) -> CommonResponse:
        """11.11 停止运动 / Stop robot move（C# ``StopRobotMove``）。"""
        return self._send_command("Robot/stopMove", "")

    # --- 12. 机器人控制命令 / Robot Control Commands ---

    def switch_on(self) -> CommonResponse:
        """
        12.1 上使能 / Enable the robot.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/switchOn", "")

    def switch_off(self) -> CommonResponse:
        """
        12.2 下使能 / Disable the robot.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/switchOff", "")

    def to_manual(self) -> CommonResponse:
        """
        12.3 进入手动模式 / ``Robot/toManual``（C# ``ToManual``，不含模式跳转组合）。

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toManual", "")

    def enter_manual_mode_via_auto(self) -> CommonResponse:
        """12.3 C# ``EnterManualModeViaAuto``：先 ``ToAuto`` 再 ``ToManual``。"""
        self.to_auto()
        return self.to_manual()

    def to_auto(self) -> CommonResponse:
        """
        12.4 进入自动模式 / Switch to auto mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toAuto", "")

    def to_remote(self) -> CommonResponse:
        """
        12.5 进入远程模式 / ``Robot/toRemote``（C# ``ToRemote``，不含前置 Auto）。

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toRemote", "")

    def enter_remote_mode_via_auto(self) -> CommonResponse:
        """12.5 C# ``EnterRemoteModeViaAuto``：先 ``ToAuto`` 再 ``ToRemote``。"""
        self.to_auto()
        return self.to_remote()

    def to_simulation(self) -> CommonResponse:
        """
        12.7 进入仿真模式 / Switch to simulation mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toSimulation", "")

    def to_actual(self) -> CommonResponse:
        """
        12.8 进入实机模式 / Switch to actual mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toActual", "")

    def start_drag(self) -> CommonResponse:
        """
        12.9 进入拖拽模式 / Enable drag-and-teach mode.
        注意：只可在远程模式和手动模式下使用 / Note: Only available in remote or manual mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/startDrag", "")

    def stop_drag(self) -> CommonResponse:
        """
        12.10 退出拖拽模式 / Disable drag-and-teach mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/stopDrag", "")

    def clear_system_error(self) -> CommonResponse:
        """
        12.11 清除错误 / Clear system errors（C# ``ClearSystemError``，协议 ``System/clearError``）。

        Returns:
            CommonResponse: 响应对象 / Response object.
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

    def get_io_values(self, io_requests: List[Dict[str, Any]]) -> CommonResponse:
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

    def set_do(self, port: int, value: int) -> CommonResponse:
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

    def set_ao(self, port: int, value: float) -> CommonResponse:
        """
        设置模拟输出 (AO) 值 / Set Analog Output value.

        Args:
            port (int): 端口号 (0~3).
            value (float): 模拟输出值.
        """
        self._validate_io(IOType.AO, port)
        db = {"type": IOType.AO, "port": port, "value": value}
        return self._send_command("IOManager/SetIOValue", db)

    def set_io_values(self, io_list: List[Dict[str, Any]]) -> List[CommonResponse]:
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

    def get_register_values(self, addresses: List[int]) -> CommonResponse:
        """
        14.1 获取多个寄存器值 / Get multiple register values.

        Args:
            addresses (List[int]): 寄存器地址列表 / List of register addresses.

        Returns:
            CommonResponse: 响应对象 / Response object.
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

    def set_register_value(self, address: int, value: Any) -> CommonResponse:
        """
        14.2 写入寄存器值 / Set a single register value.

        Args:
            address (int): 寄存器地址 / Register address.
            value (Any): 要写入的值 / Value to write.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        db = {"address": address, "value": value}
        return self._send_command("RegisterManager/SetRegisterValue", db)

    def set_extend_array_type(self, index: int, data_type: ExtendArrayType) -> CommonResponse:
        """
        14.3 设置扩展数组数据类型 / Set extended array data type.

        Args:
            index (int): 数组索引 (0-999) / Array index (0-999).
            data_type (ExtendArrayType): 数据类型枚举 / Data type enum.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        if not (0 <= index <= 999):
            raise CodroidError(f"扩展数组索引范围错误: {index} (应为 0~999) / Invalid index.")
        
        db = {
            "index": index,
            "type": data_type.value
        }
        return self._send_command("RegisterManager/setExtendArrayType", db)

    def remove_extend_array(self, index: int) -> CommonResponse:
        """
        14.4 删除扩展数组索引 (重置数据) / Remove extended array index.

        Args:
            index (int): 数组索引 (0-999) / Array index (0-999).

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        if not (0 <= index <= 999):
            raise CodroidError(f"扩展数组索引范围错误: {index} (应为 0~999)")
            
        return self._send_command("RegisterManager/removeExtendArray", {"index": index})

    # --- 17. CRI 实时控制接口 / Codroid RealTime Interface ---

    def start_cri_data_push(
        self,
        ip: str,
        port: int,
        duration: int = 100,
        high_percision: bool = True,
        mask: int = 0xFFFF,
    ) -> CommonResponse:
        """
        17.2/17.4 开启 CRI UDP 推送 / Start CRI data push（C# ``StartCriDataPush``，``CRI/StartDataPush``）。

        Args:
            ip: 本机接收 IP。
            port: 本机 UDP 端口（10000–65534）。
            duration: 推送周期 (ms)。
            high_percision: 是否双精度（协议字段名 ``highPercision`` 拼写固定）。
            mask: 位掩码，默认 ``0xFFFF``。
        """
        if port < 10000 or port > 65534:
            raise CodroidError("接收端口须在 10000–65534 / Port must be in (10000-65534)")
        db = {
            "ip": ip,
            "port": port,
            "duration": duration,
            "mask": int(mask),
            "highPercision": high_percision,
        }
        return self._send_command("CRI/StartDataPush", db)

    def stop_cri_data_push(self, ip: Optional[str] = None, port: Optional[int] = None) -> CommonResponse:
        """
        17.3/17.5 停止 CRI 推送 / Stop CRI data push（C# ``StopCriDataPush``）。
        """
        db = {}
        if ip and port:
            db = {"ip": ip, "port": port}
        try:
            return self._send_command("CRI/StopDataPush", db if db else "")
        finally:
            self._stop_cri_receiver()

    def start_cri_control(
        self,
        filter_type: CriFilterType = CriFilterType.NONE,
        duration: int = 1,
        start_buffer: int = 3,
    ) -> CommonResponse:
        """
        17.6 开启实时控制 / Start CRI control mode（C# ``StartCriControl``，``CRI/StartControl``）。

        Args:
            filter_type: 滤波类型。
            duration: 指令间隔 ms（1–16，且可整除 1000）。
            start_buffer: 启动缓冲点数（1–100）。
        """
        db = {
            "filterType": int(filter_type),
            "duration": duration,
            "startBuffer": start_buffer,
        }
        return self._send_command("CRI/StartControl", db)

    def stop_cri_control(self) -> CommonResponse:
        """17.7 关闭实时控制 / Stop CRI control（C# ``StopCriControl``）。"""
        return self._send_command("CRI/StopControl", "")

    def connect_remote_and_switch_on(self) -> CommonResponse:
        """
        与 C# ``ConnectRemoteAndSwitchOn`` 一致：``EnterRemoteModeViaAuto`` → ``SwitchOn``。
        须先 ``connect()`` / ``with`` 已建立 TCP。
        """
        self.enter_remote_mode_via_auto()
        return self.switch_on()

    # --- 历史别名（旧示例/脚本兼容；新代码请用 C# 对齐名）---
    get_statues = get_cri_data
    save_global_variables = save_global_vars
    remove_global_variables = remove_global_vars
    forward_kinematics = apos_to_cpos
    inverse_kinematics = cpos_to_apos
    jog = start_jog
    pause_move = pause_robot_motion
    resume_move = resume_robot_motion
    stop_move = stop_robot_move
    clear_error = clear_system_error
    start_data_push = start_cri_data_push
    stop_data_push = stop_cri_data_push
    start_realtime_control = start_cri_control
    stop_realtime_control = stop_cri_control
    run = run_project
    run_by_index = run_project_by_index
    get_register_value = get_register
    apos_to_cpos_pose = apos_to_cpos
    cpos_to_apos_joints = cpos_to_apos
    calculate_relative_pose_result = calculate_relative_pose

    # --- 19. 机器人设置相关接口 / Robot Settings ---

    def set_collision_sensitivity(self, sensitivity: int) -> CommonResponse:
        """
        19.1 设置碰撞检测灵敏度 / Set collision detection sensitivity.
        仅 2.3.2.10 以上版本可用 / Only available in version 2.3.2.10+.

        Args:
            sensitivity (int): 灵敏度 (0-100)，数值越大越灵敏 / Sensitivity value (0-100).

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        if not (0 <= sensitivity <= 100):
            from .exceptions import CodroidError
            raise CodroidError("灵敏度范围必须在 0~100 之间 / Sensitivity must be between 0 and 100.")
            
        return self._send_command("Robot/setCollisionSensitivity", sensitivity)

    def set_payload(self, payload_id: int) -> CommonResponse:
        """
        19.2 设置负载 / Set robot payload.
        仅 2.3.2.10 以上版本可用 / Only available in version 2.3.2.10+.

        Args:
            payload_id (int): 负载 ID (0-15) / Payload ID (0-15).

        Returns:
            CommonResponse: 响应对象 / Response object.
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


CodroidControlInterface = CodroidSession