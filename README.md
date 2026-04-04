# Android 逆向工程 MCP 工具套件

<div align="center">

⚡ 基于 Model Context Protocol (MCP) 的 Android APK 自动化逆向工程工具套件

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Java](https://img.shields.io/badge/Java-17-blue)](https://openjdk.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://www.apache.org/licenses/LICENSE-2.0)

</div>

---

## 项目简介

本项目是一个 Android 逆向工程工具集合，通过 **MCP (Model Context Protocol)** 协议将 AI 助手（如 Claude）与专业的 Android 反编译工具连接起来，实现智能化的 APK 分析与修改。

### 包含组件

| 组件 | 说明 | 路径 |
|------|------|------|
| **JADX MCP Server** | 与 JADX-GUI 集成的 MCP 服务器，提供实时反编译分析 | `java/jadx-mcp-server/` |
| **APKTool MCP Server** | 基于 APKTool 的 MCP 服务器，支持 APK 解码/编码与 Smali 修改 | `java/apktool-mcp-server/` |
| **JADX-GUI** | 带 JRE 的 JADX 反编译工具 | `java/jadx-gui/` |
| **APKTool** | APK 反编译/重打包工具 | `java/apktool/` |

---

## 功能特性

### JADX MCP Server

- 实时获取当前选中的类代码
- 搜索类、方法、字段
- 获取 AndroidManifest.xml 内容
- 获取资源文件（strings.xml 等）
- 重命名类/方法/字段/变量（代码重构）
- 调试器集成（获取堆栈帧、线程、变量）
- 交叉引用分析（查找类/方法/字段的引用）
- 支持分页查询大结果集

### APKTool MCP Server

- APK 解码与编码（反编译/重打包）
- Smali 代码浏览与修改
- 资源文件管理
- 项目结构分析
- 文件内容搜索
- 自动备份机制
- 工作空间管理

---

## 系统要求

| 环境 | 版本要求 |
|------|----------|
| Windows | Windows 10/11 |
| Python | 3.10 或更高版本 |
| Java | OpenJDK 17 (已包含在 jadx-gui/jre 中) |
| 内存 | 建议 8GB 或更高 |

---

## 快速开始

### 1. 安装依赖

```bash
# 安装 JADX MCP Server 依赖
cd java/jadx-mcp-server/jadx-mcp-server
pip install -r requirements.txt

# 安装 APKTool MCP Server 依赖
cd java/apktool-mcp-server/apktool-mcp-server
pip install -r requirements.txt
```

### 2. 启动 JADX MCP Server

```bash
cd java/jadx-mcp-server/jadx-mcp-server

# 标准模式 (stdio)
python jadx_mcp_server.py

# HTTP 模式
python jadx_mcp_server.py --http --port 8651
```

### 3. 启动 APKTool MCP Server

```bash
cd java/apktool-mcp-server/apktool-mcp-server

# 标准模式
python apktool_mcp_server.py

# HTTP 模式，指定工作目录
python apktool_mcp_server.py --http --port 8652 --workspace ./workspace
```

### 4. 配置 MCP 客户端

#### Claude Desktop 配置

在 Claude Desktop 或其他 MCP 客户端中配置：

```json
{
  "mcpServers": {
    "jadx": {
      "command": "python",
      "args": ["E:/A_java/java/jadx-mcp-server/jadx-mcp-server/jadx_mcp_server.py"]
    },
    "apktool": {
      "command": "python",
      "args": ["E:/A_java/java/apktool-mcp-server/apktool-mcp-server/apktool_mcp_server.py"]
    }
  }
}
```

#### Trae IDE 配置

在 Trae IDE 中使用本项目，请创建 `.trae/config.json` 文件：

```json
{
  "model": {
    "provider": "anthropic",
    "name": "claude-sonnet-4-5",
    "fallback": "claude-sonnet-4"
  },

  "mcp": {
    "servers": {
      "jadx-mcp-server": {
        "type": "stdio",
        "command": "java",
        "args": [
          "-jar",
          "E:/A_java/java/jadx-mcp-server/jadx-ai-mcp-6.3.0.jar"
        ],
        "enabled": true,
        "description": "jadx MCP 服务器 (Java JAR 版本)"
      },
      "jadx-mcp-python": {
        "type": "stdio",
        "command": "python",
        "args": [
          "E:/A_java/java/jadx-mcp-server/jadx-mcp-server/jadx_mcp_server.py"
        ],
        "enabled": false,
        "description": "jadx MCP 服务器 (Python 版本)"
      },
      "apktool-mcp-server": {
        "type": "stdio",
        "command": "python",
        "args": [
          "E:/A_java/java/apktool-mcp-server/apktool-mcp-server/apktool_mcp_server.py",
          "--workspace",
          "E:/A_java/apktool_workspace",
          "--apktool-path",
          "E:/A_java/java/apktool/apktool.bat"
        ],
        "enabled": true,
        "description": "apktool MCP 服务器"
      }
    }
  },

  "permission": {
    "read": {
      "allow": ["*"],
      "deny": ["*.env", "./secrets/**"]
    },
    "edit": {
      "allow": ["src/**"],
      "deny": [],
      "prompt": ["*"]
    },
    "bash": {
      "allow": ["git *"],
      "deny": ["rm *"],
      "prompt": ["*"]
    }
  },

  "tools": {
    "write": true,
    "bash": true,
    "webfetch": true,
    "search": true
  },

  "watcher": {
    "ignore": [
      "node_modules/**",
      "*.log",
      ".git/**",
      "java/jre/**",
      "*.zip",
      "*.jar"
    ]
  },

  "instructions": {
    "default": "Android 逆向工程工具项目，包含 jadx-gui、apktool 及其 MCP 服务器。"
  },

  "ui": {
    "scroll_speed": 3,
    "diff_style": "auto"
  }
}
```

Trae 配置说明：

| 配置项 | 说明 |
|--------|------|
| `model` | AI 模型配置，支持主模型和备用模型 |
| `mcp.servers` | MCP 服务器配置，包含 jadx 和 apktool 两个服务器 |
| `permission` | 文件读写和命令执行权限控制 |
| `tools` | 启用/禁用各类工具 |
| `watcher` | 文件监控忽略规则 |
| `instructions` | AI 助手的默认上下文说明 |
| `ui` | 界面显示配置 |

---

## 使用示例

### 分析 APK 文件

```
# 使用 APKTool MCP Server 解码 APK
请帮我解码 APK 文件 E:/A_java/app-debug.apk

# 分析完成后可以查看
- AndroidManifest.xml
- Smali 代码
- 资源文件
- 项目结构
```

### 代码审查与安全分析

```
# 使用 JADX MCP Server 分析代码
请帮我分析当前选中的类是否存在安全漏洞

# 搜索特定代码模式
搜索包含 "AES" 加密的类

# 查找引用
查找哪些方法调用了 sendRequest 方法
```

---

## 提示词模板

本项目提供了专门的 APK 逆向工程分析提示词模板，方便快速进行各类分析：

### 提示词模板文件

📄 **文件位置**: `prompt_template.md`

### 包含的提示词类型

| 提示词 | 用途 | 输出报告 |
|--------|------|----------|
| 通用 APK 分析 | 全面的 APK 信息提取和分析 | `分析报告.md` |
| 广告去除专项 | 定位广告 SDK 和去除方案 | `广告分析报告.md` |
| 会员破解专项 | 分析会员验证机制 | `会员分析报告.md` |
| 加固分析专项 | 识别加固方案和脱壳建议 | `加固分析报告.md` |
| 网络分析专项 | 分析网络通信和拦截点 | `网络分析报告.md` |
| 综合逆向分析 | 完整的逆向工程流程 | `逆向分析报告.md` |

### 使用方法

1. 打开 `prompt_template.md` 文件
2. 选择需要的提示词模板
3. 复制到 AI 助手
4. 替换 `[APK文件路径]` 和 `[工作目录]`
5. AI 会自动调用 MCP 工具执行分析并生成报告

### 提示词特点

- ✅ 明确调用 MCP 工具指令
- ✅ 详细的分析步骤
- ✅ 自动生成结构化报告
- ✅ 包含清理和关闭步骤
- ✅ 支持多种分析目标

---

## 项目结构

```
A_java/
├── java/
│   ├── apktool/                    # APKTool 工具
│   │   ├── apktool.bat
│   │   └── apktool.jar
│   ├── apktool-mcp-server/         # APKTool MCP Server
│   │   └── apktool-mcp-server/
│   │       ├── apktool_mcp_server.py
│   │       └── requirements.txt
│   ├── jadx-gui/                   # JADX-GUI 工具
│   │   ├── jadx-gui-1.5.5.exe
│   │   └── jre/                    # 内置 JRE
│   └── jadx-mcp-server/            # JADX MCP Server
│       └── jadx-mcp-server/
│           ├── jadx_mcp_server.py
│           ├── requirements.txt
│           └── src/
├── zip/                            # 压缩包备份
├── prompt_template.md              # APK 逆向分析提示词模板
└── README.md                       # 本文件
```

---

## 可用 MCP 工具

### JADX MCP Server 工具

| 工具名 | 功能描述 |
|--------|----------|
| `fetch_current_class` | 获取当前选中的类 |
| `get_class_source` | 获取指定类的源代码 |
| `get_all_classes` | 列出所有类（支持分页） |
| `search_classes_by_keyword` | 按关键词搜索类 |
| `get_method_by_name` | 获取指定方法的代码 |
| `get_methods_of_class` | 列出类的所有方法 |
| `get_fields_of_class` | 列出类的所有字段 |
| `get_smali_of_class` | 获取类的 Smali 代码 |
| `get_android_manifest` | 获取 AndroidManifest.xml |
| `get_strings` | 获取字符串资源 |
| `get_resource_file` | 获取资源文件内容 |
| `rename_class` | 重命名类 |
| `rename_method` | 重命名方法 |
| `rename_field` | 重命名字段 |
| `rename_variable` | 重命名变量 |
| `debug_get_stack_frames` | 获取调试堆栈帧 |
| `debug_get_variables` | 获取调试变量 |
| `get_xrefs_to_class` | 查找类的交叉引用 |
| `get_xrefs_to_method` | 查找方法的交叉引用 |

### APKTool MCP Server 工具

| 工具名 | 功能描述 |
|--------|----------|
| `decode_apk` | 解码 APK 文件 |
| `build_apk` | 从项目构建 APK |
| `get_manifest` | 获取 AndroidManifest.xml |
| `get_apktool_yml` | 获取 apktool.yml |
| `list_smali_directories` | 列出 Smali 目录 |
| `list_smali_files` | 列出 Smali 文件（支持分页） |
| `get_smali_file` | 获取 Smali 文件内容 |
| `modify_smali_file` | 修改 Smali 文件 |
| `list_resources` | 列出资源文件 |
| `get_resource_file` | 获取资源文件内容 |
| `modify_resource_file` | 修改资源文件 |
| `search_in_files` | 在文件中搜索 |
| `analyze_project_structure` | 分析项目结构 |
| `clean_project` | 清理项目 |
| `get_workspace_info` | 获取工作空间信息 |
| `health_check` | 健康检查 |

---

## 技术栈

- **Python 3.10+** - MCP Server 开发
- **FastMCP** - MCP 协议实现
- **httpx** - HTTP 客户端
- **APKTool 3.0+** - APK 反编译/重打包
- **JADX 1.5+** - Android Dex 反编译
- **Java 17** - JADX 运行环境

---

## 命令行参数

### JADX MCP Server

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--http` | False | 启用 HTTP 传输模式 |
| `--host` | 127.0.0.1 | MCP 服务器监听地址 |
| `--port` | 8651 | MCP 服务器端口 |
| `--jadx-host` | 127.0.0.1 | JADX 插件地址 |
| `--jadx-port` | 8650 | JADX 插件端口 |

### APKTool MCP Server

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--http` | False | 启用 HTTP 传输模式 |
| `--port` | 8652 | MCP 服务器端口 |
| `--workspace` | apktool_mcp_server_workspace | 工作目录 |
| `--timeout` | 300 | 命令超时时间（秒） |
| `--apktool-path` | apktool | APKTool 可执行文件路径 |

---

## 工作流程

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  AI 助手    │◄───►│   MCP Server    │◄───►│   JADX/APKTool  │
│ (Claude等)  │     │ (Python FastMCP)│     │  (Java/命令行)  │
└─────────────┘     └─────────────────┘     └─────────────────┘
       │                     │                      │
       │  1. 发送 MCP 请求    │                      │
       │────────────────────>│                      │
       │                     │  2. 调用工具         │
       │                     │─────────────────────>│
       │                     │                      │
       │                     │  3. 返回结果         │
       │                     │<─────────────────────│
       │  4. 返回 MCP 响应    │                      │
       │<────────────────────│                      │
```

---

## 报告生成

使用提示词模板进行分析后，会自动生成结构化的 Markdown 报告：

### 报告类型

| 报告名称 | 内容 | 保存位置 |
|----------|------|----------|
| `分析报告.md` | 通用 APK 分析报告 | `[工作目录]/分析报告.md` |
| `广告分析报告.md` | 广告 SDK 识别和去除方案 | `[工作目录]/广告分析报告.md` |
| `会员分析报告.md` | 会员验证机制分析 | `[工作目录]/会员分析报告.md` |
| `加固分析报告.md` | 加固识别和脱壳方案 | `[工作目录]/加固分析报告.md` |
| `网络分析报告.md` | 网络通信分析 | `[工作目录]/网络分析报告.md` |
| `逆向分析报告.md` | 综合逆向工程报告 | `[工作目录]/逆向分析报告.md` |

### 报告内容结构

每个报告通常包含：
1. **执行摘要** - 分析目标和主要发现
2. **应用概况** - 基本信息和技术栈
3. **详细分析** - 代码位置、逻辑分析
4. **解决方案** - 修改方案和实施步骤
5. **风险评估** - 技术、安全、法律风险
6. **附录** - 代码片段、工具配置

---

## 安全提示

1. **仅用于合法的安全研究和学习目的**
2. **仅分析您拥有合法权限的应用程序**
3. **不要将 MCP Server 绑定到公网地址（使用 `--host 0.0.0.0` 时请注意）**
4. **APK 修改后需要重新签名才能安装**
5. **分析完成后记得关闭 MCP 工具连接，释放资源**

---

## 许可证

本项目采用 **Apache License 2.0** 开源许可证。

---

## 致谢

- [JADX](https://github.com/skylot/jadx) - 优秀的 Android 反编译工具
- [APKTool](https://github.com/iBotPeaches/Apktool) - 强大的 APK 反编译/重打包工具
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk) - Python MCP SDK
- [Anthropic MCP](https://github.com/anthropics/mcp) - Model Context Protocol

---

<div align="center">

**Made with ❤️ for Android Reverse Engineering**

</div>