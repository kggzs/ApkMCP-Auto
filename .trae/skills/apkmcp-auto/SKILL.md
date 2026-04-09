---
name: "apkmcp-auto"
description: "Android APK 逆向工程自动化工具套件 Skill。整合 JADX、APKTool、ADB、签名工具、静态分析器和文件对比工具。当用户需要进行 APK 反编译、代码分析、设备调试、APK 签名或文件对比时调用此 Skill。"
---

# ApkMCP-Auto Android 逆向工程工具套件

## 项目概述

ApkMCP-Auto 是一个基于 **MCP (Model Context Protocol)** 的 Android APK 自动化逆向工程工具套件，通过 AI 助手与专业反编译工具的无缝集成，实现智能化的 APK 分析与修改。

## 新目录结构

项目已重新整理为统一的 `tools/` 目录结构，便于 AI 统一调度：

```
ApkMCP-Auto/
├── tools/                          # 统一工具目录
│   ├── __init__.py                 # 统一调度模块
│   ├── jadx/                       # JADX 工具
│   │   ├── server.jar              # JADX MCP Server (Java)
│   │   ├── server.py               # JADX MCP Server (Python 备选)
│   │   └── requirements.txt
│   ├── apktool/                    # APKTool 工具
│   │   ├── server.py               # APKTool MCP Server
│   │   └── requirements.txt
│   ├── adb/                        # ADB 工具
│   │   ├── server.py               # ADB MCP Server
│   │   └── requirements.txt
│   ├── sign-tools/                 # 签名工具
│   │   ├── server.py               # Sign Tools MCP Server
│   │   └── requirements.txt
│   ├── static-analyzer/            # 静态分析器
│   │   ├── server.py               # Static Analyzer
│   │   └── requirements.txt
│   ├── diff/                       # 文件对比工具
│   │   ├── server.py               # Diff Tool
│   │   └── requirements.txt
│   ├── frida/                      # Frida 动态插桩
│   │   ├── server.py               # Frida MCP Server
│   │   └── requirements.txt
│   ├── bin/                        # 二进制工具目录
│   │   ├── adb.exe                 # ADB 可执行文件
│   │   ├── apktool.jar             # APKTool JAR
│   │   ├── apktool.bat             # APKTool 启动脚本
│   │   ├── jadx-gui.exe            # JADX GUI
│   │   ├── jre/                    # Java 运行时
│   │   └── ...
│   └── workspace/                  # 工作空间
│       ├── apktool/                # APKTool 工作目录
│       └── sign-tools/             # 签名工具工作目录
├── apkmcp.py                       # 统一命令行工具
├── .trae/
│   └── config.json                 # MCP 配置（自动生成）
└── README.md
```

## 统一调度方式

### 1. 命令行工具

使用 `apkmcp.py` 统一命令行工具管理所有工具：

```bash
# 查看工具状态
python apkmcp.py status

# 列出所有工具
python apkmcp.py list

# 生成 MCP 配置
python apkmcp.py config

# 安装所有依赖
python apkmcp.py install

# 安装指定工具依赖
python apkmcp.py install apktool

# 启动指定工具
python apkmcp.py start apktool
```

### 2. Python API 调用

在 Python 代码中使用统一调度模块：

```python
from tools import ApkMCPManager, ToolType

# 创建管理器
manager = ApkMCPManager()

# 列出所有工具
tools = manager.list_tools()
for tool in tools:
    print(f"{tool.tool_type.value}: {tool.description}")

# 获取指定工具配置
jadx_config = manager.get_tool(ToolType.JADX)
print(f"JADX 路径: {jadx_config.server_path}")

# 安装依赖
manager.install_dependencies(ToolType.APKTOOL)

# 生成 MCP 配置
config = manager.get_mcp_config()
manager.save_mcp_config(".trae/config.json")
```

### 3. 便捷函数

```python
from tools import get_manager, get_tool_config, list_all_tools

# 获取默认管理器
manager = get_manager()

# 通过名称获取工具配置
tool = get_tool_config("apktool")

# 列出所有工具
tools = list_all_tools()
```

## 核心组件

### 1. JADX MCP Server
- **路径**: `tools/jadx/`
- **功能**: 与 JADX-GUI 集成，提供实时反编译分析
- **主要工具**:
  - `fetch_current_class` - 获取当前选中的类
  - `get_class_source` - 获取指定类源代码
  - `search_classes_by_keyword` - 按关键词搜索类
  - `get_android_manifest` - 获取 AndroidManifest.xml
  - `rename_class/method/field/variable` - 代码重构
  - `get_xrefs_to_class/method` - 交叉引用分析
  - `debug_get_stack_frames/variables` - 调试器集成

### 2. APKTool MCP Server
- **路径**: `tools/apktool/`
- **功能**: APK 解码/编码与 Smali 修改
- **主要工具**:
  - `decode_apk` - 解码 APK 文件
  - `build_apk` - 从项目构建 APK
  - `get_smali_file` / `modify_smali_file` - Smali 代码操作
  - `list_resources` / `modify_resource_file` - 资源管理
  - `search_in_files` - 文件内容搜索
  - `analyze_project_structure` - 项目结构分析

