# -*- coding: utf-8 -*-
"""
Frida MCP Server - 基于 FastMCP 的 Frida 动态插桩服务

功能模块：
1. 进程管理：列出、附加、启动进程
2. 脚本注入：向目标进程注入 JavaScript 代码
3. 函数 Hook：Hook 指定类的方法，捕获参数和返回值
4. 网络拦截：拦截 HTTP/HTTPS 请求和响应
5. 内存扫描：扫描进程内存中的特定模式

依赖安装：
    pip install -r requirements.txt

运行方式：
    python frida_mcp_server.py

注意：
    - 需要设备上运行 frida-server
    - Windows 下需要管理员权限运行
"""

import json
import threading
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import frida
from fastmcp import FastMCP


# ==================== 全局配置 ====================

# 创建 FastMCP 实例
mcp = FastMCP("FridaMCPServer")

# 会话管理器（线程安全）
class SessionManager:
    """
    Frida 会话管理器
    
    管理所有活动的 Frida 会话，提供线程安全的操作接口
    """
    
    def __init__(self):
        self._sessions: Dict[str, frida.core.Session] = {}
        self._scripts: Dict[str, frida.core.Script] = {}
        self._lock = threading.RLock()
        self._message_handlers: Dict[str, List[Dict]] = {}
    
    def add_session(self, session_id: str, session: frida.core.Session) -> None:
        """
        添加会话
        
        参数：
            session_id: 会话唯一标识
            session: Frida 会话对象
        """
        with self._lock:
            self._sessions[session_id] = session
            self._message_handlers[session_id] = []
    
    def get_session(self, session_id: str) -> Optional[frida.core.Session]:
        """
        获取会话
        
        参数：
            session_id: 会话唯一标识
            
        返回：
            Frida 会话对象，不存在则返回 None
        """
        with self._lock:
            return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> None:
        """
        移除会话并清理资源
        
        参数：
            session_id: 会话唯一标识
        """
        with self._lock:
            if session_id in self._scripts:
                try:
                    self._scripts[session_id].unload()
                except Exception:
                    pass
                del self._scripts[session_id]
            
            if session_id in self._sessions:
                try:
                    self._sessions[session_id].detach()
                except Exception:
                    pass
                del self._sessions[session_id]
            
            if session_id in self._message_handlers:
                del self._message_handlers[session_id]
    
    def add_script(self, session_id: str, script: frida.core.Script) -> None:
        """
        添加脚本到会话
        
        参数：
            session_id: 会话唯一标识
            script: Frida 脚本对象
        """
        with self._lock:
            if session_id in self._scripts:
                try:
                    self._scripts[session_id].unload()
                except Exception:
                    pass
            self._scripts[session_id] = script
    
    def get_script(self, session_id: str) -> Optional[frida.core.Script]:
        """
        获取会话的脚本
        
        参数：
            session_id: 会话唯一标识
            
        返回：
            Frida 脚本对象，不存在则返回 None
        """
        with self._lock:
            return self._scripts.get(session_id)
    
    def add_message(self, session_id: str, message: Dict) -> None:
        """
        添加消息到会话的消息队列
        
        参数：
            session_id: 会话唯一标识
            message: 消息字典
        """
        with self._lock:
            if session_id in self._message_handlers:
                self._message_handlers[session_id].append({
                    "timestamp": time.time(),
                    "data": message
                })
    
    def get_messages(self, session_id: str, clear: bool = True) -> List[Dict]:
        """
        获取会话的消息队列
        
        参数：
            session_id: 会话唯一标识
            clear: 是否清空消息队列
            
        返回：
            消息列表
        """
        with self._lock:
            messages = self._message_handlers.get(session_id, [])
            result = [m["data"] for m in messages]
            if clear:
                self._message_handlers[session_id] = []
            return result
    
    def list_sessions(self) -> List[str]:
        """
        获取所有会话ID列表
        
        返回：
            会话ID列表
        """
        with self._lock:
            return list(self._sessions.keys())


# 全局会话管理器实例
session_manager = SessionManager()


# ==================== 工具函数 ====================

def create_success_response(data: Any = None, message: str = "操作成功") -> Dict:
    """
    创建成功响应
    
    参数：
        data: 响应数据
        message: 成功消息
        
    返回：
        统一格式的成功响应字典
    """
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response


