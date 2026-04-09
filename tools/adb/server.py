# /// script
# requires-python = ">=3.10"
# dependencies = [ "fastmcp", "logging", "argparse" ]
# ///

"""
ADB MCP Server - Android Debug Bridge MCP Server
通过 MCP 协议提供 ADB 功能的远程调用接口
"""

import logging
import subprocess
import os
import argparse
import json
import time
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from fastmcp import FastMCP

# 设置日志配置
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 控制台日志处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# 解析命令行参数
parser = argparse.ArgumentParser("ADB MCP Server")
parser.add_argument("--http", help="通过 HTTP 流模式运行 MCP Server", action="store_true", default=False)
parser.add_argument("--port", help="指定 HTTP 模式运行的端口号 (默认:8653)", default=8653, type=int)
parser.add_argument("--adb-path", help="adb.exe 的完整路径", default=None, type=str)
args = parser.parse_args()

# 初始化 MCP Server
mcp = FastMCP("ADB-MCP Server")

# ADB 可执行文件路径
DEFAULT_ADB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adb.exe")
ADB_EXECUTABLE = args.adb_path if args.adb_path else DEFAULT_ADB_PATH

# 验证 ADB 路径是否存在
if not os.path.exists(ADB_EXECUTABLE):
    logger.warning(f"ADB 可执行文件未找到: {ADB_EXECUTABLE}")
    ADB_EXECUTABLE = "adb"  # 尝试使用系统 PATH 中的 adb


def run_adb_command(
    command_args: List[str],
    device_id: Optional[str] = None,
    timeout: int = 60,
    shell: bool = False
) -> Dict[str, Any]:
    """
    执行 ADB 命令并返回统一格式的结果
    
    参数:
        command_args: ADB 命令参数列表
        device_id: 目标设备 ID (可选)
        timeout: 命令超时时间(秒)
        shell: 是否使用 shell 模式执行
        
    返回:
        包含执行结果的字典: {"success": bool, ...}
    """
    try:
        # 构建完整命令
        cmd = [ADB_EXECUTABLE]
        
        # 如果指定了设备，添加 -s 参数
        if device_id:
            cmd.extend(["-s", device_id])
        
        # 添加子命令
        cmd.extend(command_args)
        
        logger.info(f"执行 ADB 命令: {' '.join(cmd)}")
        
        # 执行命令
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
            shell=shell
        )
        
        # 构建返回结果
        response = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": " ".join(cmd)
        }
        
        # 如果执行失败，添加错误信息
        if result.returncode != 0:
            response["error"] = result.stderr.strip() if result.stderr else f"命令执行失败，返回码: {result.returncode}"
            logger.error(f"ADB 命令执行失败: {response['error']}")
        else:
            logger.info(f"ADB 命令执行成功")
            
        return response
        
    except subprocess.TimeoutExpired:
        logger.error(f"ADB 命令执行超时 ({timeout}秒)")
        return {
            "success": False,
            "error": f"命令执行超时 ({timeout}秒)",
            "command": " ".join(cmd) if 'cmd' in dir() else "unknown"
        }
        
    except FileNotFoundError:
        logger.error(f"ADB 可执行文件未找到: {ADB_EXECUTABLE}")
        return {
            "success": False,
            "error": f"ADB 可执行文件未找到: {ADB_EXECUTABLE}",
            "adb_path": ADB_EXECUTABLE
        }
        
    except Exception as e:
        logger.error(f"执行 ADB 命令时发生异常: {str(e)}")
        return {
            "success": False,
            "error": f"执行异常: {str(e)}",
            "command": " ".join(cmd) if 'cmd' in dir() else "unknown"
        }


# ==================== 设备管理工具 ====================

@mcp.tool()
async def list_devices() -> Dict[str, Any]:
    """
    列出所有已连接的 Android 设备
    
    返回:
        包含设备列表的字典
    """
    result = run_adb_command(["devices", "-l"])
    
    if not result["success"]:
        return result
    
    # 解析设备列表
    devices = []
    lines = result["stdout"].strip().split("\n")
    
    # 跳过第一行 "List of devices attached"
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
            
        parts = line.split()
        if len(parts) < 2:
            continue
            
        device_id = parts[0]
        status = parts[1]
        
        # 解析额外信息
        device_info = {"id": device_id, "status": status}
        
        # 解析 product, model, device 等信息
        for part in parts[2:]:
            if ":" in part:
                key, value = part.split(":", 1)
                device_info[key] = value
                
        devices.append(device_info)
    
    result["devices"] = devices
    result["count"] = len(devices)
    
    return result


