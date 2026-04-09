# -*- coding: utf-8 -*-
"""
静态分析增强工具 MCP Server
提供 APK 静态分析功能，包括权限分析、字符串提取、URL/API 提取、SDK 识别
"""

import os
import re
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

from mcp.server.fastmcp import FastMCP

# 初始化 MCP Server
mcp = FastMCP("static-analyzer")


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class AnalysisResult:
    """统一分析结果格式"""
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


# =============================================================================
# 危险权限数据库
# =============================================================================

DANGEROUS_PERMISSIONS = {
    # 系统级危险权限
    "android.permission.READ_CALENDAR": "读取日历数据",
    "android.permission.WRITE_CALENDAR": "写入日历数据",
    "android.permission.CAMERA": "访问相机",
    "android.permission.READ_CONTACTS": "读取联系人",
    "android.permission.WRITE_CONTACTS": "写入联系人",
    "android.permission.GET_ACCOUNTS": "获取账户列表",
    "android.permission.ACCESS_FINE_LOCATION": "精确位置信息",
    "android.permission.ACCESS_COARSE_LOCATION": "粗略位置信息",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "后台位置访问",
    "android.permission.RECORD_AUDIO": "录音",
    "android.permission.READ_PHONE_STATE": "读取电话状态",
    "android.permission.READ_PHONE_NUMBERS": "读取电话号码",
    "android.permission.CALL_PHONE": "拨打电话",
    "android.permission.ANSWER_PHONE_CALLS": "接听电话",
    "android.permission.READ_CALL_LOG": "读取通话记录",
    "android.permission.WRITE_CALL_LOG": "写入通话记录",
    "android.permission.ADD_VOICEMAIL": "添加语音邮件",
    "android.permission.USE_SIP": "使用 SIP",
    "android.permission.PROCESS_OUTGOING_CALLS": "处理拨出电话",
    "android.permission.BODY_SENSORS": "访问身体传感器",
    "android.permission.ACTIVITY_RECOGNITION": "识别身体活动",
    "android.permission.SEND_SMS": "发送短信",
    "android.permission.RECEIVE_SMS": "接收短信",
    "android.permission.READ_SMS": "读取短信",
    "android.permission.RECEIVE_WAP_PUSH": "接收 WAP PUSH",
    "android.permission.RECEIVE_MMS": "接收彩信",
    "android.permission.READ_EXTERNAL_STORAGE": "读取外部存储",
    "android.permission.WRITE_EXTERNAL_STORAGE": "写入外部存储",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "管理外部存储",
    # 特殊权限
    "android.permission.SYSTEM_ALERT_WINDOW": "悬浮窗权限",
    "android.permission.WRITE_SETTINGS": "修改系统设置",
    "android.permission.REQUEST_INSTALL_PACKAGES": "安装应用",
    "android.permission.PACKAGE_USAGE_STATS": "应用使用情况统计",
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "无障碍服务",
    "android.permission.READ_PRIVILEGED_PHONE_STATE": "读取特权电话状态",
}


# =============================================================================
# SDK 特征数据库
# =============================================================================

