# 辅助工具 API 参考

## 发布 / 订阅

### PublishTopics

```python
class PublishTopics:
    PROJECT_STATE = "publish/ProjectState"
    VAR_UPDATE = "publish/VarUpdate"
    ROBOT_STATUS = "publish/RobotStatus"
    ROBOT_POSTURE = "publish/RobotPosture"
    ROBOT_COORDINATE = "publish/RobotCoordinate"
    LOG = "publish/Log"
    ERROR = "publish/Error"
```

控制器推送主题常量。

---

### PublishNotification

```python
@dataclass
class PublishNotification:
    ty: str        # 主题类型
    db: Any        # 推送数据
    raw_json: str  # 原始 JSON 字符串
```

---

### PublishTopicSubscription

```python
class PublishTopicSubscription:
    def dispose(self) -> None
    def Dispose(self) -> None  # C# 别名
```

订阅句柄。调用 `dispose()` 取消本地回调（不会向控制器发送取消订阅）。

---

### SubscribePublishTopic（仅 CodroidClient）

```python
def SubscribePublishTopic(
    self,
    topic_ty: str,
    handler: Callable[[PublishNotification], None],
    tc_milliseconds: int = 100,
) -> PublishTopicSubscription
```

订阅控制器推送主题。首次本地订阅时自动向控制器发送订阅请求。

```python
from codroid import CodroidClient, PublishTopics, InitConsoleUtf8

InitConsoleUtf8()

def on_status(notification):
    print(f"收到 {notification.ty}: {notification.db}")

def on_error(notification):
    print(f"错误: {notification.db}")

with CodroidClient(host="192.168.8.136") as robot:
    robot.ConnectRemoteAndSwitchOn()

    sub1 = robot.SubscribePublishTopic(PublishTopics.ROBOT_STATUS, on_status)
    sub2 = robot.SubscribePublishTopic(PublishTopics.ERROR, on_error)

    # ... 运行 ...

    sub1.dispose()
    sub2.dispose()
```

---

## 全局变量

### GetGlobalVars

```python
def GetGlobalVars(self) -> CommonResponse
```

获取所有全局变量。

### GetGlobalVarsCatalog

```python
def GetGlobalVarsCatalog(self) -> CommonResponse
```

获取全局变量目录（与 `GetGlobalVars` 相同 TCP 请求）。

### SaveGlobalVar

```python
def SaveGlobalVar(self, name: str, variable: GlobalVariable) -> CommonResponse
```

保存单个全局变量。

### SaveGlobalVars

```python
def SaveGlobalVars(self, variables: Dict[str, GlobalVariable]) -> CommonResponse
```

批量保存全局变量。变量名会经过 Lua 保留字校验。

### RemoveGlobalVars

```python
def RemoveGlobalVars(self, names: List[str]) -> CommonResponse
```

删除全局变量。

### GetProjectVar

```python
def GetProjectVar(self) -> CommonResponse
```

获取当前所有工程变量值（仅在工程运行中有效）。

```python
from codroid import GlobalVariable

# 保存
robot.SaveGlobalVar("counter", GlobalVariable(value=0, note="计数器"))
robot.SaveGlobalVar("name", GlobalVariable(value="test"))

# 批量保存
robot.SaveGlobalVars({
    "x": GlobalVariable(value=100.0),
    "y": GlobalVariable(value=200.0),
})

# 读取
response = robot.GetGlobalVars()
print(response.db)

# 删除
robot.RemoveGlobalVars(["counter", "name"])

# 获取工程变量（工程运行中）
proj_vars = robot.GetProjectVar()
```

---

## 运动学

### AposToCpos

```python
def AposToCpos(
    self,
    jp: Sequence[float],
    coor: Optional[Sequence[float]] = None,
    tool: Optional[Sequence[float]] = None,
    ep: Sequence[float] = [],
) -> CommonResponse
```

正解（关节 → 笛卡尔）。`jp` 为 6 个关节角（度）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `jp` | `Sequence[float]` | 6 个关节角（度） |
| `coor` | `Sequence[float]` | 用户坐标系 `[x,y,z,a,b,c]` |
| `tool` | `Sequence[float]` | 工具坐标系 `[x,y,z,a,b,c]` |
| `ep` | `Sequence[float]` | 外部轴位置 |

