import socket
import threading
from typing import Callable, Any
import logging

class NetworkManager:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self._message_callback = None
        self._error_callback = None
        self._connection_thread = None

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def start_message_handling(self, 
                              message_callback: Callable[[Any], None],
                              error_callback: Callable[[Exception], None]):
        self._message_callback = message_callback
        self._error_callback = error_callback
        
        self._connection_thread = threading.Thread(target=self._handle_messages)
        self._connection_thread.daemon = True
        self._connection_thread.start()

    def send_data(self, data: bytes) -> bool:
        if not self.connected or not self.socket:
            return False
        try:
            logging.debug(f"Sending data: {len(data)}: {data}")
            self.socket.sendall(data)
            return True
        except Exception as e:
            self.connected = False
            return False

    def _handle_messages(self):
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if data and self._message_callback:
                    self._message_callback(data)
            except Exception as e:
                self.connected = False
                if self._error_callback:
                    self._error_callback(e)
                break

    def disconnect(self):
        if self.connected and self.socket:
            self.socket.close()
            self.connected = False
