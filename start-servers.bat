@echo off
chcp 65001 >nul
title MCP Server 启动管理器

REM Android 逆向工程 MCP 工具套件启动脚本
REM 支持启动所有或指定 MCP 服务器

echo ================================================================================
echo Android 逆向工程 MCP 工具套件
echo MCP Server 启动管理器
echo ================================================================================
echo.

REM 设置项目根目录
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)

echo [信息] 项目根目录: %PROJECT_ROOT%
echo [信息] Python 版本:
python --version
echo.

REM 解析参数
if "%~1"=="" goto :show_help
if /i "%~1"=="all" goto :start_all
if /i "%~1"=="list" goto :list_servers
if /i "%~1"=="help" goto :show_help
if /i "%~1"=="-h" goto :show_help
if /i "%~1"=="--help" goto :show_help

REM 启动指定服务器
echo [启动] 启动指定服务器: %*
echo.
cd /d "%PROJECT_ROOT%"
python start_all_servers.py --servers %*
if errorlevel 1 (
    echo.
    echo [错误] 启动失败
    pause
    exit /b 1
)
goto :end

:start_all
echo [启动] 启动所有 MCP 服务器
echo.
cd /d "%PROJECT_ROOT%"
python start_all_servers.py
if errorlevel 1 (
    echo.
    echo [错误] 启动失败
    pause
    exit /b 1
)
goto :end

:list_servers
echo [信息] 列出所有服务器状态
echo.
cd /d "%PROJECT_ROOT%"
python start_all_servers.py --list
echo.
pause
goto :end

:show_help
echo 用法: start-servers.bat [选项]
echo.
echo 选项:
echo   all                    启动所有 MCP 服务器
echo   list                   列出所有服务器状态
echo   jadx,apktool,...       启动指定的服务器（逗号分隔）
echo   help                   显示此帮助信息
echo.
echo 可用服务器:
echo   - jadx              JADX MCP Server
echo   - apktool           APKTool MCP Server
echo   - adb               ADB MCP Server
echo   - sign-tools        Sign Tools MCP Server
echo   - static-analyzer   Static Analyzer
echo   - diff-tool         Diff Tool
echo.
echo 示例:
echo   start-servers.bat all                    启动所有服务器
echo   start-servers.bat jadx,apktool           启动 JADX 和 APKTool
echo   start-servers.bat adb                    仅启动 ADB Server
echo   start-servers.bat list                   查看服务器状态
echo.
pause
goto :end

:end
echo.
echo ================================================================================
echo 操作完成
echo ================================================================================