```python
response = robot.AposToCpos([0, 0, 90, 0, 90, 0])
print(f"TCP 位姿: {response.db}")
```

### CposToApos

```python
def CposToApos(
    self,
    cp: Sequence[float],
    rj: Optional[Sequence[float]] = None,
    ep: Sequence[float] = [],
) -> CommonResponse
```

逆解（笛卡尔 → 关节）。`cp` 为 `[x,y,z,a,b,c]`（mm + 度）。`rj` 为参考关节角（默认 `[20,20,20,20,20,20]`）。

```python
response = robot.CposToApos([400, 200, 500, 180, 0, 90])
print(f"关节角: {response.db}")
```

### CalculateRelativePose

```python
def CalculateRelativePose(
    self,
    pos: Sequence[float],
    offset: Sequence[float],
    coor_type: CoordinateType = CoordinateType.TOOL,
    pos_coor: Optional[Sequence[float]] = None,
    coor: Optional[Sequence[float]] = None,
) -> CommonResponse
```

笛卡尔坐标偏移计算。

| 参数 | 类型 | 说明 |
|------|------|------|
| `pos` | `Sequence[float]` | 当前 TCP 位姿 |
| `offset` | `Sequence[float]` | 偏移量 |
| `coor_type` | `CoordinateType` | `USER` 或 `TOOL` |
| `pos_coor` | `Sequence[float]` | 当前 TCP 坐标系 |
| `coor` | `Sequence[float]` | 偏移坐标系 |

```python
from codroid import CoordinateType

response = robot.CalculateRelativePose(
    pos=[400, 200, 500, 180, 0, 90],
    offset=[0, 0, -100, 0, 0, 0],
    coor_type=CoordinateType.TOOL,
)
print(f"偏移后位姿: {response.db}")
```

---

## ConsoleUtf8

### InitConsoleUtf8

```python
def InitConsoleUtf8() -> None
```

Windows 控制台 UTF-8 初始化。在 `cmd`（非 Windows Terminal）下运行含中文的示例时，须在入口调用。Linux / macOS 上为 no-op。

```python
from codroid import InitConsoleUtf8

InitConsoleUtf8()
```

历史别名：`init_console_utf8 = InitConsoleUtf8`

---

## PrintBanner

```python
from codroid import PrintBanner

PrintBanner("标题", "副标题")
```

在终端打印彩色横幅标题。需要安装 `colorama`：`pip install "codroid-robot-sdk[color]"`。

---

## 完整辅助工具示例

```python
from codroid import (
    CodroidClient,
    PublishTopics,
    GlobalVariable,
    CoordinateType,
    InitConsoleUtf8,
    PrintBanner,
)

InitConsoleUtf8()
PrintBanner("辅助工具示例", "Publish / 全局变量 / 运动学")

ROBOT_IP = "192.168.8.136"

# --- Publish / Subscribe ---
def on_status(notification):
    print(f"[Publish] {notification.ty}: {notification.db}")

with CodroidClient(host=ROBOT_IP) as robot:
    robot.ConnectRemoteAndSwitchOn()

    sub = robot.SubscribePublishTopic(PublishTopics.ROBOT_STATUS, on_status)

    # --- 全局变量 ---
    robot.SaveGlobalVar("test_var", GlobalVariable(value=42, note="测试"))
    response = robot.GetGlobalVars()
    print(f"全局变量: {response.db}")
    robot.RemoveGlobalVars(["test_var"])

    # --- 运动学 ---
    fk = robot.AposToCpos([0, 0, 90, 0, 90, 0])
    print(f"正解结果: {fk.db}")

    ik = robot.CposToApos([400, 200, 500, 180, 0, 90])
    print(f"逆解结果: {ik.db}")

    rel = robot.CalculateRelativePose(
        pos=[400, 200, 500, 180, 0, 90],
        offset=[0, 0, -100, 0, 0, 0],
        coor_type=CoordinateType.TOOL,
    )
    print(f"偏移结果: {rel.db}")

    sub.dispose()
```
