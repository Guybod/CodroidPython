from codroid import CodroidControlInterface

def io_demo():
    with CodroidControlInterface() as robot:
        # 1. 设置数字输出
        print("设置 DO 10 为 1")
        robot.set_do(10, 1)

        # 2. 读取数字输入
        di_val = robot.get_di(0)
        print(f"DI 0 的值为: {di_val}")

        # 3. 设置模拟输出
        print("设置 AO 2 为 4.44")
        robot.set_ao(2, 4.44)

        # 4. 读取模拟输入
        ai_val = robot.get_ai(1)
        print(f"AI 1 的值为: {ai_val}")

        # 5. 批量读取示例
        res = robot.get_io_values([
            {"type": "DI", "port": 0},
            {"type": "AI", "port": 1}
        ])
        print(f"批量读取结果: {res.db}")

if __name__ == "__main__":
    io_demo()