### 3. ADB MCP Server
- **路径**: `tools/adb/`
- **功能**: Android 设备管理和调试
- **主要工具**:
  - `list_devices` / `get_device_info` - 设备管理
  - `install_apk` / `uninstall_package` - 应用安装/卸载
  - `get_logcat` / `clear_logcat` - 日志捕获
  - `execute_shell` - Shell 命令执行
  - `push_file` / `pull_file` - 文件传输
  - `screenshot` - 屏幕截图
  - `start_activity` / `force_stop_package` - 应用控制

### 4. Sign Tools MCP Server
- **路径**: `tools/sign-tools/`
- **功能**: APK 签名和密钥管理
- **主要工具**:
  - `generate_keystore` - 生成密钥库
  - `list_keystores` / `get_keystore_info` - 密钥管理
  - `sign_apk` - APK 签名（V1/V2/V3）
  - `verify_signature` - 签名验证
  - `zipalign_apk` - 对齐优化

### 5. Static Analyzer
- **路径**: `tools/static-analyzer/`
- **功能**: 静态分析增强
- **主要工具**:
  - `analyze_permissions` - 权限分析（含危险权限识别）
  - `extract_strings` - 字符串资源提取
  - `extract_endpoints` - URL/IP/API 端点提取
  - `identify_sdks` - 第三方 SDK 识别（广告、统计、社交、支付等）
  - `full_analysis` - 完整静态分析

### 6. Diff Tool
- **路径**: `tools/diff/`
- **功能**: 文件对比
- **主要工具**:
  - `compare_apks` - APK 文件对比
  - `compare_smali` - Smali 文件行级对比
  - `compare_resources` - 资源目录对比
  - `compare_text_files` - 通用文本文件对比

### 7. Frida MCP Server
- **路径**: `tools/frida/`
- **功能**: 动态插桩分析
- **主要工具**:
  - `list_processes` / `attach_process` / `spawn_process` - 进程管理
  - `inject_script` - JavaScript 脚本注入
  - `hook_function` - 函数 Hook
  - `intercept_network` - 网络请求拦截
  - `scan_memory` / `read_memory` / `write_memory` - 内存操作
  - `enumerate_modules` / `enumerate_exports` - 模块枚举

## 典型工作流程

### APK 分析流程
```python
from tools import ApkMCPManager, ToolType

manager = ApkMCPManager()

# 1. 使用 APKTool 解码 APK
apktool = manager.get_tool(ToolType.APKTOOL)
# → 调用 decode_apk(apk_path)

# 2. 使用 Static Analyzer 进行静态分析
analyzer = manager.get_tool(ToolType.STATIC_ANALYZER)
# → 调用 full_analysis(project_dir)
# → 调用 analyze_permissions(project_dir)
# → 调用 identify_sdks(project_dir)

# 3. 使用 JADX 分析代码
jadx = manager.get_tool(ToolType.JADX)
# → 调用 get_android_manifest()
# → 调用 search_classes_by_keyword("关键词")
# → 调用 get_class_source(class_name)

# 4. 使用 Diff Tool 对比修改（如有需要）
diff = manager.get_tool(ToolType.DIFF)
# → 调用 compare_apks(original_apk, modified_apk)
```

### APK 修改与重打包流程
```python
from tools import ApkMCPManager, ToolType

manager = ApkMCPManager()

# 1. 解码 APK
apktool = manager.get_tool(ToolType.APKTOOL)
# → decode_apk(apk_path)

# 2. 修改 Smali 代码
# → get_smali_file(class_name)
# → modify_smali_file(class_name, new_content)

# 3. 修改资源文件
# → get_resource_file(resource_type, resource_name)
# → modify_resource_file(resource_type, resource_name, new_content)

# 4. 构建 APK
# → build_apk(project_dir)

# 5. 签名 APK
sign = manager.get_tool(ToolType.SIGN_TOOLS)
# → sign_apk(apk_path, keystore_name, keystore_password, key_alias)

# 6. 验证签名
# → verify_signature(signed_apk_path)
```

### 设备调试流程
```python
from tools import ApkMCPManager, ToolType

manager = ApkMCPManager()
adb = manager.get_tool(ToolType.ADB)

# 1. 连接设备
# → list_devices()

# 2. 安装 APK
# → install_apk(apk_path, device_id)

# 3. 获取日志
# → get_logcat(device_id, package_name, max_lines)

# 4. 执行调试命令
# → execute_shell(command, device_id)
```

### 动态分析流程（Frida）
```python
from tools import ApkMCPManager, ToolType

manager = ApkMCPManager()
frida = manager.get_tool(ToolType.FRIDA)

# 1. 列出进程
# → list_processes()

# 2. 附加到目标进程
# → attach_process(target)

# 3. Hook 函数
# → hook_function(session_id, class_name, method_name)

# 4. 拦截网络请求
# → intercept_network(session_id, filter_url)

# 5. 获取消息
# → get_messages(session_id)
```

