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
from wechat_backend.security.auth_enhanced import enforce_auth_middleware

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

# Register Diagnosis API blueprints (诊断报告 API)
from wechat_backend.views.diagnosis_api import register_diagnosis_api
register_diagnosis_api(app)

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

# Register PDF Export API v2 blueprints (增强版 PDF 报告导出)
from wechat_backend.views_pdf_export_v2 import register_blueprints as register_pdf_export_blueprints_v2
register_pdf_export_blueprints_v2(app)

# Register Cache API blueprints (API 缓存)
from wechat_backend.cache.api_cache import cache_bp, start_cache_maintenance
app.register_blueprint(cache_bp)
start_cache_maintenance()

# Initialize database query optimization (数据库查询优化)
from wechat_backend.database.query_optimizer import init_recommended_indexes
init_recommended_indexes()

# Register auth middleware (差距 1 修复：API 认证授权增强)
app.before_request(enforce_auth_middleware())

# 豁免 API 端点的 CSRF 验证（用于小程序 API 请求）
# 注意：CSRF 主要用于保护 Web 表单，API 使用 Token 认证，无需 CSRF 保护
# 通过设置 request.csrf_exempt = True 来豁免 CSRF 检查
@app.before_request
def csrf_exempt_api():
    if request.path.startswith('/api/') or request.path.startswith('/test/'):
        request.csrf_exempt = True

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
            from config import Config  # P0-1 修复
            # P0-1 修复：直接使用 Config 类
            api_key = Config.get_api_key(adapter_name)

            if api_key:
                # Create adapter with actual API key if available
                adapter = AIAdapterFactory.create(adapter_name, api_key)

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

# P2-1 优化：启动 SSE 清理线程并注册路由
try:
    from wechat_backend.services.sse_service_v2 import start_cleanup_thread as sse_start_cleanup, register_sse_routes
    sse_start_cleanup(interval=60)  # 每 60 秒清理一次过期连接
    register_sse_routes(app)  # 注册 SSE 路由
    app_logger.info("✅ SSE 服务已启动")
except Exception as e:
    app_logger.warning(f"⚠️  SSE 服务启动失败：{e}")

# P3-2 优化：启动配置热更新
try:
    # 修复导入路径：直接导入 backend_python.config 模块
    import sys
    from pathlib import Path
    
    # 添加 backend_python 到路径
    backend_root = Path(__file__).parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    
    # 直接导入配置模块，避免与 wechat_backend.config 冲突
    import importlib.util
    hot_reload_path = backend_root / 'config' / 'hot_reload_config.py'
    spec = importlib.util.spec_from_file_location("hot_reload_config", hot_reload_path)
    hot_reload_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hot_reload_module)
    
    get_hot_reload_config = hot_reload_module.get_hot_reload_config
    register_config_routes = hot_reload_module.register_config_routes
    
    hot_reload_config = get_hot_reload_config()
    register_config_routes(app)  # 注册配置管理路由
    app_logger.info("✅ 配置热更新已启动")
    app_logger.info("[HotReloadConfig] 路由已注册")
except Exception as e:
    app_logger.warning(f"⚠️  配置热更新启动失败：{e}")
    import traceback
    app_logger.error(f"[HotReloadConfig] 错误详情：{traceback.format_exc()}")

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


# ==================== P2-020 新增：监控大盘 API ====================

