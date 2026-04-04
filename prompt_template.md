# APK 逆向工程分析提示词模板

## 使用方法

1. 将下面的提示词复制到 AI 助手
2. 将 `[APK文件路径]` 替换为实际的 APK 文件路径
3. 将 `[工作目录]` 替换为 APK 解码后的工作目录路径
4. 根据需要选择特定的分析目标（广告去除/会员破解/加固分析）

**MCP 工具配置说明：**
- APKTool MCP Server 路径：`E:/A_java/java/apktool-mcp-server/apktool-mcp-server/apktool_mcp_server.py`
- JADX MCP Server 路径：`E:/A_java/java/jadx-mcp-server/jadx-mcp-server/jadx_mcp_server.py`
- 确保两个 MCP Server 已启动并连接

---

## 通用 APK 分析提示词

```
请帮我对 APK 文件进行全面的逆向工程分析。

APK 路径: [APK文件路径]
工作目录: [工作目录]

请按照以下步骤进行分析，使用已配置的 MCP 工具：

### 第一步：APK 解码与基础信息提取
使用 APKTool MCP Server 执行：
1. 调用 `decode_apk` 解码 APK 文件到工作目录
2. 调用 `get_manifest` 获取并分析 AndroidManifest.xml：
   - 包名、版本号、应用名称
   - 所有权限声明
   - 四大组件（Activity/Service/Receiver/Provider）清单
   - 是否存在加固或混淆特征
3. 调用 `get_apktool_yml` 分析 APK 结构
4. 调用 `analyze_project_structure` 获取项目整体分析

### 第二步：代码结构分析
使用 APKTool MCP Server 执行：
1. 调用 `list_smali_directories` 列出所有 Smali 目录
2. 调用 `list_smali_files` 获取主包 Smali 文件列表（分页获取）
3. 调用 `search_in_files` 搜索关键字符串：
   - 广告相关："ad"、"ads"、"advertisement"、"AdView"、"BannerAd"
   - 会员相关："vip"、"premium"、"member"、"pro"、"unlock"
   - 验证相关："signature"、"verify"、"check"、"license"
   - 加密相关："encrypt"、"decrypt"、"aes"、"rsa"

### 第三步：资源文件审查
使用 APKTool MCP Server 执行：
1. 调用 `list_resources` 列出所有资源类型
2. 检查 layout 资源中的广告视图
3. 调用 `get_resource_file` 获取 strings.xml 分析关键文本
4. 检查 drawable 资源中的广告图片

### 第四步：网络通信分析
使用 APKTool MCP Server 执行：
1. 调用 `search_in_files` 搜索网络相关代码：
   - "Retrofit"、"OkHttp"、"HttpURLConnection"
   - "api"、"endpoint"、"baseUrl"
   - "GET"、"POST"、"PUT"、"DELETE"
2. 分析找到的 API 接口定义类

### 第五步：生成分析报告并保存
基于以上 MCP 工具分析结果，生成完整的 APK 分析报告：

1. **应用基本信息**
   - 包名、版本号、应用名称
   - 权限列表（按危险等级分类）
   - 四大组件统计

2. **技术栈识别**
   - 网络库（OkHttp/Retrofit/Volley）
   - 架构模式（MVC/MVP/MVVM）
   - 第三方 SDK 列表

3. **代码结构统计**
   - Smali 文件总数
   - 各目录文件分布
   - 主包代码量估算

4. **安全分析**
   - 加固/混淆评估
   - 敏感权限使用
   - 明文传输风险
   - 调试模式检测

5. **潜在修改点**
   - 广告相关代码位置
   - 会员验证逻辑位置
   - 功能限制检查点

6. **修改建议**（如适用）
   - 具体文件路径
   - 修改方法说明
   - 风险提示

将完整分析报告保存为 Markdown 文件到工作目录：`[工作目录]/分析报告.md`

### 第六步：清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**

---

## 专项分析提示词

### 1. 广告去除专项分析

```
请帮我分析 APK 文件中的广告实现机制，并提供去除方案。

APK 路径: [APK文件路径]
工作目录: [工作目录]

分析目标：识别并定位所有广告相关代码和资源

请使用 MCP 工具执行以下分析：

