from codroid import CodroidControlInterface, CRIMask, CRIStreamHandler, CRIData
import time

def cri_demo():
    LOCAL_IP = "192.168.1.1"
    LOCAL_PORT = 18888
    ROBOT_IP = "192.168.1.136"

    # 1. 创建 UDP 接收器
    # 假设我们只需要时间戳、状态和关节位置
    my_mask = CRIMask.TIMESTAMP | CRIMask.STATUS_1 | CRIMask.JOINT_POS
    handler = CRIStreamHandler(high_precision=False, mask=my_mask)
    handler.bind(LOCAL_PORT)

    with CodroidControlInterface(host=ROBOT_IP) as robot:
        # 2. 通知机器人开始向我推送数据
        res = robot.start_data_push(ip=LOCAL_IP, port=LOCAL_PORT, duration=10, mask=my_mask)
        
        print(res)
        print("开始接收实时数据流...")
        try:
            for _ in range(10):
                data, addr = handler._sock.recvfrom(2048)
                parsed = handler.parse_packet(data)
                print("------------------------------------------------------------------------")
                print(f"时间戳: {parsed.timestamp}, 末端线速度: {parsed.tcp_speed}")
                print(f"关节位置: {parsed.joint_pos}, 关节速度: {parsed.joint_vel}")
                print(f"末端位置: {parsed.cartesian_pos}, 末端速度: {parsed.cartesian_vel}")
                print(f"关节力矩: {parsed.joint_torque}, 关节外力: {parsed.external_torque}")
                if parsed.status.project_running:
                    print("工程运行")
                if parsed.status.project_paused:
                    print("工程暂停")
                if parsed.status.project_stopped:
                    print("工程停止")
                if parsed.status.is_enabling:
                    print("使能")
                if parsed.status.is_disabled:
                    print("未使能")
                if parsed.status.is_manual:
                    print("手动模式下")
                if parsed.status.is_dragging:
                    print("拖动中")
                else:
                    print("未拖动")
                if parsed.status.is_moving:
                    print("运动中")
                else:
                    print("未运动")
                if parsed.status.collision_stop:
                    print("碰撞报警")
                if parsed.status.is_at_safe_pos:
                    print("在安全点位")
                if parsed.status.has_alarm:
                    print("有报警")
                if parsed.status.is_simulation:
                    print("仿真模式")
                if parsed.status.is_emergency_stop:
                    print("急停按下")
                if parsed.status.is_rescue:
                    print("救援模式")
                if parsed.status.is_auto:
                    print("自动模式")
                if parsed.status.is_remote:
                    print("远程模式")
                if parsed.status.rt_control_mode:
                    print("实施控制模式开启")
                print(f"时间戳: {parsed.timestamp}, 关节: {parsed.joint_pos}")
        finally:
            robot.stop_data_push(ip=LOCAL_IP, port=LOCAL_PORT)

if __name__ == "__main__":
    cri_demo()