def create_error_response(error: str, code: int = 500) -> Dict:
    """
    创建错误响应
    
    参数：
        error: 错误信息
        code: 错误代码
        
    返回：
        统一格式的错误响应字典
    """
    return {
        "success": False,
        "error": error,
        "code": code
    }


def check_frida_server() -> Optional[str]:
    """
    检查 frida-server 是否可用
    
    返回：
        错误信息，如果正常则返回 None
    """
    try:
        device = frida.get_local_device()
        if device is None:
            return "无法获取本地设备"
        return None
    except frida.ServerNotRunningError:
        return "frida-server 未运行，请先启动 frida-server"
    except frida.TransportError:
        return "无法连接到 frida-server，请检查设备连接"
    except Exception as e:
        return f"Frida 设备检查失败: {str(e)}"


def get_device(device_type: str = "local") -> frida.core.Device:
    """
    获取 Frida 设备
    
    参数：
        device_type: 设备类型 (local/usb/remote)
        
    返回：
        Frida 设备对象
        
    异常：
        设备获取失败时抛出异常
    """
    if device_type == "local":
        return frida.get_local_device()
    if device_type == "usb":
        return frida.get_usb_device()
    if device_type == "remote":
        return frida.get_remote_device()
    return frida.get_local_device()


# ==================== MCP 工具函数 ====================

@mcp.tool()
def list_processes(device_type: str = "local") -> Dict:
    """
    列出设备上所有运行的进程
    
    参数：
        device_type: 设备类型 (local/usb/remote)，默认 local
        
    返回：
        包含进程列表的响应字典
        
    示例：
        {"success": true, "data": [{"pid": 1234, "name": "com.example.app"}]}
    """
    error = check_frida_server()
    if error:
        return create_error_response(error, 503)
    
    try:
        device = get_device(device_type)
        processes = device.enumerate_processes()
        
        process_list = []
        for proc in processes:
            process_list.append({
                "pid": proc.pid,
                "name": proc.name,
                "parameters": proc.parameters if hasattr(proc, 'parameters') else {}
            })
        
        process_list.sort(key=lambda x: x["pid"])
        return create_success_response(process_list, f"共找到 {len(process_list)} 个进程")
    
    except frida.ServerNotRunningError:
        return create_error_response("frida-server 未运行，请先启动 frida-server", 503)
    except Exception as e:
        return create_error_response(f"获取进程列表失败: {str(e)}", 500)


@mcp.tool()
def attach_process(target: Union[str, int], device_type: str = "local") -> Dict:
    """
    附加到指定进程
    
    参数：
        target: 进程名或进程ID (PID)
        device_type: 设备类型 (local/usb/remote)，默认 local
        
    返回：
        包含会话ID的响应字典
        
    示例：
        {"success": true, "data": {"session_id": "sess_abc123"}}
    """
    error = check_frida_server()
    if error:
        return create_error_response(error, 503)
    
    try:
        device = get_device(device_type)
        
        # 尝试附加到进程
        if isinstance(target, int) or target.isdigit():
            pid = int(target)
            session = device.attach(pid)
        else:
            session = device.attach(target)
        
        # 生成会话ID
        session_id = f"sess_{id(session)}_{int(time.time())}"
        
        # 存储会话
        session_manager.add_session(session_id, session)
        
        # 设置消息处理器
        def on_message(message, data):
            session_manager.add_message(session_id, {
                "type": "message",
                "payload": message,
                "data": data.hex() if data else None
            })
        
        session.on("detached", lambda reason: session_manager.remove_session(session_id))
        
        return create_success_response({
            "session_id": session_id,
            "pid": session._impl.pid if hasattr(session._impl, 'pid') else None
        }, "进程附加成功")
    
    except frida.ProcessNotFoundError:
        return create_error_response(f"进程未找到: {target}", 404)
    except frida.PermissionDeniedError:
        return create_error_response("权限不足，请以管理员/root权限运行", 403)
    except frida.ServerNotRunningError:
        return create_error_response("frida-server 未运行，请先启动 frida-server", 503)
    except Exception as e:
        return create_error_response(f"附加进程失败: {str(e)}", 500)


