#!/usr/bin/env python3
"""
审计日志装饰器
用于自动记录管理员操作
"""

from functools import wraps
from flask import request, g
from wechat_backend.audit_logs import save_audit_log
from wechat_backend.security.auth import get_current_user_id


def log_admin_action(resource_type=None, resource_id_field=None):
    """
    审计日志装饰器
    
    Args:
        resource_type: 资源类型（如 'user', 'test', 'platform'）
        resource_id_field: 资源 ID 字段名（如 'user_id', 'test_id'）
        
    使用示例:
        @admin_bp.route('/users/<user_id>/roles', methods=['POST'])
        @require_admin
        @log_admin_action(resource_type='user', resource_id_field='user_id')
        def assign_user_role(user_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            admin_id = get_current_user_id()
            action = f.__name__
            
            # 获取资源类型和 ID
            resource = resource_type or request.endpoint
            resource_id = None
            
            if resource_id_field:
                resource_id = kwargs.get(resource_id_field) or request.args.get(resource_id_field)
            
            # 如果没有指定 resource_id，尝试从 URL 参数获取
            if not resource_id:
                for field in ['id', 'user_id', 'test_id', 'record_id']:
                    if field in kwargs:
                        resource_id = kwargs[field]
                        break
            
            # 获取请求信息
            ip_address = request.headers.get('X-Real-IP') or request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            request_method = request.method
            
            # 获取请求数据（脱敏处理）
            request_data = None
            try:
                if request.is_json:
                    request_data = request.get_json(silent=True)
                    # 脱敏敏感字段
                    if request_data:
                        for sensitive_field in ['password', 'token', 'secret', 'key']:
                            if sensitive_field in request_data:
                                request_data[sensitive_field] = '***'
            except:
                pass
            
            # 执行原函数
            response = None
            error_message = None
            response_status = 200
            
            try:
                response = f(*args, **kwargs)
                
                # 获取响应状态码
                if isinstance(response, tuple):
                    response_status = response[1] if len(response) > 1 else 200
                elif hasattr(response, 'status_code'):
                    response_status = response.status_code
                    
            except Exception as e:
                error_message = str(e)
                response_status = 500
                raise
            
            finally:
                # 记录审计日志
                save_audit_log(
                    admin_id=admin_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_method=request_method,
                    request_data=request_data,
                    response_status=response_status,
                    error_message=error_message
                )
            
            return response
        
        return decorated
    return decorator


def log_batch_action(resource_type=None):
    """
    批量操作审计日志装饰器
    
    与 log_admin_action 的区别：
    - 记录操作的总数量
    - 记录成功/失败数量
    
    使用示例:
        @admin_bp.route('/users/batch-action', methods=['POST'])
        @require_admin
        @log_batch_action(resource_type='user')
        def batch_user_action():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            admin_id = get_current_user_id()
            action = f.__name__
            resource = resource_type or request.endpoint
            
            # 获取请求信息
            ip_address = request.headers.get('X-Real-IP') or request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            request_method = request.method
            
            # 获取请求数据
            request_data = None
            try:
                if request.is_json:
                    request_data = request.get_json(silent=True)
                    # 脱敏处理
                    if request_data:
                        for sensitive_field in ['password', 'token', 'secret', 'key']:
                            if sensitive_field in request_data:
                                request_data[sensitive_field] = '***'
            except:
                pass
            
            # 执行原函数
            response = None
            error_message = None
            response_status = 200
            
            try:
                response = f(*args, **kwargs)
                
                # 获取响应状态码
                if isinstance(response, tuple):
                    response_status = response[1] if len(response) > 1 else 200
                elif hasattr(response, 'status_code'):
                    response_status = response.status_code
                    
            except Exception as e:
                error_message = str(e)
                response_status = 500
                raise
            
            finally:
                # 解析响应数据获取批量操作统计
                processed_count = 0
                failed_count = 0
                
                try:
                    if isinstance(response, tuple) and len(response) > 0:
                        response_data = response[0]
                    elif hasattr(response, 'get_json'):
                        response_data = response.get_json()
                    else:
                        response_data = response
                    
                    if isinstance(response_data, dict):
                        processed_count = response_data.get('processed', 0)
                        failed_count = response_data.get('failed', 0)
                        deleted_count = response_data.get('deleted_count', 0)
                        target_count = response_data.get('target_count', 0)
                        
                        # 使用最大的数量作为 resource_id
                        resource_id = max(processed_count, failed_count, deleted_count, target_count)
                    else:
                        resource_id = None
                except:
                    resource_id = None
                    processed_count = 0
                    failed_count = 0
                
                # 记录审计日志
                save_audit_log(
                    admin_id=admin_id,
                    action=f"{action}_batch",
                    resource=resource,
                    resource_id=str(resource_id) if resource_id else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_method=request_method,
                    request_data=request_data,
                    response_status=response_status,
                    error_message=error_message,
                )
                
                # 如果有失败，记录错误日志
                if failed_count > 0:
                    save_audit_log(
                        admin_id=admin_id,
                        action=f"{action}_batch_errors",
                        resource=resource,
                        resource_id=f"failed:{failed_count}",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_method=request_method,
                        request_data={'processed': processed_count, 'failed': failed_count},
                        response_status=response_status,
                        error_message=f"Batch operation had {failed_count} failures"
                    )
            
            return response
        
        return decorated
    return decorator