#### 1. APK 解码与基础分析
使用 APKTool MCP Server：
- 调用 `decode_apk` 解码 APK
- 调用 `get_manifest` 检查广告相关权限和组件
- 调用 `analyze_project_structure` 获取项目概览

#### 2. 广告 SDK 识别
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索广告 SDK 特征：
  - 包名关键词："com.google.android.gms.ads"、"com.facebook.ads"、"com.baidu.mobads"、"com.tencent.mm"
  - 类名关键词："AdView"、"BannerAd"、"InterstitialAd"、"RewardedAd"、"NativeAd"
  - 方法关键词："loadAd"、"showAd"、"requestAd"、"onAdLoaded"

#### 3. 广告视图定位
使用 APKTool MCP Server：
- 调用 `list_resources` 列出 layout 资源
- 调用 `get_resource_file` 获取可疑的 layout XML 文件
- 搜索广告容器："ad_container"、"ad_view"、"banner_container"

#### 4. 广告加载逻辑分析
使用 APKTool MCP Server：
- 调用 `search_in_files` 在 .smali 文件中搜索：
  - "loadAd"、"showAd"、"requestAd"
  - "onAdLoaded"、"onAdFailedToLoad"
  - "AdListener"、"AdCallback"
- 调用 `get_smali_file` 获取关键广告类的 Smali 代码

#### 5. 生成广告分析报告并保存
基于 MCP 工具分析结果，生成完整的广告分析报告：

**报告内容：**
1. **广告 SDK 清单**
   - 检测到的广告 SDK 列表
   - SDK 版本信息
   - 广告单元 ID（如有）

2. **广告代码位置**
   - 广告初始化代码文件路径
   - 广告加载方法位置
   - 广告展示触发点

3. **广告资源清单**
   - 广告布局文件
   - 广告图片资源
   - 广告配置文件

4. **去除方案**
   - 方案一：Smali 代码修改（推荐）
     - 需要修改的文件列表
     - 具体修改位置
     - 修改前后代码对比
   - 方案二：资源删除
     - 可删除的资源文件
     - 注意事项
   - 方案三：方法 Hook
     - Frida 脚本示例

5. **验证步骤**
   - 修改后如何测试
   - 常见问题排查

6. **风险提示**
   - 修改可能导致的问题
   - 应用稳定性影响

将报告保存为：`[工作目录]/广告分析报告.md`

#### 6. 清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**
```

### 2. 会员功能破解/绕过分析

```
请帮我分析 APK 文件中的会员验证机制，识别可绕过或修改的关键点。

APK 路径: [APK文件路径]
工作目录: [工作目录]

分析目标：定位会员状态验证逻辑，寻找绕过方案

请使用 MCP 工具执行以下分析：

#### 1. APK 解码
使用 APKTool MCP Server：
- 调用 `decode_apk` 解码 APK
- 调用 `get_manifest` 获取应用基本信息

#### 2. 会员相关代码定位
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索会员相关关键词：
  - "isVip"、"isPremium"、"isPro"、"isMember"、"isUnlock"
  - "getVipStatus"、"checkVip"、"verifyLicense"
  - "vip_expire"、"member_valid"、"subscription"
  - "purchase"、"buy"、"pay"、"order"
- 记录所有匹配的文件和方法

#### 3. 用户状态存储分析
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索本地存储：
  - "SharedPreferences"、"getSharedPreferences"
  - "SQLiteDatabase"、"Room"
  - "vip"、"premium"、"member"（在存储相关代码中）
- 调用 `get_smali_file` 获取关键存储类的代码

#### 4. 服务器验证逻辑
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索网络请求：
  - "user/info"、"member/info"、"vip/status"
  - "login"、"auth"、"token"
- 分析会员状态同步机制

#### 5. 功能限制检查点
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索功能限制逻辑：
  - "if.*isVip"、"if.*isPro"
  - "canUse"、"isAvailable"
  - "limit"、"restrict"
- 调用 `get_smali_file` 获取关键验证类的 Smali 代码

#### 6. 生成会员分析报告并保存
基于 MCP 工具分析结果，生成完整的会员机制分析报告：

**报告内容：**
1. **会员验证架构**
   - 验证方式（本地/服务器/混合）
   - 验证触发时机
   - 验证频率

