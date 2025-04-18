try:
    from . import rpc
except ImportError:
    import rpc  # Fallback for direct execution

from dataclasses import dataclass
from typing import List, Dict
import json

@dataclass
class Info:
    live2dShow: bool
    modelDirs: List[str]
    currentModelName: str
    allMotions: Dict[str, List[int]]
    allExpressions: List[str]

    @staticmethod
    def from_json(json_str: str) -> 'Info':
        """Load Info object from a JSON string."""
        data = json.loads(json_str)
        return Info(
            live2dShow=data['live2dShow'],
            modelDirs=data['modelDirs'],
            currentModelName=data['currentModelName'],
            allMotions={k: v for k, v in data['allMotions'].items()},
            allExpressions=data['allExpressions']
        )

class Param(Dict):
    def __init__(self, id: str, value: float = 0):
        super().__init__({'id': id, 'value': value})

class Live2D(rpc.RpcObject):
    MOTION_PRIORITY_NONE = 0
    MOTION_PRIORITY_IDLE = 1
    MOTION_PRIORITY_NORMAL = 2
    MOTION_PRIORITY_FORCE = 3
    def __init__(self, rpc_client: rpc.GenericRpcClient = None):
        super().__init__(rpc_client)

    def info(self) -> Info:
        return Info.from_json(self.call_method("getInfo"))
    
    def refresh(self) -> Info:
        return Info.from_json(self.call_method("refreshModel"))
    
    def switch_model(self, name: str):
        self.call_method("switchModel", name)

    def start_motion(self, group: str, number: int, priority: int = MOTION_PRIORITY_NORMAL) -> int:
        return self.call_method("startMotion", group, number, priority)

    def start_expression(self, expression_id: str) -> int:
        return self.call_method("startExpression", expression_id)
    
    def add_custom_update_params(self, params: List[Param]):
        self.call_method("addCustomUpdateParam", json.dumps(params))

    def remove_custom_update_param(self, params: List[Param]):
        self.call_method("removeCustomUpdateParam", json.dumps(params))
    
    def get_instance_id(self):
        if self.instance_id is None:
            self.instance_id = self.get_static_field_instance_id(
                "cc.axyz.xiaozhi.rpc.model.Live2D", "Companion"
            )
        return self.instance_id


if __name__ == '__main__':
    import time
    live_2d = Live2D()
    print(live_2d.info())
    print(live_2d.refresh())
    live_2d.switch_model('Hiyori')
    print(live_2d.start_motion('TapBody', 0))
    print(live_2d.start_expression('Angry'))
    live_2d.add_custom_update_params([Param('ParamAngleX', -60)])
    time.sleep(1)
    live_2d.add_custom_update_params([Param('ParamAngleX', 60)])
    time.sleep(1)
    live_2d.add_custom_update_params([Param('ParamAngleY', -60)])
    time.sleep(1)
    live_2d.add_custom_update_params([Param('ParamAngleY', 60)])
    time.sleep(1)
    live_2d.add_custom_update_params([Param('ParamAngleZ', -60)])
    time.sleep(1)
    live_2d.add_custom_update_params([Param('ParamAngleZ', 60)])
    time.sleep(1)
    live_2d.remove_custom_update_param([Param('ParamAngleX'), Param('ParamAngleY'), Param('ParamAngleZ')])
