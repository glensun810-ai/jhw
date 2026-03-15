#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信小程序后端服务 - 主启动文件
直接启动 app.py 模块
"""

import sys
import os

# 添加路径
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

if __name__ == '__main__':
    # 直接运行 app.py 模块
    from wechat_backend import app
    
    # app.py 的 __main__ 会自动启动 WebSocket 服务和 Flask 应用
    # 这里只需要导入即可
    print("=" * 60)
    print("微信小程序后端服务")
    print("=" * 60)
    print("🚀 启动服务...")
    print("   Flask 端口：5000")
    print("   WebSocket 端口：8765")
    print("=" * 60)
    
    # 运行 app.py 的 main 块
    import wechat_backend.app
    # 触发 __main__ 执行
    exec(open(os.path.join(base_dir, 'wechat_backend', 'app.py')).read())