2. **本地验证分析**
   - SharedPreferences 存储位置
   - 数据库表结构
   - 本地缓存机制
   - 加密方式（如有）

3. **服务器验证分析**
   - 验证 API 接口
   - 请求参数
   - 响应字段
   - 心跳检测机制

4. **功能限制点**
   - 功能限制代码位置
   - 限制类型（广告/功能/内容）
   - 限制条件

5. **破解方案**
   - 方案一：本地数据修改
     - 修改位置
     - 修改方法
   - 方案二：返回值篡改
     - Hook 点
     - Frida 脚本
   - 方案三：服务器响应修改
     - 抓包配置
     - 响应修改规则

6. **风险评估**
   - 检测风险
   - 封号风险
   - 法律风险

将报告保存为：`[工作目录]/会员分析报告.md`

⚠️ 注意：本分析仅供学习研究使用，请遵守相关法律法规。

#### 7. 清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**
```

### 3. 加固/壳分析

```
请帮我分析 APK 文件是否经过加固加壳，并评估脱壳难度。

APK 路径: [APK文件路径]
工作目录: [工作目录]

分析目标：识别加固方案，分析脱壳可行性

请使用 MCP 工具执行以下分析：

#### 1. APK 解码与初步检查
使用 APKTool MCP Server：
- 调用 `decode_apk` 尝试解码 APK
- 调用 `get_manifest` 检查入口点和组件
- 调用 `analyze_project_structure` 分析项目结构

#### 2. 加固特征识别
使用 APKTool MCP Server：
- 调用 `list_smali_directories` 检查 Smali 目录数量
- 调用 `search_in_files` 在 lib 目录搜索加固特征：
  - 360加固："libjiagu"、"libprotectClass"
  - 梆梆加固："libsecexe"、"libsecmain"、"libSecShell"
  - 爱加密："libijiami"、"libexec"
  - 腾讯乐固："libshell"、"libtup"
  - 百度加固："libbaiduprotect"
  - 阿里聚安全："libmobisec"、"libaliprotect"
  - 网易易盾："libnesec"
  - 其他："libegis"、"libedog"、"libchaosvmp"、"libx3g"

#### 3. 壳类型判断
使用 APKTool MCP Server：
- 检查 classes.dex 大小（调用 `analyze_project_structure`）
- 调用 `get_manifest` 分析入口 Activity
- 调用 `search_in_files` 搜索动态加载代码：
  - "DexClassLoader"、"PathClassLoader"
  - "loadDex"、"loadClass"
  - "attachBaseContext"

#### 4. 反调试/反篡改检测
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索反调试特征：
  - "/proc/self/status"、"TracerPid"
  - "ptrace"、"PTRACE_TRACEME"
  - "isDebuggerConnected"
  - "Xposed"、"Frida"
  - "getPackageSignature"、"checkSignature"

#### 5. 生成加固分析报告并保存
基于 MCP 工具分析结果，生成完整的加固分析报告：

**报告内容：**
1. **加固识别结果**
   - 检测到的加固厂商
   - 疑似加固版本
   - 壳类型（一代/二代/三代）
   - 加固强度评估

2. **壳特征分析**
   - 入口点分析
   - 类加载器分析
   - Native 层保护
   - 动态加载机制

3. **反调试机制**
   - 调试器检测
   - 模拟器检测
   - Root 检测
   - Hook 框架检测

4. **脱壳方案**
   - 推荐脱壳工具
   - 脱壳时机
   - Dump 位置
   - 自动化脚本

5. **动态分析建议**
   - 推荐环境（Android 版本）
   - 推荐工具（Frida/Xposed）
   - Hook 点建议
   - 反调试绕过

6. **脱壳风险**
   - 可能失败的原因
   - 替代方案

将报告保存为：`[工作目录]/加固分析报告.md`

#### 6. 清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**
```

### 4. 网络请求拦截/修改分析

```
请帮我分析 APK 的网络通信机制，定位可拦截和修改的关键点。

APK 路径: [APK文件路径]
工作目录: [工作目录]

分析目标：理解网络请求流程，找到拦截修改的入口

请使用 MCP 工具执行以下分析：