@mcp.tool()
async def get_device_info(device_id: str) -> Dict[str, Any]:
    """
    获取指定设备的详细信息
    
    参数:
        device_id: 设备 ID
        
    返回:
        包含设备详细信息的字典
    """
    if not device_id:
        return {"success": False, "error": "设备 ID 不能为空"}
    
    # 获取多项设备信息
    info_commands = {
        "android_version": ["shell", "getprop", "ro.build.version.release"],
        "sdk_version": ["shell", "getprop", "ro.build.version.sdk"],
        "device_model": ["shell", "getprop", "ro.product.model"],
        "device_brand": ["shell", "getprop", "ro.product.brand"],
        "device_manufacturer": ["shell", "getprop", "ro.product.manufacturer"],
        "device_product": ["shell", "getprop", "ro.product.name"],
        "device_serial": ["shell", "getprop", "ro.serialno"],
        "build_fingerprint": ["shell", "getprop", "ro.build.fingerprint"],
        "screen_density": ["shell", "wm", "density"],
        "screen_size": ["shell", "wm", "size"]
    }
    
    device_info = {
        "device_id": device_id,
        "timestamp": time.time()
    }
    
    errors = []
    
    for key, cmd_args in info_commands.items():
        result = run_adb_command(cmd_args, device_id=device_id)
        if result["success"]:
            device_info[key] = result["stdout"].strip()
        else:
            device_info[key] = None
            errors.append(f"{key}: {result.get('error', 'unknown error')}")
    
    # 获取电池信息
    battery_result = run_adb_command(["shell", "dumpsys", "battery"], device_id=device_id)
    if battery_result["success"]:
        battery_info = parse_battery_info(battery_result["stdout"])
        device_info["battery"] = battery_info
    
    # 获取内存信息
    mem_result = run_adb_command(["shell", "cat", "/proc/meminfo"], device_id=device_id)
    if mem_result["success"]:
        mem_info = parse_meminfo(mem_result["stdout"])
        device_info["memory"] = mem_info
    
    device_info["success"] = len(errors) < len(info_commands)
    if errors:
        device_info["partial_errors"] = errors
    
    return device_info


def parse_battery_info(battery_output: str) -> Dict[str, Any]:
    """解析电池信息输出"""
    battery_info = {}
    
    for line in battery_output.split("\n"):
        line = line.strip()
        if "level:" in line:
            battery_info["level"] = int(line.split(":")[1].strip())
        elif "scale:" in line:
            battery_info["scale"] = int(line.split(":")[1].strip())
        elif "status:" in line:
            battery_info["status"] = line.split(":")[1].strip()
        elif "health:" in line:
            battery_info["health"] = line.split(":")[1].strip()
        elif "present:" in line:
            battery_info["present"] = line.split(":")[1].strip() == "true"
        elif "technology:" in line:
            battery_info["technology"] = line.split(":")[1].strip()
    
    return battery_info


def parse_meminfo(meminfo_output: str) -> Dict[str, Any]:
    """解析内存信息输出"""
    mem_info = {}
    
    for line in meminfo_output.split("\n"):
        line = line.strip()
        if ":" in line:
            key_value = line.split(":", 1)
            key = key_value[0].strip()
            value = key_value[1].strip().split()[0] if len(key_value) > 1 else "0"
            try:
                mem_info[key] = int(value)
            except ValueError:
                mem_info[key] = value
    
    return mem_info


# ==================== APK 安装/卸载工具 ====================

