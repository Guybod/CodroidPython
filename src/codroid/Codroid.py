"""
协议会话与指令实现（原 ``CodroidControlInterface`` 模块；与 C# ``CodroidClient`` 能力对应）。

对外类：``CodroidSession``；``CodroidControlInterface`` 为兼容别名。
"""
from __future__ import annotations

import threading
import socket
import time
from typing import Any, Dict, List, Literal, Optional, Union, Sequence, cast
from .async_tcp_client import JsonStreamClient
from .exceptions import CodroidError, CodroidTimeoutError
from .define import *
from .utils import is_valid_variable_name
from .cri_realtime_packet_parser import CriRealtimePacketParser, CriStreamHandler


class CodroidSession:
    """
    TCP/UDP 协议会话与指令封装。

    C# 侧等价能力内聚于 ``CodroidClient``；Python 中 ``CodroidClient`` 继承本类并替换传输层。
    对外请优先使用 ``CodroidClient``；公开方法名与 C# / AGENTS.md §4.1 一致（PascalCase）。
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
        self._last_cri_received_utc: float = 0.0  # time.monotonic() of last CRI packet

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

    def Connect(self) -> "CodroidSession":
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
                    self._last_cri_received_utc = time.monotonic()
                except socket.timeout:
                    continue
                except Exception as e:
                    if not self._stop_event.is_set():
                        print(f"CRI 数据接收或解析错误: {e}")
        finally:
            handler._sock.close()


    def _close_connection(self):
        """
        关闭连接 / Close connection.
        """
        try:
            self.StopCriDataPush()
        finally:
            self._stop_cri_receiver()
            self._net.close()

    def Disconnect(self):
        """断开 TCP 并停止 CRI 接收（C# ``Disconnect``）。"""
        self._close_connection()

    @property
    def CriData(self) -> Optional[CriRealTimeData]:
        """最新 CRI 快照（C# ``CriData``，内部 ``cri_cache``）。"""
        return self.cri_cache

    def WaitForCriData(self, timeout: float = 5.0) -> CriRealTimeData:
        """
        等待第一个 CRI 数据包到达 / Wait for the first CRI packet.

        调用 ``*Sync`` 阻塞运动方法前，需确保 CRI 数据已开始推送。
        本方法阻塞直到收到第一个 CRI 包或超时。

        Args:
            timeout: 最大等待秒数，默认 5.0。

        Returns:
            CriRealTimeData: 首个 CRI 快照。

        Raises:
            CodroidTimeoutError: 超时未收到 CRI 数据。
        """
        start = time.monotonic()
        while (time.monotonic() - start) < timeout:
            if self.cri_cache is not None:
                return self.cri_cache
            time.sleep(0.05)
        raise CodroidTimeoutError(
            f"WaitForCriData timed out ({timeout:.1f}s). "
            "Ensure StartListenUdp / StartCriDataPush is called first."
        )

    def StartListenUdp(self): 
        try:            
            # 1. 先停止旧的推送
            self.StopCriDataPush()
            time.sleep(0.1)
            
            # 2. 先在本地打开 UDP 监听端口
            self._start_cri_receiver() 
            
            # 3. 再通知机器人开始推送数据
            self.StartCriDataPush(ip=self.local_ip, port=self.udp_port)
            
            if self.debug:
                print(f"实时数据同步已开启，监听端口: {self.udp_port}")
                
        except Exception as e:
            # 二进制环境下，务必捕获并打印具体的异常
            print(f"UDP 监听启动失败: {type(e).__name__}: {e}")
            raise e

    # --- 接口实现 ---

    def RunScript(
        self,
        main_script: str,
        sub_threads: Optional[Dict[str, str]] = None,
        sub_programs: Optional[Dict[str, str]] = None,
        interrupts: Optional[Dict[str, str]] = None,
        vars: Optional[Dict[str, Any]] = None,
    ) -> CommonResponse:
        """
        2.1 运行脚本 / Run script（C# ``RunScript``）。

        Args:
            main_script (str): Lua 脚本代码 / Lua script code.
            sub_threads (dict, optional): 子线程脚本 ``{name: lua_code}``。
            sub_programs (dict, optional): 子程序脚本 ``{name: lua_code}``。
            interrupts (dict, optional): 中断处理脚本 ``{name: lua_code}``。
            vars (dict, optional): 脚本共享变量 / Shared variables for the script.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        scripts: Dict[str, Any] = {"main": main_script}
        if sub_threads:
            scripts["subThreads"] = sub_threads
        if sub_programs:
            scripts["subPrograms"] = sub_programs
        if interrupts:
            scripts["interrupts"] = interrupts
        db: Dict[str, Any] = {"scripts": scripts}
        if vars:
            db["vars"] = vars
        return self._send_command("project/runScript", db)

    def __run_script(self, main_script: str, vars: Optional[Dict[str, Any]] = None) -> CommonResponse:
        """兼容旧代码调用 ``__run_script``。"""
        return self.RunScript(main_script, vars=vars)

    def EnterRemoteScriptMode(self) -> CommonResponse:
        """
        2.2 进入远程脚本模式 / Enter remote script mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/enterRemoteScriptMode")

    def Run(self, project_id: str) -> CommonResponse:
        """
        2.3 运行指定工程 / Run specified project.

        Args:
            project_id (str): 工程唯一标识 ID / Unique project ID.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/run", {"id": project_id})

    def RunByIndex(self, index: int) -> CommonResponse:
        """
        2.4 通过索引号运行工程 / Run project by index（C# ``RunByIndex``）。

        Args:
            index (int): 工程映射索引号 / Project mapping index.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/runByIndex", index)

    def RunStep(self, project_id: str) -> CommonResponse:
        """
        2.5 单步运行（C# ``RunStep``）。
        """
        return self._send_command("project/run", {"id": project_id})

    def PauseProject(self) -> CommonResponse:
        """
        2.6 暂停工程 / Pause project.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/pause")

    def ResumeProject(self) -> CommonResponse:
        """
        2.7 恢复运行 / Resume project.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/resume")

    def StopProject(self) -> CommonResponse:
        """
        2.8 停止运行 / Stop project.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/stop")

    def SetStartLine(self, line: int) -> CommonResponse:
        """
        2.13 设置启动行 / Set start line.

        Args:
            line (int): 主程序开始执行的行号 / Starting line number.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/setStartLine", line)

    def ClearStartLine(self) -> CommonResponse:
        """
        2.14 清除启动行设置 / Clear start line setting.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("project/clearStartLine")

    def GetGlobalVars(self):
        """
        3.2 获取全局变量 / Get global variables（C# ``GetGlobalVars``）。

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("globalVar/getVars")

    def GetGlobalVarsCatalog(self):
        """
        C# ``GetGlobalVarsCatalog``：与 ``get_global_vars`` 相同 TCP 请求（``globalVar/getVars``）；
        C# 侧再经 ``GlobalVarCatalogParser`` 解析；Python 当前直接返回原始 ``CommonResponse``。
        """
        return self.GetGlobalVars()

    def SaveGlobalVars(self, variables: Dict[str, GlobalVariable]) -> CommonResponse:
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

    def SaveGlobalVar(self, name: str, variable: GlobalVariable) -> CommonResponse:
        """C# ``SaveGlobalVar``：单变量增量保存。"""
        return self.SaveGlobalVars({name: variable})
    
    def RemoveGlobalVars(self, names: List[str]) -> CommonResponse:
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

    def GetProjectVar(self):
        """
        4.1 获取当前所有工程变量值(仅在工程运行中有效) / Get the values of all current project variables (only valid when the project is running)

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("globalVar/GetProjectVarUpdate")

    def Rs485Init(
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

    def Rs485Flush(self) -> CommonResponse:
        """
        5.2 清空 485 读取缓存 / Flush RS485 read buffer.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("EC2RS485/flushReadBuffer")

    def Rs485Read(self, length: int, timeout: int = 3000) -> CommonResponse:
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

    def Rs485Write(self, data: Union[List[int], bytes]) -> CommonResponse:
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

    def AposToCpos(
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

    def CposToApos(
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

    def CalculateRelativePose(
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

    def StartJog(
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

    def StopJog(self) -> CommonResponse:
        """
        11.2 停止点动 / Stop robot jogging.
        """
        return self._send_command("Robot/stopJog", "")

    def JogHeartbeat(self) -> CommonResponse:
        """
        11.3 点动心跳 / Jog heartbeat.
        需在点动期间每隔 0.5s 发送一次。
        """
        return self._send_command("Robot/jogHeartbeat", "")

    def MoveTo(
        self,
        move_type: MoveToType,
        target: Optional[MoveToTarget] = None,
    ) -> CommonResponse:
        """
        11.4 运动到指定位置（C# ``MoveTo`` / ``Robot/moveTo``）。

        关节/直线目标请用 ``MoveToTarget.Joint`` / ``MoveToTarget.Cartesian`` 构造。
        启动后须每 0.5s 调用 ``MoveToHeartbeat()``。
        """
        db: Dict[str, Any] = {"type": int(move_type)}
        if target is not None:
            db["target"] = target.to_dict()
        return self._send_command("Robot/moveTo", db)

    def MoveToHeartbeat(self) -> CommonResponse:
        """11.5 moveTo 心跳（C# ``MoveToHeartbeat``）。"""
        return self._send_command("Robot/moveToHeartbeat")

    def StopMoveTo(self) -> CommonResponse:
        """
        11.5b 停止 MoveTo 运动 / Stop MoveTo motion（C# ``StopMoveTo``）。

        发送 ``type=-1`` 停止当前 MoveTo 运动。

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/moveTo", {"type": MoveToType.STOP})

    def SetManualMoveRate(self, rate: int) -> CommonResponse:
        """
        11.6 设置手动运动倍率 / Set manual move rate.

        Args:
            rate (int): 速度百分比 / magnification range (1 ~ 100).
        """
        if not (1 <= rate <= 100):
            raise CodroidError("倍率范围必须在 1~100 之间 / The magnification range must be between 1 and 100")
        return self._send_command("Robot/setManualMoveRate", rate)

    def SetAutoMoveRate(self, rate: int) -> CommonResponse:
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

    def MovJ(
        self,
        target: Union[JointPoint, CartesianPoint, MovePoint],
        speed: float,
        acceleration: float,
        blend: Optional[float] = None,
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
        blend: Optional[float] = None,
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
        blend: Optional[float] = None,
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
        blend: Optional[float] = None,
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

    # --- 11.9 - 11.11 运动控制 ---

    def PauseRobotMotion(self) -> CommonResponse:
        """11.9 暂停运动 / Pause robot motion（C# ``PauseRobotMotion``）。"""
        return self._send_command("Robot/pause", "")

    def ResumeRobotMotion(self) -> CommonResponse:
        """11.10 恢复运动 / Resume robot motion（C# ``ResumeRobotMotion``）。"""
        return self._send_command("Robot/resume", "")

    def StopRobotMove(self) -> CommonResponse:
        """11.11 停止运动 / Stop robot move（C# ``StopRobotMove``）。"""
        return self._send_command("Robot/stopMove", "")

    # --- 11b. 阻塞式运动接口 / Synchronous (Blocking) Motion ---

    @staticmethod
    def _max_abs_diff(actual: List[float], expected: List[float]) -> float:
        """六轴最大绝对误差 / Max absolute joint error across 6 axes."""
        if len(actual) < 6 or len(expected) < 6:
            return float("inf")
        return max(abs(actual[i] - expected[i]) for i in range(6))

    @staticmethod
    def _euclidean_3mm(actual_pose: List[float], target_pose: List[float]) -> float:
        """笛卡尔位置欧氏距离（mm）/ Euclidean distance of xyz (mm)."""
        if len(actual_pose) < 3 or len(target_pose) < 3:
            return float("inf")
        dx = actual_pose[0] - target_pose[0]
        dy = actual_pose[1] - target_pose[1]
        dz = actual_pose[2] - target_pose[2]
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    @staticmethod
    def _max_abs_euler_diff_deg(actual_pose: List[float], target_pose: List[float]) -> float:
        """笛卡尔姿态最大欧拉角误差（度）/ Max absolute Euler angle error (deg)."""
        if len(actual_pose) < 6 or len(target_pose) < 6:
            return float("inf")
        return max(abs(actual_pose[i] - target_pose[i]) for i in range(3, 6))

    @staticmethod
    def _is_cartesian_target_reached(
        actual_pose: List[float], target_pose: List[float], options: "MotionWaitOptions"
    ) -> bool:
        """笛卡尔目标到达判定（位置 + 姿态）/ Cartesian target-reached check."""
        pos_err = CodroidSession._euclidean_3mm(actual_pose, target_pose)
        ori_err = CodroidSession._max_abs_euler_diff_deg(actual_pose, target_pose)
        return (pos_err <= options.cartesian_position_tolerance_mm
                and ori_err <= options.cartesian_orientation_tolerance_deg)

    def _ensure_cri_fresh(self, options: "MotionWaitOptions", op_name: str) -> None:
        """检查 CRI 数据是否新鲜 / Ensure CRI data is not stale."""
        last = self._last_cri_received_utc
        if last <= 0:
            raise CodroidError(
                f"{op_name} wait failed: CRI data not yet received. "
                "Call StartListenUdp / StartCriDataPush first."
            )
        age = time.monotonic() - last
        if age > options.cri_stale_timeout:
            raise CodroidTimeoutError(
                f"{op_name} wait failed: CRI data stale {age * 1000:.0f}ms, "
                f"threshold {options.cri_stale_timeout * 1000:.0f}ms."
            )

    def _build_move_target_reached_predicate(
        self, instructions: List[Dict[str, Any]], options: "MotionWaitOptions"
    ):
        """根据最后一条指令的目标类型构建到达判定谓词 / Build target-reached predicate from last instruction."""
        if not instructions:
            raise CodroidError("At least one instruction required.")
        from .robot_motion import pack_move_point, DEFAULT_RJ
        last = instructions[-1]
        tp = last.get("targetPoint", {})
        jp = tp.get("jp")
        cp = tp.get("cp")
        if jp is not None and len(jp) >= 6:
            return lambda data: self._max_abs_diff(data.joint_position, jp) <= options.joint_tolerance_deg
        if cp is not None and len(cp) >= 6:
            return lambda data: self._is_cartesian_target_reached(
                data.tcp_pose, cp, options)
        return lambda data: True

    def _wait_until_settled_by_cri(
        self,
        target_reached,
        op_name: str,
        options: "MotionWaitOptions",
    ) -> None:
        """轮询 CRI 数据直到机器人稳定到达目标 / Poll CRI until robot settles at target."""
        if options.settled_samples <= 0:
            raise CodroidError("MotionWaitOptions.settled_samples must be > 0.")
        if options.poll_interval <= 0:
            raise CodroidError("MotionWaitOptions.poll_interval must be > 0.")

        start = time.monotonic()
        settled = 0
        had_motion = False

        while (time.monotonic() - start) <= options.timeout:
            self._ensure_cri_fresh(options, op_name)
            snapshot = self.CriData
            if snapshot is None:
                time.sleep(options.poll_interval)
                continue

            reached = target_reached(snapshot)

            if snapshot.status.is_moving:
                had_motion = True

            if snapshot.status.collision_stop or snapshot.status.is_emergency_stop or snapshot.status.has_alarm:
                raise CodroidError(
                    f"{op_name} failed: abnormal state detected "
                    f"(CollisionStopped={snapshot.status.collision_stop}, "
                    f"EmergencyStopPressed={snapshot.status.is_emergency_stop}, "
                    f"HasAlarm={snapshot.status.has_alarm})."
                )

            if had_motion and not snapshot.status.is_moving and not reached:
                raise CodroidError(
                    f"{op_name} failed: motion stopped but target not reached."
                )

            still = not snapshot.status.is_moving
            if reached and still:
                settled += 1
                if settled >= options.settled_samples:
                    return
            else:
                settled = 0

            time.sleep(options.poll_interval)

        tail = self.CriData
        jp_str = ", ".join(f"{v:.3f}" for v in (tail.joint_position if tail else []))
        raise CodroidTimeoutError(
            f"{op_name} wait timed out ({options.timeout:.1f}s). "
            f"Last state: InMotion={tail.status.is_moving if tail else '?'}, "
            f"jp=[{jp_str}]"
        )

    def MoveSync(
        self,
        path: Union[MotionPath, List[MoveInstruction], List[Dict[str, Any]]],
        wait: Optional[MotionWaitOptions] = None,
    ) -> bool:
        """
        阻塞式路径执行，等待 CRI 确认最后一段到达目标 / Blocking path execution.

        Args:
            path: 运动路径（MotionPath / List[MoveInstruction] / List[Dict]）。
            wait: 等待参数，None 使用默认值。

        Returns:
            bool: 到达目标返回 True。
        """
        options = wait or MotionWaitOptions()
        self.Move(path)
        if isinstance(path, MotionPath):
            cmds = path.get_commands()
        elif isinstance(path, list) and path and isinstance(path[0], MoveInstruction):
            cmds = [inst.to_dict() for inst in cast(List[MoveInstruction], path)]
        else:
            cmds = cast(List[Dict[str, Any]], path)
        predicate = self._build_move_target_reached_predicate(cmds, options)
        self._wait_until_settled_by_cri(predicate, "MoveSync", options)
        return True

    def MovJSync(
        self,
        target: Union[JointPoint, CartesianPoint],
        speed: float, acceleration: float,
        wait: Optional[MotionWaitOptions] = None,
        blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> bool:
        """
        阻塞式关节运动 / Blocking joint moveJ.

        Args:
            target: JointPoint 或 CartesianPoint 目标。
            speed: 速度。
            acceleration: 加速度。
            wait: 等待参数，None 使用默认值。
            blend: 平滑半径。
            coor: 用户坐标系。
            tool: 工具坐标系。

        Returns:
            bool: 到达目标返回 True。
        """
        options = wait or MotionWaitOptions()
        self.MovJ(target, speed, acceleration, blend=blend, coor=coor, tool=tool)
        if isinstance(target, JointPoint):
            predicate = (lambda jp: lambda data:
                self._max_abs_diff(data.joint_position, jp) <= options.joint_tolerance_deg
            )(list(target.jp))
        else:
            predicate = (lambda cp: lambda data:
                self._is_cartesian_target_reached(data.tcp_pose, cp, options)
            )(list(target.cp))
        self._wait_until_settled_by_cri(predicate, "MovJSync", options)
        return True

    def MovLSync(
        self,
        target: Union[CartesianPoint, JointPoint],
        speed: float, acceleration: float,
        wait: Optional[MotionWaitOptions] = None,
        blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> bool:
        """
        阻塞式直线运动 / Blocking linear moveL.

        Args:
            target: CartesianPoint 或 JointPoint 目标。
            speed: 速度。
            acceleration: 加速度。
            wait: 等待参数，None 使用默认值。
            blend: 平滑半径。
            coor: 用户坐标系。
            tool: 工具坐标系。

        Returns:
            bool: 到达目标返回 True。
        """
        options = wait or MotionWaitOptions()
        self.MovL(target, speed, acceleration, blend=blend, coor=coor, tool=tool)
        if isinstance(target, JointPoint):
            predicate = (lambda jp: lambda data:
                self._max_abs_diff(data.joint_position, jp) <= options.joint_tolerance_deg
            )(list(target.jp))
        else:
            predicate = (lambda cp: lambda data:
                self._is_cartesian_target_reached(data.tcp_pose, cp, options)
            )(list(target.cp))
        self._wait_until_settled_by_cri(predicate, "MovLSync", options)
        return True

    def MovCSync(
        self,
        middle: CartesianPoint,
        target: CartesianPoint,
        speed: float, acceleration: float,
        wait: Optional[MotionWaitOptions] = None,
        blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> bool:
        """
        阻塞式圆弧运动 / Blocking arc moveC.

        Returns:
            bool: 到达目标返回 True。
        """
        options = wait or MotionWaitOptions()
        self.MovC(middle, target, speed, acceleration, blend=blend, coor=coor, tool=tool)
        inst = MoveInstruction.MovC(middle, target, speed, acceleration, blend=blend, coor=coor, tool=tool)
        cmds = [inst.to_dict()]
        predicate = self._build_move_target_reached_predicate(cmds, options)
        self._wait_until_settled_by_cri(predicate, "MovCSync", options)
        return True

    def MovCircleSync(
        self,
        middle: CartesianPoint,
        target: CartesianPoint,
        circle_num: int,
        speed: float, acceleration: float,
        wait: Optional[MotionWaitOptions] = None,
        blend: Optional[float] = None,
        coor: Optional[Sequence[float]] = None,
        tool: Optional[Sequence[float]] = None,
    ) -> bool:
        """
        阻塞式整圆运动 / Blocking full-circle moveCircle.

        Returns:
            bool: 到达目标返回 True。
        """
        options = wait or MotionWaitOptions()
        self.MovCircle(middle, target, circle_num, speed, acceleration, blend=blend, coor=coor, tool=tool)
        inst = MoveInstruction.MovCircle(middle, target, circle_num, speed, acceleration, blend=blend, coor=coor, tool=tool)
        cmds = [inst.to_dict()]
        predicate = self._build_move_target_reached_predicate(cmds, options)
        self._wait_until_settled_by_cri(predicate, "MovCircleSync", options)
        return True

    # --- 12. 机器人控制命令 / Robot Control Commands ---

    def SwitchOn(self) -> CommonResponse:
        """
        12.1 上使能 / Enable the robot.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/switchOn", "")

    def SwitchOff(self) -> CommonResponse:
        """
        12.2 下使能 / Disable the robot.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/switchOff", "")

    def ToManual(self) -> CommonResponse:
        """
        12.3 进入手动模式 / ``Robot/toManual``（C# ``ToManual``，不含模式跳转组合）。

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toManual", "")

    def EnterManualModeViaAuto(self) -> CommonResponse:
        """12.3 C# ``EnterManualModeViaAuto``：先 ``ToAuto`` 再 ``ToManual``。"""
        self.ToAuto()
        return self.ToManual()

    def ToAuto(self) -> CommonResponse:
        """
        12.4 进入自动模式 / Switch to auto mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toAuto", "")

    def ToRemote(self) -> CommonResponse:
        """
        12.5 进入远程模式 / ``Robot/toRemote``（C# ``ToRemote``，不含前置 Auto）。

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toRemote", "")

    def EnterRemoteModeViaAuto(self) -> CommonResponse:
        """12.5 C# ``EnterRemoteModeViaAuto``：先 ``ToAuto`` 再 ``ToRemote``。"""
        self.ToAuto()
        return self.ToRemote()

    def ToSimulation(self) -> CommonResponse:
        """
        12.7 进入仿真模式 / Switch to simulation mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toSimulation", "")

    def ToActual(self) -> CommonResponse:
        """
        12.8 进入实机模式 / Switch to actual mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/toActual", "")

    def StartDrag(self) -> CommonResponse:
        """
        12.9 进入拖拽模式 / Enable drag-and-teach mode.
        注意：只可在远程模式和手动模式下使用 / Note: Only available in remote or manual mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/startDrag", "")

    def StopDrag(self) -> CommonResponse:
        """
        12.10 退出拖拽模式 / Disable drag-and-teach mode.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("Robot/stopDrag", "")

    def ClearSystemError(self) -> CommonResponse:
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

    def GetIoValues(self, io_requests: List[Dict[str, Any]]) -> CommonResponse:
        """
        13.1 获取多个 IO 的当前值 / Get multiple IO values.
        
        Args:
            io_requests: 包含 type 和 port 的列表，如 [{"type": "DI", "port": 0}]
        """
        for req in io_requests:
            self._validate_io(req["type"], req["port"])
        return self._send_command("IOManager/GetIOValue", io_requests)

    def GetDi(self, port: int) -> int:
        """
        获取数字输入 (DI) 值 / Get Digital Input value.

        Args:
            port (int): 端口号 (0~15).

        Returns:
            int: 0 或 1 / 0 or 1.
        """
        res = self.GetIoValues([{"type": IOType.DI, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return int(res.db[0]["value"])
        
        raise CodroidError(f"无法获取 DI{port} 的值，响应数据为空 / Failed to get DI value.")

    def GetDo(self, port: int) -> int:
        """
        获取数字输出 (DO) 值 / Get Digital Output value.

        Args:
            port (int): 端口号 (0~15).

        Returns:
            int: 0 或 1 / 0 or 1.
        """
        res = self.GetIoValues([{"type": IOType.DO, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return int(res.db[0]["value"])
            
        raise CodroidError(f"无法获取 DO{port} 的值 / Failed to get DO value.")

    def GetAi(self, port: int) -> float:
        """
        获取模拟输入 (AI) 值 / Get Analog Input value.

        Args:
            port (int): 端口号 (0~3).

        Returns:
            float: 模拟量值 / Analog value (double).
        """
        res = self.GetIoValues([{"type": IOType.AI, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return float(res.db[0]["value"])
            
        raise CodroidError(f"无法获取 AI{port} 的值 / Failed to get AI value.")
    
    def GetAo(self, port: int) -> float:
        """
        获取模拟输出 (AO) 值 / Get Analog Output value.

        Args:
            port (int): 端口号 (0~3).

        Returns:
            float: 模拟量值 / Analog value (double).
        """
        res = self.GetIoValues([{"type": IOType.AO, "port": port}])
        if res.db is not None and len(res.db) > 0:
            return float(res.db[0]["value"])
            
        raise CodroidError(f"无法获取 AO{port} 的值 / Failed to get AO value.")

    # --- 13.2 写入 IO 相关接口 / Set IO Interface ---

    def SetDo(self, port: int, value: int) -> CommonResponse:
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

    def SetAo(self, port: int, value: float) -> CommonResponse:
        """
        设置模拟输出 (AO) 值 / Set Analog Output value.

        Args:
            port (int): 端口号 (0~3).
            value (float): 模拟输出值.
        """
        self._validate_io(IOType.AO, port)
        db = {"type": IOType.AO, "port": port, "value": value}
        return self._send_command("IOManager/SetIOValue", db)

    def SetIoValues(self, io_list: List[Dict[str, Any]]) -> List[CommonResponse]:
        """
        批量设置 IO 值 / Bulk set IO values.
        注：由于协议 13.2 是单点设置，此处通过循环调用实现。

        Args:
            io_list: 包含 type, port, value 的字典列表.
        """
        results = []
        for item in io_list:
            if item["type"] in (IOType.DO, IOType.DI): # 协议通常只写 DO/AO
                results.append(self.SetDo(item["port"], item["value"]))
            else:
                results.append(self.SetAo(item["port"], item["value"]))
        return results

    # --- 14. 寄存器相关接口 / Register Interface ---

    def GetRegisterValues(self, addresses: List[int]) -> CommonResponse:
        """
        14.1 获取多个寄存器值 / Get multiple register values.

        Args:
            addresses (List[int]): 寄存器地址列表 / List of register addresses.

        Returns:
            CommonResponse: 响应对象 / Response object.
        """
        return self._send_command("RegisterManager/GetRegisterValue", addresses)

    def GetRegisterValue(self, address: int) -> Any:
        """
        快捷方法：获取单个寄存器值 / Get a single register value.

        Args:
            address (int): 寄存器地址 / Register address.

        Returns:
            Any: 寄存器的值 / The value of the register.
        """
        res = self.GetRegisterValues([address])
        if res.db is not None and len(res.db) > 0:
            return res.db[0]["value"]
        raise CodroidError(f"无法获取寄存器 {address} 的值 / Failed to get register value.")

    def SetRegisterValue(self, address: int, value: Any) -> CommonResponse:
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

    def SetExtendArrayType(self, index: int, data_type: ExtendArrayType) -> CommonResponse:
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

    def RemoveExtendArray(self, index: int) -> CommonResponse:
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

    def StartCriDataPush(
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

    def StopCriDataPush(self, ip: Optional[str] = None, port: Optional[int] = None) -> CommonResponse:
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

    def StartCriControl(
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

    def StopCriControl(self) -> CommonResponse:
        """17.7 关闭实时控制 / Stop CRI control（C# ``StopCriControl``）。"""
        return self._send_command("CRI/StopControl", "")

    def ConnectRemoteAndSwitchOn(self) -> CommonResponse:
        """
        与 C# ``ConnectRemoteAndSwitchOn`` 一致：``EnterRemoteModeViaAuto`` → ``SwitchOn``。
        须先 ``Connect()`` / ``with`` 已建立 TCP。
        """
        self.EnterRemoteModeViaAuto()
        return self.SwitchOn()

    # --- 19. 机器人设置相关接口 / Robot Settings ---

    def _send_save_robot_parameter(self, db: Dict[str, Any]) -> CommonResponse:
        return self._send_command("Robot/SaveRobotParameter", db)

    def SetCollisionSensitivity(self, sensitivity: int) -> CommonResponse:
        """
        19.1 设置碰撞检测灵敏度（``Robot/setCollisionSensitivity``，db 为 0~100 整数）。
        仅固件 2.3.2.10+ 可用。
        """
        from .robot_settings import validate_collision_sensitivity

        validate_collision_sensitivity(sensitivity)
        return self._send_command("Robot/setCollisionSensitivity", sensitivity)

    def SetPayload(self, payload_id: int) -> CommonResponse:
        """
        设置当前负载编号（``Robot/setPayload``，与 19.5 负载表不同）。
        仅固件 2.3.2.10+ 可用。
        """
        from .robot_settings import validate_default_slot_id

        validate_default_slot_id(payload_id, "payload_id")
        return self._send_command("Robot/setPayload", payload_id)

    def GetRobotParameters(self):
        """
        19.7 获取设置界面参数（``Robot/GetRobotParameter``）。
        返回 ``RobotParameters`` 快照。
        """
        from .robot_settings import RobotParameters

        response = self._send_command("Robot/GetRobotParameter", "")
        return RobotParameters.from_db(response.db)

    def SetDefaultPayloadId(self, payload_id: int) -> CommonResponse:
        """19.2 仅设置默认负载编号（``Robot/SaveRobotParameter``）。"""
        from .robot_settings import (
            build_default_payload_id_db,
            validate_default_slot_id,
        )

        validate_default_slot_id(payload_id, "payload_id")
        return self._send_save_robot_parameter(build_default_payload_id_db(payload_id))

    def SetDefaultToolId(self, tool_id: int) -> CommonResponse:
        """19.3 仅设置默认工具坐标系编号。"""
        from .robot_settings import build_default_tool_id_db, validate_default_slot_id

        validate_default_slot_id(tool_id, "tool_id")
        return self._send_save_robot_parameter(build_default_tool_id_db(tool_id))

    def SetDefaultUserCoordinateId(self, coordinate_id: int) -> CommonResponse:
        """19.6 仅设置默认用户坐标系编号（``defaultCoordinateId``，0~15）。"""
        from .robot_settings import (
            build_default_coordinate_id_db,
            validate_default_slot_id,
        )

        validate_default_slot_id(coordinate_id, "coordinate_id")
        return self._send_save_robot_parameter(
            build_default_coordinate_id_db(coordinate_id)
        )

    def SaveToolFrames(self, frames) -> CommonResponse:
        """19.4 下发完整工具坐标系表（16 项，id=0 须全零）。"""
        from .robot_settings import build_tool_db, validate_tool_frames_for_save

        validate_tool_frames_for_save(frames)
        return self._send_save_robot_parameter(build_tool_db(frames))

    def SetToolFrame(self, frame_id: int, frame) -> CommonResponse:
        """
        19.4 修改单个工具坐标系：先 ``GetRobotParameters``，再合并槽位后保存。
        ``frame_id`` 仅允许 1~15。
        """
        from .robot_settings import (
            RobotFrame,
            build_tool_db,
            merge_tool_frame,
            validate_frame_id_matches,
            validate_tool_frames_for_save,
            validate_writable_frame_id,
        )

        if isinstance(frame, RobotFrame):
            robot_frame = frame
        elif isinstance(frame, dict):
            robot_frame = RobotFrame.from_mapping(frame)
        else:
            raise CodroidError("frame 须为 RobotFrame 或 dict。")
        validate_writable_frame_id(frame_id)
        validate_frame_id_matches(frame_id, robot_frame)
        current = self.GetRobotParameters()
        merged = merge_tool_frame(current.tool, frame_id, robot_frame)
        validate_tool_frames_for_save(merged)
        return self._send_save_robot_parameter(build_tool_db(merged))

    def SavePayloadFrames(self, frames) -> CommonResponse:
        """19.5 下发完整负载坐标系表。"""
        from .robot_settings import build_payload_db, validate_payload_frames_for_save

        validate_payload_frames_for_save(frames)
        return self._send_save_robot_parameter(build_payload_db(frames))

    def SetPayloadFrame(self, frame_id: int, frame) -> CommonResponse:
        """
        19.5 修改单个负载坐标系：先读后改再 ``SaveRobotParameter``。
        ``frame_id`` 仅允许 1~15。
        """
        from .robot_settings import (
            RobotPayloadFrame,
            build_payload_db,
            merge_payload_frame,
            validate_payload_frame_id_matches,
            validate_payload_frames_for_save,
            validate_writable_frame_id,
        )

        if isinstance(frame, RobotPayloadFrame):
            payload_frame = frame
        elif isinstance(frame, dict):
            payload_frame = RobotPayloadFrame.from_mapping(frame)
        else:
            raise CodroidError("frame 须为 RobotPayloadFrame 或 dict。")
        validate_writable_frame_id(frame_id)
        validate_payload_frame_id_matches(frame_id, payload_frame)
        current = self.GetRobotParameters()
        merged = merge_payload_frame(current.payload, frame_id, payload_frame)
        validate_payload_frames_for_save(merged)
        return self._send_save_robot_parameter(build_payload_db(merged))

    def SaveUserCoordinateFrames(self, frames) -> CommonResponse:
        """19.6 下发完整用户坐标系表。"""
        from .robot_settings import build_coordinate_db, validate_tool_frames_for_save

        validate_tool_frames_for_save(frames)
        return self._send_save_robot_parameter(build_coordinate_db(frames))

    def SetUserCoordinateFrame(self, frame_id: int, frame) -> CommonResponse:
        """
        19.6 修改单个用户坐标系：先读后改。
        ``frame_id`` 仅允许 1~15。
        """
        from .robot_settings import (
            RobotFrame,
            build_coordinate_db,
            merge_coordinate_frame,
            validate_frame_id_matches,
            validate_tool_frames_for_save,
            validate_writable_frame_id,
        )

        if isinstance(frame, RobotFrame):
            coord_frame = frame
        elif isinstance(frame, dict):
            coord_frame = RobotFrame.from_mapping(frame)
        else:
            raise CodroidError("frame 须为 RobotFrame 或 dict。")
        validate_writable_frame_id(frame_id)
        validate_frame_id_matches(frame_id, coord_frame)
        current = self.GetRobotParameters()
        merged = merge_coordinate_frame(current.coordinate, frame_id, coord_frame)
        validate_tool_frames_for_save(merged)
        return self._send_save_robot_parameter(build_coordinate_db(merged))

    # 支持 with 语句
    def __enter__(self):
        self.Connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.Disconnect()


CodroidControlInterface = CodroidSession