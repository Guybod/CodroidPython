from codroid import CodroidControlInterface

def run_demo():
    # 使用 context manager (with) 是最推荐的做法
    with CodroidControlInterface() as robot:
        # 定义 Lua 程序
        lua_code = "print('Hello Codroid')\nmovej([0,0,0,0,0,0])"
        
        # 定义共享变量
        vars_data = {"v1": 100, "v2": "test"}

        print("开始发送脚本...")
        res = robot.__run_script(main_code=lua_code, vars=vars_data)
        
        if res.is_success:
            print("脚本执行请求已发送")
        else:
            print(f"发送失败: {res.err}")

if __name__ == "__main__":
    run_demo()