@mcp.tool()
def spawn_process(program: str, args: Optional[List[str]] = None, 
                  device_type: str = "local") -> Dict:
    """
    启动新进程并附加
    
    参数：
        program: 要启动的程序路径
        args: 程序参数列表
        device_type: 设备类型 (local/usb/remote)，默认 local
        
    返回：
        包含会话ID和PID的响应字典
        
    示例：
        {"success": true, "data": {"session_id": "sess_abc123", "pid": 5678}}
    """
    error = check_frida_server()
    if error:
        return create_error_response(error, 503)
    
    try:
        device = get_device(device_type)
        
        # 启动进程
        argv = [program]
        if args:
            argv.extend(args)
        
        pid = device.spawn(argv)
        session = device.attach(pid)
        
        # 生成会话ID
        session_id = f"sess_{id(session)}_{int(time.time())}"
        
        # 存储会话
        session_manager.add_session(session_id, session)
        
        # 设置分离回调
        session.on("detached", lambda reason: session_manager.remove_session(session_id))
        
        return create_success_response({
            "session_id": session_id,
            "pid": pid,
            "program": program
        }, "进程启动并附加成功")
    
    except frida.ExecutableNotFoundError:
        return create_error_response(f"可执行文件未找到: {program}", 404)
    except frida.PermissionDeniedError:
        return create_error_response("权限不足，请以管理员/root权限运行", 403)
    except frida.ServerNotRunningError:
        return create_error_response("frida-server 未运行，请先启动 frida-server", 503)
    except Exception as e:
        return create_error_response(f"启动进程失败: {str(e)}", 500)


@mcp.tool()
def resume_process(session_id: str) -> Dict:
    """
    恢复进程执行（用于 spawn 后）
    
    参数：
        session_id: 会话ID
        
    返回：
        操作结果响应字典
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    try:
        device = frida.get_local_device()
        pid = session._impl.pid if hasattr(session._impl, 'pid') else None
        if pid:
            device.resume(pid)
            return create_success_response(None, "进程已恢复执行")
        return create_error_response("无法获取进程ID", 500)
    except Exception as e:
        return create_error_response(f"恢复进程失败: {str(e)}", 500)


@mcp.tool()
def inject_script(session_id: str, script_code: str) -> Dict:
    """
    向目标进程注入 JavaScript 代码
    
    参数：
        session_id: 会话ID
        script_code: JavaScript 代码字符串
        
    返回：
        操作结果响应字典
        
    示例脚本：
        console.log("Hello from Frida!");
        var modules = Process.enumerateModules();
        console.log("Modules: " + modules.length);
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    try:
        # 创建脚本
        script = session.create_script(script_code)
        
        # 设置消息处理器
        def on_message(message, data):
            session_manager.add_message(session_id, {
                "type": "script_message",
                "payload": message,
                "data": data.hex() if data else None
            })
        
        script.on("message", on_message)
        
        # 加载脚本
        script.load()
        
        # 存储脚本
        session_manager.add_script(session_id, script)
        
        return create_success_response(None, "脚本注入成功")
    
    except frida.ScriptRuntimeError as e:
        return create_error_response(f"脚本运行时错误: {str(e)}", 400)
    except frida.ScriptLoadError as e:
        return create_error_response(f"脚本加载失败: {str(e)}", 400)
    except Exception as e:
        return create_error_response(f"脚本注入失败: {str(e)}", 500)


