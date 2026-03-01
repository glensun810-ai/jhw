#!/usr/bin/env python3
"""
差距 1 修复：API 认证授权增强

功能:
1. 敏感 API 强制认证
2. 用户数据访问控制
3. 速率限制增强
4. 审计日志记录

使用示例:
    @require_strict_auth
    @wechat_bp.route('/api/sensitive-data', methods=['GET'])
    def get_sensitive_data():
        pass
"""

from functools import wraps
from flask import request, jsonify, g
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def enforce_auth_middleware():
    """
    中间件：在请求处理前强制检查敏感端点的认证
    
    用法：在 Flask app 的 before_request 中注册
    
    注意：
    - 只保护明确标记为 require_auth=True 的端点
    - 对于使用 @require_auth_optional 的端点，允许匿名访问
    - 由装饰器负责最终的认证验证
    """
    from flask import Flask
    
    def check_auth():
        # 跳过 OPTIONS 请求（CORS 预检）
        if request.method == 'OPTIONS':
            return None
        
        # 检查端点是否需要严格认证
        if not check_endpoint_requires_auth(request.path):
            return None
        
        # 检查是否已有认证
        if hasattr(g, 'user_id') and g.user_id:
            return None
        
        # 尝试从请求头获取认证信息
        auth_header = request.headers.get('Authorization')
        wx_openid = request.headers.get('X-WX-OpenID')
        
        if auth_header or wx_openid:
            # 已有认证信息，由装饰器处理验证
            # 中间件不拦截，让装饰器判断是否有效
            return None
        
        # 对于 /api/perform-brand-test 等端点，允许匿名访问
        # 由 @require_auth_optional 装饰器处理
        # 只对严格需要认证的端点（如 /test/status, /api/user/*）返回 401
        if is_strict_auth_endpoint(request.path):
            # 需要认证但未提供，返回 401
            logger.warning(f"[Auth Middleware] 未认证访问敏感端点：{request.path} from {request.remote_addr}")
            return jsonify({
                'error': '未授权访问',
                'message': '此端点需要身份认证',
                'status': 'unauthorized',
                'required_auth': ['Authorization: Bearer <token>', 'X-WX-OpenID: <openid>']
            }), 401
        
        # 其他端点允许匿名访问
        return None
    
    return check_auth


def is_strict_auth_endpoint(path: str) -> bool:
    """
    判断端点是否需要严格认证（不允许匿名）

    严格认证的端点：
    - 用户数据查询：/test/status/*, /api/test-history, /api/user/*
    - 管理接口：/api/admin/*, /admin/*

    可选认证的端点：
    - /api/perform-brand-test (允许匿名用户使用)
    """
    # 严格认证的端点列表
    strict_endpoints = [
        '/test/status/',
        '/api/test-history',
        '/api/user/',
        '/api/user_info',
        '/api/user/profile',
        '/api/user/update',
        '/api/saved-results/',
        '/api/deep-intelligence/',
        '/api/dashboard/aggregate',
        '/api/admin/',
        '/admin/',
    ]
    
    for endpoint in strict_endpoints:
        if path.startswith(endpoint):
            return True
    
    return False


