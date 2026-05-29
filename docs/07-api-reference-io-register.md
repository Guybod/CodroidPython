# IO 与寄存器 API 参考

## IO 操作

### 数字 IO

#### GetDi

```python
def GetDi(self, port: int) -> int
```

获取数字输入（DI）值。端口 0~15，返回 0 或 1。

#### GetDo

```python
def GetDo(self, port: int) -> int
```

获取数字输出（DO）值。端口 0~15，返回 0 或 1。

#### SetDo

```python
def SetDo(self, port: int, value: int) -> CommonResponse
```

设置数字输出（DO）值。端口 0~15，值为 0 或 1。

```python
di0 = robot.GetDi(0)        # 读取 DI 端口 0
robot.SetDo(10, 1)          # 设置 DO 端口 10 为 1
robot.SetDo(10, di0)        # 将 DI 值写入 DO
```

---

### 模拟 IO

#### GetAi

```python
def GetAi(self, port: int) -> float
```

获取模拟输入（AI）值。端口 0~3。

#### GetAo

```python
def GetAo(self, port: int) -> float
```

获取模拟输出（AO）值。端口 0~3。

#### SetAo

```python
def SetAo(self, port: int, value: float) -> CommonResponse
```

设置模拟输出（AO）值。端口 0~3。

```python
ai0 = robot.GetAi(0)        # 读取 AI 端口 0
robot.SetAo(0, 3.14)        # 设置 AO 端口 0
```

---

### 批量 IO

#### GetIoValues

```python
def GetIoValues(self, io_requests: List[Dict[str, Any]]) -> CommonResponse
```

批量读取多个 IO 值。

| 参数 | 类型 | 说明 |
|------|------|------|
| `io_requests` | `List[Dict]` | 包含 `type` 和 `port` 的列表 |

```python
response = robot.GetIoValues([
    {"type": "DI", "port": 0},
    {"type": "DI", "port": 1},
    {"type": "AI", "port": 0},
])
for item in response.db:
    print(f"{item['type']}{item['port']} = {item['value']}")
```

#### SetIoValues

```python
def SetIoValues(self, io_list: List[Dict[str, Any]]) -> List[CommonResponse]
```

批量设置 IO 值。内部通过循环调用 `SetDo` / `SetAo` 实现。

```python
robot.SetIoValues([
    {"type": "DO", "port": 0, "value": 1},
    {"type": "DO", "port": 1, "value": 0},
    {"type": "AO", "port": 0, "value": 3.14},
])
```

---

### IO 端口范围

| 类型 | 端口范围 | 值类型 |
|------|----------|--------|
| DI（数字输入） | 0~15 | 0 或 1 |
| DO（数字输出） | 0~15 | 0 或 1 |
| AI（模拟输入） | 0~3 | float |
| AO（模拟输出） | 0~3 | float |

超出范围抛出 `CodroidError`。

---

## 寄存器操作

### GetRegisterValue

```python
def GetRegisterValue(self, address: int) -> Any
```

获取单个寄存器值。

### GetRegisterValues

```python
def GetRegisterValues(self, addresses: List[int]) -> CommonResponse
```

批量获取多个寄存器值。

```python
val = robot.GetRegisterValue(0)
vals = robot.GetRegisterValues([0, 1, 2])
for item in vals.db:
    print(f"R{item['address']} = {item['value']}")
```

### SetRegisterValue

```python
def SetRegisterValue(self, address: int, value: Any) -> CommonResponse
```

写入寄存器值。

```python
robot.SetRegisterValue(0, 42)
robot.SetRegisterValue(1, 3.14)
```

---

### 扩展数组

#### SetExtendArrayType

```python
def SetExtendArrayType(self, index: int, data_type: ExtendArrayType) -> CommonResponse
```

设置扩展数组数据类型。`index` 范围 0~999。

| 数据类型 | 说明 |
|----------|------|
| `ExtendArrayType.BOOL` | 布尔 |
| `ExtendArrayType.UINT8` | 无符号 8 位整数 |
| `ExtendArrayType.INT8` | 有符号 8 位整数 |
| `ExtendArrayType.UINT16` | 无符号 16 位整数 |
| `ExtendArrayType.INT16` | 有符号 16 位整数 |
| `ExtendArrayType.UINT32` | 无符号 32 位整数 |
| `ExtendArrayType.INT32` | 有符号 32 位整数 |
| `ExtendArrayType.FLOAT32` | 32 位浮点数 |

```python
from codroid import ExtendArrayType

robot.SetExtendArrayType(0, ExtendArrayType.FLOAT32)
```

#### RemoveExtendArray

```python
def RemoveExtendArray(self, index: int) -> CommonResponse
```

删除扩展数组索引（重置数据）。`index` 范围 0~999。

---

## 完整 IO + 寄存器示例

```python
from codroid import CodroidClient, ExtendArrayType, InitConsoleUtf8

InitConsoleUtf8()

with CodroidClient(host="192.168.8.136") as robot:
    robot.ConnectRemoteAndSwitchOn()

    # --- IO ---
    # 读取单个 DI
    di0 = robot.GetDi(0)
    print(f"DI 0 = {di0}")

    # 写入单个 DO
    robot.SetDo(10, 1)

    # 批量读取
    io_data = robot.GetIoValues([
        {"type": "DI", "port": 0},
        {"type": "DI", "port": 1},
        {"type": "AI", "port": 0},
    ])
    for item in io_data.db:
        print(f"  {item['type']}{item['port']} = {item['value']}")

    # --- 寄存器 ---
    # 读取单个
    val = robot.GetRegisterValue(0)
    print(f"R0 = {val}")

    # 写入
    robot.SetRegisterValue(0, val + 1)

    # 批量读取
    regs = robot.GetRegisterValues([0, 1, 2])
    for item in regs.db:
        print(f"  R{item['address']} = {item['value']}")

    # 扩展数组
    robot.SetExtendArrayType(0, ExtendArrayType.FLOAT32)
    robot.RemoveExtendArray(0)
```
