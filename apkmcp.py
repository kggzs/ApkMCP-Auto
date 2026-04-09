#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ApkMCP-Auto 统一命令行工具

提供统一的命令行接口来管理所有 MCP 工具
所有路径使用相对路径，确保项目可移植

用法:
    python apkmcp.py status              # 查看工具状态
    python apkmcp.py config              # 生成 MCP 配置
    python apkmcp.py install [tool]      # 安装依赖
    python apkmcp.py list                # 列出所有工具
    python apkmcp.py start [tool]        # 启动指定工具
"""

import sys
import os
import json
import argparse
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ToolType(Enum):
    """工具类型枚举"""
    JADX = "jadx"
    APKTOOL = "apktool"
    ADB = "adb"
    SIGN_TOOLS = "sign-tools"
    STATIC_ANALYZER = "static-analyzer"
    DIFF = "diff"
    FRIDA = "frida"


@dataclass
class ToolConfig:
    """工具配置类"""
    name: str
    tool_type: ToolType
    server_path: str  # 相对路径
    requirements_path: str  # 相对路径
    port: int
    enabled: bool = True
    description: str = ""
    extra_args: List[str] = field(default_factory=list)


class ApkMCPManager:
    """
    ApkMCP-Auto 工具管理器
    统一管理所有工具的启动、停止和配置
    所有路径使用相对路径，确保项目可移植
    """

    # 默认端口分配
    DEFAULT_PORTS = {
        ToolType.JADX: 8651,
        ToolType.APKTOOL: 8652,
        ToolType.ADB: 8653,
        ToolType.SIGN_TOOLS: 8654,
        ToolType.STATIC_ANALYZER: 8655,
        ToolType.DIFF: 8656,
        ToolType.FRIDA: 8657,
    }

    def __init__(self, base_path: Optional[str] = None):
        """
        初始化管理器

        参数:
            base_path: 工具根目录，默认为当前文件所在目录下的 tools
        """
        if base_path is None:
            # 获取项目根目录（apkmcp.py 所在目录）
            project_root = Path(__file__).parent
            base_path = project_root / "tools"

        self.base_path = Path(base_path)
        self.project_path = self.base_path.parent
        self.bin_path = self.base_path / "bin"
        self.workspace_path = self.base_path / "workspace"

        # 初始化工具配置
        self.tools: Dict[ToolType, ToolConfig] = self._init_tools()

        logger.info(f"ApkMCPManager 初始化完成，基础路径: {self.base_path}")

    def _get_relative_path(self, path: Path, relative_to: Optional[Path] = None) -> str:
        """获取相对路径"""
        if relative_to is None:
            relative_to = self.project_path

        try:
            return str(path.relative_to(relative_to)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    def _init_tools(self) -> Dict[ToolType, ToolConfig]:
        """初始化所有工具配置（使用相对路径）"""
        tools = {}

        tools[ToolType.JADX] = ToolConfig(
            name="jadx-mcp-server",
            tool_type=ToolType.JADX,
            server_path=self._get_relative_path(self.base_path / "jadx" / "server.jar"),
            requirements_path=self._get_relative_path(self.base_path / "jadx" / "requirements.txt"),
            port=self.DEFAULT_PORTS[ToolType.JADX],
            description="JADX MCP 服务器 - Java 反编译分析"
        )

        tools[ToolType.APKTOOL] = ToolConfig(
            name="apktool-mcp-server",
            tool_type=ToolType.APKTOOL,
            server_path=self._get_relative_path(self.base_path / "apktool" / "server.py"),
            requirements_path=self._get_relative_path(self.base_path / "apktool" / "requirements.txt"),
            port=self.DEFAULT_PORTS[ToolType.APKTOOL],
            description="APKTool MCP 服务器 - APK 解码/编码",
            extra_args=[
                "--workspace", self._get_relative_path(self.workspace_path / "apktool"),
                "--apktool-path", self._get_relative_path(self.bin_path / "apktool.bat")
            ]
        )

        tools[ToolType.ADB] = ToolConfig(
            name="adb-mcp-server",
            tool_type=ToolType.ADB,
            server_path=self._get_relative_path(self.base_path / "adb" / "server.py"),
            requirements_path=self._get_relative_path(self.base_path / "adb" / "requirements.txt"),
            port=self.DEFAULT_PORTS[ToolType.ADB],
            description="ADB MCP 服务器 - 设备管理和调试",
            extra_args=["--adb-path", self._get_relative_path(self.bin_path / "adb.exe")]
        )

        tools[ToolType.SIGN_TOOLS] = ToolConfig(
            name="sign-tools-mcp-server",
            tool_type=ToolType.SIGN_TOOLS,
            server_path=self._get_relative_path(self.base_path / "sign-tools" / "server.py"),
            requirements_path=self._get_relative_path(self.base_path / "sign-tools" / "requirements.txt"),
            port=self.DEFAULT_PORTS[ToolType.SIGN_TOOLS],
            description="签名工具 MCP 服务器 - APK 签名和密钥管理",
            extra_args=["--workspace", self._get_relative_path(self.workspace_path / "sign-tools")]
        )

        tools[ToolType.STATIC_ANALYZER] = ToolConfig(
            name="static-analyzer",
            tool_type=ToolType.STATIC_ANALYZER,
            server_path=self._get_relative_path(self.base_path / "static-analyzer" / "server.py"),
            requirements_path=self._get_relative_path(self.base_path / "static-analyzer" / "requirements.txt"),
            port=self.DEFAULT_PORTS[ToolType.STATIC_ANALYZER],
            description="静态分析工具 - 权限、字符串、SDK 识别"
        )

        tools[ToolType.DIFF] = ToolConfig(
            name="diff-tool",
            tool_type=ToolType.DIFF,
            server_path=self._get_relative_path(self.base_path / "diff" / "server.py"),
            requirements_path=self._get_relative_path(self.base_path / "diff" / "requirements.txt"),
            port=self.DEFAULT_PORTS[ToolType.DIFF],
            description="文件对比工具 - APK、Smali、资源对比"
        )

        tools[ToolType.FRIDA] = ToolConfig(
            name="frida-mcp-server",
            tool_type=ToolType.FRIDA,
            server_path=self._get_relative_path(self.base_path / "frida" / "server.py"),
            requirements_path=self._get_relative_path(self.base_path / "frida" / "requirements.txt"),
            port=self.DEFAULT_PORTS[ToolType.FRIDA],
            description="Frida MCP 服务器 - 动态插桩分析"
        )

        return tools

    def _resolve_path(self, rel_path: str) -> Path:
        """将相对路径解析为绝对路径"""
        path = Path(rel_path)
        if path.is_absolute():
            return path
        return self.project_path / path

    def get_tool(self, tool_type: ToolType) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self.tools.get(tool_type)

    def list_tools(self) -> List[ToolConfig]:
        """列出所有工具配置"""
        return list(self.tools.values())

    def install_dependencies(self, tool_type: ToolType) -> bool:
        """安装工具依赖"""
        config = self.tools.get(tool_type)
        if not config:
            return False

        req_file = self._resolve_path(config.requirements_path)
        if not req_file.exists():
            logger.info(f"工具 {tool_type.value} 没有依赖文件")
            return True

        try:
            logger.info(f"正在安装 {tool_type.value} 的依赖...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info(f"{tool_type.value} 依赖安装成功")
                return True
            else:
                logger.error(f"{tool_type.value} 依赖安装失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"安装依赖时出错: {e}")
            return False

    def get_mcp_config(self) -> Dict[str, Any]:
        """生成 MCP 配置（使用相对路径）"""
        config = {"mcpServers": {}}

        for tool_type, tool_config in self.tools.items():
            if not tool_config.enabled:
                continue

            server_config = {
                "type": "stdio",
                "enabled": True,
                "description": tool_config.description
            }

            if tool_type == ToolType.JADX:
                java_path = self._get_relative_path(self.bin_path / "jre" / "bin" / "java.exe")
                server_config["command"] = java_path
                server_config["args"] = ["-jar", tool_config.server_path]
            else:
                server_config["command"] = "python"
                server_config["args"] = [tool_config.server_path] + tool_config.extra_args

            config["mcpServers"][tool_config.name] = server_config

        return config

    def save_mcp_config(self, output_path: Optional[str] = None) -> str:
        """保存 MCP 配置到文件"""
        if output_path is None:
            output_path = self.project_path / ".trae" / "config.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        config = self.get_mcp_config()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"MCP 配置已保存到: {output_path}")
        return str(output_path)

    def print_status(self):
        """打印工具状态"""
        print("\n" + "=" * 80)
        print("ApkMCP-Auto 工具套件状态")
        print("=" * 80)
        print(f"项目路径: {self.project_path}")
        print(f"工具路径: {self.base_path}")
        print(f"工作空间: {self.workspace_path}")
        print()

        for tool_type, config in self.tools.items():
            status = "启用" if config.enabled else "禁用"
            server_abs = self._resolve_path(config.server_path)
            req_abs = self._resolve_path(config.requirements_path)
            server_exists = "✓" if server_abs.exists() else "✗"
            req_exists = "✓" if req_abs.exists() else "✗"

            print(f"[{status}] {tool_type.value}")
            print(f"  描述: {config.description}")
            print(f"  端口: {config.port}")
            print(f"  服务器文件: {server_exists} {config.server_path}")
            print(f"  依赖文件: {req_exists} {config.requirements_path}")
            print()

        print("=" * 80)


def get_tool_config(tool_name: str) -> Optional[ToolConfig]:
    """通过名称获取工具配置"""
    manager = ApkMCPManager()
    try:
        tool_type = ToolType(tool_name.lower())
        return manager.get_tool(tool_type)
    except ValueError:
        return None


# ==================== 命令处理函数 ====================

def cmd_status(args):
    """查看工具状态命令"""
    manager = ApkMCPManager()
    manager.print_status()
    return 0


def cmd_config(args):
    """生成 MCP 配置命令"""
    manager = ApkMCPManager()

    if args.output:
        config_path = manager.save_mcp_config(args.output)
    else:
        config_path = manager.save_mcp_config()

    print(f"\nMCP 配置已保存到: {config_path}")

    if args.preview:
        config = manager.get_mcp_config()
        print("\n配置预览:")
        print(json.dumps(config, indent=2, ensure_ascii=False))

    return 0


def cmd_install(args):
    """安装依赖命令"""
    manager = ApkMCPManager()

    if args.tool:
        tool_config = get_tool_config(args.tool)
        if not tool_config:
            print(f"错误: 未知工具 '{args.tool}'")
            print(f"可用工具: {', '.join([t.value for t in ToolType])}")
            return 1

        print(f"正在安装 {args.tool} 的依赖...")
        success = manager.install_dependencies(tool_config.tool_type)
        if success:
            print(f"✓ {args.tool} 依赖安装成功")
        else:
            print(f"✗ {args.tool} 依赖安装失败")
            return 1
    else:
        print("正在安装所有工具的依赖...")
        all_success = True
        for tool_type in ToolType:
            print(f"\n[{tool_type.value}]")
            success = manager.install_dependencies(tool_type)
            if success:
                print(f"  ✓ {tool_type.value} 依赖安装成功")
            else:
                print(f"  ✗ {tool_type.value} 依赖安装失败")
                all_success = False

        if all_success:
            print("\n✓ 所有依赖安装完成")
        else:
            print("\n✗ 部分依赖安装失败")
            return 1

    return 0


def cmd_list(args):
    """列出所有工具命令"""
    manager = ApkMCPManager()
    tools = manager.list_tools()

    print("\n" + "=" * 80)
    print("ApkMCP-Auto 工具列表")
    print("=" * 80)

    for i, tool in enumerate(tools, 1):
        status = "启用" if tool.enabled else "禁用"
        print(f"\n{i}. {tool.tool_type.value} [{status}]")
        print(f"   名称: {tool.name}")
        print(f"   描述: {tool.description}")
        print(f"   端口: {tool.port}")
        print(f"   路径: {tool.server_path}")

    print("\n" + "=" * 80)
    print(f"共 {len(tools)} 个工具")
    return 0


def cmd_start(args):
    """启动工具命令"""
    manager = ApkMCPManager()

    if not args.tool:
        print("错误: 请指定要启动的工具")
        print(f"可用工具: {', '.join([t.value for t in ToolType])}")
        return 1

    tool_config = get_tool_config(args.tool)
    if not tool_config:
        print(f"错误: 未知工具 '{args.tool}'")
        print(f"可用工具: {', '.join([t.value for t in ToolType])}")
        return 1

    print(f"正在启动 {args.tool}...")
    print(f"服务器: {tool_config.server_path}")

    try:
        if args.tool == "jadx":
            java_path = str(Path(manager.base_path) / "bin" / "jre" / "bin" / "java.exe")
            cmd = [java_path, "-jar", tool_config.server_path]
        else:
            cmd = [sys.executable, tool_config.server_path] + tool_config.extra_args

        print(f"命令: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"✓ {args.tool} 已启动 (PID: {process.pid})")

        try:
            process.wait(timeout=2)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"✗ {args.tool} 启动失败:")
                print(stderr or stdout)
                return 1
        except subprocess.TimeoutExpired:
            pass

        return 0

    except Exception as e:
        print(f"✗ 启动失败: {e}")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ApkMCP-Auto 统一命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s status                    # 查看工具状态
    %(prog)s config                    # 生成 MCP 配置
    %(prog)s config -o config.json     # 保存到指定文件
    %(prog)s install                   # 安装所有依赖
    %(prog)s install apktool           # 安装 apktool 依赖
    %(prog)s list                      # 列出所有工具
    %(prog)s start apktool             # 启动 apktool 服务器
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    status_parser = subparsers.add_parser("status", help="查看工具状态")
    status_parser.set_defaults(func=cmd_status)

    config_parser = subparsers.add_parser("config", help="生成 MCP 配置")
    config_parser.add_argument("-o", "--output", help="输出文件路径")
    config_parser.add_argument("-p", "--preview", action="store_true", help="预览配置")
    config_parser.set_defaults(func=cmd_config)

    install_parser = subparsers.add_parser("install", help="安装依赖")
    install_parser.add_argument("tool", nargs="?", help="工具名称 (可选，不指定则安装所有)")
    install_parser.set_defaults(func=cmd_install)

    list_parser = subparsers.add_parser("list", help="列出所有工具")
    list_parser.set_defaults(func=cmd_list)

    start_parser = subparsers.add_parser("start", help="启动指定工具")
    start_parser.add_argument("tool", help="工具名称")
    start_parser.set_defaults(func=cmd_start)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
