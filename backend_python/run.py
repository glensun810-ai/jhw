#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask 应用启动文件
使用方法: python run.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    """创建应用实例 - 从 wechat_backend 导入现有的 app 实例"""
    from wechat_backend import app
    return app

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    # 直接运行时的配置
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes')

    print(f"🚀 Starting WeChat Backend API server on port {port}")
    print(f"🔧 Debug mode: {'on' if debug else 'off'}")
    print(f"📝 Log file: logs/app.log")

    app.run(
        host='127.0.0.1',
        port=port,
        debug=debug
    )