# ApkMCP-Auto AI 项目指引

> 本文档专为 AI 助手设计，说明如何在本项目中调用 Skill 和 MCP 工具

---

## 快速判断

当用户提出以下需求时，**立即调用 `apkmcp-auto` Skill**：

| 用户意图 | 触发关键词 |
|---------|-----------|
| APK 反编译/分析 | "反编译 APK"、"分析 APK"、"查看 APK 代码" |
| Smali 修改 | "修改 Smali"、"改代码"、"去广告"、"破解" |
| APK 打包/签名 | "打包 APK"、"签名"、"重新编译" |
| 设备调试 | "连接手机"、"安装 APK"、"查看日志"、"adb" |
| 代码对比 | "对比 APK"、"比较文件差异"、"diff" |
| 动态分析 | "Hook"、"Frida"、"动态调试"、"拦截请求" |
| 静态分析 | "分析权限"、"提取字符串"、"识别 SDK" |

---

## 调用 Skill

### 方式一：直接调用 Skill 工具（推荐）

当识别到 APK 相关任务时，**立即执行**：

```
调用 Skill: apkmcp-auto
```

Skill 会自动加载并指导后续操作。

### 方式二：使用 apkmcp.py 命令行工具

```bash
# 查看所有工具状态
python apkmcp.py status

# 生成 MCP 配置
python apkmcp.py config

# 安装所有依赖
python apkmcp.py install

# 列出所有可用工具
python apkmcp.py list
```

---

## MCP 配置说明

项目 MCP 配置位于 `.trae/config.json`，包含 7 个 MCP 服务器：

| MCP Server | 功能 | 何时调用 |
|-----------|------|---------|
| `jadx-mcp-server` | Java 反编译分析 | 需要查看 Java 源代码、搜索类/方法、获取 Manifest |
| `apktool-mcp-server` | APK 解码/编码 | 需要反编译 APK 为 Smali、修改资源、重新打包 |
| `adb-mcp-server` | 设备管理和调试 | 需要连接设备、安装 APK、获取日志、执行 Shell |
| `sign-tools-mcp-server` | APK 签名和密钥管理 | 需要生成密钥、签名 APK、验证签名 |
| `static-analyzer` | 静态分析 | 需要分析权限、提取字符串、识别第三方 SDK |
| `diff-tool` | 文件对比 | 需要对比两个 APK 或 Smali 文件的差异 |
| `frida-mcp-server` | 动态插桩分析 | 需要 Hook 函数、拦截网络、内存操作 |

---

## 典型任务处理流程

### 任务 1：完整 APK 分析

```
用户：分析这个 APK 文件

AI 处理步骤：
1. 调用 Skill: apkmcp-auto
2. 使用 apktool-mcp-server 解码 APK
3. 使用 static-analyzer 进行静态分析
4. 使用 jadx-mcp-server 分析代码结构
5. 生成分析报告
```

### 任务 2：去除广告

```
用户：帮我去掉这个 APK 的广告

AI 处理步骤：
1. 调用 Skill: apkmcp-auto
2. 使用 apktool-mcp-server 解码 APK
3. 使用 static-analyzer 识别广告 SDK
4. 使用 jadx-mcp-server 定位广告代码
5. 使用 apktool-mcp-server 修改 Smali 代码
6. 使用 apktool-mcp-server 重新构建 APK
7. 使用 sign-tools-mcp-server 签名 APK
8. 使用 diff-tool 对比修改前后的差异
```

### 任务 3：设备调试

```
用户：连接我的手机并安装 APK

AI 处理步骤：
1. 调用 Skill: apkmcp-auto
2. 使用 adb-mcp-server 列出设备
3. 使用 adb-mcp-server 安装 APK
4. 使用 adb-mcp-server 获取日志
```

### 任务 4：动态分析

```
用户：Hook 这个应用的登录函数

AI 处理步骤：
1. 调用 Skill: apkmcp-auto
2. 使用 frida-mcp-server 列出进程
3. 使用 frida-mcp-server 附加到目标进程
4. 使用 frida-mcp-server hook_function
5. 使用 frida-mcp-server 获取消息
```

---

## MCP 工具详细说明

### 1. JADX MCP Server (jadx-mcp-server)

**用途**：Java 代码反编译和分析

**常用工具**：
- `get_android_manifest` - 获取 AndroidManifest.xml
- `search_classes_by_keyword` - 搜索类
- `get_class_source` - 获取类源代码
- `get_method_by_name` - 获取方法代码
- `get_xrefs_to_method` - 查找方法引用
- `rename_class/method/field` - 代码重构

**调用示例**：
```python
# 获取 Manifest
get_android_manifest()

# 搜索包含 "login" 的类
search_classes_by_keyword(keyword="login")

# 获取类源代码
get_class_source(class_name="com.example.MainActivity")
```

### 2. APKTool MCP Server (apktool-mcp-server)

**用途**：APK 解码、修改、重打包

