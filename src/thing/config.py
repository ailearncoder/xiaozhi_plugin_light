from typing import List, Dict, Union, Callable, Any, Type
import json
import inspect

class ConfigItem:
    """配置项基类"""
    def __init__(self, 
                 type: str,
                 key: str,
                 title: str,
                 required: bool = False,
                 default: Union[str, int, bool, List[int]] = None):
        self.type = type
        self.key = key
        self.title = title
        self.required = required
        self.default = default

    def to_dict(self) -> Dict:
        """转换为字典结构，自动包含子类所有属性"""
        base = {
            "type": self.type,
            "key": self.key,
            "title": self.title,
            "required": self.required,
            "default": self.default
        }
        instance_dict = vars(self).copy()
        for key in base:
            instance_dict.pop(key, None)
        return {k: v for k, v in {**base, **instance_dict}.items() if v is not None}

class TextItem(ConfigItem):
    """文本类型配置项"""
    def __init__(self, key, title, hint=None, pattern=None, **kwargs):
        super().__init__("text", key, title, **kwargs)
        self.hint = hint
        self.pattern = pattern

    @classmethod
    def validate_data(cls, data: Dict):
        required = {'type', 'key', 'title'}
        allowed = {'type', 'key', 'title', 'hint', 'pattern', 'required', 'default'}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"TextItem missing required fields: {missing}")
        if data['type'] != 'text':
            raise ValueError("TextItem type must be 'text'")
        unknown = data.keys() - allowed
        if unknown:
            raise ValueError(f"TextItem unknown fields: {unknown}")
        if 'hint' in data and not isinstance(data['hint'], str):
            raise ValueError("TextItem hint must be string")
        if 'pattern' in data and not isinstance(data['pattern'], str):
            raise ValueError("TextItem pattern must be string")
        if 'required' in data and not isinstance(data['required'], bool):
            raise ValueError("TextItem required must be boolean")
        if 'default' in data and data['default'] is not None and not isinstance(data['default'], str):
            raise ValueError("TextItem default must be string or null")

    @classmethod
    def from_dict(cls, data: Dict) -> 'TextItem':
        cls.validate_data(data)
        return cls(
            key=data['key'],
            title=data['title'],
            hint=data.get('hint'),
            pattern=data.get('pattern'),
            required=data.get('required', False),
            default=data.get('default')
        )

class NumberItem(ConfigItem):
    """数字类型配置项"""
    def __init__(self, key, title, min: Union[int, float], max: Union[int, float], **kwargs):
        super().__init__("number", key, title, **kwargs)
        self.min = min
        self.max = max

    @classmethod
    def validate_data(cls, data: Dict):
        required = {'type', 'key', 'title', 'min', 'max'}
        allowed = {'type', 'key', 'title', 'min', 'max', 'required', 'default'}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"NumberItem missing required fields: {missing}")
        if data['type'] != 'number':
            raise ValueError("NumberItem type must be 'number'")
        unknown = data.keys() - allowed
        if unknown:
            raise ValueError(f"NumberItem unknown fields: {unknown}")
        if not isinstance(data['min'], (int, float)):
            raise ValueError("NumberItem min must be number")
        if not isinstance(data['max'], (int, float)):
            raise ValueError("NumberItem max must be number")
        if data['min'] >= data['max']:
            raise ValueError("NumberItem min must be less than max")
        if 'required' in data and not isinstance(data['required'], bool):
            raise ValueError("NumberItem required must be boolean")
        if 'default' in data and data['default'] is not None and not isinstance(data['default'], (int, float)):
            raise ValueError("NumberItem default must be number or null")

    @classmethod
    def from_dict(cls, data: Dict) -> 'NumberItem':
        cls.validate_data(data)
        return cls(
            key=data['key'],
            title=data['title'],
            min=data['min'],
            max=data['max'],
            required=data.get('required', False),
            default=data.get('default')
        )

class SwitchItem(ConfigItem):
    """开关类型配置项"""
    def __init__(self, key, title, **kwargs):
        super().__init__("switch", key, title, **kwargs)

    @classmethod
    def validate_data(cls, data: Dict):
        required = {'type', 'key', 'title'}
        allowed = {'type', 'key', 'title', 'required', 'default'}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"SwitchItem missing required fields: {missing}")
        if data['type'] != 'switch':
            raise ValueError("SwitchItem type must be 'switch'")
        unknown = data.keys() - allowed
        if unknown:
            raise ValueError(f"SwitchItem unknown fields: {unknown}")
        if 'required' in data and not isinstance(data['required'], bool):
            raise ValueError("SwitchItem required must be boolean")
        if 'default' in data and not isinstance(data['default'], bool):
            raise ValueError("SwitchItem default must be boolean")

    @classmethod
    def from_dict(cls, data: Dict) -> 'SwitchItem':
        cls.validate_data(data)
        return cls(
            key=data['key'],
            title=data['title'],
            required=data.get('required', False),
            default=data.get('default')
        )

