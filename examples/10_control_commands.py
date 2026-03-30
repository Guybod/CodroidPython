from codroid import CodroidControlInterface, CodroidError
import time

def demo_control():
    # 使用上下文管理器自动连接
    with CodroidControlInterface(host="192.168.1.136") as robot:
        try:
            # 1. 清除可能存在的错误
            print("正在清除错误...")
            robot.clear_error()
            time.sleep(0.5)

            # 2. 机器人上使能
            print("正在上使能...")
            robot.switch_on()
            time.sleep(1)

            # 3. 切换到仿真模式进行测试
            print("进入仿真模式...")
            robot.to_simulation()

            # 4. 尝试进入拖拽模式 (假设当前在允许的模式下)
            print("开启拖拽模式...")
            robot.start_drag()
            time.sleep(5) # 允许用户拖动 5 秒
            
            print("关闭拖拽模式...")
            robot.stop_drag()

            # 5. 下使能
            print("正在下使能...")
            robot.switch_off()

        except CodroidError as e:
            print(f"操作失败: {e}")

if __name__ == "__main__":
    demo_control()