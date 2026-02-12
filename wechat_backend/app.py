from flask import Flask, request, jsonify, g
import hashlib
import hmac
import json
import requests
from datetime import datetime
import os

from config import Config

# Initialize logging before other imports to capture all logs
from .logging_config import setup_logging
setup_logging(
    log_level=Config.LOG_LEVEL,
    log_file=Config.LOG_FILE,
    max_bytes=Config.LOG_MAX_BYTES,
    backup_count=Config.LOG_BACKUP_COUNT
)

# Import logger after setting up logging
from .logging_config import app_logger

# Initialize database
from .database import init_db
init_db()

# Security imports
from .security.input_validation import validate_and_sanitize_request, InputValidator, InputSanitizer
from .security.rate_limiting import rate_limit, CombinedRateLimiter

# Conditionally import auth module to handle JWT dependency
try:
    from .security.auth import require_auth, require_auth_optional, get_current_user_id
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
app.config.from_object(Config)

# Add security headers
@app.after_request
def after_request(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    return response

# Register the blueprint
from wechat_backend.views import wechat_bp
app.register_blueprint(wechat_bp)

# Start monitoring system
from wechat_backend.monitoring.monitoring_config import initialize_monitoring
initialize_monitoring()

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
    app.run(debug=Config.DEBUG, host='127.0.0.1', port=5001)