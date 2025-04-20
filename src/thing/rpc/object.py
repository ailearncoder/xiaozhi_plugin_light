from typing import Any
from . import GenericRpcClient
from ..utils.exceptions import RpcError

def static_field(class_name, field_name):
    """生成静态字段参数结构"""
    return {
        "type": "staticField",
        "className": class_name,
        "fieldName": field_name
    }

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