@app.route('/api/monitoring/dashboard', methods=['GET'])
@rate_limit(limit=30, window=60, per='ip')  # 每分钟 30 次
def get_monitoring_dashboard_api():
    """
    获取监控大盘数据
    
    查询参数：
        period: 时间周期 ('today', 'week', 'month'), 默认 'today'
    
    返回：
        监控大盘数据
    """
    try:
        from wechat_backend.services.diagnosis_monitor_service import get_monitoring_dashboard
        
        period = request.args.get('period', 'today')
        if period not in ['today', 'week', 'month']:
            period = 'today'
        
        dashboard_data = get_monitoring_dashboard(period)
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        app_logger.error(f"[P2-020 监控] 获取大盘数据失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/monitoring/recent', methods=['GET'])
@rate_limit(limit=30, window=60, per='ip')
def get_recent_diagnosis_api():
    """
    获取最近的诊断列表

    查询参数：
        limit: 返回数量限制，默认 20

    返回：
        诊断列表
    """
    try:
        from wechat_backend.services.diagnosis_monitor_service import get_recent_diagnosis_list

        limit = min(int(request.args.get('limit', '20')), 100)  # 最多 100 条

        recent_list = get_recent_diagnosis_list(limit)

        return jsonify({
            'success': True,
            'data': recent_list,
            'count': len(recent_list)
        })

    except Exception as e:
        app_logger.error(f"[P2-020 监控] 获取最近诊断列表失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/admin/monitoring')
@require_auth  # P0-005 修复：添加身份验证
def monitoring_dashboard_page():
    """
    监控大盘前端页面
    
    P0-005 修复：添加权限验证，仅允许认证用户访问
    """
    try:
        from flask import send_file
        import os

        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'pages', 'admin', 'monitoring-dashboard.html'
        )

        if os.path.exists(dashboard_path):
            return send_file(dashboard_path)
        else:
            return jsonify({
                'error': '监控大盘页面文件不存在',
                'path': dashboard_path
            }), 404

    except Exception as e:
        app_logger.error(f"[监控大盘] 页面加载失败：{e}")
        return jsonify({
            'error': str(e)
        }), 500


# ==================== P1-015 新增：WAL 恢复机制 ====================

def initialize_wal_recovery():
    """
    初始化 WAL 恢复机制
    
    功能：
    1. 清理过期的 WAL 文件（超过 24 小时）
    2. 检查是否有未完成的执行需要恢复
    3. 记录恢复统计信息
    
    注意：此函数在服务启动时调用，不影响现有请求
    """
    try:
        from wechat_backend.nxm_execution_engine import cleanup_expired_wal, read_wal
        import glob
        import os
        
        app_logger.info("[WAL 恢复] 开始初始化 WAL 恢复机制...")
        
        # 1. 清理过期 WAL 文件
        cleanup_expired_wal(max_age_hours=24)
        app_logger.info("[WAL 恢复] 过期 WAL 文件清理完成")
        
        # 2. 检查未完成的执行
        wal_dir = '/tmp/nxm_wal'
        if os.path.exists(wal_dir):
            wal_files = glob.glob(os.path.join(wal_dir, 'nxm_wal_*.pkl'))
            incomplete_count = 0
            
            for wal_file in wal_files:
                try:
                    filename = os.path.basename(wal_file)
                    execution_id = filename.replace('nxm_wal_', '').replace('.pkl', '')
                    wal_data = read_wal(execution_id)
                    
                    if wal_data:
                        completed = wal_data.get('completed', 0)
                        total = wal_data.get('total', 0)
                        
                        if completed < total:
                            incomplete_count += 1
                            app_logger.warning(
                                f"[WAL 恢复] 发现未完成执行：{execution_id}, "
                                f"进度：{completed}/{total} ({completed*100//max(total,1)}%)"
                            )
                except Exception as e:
                    app_logger.error(f"[WAL 恢复] 检查 WAL 文件失败：{wal_file}, 错误：{e}")
            
            if incomplete_count > 0:
                # P1-003 修复：降低日志级别为 INFO，避免日志过多
                app_logger.info(
                    f"[WAL 恢复] 发现 {incomplete_count} 个未完成的执行，"
                    f"用户重新访问时可从 WAL 恢复进度"
                )
            else:
                app_logger.info("[WAL 恢复] 所有 WAL 执行均已完成或已过期")
        
        app_logger.info("[WAL 恢复] WAL 恢复机制初始化完成")
        
    except Exception as e:
        app_logger.error(f"[WAL 恢复] 初始化失败：{e}\n{traceback.format_exc()}")


if __name__ == '__main__':
    # P1-015 新增：在服务启动时初始化 WAL 恢复机制
    initialize_wal_recovery()
    
    # Explicitly specify host and port to align with frontend contract
    # Using standard Flask port 5000 for consistency
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)