@mcp.tool()
async def install_apk(
    apk_path: str,
    device_id: Optional[str] = None,
    reinstall: bool = False,
    downgrade: bool = False,
    grant_permissions: bool = False
) -> Dict[str, Any]:
    """
    在设备上安装 APK 文件
    
    参数:
        apk_path: APK 文件路径
        device_id: 目标设备 ID (可选，未指定则使用第一个可用设备)
        reinstall: 是否重新安装 (保留数据)
        downgrade: 是否允许降级安装
        grant_permissions: 是否自动授予所有权限
        
    返回:
        包含安装结果的字典
    """
    # 验证 APK 文件路径
    if not apk_path or not os.path.exists(apk_path):
        return {"success": False, "error": f"APK 文件不存在: {apk_path}"}
    
    if not apk_path.lower().endswith(".apk"):
        return {"success": False, "error": "文件必须是 .apk 格式"}
    
    # 构建安装命令
    cmd_args = ["install"]
    
    if reinstall:
        cmd_args.append("-r")
    if downgrade:
        cmd_args.append("-d")
    if grant_permissions:
        cmd_args.append("-g")
    
    cmd_args.append(apk_path)
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=120)
    
    # 解析安装结果
    if result["success"]:
        output = result["stdout"].strip()
        if "Success" in output:
            result["installed"] = True
            result["message"] = "APK 安装成功"
        else:
            result["installed"] = False
            result["message"] = output
    else:
        result["installed"] = False
        # 提取常见错误信息
        error_patterns = {
            "INSTALL_FAILED_ALREADY_EXISTS": "应用已存在，请使用 reinstall 参数",
            "INSTALL_FAILED_VERSION_DOWNGRADE": "版本降级被拒绝，请使用 downgrade 参数",
            "INSTALL_FAILED_INVALID_APK": "APK 文件无效",
            "INSTALL_FAILED_INSUFFICIENT_STORAGE": "设备存储空间不足",
            "INSTALL_PARSE_FAILED": "APK 解析失败",
            "INSTALL_FAILED_USER_RESTRICTED": "用户限制安装"
        }
        
        for pattern, message in error_patterns.items():
            if pattern in result.get("stderr", "") or pattern in result.get("stdout", ""):
                result["error_detail"] = message
                break
    
    return result


@mcp.tool()
async def uninstall_package(
    package_name: str,
    device_id: Optional[str] = None,
    keep_data: bool = False
) -> Dict[str, Any]:
    """
    卸载设备上的应用包
    
    参数:
        package_name: 应用包名 (如: com.example.app)
        device_id: 目标设备 ID (可选)
        keep_data: 是否保留应用数据
        
    返回:
        包含卸载结果的字典
    """
    if not package_name:
        return {"success": False, "error": "包名不能为空"}
    
    # 验证包名格式
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$', package_name):
        return {"success": False, "error": "包名格式无效"}
    
    # 构建卸载命令
    cmd_args = ["uninstall"]
    if keep_data:
        cmd_args.append("-k")
    cmd_args.append(package_name)
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=60)
    
    # 解析卸载结果
    if result["success"]:
        output = result["stdout"].strip()
        if "Success" in output:
            result["uninstalled"] = True
            result["message"] = f"包 {package_name} 卸载成功"
        else:
            result["uninstalled"] = False
            result["message"] = output
    else:
        result["uninstalled"] = False
        # 解析常见错误
        if "DELETE_FAILED_INTERNAL_ERROR" in result.get("stderr", ""):
            result["error_detail"] = "系统应用无法卸载"
        elif "Unknown package" in result.get("stdout", ""):
            result["error_detail"] = "包不存在"
    
    return result


