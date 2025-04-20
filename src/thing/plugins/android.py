try:
    from .. import rpc
except ImportError:
    import rpc  # Fallback for direct execution

class Uri:
    @staticmethod
    def parse(uri_str, rpc_client: rpc.GenericRpcClient = None) -> rpc.RpcObject:
        """解析URI字符串"""
        if rpc_client is None:
            rpc_client = rpc.GenericRpcClient()
        response = rpc_client.call_static_method("android.net.Uri", "parse", [uri_str])
        return rpc.RpcObject(rpc_client, response["instanceId"])

class Intent(rpc.RpcObject):
    # 预定义常用静态字段
    ACTION_VIEW = rpc.static_field("android.content.Intent", "ACTION_VIEW")
    FLAG_ACTIVITY_NEW_TASK = rpc.static_field(
        "android.content.Intent", "FLAG_ACTIVITY_NEW_TASK"
    )

    def __init__(self, action = None, rpc_client: rpc.GenericRpcClient = None):
        self.action = [action] if action else []
        super().__init__(rpc_client)

    def get_instance_id(self):
        if self.instance_id is None:
            self.instance_id = self.create_instance_id(
                "android.content.Intent", self.action
            )
        return self.instance_id

    def set_flags(self, flags):
        """设置标志位"""
        return self.call_method("setFlags", flags)

    def set_data(self, uri):
        """设置数据URI"""
        return self.call_method("setData", uri)


class FlashLight(rpc.RpcObject):
    def __init__(self, rpc_client: rpc.GenericRpcClient = None):
        super().__init__(rpc_client)

    def open(self):
        self.call_method("openFlashLight")

    def close(self):
        self.call_method("closeFlashLight")

    def get_instance_id(self):
        if self.instance_id is None:
            self.instance_id = self.get_static_field_instance_id(
                "cc.axyz.xiaozhi.rpc.model.Message", "Companion"
            )
        return self.instance_id


# 定义你的RPC客户端类
class AndroidDevice(rpc.RpcObject):
    def __init__(self, rpc_client: rpc.GenericRpcClient = None):
        super().__init__(rpc_client, "activityContext")

    def open_flashlight(self):
        flash_light = FlashLight()
        flash_light.open()

    def close_flashlight(self):
        flash_light = FlashLight()
        flash_light.close()

    def start_activity(self, intent: Intent):
        self.call_method("startActivity", intent)


def test_flashlight():
    # 调用方法
    try:
        device = AndroidDevice()
        device.open_flashlight()
        time.sleep(1)
        device.close_flashlight()
    except RpcError as e:
        print(f"操作失败: {e}")


def test_intent():
    device = AndroidDevice()
    # 创建ACTION_VIEW类型的Intent
    intent = Intent(Intent.ACTION_VIEW)
    # 设置标志位
    intent.set_flags(Intent.FLAG_ACTIVITY_NEW_TASK)
    # 创建URI
    uri = Uri.parse("baidumap://map/navi?query=故宫&src=andr.xiaomi.voiceassist")
    # uri = Uri.parse("baidumap://map/place/search?query=海底捞&src=andr.xiaomi.voiceassist")
    # 设置数据URI
    intent.set_data(uri)
    # 启动Activity
    device.start_activity(intent)


if __name__ == "__main__":
    import time
    from rpc import RpcError
    import sys

    if len(sys.argv) != 2:
        print("Usage: python android.py <port>")
        exit(1)
    # test_flashlight()
    test_intent()
    # time.sleep(100)
    print("Done.")
