### 小智Apk插件
支持Apk版本：3.2及以上

### 插件功能
1. 支持开灯关灯指令，操作手机摄像头闪光灯

### 插件使用
1. 打包此目录所有文件为zip压缩包
```
xiaozhi_plugin_light
├── install.json
├── manifest.json
├── readme.md
├── requirements.txt
└── src
    ├── main.py
    └── thing
        ├── __init__.py
        ├── android.py
        ├── core.py
        ├── protocol.py
        └── rpc.py
```
```
zip -r xiaozhi_plugin_light.zip xiaozhi_plugin_light
```
2. 设置 -> 插件列表 -> 插件商店 -> 自定义插件(右上角菜单)
3. 导入zip压缩包

### 插件文件
- install.json 插件安装描述文件
- manifest.json 插件配置描述文件
- requirements.txt 插件Python依赖文件
- src/main.py 插件主程序

**注意：**
install.json 中 
- `id` 字段为插件的唯一标识。
- `name` 字段为插件的调用名称，也需保持唯一。
