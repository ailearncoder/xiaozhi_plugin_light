class RpcError(Exception):
    def __init__(self, message: str, code: int = 500):
        self.code = code
        super().__init__(f"[{code}] {message}")

class ConnectionError(RpcError):
    def __init__(self, message: str):
        super().__init__(f"连接错误: {message}", 503)

class TimeoutError(RpcError):
    def __init__(self, operation: str, timeout: float):
        super().__init__(f"操作超时: {operation} ({timeout}s)", 504)

class PropertyTypeError(TypeError):
    """Exception raised when a property has an invalid type."""
    pass

class PropertyValueError(ValueError):
    """Exception raised when a property returns an invalid value."""
    pass