@mcp.tool()
async def get_package_info(package_name: str, device_id: Optional[str] = None) -> Dict[str, Any]:
    """
    获取应用包的详细信息
    
    参数:
        package_name: 应用包名
        device_id: 目标设备 ID (可选)
        
    返回:
        包含包详细信息的字典
    """
    if not package_name:
        return {"success": False, "error": "包名不能为空"}
    
    # 获取包信息
    result = run_adb_command(
        ["shell", "dumpsys", "package", package_name],
        device_id=device_id,
        timeout=30
    )
    
    if not result["success"]:
        # 检查包是否存在
        if "Unable to find package" in result.get("stdout", ""):
            return {"success": False, "error": f"包 {package_name} 不存在"}
        return result
    
    output = result["stdout"]
    
    # 解析包信息
    package_info = {
        "package_name": package_name,
        "version_name": None,
        "version_code": None,
        "target_sdk": None,
        "min_sdk": None,
        "install_time": None,
        "update_time": None,
        "permissions": [],
        "activities": [],
        "services": [],
        "receivers": []
    }
    
    lines = output.split("\n")
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        # 解析版本信息
        if "versionName=" in line:
            match = re.search(r'versionName=([^\s]+)', line)
            if match:
                package_info["version_name"] = match.group(1)
        
        if "versionCode=" in line:
            match = re.search(r'versionCode=(\d+)', line)
            if match:
                package_info["version_code"] = int(match.group(1))
        
        # 解析 SDK 版本
        if "targetSdk=" in line:
            match = re.search(r'targetSdk=(\d+)', line)
            if match:
                package_info["target_sdk"] = int(match.group(1))
        
        if "minSdk=" in line:
            match = re.search(r'minSdk=(\d+)', line)
            if match:
                package_info["min_sdk"] = int(match.group(1))
        
        # 解析安装时间
        if "firstInstallTime=" in line:
            match = re.search(r'firstInstallTime=([\d-]+ [\d:]+)', line)
            if match:
                package_info["install_time"] = match.group(1)
        
        if "lastUpdateTime=" in line:
            match = re.search(r'lastUpdateTime=([\d-]+ [\d:]+)', line)
            if match:
                package_info["update_time"] = match.group(1)
        
        # 解析权限
        if "requested permissions:" in line.lower():
            current_section = "permissions"
            continue
        
        # 解析组件
        if "activity" in line.lower() and "{" in line:
            match = re.search(r'([a-zA-Z0-9._]+)/([a-zA-Z0-9._]+)', line)
            if match:
                package_info["activities"].append(match.group(2))
        
        if "service" in line.lower() and "{" in line:
            match = re.search(r'([a-zA-Z0-9._]+)/([a-zA-Z0-9._]+)', line)
            if match:
                package_info["services"].append(match.group(2))
        
        if "receiver" in line.lower() and "{" in line:
            match = re.search(r'([a-zA-Z0-9._]+)/([a-zA-Z0-9._]+)', line)
            if match:
                package_info["receivers"].append(match.group(2))
        
        # 收集权限
        if current_section == "permissions" and line.startswith("android.permission."):
            package_info["permissions"].append(line.split()[0])
    
    result["package_info"] = package_info
    result["success"] = True
    
    return result


# ==================== 日志和 Shell 工具 ====================

@mcp.tool()
async def get_logcat(
    device_id: Optional[str] = None,
    package_name: Optional[str] = None,
    log_level: Optional[str] = None,
    max_lines: int = 100,
    filter_pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取设备日志 (logcat)
    
    参数:
        device_id: 目标设备 ID (可选)
        package_name: 过滤特定应用的日志 (可选)
        log_level: 日志级别过滤 (V/D/I/W/E/F)
        max_lines: 最大返回行数
        filter_pattern: 正则过滤模式 (可选)
        
    返回:
        包含日志内容的字典
    """
    # 构建 logcat 命令
    cmd_args = ["logcat", "-d", "-t", str(max_lines)]
    
    # 添加日志级别过滤
    if log_level and log_level.upper() in ["V", "D", "I", "W", "E", "F"]:
        cmd_args.extend(["*:" + log_level.upper()])
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=30)
    
    if not result["success"]:
        return result
    
    # 解析日志行
    log_lines = result["stdout"].strip().split("\n")
    filtered_logs = []
    
    for line in log_lines:
        # 如果指定了包名，过滤相关日志
        if package_name and package_name not in line:
            continue
        
        # 如果指定了过滤模式
        if filter_pattern:
            try:
                if not re.search(filter_pattern, line):
                    continue
            except re.error:
                pass
        
        filtered_logs.append(line)
    
    result["logs"] = filtered_logs
    result["total_lines"] = len(log_lines)
    result["filtered_lines"] = len(filtered_logs)
    result["max_lines_requested"] = max_lines
    
    return result


@mcp.tool()
async def clear_logcat(device_id: Optional[str] = None) -> Dict[str, Any]:
    """
    清除设备日志缓冲区
    
    参数:
        device_id: 目标设备 ID (可选)
        
    返回:
        包含清除结果的字典
    """
    result = run_adb_command(["logcat", "-c"], device_id=device_id, timeout=10)
    
    if result["success"]:
        result["message"] = "日志缓冲区已清除"
        result["cleared"] = True
    else:
        result["cleared"] = False
    
    return result


@mcp.tool()
async def execute_shell(
    command: str,
    device_id: Optional[str] = None,
    timeout: int = 30,
    root: bool = False
) -> Dict[str, Any]:
    """
    在设备上执行 shell 命令
    
    参数:
        command: 要执行的 shell 命令
        device_id: 目标设备 ID (可选)
        timeout: 命令超时时间(秒)
        root: 是否以 root 权限执行
        
    返回:
        包含执行结果的字典
    """
    if not command:
        return {"success": False, "error": "命令不能为空"}
    
    # 构建 shell 命令
    cmd_args = ["shell"]
    if root:
        cmd_args.append("su -c")
    cmd_args.append(command)
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=timeout)
    
    return result


# ==================== 文件传输和截图工具 ====================

@mcp.tool()
async def push_file(
    local_path: str,
    remote_path: str,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    将本地文件推送到设备
    
    参数:
        local_path: 本地文件路径
        remote_path: 设备上的目标路径
        device_id: 目标设备 ID (可选)
        
    返回:
        包含推送结果的字典
    """
    # 验证本地文件
    if not local_path or not os.path.exists(local_path):
        return {"success": False, "error": f"本地文件不存在: {local_path}"}
    
    if not remote_path:
        return {"success": False, "error": "远程路径不能为空"}
    
    # 构建 push 命令
    cmd_args = ["push", local_path, remote_path]
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=120)
    
    if result["success"]:
        # 解析传输结果
        output = result["stdout"].strip()
        if "pushed" in output or "1 file pushed" in output:
            result["pushed"] = True
            result["message"] = f"文件已推送到 {remote_path}"
            
            # 尝试解析传输速度
            speed_match = re.search(r'(\d+\.?\d*) MB/s', output)
            if speed_match:
                result["transfer_speed"] = float(speed_match.group(1))
        else:
            result["pushed"] = False
            result["message"] = output
    else:
        result["pushed"] = False
    
    return result


