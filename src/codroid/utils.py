# src/codroid/utils.py
import re
from typing import Set

# 基于你提供的文档整理的保留字集合
RESERVED_NAMES: Set[str] = {
    # Lua 基础保留字
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function", 
    "goto", "if", "in", "local", "nil", "not", "or", "repeat", "return", 
    "then", "true", "until", "while", "table", "math",
    # 系统 IO 与 组定义
    "DO", "DOGroup", "DIO", "DIOGroup", "AO", "AIO", "ModbusTCP",
    # 运动控制
    "setSpeedJ", "setAccJ", "setSpeedL", "setAccL", "setBlender", "setMoveRate",
    "getCoor", "getTool", "setCoor", "editCoor", "setTool", "editTool", "setPayload",
    "enableVibrationSuppression", "disableVibrationSuppression",
    "setCollisionDetectionSensitivity", "initComplianceControl", 
    "enableComplianceControl", "disableComplianceControl",
    "forceControlZeroCalibrate", "setFilterPeriod", "searchSuccessed",
    # 状态获取与坐标转换
    "getJoint", "getTCP", "aposToCpos", "cposToApos", "cposToCpos",
    "posOffset", "posTrans", "coorRel", "toolRel", "getJointTorque", "getJointExternalTorque",
    # 托盘与逆解
    "createTray", "getTrayPos", "posInverse", "distance", "interPos", "planeTrans",
    "getTrajStart", "getTrajEnd", "arrayAdd", "arraySub", "coorTrans",
    # 运动指令
    "movJ", "movL", "movC", "movCircle", "movLW", "movCW", "movTraj",
    "setWeave", "weaveStart", "weaveEnd",
    # 寄存器与 IO 操作
    "setDO", "getDI", "getDO", "setDOGroup", "getDIGroup", "getDOGroup", 
    "setAO", "getAI", "getAO", "getRegisterBool", "setRegisterBool", 
    "getRegisterInt", "setRegisterInt", "getRegisterFloat", "setRegisterFloat",
    # 通讯
    "RS485init", "RS485flush", "RS485write", "RS485read",
    "readCoils", "readDiscreteInputs", "readHoldingRegisters", "readInputRegisters",
    "writeSingleCoil", "writeSingleRegister", "writeMultipleCoils", "writeMultipleRegisters",
    "createSocketClient", "connectSocketClient", "writeSocketClient", "readSocketClient", "closeSocketClient",
    # 系统控制
    "wait", "waitCondition", "systemTime", "stopProject", "pauseProject", 
    "runScript", "pauseScript", "resumeScript", "stopScript", "callModule", "print",
    "setInterruptInterval", "setInterruptCondition", "clearInterrupt",
    # 字符串与数组
    "strcmp", "strToNumberArray", "arrayToStr",
    # 工艺指令 (焊接、寻位等)
    "enableMultiWeld", "getCurSeam", "isMultiWeldFinished", "setMultiWeldOffset", 
    "weldNextSeam", "resetMultiWeld", "searchStart", "setMasterFlag", 
    "getOffsetValue", "search", "searchEnd", "searchOffset", "searchOffsetEnd", "searchError"
}

def is_valid_variable_name(name: str) -> bool:
    """
    检查变量名是否符合 Codroid 机器人 Lua 语法及系统保留字规则。
    
    Args:
        name: 变量名字符串
        
    Returns:
        bool: 合法返回 True，否则返回 False
    """
    if not name or not isinstance(name, str):
        return False

    # 1. 基础语法规则：字母或下划线开头，后接字母、数字或下划线
    # 同时过滤掉中文（Lua 变量名不建议使用中文）
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', name):
        return False

    # 2. 避免使用双下划线开头
    if name.startswith('__'):
        return False

    # 3. 检查是否为保留关键字或系统函数名
    if name in RESERVED_NAMES:
        return False

    return True