#### 1. APK 解码
使用 APKTool MCP Server：
- 调用 `decode_apk` 解码 APK
- 调用 `get_manifest` 获取应用信息

#### 2. 网络库识别
使用 APKTool MCP Server：
- 调用 `search_in_files` 识别网络库：
  - "OkHttpClient"、"OkHttp"
  - "Retrofit"、"Retrofit.Builder"
  - "Volley"、"RequestQueue"
  - "HttpURLConnection"
  - "addInterceptor"、"Interceptor"
- 调用 `get_smali_file` 获取网络客户端初始化类的代码

#### 3. API 接口收集
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索 API 定义：
  - "baseUrl"、"BASE_URL"
  - "@GET"、"@POST"、"@PUT"、"@DELETE"
  - "https://"、"http://"
- 调用 `list_smali_files` 定位 API 接口定义类
- 调用 `get_smali_file` 获取关键 API 接口类的代码

#### 4. 关键请求定位
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索关键请求：
  - 登录："login"、"signin"、"auth"
  - 会员："vip"、"member"、"premium"
  - 广告："ad"、"ads"、"advertisement"
  - 统计："stat"、"analytics"、"track"

#### 5. 加密/签名机制
使用 APKTool MCP Server：
- 调用 `search_in_files` 搜索加密签名代码：
  - "MD5"、"SHA1"、"SHA256"
  - "sign"、"signature"、"hmac"
  - "encrypt"、"decrypt"
  - "timestamp"、"nonce"
  - "CertificatePinner"、"SSL"
- 调用 `get_smali_file` 获取加密工具类的代码

#### 6. 生成网络分析报告并保存
基于 MCP 工具分析结果，生成完整的网络通信分析报告：

**报告内容：**
1. **网络架构**
   - 使用的网络库
   - 客户端配置
   - 拦截器设置

2. **API 接口清单**
   - 接口地址
   - 请求方法
   - 参数说明
   - 响应格式

3. **关键请求分析**
   - 登录请求
   - 会员验证请求
   - 广告配置请求
   - 数据上报请求

4. **安全机制**
   - 签名算法
   - 加密方式
   - SSL Pinning
   - 防重放机制

5. **拦截方案**
   - 抓包工具配置
   - SSL Pinning 绕过
   - 请求修改示例
   - 响应修改示例

6. **Hook 脚本**
   - Frida 脚本示例
   - 关键函数 Hook
   - 参数修改示例

将报告保存为：`[工作目录]/网络分析报告.md`

#### 7. 清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**
```

---

## 综合逆向分析提示词

```
请对以下 APK 进行全面的逆向工程分析，目标是 [广告去除/会员破解/功能解锁/加固分析]。

APK 路径: [APK文件路径]
工作目录: [工作目录]

请使用已配置的 MCP 工具按以下流程执行：

### Phase 1: 环境准备与 APK 解码
使用 APKTool MCP Server：
1. 调用 `health_check` 确认服务状态
2. 调用 `decode_apk` 解码 APK 到工作目录
3. 调用 `analyze_project_structure` 获取项目整体分析
4. 调用 `get_workspace_info` 确认工作空间状态

### Phase 2: 基础信息提取
使用 APKTool MCP Server：
1. 调用 `get_manifest` 分析 AndroidManifest.xml
2. 调用 `get_apktool_yml` 了解 APK 元数据
3. 调用 `list_smali_directories` 获取代码结构
4. 调用 `list_resources` 获取资源概览

### Phase 3: 目标代码定位
使用 APKTool MCP Server：
1. 根据目标调用 `search_in_files` 搜索关键词：
   - 广告去除："ad"、"AdView"、"loadAd"、"showAd"
   - 会员破解："isVip"、"isPro"、"checkVip"、"verify"
   - 功能解锁："isUnlock"、"canUse"、"limit"
   - 加固分析："libjiagu"、"libshell"、"DexClassLoader"
2. 调用 `list_smali_files` 获取主包代码列表
3. 调用 `get_smali_file` 获取关键类的 Smali 代码

### Phase 4: 深度分析
使用 APKTool MCP Server：
1. 调用 `search_in_files` 搜索相关代码模式
2. 调用 `get_resource_file` 检查相关资源
3. 分析代码逻辑和调用链

