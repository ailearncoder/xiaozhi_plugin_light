import socket
import sys
import struct
import json
import threading
import time
from typing import Dict, Any, Callable, Optional, Union, List, Tuple
from enum import Enum, auto
import os
import logging

from ..config import AppConfig

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

core_log = logging.getLogger('core')

# Import the protocol module
try:
    from ..protocol import MessageParser, ParsedMessage, serialize_obj
    from ..utils import NetworkManager, PropertyTypeError, PropertyValueError
    from .decorators import property_def, method_def, PropertyType
except ImportError:
    from protocol import MessageParser, ParsedMessage, serialize_obj # Fallback for direct execution
    from utils import NetworkManager, PropertyTypeError, PropertyValueError
    from decorators import property_def, method_def, PropertyType

class Thing:
    def __init__(self, 
                 title: str = None, summary: str = None,
                 name: str = None, description: str = None,
                 host: str = "127.0.0.1", port: int = 80):
        """
        初始化类实例。

        Args:
            title (str): 标题, 用于在插件列表中显示。
            summary (str): 摘要, 用于在插件列表中显示。
            name (str): 名称, 用于大模型中识别。
            description (str): 描述, 用于大模型中识别。
            host (str, optional): 主机地址，默认为 "127.0.0.1"。
            port (int, optional): 端口号，默认为 80。
        """
        if os.path.exists("install.json"):
            core_log.debug("Found install.json, using it to initialize the class")
            with open("install.json", "r") as f:
                install_info:Dict = json.load(f)
                title = install_info.get("title", title)
                summary = install_info.get("summary", summary)
                name = install_info.get("name", name)
                description = install_info.get("description", description)
        if not all([title, summary, name, description]):
            raise ValueError("title, summary, name, and description must be provided")
        self._config = None
        if os.path.exists('manifest.json'):
            with open('manifest.json', 'r') as f:
                mainfest:Dict = json.load(f)
                self._config = AppConfig.from_obj(mainfest["settings"])
                core_log.debug(f"Loaded config: manifest.json")
        self.title = title
        self.summary = summary
        self.name = name
        self.description = description
        self.host = os.getenv("THING_HOST", host)
        self.port = int(os.getenv("THING_PORT", port))
        self.network = NetworkManager(self.host, self.port)
        self.parser = MessageParser(self._on_message, self._on_error)
        self.properties = {}
        self.methods = {}
        self._property_getters = {}
        self._method_handlers = {}
        self._connection_thread = None
        self._enable = False

        # Register decorated properties and methods
        self._register_decorated_items()

    @property
    def connected(self) -> bool:
        """
        检查是否已连接到服务器。
        Returns:
            bool: 如果已连接则返回 True，否则返回 False。
        """
        return self.network.connected

    def _register_decorated_items(self):
        """Register properties and methods defined using decorators."""
        for attr_name in dir(self.__class__):
            # Skip dunder methods
            if attr_name.startswith('__'):
                continue

            attr = getattr(self.__class__, attr_name)

            # Check for property decorators
            if hasattr(attr, '_thing_property'):
                prop_info = attr._thing_property
                self.properties[attr_name] = {
                    "description": prop_info["description"], 
                    "type": str(prop_info["type"])  # Convert enum to string for JSON
                }

                # Create a getter that validates the return value type
                self._property_getters[attr_name] = (
                    lambda self=self, fn=attr, prop_type=prop_info["type"]: 
                    self._validate_property_value(fn(self), prop_type)
                )

            # Check for method decorators
            elif hasattr(attr, '_thing_method'):
                method_info = attr._thing_method

                # Convert parameter types from enum to string for JSON
                parameters = {}
                for param_name, param_spec in method_info["parameters"].items():
                    param_copy = param_spec.copy()
                    if "type" in param_copy and isinstance(param_copy["type"], PropertyType):
                        param_copy["type"] = str(param_copy["type"])
                    parameters[param_name] = param_copy

                self.methods[attr_name] = {
                    "description": method_info["description"],
                    "parameters": parameters
                }

                # Method handler with parameter validation
                def method_handler(self=self, fn=attr, params_info=method_info["parameters"], **kwargs):
                    # Validate parameters before calling the method
                    for param_name, param_spec in params_info.items():
                        if param_name in kwargs:
                            kwargs[param_name] = self._validate_property_value(
                                kwargs[param_name], 
                                param_spec["type"]
                            )
                    return fn(self, **kwargs)

                self._method_handlers[attr_name] = method_handler

    def _validate_property_value(self, value, prop_type):
        """Validate and convert a property value based on its type."""
        if prop_type == PropertyType.NUMBER:
            if not isinstance(value, (int, float)):
                raise PropertyValueError(f"Expected a number, got {type(value).__name__}")
            return float(value)

        elif prop_type == PropertyType.BOOLEAN:
            if not isinstance(value, bool):
                raise PropertyValueError(f"Expected a boolean, got {type(value).__name__}")
            return bool(value)

        elif prop_type == PropertyType.STRING:
            return str(value)

        else:
            raise PropertyTypeError(f"Unknown property type: {prop_type}")

    def _send_registration(self):
        """Send the registration message to the server."""
        plugin = {
            "title": self.title,
            "summary": self.summary,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "methods": self.methods
        }
        install = None
        with open("install.json") as f:
            install = json.load(f)
        self.send_json({"action": "register", "type": 1, "plugin": plugin, "install": install})

    def _handle_raw_message(self, raw_data: bytes):
        """处理原始网络数据"""
        self.parser.process_data(raw_data)

    def _on_network_error(self, error: Exception):
        """网络错误处理"""
        print(f"Network error: {error}")
        self.network.disconnect()

    def connect(self):
        """Connect to the server and register this thing."""
        if self.network.connect():
            self.network.start_message_handling(
                self._handle_raw_message,
                self._on_network_error
            )
            # 发送注册信息
            self._send_registration()
            return True
        return False

    def disconnect(self):
        """Disconnect from the server."""
        self.network.disconnect()

    def send_json(self, data: dict):
        """Send JSON data to the server."""
        return self.network.send_data(serialize_obj(data))

    def _on_message(self, message):
        """Handle parsed messages."""
        if isinstance(message, ParsedMessage.TextMessage):
            try:
                json_data:Dict = json.loads(message.text)
                core_log.debug(f"Received message: {json_data}")
                uuid = json_data.get("uuid")
                action = json_data.get("action")

                if action == "getPluginProperty":
                    self._handle_get_property(json_data, uuid)
                elif action == "callPluginMethod":
                    self._handle_call_method(json_data, uuid)
                elif action == "setPluginEnabled":
                    self._handle_set_enabled(json_data, uuid)
                elif action == "getPluginConfig":
                    self._handle_get_config(json_data, uuid)
                elif action == "setPluginConfig":
                    self._handle_set_config(json_data, uuid)
                elif action == "savePluginConfig":
                    self._handle_save_config(json_data, uuid)
            except Exception as e:
                print(f"Message processing error: {e}")
        elif isinstance(message, ParsedMessage.BinaryMessage):
            print(f"Received binary message of length: {len(message.data)}")

    def _handle_get_property(self, json_data:Dict, uuid):
        """Handle property get requests."""
        plugin_name = json_data.get("pluginName")
        property_name = json_data.get("propertyName")

        if plugin_name == self.name and property_name in self._property_getters:
            try:
                value = self._property_getters[property_name]()
                self.send_json({
                    "action": "getPluginProperty",
                    "uuid": uuid,
                    "pluginName": plugin_name,
                    "propertyName": property_name,
                    "value": value
                })
            except Exception as e:
                print(f"Error getting property {property_name}: {str(e)}")
                # Return an error response
                self.send_json({
                    "action": "getPluginProperty",
                    "uuid": uuid,
                    "pluginName": plugin_name,
                    "propertyName": property_name,
                    "error": str(e)
                })

    def _handle_call_method(self, json_data:Dict, uuid):
        """Handle method call requests."""
        plugin_name = json_data.get("pluginName")
        method_name = json_data.get("methodName")
        parameters = json_data.get("parameters", {})

        if plugin_name == self.name and method_name in self._method_handlers:
            try:
                result = self._method_handlers[method_name](**parameters)
                self.send_json({
                    "action": "callPluginMethod",
                    "uuid": uuid,
                    "pluginName": plugin_name,
                    "methodName": method_name,
                    "result": result
                })
            except Exception as e:
                print(f"Error calling method {method_name}: {str(e)}")
                # Return an error response
                self.send_json({
                    "action": "callPluginMethod",
                    "uuid": uuid,
                    "pluginName": plugin_name,
                    "methodName": method_name,
                    "error": str(e)
                })
                core_log.error(f"Error calling method {method_name}", exc_info=True)

    def _handle_set_enabled(self, json_data:Dict, uuid):
        """Handle set enabled requests."""
        plugin_name = json_data.get("pluginName")
        enabled = json_data.get("enabled")
        if plugin_name == self.name:
            success, msg = self.setEnabled(enabled)
            self.send_json({"uuid": uuid, "success": success, "message": msg})
            if success:
                self._enable = enabled

    def _handle_get_config(self, json_data:Dict, uuid):
        """Handle get config requests."""
        plugin_name = json_data.get("pluginName")
        if plugin_name == self.name:
            self.send_json({
                "uuid": uuid,
                "configJson": self.getConfig()
            })

    def _handle_set_config(self, json_data:Dict, uuid):
        """Handle set config requests."""
        plugin_name = json_data.get("pluginName")
        if plugin_name == self.name:
            config_json = json_data.get("configJson")
            self.send_json({
                "uuid": uuid,
                "success": self.setConfig(config_json)
            })

    def _handle_save_config(self, json_data:Dict, uuid):
        """Handle save config requests."""
        plugin_name = json_data.get("pluginName")
        if plugin_name == self.name:
            if self._config:
                with open('manifest.json') as f:
                    mainfest:Dict = json.load(f)
                mainfest["settings"] = self._config.to_json()
                with open('manifest.json', 'w') as f:
                    json.dump(mainfest, f, ensure_ascii=False, indent=4)
            self.send_json({
                "uuid": uuid,
                "success": True
            })

    def _on_error(self, error):
        """Handle parser errors."""
        print(f"Parser error: {error}")

    def setEnabled(self, enabled) -> Tuple[bool, str]:
        """
        设置启用状态，由手机发起

        Args:
            enabled (bool): 启用状态, True 表示启用, False 表示禁用。

        Returns:
            Tuple[bool, str]: 一个元组，包含操作结果和提示信息。
                - bool: 操作结果, True 表示操作成功, False 表示操作失败。
                - str: 提示信息，用于描述操作结果。

        """
        return True, "ok"

    def getConfig(self) -> Dict:
        """
        获取配置信息，由手机发起
        Returns:
            Dict: 配置信息字典。
        """
        if self._config:
            return self._config.to_json()
        return {}

    def setConfig(self, config_json:Dict) -> bool:
        """
        设置配置信息，由手机发起
        Args:
            config_json (Dict): 配置信息字典。
        Returns:
            bool: 操作结果, True 表示操作成功, False 表示操作失败。
        """
        key = config_json.get("key")
        value = config_json.get("value")
        if not key or not value:
            core_log.debug(f"Invalid config: {config_json}")
            return False
        if hasattr(self, f"config_{key}") and callable(getattr(self, f"config_{key}")):
            if getattr(self, f"config_{key}")(value):
                self._config.handle_update(key, value)
                return True
        core_log.debug(f"cant find config_{key} function")
        return False

    def get_definition(self):
        return json.dumps({
            "title": self.title,
            "summary": self.summary,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "methods": self.methods,
        }, ensure_ascii = False, indent=4)
