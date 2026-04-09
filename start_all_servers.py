# -*- coding: utf-8 -*-
"""
MCP Server 启动脚本
支持启动所有或指定服务器

功能：
- 批量启动 MCP 服务器
- 支持指定服务器列表
- 自动检测服务器状态
- 支持 HTTP 模式和 stdio 模式

作者：AI Assistant
"""

import subprocess
import os
import sys
import time
import argparse
import signal
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()

# MCP 服务器配置
SERVERS_CONFIG = {
    "jadx": {
        "name": "JADX MCP Server",
        "script": PROJECT_ROOT / "java" / "jadx-mcp-server" / "jadx-mcp-server" / "jadx_mcp_server.py",
        "port": 8651,
        "args": []
    },
    "apktool": {
        "name": "APKTool MCP Server",
        "script": PROJECT_ROOT / "java" / "apktool-mcp-server" / "apktool-mcp-server" / "apktool_mcp_server.py",
        "port": 8652,
        "args": [
            "--workspace", str(PROJECT_ROOT / "workspace" / "apktool"),
            "--apktool-path", str(PROJECT_ROOT / "java" / "apktool" / "apktool.bat")
        ]
    },
    "adb": {
        "name": "ADB MCP Server",
        "script": PROJECT_ROOT / "adb" / "adb-mcp-server" / "adb_mcp_server.py",
        "port": 8653,
        "args": [
            "--adb-path", str(PROJECT_ROOT / "adb" / "adb.exe")
        ]
    },
    "sign-tools": {
        "name": "Sign Tools MCP Server",
        "script": PROJECT_ROOT / "sign-tools-mcp-server" / "sign-tools-mcp-server" / "sign_tools_mcp_server.py",
        "port": 8654,
        "args": [
            "--workspace", str(PROJECT_ROOT / "workspace" / "sign-tools")
        ]
    },
    "static-analyzer": {
        "name": "Static Analyzer",
        "script": PROJECT_ROOT / "static-analyzer" / "static_analyzer.py",
        "port": None,  # stdio 模式
        "args": []
    },
    "diff-tool": {
        "name": "Diff Tool",
        "script": PROJECT_ROOT / "diff-tool" / "diff_tool.py",
        "port": None,  # stdio 模式
        "args": []
    }
}


