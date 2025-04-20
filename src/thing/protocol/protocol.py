import enum
import struct
import json
from typing import Callable, Union, Optional, List, Tuple

class MessageType(enum.IntEnum):
    """消息类型枚举"""
    BINARY = 0
    TEXT = 1

    @classmethod
    def from_byte(cls, value: int) -> 'MessageType':
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Unknown message type: {value}")

def serialize(message: [str | bytes], type: MessageType = None) -> bytes:
    send_data = bytearray()
    if type is None:
        if isinstance(message, str):
            type = MessageType.TEXT
            send_data.extend(message.encode('utf-8'))
        elif isinstance(message, bytes):
            type = MessageType.BINARY
            send_data.extend(message)
        else:
            raise ValueError("Invalid message type")
    data = bytearray()
    data.append(type.value)
    data.extend(struct.pack("<I", len(send_data)))
    data.extend(send_data)
    return data

def serialize_obj(obj: [dict | list]) -> bytes:
    if isinstance(obj, dict):
        return serialize(json.dumps(obj, ensure_ascii=False))
    elif isinstance(obj, list):
        return serialize(json.dumps(obj, ensure_ascii=False))
    else:
        raise ValueError("Invalid object type")

class ParsedMessage:
    """解析后的消息结构"""
    class BinaryMessage:
        def __init__(self, data: bytes):
            self.data = data

        def __eq__(self, other):
            if not isinstance(other, ParsedMessage.BinaryMessage):
                return False
            return self.data == other.data

        def __repr__(self):
            return f"BinaryMessage(data={self.data!r})"

    class TextMessage:
        def __init__(self, text: str):
            self.text = text

        def __eq__(self, other):
            if not isinstance(other, ParsedMessage.TextMessage):
                return False
            return self.text == other.text

        def __repr__(self):
            return f"TextMessage(text={self.text!r})"

class MessageParser:
    HEADER_SIZE = 5

    def __init__(self,
                 on_message_received: Callable[[Union[ParsedMessage.BinaryMessage, ParsedMessage.TextMessage]], None],
                 on_error: Callable[[Exception], None]):
        self.on_message_received = on_message_received
        self.on_error = on_error
        self.buffer = bytearray()
        self.current_message_length = -1
        self.current_message_type = None

    def process_data(self, data: bytes, offset: int = 0, length: Optional[int] = None):
        try:
            if length is None:
                length = len(data) - offset

            # Add new data to buffer
            self.buffer.extend(data[offset:offset+length])

            # Parse messages
            self._parse_messages()
        except Exception as e:
            self.buffer.clear()
            self.current_message_length = -1
            self.current_message_type = None
            self.on_error(e)

    def _parse_messages(self):
        while len(self.buffer) > 0:
            # Try to parse header
            if self.current_message_length == -1 or self.current_message_type is None:
                if len(self.buffer) < self.HEADER_SIZE:
                    # Not enough data for header
                    return

                try:
                    type_value = self.buffer[0]
                    self.current_message_type = MessageType.from_byte(type_value)

                    # Python uses network byte order (big-endian) by default, but we need little-endian
                    self.current_message_length = struct.unpack_from("<I", self.buffer, 1)[0]

                    if self.current_message_length < 0:
                        raise ValueError(f"Invalid message length: {self.current_message_length}")
                except ValueError as e:
                    raise ValueError(f"Invalid message header: {e}")

            # Check if we have a complete message
            total_length = self.HEADER_SIZE + self.current_message_length
            if len(self.buffer) < total_length:
                # Not enough data for message body
                return

            # Extract message content
            message_body = bytes(self.buffer[self.HEADER_SIZE:total_length])

            # Create and process message
            if self.current_message_type == MessageType.BINARY:
                parsed_message = ParsedMessage.BinaryMessage(message_body)
            elif self.current_message_type == MessageType.TEXT:
                parsed_message = ParsedMessage.TextMessage(message_body.decode('utf-8'))
            else:
                raise ValueError(f"Unsupported message type: {self.current_message_type}")

            self.on_message_received(parsed_message)

            # Remove processed message from buffer
            del self.buffer[:total_length]

            # Reset state for next message
            self.current_message_length = -1
            self.current_message_type = None

    def reset(self):
        self.buffer.clear()
        self.current_message_length = -1
        self.current_message_type = None

if __name__ == "__main__":
    def on_message(message):
        if isinstance(message, ParsedMessage.TextMessage):
            print(f"Received text message: {message.text}")
        elif isinstance(message, ParsedMessage.BinaryMessage):
            print(f"Received binary message of length: {len(message.data)}")

    def on_error(error):
        print(f"Error: {error}")

    parser = MessageParser(on_message, on_error)
    parser.process_data(b'\x01\x05\x00\x00\x00Hello')  # 文本消息 "Hello"
    parser.process_data(b'\x00\x03\x00\x00\x00\x01\x02\x03')  # 二进制消息 [1,2,3]
    parser.process_data(b'\x01\x05\x00\x00\x00Hello\x00\x03\x00\x00\x00\x01\x02\x03')