class SingleChoiceItem(ConfigItem):
    """单选类型配置项"""
    def __init__(self, key, title, options: List[str], **kwargs):
        super().__init__("single_choice", key, title, **kwargs)
        self.options = options

    @classmethod
    def validate_data(cls, data: Dict):
        required = {'type', 'key', 'title', 'options'}
        allowed = {'type', 'key', 'title', 'options', 'required', 'default'}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"SingleChoiceItem missing required fields: {missing}")
        if data['type'] != 'single_choice':
            raise ValueError("SingleChoiceItem type must be 'single_choice'")
        unknown = data.keys() - allowed
        if unknown:
            raise ValueError(f"SingleChoiceItem unknown fields: {unknown}")
        if not isinstance(data['options'], list) or not all(isinstance(opt, str) for opt in data['options']):
            raise ValueError("SingleChoiceItem options must be list of strings")
        if 'default' in data and data['default'] is not None:
            if not isinstance(data['default'], int) or data['default'] < 0 or data['default'] >= len(data['options']):
                raise ValueError("SingleChoiceItem default must be valid index")

    @classmethod
    def from_dict(cls, data: Dict) -> 'SingleChoiceItem':
        cls.validate_data(data)
        return cls(
            key=data['key'],
            title=data['title'],
            options=data['options'],
            required=data.get('required', False),
            default=data.get('default')
        )

class MultiChoiceItem(SingleChoiceItem):
    """多选类型配置项"""
    def __init__(self, key, title, options: List[str], **kwargs):
        super().__init__(key, title, options, **kwargs)
        self.type = "multi_choice"

    @classmethod
    def validate_data(cls, data: Dict):
        required = {'type', 'key', 'title', 'options'}
        allowed = {'type', 'key', 'title', 'options', 'required', 'default'}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"MultiChoiceItem missing required fields: {missing}")
        if data['type'] != 'multi_choice':
            raise ValueError("MultiChoiceItem type must be 'multi_choice'")
        unknown = data.keys() - allowed
        if unknown:
            raise ValueError(f"MultiChoiceItem unknown fields: {unknown}")
        if not isinstance(data['options'], list) or not all(isinstance(opt, str) for opt in data['options']):
            raise ValueError("MultiChoiceItem options must be list of strings")
        if 'default' in data and data['default'] is not None:
            if (not isinstance(data['default'], list) or 
                not all(isinstance(idx, int) for idx in data['default']) or
                any(idx < 0 or idx >= len(data['options']) for idx in data['default'])):
                raise ValueError("MultiChoiceItem default must be list of valid indices")

    @classmethod
    def from_dict(cls, data: Dict) -> 'MultiChoiceItem':
        cls.validate_data(data)
        return cls(
            key=data['key'],
            title=data['title'],
            options=data['options'],
            required=data.get('required', False),
            default=data.get('default')
        )

class SliderItem(NumberItem):
    """滑动条类型配置项"""
    def __init__(self, key, title, min: int, max: int, step: int = 1, **kwargs):
        super().__init__(key, title, min, max, **kwargs)
        self.type = "slider"
        self.step = step

    @classmethod
    def validate_data(cls, data: Dict):
        required = {'type', 'key', 'title', 'min', 'max'}
        allowed = {'type', 'key', 'title', 'min', 'max', 'step', 'required', 'default'}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"SliderItem missing required fields: {missing}")
        if data['type'] != 'slider':
            raise ValueError("SliderItem type must be 'slider'")
        unknown = data.keys() - allowed
        if unknown:
            raise ValueError(f"SliderItem unknown fields: {unknown}")
        if not isinstance(data['min'], int):
            raise ValueError("SliderItem min must be integer")
        if not isinstance(data['max'], int):
            raise ValueError("SliderItem max must be integer")
        if data['min'] >= data['max']:
            raise ValueError("SliderItem min must be less than max")
        step = data.get('step', 1)
        if not isinstance(step, int) or step <= 0:
            raise ValueError("SliderItem step must be positive integer")
        if 'default' in data and data['default'] is not None and not isinstance(data['default'], int):
            raise ValueError("SliderItem default must be integer or null")

    @classmethod
    def from_dict(cls, data: Dict) -> 'SliderItem':
        cls.validate_data(data)
        return cls(
            key=data['key'],
            title=data['title'],
            min=data['min'],
            max=data['max'],
            step=data.get('step', 1),
            required=data.get('required', False),
            default=data.get('default')
        )

class ConfigSection:
    """配置区块"""
    def __init__(self, title: str):
        self.title = title
        self.items: List[ConfigItem] = []
    
    def add_item(self, item: ConfigItem):
        self.items.append(item)
        return self

