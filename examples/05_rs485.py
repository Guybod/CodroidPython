from codroid import CodroidControlInterface, RS485BaudRate

def main():
    # 使用上下文管理器确保连接关闭
    with CodroidControlInterface() as robot:
        # 1. 初始化 485 接口
        print("初始化 485: 115200, N, 8, 1")
        robot.rs485_init(baudrate=RS485BaudRate.B115200)

        # 2. 清空缓存
        robot.rs485_flush()

        # 3. 发送数据 (例如控制夹爪的指令)
        cmd = b"\x01\x03\x00\x00\x00\x02\xC4\x0B" # 示例 Modbus 指令
        print(f"发送数据: {cmd.hex()}")
        robot.rs485_write(cmd)

        # 4. 读取响应
        print("等待响应...")
        res = robot.rs485_read(length=7, timeout=1000)
        
        if res.is_success and res.db:
            # 这里的 res.db 是 [1, 3, 4, ...] 这种整数列表
            received_bytes = bytes(res.db)
            print(f"收到数据 (Hex): {received_bytes.hex()}")
        else:
            print("未收到数据或读取失败")

if __name__ == "__main__":
    main()