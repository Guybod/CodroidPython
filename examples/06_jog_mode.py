import time
import threading
from codroid import CodroidControlInterface, JogMode, JogCoorType

def start_heartbeat(robot, stop_event, interval=0.4):
    """后台心跳线程函数"""
    while not stop_event.is_set():
        try:
            robot.jog_heartbeat()
            time.sleep(interval)
        except Exception:
            break

def jog_demo():
    with CodroidControlInterface() as robot:
        # 1. 设置倍率
        robot.set_manual_move_rate(50)
        
        # 2. 准备心跳控制
        stop_heartbeat = threading.Event()
        heartbeat_thread = threading.Thread(
            target=start_heartbeat, 
            args=(robot, stop_heartbeat)
        )

        print("开始点动 (轴1，正方向)...")
        robot.jog(mode=JogMode.JOINT, index=1, speed=-0.5)
        
        # 启动心跳
        heartbeat_thread.start()
        
        # 运动 2 秒
        time.sleep(2)
        
        # 3. 停止点动
        print("停止点动")
        stop_heartbeat.set() # 停止心跳
        heartbeat_thread.join()
        robot.stop_jog()

if __name__ == "__main__":
    jog_demo()