class AppConfig:
    """应用配置生成器（含回调机制）"""
    type_to_class: Dict[str, Type[ConfigItem]] = {
        'text': TextItem,
        'number': NumberItem,
        'switch': SwitchItem,
        'single_choice': SingleChoiceItem,
        'multi_choice': MultiChoiceItem,
        'slider': SliderItem,
    }

    def __init__(self, title: str = "应用配置", version: int = 1):
        self.title = title
        self.version = version
        self.sections: List[ConfigSection] = []
        self._callbacks: Dict[str, List[Callable[[Any], None]]] = {}
        self._items_by_key: Dict[str, ConfigItem] = {}

    def add_section(self, section: ConfigSection):
        for item in section.items:
            if item.key in self._items_by_key:
                raise ValueError(f"Duplicate key: {item.key}")
            self._items_by_key[item.key] = item
        self.sections.append(section)
        return self
    
    def register_callback(self, key: str, callback: Callable[[Any], None]):
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)
        return self
    
    def handle_update(self, key: str, value: Any):
        if key not in self._items_by_key:
            raise KeyError(f"Unknown config key: {key}")
        item = self._items_by_key[key]
        item.default = value
        if key in self._callbacks:
            for callback in self._callbacks[key]:
                callback(value)
    
    def to_json(self) -> str:
        config = {
            "title": self.title,
            "version": self.version,
            "sections": [
                {
                    "title": section.title,
                    "items": [item.to_dict() for item in section.items]
                } 
                for section in self.sections
            ]
        }
        return config

    def to_json_str(self, indent=2) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> 'AppConfig':
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON format") from e
        return AppConfig.from_obj(data)

    @classmethod
    def from_obj(cls, data: Dict) -> 'AppConfig':
        required_top = {'title', 'version', 'sections'}
        missing_top = required_top - data.keys()
        if missing_top:
            raise ValueError(f"Missing top-level fields: {missing_top}")
        
        app_config = cls(title=data['title'], version=data['version'])
        for section_data in data['sections']:
            if 'title' not in section_data:
                raise ValueError("Section missing title")
            section = ConfigSection(title=section_data['title'])
            
            for item_data in section_data.get('items', []):
                if 'type' not in item_data:
                    raise ValueError("Item missing 'type' field")
                item_type = item_data['type']
                item_class = cls.type_to_class.get(item_type)
                if not item_class:
                    raise ValueError(f"Unknown item type: {item_type}")
                try:
                    item = item_class.from_dict(item_data)
                except ValueError as e:
                    raise ValueError(f"Invalid item data for key {item_data.get('key')}: {e}") from e
                section.add_item(item)
            
            app_config.add_section(section)
        
        return app_config

# 示例用法
if __name__ == "__main__":
    # 测试JSON解析
    sample_json = """
    {
        "title": "应用配置",
        "version": 1,
        "sections": [
            {
                "title": "基本设置",
                "items": [
                    {
                        "type": "text",
                        "key": "username",
                        "title": "用户名",
                        "hint": "请输入3-16位字母数字",
                        "required": true,
                        "pattern": "^[a-zA-Z0-9]{3,16}$",
                        "default": "user123"
                    },
                    {
                        "type": "number",
                        "key": "age",
                        "title": "年龄",
                        "min": 1,
                        "max": 150,
                        "default": 25
                    },
                    {
                        "type": "switch",
                        "key": "dark_mode",
                        "title": "夜间模式",
                        "default": true
                    }
                ]
            },
            {
                "title": "高级设置",
                "items": [
                    {
                        "type": "single_choice",
                        "key": "resolution",
                        "title": "分辨率",
                        "options": ["720p", "1080p", "2K", "4K"],
                        "default": 1
                    },
                    {
                        "type": "multi_choice",
                        "key": "languages",
                        "title": "支持语言",
                        "options": ["中文", "English", "日本語", "Español"],
                        "default": [0, 1]
                    },
                    {
                        "type": "slider",
                        "key": "brightness",
                        "title": "屏幕亮度",
                        "min": 0,
                        "max": 100,
                        "step": 5,
                        "default": 70
                    }
                ]
            }
        ]
    }
    """
    
    # 从JSON解析配置
    parsed_config = AppConfig.from_json(sample_json)
    print("JSON解析成功，生成的配置:")
    print(parsed_config.to_json())
    
    # 测试错误JSON
    invalid_json = """
    {
        "title": "错误配置",
        "version": 1,
        "sections": [
            {
                "title": "错误项",
                "items": [
                    {
                        "type": "text",
                        "key": "test",
                        "title": "测试文本",
                        "min": 10
                    }
                ]
            }
        ]
    }
    """
    try:
        AppConfig.from_json(invalid_json)
    except ValueError as e:
        print("\n捕获预期错误:", e)