### Phase 5: 生成综合报告并保存
基于 MCP 工具分析结果，生成完整的逆向分析报告：

**报告内容：**
1. **执行摘要**
   - 分析目标
   - 主要发现
   - 关键结论

2. **应用概况**
   - 基本信息
   - 技术栈
   - 代码规模

3. **详细分析结果**
   - 根据分析目标展开
   - 代码位置
   - 逻辑分析

4. **解决方案**
   - 多种方案对比
   - 推荐方案
   - 实施步骤

5. **风险评估**
   - 技术风险
   - 安全风险
   - 法律风险

6. **附录**
   - 关键代码片段
   - 工具配置
   - 参考资源

将报告保存为：`[工作目录]/逆向分析报告.md`

### Phase 6: 清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**

⚠️ 注意：本分析仅供学习研究使用，请遵守相关法律法规，仅分析拥有合法权限的应用。
```

---

## 使用示例

### 示例 1：分析某视频 APP 会员机制

```
请对以下 APK 进行全面的逆向工程分析，目标是会员破解。

APK 路径: E:/A_java/samples/video_app.apk
工作目录: E:/A_java/workspace/video_app

请使用已配置的 MCP 工具按以下流程执行：

### Phase 1: 环境准备与 APK 解码
使用 APKTool MCP Server：
1. 调用 `health_check` 确认服务状态
2. 调用 `decode_apk` 解码 APK 到工作目录
3. 调用 `analyze_project_structure` 获取项目整体分析
4. 调用 `get_workspace_info` 确认工作空间状态

### Phase 2: 基础信息提取
...

### Phase 6: 清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**
```

### 示例 2：去除某工具 APP 广告

```
请对以下 APK 进行全面的逆向工程分析，目标是广告去除。

APK 路径: E:/A_java/samples/tool_app.apk
工作目录: E:/A_java/workspace/tool_app

该 APP 启动页有全屏广告，使用时有横幅广告和插屏广告。

请使用已配置的 MCP 工具按以下流程执行：

### Phase 1: 环境准备与 APK 解码
...

### Phase 6: 清理并关闭 MCP 工具
1. 调用 `clean_project` 清理临时文件（可选）
2. **关闭 MCP 工具连接**
```

---

## MCP 工具快速参考

### APKTool MCP Server 可用工具

| 工具名 | 用途 |
|--------|------|
| `health_check` | 检查服务状态 |
| `decode_apk` | 解码 APK 文件 |
| `build_apk` | 构建 APK 文件 |
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

### JADX MCP Server 可用工具（需要配合 JADX-GUI）

| 工具名 | 用途 |
|--------|------|
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
| `get_xrefs_to_class` | 查找类的交叉引用 |
| `get_xrefs_to_method` | 查找方法的交叉引用 |

---

## 注意事项

1. **法律合规**：本提示词仅供学习研究使用，请确保你有合法权限分析目标 APK
2. **安全风险**：修改后的 APK 可能存在安全隐患，请谨慎安装使用
3. **技术限制**：部分高级加固方案可能需要更专业的脱壳工具和技术
4. **动态分析**：静态分析有局限，复杂逻辑可能需要结合动态调试
5. **MCP 连接**：使用前请确保 MCP Server 已正确启动并连接
6. **资源清理**：分析完成后记得关闭 MCP 工具连接，释放资源

---

## 推荐工具链

| 用途 | 工具 | 路径/说明 |
|------|------|-----------|
| APK 解码/编码 | APKTool MCP Server | `java/apktool-mcp-server/` |
| Java 代码分析 | JADX MCP Server | `java/jadx-mcp-server/` |
| 图形化反编译 | JADX-GUI | `java/jadx-gui/jadx-gui-1.5.5.exe` |
| Smali 编辑 | VS Code + Smali 插件 | 推荐编辑器 |
| 动态调试 | Android Studio、Frida | 配合真机/模拟器 |
| 抓包分析 | Charles Proxy、Burp Suite | 网络请求拦截 |
| 签名工具 | apksigner、jarsigner | Android SDK 自带 |
| 加固识别 | ApkScan-PKID、易盾在线检测 | 在线工具 |
