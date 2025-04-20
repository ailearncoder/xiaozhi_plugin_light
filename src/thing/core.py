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

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

core_log = logging.getLogger('core')

# Import the protocol module
try:
    from . import protocol
except ImportError:
    import protocol  # Fallback for direct execution

# Define property types using an enum for better IDE support and type checking
class PropertyType(Enum):
    NUMBER = "number"
    BOOLEAN = "boolean"
    STRING = "string"
    
    def __str__(self):
        return self.value

class PropertyTypeError(TypeError):
    """Exception raised when a property has an invalid type."""
    pass

class PropertyValueError(ValueError):
    """Exception raised when a property returns an invalid value."""
    pass

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
        if os.path.exists("../install.json"):
            with open("../install.json", "r") as f:
                install_info = json.load(f)
                self.title = install_info.get("title", title)
                self.summary = install_info.get("summary", summary)
                self.name = install_info.get("name", name)
                self.description = install_info.get("description", description)
        if not title or not summary or not name or not description:
            raise ValueError("title, summary, name, and description must be provided")
        self.title = title
        self.summary = summary
        self.name = name
        self.description = description
        self.host = os.getenv("THING_HOST", host)
        self.port = int(os.getenv("THING_PORT", port))
        self.socket = None
        self.connected = False
        self.properties = {}
        self.methods = {}
        self._property_getters = {}
        self._method_handlers = {}
        self._connection_thread = None
        self._enable = False

        # Register decorated properties and methods
        self._register_decorated_items()

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

    def connect(self):
        """Connect to the server and register this thing."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True

            # Create the plugin definition
            plugin = {
                "title": self.title,
                "summary": self.summary,
                "name": self.name,
                "description": self.description,
                "properties": self.properties,
                "methods": self.methods
            }

            # Register with the server
            self.send_json({"action": "register", "type": 1, "plugin": plugin})

            # Start message handling in a separate thread
            self._connection_thread = threading.Thread(target=self._handle_messages)
            self._connection_thread.daemon = True
            self._connection_thread.start()

            return True
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from the server."""
        if self.connected and self.socket:
            self.socket.close()
            self.connected = False

    def send_data(self, data: bytes):
        """Send binary data to the server."""
        if not self.connected:
            return False

        send_data = bytearray()
        send_data.append(1)
        send_data.extend(struct.pack("<I", len(data)))
        send_data.extend(data)
        try:
            self.socket.sendall(send_data)
            return True
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False
            return False

    def send_json(self, data: dict):
        """Send JSON data to the server."""
        return self.send_data(json.dumps(data).encode())

    def _handle_messages(self):
        """Handle incoming messages from the server."""
        parser = protocol.MessageParser(self._on_message, self._on_error)

        while self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    self.connected = False
                    break
                parser.process_data(data)
            except Exception as e:
                print(f"Message handling error: {e}")
                self.connected = False
                break

        print("Connection closed")

    def _on_message(self, message):
        """Handle parsed messages."""
        if isinstance(message, protocol.ParsedMessage.TextMessage):
            try:
                json_data = json.loads(message.text)
                core_log.debug(f"Received message: {json_data}")
                uuid = json_data.get("uuid")
                action = json_data.get("action")

                if action == "getPluginProperty":
                    self._handle_get_property(json_data, uuid)
                elif action == "callPluginMethod":
                    self._handle_call_method(json_data, uuid)
                elif action == "setPluginEnabled":
                    self._handle_set_enabled(json_data, uuid)
            except Exception as e:
                print(f"Message processing error: {e}")
        elif isinstance(message, protocol.ParsedMessage.BinaryMessage):
            print(f"Received binary message of length: {len(message.data)}")

    def _handle_get_property(self, json_data, uuid):
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

    def _handle_call_method(self, json_data, uuid):
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

    def _handle_set_enabled(self, json_data, uuid):
        """Handle set enabled requests."""
        plugin_name = json_data.get("pluginName")
        enabled = json_data.get("enabled")
        if plugin_name == self.name:
            success, msg = self.setEnabled(enabled)
            self.send_json({"uuid": uuid, "success": success, "message": msg})
            if success:
                self._enable = enabled

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

    def get_definition(self):
        return json.dumps({
            "title": self.title,
            "summary": self.summary,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "methods": self.methods,
        })


# Enhanced property decorator with type validation using enums
def property_def(description: str, property_type: PropertyType):
    """
    Decorator for defining a property of a Thing.
    
    Args:
        description: Human-readable description of the property
        property_type: Type of the property, must be a PropertyType enum value
    
    Raises:
        PropertyTypeError: If property_type is not a PropertyType enum value
    """
    if not isinstance(property_type, PropertyType):
        raise PropertyTypeError(f"Property type must be a PropertyType enum value, got {type(property_type).__name__}")
    
    def decorator(func):
        func._thing_property = {
            "description": description,
            "type": property_type
        }
        return func
    return decorator

# Enhanced method decorator with parameter type validation using enums
def method_def(description: str, parameters: Dict[str, Dict[str, Any]]):
    """
    Decorator for defining a method of a Thing.
    
    Args:
        description: Human-readable description of the method
        parameters: Dictionary of parameter specs with their types and descriptions
    
    Raises:
        PropertyTypeError: If any parameter type is invalid
    """
    # Validate parameter types
    for param_name, param_spec in parameters.items():
        if "type" in param_spec and not isinstance(param_spec["type"], PropertyType):
            raise PropertyTypeError(f"Parameter type for {param_name} must be a PropertyType enum value, "
                                    f"got {type(param_spec['type']).__name__}")
    
    def decorator(func):
        func._thing_method = {
            "description": description,
            "parameters": parameters
        }
        return func
    return decorator
