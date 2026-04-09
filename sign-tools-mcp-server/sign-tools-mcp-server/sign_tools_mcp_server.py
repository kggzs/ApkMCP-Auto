# /// script
# requires-python = ">=3.10"
# dependencies = [ "fastmcp", "logging", "argparse" ]
# ///

"""
Sign Tools MCP Server
APK 签名工具 MCP 服务器

功能：
- 密钥库管理（生成、列表、信息查询）
- APK 签名（支持 V1/V2/V3）
- 签名验证
- zipalign 对齐优化

作者：AI Assistant
"""

import logging
import subprocess
import os
import argparse
import json
import time
from typing import List, Union, Dict, Optional
from pathlib import Path
from fastmcp import FastMCP

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 控制台日志处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# 解析命令行参数
parser = argparse.ArgumentParser("Sign Tools MCP Server")
parser.add_argument("--http", help="通过 HTTP 流提供 MCP 服务", action="store_true", default=False)
parser.add_argument("--port", help="指定 --http 模式下的端口号（默认:8653）", default=8653, type=int)
parser.add_argument("--workspace", help="指定工作目录", default="workspace", type=str)
parser.add_argument("--java-home", help="指定 Java 主目录（包含 keytool 和 apksigner）", default=None, type=str)
parser.add_argument("--timeout", help="命令执行超时时间（秒）", default=300, type=int)
args = parser.parse_args()

# 初始化 MCP 服务器
mcp = FastMCP("Sign-Tools-MCP Server")

# 工作目录配置
WORKSPACE_DIR = os.environ.get("SIGN_TOOLS_WORKSPACE", args.workspace)
KEYSTORE_DIR = os.path.join(WORKSPACE_DIR, "keystores")
DEFAULT_TIMEOUT = args.timeout

# Java 工具路径配置
JAVA_HOME = args.java_home
KEYTOOL_PATH = None
APKSIGNER_PATH = None
ZIPALIGN_PATH = None


def init_java_paths():
    """
    初始化 Java 工具路径
    
    优先使用用户指定的 Java 路径，否则尝试自动检测
    """
    global KEYTOOL_PATH, APKSIGNER_PATH, ZIPALIGN_PATH, JAVA_HOME
    
    # 如果指定了 Java 主目录
    if JAVA_HOME and os.path.exists(JAVA_HOME):
        bin_dir = os.path.join(JAVA_HOME, "bin")
        KEYTOOL_PATH = os.path.join(bin_dir, "keytool.exe" if os.name == 'nt' else "keytool")
        
        # apksigner 可能在 build-tools 中
        possible_apksigner_paths = [
            os.path.join(bin_dir, "apksigner.bat" if os.name == 'nt' else "apksigner"),
            os.path.join(JAVA_HOME, "..", "build-tools", "apksigner.bat" if os.name == 'nt' else "apksigner"),
        ]
        for path in possible_apksigner_paths:
            if os.path.exists(path):
                APKSIGNER_PATH = path
                break
        
        # zipalign 路径
        possible_zipalign_paths = [
            os.path.join(bin_dir, "zipalign.exe" if os.name == 'nt' else "zipalign"),
            os.path.join(JAVA_HOME, "..", "build-tools", "zipalign.exe" if os.name == 'nt' else "zipalign"),
        ]
        for path in possible_zipalign_paths:
            if os.path.exists(path):
                ZIPALIGN_PATH = path
                break
    
    # 尝试使用系统环境变量中的工具
    if not KEYTOOL_PATH or not os.path.exists(KEYTOOL_PATH):
        KEYTOOL_PATH = "keytool"
    if not APKSIGNER_PATH or not os.path.exists(APKSIGNER_PATH):
        APKSIGNER_PATH = "apksigner"
    if not ZIPALIGN_PATH or not os.path.exists(ZIPALIGN_PATH):
        ZIPALIGN_PATH = "zipalign"
    
    logger.info(f"Java 工具路径: keytool={KEYTOOL_PATH}, apksigner={APKSIGNER_PATH}, zipalign={ZIPALIGN_PATH}")


