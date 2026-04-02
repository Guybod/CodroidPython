"""
基础示例：连接机器人并停止当前工程
"""
from codroid import CodroidControlInterface, MovePoint


def main():

    # 初始化时指定本地接收数据的 IP 和端口
    robot = CodroidControlInterface(
        host="192.168.8.136", 
        local_ip="192.168.8.1", 
        udp_port=10086
    )

    # 调用 connect 时会自动：连接TCP -> 切自动 -> 切远程 -> 开启推送 -> 启动线程
    robot.connect()
    robot.switch_on()

    p1 = MovePoint(jp=[0, 0, 90, 0, 90, 0])
    p2 = MovePoint(jp=[0, 0, 0, 0, 0, 0])
    robot.move_j(p1,60,120)
    robot.move_j(p2,60,120)
    robot.move_j(p1,60,120)
    robot.move_j(p2,60,120)
    robot.move_j(p1,60,120)
    robot.move_j(p2,60,120)

    try:
        while True:
            # 直接从缓存中读取实时数据
            data = robot.cri_cache
            if data:
                print(f"当前关节角度: {data.joint_pos}")
                print(f"是否正在运动: {data.status.is_moving}")
            import time
            time.sleep(0.1)
    except KeyboardInterrupt:
        robot.disconnect()

if __name__ == "__main__":
    main()