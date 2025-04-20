import socket
from typing import Optional
from .exceptions import ConnectionError
import time

class ConnectionManager:
    def __init__(self, host: str = 'localhost', port: int = 8080):
        self.host = host
        self.port = port
        self._connection: Optional[socket.socket] = None
        self._buffer = b""  # 新增缓冲区
        self._connected = False  # 新增连接状态

    def create_connection(self) -> socket.socket:
        try:
            if not self._connected:  # 防止重复连接
                self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._connection.settimeout(5)  # 默认超时时间
                self._connection.connect((self.host, self.port))
                self._connected = True
            return self._connection
        except OSError as e:
            raise ConnectionError(f"Connection failed: {e}")

    # 新增通用数据操作方法
    def send_all(self, data):
        try:
            return self._connection.sendall(data)
        except OSError:
            self.close_connection()
            raise ConnectionError("Connection lost during sending")

    def recv_until(self, delimiter=b"\n", timeout=5):
        """接收数据直到遇到分隔符"""
        start_time = time.time()
        while delimiter not in self._buffer:
            try:
                self._connection.settimeout(timeout)
                chunk = self._connection.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed by server")
                self._buffer += chunk
                if time.time() - start_time > timeout:
                    raise TimeoutError("Receive timed out")
            except socket.timeout:
                raise TimeoutError("Receive timed out")
        line, _, self._buffer = self._buffer.partition(delimiter)
        return line

    def close_connection(self):
        if self._connection:
            try:
                self._connection.close()
            finally:
                self._connected = False
                self._buffer = b""
                self._connection = None
