#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask 应用启动文件
使用方法：python run.py

P1 修复：解决 ImportError 相对路径越界问题
P2 修复：统一配置文件加载机制
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# =============================================================================
# P1 修复：环境路径固化 (Path Injection)
# 动态将 backend_python 目录添加到 sys.path，确保项目根目录被正确识别
# =============================================================================
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

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

if __name__ == '__main__':
    # 直接运行时的配置 - 使用 5000 端口以与前端保持一致
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes')

    print(f"🚀 Starting WeChat Backend API server on port {port}")
    print(f"🔧 Debug mode: {'on' if debug else 'off'}")
    print(f"📝 Log file: logs/app.log")

    app.run(
        host='127.0.0.1',
        port=port,
        debug=debug
    )
