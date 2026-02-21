from flask import Flask, request, jsonify, g
from flask_cors import CORS
import hashlib
import hmac
import json
import requests
from datetime import datetime
import os

from config import Config

# Initialize logging before other imports to capture all logs
#
from wechat_backend.logging_config import setup_logging
setup_logging(
    log_level=Config.LOG_LEVEL,
    log_file=Config.LOG_FILE,
    max_bytes=Config.LOG_MAX_BYTES,
    backup_count=Config.LOG_BACKUP_COUNT
)

# Import logger after setting up logging
from wechat_backend.logging_config import app_logger

# Initialize database
from wechat_backend.database import init_db
init_db()

# Initialize task status database
from wechat_backend.models import init_task_status_db
init_task_status_db()

# Security imports
from wechat_backend.security.input_validation import validate_and_sanitize_request, InputValidator, InputSanitizer
from wechat_backend.security.rate_limiting import rate_limit, CombinedRateLimiter

# Conditionally import auth module to handle JWT dependency
try:
    from wechat_backend.security.auth import require_auth, require_auth_optional, get_current_user_id
except RuntimeError as e:
    if "PyJWT is required" in str(e):
        # 如果JWT不可用，创建占位符函数
        def require_auth(f):
            from functools import wraps
            from flask import jsonify
            @wraps(f)
            def decorated_function(*args, **kwargs):
                return jsonify({'error': 'Authentication service unavailable'}), 500
            return decorated_function

        def require_auth_optional(f):
            # 可选认证装饰器的占位符 - 不进行认证
            from functools import wraps
            @wraps(f)
            def decorated_function(*args, **kwargs):
                return f(*args, **kwargs)
            return decorated_function

        def get_current_user_id():
            return None
    else:
        raise

# Configuration
APP_ID = Config.WECHAT_APP_ID
APP_SECRET = Config.WECHAT_APP_SECRET

# Global variable to store access token
access_token = None
token_expiration_time = None


def get_access_token():
    """Get access token from WeChat API"""
    global access_token, token_expiration_time

    # Check if token is still valid
    if access_token and token_expiration_time and datetime.now() < datetime.fromtimestamp(token_expiration_time):
        app_logger.debug("Using cached access token")
        return access_token

    # Request new access token
    params = {
        'grant_type': 'client_credential',
        'appid': APP_ID,
        'secret': APP_SECRET
    }

    app_logger.info(f"Requesting new access token for app_id: {APP_ID}")
    response = requests.get(Config.WECHAT_ACCESS_TOKEN_URL, params=params)
    data = response.json()

    if 'access_token' in data:
        access_token = data['access_token']
        expires_in = data.get('expires_in', 7200)  # Default to 2 hours
        token_expiration_time = datetime.now().timestamp() + expires_in - 300  # Refresh 5 min early
        app_logger.info("Successfully obtained new access token")
        return access_token
    else:
        app_logger.error(f"Failed to get access token: {data}")
        raise Exception(f"Failed to get access token: {data}")


# Create Flask app with security enhancements
app = Flask(__name__)
#app.config.from_object(Config)

# Enable CORS BEFORE registering blueprints
# 配置支持微信小程序的跨域请求，包括OPTIONS预检请求
CORS(app, 
     supports_credentials=True, 
     resources={
         r"/api/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-WX-OpenID", "X-OpenID", "X-Wechat-OpenID", "X-Requested-With"],
             "expose_headers": ["Content-Type", "X-Request-ID"],
             "supports_credentials": True
         }
     })

# Register the blueprint AFTER CORS configuration
from wechat_backend.views import wechat_bp
app.register_blueprint(wechat_bp)

# Register GEO Analysis API blueprints (P0 级空缺修复)
from wechat_backend.views_geo_analysis import init_geo_analysis_routes
init_geo_analysis_routes(app)

# Register P1 Analysis API blueprints (P1 级空缺修复)
from wechat_backend.views_p1_analysis import init_p1_analysis_routes
init_p1_analysis_routes(app)

# Register P2 Optimization API blueprints (P2 级空缺修复)
from wechat_backend.views_p2_optimization import init_p2_optimization_routes
init_p2_optimization_routes(app)

# Register Permission Management API blueprints (P1 级后端支持)
from wechat_backend.views_permission import init_permission_routes, init_permission_db
init_permission_routes(app)
init_permission_db()  # 初始化权限数据库表

# Register PDF Export API blueprints (P1-3 报告导出功能)
from wechat_backend.views_pdf_export import init_pdf_export_routes
init_pdf_export_routes(app)

# Register Admin API blueprints (P2-1 管理后台)
from wechat_backend.views_admin import init_admin_routes
init_admin_routes(app)

# Register Analytics API blueprints (P2-2 使用分析)
from wechat_backend.views_analytics import init_analytics_routes
init_analytics_routes(app)

