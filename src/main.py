from ast import Dict
from thing.core import Thing, property_def, method_def, PropertyType
from thing.plugins import AndroidDevice
from thing import AppConfig
from typing import Tuple
import time
import json
import sys
import os

class Light(Thing):
    def __init__(self):
        # Initialize internal state
        self._brightness = 100
        self._power = False
        self._online = True
        self._device = AndroidDevice()
        super().__init__()
    
    @property_def("Current brightness", PropertyType.NUMBER)
    def brightness(self):
        print(f"Getting brightness {self._brightness}")
        return self._brightness
    
    @property_def("Whether the light is on", PropertyType.BOOLEAN)
    def power(self):
        print(f"Getting power {self._power}")
        return self._power
    
    @property_def("Whether the device is online", PropertyType.BOOLEAN)
    def online(self):
        print(f"Getting online {self._online}")
        return self._online
    
    @method_def(
        "Set the brightness",
        {
            "brightness": {
                "description": "An integer between 0 and 100", 
                "type": PropertyType.NUMBER
            }
        }
    )
    def SetBrightness(self, brightness):
        if not 0 <= brightness <= 100:
            raise ValueError("Brightness must be between 0 and 100")
            
        self._brightness = brightness
        print(f"Setting brightness to {brightness}")
        return True
    
    @method_def(
        "Set whether the light is on or off",
        {
            "power": {
                "description": "True for on, False for off", 
                "type": PropertyType.BOOLEAN
            }
        }
    )
    def SetPower(self, power):
        self._power = power
        if self._power:
            self._device.open_flashlight()
        else:
            self._device.close_flashlight()
        print(f"Setting power to {power}")

    def setEnabled(self, enabled) -> Tuple[bool, str]:
        print(f"Setting enabled to {enabled}")
        return super().setEnabled(enabled)

    def config_power(self, power):
        print(f"Configuring power to {power}")
        return True

    def config_brightness(self, brightness):
        print(f"Configuring brightness to {brightness}")
        return True

# Usage
if __name__ == "__main__":
    light = Light()
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        # 这个不能去掉，否则无法识别插件信息
        with open("info.json", "w") as f:
            f.write(light.get_definition())
        exit(0)
    light.connect()
    # Keep the main thread running
    try:
        while light.connected:
            time.sleep(1)
    except KeyboardInterrupt:
        light.disconnect()
