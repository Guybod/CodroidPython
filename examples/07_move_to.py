import time
import threading
from codroid import CodroidControlInterface, MoveToType, MoveTarget

def heartbeat_worker(robot, stop_event):
    """
    后台心跳线程：每 400ms 发送一次 moveToHeartbeat。
    使用 400ms 是为了留出 100ms 的余量，确保符合 500ms 的协议要求。
    """
    print("[心跳] 启动运行维持心跳...")
    while not stop_event.is_set():
        try:
            robot.move_to_heartbeat()
            time.sleep(0.4) 
        except Exception as e:
            print(f"[心跳] 异常中断: {e}")
            break
    print("[心跳] 已停止")

def moveto_demo():
    # 1. 初始化并连接
    with CodroidControlInterface(host="192.168.1.136") as robot:
        
        # 准备心跳控制工具
        stop_event = threading.Event()
        
        try:
            # --- 场景 1: 运动到预设的 Home 位置 ---
            print("\n>>> 场景 1: 运动到 Home 位置")
            robot.move_to(MoveToType.HOME)
            
            # 立即启动心跳维持
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            
            # 假设运动需要 3 秒
            time.sleep(3)
            
            # 停止心跳（模拟运动完成或需要切换指令）
            stop_event.set()
            t.join()


            # --- 场景 2: 关节规划运动到指定坐标 (Type 4) ---
            print("\n>>> 场景 2: 关节规划运动 (Type 4)")
            
            # 定义目标关节角 [j1, j2, j3, j4, j5, j6] 单位: deg
            target_joints = MoveTarget(jp=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            
            robot.move_to(MoveToType.JOINT, target=target_joints)
            
            # 重新启动心跳
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            
            # 运行 5 秒
            time.sleep(5)
            
            # 结束心跳
            stop_event.set()
            t.join()


            # --- 场景 3: 直线规划运动到笛卡尔坐标 (Type 5) ---
            print("\n>>> 场景 3: 直线规划运动 (Type 5)")
            
            # 定义目标末端位置 [x, y, z, a, b, c]
            target_pose = MoveTarget(cp=[350.0, 100.0, 400.0, 180.0, 0.0, 90.0])
            
            robot.move_to(MoveToType.LINEAR, target=target_pose)
            
            # 启动心跳
            stop_event.clear()
            t = threading.Thread(target=heartbeat_worker, args=(robot, stop_event))
            t.start()
            
            time.sleep(4)
            
            # 结束运动
            stop_event.set()
            t.join()

            print("\n所有运动演示完成")

        except Exception as e:
            print(f"执行过程中发生错误: {e}")
            stop_event.set() # 确保线程能关闭

if __name__ == "__main__":
    moveto_demo()