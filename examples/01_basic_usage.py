"""
基础示例：连接机器人并停止当前工程
"""
from codroid import CodroidControlInterface

def main():
    # 初始化接口（默认 IP 192.168.1.136）
    robot = CodroidControlInterface(host="192.168.1.136")
    
    try:
        # 建立连接
        robot.connect()
        print("连接成功")

        robot.debug = True
        # 停止当前运行的工程
        print("正在停止工程...")
        response = robot.stop_project()
        print(f"服务器响应: ID={response.id}, 类型={response.ty}")

    finally:
        # 务必记得断开连接
        robot.disconnect()
        print("已断开连接")

if __name__ == "__main__":
    main()