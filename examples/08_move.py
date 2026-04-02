import time

from codroid import CodroidControlInterface, MovePoint

def move_demo():
    robot = CodroidControlInterface(host="192.168.1.136",local_ip="192.168.1.150",udp_port=10086)
    robot.debug = True
    robot.connect()

    # 1. 关节运动到 A 点
    p1_j = MovePoint(jp=[0, 0, 90, 0, 90, 0])
    p2_j = MovePoint(jp=[0, 0, 0, 0, 0, 0])
    robot.move_j(p2_j, speed=10, acc=40)
    while True:
        # 获取缓存
        data = robot.get_statues()
        
        # 解决 Pylance 报错：检查 data 是否存在
        if data is not None:
            if not data.status.is_moving:
                break
            print(f"机器人正在运行... 当前位置: {data.joint_pos}")
        else:
            print("等待实时数据包...")
        
        time.sleep(0.01) # 降低 CPU 占用，100ms 检查一次
    robot.move_j(p1_j, speed=10, acc=40)
    while True:
        # 获取缓存
        data = robot.get_statues()
        
        # 解决 Pylance 报错：检查 data 是否存在
        if data is not None:
            if not data.status.is_moving:
                break
            print(f"机器人正在运行... 当前位置: {data.joint_pos}")
        else:
            print("等待实时数据包...")
        
        time.sleep(0.05) # 降低 CPU 占用，50ms 检查一次

    print("运动已完成")
    # # 2. 直线运动到 B 点 (带平滑过渡)
    # p2 = MovePoint(cp=[400, 100, 300, 180, 0, 0])
    # robot.move_l(p2, speed=100, acc=200, blend=10)

    # # 3. 圆弧运动 (必须是 cp)
    # target_cp = [400, -100, 300, 180, 0, 0]
    # middle_cp = [450, 0, 300, 180, 0, 0]
    # robot.move_c(target_cp, middle_cp, speed=50, acc=100)

    time.sleep(5)

if __name__ == "__main__":
    move_demo()