# Register Audit API blueprints (P1-8 审计日志系统)
from wechat_backend.views_audit import init_audit_routes
init_audit_routes(app)

# Register Intelligence Pipeline API blueprints (情报流水线)
from wechat_backend.views_intelligence import register_blueprints as register_intelligence_blueprints
register_intelligence_blueprints(app)

# Register Data Sync API blueprints (数据同步)
from wechat_backend.views_sync import register_blueprints as register_sync_blueprints
register_sync_blueprints(app)

# Register User Behavior Analytics API blueprints (用户行为分析)
from wechat_backend.views_analytics_behavior import register_blueprints as register_analytics_blueprints
register_analytics_blueprints(app)

# Register Audit Log API blueprints (完整审计日志)
from wechat_backend.views_audit_full import register_blueprints as register_audit_full_blueprints
register_audit_full_blueprints(app)

# Register PDF Export API blueprints (PDF 报告导出)
from wechat_backend.views_pdf_export import register_blueprints as register_pdf_export_blueprints
register_pdf_export_blueprints(app)

# Register Cache API blueprints (API 缓存)
from wechat_backend.cache.api_cache import cache_bp, start_cache_maintenance
app.register_blueprint(cache_bp)
start_cache_maintenance()

# Initialize database query optimization (数据库查询优化)
from wechat_backend.database.query_optimizer import init_recommended_indexes
init_recommended_indexes()

# Add security headers
@app.after_request
def after_request(response):
    """Add security headers to all responses"""
    # 不覆盖CORS已经设置的头部
    if 'X-Content-Type-Options' not in response.headers:
        response.headers['X-Content-Type-Options'] = 'nosniff'
    if 'X-Frame-Options' not in response.headers:
        response.headers['X-Frame-Options'] = 'DENY'
    if 'X-XSS-Protection' not in response.headers:
        response.headers['X-XSS-Protection'] = '1; mode=block'
    # 移除可能导致API请求问题的CSP头部
    # response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    return response

# Start monitoring system
from wechat_backend.monitoring.monitoring_config import initialize_monitoring
initialize_monitoring()

def warm_up_adapters():
    """预热所有已注册的API适配器"""
    from wechat_backend.logging_config import api_logger
    from wechat_backend.ai_adapters.factory import AIAdapterFactory

    api_logger.info("Starting adapter warm-up...")

    # List of adapters to warm up
    adapters_to_warm = ['doubao', 'deepseek', 'qwen', 'chatgpt', 'gemini', 'zhipu', 'wenxin']

    for adapter_name in adapters_to_warm:
        try:
            # Try to create a minimal instance for health check
            # We'll use a dummy API key for the warm-up, as the actual key will be validated later
            from config_manager import Config as PlatformConfigManager
            config_manager = PlatformConfigManager()
            platform_config = config_manager.get_platform_config(adapter_name)

            if platform_config and platform_config.api_key:
                # Create adapter with actual API key if available
                adapter = AIAdapterFactory.create(adapter_name, platform_config.api_key, platform_config.default_model or f"test-{adapter_name}")

                # If the adapter has a health check method, call it
                if hasattr(adapter, '_health_check'):
                    adapter._health_check()
                    api_logger.info(f"Adapter {adapter_name} health check completed")
                else:
                    api_logger.info(f"Adapter {adapter_name} created successfully (no health check method)")
            else:
                api_logger.warning(f"Adapter {adapter_name} has no API key configured, skipping warm-up")

        except Exception as e:
            api_logger.warning(f"Adapter {adapter_name} warm-up failed: {e}")

    api_logger.info("Adapter warm-up completed")


# Warm up adapters in a background thread after app initialization
import threading
threading.Thread(target=warm_up_adapters, daemon=True).start()

@app.route('/')
@rate_limit(limit=100, window=60, per='ip')  # 限制每个IP每分钟最多100个请求
def index():
    app_logger.info("Index endpoint accessed")
    return jsonify({
        'message': 'WeChat Mini Program Backend Server',
        'status': 'running',
        'app_id': APP_ID
    })

@app.route('/health')
@rate_limit(limit=1000, window=60, per='ip')  # 健康检查可以更频繁
def health_check():
    app_logger.debug("Health check endpoint accessed")
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/config', methods=['GET'])
@require_auth_optional  # 可选身份验证，支持微信会话
@rate_limit(limit=10, window=60, per='ip')
def get_config():
    """Return basic configuration info"""
    user_id = get_current_user_id() or 'anonymous'
    app_logger.info(f"Configuration endpoint accessed by user: {user_id}")
    return jsonify({
        'app_id': APP_ID,
        'server_time': datetime.now().isoformat(),
        'status': 'active',
        'user_id': user_id
    })


if __name__ == '__main__':
    # Explicitly specify host and port to align with frontend contract
    # Using standard Flask port 5000 for consistency
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)