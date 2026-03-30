import time

from codroid import CodroidControlInterface

def demo():
    with CodroidControlInterface() as robot:
        # 定义要运行的程序
        projtecid = "projectluademo"

        index = 0

        res = robot.run_project(projtecid)
        if res.is_success:
            print("运行成功")

        time.sleep(5)

        res = robot.pause_project()
        if res.is_success:
            print("暂停成功")

        time.sleep(5)

        res = robot.resume_project()
        if res.is_success:
            print("恢复成功")

        time.sleep(5)

        res = robot.stop_project()
        if res.is_success:
            print("停止成功")

        time.sleep(5)

        res = robot.run_project_by_index(index)
        if res.is_success:
            print("映射启动成功")

        time.sleep(5)

        res = robot.stop_project()
        if res.is_success:
            print("停止成功")



if __name__ == "__main__":
    demo()