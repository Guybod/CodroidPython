from codroid import CodroidControlInterface, MotionPath, MovePoint

def path_demo():
    with CodroidControlInterface() as robot:
        # 1. 创建路径构建器
        path = MotionPath()
        
        # 2. 链式添加一系列指令
        path.mov_j(MovePoint(jp=[0, 0, 90, 0, 90, 0]), speed=60, acc=150) \
            .mov_l(MovePoint(cp=[494,191,444,-180,0,-90]), speed=500, acc=1500, blend=30) \
            .mov_l(MovePoint(cp=[294,191,444,-180,0,-90]), speed=500, acc=1500, blend=30) \
            .mov_l(MovePoint(cp=[494,391,444,-180,0,-90]), speed=500, acc=1500, blend=30) \
            .mov_l(MovePoint(cp=[494,191,644,-180,0,-90]), speed=500, acc=1500, blend=30) \
            .mov_j(MovePoint(jp=[0, 0, 90, 0, 90, 0]), speed=60, acc=150, blend=0)
        
        # 3. 一次性执行
        print("正在发送连续路径...")
        res = robot.execute_path(path)
        
        if res.is_success:
            print("路径指令已送达机器人")

if __name__ == "__main__":
    path_demo()