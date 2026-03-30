from codroid import CodroidControlInterface, MovePoint

def move_demo():
    with CodroidControlInterface() as robot:
        # 1. 关节运动到 A 点
        p1 = MovePoint(jp=[0, -90, 90, 0, 90, 0])
        robot.move_j(p1, speed=50, acc=100)

        # 2. 直线运动到 B 点 (带平滑过渡)
        p2 = MovePoint(cp=[400, 100, 300, 180, 0, 0])
        robot.move_l(p2, speed=100, acc=200, blend=10)

        # 3. 圆弧运动 (必须是 cp)
        target_cp = [400, -100, 300, 180, 0, 0]
        middle_cp = [450, 0, 300, 180, 0, 0]
        robot.move_c(target_cp, middle_cp, speed=50, acc=100)

if __name__ == "__main__":
    move_demo()