# 初始化 Java 路径
init_java_paths()

# 确保工作目录存在
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(KEYSTORE_DIR, exist_ok=True)


def run_command(command: List[str], timeout: int = DEFAULT_TIMEOUT, cwd: Optional[str] = None,
                input_data: Optional[str] = None) -> Dict[str, Union[str, int, bool]]:
    """
    执行命令并返回结果
    
    参数:
        command: 命令及参数列表
        timeout: 超时时间（秒）
        cwd: 工作目录
        input_data: 输入数据（用于交互式命令）
        
    返回:
        包含执行结果的字典
    """
    try:
        logger.info(f"执行命令: {' '.join(command)}")
        
        # 输入验证
        if not command or not all(isinstance(arg, str) for arg in command):
            return {
                "success": False,
                "error": "无效的命令格式"
            }
        
        # 准备输入数据
        stdin = subprocess.PIPE if input_data else None
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,  # 不抛出异常，我们自己处理返回码
            timeout=timeout,
            cwd=cwd,
            input=input_data
        )
        
        # keytool 和 apksigner 的返回码 0 表示成功
        success = result.returncode == 0
        
        if success:
            logger.info(f"命令执行成功，返回码: {result.returncode}")
        else:
            logger.warning(f"命令执行失败，返回码: {result.returncode}")
        
        return {
            "success": success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": " ".join(command)
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"命令执行超时（{timeout}秒）")
        return {
            "success": False,
            "error": f"命令执行超时（{timeout}秒）",
            "command": " ".join(command)
        }
        
    except FileNotFoundError as e:
        logger.error(f"命令未找到: {e}")
        return {
            "success": False,
            "error": f"命令未找到: {command[0]}",
            "command": " ".join(command)
        }
        
    except Exception as e:
        logger.error(f"执行命令时发生错误: {str(e)}")
        return {
            "success": False,
            "error": f"执行错误: {str(e)}",
            "command": " ".join(command)
        }


def validate_keystore_name(name: str) -> Dict[str, Union[bool, str]]:
    """
    验证密钥库名称是否合法
    
    参数:
        name: 密钥库名称
        
    返回:
        验证结果字典
    """
    if not name or not isinstance(name, str):
        return {"valid": False, "error": "密钥库名称不能为空"}
    
    # 检查非法字符
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        if char in name:
            return {"valid": False, "error": f"密钥库名称包含非法字符: {char}"}
    
    # 检查长度
    if len(name) > 255:
        return {"valid": False, "error": "密钥库名称过长（最大255字符）"}
    
    return {"valid": True}


def validate_apk_path(apk_path: str) -> Dict[str, Union[bool, str]]:
    """
    验证 APK 文件路径
    
    参数:
        apk_path: APK 文件路径
        
    返回:
        验证结果字典
    """
    if not apk_path or not isinstance(apk_path, str):
        return {"valid": False, "error": "APK 路径不能为空"}
    
    if not os.path.exists(apk_path):
        return {"valid": False, "error": f"APK 文件不存在: {apk_path}"}
    
    if not apk_path.lower().endswith('.apk'):
        return {"valid": False, "error": "文件必须是 .apk 格式"}
    
    return {"valid": True}