SDK_PATTERNS = {
    # 广告 SDK
    "广告": {
        "packages": [
            "com.google.android.gms.ads",
            "com.google.android.gms.admob",
            "com.facebook.ads",
            "com.mopub",
            "com.inmobi",
            "com.chartboost.sdk",
            "com.applovin",
            "com.unity3d.ads",
            "com.vungle",
            "com.adcolony",
            "com.flurry.android",
            "com.millennialmedia",
            "com.smaato",
            "com.startapp",
            "com.appnext",
            "com.yandex.mobile.ads",
            "com.baidu.mobads",
            "com.qq.e.ads",
            "com.tencent.mm.opensdk",
            "com.umeng.ad",
            "com.gdt",
        ],
        "classes": [
            "AdView", "InterstitialAd", "RewardedAd", "BannerAd",
            "AdLoader", "AdRequest", "AdListener",
        ],
    },
    # 统计分析 SDK
    "统计": {
        "packages": [
            "com.google.firebase.analytics",
            "com.google.android.gms.analytics",
            "com.umeng.analytics",
            "com.umeng.commonsdk",
            "com.tencent.stat",
            "com.baidu.mobstat",
            "com.sensorsdata.analytics",
            "cn.thinkingdata.analytics",
            "com.growingio.android.sdk",
            "io.branch.sdk",
            "com.appsflyer",
            "com.adjust.sdk",
            "com.kochava.android.tracker",
            "com.talkingdata.sdk",
            "com.mixpanel.android",
            "com.amplitude.api",
            "com.segment.analytics",
            "com.flurry.sdk",
        ],
        "classes": [
            "Analytics", "Tracker", "EventBuilder", "UserProperties",
            "TrackEvent", "LogEvent", "onEvent",
        ],
    },
    # 社交 SDK
    "社交": {
        "packages": [
            "com.facebook",
            "com.twitter.sdk",
            "com.tencent.mm.opensdk",
            "com.sina.weibo.sdk",
            "com.tencent.mobileqq",
            "com.tencent.tauth",
            "com.twitter.android",
            "com.linkedin.android",
            "com.google.android.gms.plus",
            "com.vk.sdk",
            "com.linecorp",
            "com.kakao.sdk",
            "com.nhn.android",
            "com.snapchat.sdk",
            "com.instagram.android",
            "com.whatsapp",
            "com.telegram",
        ],
        "classes": [
            "ShareDialog", "LoginManager", "CallbackManager",
            "IWXAPI", "WBAPI", "TwitterAuthClient",
        ],
    },
    # 支付 SDK
    "支付": {
        "packages": [
            "com.alipay.sdk",
            "com.tencent.mm.opensdk",
            "com.unionpay",
            "com.google.android.gms.wallet",
            "com.paypal.android",
            "com.stripe.android",
            "com.braintreepayments",
            "com.adyen",
            "com.squareup.sdk",
            "com.payu",
            "com.razorpay",
            "com.paytm.pgsdk",
            "com.phonepe.sdk",
            "com.amazon.device.iap",
            "com.samsung.android.sdk.iap",
        ],
        "classes": [
            "PayTask", "PayReq", "PayResp", "Payment",
            "BillingClient", "BillingFlowParams", "Purchase",
        ],
    },
    # 推送 SDK
    "推送": {
        "packages": [
            "com.google.firebase.messaging",
            "com.huawei.hms.push",
            "com.xiaomi.push",
            "com.xiaomi.mipush",
            "com.meizu.cloud.push",
            "com.oppo.push",
            "com.vivo.push",
            "com.tencent.android.tpush",
            "cn.jpush.android",
            "com.getui",
            "com.igexin",
            "com.baidu.android.pushservice",
            "com.aliyun.ams.push",
            "com.amazon.device.messaging",
            "com.onesignal",
            "com.pusher.pushnotifications",
        ],
        "classes": [
            "FirebaseMessagingService", "PushMessageReceiver",
            "XMPushService", "PushManager",
        ],
    },
    # 地图 SDK
    "地图": {
        "packages": [
            "com.google.android.gms.maps",
            "com.amap.api",
            "com.baidu.mapapi",
            "com.tencent.tencentmap",
            "com.mapbox.mapboxsdk",
            "com.baidu.BaiduMap",
            "com.autonavi",
        ],
        "classes": [
            "GoogleMap", "MapView", "AMap", "BaiduMap",
            "MapFragment", "SupportMapFragment",
        ],
    },
    # 崩溃报告 SDK
    "崩溃报告": {
        "packages": [
            "com.google.firebase.crashlytics",
            "com.bugly",
            "com.tencent.bugly",
            "com.splunk.mint",
            "com.crittercism",
            "com.bugsense",
            "com.instabug",
            "io.fabric.sdk",
            "com.crashlytics.android",
            "com.microsoft.appcenter.crashes",
            "com.bugsnag",
            "com.sentry",
        ],
        "classes": [
            "Crashlytics", "CrashReport", "Bugly",
            "Instabug", "Sentry",
        ],
    },
}


# =============================================================================
# 工具函数
# =============================================================================

def is_apk_file(path: str) -> bool:
    """
    检查路径是否为 APK 文件

    Args:
        path: 文件路径

    Returns:
        是否为 APK 文件
    """
    return path.lower().endswith(".apk") and os.path.isfile(path)