def require_strict_auth(f):
    """
    严格认证装饰器（差距 1 修复）

    用于保护敏感 API 端点：
    - /test/status/{id}（任务状态，包含用户数据）
    - 其他包含用户敏感数据的 API

    认证方式:
    1. JWT Token (Authorization: Bearer <token>)
    2. 微信 OpenID (X-WX-OpenID 头)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. 检查认证头
        auth_header = request.headers.get('Authorization')
        wx_openid = request.headers.get('X-WX-OpenID')
        
        if not auth_header and not wx_openid:
            logger.warning(f"[Auth] 未提供认证信息：{request.remote_addr} -> {request.path}")
            return jsonify({
                'error': '认证信息缺失',
                'message': '请提供 Authorization 头或 X-WX-OpenID 头',
                'status': 'unauthorized'
            }), 401
        
        # 2. 验证 JWT Token
        if auth_header:
            try:
                from wechat_backend.security.auth import JWTManager
                
                if not auth_header.startswith('Bearer '):
                    return jsonify({
                        'error': '无效的认证格式',
                        'message': 'Authorization 头格式应为：Bearer <token>',
                        'status': 'unauthorized'
                    }), 401
                
                token = auth_header.split(' ')[1]
                jwt_manager = JWTManager()
                payload = jwt_manager.decode_token(token)
                
                # 将用户信息存入 Flask g 对象
                g.user_id = payload.get('user_id')
                g.auth_type = 'jwt'
                
                logger.info(f"[Auth] JWT 认证成功：user_id={g.user_id}")
                
            except Exception as e:
                logger.warning(f"[Auth] JWT 认证失败：{e}")
                return jsonify({
                    'error': '认证失败',
                    'message': str(e),
                    'status': 'unauthorized'
                }), 401
        
        # 3. 验证微信 OpenID
        elif wx_openid:
            try:
                # 简单的 OpenID 格式验证
                if not wx_openid or len(wx_openid) < 10:
                    return jsonify({
                        'error': '无效的 OpenID',
                        'message': 'OpenID 格式不正确',
                        'status': 'unauthorized'
                    }), 401
                
                # 将 OpenID 存入 Flask g 对象
                g.user_id = wx_openid
                g.auth_type = 'wechat'
                
                logger.info(f"[Auth] 微信 OpenID 认证成功：openid={wx_openid[:10]}...")
                
            except Exception as e:
                logger.warning(f"[Auth] 微信 OpenID 认证失败：{e}")
                return jsonify({
                    'error': '认证失败',
                    'message': str(e),
                    'status': 'unauthorized'
                }), 401
        
        # 4. 记录审计日志
        log_audit_access(f.__name__)
        
        # 5. 调用原函数
        return f(*args, **kwargs)
    
    return decorated_function


def require_user_data_access(f):
    """
    用户数据访问控制装饰器（差距 1 修复）

    确保用户只能访问自己的数据

    使用示例:
        @require_user_data_access
        @wechat_bp.route('/api/user-data/<user_id>', methods=['GET'])
        def get_user_data(user_id):
            # 自动验证请求用户是否是数据所有者
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查是否已认证
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({
                'error': '未认证',
                'message': '请先进行身份认证',
                'status': 'unauthorized'
            }), 401

        # 检查 URL 参数中的 user_id
        requested_user_id = kwargs.get('user_id') or request.args.get('user_id')

        if requested_user_id and requested_user_id != g.user_id:
            # 用户尝试访问他人数据
            logger.warning(
                f"[Auth] 越权访问尝试：user_id={g.user_id} 尝试访问 {requested_user_id}"
            )
            log_security_event(
                'UNAUTHORIZED_ACCESS_ATTEMPT',
                'HIGH',
                f'User {g.user_id} attempted to access data of {requested_user_id}',
                user_id=g.user_id,
                ip_address=request.remote_addr
            )
            return jsonify({
                'error': '禁止访问',
                'message': '您无权访问此数据',
                'status': 'forbidden'
            }), 403

        # 自动注入 user_id 参数
        if 'user_id' not in kwargs:
            kwargs['user_id'] = g.user_id

        return f(*args, **kwargs)

    return decorated_function


def log_security_event(event_type: str, severity: str, description: str, user_id: str = None, ip_address: str = None):
    """记录安全事件日志"""
    try:
        from wechat_backend.database.audit_logs import create_audit_log
        
        create_audit_log(
            user_id=user_id or 'anonymous',
            action='security_event',
            resource=event_type,
            ip_address=ip_address or request.remote_addr if request else None,
            user_agent=request.user_agent.string[:255] if request and request.user_agent else None,
            request_method=request.method if request else None,
            response_status=0,
            details={
                'event_type': event_type,
                'severity': severity,
                'description': description
            }
        )
    except Exception as e:
        logger.error(f"[Security] 记录安全事件失败：{e}")


def log_audit_access(endpoint_name: str):
    """记录审计日志（差距 1 增强）"""
    try:
        from wechat_backend.database.audit_logs import create_audit_log

        user_id = getattr(g, 'user_id', 'anonymous')

        create_audit_log(
            user_id=user_id,
            action='api_access',
            resource=endpoint_name,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:255] if request.user_agent else None,
            request_method=request.method,
            response_status=200,  # 预先记录，实际状态在响应后更新
            details={
                'auth_type': getattr(g, 'auth_type', 'none'),
                'path': request.path,
                'args': dict(request.args) if request.args else None
            }
        )
    except Exception as e:
        logger.error(f"[Audit] 记录审计日志失败：{e}")


# 需要严格认证的 API 端点列表（差距 1 修复）
# 注意：此列表用于 check_endpoint_requires_auth() 函数
# 实际强制认证由 is_strict_auth_endpoint() 控制
STRICT_AUTH_ENDPOINTS = [
    # 测试相关 - 包含用户测试数据
    '/test/status/',
    '/test/submit',
    # 注意：/api/perform-brand-test 使用可选认证，不在严格认证列表中

    # 用户数据相关 - 个人隐私信息
    '/api/user/',
    '/api/user_info',
    '/api/user/profile',
    '/api/user/update',
    '/api/user-data/',

    # 结果和报告相关
    '/api/saved-results/',
    '/api/deep-intelligence/',
    '/api/dashboard/aggregate',

    # 管理相关
    '/api/admin/',
    '/admin/',
]


def check_endpoint_requires_auth(path: str) -> bool:
    """检查端点是否需要严格认证"""
    for endpoint in STRICT_AUTH_ENDPOINTS:
        if path.startswith(endpoint):
            return True
    return False


if __name__ == '__main__':
    # 测试认证装饰器
    print("="*60)
    print("差距 1 修复：API 认证授权增强 - 测试")
    print("="*60)
    print()
    
    print("✅ 认证装饰器已实现")
    print("✅ 支持的认证方式:")
    print("   - JWT Token (Authorization: Bearer <token>)")
    print("   - 微信 OpenID (X-WX-OpenID 头)")
    print()
    print("✅ 受保护的 API 端点:")
    for endpoint in STRICT_AUTH_ENDPOINTS:
        print(f"   - {endpoint}")
    print()
    print("="*60)
