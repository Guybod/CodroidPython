class CodroidError(Exception):
    """Codroid SDK 的基础异常类"""
    pass

class CodroidNetworkError(CodroidError):
    """网络连接或通信异常"""
    pass

class CodroidTimeoutError(CodroidError):
    """操作超时异常"""
    pass