@mcp.tool()
def hook_function(session_id: str, class_name: str, method_name: str,
                  module_name: Optional[str] = None) -> Dict:
    """
    Hook 指定类的方法，捕获参数和返回值
    
    参数：
        session_id: 会话ID
        class_name: 类名（Android: com.example.Class, iOS: ClassName）
        method_name: 方法名
        module_name: 模块名（可选，用于定位特定库）
        
    返回：
        操作结果响应字典
        
    示例：
        hook_function("sess_123", "java.lang.String", "valueOf")
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    # 构建 Hook 脚本
    script_code = f"""
    (function() {{
        console.log("[*] Starting hook for {class_name}.{method_name}");
        
        var messages = [];
        
        function sendMessage(type, data) {{
            messages.push({{type: type, data: data, timestamp: Date.now()}});
            send({{type: type, data: data}});
        }}
        
        // Android Java Hook
        if (Java.available) {{
            Java.perform(function() {{
                try {{
                    var targetClass = Java.use("{class_name}");
                    var overloads = targetClass["{method_name}"].overloads;
                    
                    console.log("[*] Found " + overloads.length + " overloads");
                    
                    overloads.forEach(function(overload, index) {{
                        overload.implementation = function() {{
                            var args = Array.prototype.slice.call(arguments);
                            var argsStr = args.map(function(arg) {{
                                try {{
                                    return arg ? arg.toString() : "null";
                                }} catch(e) {{
                                    return "[object]";
                                }}
                            }}).join(", ");
                            
                            console.log("[+] {class_name}.{method_name}(" + argsStr + ")");
                            
                            var result = this["{method_name}"].apply(this, arguments);
                            
                            var resultStr = "null";
                            try {{
                                resultStr = result ? result.toString() : "null";
                            }} catch(e) {{
                                resultStr = "[object]";
                            }}
                            
                            console.log("[+] Return: " + resultStr);
                            
                            sendMessage("hook_call", {{
                                class: "{class_name}",
                                method: "{method_name}",
                                overload_index: index,
                                arguments: argsStr,
                                return_value: resultStr
                            }});
                            
                            return result;
                        }};
                    }});
                    
                    console.log("[*] Hook installed successfully");
                }} catch(e) {{
                    console.error("[-] Hook failed: " + e.message);
                    sendMessage("error", {{message: e.message}});
                }}
            }});
        }}
        
        // iOS Objective-C Hook
        if (ObjC.available) {{
            try {{
                var className = "{class_name}";
                var methodName = "{method_name}";
                
                var hook = ObjC.classes[className][methodName];
                Interceptor.attach(hook.implementation, {{
                    onEnter: function(args) {{
                        console.log("[+] " + className + " " + methodName);
                        this.className = className;
                        this.methodName = methodName;
                    }},
                    onLeave: function(retval) {{
                        console.log("[+] Return: " + retval);
                        sendMessage("hook_call", {{
                            class: className,
                            method: methodName,
                            return_value: retval.toString()
                        }});
                    }}
                }});
                
                console.log("[*] iOS Hook installed");
            }} catch(e) {{
                console.error("[-] iOS Hook failed: " + e.message);
            }}
        }}
        
        // Native Function Hook (通用)
        try {{
            var module = Process.findModuleByName("{module_name or ''}");
            if (module) {{
                console.log("[*] Module found: " + module.name);
            }}
        }} catch(e) {{
            // 忽略模块查找错误
        }}
        
        // 导出消息获取函数
        rpc.exports = {{
            getMessages: function() {{
                var result = messages;
                messages = [];
                return result;
            }}
        }};
    }})();
    """
    
    return inject_script(session_id, script_code)


@mcp.tool()
def intercept_network(session_id: str, filter_url: Optional[str] = None) -> Dict:
    """
    拦截 HTTP/HTTPS 请求和响应
    
    参数：
        session_id: 会话ID
        filter_url: URL过滤模式（可选，如 "api.example.com"）
        
    返回：
        操作结果响应字典
        
    说明：
        支持 Android (OkHttp/HttpURLConnection) 和 iOS (NSURLSession)
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    filter_pattern = filter_url or ""
    
    script_code = f"""
    (function() {{
        console.log("[*] Starting network interception");
        
        var filterPattern = "{filter_pattern}";
        
        function shouldIntercept(url) {{
            if (!filterPattern) return true;
            return url.indexOf(filterPattern) !== -1;
        }}
        
        function sendNetworkEvent(type, data) {{
            send({{
                type: "network_" + type,
                data: data,
                timestamp: Date.now()
            }});
        }}
        
        // Android OkHttp Hook
        if (Java.available) {{
            Java.perform(function() {{
                try {{
                    // Hook OkHttp RealCall
                    var RealCall = Java.use("okhttp3.RealCall");
                    if (RealCall) {{
                        RealCall.execute.implementation = function() {{
                            var request = this.request();
                            var url = request.url().toString();
                            
                            if (shouldIntercept(url)) {{
                                var headers = [];
                                var headerNames = request.headers().names().toArray();
                                for (var i = 0; i < headerNames.length; i++) {{
                                    headers.push({{
                                        name: headerNames[i],
                                        value: request.header(headerNames[i])
                                    }});
                                }}
                                
                                console.log("[HTTP Request] " + url);
                                
                                sendNetworkEvent("request", {{
                                    url: url,
                                    method: request.method(),
                                    headers: headers,
                                    source: "okhttp"
                                }});
                            }}
                            
                            var response = this.execute();
                            
                            if (shouldIntercept(url)) {{
                                console.log("[HTTP Response] " + response.code());
                                
                                sendNetworkEvent("response", {{
                                    url: url,
                                    status_code: response.code(),
                                    message: response.message(),
                                    source: "okhttp"
                                }});
                            }}
                            
                            return response;
                        }};
                    }}
                }} catch(e) {{
                    console.log("OkHttp hook skipped: " + e.message);
                }}
                
                // Hook HttpURLConnection
                try {{
                    var URL = Java.use("java.net.URL");
                    var HttpURLConnection = Java.use("java.net.HttpURLConnection");
                    
                    URL.openConnection.implementation = function() {{
                        var conn = this.openConnection();
                        var url = this.toString();
                        
                        if (shouldIntercept(url)) {{
                            console.log("[URLConnection] " + url);
                            sendNetworkEvent("request", {{
                                url: url,
                                method: "GET",
                                source: "HttpURLConnection"
                            }});
                        }}
                        
                        return conn;
                    }};
                }} catch(e) {{
                    console.log("HttpURLConnection hook skipped: " + e.message);
                }}
            }});
        }}
        
        // iOS NSURLSession Hook
        if (ObjC.available) {{
            try {{
                var NSURLSession = ObjC.classes.NSURLSession;
                var dataTaskWithRequest = NSURLSession["- dataTaskWithRequest:completionHandler:"];
                
                Interceptor.attach(dataTaskWithRequest.implementation, {{
                    onEnter: function(args) {{
                        var request = ObjC.Object(args[2]);
                        var url = request.URL().absoluteString().toString();
                        
                        if (shouldIntercept(url)) {{
                            console.log("[iOS HTTP] " + url);
                            sendNetworkEvent("request", {{
                                url: url,
                                method: request.HTTPMethod().toString(),
                                source: "NSURLSession"
                            }});
                        }}
                    }}
                }});
            }} catch(e) {{
                console.log("NSURLSession hook skipped: " + e.message);
            }}
        }}
        
        // SSL Pinning Bypass (通用)
        try {{
            // 尝试绕过 SSL Pinning
            var modules = Process.enumerateModules();
            modules.forEach(function(module) {{
                // 查找常见的 SSL 验证函数
                var symbols = Module.enumerateExports(module.name);
                symbols.forEach(function(symbol) {{
                    if (symbol.name.indexOf("SSL") !== -1 || 
                        symbol.name.indexOf("verify") !== -1) {{
                        console.log("[SSL] Found: " + module.name + "!" + symbol.name);
                    }}
                }});
            }});
        }} catch(e) {{
            console.log("SSL enumeration skipped: " + e.message);
        }}
        
        console.log("[*] Network interception active");
    }})();
    """
    
    return inject_script(session_id, script_code)


