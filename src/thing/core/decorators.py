from typing import Callable, Any, Dict
from enum import Enum
from ..utils.exceptions import PropertyTypeError

class PropertyType(Enum):
    NUMBER = 'number'
    BOOLEAN = 'boolean'
    STRING = 'string'
    def __str__(self):
        return self.value

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