class ServerManager:
    """MCP 服务器管理器"""

    def __init__(self):
        self.running_processes: Dict[str, subprocess.Popen] = {}
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """设置信号处理器，确保程序退出时关闭所有子进程"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """信号处理器"""
        print("\n接收到终止信号，正在关闭所有服务器...")
        self.stop_all_servers()
        sys.exit(0)

    def check_script_exists(self, server_key: str) -> bool:
        """
        检查服务器脚本是否存在

        参数:
            server_key: 服务器标识

        返回:
            脚本是否存在
        """
        config = SERVERS_CONFIG.get(server_key)
        if not config:
            return False
        return config["script"].exists()

    def start_server(self, server_key: str, http_mode: bool = False) -> Optional[subprocess.Popen]:
        """
        启动单个服务器

        参数:
            server_key: 服务器标识
            http_mode: 是否使用 HTTP 模式

        返回:
            子进程对象，失败返回 None
        """
        config = SERVERS_CONFIG.get(server_key)
        if not config:
            print(f"[错误] 未知的服务器: {server_key}")
            return None

        if not self.check_script_exists(server_key):
            print(f"[错误] 服务器脚本不存在: {config['script']}")
            return None

        # 构建命令
        cmd = [sys.executable, str(config["script"])]

        # 添加 HTTP 模式参数
        if http_mode and config["port"]:
            cmd.extend(["--http", "--port", str(config["port"])])

        # 添加额外参数
        cmd.extend(config["args"])

        try:
            print(f"[启动] {config['name']}...")
            if http_mode and config["port"]:
                print(f"       HTTP 模式，端口: {config['port']}")
            else:
                print(f"       stdio 模式")

            # 启动子进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            self.running_processes[server_key] = process
            print(f"[成功] {config['name']} 已启动 (PID: {process.pid})")
            return process

        except Exception as e:
            print(f"[错误] 启动 {config['name']} 失败: {e}")
            return None

    def stop_server(self, server_key: str):
        """
        停止单个服务器

        参数:
            server_key: 服务器标识
        """
        if server_key not in self.running_processes:
            return

        process = self.running_processes[server_key]
        config = SERVERS_CONFIG.get(server_key, {})
        name = config.get("name", server_key)

        try:
            print(f"[停止] {name} (PID: {process.pid})...")

            # Windows 上使用 taskkill
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                              capture_output=True)
            else:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

            del self.running_processes[server_key]
            print(f"[成功] {name} 已停止")

        except Exception as e:
            print(f"[错误] 停止 {name} 失败: {e}")

    def stop_all_servers(self):
        """停止所有运行的服务器"""
        for server_key in list(self.running_processes.keys()):
            self.stop_server(server_key)

    def get_server_status(self, server_key: str) -> Dict:
        """
        获取服务器状态

        参数:
            server_key: 服务器标识

        返回:
            状态信息字典
        """
        config = SERVERS_CONFIG.get(server_key, {})
        process = self.running_processes.get(server_key)

        status = {
            "key": server_key,
            "name": config.get("name", server_key),
            "script_exists": self.check_script_exists(server_key),
            "running": False,
            "pid": None
        }

        if process:
            status["pid"] = process.pid
            status["running"] = process.poll() is None

        return status

    def list_all_servers(self):
        """列出所有服务器及其状态"""
        print("\n" + "=" * 80)
        print("MCP 服务器列表")
        print("=" * 80)
        print(f"{'服务器':<25} {'状态':<12} {'PID':<10} {'脚本存在':<10}")
        print("-" * 80)

        for key in SERVERS_CONFIG.keys():
            status = self.get_server_status(key)
            state = "运行中" if status["running"] else "已停止"
            pid = str(status["pid"]) if status["pid"] else "-"
            exists = "是" if status["script_exists"] else "否"
            print(f"{status['name']:<25} {state:<12} {pid:<10} {exists:<10}")

        print("=" * 80)

    def print_banner(self):
        """打印启动横幅"""
        print("=" * 80)
        print("Android 逆向工程 MCP 工具套件")
        print("MCP Server 启动管理器")
        print("=" * 80)
        print()


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数

    返回:
        解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="MCP Server 启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动所有服务器
  python start_all_servers.py

  # 启动指定服务器
  python start_all_servers.py --servers jadx,apktool,adb

  # 使用 HTTP 模式启动
  python start_all_servers.py --http

  # 仅列出服务器状态
  python start_all_servers.py --list

可用服务器:
  - jadx: JADX MCP Server
  - apktool: APKTool MCP Server
  - adb: ADB MCP Server
  - sign-tools: Sign Tools MCP Server
  - static-analyzer: Static Analyzer
  - diff-tool: Diff Tool
        """
    )

    parser.add_argument(
        "--servers",
        type=str,
        default="all",
        help="要启动的服务器，逗号分隔（默认: all）"
    )

    parser.add_argument(
        "--http",
        action="store_true",
        help="使用 HTTP 模式启动（仅支持部分服务器）"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出服务器状态，不启动"
    )

    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="启动后等待的秒数（默认: 0，即无限等待）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    manager = ServerManager()
    manager.print_banner()

    # 仅列出状态
    if args.list:
        manager.list_all_servers()
        return

    # 确定要启动的服务器
    if args.servers.lower() == "all":
        servers_to_start = list(SERVERS_CONFIG.keys())
    else:
        servers_to_start = [s.strip() for s in args.servers.split(",")]

    # 验证服务器名称
    invalid_servers = [s for s in servers_to_start if s not in SERVERS_CONFIG]
    if invalid_servers:
        print(f"[警告] 忽略未知的服务器: {', '.join(invalid_servers)}")
        servers_to_start = [s for s in servers_to_start if s in SERVERS_CONFIG]

    if not servers_to_start:
        print("[错误] 没有有效的服务器需要启动")
        return

    print(f"准备启动 {len(servers_to_start)} 个服务器:")
    for key in servers_to_start:
        config = SERVERS_CONFIG[key]
        print(f"  - {config['name']}")
    print()

    # 启动服务器
    started_count = 0
    for server_key in servers_to_start:
        process = manager.start_server(server_key, http_mode=args.http)
        if process:
            started_count += 1
        time.sleep(0.5)  # 避免同时启动造成冲突

    print()
    print(f"成功启动 {started_count}/{len(servers_to_start)} 个服务器")
    print()

    # 显示状态
    manager.list_all_servers()

    # 等待模式
    if args.wait > 0:
        print(f"\n等待 {args.wait} 秒后自动关闭...")
        try:
            time.sleep(args.wait)
        except KeyboardInterrupt:
            pass
        manager.stop_all_servers()
    else:
        print("\n按 Ctrl+C 停止所有服务器")
        try:
            while True:
                time.sleep(1)
                # 检查是否有进程退出
                for key, process in list(manager.running_processes.items()):
                    if process.poll() is not None:
                        config = SERVERS_CONFIG[key]
                        print(f"\n[警告] {config['name']} 已退出")
                        del manager.running_processes[key]

                if not manager.running_processes:
                    print("\n所有服务器已停止")
                    break
        except KeyboardInterrupt:
            pass
        finally:
            manager.stop_all_servers()


if __name__ == "__main__":
    main()