def is_decoded_project(path: str) -> bool:
    """
    检查路径是否为已解码的项目目录

    Args:
        path: 目录路径

    Returns:
        是否为已解码的项目目录（包含 AndroidManifest.xml）
    """
    if not os.path.isdir(path):
        return False
    manifest_path = os.path.join(path, "AndroidManifest.xml")
    return os.path.isfile(manifest_path)


def extract_apk_manifest(apk_path: str, temp_dir: str) -> Optional[str]:
    """
    从 APK 文件中提取 AndroidManifest.xml

    Args:
        apk_path: APK 文件路径
        temp_dir: 临时目录路径

    Returns:
        解压后的 manifest 文件路径，失败返回 None
    """
    try:
        with zipfile.ZipFile(apk_path, 'r') as zip_ref:
            manifest_name = "AndroidManifest.xml"
            if manifest_name in zip_ref.namelist():
                extract_path = os.path.join(temp_dir, manifest_name)
                zip_ref.extract(manifest_name, temp_dir)
                return extract_path
    except Exception as e:
        print(f"提取 manifest 失败: {e}")
    return None


def parse_manifest(manifest_path: str) -> Optional[ET.Element]:
    """
    解析 AndroidManifest.xml

    Args:
        manifest_path: manifest 文件路径

    Returns:
        解析后的 XML 根元素，失败返回 None
    """
    try:
        tree = ET.parse(manifest_path)
        return tree.getroot()
    except Exception as e:
        print(f"解析 manifest 失败: {e}")
        return None


def get_namespace(root: ET.Element) -> str:
    """
    获取 XML 命名空间

    Args:
        root: XML 根元素

    Returns:
        命名空间字符串
    """
    ns_match = re.match(r'\{([^}]+)\}', root.tag)
    if ns_match:
        return ns_match.group(1)
    return "http://schemas.android.com/apk/res/android"


def find_smali_files(project_path: str) -> List[str]:
    """
    查找项目中的所有 smali 文件

    Args:
        project_path: 项目目录路径

    Returns:
        smali 文件路径列表
    """
    smali_files = []
    for root, dirs, files in os.walk(project_path):
        # 跳过资源目录
        if "res" in root or "assets" in root:
            continue
        for file in files:
            if file.endswith(".smali"):
                smali_files.append(os.path.join(root, file))
    return smali_files


def find_string_files(project_path: str) -> List[str]:
    """
    查找项目中的字符串资源文件

    Args:
        project_path: 项目目录路径

    Returns:
        strings.xml 文件路径列表
    """
    string_files = []
    res_path = os.path.join(project_path, "res")
    if not os.path.isdir(res_path):
        return string_files

    for root, dirs, files in os.walk(res_path):
        for file in files:
            if file == "strings.xml":
                string_files.append(os.path.join(root, file))
    return string_files


def is_base64_encoded(text: str) -> bool:
    """
    检查文本是否为 Base64 编码

    Args:
        text: 待检查文本

    Returns:
        是否为 Base64 编码
    """
    if len(text) < 20:
        return False
    pattern = r'^[A-Za-z0-9+/]*={0,2}$'
    if not re.match(pattern, text):
        return False
    # 检查是否包含 Base64 特征
    if len(text) % 4 != 0:
        return False
    return True


def is_hex_encoded(text: str) -> bool:
    """
    检查文本是否为十六进制编码

    Args:
        text: 待检查文本

    Returns:
        是否为十六进制编码
    """
    if len(text) < 20:
        return False
    pattern = r'^[0-9a-fA-F]+$'
    return bool(re.match(pattern, text))


def is_likely_encrypted(text: str) -> bool:
    """
    判断字符串是否可能为加密字符串

    Args:
        text: 待检查文本

    Returns:
        是否可能为加密字符串
    """
    # 长随机字符串可能是加密的
    if len(text) >= 32:
        # 检查字符分布
        unique_chars = len(set(text))
        if unique_chars / len(text) > 0.7:
            return True
        if is_base64_encoded(text):
            return True
        if is_hex_encoded(text):
            return True
    return False


def extract_urls_from_text(text: str) -> List[str]:
    """
    从文本中提取 URL

    Args:
        text: 待分析文本

    Returns:
        URL 列表
    """
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
    return re.findall(url_pattern, text)


