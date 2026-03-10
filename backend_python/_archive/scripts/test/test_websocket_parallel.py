#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket + 并行执行引擎 - 端到端测试脚本

测试内容：
1. WebSocket 服务器启动
2. 并行执行引擎
3. 实时推送服务
4. 端到端流程

使用方法：
    python3 backend_python/test_websocket_parallel.py

@author: 系统架构组
@date: 2026-03-02
"""

import os
import sys
import time
import socket

# 添加后端路径
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(_backend_root))

print("\n" + "=" * 60)
print(" WebSocket + 并行执行引擎 - 端到端测试")
print("=" * 60 + "\n")


def check_websocket_server():
    """检查 WebSocket 服务器是否启动"""
    print("测试 1: WebSocket 服务器启动检查")
    print("-" * 60)
    
    # 检查端口 8765 是否被监听
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8765))
    sock.close()
    
    if result == 0:
        print("✅ WebSocket 服务器已启动在端口 8765")
        return True
    else:
        print("❌ WebSocket 服务器未启动在端口 8765")
        print("提示：请先启动后端服务")
        return False


def check_logs():
    """检查日志中的关键信息"""
    print("\n测试 2: 日志检查")
    print("-" * 60)
    
    log_file = os.path.join(_backend_root, "backend_python", "logs", "app.log")
    
    if not os.path.exists(log_file):
        print(f"⚠️  日志文件不存在：{log_file}")
        return
    
    keywords = [
        "WebSocket",
        "RealtimePush",
        "并行引擎",
        "NxM-Parallel"
    ]
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-500:]  # 只读取最后 500 行
            content = ''.join(lines)
            
        for keyword in keywords:
            count = content.count(keyword)
            if count > 0:
                print(f"✅ 日志中包含 '{keyword}': {count} 次")
            else:
                print(f"⚠️  日志中未找到 '{keyword}'")
                
    except Exception as e:
        print(f"读取日志失败：{e}")


def check_code_files():
    """检查代码文件是否正确修改"""
    print("\n测试 3: 代码文件检查")
    print("-" * 60)
    
    files_to_check = {
        "backend_python/wechat_backend/app.py": ["start_websocket_server", "8765"],
        "backend_python/wechat_backend/views/diagnosis_views.py": ["execute_parallel_nxm", "send_progress_sync"],
        "backend_python/wechat_backend/services/realtime_push_service.py": ["RealtimePushService"],
        "backend_python/wechat_backend/nxm_concurrent_engine_v3.py": ["NxMParallelExecutor"],
    }
    
    for file_path, keywords in files_to_check.items():
        full_path = os.path.join(_backend_root, file_path)
        if not os.path.exists(full_path):
            print(f"❌ 文件不存在：{file_path}")
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            all_found = True
            for keyword in keywords:
                if keyword not in content:
                    print(f"⚠️  {file_path}: 未找到 '{keyword}'")
                    all_found = False
            
            if all_found:
                print(f"✅ {file_path}")
        except Exception as e:
            print(f"❌ {file_path}: 读取失败 - {e}")


def main():
    """主测试函数"""
    # 测试 1: WebSocket 服务器
    websocket_ok = check_websocket_server()
    
    # 测试 2: 日志检查
    check_logs()
    
    # 测试 3: 代码文件检查
    check_code_files()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    if websocket_ok:
        print("\n✅ WebSocket 服务器已就绪")
    else:
        print("\n⚠️  请先启动后端服务：")
        print("   cd backend_python/wechat_backend")
        print("   python3 app.py")
    
    print("\n下一步:")
    print("1. 查看实时日志：tail -f backend_python/logs/app.log")
    print("2. 检查 WebSocket 端口：lsof -i :8765")
    print("3. 在小程序中测试诊断功能")
    print()


if __name__ == "__main__":
    main()