## 配置说明

### 自动生成 MCP 配置

使用命令行工具自动生成配置：

```bash
python apkmcp.py config
```

这将生成 `.trae/config.json`：

```json
{
  "mcpServers": {
    "jadx-mcp-server": {
      "type": "stdio",
      "command": "E:/www/ApkMCP-Auto/tools/bin/jre/bin/java.exe",
      "args": ["-jar", "E:/www/ApkMCP-Auto/tools/jadx/server.jar"],
      "enabled": true,
      "description": "JADX MCP 服务器 - Java 反编译分析"
    },
    "apktool-mcp-server": {
      "type": "stdio",
      "command": "python",
      "args": [
        "E:/www/ApkMCP-Auto/tools/apktool/server.py",
        "--workspace", "E:/www/ApkMCP-Auto/tools/workspace/apktool",
        "--apktool-path", "E:/www/ApkMCP-Auto/tools/bin/apktool.bat"
      ],
      "enabled": true,
      "description": "APKTool MCP 服务器 - APK 解码/编码"
    },
    "adb-mcp-server": {
      "type": "stdio",
      "command": "python",
      "args": [
        "E:/www/ApkMCP-Auto/tools/adb/server.py",
        "--adb-path", "E:/www/ApkMCP-Auto/tools/bin/adb.exe"
      ],
      "enabled": true,
      "description": "ADB MCP 服务器 - 设备管理和调试"
    },
    "sign-tools-mcp-server": {
      "type": "stdio",
      "command": "python",
      "args": [
        "E:/www/ApkMCP-Auto/tools/sign-tools/server.py",
        "--workspace", "E:/www/ApkMCP-Auto/tools/workspace/sign-tools"
      ],
      "enabled": true,
      "description": "签名工具 MCP 服务器 - APK 签名和密钥管理"
    },
    "static-analyzer": {
      "type": "stdio",
      "command": "python",
      "args": ["E:/www/ApkMCP-Auto/tools/static-analyzer/server.py"],
      "enabled": true,
      "description": "静态分析工具 - 权限、字符串、SDK 识别"
    },
    "diff-tool": {
      "type": "stdio",
      "command": "python",
      "args": ["E:/www/ApkMCP-Auto/tools/diff/server.py"],
      "enabled": true,
      "description": "文件对比工具 - APK、Smali、资源对比"
    },
    "frida-mcp-server": {
      "type": "stdio",
      "command": "python",
      "args": ["E:/www/ApkMCP-Auto/tools/frida/server.py"],
      "enabled": true,
      "description": "Frida MCP 服务器 - 动态插桩分析"
    }
  }
}
```

## 使用示例

### 示例 1: 完整 APK 分析
```
用户: 分析 APK 文件 E:/test.apk

AI: 我将帮您全面分析这个 APK 文件。让我按步骤进行：

1. 首先使用 APKTool 解码 APK
2. 进行静态分析（权限、SDK、字符串）
3. 使用 JADX 分析代码结构

[调用 MCP 工具执行分析...]
```

### 示例 2: 去除广告
```
用户: 帮我去除这个 APK 中的广告

AI: 我将帮您分析并去除广告。步骤如下：

1. 解码 APK
2. 识别广告 SDK
3. 定位广告相关代码
4. 修改 Smali 代码禁用广告
5. 重新打包并签名

[调用相关 MCP 工具...]
```

### 示例 3: 调试应用
```
用户: 连接设备并安装 APK

AI: 我来帮您连接设备和安装 APK：

1. 列出已连接设备
2. 安装 APK 到设备
3. 启动应用并获取日志

[调用 ADB MCP Server 工具...]
```

## 注意事项

1. **合法性**: 仅用于合法的安全研究和学习目的
2. **权限**: 仅分析您拥有合法权限的应用程序
3. **安全**: 不要将 MCP Server 绑定到公网地址
4. **签名**: APK 修改后需要重新签名才能安装
5. **资源释放**: 分析完成后关闭 MCP 工具连接

## 技术栈

- **Python 3.10+** - MCP Server 开发
- **FastMCP** - MCP 协议实现
- **APKTool 3.0+** - APK 反编译/重打包
- **JADX 1.5+** - Android Dex 反编译
- **Java 17** - JADX 运行环境
- **ADB** - Android 调试桥
- **Frida** - 动态插桩框架

## 报告生成

使用提示词模板进行分析后，会自动生成结构化报告：
- `分析报告.md` - 通用 APK 分析报告
- `广告分析报告.md` - 广告 SDK 识别和去除方案
- `会员分析报告.md` - 会员验证机制分析
- `加固分析报告.md` - 加固识别和脱壳方案
- `网络分析报告.md` - 网络通信分析
- `逆向分析报告.md` - 综合逆向工程报告