@mcp.tool()
def scan_memory(session_id: str, pattern: str, 
                module_name: Optional[str] = None,
                protection: str = "r--") -> Dict:
    """
    扫描进程内存中的特定模式
    
    参数：
        session_id: 会话ID
        pattern: 内存模式（十六进制字符串，如 "48 89 5C 24 ??" 或 "hello"）
        module_name: 模块名（可选，限定扫描范围）
        protection: 内存保护标志（r=读, w=写, x=执行, -=无），默认 "r--"
        
    返回：
        包含扫描结果的响应字典
        
    示例：
        scan_memory("sess_123", "48 89 5C 24", "libtarget.so")
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    script_code = f"""
    (function() {{
        console.log("[*] Starting memory scan");
        
        var pattern = "{pattern}";
        var moduleName = "{module_name or ''}";
        var protection = "{protection}";
        var results = [];
        
        try {{
            var ranges = [];
            
            if (moduleName) {{
                // 扫描特定模块
                var module = Process.findModuleByName(moduleName);
                if (!module) {{
                    send({{
                        type: "scan_error",
                        error: "Module not found: " + moduleName
                    }});
                    return;
                }}
                ranges.push({{
                    base: module.base,
                    size: module.size
                }});
            }} else {{
                // 扫描所有符合条件的内存范围
                var allRanges = Process.enumerateRanges(protection);
                ranges = allRanges.map(function(r) {{
                    return {{base: r.base, size: r.size}};
                }});
            }}
            
            console.log("[*] Scanning " + ranges.length + " memory ranges");
            
            ranges.forEach(function(range) {{
                try {{
                    var matches = Memory.scanSync(range.base, range.size, pattern);
                    matches.forEach(function(match) {{
                        var address = match.address;
                        var size = match.size;
                        
                        // 尝试读取一些上下文数据
                        var context = null;
                        try {{
                            context = Memory.readByteArray(address, Math.min(size + 16, 64));
                        }} catch(e) {{
                            // 忽略读取错误
                        }}
                        
                        results.push({{
                            address: address.toString(),
                            size: size,
                            context: context ? HexDump.encode(context) : null
                        }});
                        
                        console.log("[+] Match at: " + address);
                    }});
                }} catch(e) {{
                    console.log("[-] Scan error in range: " + e.message);
                }}
            }});
            
            console.log("[*] Scan complete. Found " + results.length + " matches");
            
            send({{
                type: "scan_complete",
                pattern: pattern,
                matches_found: results.length,
                matches: results.slice(0, 100)  // 限制返回数量
            }});
            
        }} catch(e) {{
            console.error("[-] Memory scan failed: " + e.message);
            send({{
                type: "scan_error",
                error: e.message
            }});
        }}
        
        // 导出结果获取函数
        rpc.exports = {{
            getScanResults: function() {{
                return results;
            }}
        }};
    }})();
    """
    
    return inject_script(session_id, script_code)


@mcp.tool()
def read_memory(session_id: str, address: str, size: int) -> Dict:
    """
    读取进程内存数据
    
    参数：
        session_id: 会话ID
        address: 内存地址（十六进制字符串，如 "0x7fff1234000"）
        size: 读取字节数
        
    返回：
        包含内存数据的响应字典
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    script_code = f"""
    (function() {{
        var address = ptr("{address}");
        var size = {size};
        
        try {{
            var data = Memory.readByteArray(address, size);
            var hexStr = HexDump.encode(data);
            var utf8Str = null;
            
            try {{
                utf8Str = Memory.readUtf8String(address, size);
            }} catch(e) {{
                // 不是有效的 UTF-8 字符串
            }}
            
            send({{
                type: "memory_read",
                address: "{address}",
                size: size,
                hex: hexStr,
                utf8: utf8Str
            }});
            
            console.log("[+] Memory read: " + size + " bytes from " + address);
        }} catch(e) {{
            console.error("[-] Memory read failed: " + e.message);
            send({{
                type: "memory_error",
                error: e.message
            }});
        }}
    }})();
    """
    
    return inject_script(session_id, script_code)


