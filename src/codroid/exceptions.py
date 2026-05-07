class CodroidError(Exception):
    """Codroid SDK 的基础异常类"""
    pass


class CodroidCommandException(CodroidError):
    """控制器返回 ``err`` 或协议失败（与 C# ``CodroidCommandException`` 文档对齐；当前与 ``CodroidError`` 并列使用）。"""
    pass

class CodroidNetworkError(CodroidError):
    """网络连接或通信异常"""
    pass

class CodroidTimeoutError(CodroidError):
    """操作超时异常"""
    pass