def extract_ips_from_text(text: str) -> List[str]:
    """
    从文本中提取 IP 地址

    Args:
        text: 待分析文本

    Returns:
        IP 地址列表
    """
    ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    return re.findall(ip_pattern, text)


def extract_api_endpoints_from_text(text: str) -> List[str]:
    """
    从文本中提取 API 端点

    Args:
        text: 待分析文本

    Returns:
        API 端点列表
    """
    # API 端点模式
    patterns = [
        r'/api/[\w/]+',
        r'/v\d+/[\w/]+',
        r'/rest/[\w/]+',
        r'/service/[\w/]+',
        r'/endpoint/[\w/]+',
    ]
    endpoints = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        endpoints.extend(matches)
    return endpoints


# =============================================================================
# MCP 工具函数
# =============================================================================

@mcp.tool()
def analyze_permissions(input_path: str) -> Dict[str, Any]:
    """
    分析 AndroidManifest.xml 中的权限

    Args:
        input_path: APK 文件路径或已解码项目目录路径

    Returns:
        权限分析结果
    """
    result = AnalysisResult(success=False)

    # 验证输入路径
    if not os.path.exists(input_path):
        result.message = f"路径不存在: {input_path}"
        return result.to_dict()

    manifest_path = None
    temp_dir = None

    try:
        if is_apk_file(input_path):
            # 从 APK 提取 manifest
            import tempfile
            temp_dir = tempfile.mkdtemp()
            manifest_path = extract_apk_manifest(input_path, temp_dir)
            if not manifest_path:
                result.message = "无法从 APK 提取 AndroidManifest.xml"
                return result.to_dict()
        elif is_decoded_project(input_path):
            manifest_path = os.path.join(input_path, "AndroidManifest.xml")
        else:
            result.message = "无效的输入路径，必须是 APK 文件或已解码的项目目录"
            return result.to_dict()

        # 解析 manifest
        root = parse_manifest(manifest_path)
        if root is None:
            result.message = "无法解析 AndroidManifest.xml"
            return result.to_dict()

        ns = get_namespace(root)

        # 提取权限
        permissions = []
        dangerous_perms = []

        for perm in root.findall(f".//{{{ns}}}uses-permission"):
            name = perm.get(f"{{{ns}}}name", "")
            if name:
                perm_info = {
                    "name": name,
                    "is_dangerous": name in DANGEROUS_PERMISSIONS,
                    "description": DANGEROUS_PERMISSIONS.get(name, ""),
                }
                permissions.append(perm_info)

                if name in DANGEROUS_PERMISSIONS:
                    dangerous_perms.append(perm_info)

        # 提取自定义权限
        custom_permissions = []
        for perm in root.findall(f".//{{{ns}}}permission"):
            name = perm.get(f"{{{ns}}}name", "")
            protection_level = perm.get(f"{{{ns}}}protectionLevel", "")
            if name:
                custom_permissions.append({
                    "name": name,
                    "protection_level": protection_level,
                })

        result.success = True
        result.message = f"共发现 {len(permissions)} 个权限，其中 {len(dangerous_perms)} 个危险权限"
        result.data = {
            "total_permissions": len(permissions),
            "dangerous_count": len(dangerous_perms),
            "permissions": permissions,
            "dangerous_permissions": dangerous_perms,
            "custom_permissions": custom_permissions,
        }

    except Exception as e:
        result.message = f"分析权限时出错: {str(e)}"
        result.errors.append(str(e))

    finally:
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

    return result.to_dict()