@mcp.tool()
async def health_check() -> Dict:
    """
    检查 Sign Tools MCP 服务器和工具的健康状态
    
    返回:
        包含服务器状态和各工具可用性的字典
    """
    try:
        result = {
            "server_status": "running",
            "workspace_dir": WORKSPACE_DIR,
            "keystore_dir": KEYSTORE_DIR,
            "workspace_exists": os.path.exists(WORKSPACE_DIR),
            "keystore_dir_exists": os.path.exists(KEYSTORE_DIR),
            "timestamp": time.time(),
            "tools": {}
        }
        
        # 检查 keytool
        keytool_result = run_command([KEYTOOL_PATH, "-help"], timeout=10)
        result["tools"]["keytool"] = {
            "available": keytool_result["success"],
            "path": KEYTOOL_PATH
        }
        if not keytool_result["success"]:
            result["tools"]["keytool"]["error"] = keytool_result.get("error", "未知错误")
        
        # 检查 apksigner
        apksigner_result = run_command([APKSIGNER_PATH, "--help"], timeout=10)
        result["tools"]["apksigner"] = {
            "available": apksigner_result["success"],
            "path": APKSIGNER_PATH
        }
        if not apksigner_result["success"]:
            result["tools"]["apksigner"]["error"] = apksigner_result.get("error", "未知错误")
        
        # 检查 zipalign
        zipalign_result = run_command([ZIPALIGN_PATH, "-h"], timeout=10)
        result["tools"]["zipalign"] = {
            "available": zipalign_result["success"],
            "path": ZIPALIGN_PATH
        }
        if not zipalign_result["success"]:
            result["tools"]["zipalign"]["error"] = zipalign_result.get("error", "未知错误")
        
        # 统计密钥库数量
        try:
            keystore_count = len([f for f in os.listdir(KEYSTORE_DIR) if f.endswith('.jks') or f.endswith('.keystore')])
            result["keystore_count"] = keystore_count
        except Exception as e:
            result["keystore_count"] = 0
            result["keystore_error"] = str(e)
        
        logger.info("Sign Tools MCP Server: 健康检查完成")
        return result
        
    except Exception as e:
        logger.error(f"健康检查错误: {str(e)}")
        return {
            "server_status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


@mcp.tool()
async def generate_keystore(
    alias: str,
    keystore_name: Optional[str] = None,
    password: Optional[str] = None,
    keyalg: str = "RSA",
    keysize: int = 2048,
    validity: int = 3650,
    dname_cn: str = "Unknown",
    dname_ou: str = "Unknown",
    dname_o: str = "Unknown",
    dname_l: str = "Unknown",
    dname_st: str = "Unknown",
    dname_c: str = "CN"
) -> Dict:
    """
    生成新的密钥库（Keystore）
    
    参数:
        alias: 密钥别名（必填）
        keystore_name: 密钥库文件名（可选，默认为 alias.jks）
        password: 密钥库和密钥密码（可选，默认随机生成）
        keyalg: 密钥算法（默认 RSA）
        keysize: 密钥长度（默认 2048）
        validity: 有效期（天，默认 3650 即 10 年）
        dname_cn: 常用名（CN）
        dname_ou: 组织单位（OU）
        dname_o: 组织（O）
        dname_l: 城市/地区（L）
        dname_st: 省份（ST）
        dname_c: 国家代码（C，默认 CN）
        
    返回:
        包含生成结果的字典
    """
    # 验证别名
    if not alias or not isinstance(alias, str):
        return {"success": False, "error": "密钥别名不能为空"}
    
    # 生成密钥库名称
    if not keystore_name:
        keystore_name = f"{alias}.jks"
    
    # 确保扩展名正确
    if not keystore_name.endswith(('.jks', '.keystore')):
        keystore_name += ".jks"
    
    # 验证密钥库名称
    name_validation = validate_keystore_name(keystore_name)
    if not name_validation["valid"]:
        return {"success": False, "error": name_validation["error"]}
    
    # 生成密码（如果未提供）
    generated_password = False
    if not password:
        import secrets
        password = secrets.token_urlsafe(16)
        generated_password = True
    
    # 构建密钥库路径
    keystore_path = os.path.join(KEYSTORE_DIR, keystore_name)
    
    # 检查是否已存在
    if os.path.exists(keystore_path):
        return {
            "success": False,
            "error": f"密钥库已存在: {keystore_name}",
            "keystore_path": keystore_path
        }
    
    # 构建 Distinguished Name
    dname = f"CN={dname_cn}, OU={dname_ou}, O={dname_o}, L={dname_l}, ST={dname_st}, C={dname_c}"
    
    # 构建 keytool 命令
    command = [
        KEYTOOL_PATH,
        "-genkeypair",
        "-alias", alias,
        "-keyalg", keyalg,
        "-keysize", str(keysize),
        "-validity", str(validity),
        "-keystore", keystore_path,
        "-dname", dname,
        "-storepass", password,
        "-keypass", password
    ]
    
    result = run_command(command, timeout=60)
    
    if result["success"]:
        result["keystore_name"] = keystore_name
        result["keystore_path"] = keystore_path
        result["alias"] = alias
        result["password"] = password if generated_password else "[用户提供的密码]"
        result["password_generated"] = generated_password
        result["keyalg"] = keyalg
        result["keysize"] = keysize
        result["validity_days"] = validity
        result["dname"] = dname
        result["message"] = f"密钥库 '{keystore_name}' 创建成功"
    
    return result


@mcp.tool()
async def list_keystores() -> Dict:
    """
    列出所有密钥库文件
    
    返回:
        包含密钥库列表的字典
    """
    try:
        keystores = []
        
        if not os.path.exists(KEYSTORE_DIR):
            return {
                "success": False,
                "error": f"密钥库目录不存在: {KEYSTORE_DIR}",
                "keystores": []
            }
        
        for filename in os.listdir(KEYSTORE_DIR):
            if filename.endswith(('.jks', '.keystore', '.p12', '.pfx')):
                file_path = os.path.join(KEYSTORE_DIR, filename)
                try:
                    stat = os.stat(file_path)
                    keystores.append({
                        "name": filename,
                        "path": file_path,
                        "size": stat.st_size,
                        "created_time": stat.st_ctime,
                        "modified_time": stat.st_mtime
                    })
                except Exception as e:
                    logger.warning(f"获取密钥库信息失败 {filename}: {e}")
        
        # 按修改时间排序（最新的在前）
        keystores.sort(key=lambda x: x["modified_time"], reverse=True)
        
        return {
            "success": True,
            "keystores": keystores,
            "count": len(keystores),
            "keystore_dir": KEYSTORE_DIR
        }
        
    except Exception as e:
        logger.error(f"列出密钥库时发生错误: {str(e)}")
        return {
            "success": False,
            "error": f"列出密钥库失败: {str(e)}",
            "keystores": []
        }


@mcp.tool()
async def get_keystore_info(keystore_name: str, password: str) -> Dict:
    """
    获取密钥库的详细信息
    
    参数:
        keystore_name: 密钥库文件名
        password: 密钥库密码
        
    返回:
        包含密钥库详细信息的字典
    """
    # 验证密钥库名称
    name_validation = validate_keystore_name(keystore_name)
    if not name_validation["valid"]:
        return {"success": False, "error": name_validation["error"]}
    
    # 构建密钥库路径
    keystore_path = os.path.join(KEYSTORE_DIR, keystore_name)
    
    if not os.path.exists(keystore_path):
        return {
            "success": False,
            "error": f"密钥库不存在: {keystore_name}",
            "keystore_path": keystore_path
        }
    
    # 获取密钥库列表信息
    list_command = [
        KEYTOOL_PATH,
        "-list",
        "-keystore", keystore_path,
        "-storepass", password,
        "-v"  # 详细输出
    ]
    
    list_result = run_command(list_command, timeout=30)
    
    if not list_result["success"]:
        # 可能是密码错误
        if "password" in list_result.get("stderr", "").lower() or list_result.get("returncode") == 1:
            return {
                "success": False,
                "error": "密钥库密码错误",
                "keystore_name": keystore_name
            }
        return {
            "success": False,
            "error": f"获取密钥库信息失败: {list_result.get('stderr', '未知错误')}",
            "keystore_name": keystore_name
        }
    
    # 解析输出
    output = list_result.get("stdout", "")
    
    # 提取基本信息
    info = {
        "keystore_name": keystore_name,
        "keystore_path": keystore_path,
        "keystore_type": None,
        "entries": []
    }
    
    lines = output.split('\n')
    current_entry = None
    
    for line in lines:
        line = line.strip()
        
        # 提取密钥库类型
        if line.startswith("Keystore type:"):
            info["keystore_type"] = line.split(":", 1)[1].strip()
        
        # 提取密钥库提供者
        if line.startswith("Keystore provider:"):
            info["keystore_provider"] = line.split(":", 1)[1].strip()
        
        # 新条目开始
        if line.startswith("Alias name:"):
            if current_entry:
                info["entries"].append(current_entry)
            current_entry = {
                "alias": line.split(":", 1)[1].strip()
            }
        
        # 提取条目信息
        if current_entry:
            if line.startswith("Creation date:"):
                current_entry["creation_date"] = line.split(":", 1)[1].strip()
            elif line.startswith("Entry type:"):
                current_entry["entry_type"] = line.split(":", 1)[1].strip()
            elif line.startswith("Owner:"):
                current_entry["owner"] = line.split(":", 1)[1].strip()
            elif line.startswith("Issuer:"):
                current_entry["issuer"] = line.split(":", 1)[1].strip()
            elif line.startswith("Serial number:"):
                current_entry["serial_number"] = line.split(":", 1)[1].strip()
            elif line.startswith("Valid from:"):
                current_entry["valid_from"] = line.split(":", 1)[1].strip()
            elif line.startswith("Certificate fingerprints:"):
                current_entry["fingerprints"] = {}
            elif "fingerprints" in current_entry and line.startswith("SHA1:"):
                current_entry["fingerprints"]["sha1"] = line.split(":", 1)[1].strip()
            elif "fingerprints" in current_entry and line.startswith("SHA256:"):
                current_entry["fingerprints"]["sha256"] = line.split(":", 1)[1].strip()
    
    # 添加最后一个条目
    if current_entry:
        info["entries"].append(current_entry)
    
    info["entry_count"] = len(info["entries"])
    
    return {
        "success": True,
        "keystore_info": info,
        "raw_output": output
    }


@mcp.tool()
async def sign_apk(
    apk_path: str,
    keystore_name: str,
    keystore_password: str,
    key_alias: str,
    key_password: Optional[str] = None,
    output_apk: Optional[str] = None,
    sign_v1: bool = True,
    sign_v2: bool = True,
    sign_v3: bool = False,
    min_sdk_version: Optional[int] = None
) -> Dict:
    """
    对 APK 文件进行签名
    
    参数:
        apk_path: 待签名的 APK 文件路径
        keystore_name: 密钥库文件名
        keystore_password: 密钥库密码
        key_alias: 密钥别名
        key_password: 密钥密码（如果与密钥库密码不同）
        output_apk: 输出 APK 路径（可选，默认覆盖原文件）
        sign_v1: 是否使用 V1 签名（JAR 签名）
        sign_v2: 是否使用 V2 签名（APK 签名方案 v2）
        sign_v3: 是否使用 V3 签名（APK 签名方案 v3）
        min_sdk_version: 最小 SDK 版本（可选）
        
    返回:
        包含签名结果的字典
    """
    # 验证 APK 路径
    apk_validation = validate_apk_path(apk_path)
    if not apk_validation["valid"]:
        return {"success": False, "error": apk_validation["error"]}
    
    # 验证密钥库
    name_validation = validate_keystore_name(keystore_name)
    if not name_validation["valid"]:
        return {"success": False, "error": name_validation["error"]}
    
    keystore_path = os.path.join(KEYSTORE_DIR, keystore_name)
    if not os.path.exists(keystore_path):
        return {
            "success": False,
            "error": f"密钥库不存在: {keystore_name}",
            "keystore_path": keystore_path
        }
    
    # 如果未指定密钥密码，使用密钥库密码
    if not key_password:
        key_password = keystore_password
    
    # 确定输出路径
    if output_apk:
        output_path = output_apk
    else:
        # 默认覆盖原文件
        output_path = apk_path
    
    # 如果输出路径与原路径不同，先复制文件
    temp_apk = None
    if output_path != apk_path:
        import shutil
        try:
            shutil.copy2(apk_path, output_path)
        except Exception as e:
            return {
                "success": False,
                "error": f"复制 APK 文件失败: {str(e)}"
            }
    
    # 构建 apksigner 命令
    command = [
        APKSIGNER_PATH,
        "sign",
        "--ks", keystore_path,
        "--ks-pass", f"pass:{keystore_password}",
        "--ks-key-alias", key_alias,
        "--key-pass", f"pass:{key_password}"
    ]
    
    # 添加签名版本选项
    if not sign_v1:
        command.append("--v1-signing-enabled=false")
    if not sign_v2:
        command.append("--v2-signing-enabled=false")
    if sign_v3:
        command.append("--v3-signing-enabled=true")
    
    # 添加最小 SDK 版本
    if min_sdk_version:
        command.extend(["--min-sdk-version", str(min_sdk_version)])
    
    # 添加输出路径
    command.append(output_path)
    
    result = run_command(command, timeout=120)
    
    # 添加额外信息到结果
    result["apk_path"] = apk_path
    result["output_apk"] = output_path
    result["keystore_name"] = keystore_name
    result["key_alias"] = key_alias
    result["sign_versions"] = {
        "v1": sign_v1,
        "v2": sign_v2,
        "v3": sign_v3
    }
    
    if result["success"]:
        # 获取签名后文件大小
        try:
            result["apk_size"] = os.path.getsize(output_path)
        except:
            pass
        result["message"] = "APK 签名成功"
    
    return result


@mcp.tool()
async def verify_signature(apk_path: str, verbose: bool = True) -> Dict:
    """
    验证 APK 的签名
    
    参数:
        apk_path: APK 文件路径
        verbose: 是否显示详细信息
        
    返回:
        包含验证结果的字典
    """
    # 验证 APK 路径
    apk_validation = validate_apk_path(apk_path)
    if not apk_validation["valid"]:
        return {"success": False, "error": apk_validation["error"]}
    
    # 构建 apksigner 验证命令
    command = [
        APKSIGNER_PATH,
        "verify"
    ]
    
    if verbose:
        command.append("-v")
    
    command.append(apk_path)
    
    result = run_command(command, timeout=60)
    
    result["apk_path"] = apk_path
    result["verified"] = result["success"]
    
    # 解析验证输出
    if result["success"] and verbose:
        output = result.get("stdout", "")
        
        # 提取签名信息
        signature_info = {
            "v1": False,
            "v2": False,
            "v3": False,
            "v4": False
        }
        
        for line in output.split('\n'):
            line = line.strip()
            if 'Verified using v1 scheme (JAR signing):' in line:
                signature_info["v1"] = 'true' in line.lower()
            elif 'Verified using v2 scheme (APK Signature Scheme v2):' in line:
                signature_info["v2"] = 'true' in line.lower()
            elif 'Verified using v3 scheme (APK Signature Scheme v3):' in line:
                signature_info["v3"] = 'true' in line.lower()
            elif 'Verified using v4 scheme (APK Signature Scheme v4):' in line:
                signature_info["v4"] = 'true' in line.lower()
        
        result["signature_info"] = signature_info
    
    return result


@mcp.tool()
async def zipalign_apk(
    apk_path: str,
    output_apk: Optional[str] = None,
    alignment: int = 4,
    verify_only: bool = False
) -> Dict:
    """
    对 APK 进行 zipalign 对齐优化
    
    zipalign 是 Android SDK 提供的工具，用于确保 APK 中未压缩数据
    在文件中的偏移量是 4 字节对齐的，这有助于减少内存使用。
    
    参数:
        apk_path: APK 文件路径
        output_apk: 输出 APK 路径（可选，默认覆盖原文件）
        alignment: 对齐字节数（默认 4，必须是 4 的倍数）
        verify_only: 仅验证对齐，不进行对齐操作
        
    返回:
        包含对齐结果的字典
    """
    # 验证 APK 路径
    apk_validation = validate_apk_path(apk_path)
    if not apk_validation["valid"]:
        return {"success": False, "error": apk_validation["error"]}
    
    # 验证对齐参数
    if alignment <= 0 or alignment % 4 != 0:
        return {
            "success": False,
            "error": "对齐字节数必须是 4 的正倍数"
        }
    
    if verify_only:
        # 仅验证对齐
        command = [
            ZIPALIGN_PATH,
            "-c",  # 检查对齐
            "-v",  # 详细输出
            str(alignment),
            apk_path
        ]
        
        result = run_command(command, timeout=60)
        result["apk_path"] = apk_path
        result["verify_only"] = True
        result["alignment"] = alignment
        
        # 解析验证结果
        if result["success"]:
            result["aligned"] = True
            result["message"] = "APK 已正确对齐"
        else:
            result["aligned"] = False
            result["message"] = "APK 未对齐或对齐不正确"
        
        return result
    
    # 执行对齐操作
    # 确定输出路径
    if output_apk:
        output_path = output_apk
    else:
        # 使用临时文件，然后替换原文件
        output_path = f"{apk_path}.aligned"
    
    command = [
        ZIPALIGN_PATH,
        "-f",  # 强制覆盖输出文件
        "-v",  # 详细输出
        str(alignment),
        apk_path,
        output_path
    ]
    
    result = run_command(command, timeout=120)
    
    result["apk_path"] = apk_path
    result["output_apk"] = output_path
    result["alignment"] = alignment
    result["verify_only"] = False
    
    if result["success"]:
        # 如果输出路径是临时文件，替换原文件
        if output_path == f"{apk_path}.aligned":
            try:
                import shutil
                shutil.move(output_path, apk_path)
                result["output_apk"] = apk_path
                result["message"] = "APK 对齐成功（已覆盖原文件）"
            except Exception as e:
                result["warning"] = f"对齐成功但替换原文件失败: {str(e)}"
        else:
            result["message"] = "APK 对齐成功"
        
        # 获取对齐后文件大小
        try:
            result["apk_size"] = os.path.getsize(result["output_apk"])
        except:
            pass
    
    return result


@mcp.tool()
async def delete_keystore(keystore_name: str) -> Dict:
    """
    删除密钥库文件
    
    参数:
        keystore_name: 密钥库文件名
        
    返回:
        包含删除结果的字典
    """
    # 验证密钥库名称
    name_validation = validate_keystore_name(keystore_name)
    if not name_validation["valid"]:
        return {"success": False, "error": name_validation["error"]}
    
    keystore_path = os.path.join(KEYSTORE_DIR, keystore_name)
    
    if not os.path.exists(keystore_path):
        return {
            "success": False,
            "error": f"密钥库不存在: {keystore_name}",
            "keystore_path": keystore_path
        }
    
    try:
        os.remove(keystore_path)
        return {
            "success": True,
            "message": f"密钥库 '{keystore_name}' 已删除",
            "keystore_name": keystore_name,
            "keystore_path": keystore_path
        }
    except Exception as e:
        logger.error(f"删除密钥库失败: {str(e)}")
        return {
            "success": False,
            "error": f"删除密钥库失败: {str(e)}",
            "keystore_name": keystore_name
        }


@mcp.tool()
async def get_workspace_info() -> Dict:
    """
    获取工作空间信息
    
    返回:
        包含工作空间信息的字典
    """
    try:
        info = {
            "workspace_dir": WORKSPACE_DIR,
            "keystore_dir": KEYSTORE_DIR,
            "workspace_exists": os.path.exists(WORKSPACE_DIR),
            "keystore_dir_exists": os.path.exists(KEYSTORE_DIR),
            "keystores": [],
            "keystore_count": 0,
            "total_keystore_size": 0
        }
        
        if os.path.exists(KEYSTORE_DIR):
            for filename in os.listdir(KEYSTORE_DIR):
                if filename.endswith(('.jks', '.keystore', '.p12', '.pfx')):
                    file_path = os.path.join(KEYSTORE_DIR, filename)
                    try:
                        stat = os.stat(file_path)
                        keystore_info = {
                            "name": filename,
                            "size": stat.st_size,
                            "modified_time": stat.st_mtime
                        }
                        info["keystores"].append(keystore_info)
                        info["total_keystore_size"] += stat.st_size
                    except Exception as e:
                        logger.warning(f"获取密钥库信息失败 {filename}: {e}")
            
            info["keystore_count"] = len(info["keystores"])
        
        # 获取磁盘空间信息
        try:
            import shutil
            total, used, free = shutil.disk_usage(WORKSPACE_DIR)
            info["disk_space"] = {
                "total": total,
                "used": used,
                "free": free
            }
        except Exception as e:
            logger.warning(f"获取磁盘空间信息失败: {e}")
        
        return {
            "success": True,
            "workspace_info": info
        }
        
    except Exception as e:
        logger.error(f"获取工作空间信息失败: {str(e)}")
        return {
            "success": False,
            "error": f"获取工作空间信息失败: {str(e)}"
        }


def main():
    """
    主函数，启动 MCP 服务器
    """
    print("=" * 80)
    print("Sign Tools MCP Server")
    print("APK 签名工具 MCP 服务器")
    print("=" * 80)
    print()
    
    # 显示配置信息
    print("配置信息:")
    print(f"  工作目录: {WORKSPACE_DIR}")
    print(f"  密钥库目录: {KEYSTORE_DIR}")
    print(f"  默认超时: {DEFAULT_TIMEOUT}秒")
    print(f"  HTTP 模式: {'启用' if args.http else '禁用'}")
    if args.http:
        print(f"  HTTP 端口: {args.port}")
    print(f"  keytool 路径: {KEYTOOL_PATH}")
    print(f"  apksigner 路径: {APKSIGNER_PATH}")
    print(f"  zipalign 路径: {ZIPALIGN_PATH}")
    print()
    
    # 执行健康检查
    print("正在执行健康检查...")
    try:
        import asyncio
        health_result = asyncio.run(health_check())
        
        if health_result.get("server_status") == "running":
            print("服务器状态: 运行中")
        else:
            print("服务器状态: 错误")
        
        # 显示工具状态
        tools = health_result.get("tools", {})
        for tool_name, tool_info in tools.items():
            status = "可用" if tool_info.get("available") else "不可用"
            print(f"  {tool_name}: {status}")
            if not tool_info.get("available") and "error" in tool_info:
                print(f"    错误: {tool_info['error']}")
        
        # 显示密钥库数量
        keystore_count = health_result.get("keystore_count", 0)
        print(f"  密钥库数量: {keystore_count}")
        
    except Exception as e:
        print(f"健康检查失败: {e}")
    
    print()
    print("可用的 MCP 工具:")
    tools = [
        "health_check", "generate_keystore", "list_keystores",
        "get_keystore_info", "delete_keystore", "sign_apk",
        "verify_signature", "zipalign_apk", "get_workspace_info"
    ]
    
    for i, tool in enumerate(tools, 1):
        print(f"  {i:2d}. {tool}")
    
    print()
    print("正在启动 MCP 服务器...")
    
    if args.http:
        print(f"服务器将在 http://127.0.0.1:{args.port} 上运行")
        mcp.run(transport="streamable-http", port=args.port)
    else:
        print("服务器在 stdio 模式下运行")
        mcp.run()


if __name__ == "__main__":
    main()
