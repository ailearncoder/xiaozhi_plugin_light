from abc import ABC, abstractmethod

class MessageParser(ABC):
    @abstractmethod
    def parse(self, raw_data: bytes):
        """解析原始数据为消息对象"""
        pass

    @abstractmethod
    def serialize(self, message) -> bytes:
        """序列化消息对象为字节数据"""
        pass