@mcp.tool()
def extract_strings(input_path: str) -> Dict[str, Any]:
    """
    从 APK 或项目目录提取字符串资源

    Args:
        input_path: APK 文件路径或已解码项目目录路径

    Returns:
        字符串提取结果
    """
    result = AnalysisResult(success=False)

    if not os.path.exists(input_path):
        result.message = f"路径不存在: {input_path}"
        return result.to_dict()

    try:
        all_strings = []
        encrypted_strings = []
        string_files = []

        if is_apk_file(input_path):
            # 从 APK 中提取字符串
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                for name in zip_ref.namelist():
                    if "res/values" in name and name.endswith(".xml"):
                        try:
                            content = zip_ref.read(name).decode('utf-8', errors='ignore')
                            string_files.append({
                                "file": name,
                                "content": content,
                            })
                        except Exception:
                            pass
        elif is_decoded_project(input_path):
            string_files_paths = find_string_files(input_path)
            for file_path in string_files_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        rel_path = os.path.relpath(file_path, input_path)
                        string_files.append({
                            "file": rel_path,
                            "content": content,
                        })
                except Exception:
                    pass
        else:
            result.message = "无效的输入路径"
            return result.to_dict()

        # 解析字符串
        for sf in string_files:
            try:
                root = ET.fromstring(sf["content"])
                for string_elem in root.findall("string"):
                    name = string_elem.get("name", "")
                    text = "".join(string_elem.itertext())
                    if text:
                        string_info = {
                            "name": name,
                            "value": text,
                            "file": sf["file"],
                            "length": len(text),
                        }

                        # 检查是否为加密字符串
                        if is_likely_encrypted(text):
                            string_info["suspicious"] = True
                            string_info["suspicious_type"] = "可能加密"
                            encrypted_strings.append(string_info)

                        all_strings.append(string_info)
            except Exception:
                # XML 解析失败，使用正则提取
                pattern = r'<string\s+name="([^"]+)"[^>]*>([^<]*)</string>'
                matches = re.findall(pattern, sf["content"])
                for name, text in matches:
                    if text:
                        string_info = {
                            "name": name,
                            "value": text,
                            "file": sf["file"],
                            "length": len(text),
                        }

                        if is_likely_encrypted(text):
                            string_info["suspicious"] = True
                            string_info["suspicious_type"] = "可能加密"
                            encrypted_strings.append(string_info)

                        all_strings.append(string_info)

        result.success = True
        result.message = f"共提取 {len(all_strings)} 个字符串，发现 {len(encrypted_strings)} 个可疑加密字符串"
        result.data = {
            "total_strings": len(all_strings),
            "suspicious_count": len(encrypted_strings),
            "strings": all_strings[:100],  # 限制返回数量
            "suspicious_strings": encrypted_strings,
        }

    except Exception as e:
        result.message = f"提取字符串时出错: {str(e)}"
        result.errors.append(str(e))

    return result.to_dict()


@mcp.tool()
def extract_endpoints(input_path: str) -> Dict[str, Any]:
    """
    提取 URL、IP 地址、API 端点

    Args:
        input_path: APK 文件路径或已解码项目目录路径

    Returns:
        端点提取结果
    """
    result = AnalysisResult(success=False)

    if not os.path.exists(input_path):
        result.message = f"路径不存在: {input_path}"
        return result.to_dict()

    try:
        urls = set()
        ips = set()
        api_endpoints = set()
        smali_files = []

        if is_apk_file(input_path):
            # 从 APK 中提取
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                for name in zip_ref.namelist():
                    if name.endswith(".smali") or name.endswith(".xml"):
                        try:
                            content = zip_ref.read(name).decode('utf-8', errors='ignore')
                            file_urls = extract_urls_from_text(content)
                            file_ips = extract_ips_from_text(content)
                            file_apis = extract_api_endpoints_from_text(content)

                            urls.update(file_urls)
                            ips.update(file_ips)
                            api_endpoints.update(file_apis)
                        except Exception:
                            pass
        elif is_decoded_project(input_path):
            # 从 smali 文件提取
            smali_files = find_smali_files(input_path)

            # 同时检查资源文件
            string_files = find_string_files(input_path)

            for file_path in smali_files + string_files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    file_urls = extract_urls_from_text(content)
                    file_ips = extract_ips_from_text(content)
                    file_apis = extract_api_endpoints_from_text(content)

                    urls.update(file_urls)
                    ips.update(file_ips)
                    api_endpoints.update(file_apis)
                except Exception:
                    pass
        else:
            result.message = "无效的输入路径"
            return result.to_dict()

        # 过滤和分类
        filtered_urls = [u for u in urls if len(u) > 10]
        filtered_ips = [ip for ip in ips if not ip.startswith("127.") and not ip.startswith("192.168.")]

        result.success = True
        result.message = f"发现 {len(filtered_urls)} 个 URL，{len(filtered_ips)} 个 IP，{len(api_endpoints)} 个 API 端点"
        result.data = {
            "urls": list(filtered_urls)[:50],
            "ips": list(filtered_ips)[:50],
            "api_endpoints": list(api_endpoints)[:50],
            "total_urls": len(filtered_urls),
            "total_ips": len(filtered_ips),
            "total_api_endpoints": len(api_endpoints),
        }

    except Exception as e:
        result.message = f"提取端点时出错: {str(e)}"
        result.errors.append(str(e))

    return result.to_dict()