@mcp.tool()
def write_memory(session_id: str, address: str, data: str,
                 data_type: str = "hex") -> Dict:
    """
    写入进程内存数据
    
    参数：
        session_id: 会话ID
        address: 内存地址（十六进制字符串）
        data: 要写入的数据
        data_type: 数据类型（hex/utf8/ascii），默认 hex
        
    返回：
        操作结果响应字典
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    script_code = f"""
    (function() {{
        var address = ptr("{address}");
        var data = "{data}";
        var dataType = "{data_type}";
        
        try {{
            if (dataType === "hex") {{
                var bytes = [];
                for (var i = 0; i < data.length; i += 2) {{
                    bytes.push(parseInt(data.substr(i, 2), 16));
                }}
                Memory.writeByteArray(address, bytes);
            }} else if (dataType === "utf8") {{
                Memory.writeUtf8String(address, data);
            }} else if (dataType === "ascii") {{
                Memory.writeAnsiString(address, data);
            }}
            
            send({{
                type: "memory_write",
                address: "{address}",
                bytes_written: data.length
            }});
            
            console.log("[+] Memory written: " + data.length + " bytes to " + address);
        }} catch(e) {{
            console.error("[-] Memory write failed: " + e.message);
            send({{
                type: "memory_error",
                error: e.message
            }});
        }}
    }})();
    """
    
    return inject_script(session_id, script_code)


@mcp.tool()
def get_messages(session_id: str, clear: bool = True) -> Dict:
    """
    获取会话的消息队列
    
    参数：
        session_id: 会话ID
        clear: 是否清空消息队列，默认 True
        
    返回：
        包含消息列表的响应字典
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    messages = session_manager.get_messages(session_id, clear)
    return create_success_response(messages, f"获取到 {len(messages)} 条消息")


