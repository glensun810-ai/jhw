#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask 应用启动文件
使用方法：python run.py

P1 修复：解决 ImportError 相对路径越界问题
P2 修复：统一配置文件加载机制
P3 修复：使用新的目录结构
P4 修复：端口占用自动检测和解决（2026-03-07）
"""

import os
import sys
import socket
import signal
from pathlib import Path
from dotenv import load_dotenv

# =============================================================================
# P1 修复：环境路径固化 (Path Injection)
# 动态将 backend_python 目录添加到 sys.path，确保项目根目录被正确识别
# =============================================================================
base_dir = os.path.dirname(os.path.abspath(__file__))

# 添加 backend_python 根目录到路径（确保 utils 等顶层模块可被导入）
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 添加 src 到路径（新结构）
src_dir = os.path.join(base_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 添加 wechat_backend 到路径
wechat_backend_dir = os.path.join(base_dir, 'wechat_backend')
if wechat_backend_dir not in sys.path:
    sys.path.insert(0, wechat_backend_dir)

# =============================================================================
# P2 修复：统一配置文件加载机制
# 加载项目根目录的 .env 文件，确保配置一致性
# =============================================================================
# 获取项目根目录
root_dir = Path(base_dir).parent
env_file = root_dir / '.env'

# 加载 .env 文件
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ 已加载配置文件：{env_file}")
else:
    print(f"⚠️  未找到配置文件：{env_file}")
    print(f"   请确保项目根目录下存在 .env 文件")

def create_app():
    """创建应用实例 - 从 wechat_backend 导入现有的 app 实例"""
    from wechat_backend.app import app
    return app

# 创建应用实例
app = create_app()


def check_port_available(port: int) -> bool:
    """
    检查端口是否可用
    
    Args:
        port: 要检查的端口号
    
    Returns:
        bool: 端口是否可用
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False


def find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """
    查找可用的端口
    
    Args:
        start_port: 起始端口号
        max_attempts: 最大尝试次数
    
    Returns:
        int: 可用的端口号
    """
    for attempt in range(max_attempts):
        port = start_port + attempt
        if check_port_available(port):
            return port
    
    # 如果所有端口都不可用，返回 0 让系统自动分配
    return 0


def kill_process_on_port(port: int) -> bool:
    """
    尝试终止占用端口的进程
    
    Args:
        port: 端口号
    
    Returns:
        bool: 是否成功终止进程
    """
    try:
        # macOS/Linux: 使用 lsof 查找占用端口的进程
        import subprocess
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"✅ Terminated process {pid} on port {port}")
                except Exception as e:
                    print(f"⚠️  Failed to terminate process {pid}: {e}")
            return True
    except Exception as e:
        print(f"⚠️  Failed to kill process on port {port}: {e}")
    
    return False


def setup_port(port: int) -> int:
    """
    设置端口，如果端口被占用则自动解决
    
    Args:
        port: 期望的端口号
    
    Returns:
        int: 实际使用的端口号
    """
    # 检查端口是否可用
    if check_port_available(port):
        return port
    
    print(f"⚠️  Port {port} is already in use")
    
    # 尝试终止占用端口的进程
    if kill_process_on_port(port):
        # 等待进程终止
        import time
        time.sleep(1)
        
        # 再次检查端口是否可用
        if check_port_available(port):
            print(f"✅ Port {port} is now available")
            return port
    
    # 如果无法终止进程，尝试下一个可用端口
    print(f"⚠️  Trying to find alternative port...")
    available_port = find_available_port(port + 1)
    
    if available_port > 0:
        print(f"✅ Using alternative port {available_port}")
        return available_port
    else:
        print(f"❌ No available port found, system will auto-assign")
        return 0


if __name__ == '__main__':
    # P2-1 修复：应用优化的日志配置
    try:
        from wechat_backend.log_level_config import setup_optimized_logging, OPTIMIZATION_TIPS
        setup_optimized_logging()
        print("✅ P2-1: 优化的日志配置已应用")
    except Exception as e:
        print(f"⚠️  日志优化配置加载失败：{e}")
        print("   使用默认日志配置")

    # 直接运行时的配置 - 使用 5001 端口（5000 可能被 macOS Control Center 占用）
    default_port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes')

    # 【P4 修复 - 2026-03-07】自动解决端口占用问题
    port = setup_port(default_port)

    print(f"🚀 Starting WeChat Backend API server on port {port}")
    print(f"🔧 Debug mode: {'on' if debug else 'off'}")
    print(f"📝 Log file: logs/app.log")
    print(f"📁 Using new directory structure: src/")

    # 【P0-DB-INIT-001 修复】禁用 reloader 避免双进程竞争导致数据库初始化异常
    # 保留 debug=True 用于开发调试，但 use_reloader=False 防止重启动器产生子进程
    app.run(
        host='127.0.0.1',
        port=port,
        debug=debug,
        use_reloader=False,  # 禁用 reloader 避免双进程竞争
        threaded=True        # 启用多线程处理请求
    )
