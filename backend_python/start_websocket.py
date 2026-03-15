#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket 服务启动脚本
独立启动 WebSocket 服务
"""

import sys
import os
import asyncio

# 添加路径
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

wechat_backend_dir = os.path.join(base_dir, 'wechat_backend')
if wechat_backend_dir not in sys.path:
    sys.path.insert(0, wechat_backend_dir)

async def start_websocket():
    """启动 WebSocket 服务"""
    try:
        from websockets import serve
        from wechat_backend.websocket_route import handle_websocket_connection
        
        print("🚀 启动 WebSocket 服务...")
        print("   监听地址：ws://127.0.0.1:8765")
        
        async with serve(handle_websocket_connection, "0.0.0.0", 8765):
            print("✅ WebSocket 服务已启动")
            print("   连接地址：ws://127.0.0.1:8765/ws/diagnosis/{execution_id}")
            await asyncio.Future()  # 保持运行
            
    except Exception as e:
        print(f"❌ WebSocket 服务启动失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("微信小程序 WebSocket 服务")
    print("=" * 60)
    asyncio.run(start_websocket())
