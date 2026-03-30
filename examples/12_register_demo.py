from codroid import CodroidControlInterface, ExtendArrayType

def register_demo():
    with CodroidControlInterface() as robot:
        # 1. 操作基础寄存器
        print("设置寄存器 49300 为 123.45")
        robot.set_register_value(49300, 123.45)
        
        val = robot.get_register(49300)
        print(f"寄存器 49300 的值为: {val}")

        # 2. 操作扩展数组
        print("配置扩展数组索引 999 为 Float32 类型")
        robot.set_extend_array_type(999, ExtendArrayType.FLOAT32)
        
        # 3. 删除/重置扩展数组
        print("重置扩展数组索引 999")
        robot.remove_extend_array(999)

if __name__ == "__main__":
    register_demo()