@mcp.tool()
def detach_session(session_id: str) -> Dict:
    """
    分离会话
    
    参数：
        session_id: 会话ID
        
    返回：
        操作结果响应字典
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    try:
        session_manager.remove_session(session_id)
        return create_success_response(None, "会话已分离")
    except Exception as e:
        return create_error_response(f"分离会话失败: {str(e)}", 500)


@mcp.tool()
def list_sessions() -> Dict:
    """
    列出所有活动会话
    
    返回：
        包含会话ID列表的响应字典
    """
    sessions = session_manager.list_sessions()
    return create_success_response(sessions, f"共 {len(sessions)} 个活动会话")


@mcp.tool()
def enumerate_modules(session_id: str) -> Dict:
    """
    枚举进程加载的模块
    
    参数：
        session_id: 会话ID
        
    返回：
        包含模块列表的响应字典
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    script_code = """
    (function() {
        try {
            var modules = Process.enumerateModules();
            var result = modules.map(function(m) {
                return {
                    name: m.name,
                    base: m.base.toString(),
                    size: m.size,
                    path: m.path
                };
            });
            
            send({
                type: "modules",
                count: result.length,
                modules: result
            });
            
            console.log("[*] Found " + result.length + " modules");
        } catch(e) {
            console.error("[-] Module enumeration failed: " + e.message);
            send({
                type: "error",
                error: e.message
            });
        }
    })();
    """
    
    return inject_script(session_id, script_code)


@mcp.tool()
def enumerate_exports(session_id: str, module_name: str) -> Dict:
    """
    枚举模块的导出符号
    
    参数：
        session_id: 会话ID
        module_name: 模块名
        
    返回：
        包含导出符号列表的响应字典
    """
    session = session_manager.get_session(session_id)
    if not session:
        return create_error_response("会话不存在或已断开", 404)
    
    script_code = f"""
    (function() {{
        try {{
            var exports = Module.enumerateExports("{module_name}");
            var result = exports.map(function(e) {{
                return {{
                    name: e.name,
                    address: e.address.toString(),
                    type: e.type
                }};
            }});
            
            send({{
                type: "exports",
                module: "{module_name}",
                count: result.length,
                exports: result
            }});
            
            console.log("[*] Found " + result.length + " exports in {module_name}");
        }} catch(e) {{
            console.error("[-] Export enumeration failed: " + e.message);
            send({{
                type: "error",
                error: e.message
            }});
        }}
    }})();
    """
    
    return inject_script(session_id, script_code)


# ==================== 主程序入口 ====================

def main():
    """
    主程序入口
    
    启动 FastMCP 服务器
    """
    print("=" * 60)
    print("Frida MCP Server")
    print("=" * 60)
    print()
    
    # 检查 Frida 环境
    error = check_frida_server()
    if error:
        print(f"[!] 警告: {error}")
        print("[!] 某些功能可能无法使用")
    else:
        print("[+] Frida 环境检查通过")
    
    print()
    print("可用工具:")
    print("  - list_processes: 列出所有进程")
    print("  - attach_process: 附加到进程")
    print("  - spawn_process: 启动并附加进程")
    print("  - inject_script: 注入 JavaScript 脚本")
    print("  - hook_function: Hook 函数调用")
    print("  - intercept_network: 拦截网络请求")
    print("  - scan_memory: 扫描内存")
    print("  - read_memory: 读取内存")
    print("  - write_memory: 写入内存")
    print("  - enumerate_modules: 枚举模块")
    print("  - enumerate_exports: 枚举导出符号")
    print("  - get_messages: 获取消息")
    print("  - detach_session: 分离会话")
    print("  - list_sessions: 列出会话")
    print()
    print("=" * 60)
    
    # 启动 MCP 服务器
    mcp.run()


if __name__ == "__main__":
    main()
