from codroid import CodroidControlInterface, GlobalVariable

def demo():
    with CodroidControlInterface() as robot:
        # 定义要保存的变量组
        vars_to_save = {
            "v_int": GlobalVariable(value=1024, note="整数示例"),
            "v_str": GlobalVariable(value="Codroid", note="字符串示例"),
            "v_list": GlobalVariable(value=[1.1, 2.2, 3.3], note="数展示例"),
            "v_map": GlobalVariable(value={"power": 100, "status": "on"}, note="Map示例")
        }

        print("正在增量保存全局变量...")
        res = robot.save_global_variables(vars_to_save)
        
        if res.is_success:
            print("保存成功！")

if __name__ == "__main__":
    demo()