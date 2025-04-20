from ast import Dict
from typing import Any, Optional
from ..utils.connection import ConnectionManager
from ..utils.exceptions import RpcError, TimeoutError
import json
import os
import threading
import logging
import uuid

level_mapping = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET
}
logging.basicConfig(level=level_mapping.get(os.getenv("LOG_LEVEL", 'ERROR'), logging.ERROR),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
rpc_logger = logging.getLogger('rpc')

class GenericRpcClient():
    def __init__(self, endpoint = '127.0.0.1:80', timeout=5):
        self.host, port = endpoint.split(":")
        self.host = os.getenv("RPC_HOST", self.host)
        port = os.getenv("RPC_PORT", port)
        self.port = int(port)
        self.timeout = timeout
        self.instance_cache = {}
        self.request_counter = 0
        self._lock = threading.Lock()
        self.conn_manager = ConnectionManager(self.host, self.port)
        self._buffer = b""
        self._connected = False

    def __del__(self):
        self.close()

    def _next_id(self):
        self.request_counter += 1
        return f"py_{self.request_counter}_{uuid.uuid4().hex[:6]}"

    def _ensure_connection(self):
        """自动由ConnectionManager维护连接"""
        try:
            self.conn_manager.create_connection()
        except ConnectionError as e:
            raise RpcError(str(e), code=-32001)

    def _reconnect(self):
        """重连简化为重置连接"""
        self.conn_manager.close_connection()
        self._ensure_connection()

    def close(self):
        """关闭连接"""
        self.conn_manager.close_connection()

    def _send_all(self, data):
        """发送数据委托给ConnectionManager"""
        try:
            self.conn_manager.send_all(data)
        except ConnectionError:
            self._reconnect()
            self.conn_manager.send_all(data)

    def _recv_until(self):
        """接收数据委托给ConnectionManager"""
        try:
            return self.conn_manager.recv_until(timeout=self.timeout)
        except TimeoutError as e:
            raise RpcError(str(e), code=-32003)
        except ConnectionError as e:
            raise RpcError(str(e), code=-32004)

    def _send_request(self, payload):
        """发送请求并接收响应"""
        with self._lock:
            try:
                self._ensure_connection()
                request_id = payload["id"]
                
                # 发送请求
                data = json.dumps(payload, ensure_ascii=False)
                rpc_logger.debug("Sending request: %s", data)
                self._send_all(data.encode() + b"\n")

                # 接收响应
                while True:
                    line = self._recv_until()
                    rpc_logger.debug("Received response: %s", line)
                    response:dict = json.loads(line.decode())

                    if "id" not in response:
                        continue  # 跳过通知类型的消息
                    if response["id"] == request_id:
                        if "error" in response:
                            error:dict = response ["error"]
                            raise RpcError(error.get("message"), code=error.get("code"))
                        return response.get("result")
                    
            except json.JSONDecodeError as e:
                raise RpcError(f"Invalid JSON response: {str(e)}", code=-32002)
            except Exception as e:
                self.close()
                logging.error(f"RPC communication failed", exc_info = e)
                if isinstance(e, RpcError):
                    raise
                raise RpcError(f"RPC communication failed: {str(e)}")
    
    def get_static_field(self, class_name, field_name):
        """获取静态字段值"""
        payload = {
            "jsonrpc": "2.0",
            "method": "getStaticField",
            "params": {
                "className": class_name,
                "fieldName": field_name
            },
            "id": self._next_id()
        }
        return self._send_request(payload)
    
    def create_instance(self, class_name, constructor_params):
        """创建新实例"""
        payload = {
            "jsonrpc": "2.0",
            "method": "createInstance",
            "params": {
                "className": class_name,
                "constructorParams": constructor_params
            },
            "id": self._next_id()
        }
        return self._send_request(payload)

    def call_static_method(self, class_name, method_name, method_params):
        """调用静态方法"""
        payload = {
            "jsonrpc": "2.0",
            "method": "callStaticMethod",
            "params": {
                "className": class_name,
                "methodName": method_name,
                "methodParams": method_params
            },
            "id": self._next_id()
        }
        return self._send_request(payload)

    def call_instance_method(self, instance_id, method_name, method_params):
        """调用实例方法"""
        payload = {
            "jsonrpc": "2.0",
            "method": "callMethod",
            "params": {
                "instanceId": instance_id,
                "methodName": method_name,
                "methodParams": method_params
            },
            "id": self._next_id()
        }
        return self._send_request(payload)
