"""
身份验证和授权模块
支持微信小程序会话认证和JWT令牌认证
"""

try:
    import jwt
except ImportError:
    jwt = None

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
from functools import wraps
from flask import request, jsonify, g

# 尝试从项目根目录导入配置
try:
    from config import Config
except ImportError:
    # 如果直接导入失败，创建一个默认配置类
    class Config:
        SECRET_KEY = ""  # 生产环境中必须通过环境变量设置
        LOG_LEVEL = "INFO"
        LOG_FILE = "logs/app.log"
        LOG_MAX_BYTES = 10485760  # 10MB
        LOG_BACKUP_COUNT = 5
        # WeChat配置
        WECHAT_APP_ID = ""
        WECHAT_APP_SECRET = ""
        WECHAT_TOKEN = ""  # 生产环境中必须通过环境变量设置
        WECHAT_ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
        WECHAT_CODE_TO_SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
        DEBUG = False  # 生产环境中应为False

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """身份验证错误"""
    pass


class AuthorizationError(Exception):
    """授权错误"""
    pass


class JWTManager:
    """JWT管理器"""

    def __init__(self, secret_key: str = None, algorithm: str = 'HS256'):
        if jwt is None:
            raise RuntimeError("PyJWT is required for JWT functionality. Please install it with 'pip install PyJWT'")

        self.secret = secret_key or Config.SECRET_KEY
        self.algorithm = algorithm

    def generate_token(self, user_id: str, expires_delta: timedelta = None, additional_claims: Dict = None) -> str:
        """生成JWT令牌"""
        if jwt is None:
            raise RuntimeError("PyJWT is required for JWT functionality")

        if expires_delta is None:
            expires_delta = timedelta(hours=24)  # 默认24小时过期

        now = datetime.utcnow()
        payload = {
            'user_id': user_id,
            'iat': now,
            'exp': now + expires_delta
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> Dict:
        """解码JWT令牌"""
        if jwt is None:
            raise RuntimeError("PyJWT is required for JWT functionality")

        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("令牌已过期")
        except jwt.InvalidTokenError:
            raise AuthenticationError("无效的令牌")

    def verify_token(self, token: str, expected_user_id: str = None) -> bool:
        """验证JWT令牌"""
        if jwt is None:
            raise RuntimeError("PyJWT is required for JWT functionality")

        try:
            payload = self.decode_token(token)
            if expected_user_id and payload.get('user_id') != expected_user_id:
                return False
            return True
        except AuthenticationError:
            return False


class PasswordHasher:
    """密码哈希器"""

    @staticmethod
    def hash_password(password: str, salt: str = None) -> str:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(32)

        # 使用SHA-256进行哈希
        pwd_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        return f"{salt}${pwd_hash}"

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """验证密码"""
        if '$' not in hashed_password:
            return False

        salt, stored_hash = hashed_password.split('$')
        pwd_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

        return secrets.compare_digest(pwd_hash, stored_hash)


class AccessControl:
    """访问控制"""

    def __init__(self):
        self.role_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users'],
            'user': ['read', 'write'],
            'guest': ['read']
        }
        self.user_roles = {}  # user_id -> role

    def assign_role(self, user_id: str, role: str):
        """分配角色给用户"""
        if role not in self.role_permissions:
            raise ValueError(f"未知角色: {role}")
        self.user_roles[user_id] = role

    def has_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否有特定权限"""
        role = self.user_roles.get(user_id)
        if not role:
            return False

        permissions = self.role_permissions.get(role, [])
        return permission in permissions

    def require_permission(self, permission: str):
        """装饰器：要求特定权限"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # 假设用户ID已通过身份验证并存储在g对象中
                user_id = getattr(g, 'user_id', None)
                if not user_id:
                    return jsonify({'error': '未认证'}), 401

                if not self.has_permission(user_id, permission):
                    return jsonify({'error': '无权限访问'}), 403

                return f(*args, **kwargs)
            return decorated_function
        return decorator


def require_auth(f):
    """装饰器：要求身份验证（支持JWT和微信会话）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = None
        
        # 首先尝试从JWT令牌获取用户ID
        if jwt:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    payload = jwt_manager.decode_token(token)
                    user_id = payload.get('user_id') or payload.get('openid')
                    if user_id:
                        g.user_id = user_id
                        g.auth_method = 'jwt'
                        logger.debug(f"Authenticated via JWT: {user_id}")
                        return f(*args, **kwargs)
                except AuthenticationError:
                    pass  # JWT验证失败，尝试其他方法
        
        # 如果JWT验证失败，尝试从微信会话获取用户ID
        # 微信小程序通常会在请求头中包含一些标识信息
        wechat_openid = request.headers.get('X-WX-OpenID') or request.headers.get('X-OpenID') or request.headers.get('X-Wechat-OpenID')
        if wechat_openid:
            g.user_id = wechat_openid
            g.auth_method = 'wechat_session'
            logger.debug(f"Authenticated via WeChat session: {wechat_openid}")
            return f(*args, **kwargs)
        
        # 尝试从请求体获取用户信息（某些情况下前端可能传递）
        if request.is_json:
            data = request.get_json()
            if data and 'userOpenid' in data:
                g.user_id = data['userOpenid']
                g.auth_method = 'frontend_passed'
                logger.debug(f"Authenticated via frontend-passed openid: {data['userOpenid']}")
                return f(*args, **kwargs)
        
        # 如果所有认证方法都失败，返回401
        return jsonify({
            'error': 'Authentication required',
            'message': 'Please provide a valid authentication token or WeChat session info',
            'auth_methods': [
                'Authorization: Bearer <token>', 
                'X-WX-OpenID: <openid>', 
                'X-OpenID: <openid>',
                'X-Wechat-OpenID: <openid>',
                'userOpenid in request body'
            ]
        }), 401

    return decorated_function


def require_auth_optional(f):
    """装饰器：可选身份验证（即使认证失败也继续执行）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = None
        
        # 尝试JWT认证
        if jwt:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    payload = jwt_manager.decode_token(token)
                    user_id = payload.get('user_id') or payload.get('openid')
                except AuthenticationError:
                    pass  # JWT验证失败，继续
        
        # 尝试微信会话认证
        if not user_id:
            wechat_openid = request.headers.get('X-WX-OpenID') or request.headers.get('X-OpenID') or request.headers.get('X-Wechat-OpenID')
            if wechat_openid:
                user_id = wechat_openid
        
        # 设置用户ID（即使为None）
        g.user_id = user_id
        g.is_authenticated = user_id is not None
        g.auth_method = 'jwt' if jwt and request.headers.get('Authorization', '').startswith('Bearer ') else 'wechat_session' if user_id else 'none'
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user_id() -> Optional[str]:
    """获取当前认证用户的ID"""
    return getattr(g, 'user_id', None)


def get_auth_method() -> str:
    """获取认证方法"""
    return getattr(g, 'auth_method', 'none')


def is_authenticated() -> bool:
    """检查用户是否已认证"""
    return getattr(g, 'is_authenticated', False)


# 全局实例
try:
    jwt_manager = JWTManager()
except RuntimeError:
    # 如果JWT不可用，设置为None，但不影响其他功能
    jwt_manager = None

access_control = AccessControl()
password_hasher = PasswordHasher()