**常用工具**：
- `decode_apk` - 解码 APK
- `build_apk` - 构建 APK
- `get_smali_file` / `modify_smali_file` - Smali 操作
- `list_resources` / `modify_resource_file` - 资源管理
- `search_in_files` - 文件搜索

**调用示例**：
```python
# 解码 APK
decode_apk(apk_path="E:/test.apk")

# 获取 Smali 文件
get_smali_file(class_name="com.example.MainActivity")

# 修改 Smali 文件
modify_smali_file(class_name="com.example.MainActivity", content="...")

# 构建 APK
build_apk(project_dir="workspace/test")
```

### 3. ADB MCP Server (adb-mcp-server)

**用途**：设备管理和调试

**常用工具**：
- `list_devices` - 列出设备
- `install_apk` / `uninstall_package` - 应用管理
- `get_logcat` - 获取日志
- `execute_shell` - 执行 Shell 命令
- `screenshot` - 截图

**调用示例**：
```python
# 列出设备
list_devices()

# 安装 APK
install_apk(apk_path="E:/test.apk", device_id="xxx")

# 获取日志
get_logcat(package_name="com.example.app", max_lines=100)
```

### 4. Sign Tools MCP Server (sign-tools-mcp-server)

**用途**：APK 签名管理

**常用工具**：
- `generate_keystore` - 生成密钥库
- `sign_apk` - 签名 APK
- `verify_signature` - 验证签名
- `zipalign_apk` - 对齐优化

**调用示例**：
```python
# 生成密钥库
generate_keystore(name="mykey", password="123456", alias="key0")

# 签名 APK
sign_apk(apk_path="E:/test.apk", keystore_name="mykey", 
         keystore_password="123456", key_alias="key0")
```

### 5. Static Analyzer (static-analyzer)

**用途**：静态代码分析

**常用工具**：
- `analyze_permissions` - 权限分析
- `extract_strings` - 提取字符串
- `extract_endpoints` - 提取 URL/API
- `identify_sdks` - 识别第三方 SDK
- `full_analysis` - 完整分析

**调用示例**：
```python
# 完整分析
full_analysis(project_dir="workspace/test")

# 识别 SDK
identify_sdks(project_dir="workspace/test")
```

### 6. Diff Tool (diff-tool)

**用途**：文件对比

**常用工具**：
- `compare_apks` - 对比 APK
- `compare_smali` - 对比 Smali 文件
- `compare_resources` - 对比资源

**调用示例**：
```python
# 对比两个 APK
compare_apks(original_apk="E:/original.apk", modified_apk="E:/modified.apk")
```

### 7. Frida MCP Server (frida-mcp-server)

**用途**：动态插桩分析

**常用工具**：
- `list_processes` - 列出进程
- `attach_process` - 附加进程
- `hook_function` - Hook 函数
- `intercept_network` - 拦截网络
- `scan_memory` / `read_memory` - 内存操作

**调用示例**：
```python
# 列出进程
list_processes()

# 附加进程
attach_process(target="com.example.app")

# Hook 函数
hook_function(session_id="xxx", class_name="com.example.Login", 
              method_name="checkPassword")
```

---

## 工作目录结构

```
ApkMCP-Auto/
├── .trae/
│   ├── config.json              # MCP 配置（自动生成）
│   └── skills/
│       └── apkmcp-auto/         # Skill 定义
│           └── SKILL.md
├── tools/                       # 工具目录
│   ├── bin/                     # 二进制工具
│   │   ├── adb.exe
│   │   ├── apktool.jar
│   │   ├── jadx-gui.exe
│   │   └── jre/                 # Java 运行时
│   ├── jadx/
│   ├── apktool/
│   ├── adb/
│   ├── sign-tools/
│   ├── static-analyzer/
│   ├── diff/
│   ├── frida/
│   └── workspace/               # 工作空间
│       ├── apktool/
│       └── sign-tools/
├── apkmcp.py                    # 统一命令行工具
└── AI_GUIDE.md                  # 本文件
```

---

## 重要提示

1. **路径处理**：所有路径使用相对路径，确保项目可移植
2. **依赖安装**：首次使用前运行 `python apkmcp.py install`
3. **配置生成**：运行 `python apkmcp.py config` 生成 MCP 配置
4. **合法性**：仅用于合法的安全研究和学习目的
5. **权限**：仅分析拥有合法权限的应用程序

---

## 快速参考卡

| 我想做... | 调用... | 关键工具 |
|----------|--------|---------|
| 查看 APK 代码 | jadx-mcp-server | get_class_source |
| 修改 APK | apktool-mcp-server | decode_apk → modify_smali_file → build_apk |
| 签名 APK | sign-tools-mcp-server | sign_apk |
| 连接设备 | adb-mcp-server | list_devices, install_apk |
| 分析权限 | static-analyzer | analyze_permissions |
| 对比文件 | diff-tool | compare_apks |
| Hook 函数 | frida-mcp-server | hook_function |

---

**文档版本**: 1.0  
**适用项目**: ApkMCP-Auto  
**最后更新**: 2025-04-09
