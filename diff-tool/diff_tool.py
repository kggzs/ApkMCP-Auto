# -*- coding: utf-8 -*-
"""
文件对比工具 MCP Server
提供 APK、Smali、资源文件的对比功能
"""

import os
import hashlib
import zipfile
import tempfile
import shutil
import difflib
from pathlib import Path
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP 服务
mcp = FastMCP("diff-tool")


def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """
    计算文件哈希值
    
    参数:
        file_path: 文件路径
        algorithm: 哈希算法 (md5/sha1/sha256)
    
    返回:
        哈希字符串
    """
    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def format_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    参数:
        size_bytes: 字节数
    
    返回:
        格式化后的字符串 (如: 1.5 MB)
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def create_success_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建成功响应格式
    
    参数:
        data: 响应数据
    
    返回:
        统一格式的成功响应
    """
    return {"success": True, "data": data}


def create_error_result(error_message: str) -> Dict[str, Any]:
    """
    创建错误响应格式
    
    参数:
        error_message: 错误信息
    
    返回:
        统一格式的错误响应
    """
    return {"success": False, "error": error_message}


@mcp.tool()
def compare_apks(apk_path1: str, apk_path2: str) -> Dict[str, Any]:
    """
    对比两个 APK 文件的差异
    
    对比内容包括：文件列表、文件大小、文件哈希值
    
    参数:
        apk_path1: 第一个 APK 文件路径
        apk_path2: 第二个 APK 文件路径
    
    返回:
        包含差异信息的字典
    """
    # 验证文件是否存在
    if not os.path.exists(apk_path1):
        return create_error_result(f"APK 文件不存在: {apk_path1}")
    if not os.path.exists(apk_path2):
        return create_error_result(f"APK 文件不存在: {apk_path2}")
    
    # 验证文件扩展名
    if not apk_path1.lower().endswith(".apk"):
        return create_error_result(f"文件不是 APK 格式: {apk_path1}")
    if not apk_path2.lower().endswith(".apk"):
        return create_error_result(f"文件不是 APK 格式: {apk_path2}")
    
    temp_dir1 = None
    temp_dir2 = None
    
    try:
        # 创建临时目录解压 APK
        temp_dir1 = tempfile.mkdtemp(prefix="apk1_")
        temp_dir2 = tempfile.mkdtemp(prefix="apk2_")
        
        # 解压 APK 文件
        with zipfile.ZipFile(apk_path1, "r") as zip_ref:
            zip_ref.extractall(temp_dir1)
        with zipfile.ZipFile(apk_path2, "r") as zip_ref:
            zip_ref.extractall(temp_dir2)
        
        # 收集文件信息
        files1 = {}
        files2 = {}
        
        for root, _, filenames in os.walk(temp_dir1):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, temp_dir1).replace("\\", "/")
                file_size = os.path.getsize(full_path)
                file_hash = calculate_file_hash(full_path)
                files1[rel_path] = {"size": file_size, "hash": file_hash}
        
        for root, _, filenames in os.walk(temp_dir2):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, temp_dir2).replace("\\", "/")
                file_size = os.path.getsize(full_path)
                file_hash = calculate_file_hash(full_path)
                files2[rel_path] = {"size": file_size, "hash": file_hash}
        
        # 对比差异
        only_in_apk1 = []
        only_in_apk2 = []
        modified_files = []
        identical_files = []
        
        all_files = set(files1.keys()) | set(files2.keys())
        
        for file_path in sorted(all_files):
            if file_path in files1 and file_path not in files2:
                only_in_apk1.append({
                    "path": file_path,
                    "size": format_size(files1[file_path]["size"]),
                    "size_bytes": files1[file_path]["size"],
                    "hash": files1[file_path]["hash"]
                })
            elif file_path in files2 and file_path not in files1:
                only_in_apk2.append({
                    "path": file_path,
                    "size": format_size(files2[file_path]["size"]),
                    "size_bytes": files2[file_path]["size"],
                    "hash": files2[file_path]["hash"]
                })
            elif files1[file_path]["hash"] != files2[file_path]["hash"]:
                modified_files.append({
                    "path": file_path,
                    "apk1_size": format_size(files1[file_path]["size"]),
                    "apk2_size": format_size(files2[file_path]["size"]),
                    "apk1_size_bytes": files1[file_path]["size"],
                    "apk2_size_bytes": files2[file_path]["size"],
                    "apk1_hash": files1[file_path]["hash"],
                    "apk2_hash": files2[file_path]["hash"]
                })
            else:
                identical_files.append({
                    "path": file_path,
                    "size": format_size(files1[file_path]["size"]),
                    "hash": files1[file_path]["hash"]
                })
        
        # 计算 APK 整体信息
        apk1_size = os.path.getsize(apk_path1)
        apk2_size = os.path.getsize(apk_path2)
        
        result = {
            "apk1_info": {
                "path": apk_path1,
                "size": format_size(apk1_size),
                "size_bytes": apk1_size,
                "file_count": len(files1)
            },
            "apk2_info": {
                "path": apk_path2,
                "size": format_size(apk2_size),
                "size_bytes": apk2_size,
                "file_count": len(files2)
            },
            "summary": {
                "only_in_apk1_count": len(only_in_apk1),
                "only_in_apk2_count": len(only_in_apk2),
                "modified_count": len(modified_files),
                "identical_count": len(identical_files),
                "total_differences": len(only_in_apk1) + len(only_in_apk2) + len(modified_files)
            },
            "only_in_apk1": only_in_apk1,
            "only_in_apk2": only_in_apk2,
            "modified_files": modified_files,
            "identical_files": identical_files[:100]  # 限制相同文件数量
        }
        
        return create_success_result(result)
        
    except zipfile.BadZipFile:
        return create_error_result("APK 文件损坏或不是有效的 ZIP 格式")
    except Exception as e:
        return create_error_result(f"对比 APK 时发生错误: {str(e)}")
    finally:
        # 清理临时目录
        if temp_dir1 and os.path.exists(temp_dir1):
            shutil.rmtree(temp_dir1, ignore_errors=True)
        if temp_dir2 and os.path.exists(temp_dir2):
            shutil.rmtree(temp_dir2, ignore_errors=True)


@mcp.tool()
def compare_smali(smali_path1: str, smali_path2: str) -> Dict[str, Any]:
    """
    对比两个 Smali 文件的行级差异
    
    使用 difflib 生成统一的差异输出格式
    
    参数:
        smali_path1: 第一个 Smali 文件路径
        smali_path2: 第二个 Smali 文件路径
    
    返回:
        包含行级差异信息的字典
    """
    # 验证文件是否存在
    if not os.path.exists(smali_path1):
        return create_error_result(f"Smali 文件不存在: {smali_path1}")
    if not os.path.exists(smali_path2):
        return create_error_result(f"Smali 文件不存在: {smali_path2}")
    
    # 验证文件类型
    if not smali_path1.lower().endswith(".smali"):
        return create_error_result(f"文件不是 Smali 格式: {smali_path1}")
    if not smali_path2.lower().endswith(".smali"):
        return create_error_result(f"文件不是 Smali 格式: {smali_path2}")
    
    try:
        # 读取文件内容
        with open(smali_path1, "r", encoding="utf-8", errors="ignore") as f:
            lines1 = f.readlines()
        with open(smali_path2, "r", encoding="utf-8", errors="ignore") as f:
            lines2 = f.readlines()
        
        # 获取文件名
        filename1 = os.path.basename(smali_path1)
        filename2 = os.path.basename(smali_path2)
        
        # 使用 difflib 生成统一差异格式
        diff = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=filename1,
            tofile=filename2,
            lineterm=""
        ))
        
        # 统计信息
        added_lines = 0
        removed_lines = 0
        modified_lines = 0
        
        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                added_lines += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed_lines += 1
        
        # 计算相似度
        sm = difflib.SequenceMatcher(None, lines1, lines2)
        similarity = sm.ratio() * 100
        
        # 生成简洁的差异摘要
        diff_summary = []
        current_hunk = None
        
        for line in diff:
            if line.startswith("@@"):
                # 提取行号信息
                parts = line.split(" ")
                if len(parts) >= 3:
                    old_range = parts[1][1:]  # 去掉 "-"
                    new_range = parts[2][1:]  # 去掉 "+"
                    current_hunk = {
                        "range": f"旧文件: {old_range}, 新文件: {new_range}",
                        "changes": []
                    }
                    diff_summary.append(current_hunk)
            elif current_hunk is not None:
                current_hunk["changes"].append(line)
        
        # 限制差异摘要数量
        if len(diff_summary) > 50:
            diff_summary = diff_summary[:50]
            diff_summary.append({"range": "...", "changes": ["差异过多，已截断显示"]})        
        result = {
            "file1_info": {
                "path": smali_path1,
                "filename": filename1,
                "line_count": len(lines1),
                "size": format_size(os.path.getsize(smali_path1))
            },
            "file2_info": {
                "path": smali_path2,
                "filename": filename2,
                "line_count": len(lines2),
                "size": format_size(os.path.getsize(smali_path2))
            },
            "summary": {
                "similarity_percent": round(similarity, 2),
                "added_lines": added_lines,
                "removed_lines": removed_lines,
                "total_changes": added_lines + removed_lines,
                "is_identical": len(diff) == 0
            },
            "diff_summary": diff_summary,
            "full_diff": diff[:200]  # 限制完整差异行数
        }
        
        return create_success_result(result)
        
    except Exception as e:
        return create_error_result(f"对比 Smali 文件时发生错误: {str(e)}")


@mcp.tool()
def compare_resources(res_dir1: str, res_dir2: str) -> Dict[str, Any]:
    """
    对比两个资源目录的差异
    
    对比内容包括：文件列表、目录结构、文件大小、文件哈希
    
    参数:
        res_dir1: 第一个资源目录路径
        res_dir2: 第二个资源目录路径
    
    返回:
        包含资源差异信息的字典
    """
    # 验证目录是否存在
    if not os.path.exists(res_dir1):
        return create_error_result(f"资源目录不存在: {res_dir1}")
    if not os.path.exists(res_dir2):
        return create_error_result(f"资源目录不存在: {res_dir2}")
    if not os.path.isdir(res_dir1):
        return create_error_result(f"路径不是目录: {res_dir1}")
    if not os.path.isdir(res_dir2):
        return create_error_result(f"路径不是目录: {res_dir2}")
    
    try:
        # 收集资源文件信息
        def collect_resources(directory: str) -> Dict[str, Dict[str, Any]]:
            """递归收集目录中的资源文件信息"""
            resources = {}
            for root, dirs, files in os.walk(directory):
                # 排除隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                
                for filename in files:
                    if filename.startswith("."):
                        continue
                    
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, directory).replace("\\", "/")
                    
                    try:
                        file_size = os.path.getsize(full_path)
                        file_hash = calculate_file_hash(full_path)
                        resources[rel_path] = {
                            "size": file_size,
                            "hash": file_hash,
                            "extension": os.path.splitext(filename)[1].lower()
                        }
                    except (OSError, IOError):
                        # 跳过无法访问的文件
                        continue
            return resources
        
        resources1 = collect_resources(res_dir1)
        resources2 = collect_resources(res_dir2)
        
        # 按文件类型分类
        def categorize_by_extension(resources: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
            """按扩展名分类资源文件"""
            categories = {}
            for path, info in resources.items():
                ext = info["extension"] or "(无扩展名)"
                if ext not in categories:
                    categories[ext] = []
                categories[ext].append(path)
            return categories
        
        categories1 = categorize_by_extension(resources1)
        categories2 = categorize_by_extension(resources2)
        
        # 对比差异
        only_in_dir1 = []
        only_in_dir2 = []
        modified_resources = []
        identical_resources = []
        
        all_resources = set(resources1.keys()) | set(resources2.keys())
        
        for res_path in sorted(all_resources):
            if res_path in resources1 and res_path not in resources2:
                only_in_dir1.append({
                    "path": res_path,
                    "size": format_size(resources1[res_path]["size"]),
                    "size_bytes": resources1[res_path]["size"],
                    "type": resources1[res_path]["extension"] or "unknown"
                })
            elif res_path in resources2 and res_path not in resources1:
                only_in_dir2.append({
                    "path": res_path,
                    "size": format_size(resources2[res_path]["size"]),
                    "size_bytes": resources2[res_path]["size"],
                    "type": resources2[res_path]["extension"] or "unknown"
                })
            elif resources1[res_path]["hash"] != resources2[res_path]["hash"]:
                modified_resources.append({
                    "path": res_path,
                    "dir1_size": format_size(resources1[res_path]["size"]),
                    "dir2_size": format_size(resources2[res_path]["size"]),
                    "dir1_size_bytes": resources1[res_path]["size"],
                    "dir2_size_bytes": resources2[res_path]["size"],
                    "type": resources1[res_path]["extension"] or "unknown"
                })
            else:
                identical_resources.append({
                    "path": res_path,
                    "size": format_size(resources1[res_path]["size"]),
                    "type": resources1[res_path]["extension"] or "unknown"
                })
        
        # 计算目录大小
        def calculate_dir_size(directory: str) -> int:
            """计算目录总大小"""
            total_size = 0
            for root, _, files in os.walk(directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        continue
            return total_size
        
        dir1_size = calculate_dir_size(res_dir1)
        dir2_size = calculate_dir_size(res_dir2)
        
        # 统计各类型文件数量
        all_extensions = set(categories1.keys()) | set(categories2.keys())
        type_comparison = []
        for ext in sorted(all_extensions):
            count1 = len(categories1.get(ext, []))
            count2 = len(categories2.get(ext, []))
            type_comparison.append({
                "type": ext,
                "dir1_count": count1,
                "dir2_count": count2,
                "difference": count2 - count1
            })
        
        result = {
            "dir1_info": {
                "path": res_dir1,
                "total_size": format_size(dir1_size),
                "size_bytes": dir1_size,
                "file_count": len(resources1)
            },
            "dir2_info": {
                "path": res_dir2,
                "total_size": format_size(dir2_size),
                "size_bytes": dir2_size,
                "file_count": len(resources2)
            },
            "summary": {
                "only_in_dir1_count": len(only_in_dir1),
                "only_in_dir2_count": len(only_in_dir2),
                "modified_count": len(modified_resources),
                "identical_count": len(identical_resources),
                "total_differences": len(only_in_dir1) + len(only_in_dir2) + len(modified_resources)
            },
            "type_comparison": type_comparison,
            "only_in_dir1": only_in_dir1[:100],  # 限制数量
            "only_in_dir2": only_in_dir2[:100],
            "modified_resources": modified_resources[:100],
            "identical_resources": identical_resources[:50]
        }
        
        return create_success_result(result)
        
    except Exception as e:
        return create_error_result(f"对比资源目录时发生错误: {str(e)}")


@mcp.tool()
def compare_text_files(file_path1: str, file_path2: str) -> Dict[str, Any]:
    """
    对比两个文本文件的差异
    
    通用文本文件对比工具，支持任意文本格式
    
    参数:
        file_path1: 第一个文本文件路径
        file_path2: 第二个文本文件路径
    
    返回:
        包含文本差异信息的字典
    """
    # 验证文件是否存在
    if not os.path.exists(file_path1):
        return create_error_result(f"文件不存在: {file_path1}")
    if not os.path.exists(file_path2):
        return create_error_result(f"文件不存在: {file_path2}")
    
    # 验证是否为文件
    if not os.path.isfile(file_path1):
        return create_error_result(f"路径不是文件: {file_path1}")
    if not os.path.isfile(file_path2):
        return create_error_result(f"路径不是文件: {file_path2}")
    
    try:
        # 读取文件内容
        with open(file_path1, "r", encoding="utf-8", errors="ignore") as f:
            lines1 = f.readlines()
        with open(file_path2, "r", encoding="utf-8", errors="ignore") as f:
            lines2 = f.readlines()
        
        # 获取文件名
        filename1 = os.path.basename(file_path1)
        filename2 = os.path.basename(file_path2)
        
        # 生成差异
        diff = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=filename1,
            tofile=filename2,
            lineterm=""
        ))
        
        # 统计信息
        added_lines = sum(1 for line in diff if line.startswith("+") and not line.startswith("++"))
        removed_lines = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        
        # 计算相似度
        sm = difflib.SequenceMatcher(None, lines1, lines2)
        similarity = sm.ratio() * 100
        
        result = {
            "file1_info": {
                "path": file_path1,
                "filename": filename1,
                "line_count": len(lines1),
                "size": format_size(os.path.getsize(file_path1))
            },
            "file2_info": {
                "path": file_path2,
                "filename": filename2,
                "line_count": len(lines2),
                "size": format_size(os.path.getsize(file_path2))
            },
            "summary": {
                "similarity_percent": round(similarity, 2),
                "added_lines": added_lines,
                "removed_lines": removed_lines,
                "total_changes": added_lines + removed_lines,
                "is_identical": len(diff) == 0
            },
            "diff_preview": diff[:100]  # 限制预览行数
        }
        
        return create_success_result(result)
        
    except Exception as e:
        return create_error_result(f"对比文本文件时发生错误: {str(e)}")


if __name__ == "__main__":
    # 启动 MCP 服务
    mcp.run(transport="stdio")
