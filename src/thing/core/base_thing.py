from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
import json

class BaseThing(ABC):
    def __init__(self, host: str = "127.0.0.1", port: int = 80):
        self.connected = False
        self.instance_id = None
        self.host = host
        self.port = port
        self._enable = False

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_definition(self) -> str:
        pass

    def setEnabled(self, enabled: bool) -> Tuple[bool, str]:
        self._enable = enabled
        return (True, "")

    # 新增通用网络操作方法
    def send_json(self, data: Dict[str, Any]) -> bool:
        """统一JSON发送方法"""
        return self._send_data(json.dumps(data).encode())

    @abstractmethod
    def _send_data(self, data: bytes) -> bool:
        pass
