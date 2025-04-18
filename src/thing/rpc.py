import socket
import json
import uuid
import threading
import logging
import os

logging.basicConfig(level=logging.getLevelName(os.getenv("LOG_LEVEL", 'ERROR')),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
rpc_logger = logging.getLogger('rpc')

class RpcClientMeta(type):
    """元类用于自动注册RPC方法"""
    def __new__(cls, name, bases, attrs):
        rpc_methods = {}
        for attr_name, attr_value in attrs.items():
            if hasattr(attr_value, '_rpc_info'):
                rpc_methods[attr_name] = attr_value._rpc_info
        attrs['_rpc_methods'] = rpc_methods
        return super().__new__(cls, name, bases, attrs)

class GenericRpcClient(metaclass=RpcClientMeta):
    def __init__(self, endpoint = '127.0.0.1:80', timeout=5):
        self.host, port = endpoint.split(":")
        self.host = os.getenv("RPC_HOST", self.host)
        port = os.getenv("RPC_PORT", port)
        self.port = int(port)
        self.timeout = timeout
        self.instance_cache = {}
        self.request_counter = 0
        self._lock = threading.Lock()
        self._socket = None
        self._buffer = b""
        self._connected = False

    def __del__(self):
        self.close()

    def _next_id(self):
        self.request_counter += 1
        return f"py_{self.request_counter}_{uuid.uuid4().hex[:6]}"

    def _ensure_connection(self):
        """建立并维护TCP连接"""
        if not self._connected:
            try:
                rpc_logger.debug("Connecting to RPC server at %s:%s", self.host, self.port)
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(self.timeout)
                self._socket.connect((self.host, self.port))
                self._connected = True
                rpc_logger.debug("Connected to RPC server at %s:%s", self.host, self.port)
            except socket.error as e:
                raise RpcError(f"Connection failed: {str(e)}", code=-32001)

    def _reconnect(self):
        """重新建立连接"""
        self.close()
        self._ensure_connection()

    def close(self):
        """关闭连接"""
        if self._socket:
            try:
                rpc_logger.debug("Closing connection to RPC server at %s:%s", self.host, self.port)
                self._socket.close()
            except:
                pass
            self._socket = None
        self._connected = False
        self._buffer = b""

    def _send_all(self, data):
        """带重试的完整数据发送"""
        try:
            self._socket.sendall(data)
        except socket.error:
            self._reconnect()
            self._socket.sendall(data)

    def _recv_until(self):
        """接收数据直到遇到换行符"""
        while b"\n" not in self._buffer:
            try:
                chunk = self._socket.recv(4096)
                if not chunk:
                    raise RpcError("Connection closed by server")
                self._buffer += chunk
            except socket.timeout:
                raise RpcError("Request timed out")
            except socket.error as e:
                raise RpcError(f"Socket error: {str(e)}")

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
                    self._recv_until()
                    line, self._buffer = self._buffer.split(b"\n", 1)
                    rpc_logger.debug("Received response: %s", line)
                    response = json.loads(line.decode())

                    if "id" not in response:
                        continue  # 跳过通知类型的消息
                    if response["id"] == request_id:
                        if "error" in response:
                            error = response["error"]
                            raise RpcError(error.get("message"), code=error.get("code"))
                        return response.get("result")
                    
            except json.JSONDecodeError as e:
                raise RpcError(f"Invalid JSON response: {str(e)}", code=-32002)
            except Exception as e:
                self.close()
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

class RpcObject:
    """
    RPC对象基类，用于封装具有instanceId的远程对象
    """
    def __init__(self, rpc_client: GenericRpcClient = None, instance_id = None):
        self.rpc_client = GenericRpcClient() if rpc_client is None else rpc_client
        self.instance_id = instance_id
        self._auto_close = rpc_client is None

    def __del__(self):
        if self._auto_close and self.rpc_client is not None:
            self.rpc_client.close()

    def get_static_field_instance_id(self, class_name: str, field_name: str):
        """获取静态字段值"""
        if self.rpc_client is None:
            raise RpcError(f"RPC client not set")
        return self.rpc_client.get_static_field(class_name, field_name)["instanceId"]
    
    def create_instance_id(self, class_name, constructor_params = []):
        """创建新实例"""
        if self.rpc_client is None:
            raise RpcError(f"RPC client not set")
        return self.rpc_client.create_instance(class_name, constructor_params)["instanceId"]

    def call_method(self, method_name, *params):
        """调用实例方法"""
        instance_id = self.get_instance_id()
        if self.rpc_client is None or instance_id is None:
            raise RpcError(f"RPC client or instance ID not set {self.rpc_client} {instance_id}")
        processed_params = []
        for param in params:
            if isinstance(param, RpcObject):
                if param.instance_id is None:
                    raise RpcError(f"Instance ID of parameter object is not set")
                processed_params.append({
                    "type": "object",
                    "instanceId": param.instance_id
                })
            else:
                processed_params.append(param)
                
        return self.rpc_client.call_instance_method(
            instance_id,
            method_name,
            processed_params
        )

    def get_instance_id(self):
        return self.instance_id

def static_field(class_name, field_name):
    """生成静态字段参数结构"""
    return {
        "type": "staticField",
        "className": class_name,
        "fieldName": field_name
    }

class RpcError(Exception):
    def __init__(self, message, code=-32000):
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self):
        return f"[{self.code}] {self.message}"