@mcp.tool()
async def pull_file(
    remote_path: str,
    local_path: str,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    从设备拉取文件到本地
    
    参数:
        remote_path: 设备上的文件路径
        local_path: 本地保存路径
        device_id: 目标设备 ID (可选)
        
    返回:
        包含拉取结果的字典
    """
    if not remote_path:
        return {"success": False, "error": "远程路径不能为空"}
    
    if not local_path:
        return {"success": False, "error": "本地路径不能为空"}
    
    # 确保本地目录存在
    local_dir = os.path.dirname(local_path)
    if local_dir and not os.path.exists(local_dir):
        try:
            os.makedirs(local_dir, exist_ok=True)
        except Exception as e:
            return {"success": False, "error": f"无法创建本地目录: {str(e)}"}
    
    # 构建 pull 命令
    cmd_args = ["pull", remote_path, local_path]
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=120)
    
    if result["success"]:
        output = result["stdout"].strip()
        if "pulled" in output or "1 file pulled" in output:
            result["pulled"] = True
            result["message"] = f"文件已拉取到 {local_path}"
            
            # 获取文件大小
            if os.path.exists(local_path):
                result["file_size"] = os.path.getsize(local_path)
                
            # 尝试解析传输速度
            speed_match = re.search(r'(\d+\.?\d*) MB/s', output)
            if speed_match:
                result["transfer_speed"] = float(speed_match.group(1))
        else:
            result["pulled"] = False
            result["message"] = output
    else:
        result["pulled"] = False
        # 解析常见错误
        if "does not exist" in result.get("stderr", ""):
            result["error_detail"] = "远程文件不存在"
        elif "Permission denied" in result.get("stderr", ""):
            result["error_detail"] = "权限不足，无法访问文件"
    
    return result


@mcp.tool()
async def screenshot(
    local_path: Optional[str] = None,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    截取设备屏幕并保存到本地
    
    参数:
        local_path: 本地保存路径 (可选，默认保存到当前目录)
        device_id: 目标设备 ID (可选)
        
    返回:
        包含截图结果的字典
    """
    # 生成默认文件名
    if not local_path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        local_path = f"screenshot_{timestamp}.png"
    
    # 确保本地目录存在
    local_dir = os.path.dirname(local_path)
    if local_dir and not os.path.exists(local_dir):
        try:
            os.makedirs(local_dir, exist_ok=True)
        except Exception as e:
            return {"success": False, "error": f"无法创建本地目录: {str(e)}"}
    
    # 设备上的临时路径
    remote_path = "/sdcard/screenshot_temp.png"
    
    # 截图到设备
    screenshot_result = run_adb_command(
        ["shell", "screencap", "-p", remote_path],
        device_id=device_id,
        timeout=30
    )
    
    if not screenshot_result["success"]:
        return {
            "success": False,
            "error": "截图失败",
            "detail": screenshot_result.get("stderr", "unknown error")
        }
    
    # 拉取截图到本地
    pull_result = run_adb_command(
        ["pull", remote_path, local_path],
        device_id=device_id,
        timeout=30
    )
    
    if not pull_result["success"]:
        return {
            "success": False,
            "error": "拉取截图失败",
            "detail": pull_result.get("stderr", "unknown error")
        }
    
    # 删除设备上的临时文件
    run_adb_command(["shell", "rm", remote_path], device_id=device_id, timeout=10)
    
    # 获取截图信息
    result = {
        "success": True,
        "screenshot_path": local_path,
        "message": f"截图已保存到: {local_path}"
    }
    
    if os.path.exists(local_path):
        result["file_size"] = os.path.getsize(local_path)
    
    return result


# ==================== 应用包管理工具 ====================

@mcp.tool()
async def list_packages(
    device_id: Optional[str] = None,
    system_apps: bool = False,
    third_party_apps: bool = True,
    filter_pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    列出设备上安装的应用包
    
    参数:
        device_id: 目标设备 ID (可选)
        system_apps: 是否包含系统应用
        third_party_apps: 是否包含第三方应用
        filter_pattern: 包名过滤模式 (可选)
        
    返回:
        包含应用包列表的字典
    """
    # 构建 list packages 命令
    cmd_args = ["shell", "pm", "list", "packages"]
    
    if third_party_apps and not system_apps:
        cmd_args.append("-3")
    elif system_apps and not third_party_apps:
        cmd_args.append("-s")
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=30)
    
    if not result["success"]:
        return result
    
    # 解析包列表
    packages = []
    lines = result["stdout"].strip().split("\n")
    
    for line in lines:
        line = line.strip()
        if line.startswith("package:"):
            package_name = line.replace("package:", "").strip()
            
            # 应用过滤模式
            if filter_pattern:
                try:
                    if not re.search(filter_pattern, package_name, re.IGNORECASE):
                        continue
                except re.error:
                    pass
            
            packages.append(package_name)
    
    packages.sort()
    
    result["packages"] = packages
    result["count"] = len(packages)
    result["system_apps_included"] = system_apps
    result["third_party_apps_included"] = third_party_apps
    
    return result


@mcp.tool()
async def start_activity(
    component: str,
    device_id: Optional[str] = None,
    action: Optional[str] = None,
    data: Optional[str] = None,
    extras: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    启动应用的 Activity
    
    参数:
        component: 组件名 (如: com.example.app/.MainActivity)
        device_id: 目标设备 ID (可选)
        action: Intent action (可选)
        data: Intent data URI (可选)
        extras: Intent extras 字典 (可选)
        
    返回:
        包含启动结果的字典
    """
    if not component:
        return {"success": False, "error": "组件名不能为空"}
    
    # 构建 am start 命令
    cmd_args = ["shell", "am", "start", "-n", component]
    
    if action:
        cmd_args.extend(["-a", action])
    
    if data:
        cmd_args.extend(["-d", data])
    
    if extras:
        for key, value in extras.items():
            cmd_args.extend(["-e", key, value])
    
    result = run_adb_command(cmd_args, device_id=device_id, timeout=30)
    
    if result["success"]:
        output = result["stdout"].strip()
        if "Starting" in output or "Error" not in output:
            result["started"] = True
            result["message"] = f"Activity 已启动: {component}"
        else:
            result["started"] = False
            result["message"] = output
    else:
        result["started"] = False
        # 解析常见错误
        if "does not exist" in result.get("stderr", ""):
            result["error_detail"] = "组件不存在"
        elif "SecurityException" in result.get("stderr", ""):
            result["error_detail"] = "权限不足，无法启动组件"
    
    return result


@mcp.tool()
async def force_stop_package(
    package_name: str,
    device_id: Optional[str] = None,
    clear_data: bool = False
) -> Dict[str, Any]:
    """
    强制停止应用包
    
    参数:
        package_name: 应用包名
        device_id: 目标设备 ID (可选)
        clear_data: 是否同时清除应用数据
        
    返回:
        包含停止结果的字典
    """
    if not package_name:
        return {"success": False, "error": "包名不能为空"}
    
    results = {
        "package_name": package_name,
        "stopped": False,
        "data_cleared": False
    }
    
    # 强制停止应用
    stop_result = run_adb_command(
        ["shell", "am", "force-stop", package_name],
        device_id=device_id,
        timeout=30
    )
    
    if stop_result["success"]:
        results["stopped"] = True
        results["stop_message"] = f"应用 {package_name} 已强制停止"
    else:
        results["stop_error"] = stop_result.get("stderr", "unknown error")
    
    # 如果需要清除数据
    if clear_data:
        clear_result = run_adb_command(
            ["shell", "pm", "clear", package_name],
            device_id=device_id,
            timeout=30
        )
        
        if clear_result["success"] and "Success" in clear_result.get("stdout", ""):
            results["data_cleared"] = True
            results["clear_message"] = f"应用 {package_name} 数据已清除"
        else:
            results["clear_error"] = clear_result.get("stderr", "unknown error")
    
    results["success"] = results["stopped"]
    
    return results


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    检查 ADB MCP Server 和 ADB 安装状态
    
    返回:
        包含服务器状态和 ADB 可用性的字典
    """
    result = {
        "server_status": "running",
        "adb_path": ADB_EXECUTABLE,
        "adb_exists": os.path.exists(ADB_EXECUTABLE),
        "timestamp": time.time()
    }
    
    # 检查 ADB 版本
    version_result = run_adb_command(["version"], timeout=10)
    
    if version_result["success"]:
        result["adb_available"] = True
        result["adb_version"] = version_result["stdout"].strip()
    else:
        result["adb_available"] = False
        result["adb_error"] = version_result.get("error", "unknown error")
    
    # 检查已连接设备
    devices_result = await list_devices()
    if devices_result["success"]:
        result["connected_devices"] = devices_result.get("count", 0)
        result["devices"] = devices_result.get("devices", [])
    
    logger.info("ADB MCP Server: 健康检查完成")
    
    return result


def main():
    """主函数 - 启动 ADB MCP Server"""
    print("=" * 80)
    print("ADB MCP Server")
    print("Android Debug Bridge MCP Server")
    print("=" * 80)
    print()
    
    # 显示配置信息
    print("配置信息:")
    print(f"  ADB 路径: {ADB_EXECUTABLE}")
    print(f"  ADB 存在: {'是' if os.path.exists(ADB_EXECUTABLE) else '否'}")
    print(f"  HTTP 模式: {'启用' if args.http else '禁用'}")
    if args.http:
        print(f"  HTTP 端口: {args.port}")
    print()
    
    # 执行初始健康检查
    print("执行初始健康检查...")
    try:
        import asyncio
        health_result = asyncio.run(health_check())
        
        if health_result.get("server_status") == "running":
            print("服务器状态: 运行中")
        else:
            print("服务器状态: 异常")
        
        if health_result.get("adb_available"):
            print(f"ADB 可用: {health_result.get('adb_version', '版本未知')}")
        else:
            print("ADB 不可用")
            print(f"错误: {health_result.get('adb_error', '未知错误')}")
        
        connected_devices = health_result.get("connected_devices", 0)
        print(f"已连接设备数: {connected_devices}")
        
        if connected_devices > 0:
            print("已连接设备列表:")
            for device in health_result.get("devices", []):
                device_id = device.get("id", "unknown")
                status = device.get("status", "unknown")
                model = device.get("model", "unknown")
                print(f"  - {device_id} ({status}) - {model}")
        
    except Exception as e:
        print(f"健康检查失败: {e}")
    
    print()
    print("可用的 MCP 工具:")
    tools = [
        "health_check", "list_devices", "get_device_info",
        "install_apk", "uninstall_package", "get_package_info",
        "get_logcat", "execute_shell", "clear_logcat",
        "push_file", "pull_file", "screenshot",
        "list_packages", "start_activity", "force_stop_package"
    ]
    
    for i, tool in enumerate(tools, 1):
        print(f"  {i:2d}. {tool}")
    
    print()
    print("启动 MCP Server...")
    
    if args.http:
        print(f"服务器地址: http://127.0.0.1:{args.port}")
        mcp.run(transport="streamable-http", port=args.port)
    else:
        print("服务器运行在 stdio 模式")
        mcp.run()


if __name__ == "__main__":
    main()