@mcp.tool()
def identify_sdks(input_path: str) -> Dict[str, Any]:
    """
    识别第三方 SDK（广告、统计、社交、支付等）

    Args:
        input_path: APK 文件路径或已解码项目目录路径

    Returns:
        SDK 识别结果
    """
    result = AnalysisResult(success=False)

    if not os.path.exists(input_path):
        result.message = f"路径不存在: {input_path}"
        return result.to_dict()

    try:
        found_sdks = {}
        all_packages = set()
        all_classes = set()

        if is_apk_file(input_path):
            # 从 APK 中提取包名和类名
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                for name in zip_ref.namelist():
                    if name.endswith(".smali"):
                        # 从 smali 路径提取包名
                        parts = name.split('/')
                        if len(parts) >= 2:
                            package = '.'.join(parts[:-1])
                            all_packages.add(package)
                            class_name = parts[-1].replace('.smali', '')
                            all_classes.add(class_name)
        elif is_decoded_project(input_path):
            # 从 smali 文件提取
            smali_files = find_smali_files(input_path)

            for file_path in smali_files:
                rel_path = os.path.relpath(file_path, input_path)
                parts = rel_path.split(os.sep)
                if len(parts) >= 2:
                    package = '.'.join(parts[:-1])
                    all_packages.add(package)
                    class_name = parts[-1].replace('.smali', '')
                    all_classes.add(class_name)
        else:
            result.message = "无效的输入路径"
            return result.to_dict()

        # 匹配 SDK 特征
        for sdk_type, patterns in SDK_PATTERNS.items():
            matched_sdks = []

            # 匹配包名
            for pkg_pattern in patterns["packages"]:
                for pkg in all_packages:
                    if pkg_pattern in pkg:
                        matched_sdks.append({
                            "name": pkg_pattern,
                            "type": "package",
                            "match": pkg,
                        })

            # 匹配类名
            for class_pattern in patterns["classes"]:
                for cls in all_classes:
                    if class_pattern.lower() in cls.lower():
                        matched_sdks.append({
                            "name": class_pattern,
                            "type": "class",
                            "match": cls,
                        })

            if matched_sdks:
                found_sdks[sdk_type] = matched_sdks

        # 统计
        total_sdks = sum(len(sdks) for sdks in found_sdks.values())

        result.success = True
        result.message = f"识别到 {len(found_sdks)} 类 SDK，共 {total_sdks} 个匹配"
        result.data = {
            "total_categories": len(found_sdks),
            "total_matches": total_sdks,
            "sdks": found_sdks,
        }

    except Exception as e:
        result.message = f"识别 SDK 时出错: {str(e)}"
        result.errors.append(str(e))

    return result.to_dict()


@mcp.tool()
def full_analysis(input_path: str) -> Dict[str, Any]:
    """
    执行完整的静态分析

    Args:
        input_path: APK 文件路径或已解码项目目录路径

    Returns:
        完整分析结果
    """
    result = AnalysisResult(success=False)

    if not os.path.exists(input_path):
        result.message = f"路径不存在: {input_path}"
        return result.to_dict()

    try:
        # 执行所有分析
        permissions_result = analyze_permissions(input_path)
        strings_result = extract_strings(input_path)
        endpoints_result = extract_endpoints(input_path)
        sdks_result = identify_sdks(input_path)

        result.success = True
        result.message = "完整分析完成"
        result.data = {
            "permissions": permissions_result,
            "strings": strings_result,
            "endpoints": endpoints_result,
            "sdks": sdks_result,
        }

    except Exception as e:
        result.message = f"完整分析时出错: {str(e)}"
        result.errors.append(str(e))

    return result.to_dict()


# =============================================================================
# 主入口
# =============================================================================

if __name__ == "__main__":
    mcp.run()
