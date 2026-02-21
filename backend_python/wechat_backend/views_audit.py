#!/usr/bin/env python3
"""
审计日志 API 端点
提供审计日志查询、统计、导出等功能
"""

from flask import Blueprint, request, jsonify, Response
from datetime import datetime, timedelta
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth, get_current_user_id
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.audit_logs import (
    get_audit_logs, 
    get_audit_statistics, 
    get_suspicious_activities,
    export_audit_logs
)

# 创建审计日志蓝图
audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


def require_admin(f):
    """装饰器：要求管理员权限"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        
        # 检查是否为管理员（从数据库检查）
        if not user_id or user_id == 'anonymous':
            return jsonify({'error': 'Admin access required'}), 403
        
        # 这里简化处理，实际应该检查用户角色
        # 生产环境应该实现完整的角色检查
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# 审计日志查询 API
# ============================================================================

@audit_bp.route('/logs', methods=['GET'])
@require_auth
@require_admin
@rate_limit(limit=30, window=60, per='ip')
def query_audit_logs():
    """
    查询审计日志
    
    Query Parameters:
    - admin_id: 管理员 ID（可选）
    - action: 操作类型（可选）
    - resource: 资源类型（可选）
    - start_date: 开始日期（可选，格式：YYYY-MM-DD）
    - end_date: 结束日期（可选，格式：YYYY-MM-DD）
    - page: 页码（默认 1）
    - page_size: 每页数量（默认 20）
    """
    api_logger.info(f"Query audit logs by admin: {get_current_user_id()}")
    
    try:
        # 获取查询参数
        admin_id = request.args.get('admin_id')
        action = request.args.get('action')
        resource = request.args.get('resource')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        # 限制最大页大小
        page_size = min(page_size, 100)
        
        # 查询日志
        result = get_audit_logs(
            admin_id=admin_id,
            action=action,
            resource=resource,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        api_logger.error(f"Error querying audit logs: {e}")
        return jsonify({'error': 'Failed to query audit logs'}), 500


# ============================================================================
# 审计统计 API
# ============================================================================

@audit_bp.route('/statistics', methods=['GET'])
@require_auth
@require_admin
@rate_limit(limit=10, window=60, per='ip')
def get_audit_stats():
    """
    获取审计统计数据
    
    Query Parameters:
    - days: 统计天数（默认 7）
    """
    api_logger.info(f"Get audit statistics by admin: {get_current_user_id()}")
    
    try:
        days = request.args.get('days', 7, type=int)
        
        # 限制最大天数
        days = min(days, 90)
        
        # 获取统计数据
        stats = get_audit_statistics(days)
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        api_logger.error(f"Error getting audit statistics: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500


# ============================================================================
# 可疑活动检测 API
# ============================================================================

@audit_bp.route('/suspicious', methods=['GET'])
@require_auth
@require_admin
@rate_limit(limit=10, window=60, per='ip')
def get_suspicious():
    """
    获取可疑活动列表
    
    Query Parameters:
    - threshold: 阈值（默认 10）
    - minutes: 时间窗口（默认 5）
    """
    api_logger.info(f"Get suspicious activities by admin: {get_current_user_id()}")
    
    try:
        threshold = request.args.get('threshold', 10, type=int)
        minutes = request.args.get('minutes', 5, type=int)
        
        # 获取可疑活动
        suspicious = get_suspicious_activities(threshold, minutes)
        
        return jsonify({
            'status': 'success',
            'data': {
                'suspicious_activities': suspicious,
                'count': len(suspicious),
                'threshold': threshold,
                'window_minutes': minutes
            }
        })
        
    except Exception as e:
        api_logger.error(f"Error getting suspicious activities: {e}")
        return jsonify({'error': 'Failed to get suspicious activities'}), 500


# ============================================================================
# 审计日志导出 API
# ============================================================================

@audit_bp.route('/export', methods=['GET'])
@require_auth
@require_admin
@rate_limit(limit=5, window=60, per='ip')
def export_logs():
    """
    导出审计日志
    
    Query Parameters:
    - format: 导出格式（csv/json，默认 csv）
    - admin_id: 管理员 ID（可选）
    - start_date: 开始日期（可选）
    - end_date: 结束日期（可选）
    """
    api_logger.info(f"Export audit logs by admin: {get_current_user_id()}")
    
    try:
        format_type = request.args.get('format', 'csv')
        admin_id = request.args.get('admin_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 导出数据
        data = export_audit_logs(
            format=format_type,
            admin_id=admin_id,
            start_date=start_date,
            end_date=end_date
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'json':
            return Response(
                data,
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename=audit_logs_{timestamp}.json'
                }
            )
        else:
            return Response(
                data.encode('utf-8-sig'),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=audit_logs_{timestamp}.csv'
                }
            )
        
    except Exception as e:
        api_logger.error(f"Error exporting audit logs: {e}")
        return jsonify({'error': 'Failed to export audit logs'}), 500


# ============================================================================
# 管理员操作统计 API
# ============================================================================

@audit_bp.route('/admin-stats', methods=['GET'])
@require_auth
@require_admin
@rate_limit(limit=10, window=60, per='ip')
def get_admin_statistics():
    """
    获取管理员操作统计
    
    Query Parameters:
    - days: 统计天数（默认 7）
    """
    api_logger.info(f"Get admin statistics by admin: {get_current_user_id()}")
    
    try:
        days = request.args.get('days', 7, type=int)
        days = min(days, 90)
        
        stats = get_audit_statistics(days)
        
        # 提取管理员相关统计
        admin_stats = {
            'admin_stats': stats['admin_stats'],
            'total_actions': stats['total_actions'],
            'error_count': stats['error_count'],
            'error_rate': stats['error_rate'],
            'period': stats['period']
        }
        
        return jsonify({
            'status': 'success',
            'data': admin_stats
        })
        
    except Exception as e:
        api_logger.error(f"Error getting admin statistics: {e}")
        return jsonify({'error': 'Failed to get admin statistics'}), 500


def init_audit_routes(app):
    """初始化审计日志路由"""
    app.register_blueprint(audit_bp)
    api_logger.info("Audit routes initialized")
