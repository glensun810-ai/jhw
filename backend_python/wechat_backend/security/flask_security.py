"""
安全增强的 Flask 应用配置
"""

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
import os

def create_secure_app():
    """创建安全增强的 Flask 应用"""
    app = Flask(__name__)

    # 基本安全配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None

    # CSRF 保护
    csrf = CSRFProtect(app)

    # 安全头设置
    csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' cdn.jsdelivr.net",
        'style-src': "'self' 'unsafe-inline' cdn.jsdelivr.net",
        'img-src': "'self' data: https:",
        'font-src': "'self' fonts.gstatic.com",
        'connect-src': "'self' https://api.deepseek.com https://dashscope.aliyuncs.com",
    }

    # 开发环境不强制 HTTPS，生产环境才启用
    is_production = os.environ.get('FLASK_ENV') == 'production'
    
    Talisman(app,
             force_https=is_production,  # 仅生产环境强制 HTTPS
             strict_transport_security=is_production,
             content_security_policy=csp,
             frame_options='DENY')

    return app, csrf
