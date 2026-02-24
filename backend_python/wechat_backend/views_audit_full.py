#!/usr/bin/env python3
"""
审计日志 API 接口
完整的操作审计追踪功能

功能:
1. 审计事件记录 (Audit Event Logging)
2. 审计日志查询 (Audit Log Query)
3. 审计报告生成 (Audit Report)
4. 合规性检查 (Compliance Check)
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from functools import wraps
from flask import Blueprint, request, jsonify, g, has_request_context
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth_optional, get_current_user_id, is_authenticated
from wechat_backend.security.rate_limiting import rate_limit

# 创建 Blueprint
audit_full_bp = Blueprint('audit_full', __name__)

# 内存存储（生产环境应使用数据库）
_audit_logs: List[Dict[str, Any]] = []
_audit_indexes: Dict[str, List[int]] = {}  # 索引加速查询


@audit_full_bp.route('/api/audit/log', methods=['POST'])
@require_auth_optional
@rate_limit(limit=200, window=60, per='endpoint')
def log_audit_event():
    """
    记录审计事件
    
    Request Body:
        - action: 操作类型 (required)
        - resource: 资源类型 (optional)
        - resource_id: 资源 ID (optional)
        - details: 详细信息 (optional)
        - severity: 严重级别 (info, warning, error, critical)
    
    支持的操作类型:
        - LOGIN: 登录
        - LOGOUT: 登出
        - CREATE: 创建资源
        - READ: 读取资源
        - UPDATE: 更新资源
        - DELETE: 删除资源
        - EXPORT: 导出数据
        - IMPORT: 导入数据
        - PERMISSION_CHANGE: 权限变更
        - CONFIG_CHANGE: 配置变更
        - SECURITY_EVENT: 安全事件
    """
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id() or 'anonymous'
        
        action = data.get('action')
        if not action:
            return jsonify({
                'status': 'error',
                'error': 'action is required',
                'code': 'MISSING_ACTION'
            }), 400
        
        # 构建审计日志记录
        audit_record = _create_audit_record(
            user_id=user_id,
            action=action,
            resource=data.get('resource'),
            resource_id=data.get('resource_id'),
            details=data.get('details'),
            severity=data.get('severity', 'info')
        )
        
        # 保存审计日志
        _save_audit_log(audit_record)
        
        api_logger.info(f'审计事件记录：user_id={user_id}, action={action}, severity={audit_record["severity"]}')
        
        return jsonify({
            'status': 'success',
            'audit_id': audit_record['audit_id'],
            'timestamp': audit_record['timestamp'],
            'message': '审计事件记录成功'
        })
        
    except Exception as e:
        api_logger.error(f'审计事件记录失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'AUDIT_LOG_ERROR'
        }), 500


@audit_full_bp.route('/api/audit/logs', methods=['GET'])
@require_auth_optional
@rate_limit(limit=50, window=60, per='endpoint')
def get_audit_logs():
    """
    查询审计日志
    
    Query Parameters:
        - user_id: 用户 ID（可选）
        - action: 操作类型（可选）
        - resource: 资源类型（可选）
        - severity: 严重级别（可选）
        - start_time: 开始时间（可选）
        - end_time: 结束时间（可选）
        - page: 页码（默认 1）
        - page_size: 每页数量（默认 20）
    
    Response:
        - logs: 日志列表
        - total: 总数
        - page: 页码
        - page_size: 每页数量
    """
    try:
        user_id = request.args.get('user_id')
        action = request.args.get('action')
        resource = request.args.get('resource')
        severity = request.args.get('severity')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        api_logger.info(f'查询审计日志：user_id={user_id}, action={action}, page={page}')
        
        # 查询日志
        logs = _query_audit_logs(
            user_id=user_id,
            action=action,
            resource=resource,
            severity=severity,
            start_time=start_time,
            end_time=end_time
        )
        
        # 分页
        total = len(logs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_logs = logs[start_idx:end_idx]
        
        return jsonify({
            'status': 'success',
            'data': {
                'logs': paginated_logs,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        api_logger.error(f'查询审计日志失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'QUERY_ERROR'
        }), 500


@audit_full_bp.route('/api/audit/report', methods=['GET'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
def get_audit_report():
    """
    获取审计报告
    
    Query Parameters:
        - period: 统计周期 (today, week, month, custom)
        - start_date: 开始日期（custom 周期需要）
        - end_date: 结束日期（custom 周期需要）
        - group_by: 分组维度 (user, action, resource, severity)
    
    Response:
        - summary: 摘要统计
        - breakdown: 分类统计
        - trends: 趋势数据
        - top_users: 活跃用户
        - security_events: 安全事件
    """
    try:
        period = request.args.get('period', 'week')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        group_by = request.args.get('group_by', 'action')
        
        api_logger.info(f'生成审计报告：period={period}, group_by={group_by}')
        
        # 计算日期范围
        date_range = _calculate_audit_date_range(period, start_date, end_date)
        
        # 生成报告
        report = _generate_audit_report(date_range, group_by)
        
        return jsonify({
            'status': 'success',
            'data': report,
            'period': period,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'生成审计报告失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'REPORT_ERROR'
        }), 500


@audit_full_bp.route('/api/audit/compliance', methods=['GET'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
def check_compliance():
    """
    合规性检查
    
    Query Parameters:
        - check_type: 检查类型 (all, data_access, permission, security)
    
    Response:
        - compliant: 是否合规
        - issues: 问题列表
        - recommendations: 建议
    """
    try:
        check_type = request.args.get('check_type', 'all')
        
        api_logger.info(f'合规性检查：check_type={check_type}')
        
        # 执行合规性检查
        compliance_result = _perform_compliance_check(check_type)
        
        return jsonify({
            'status': 'success',
            'data': compliance_result,
            'checked_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        api_logger.error(f'合规性检查失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'COMPLIANCE_ERROR'
        }), 500


@audit_full_bp.route('/api/audit/user-activity/<user_id>', methods=['GET'])
@require_auth_optional
def get_user_activity(user_id: str):
    """
    获取用户活动记录
    
    Path Parameters:
        - user_id: 用户 ID
    
    Query Parameters:
        - days: 天数（默认 7）
    
    Response:
        - user_id: 用户 ID
        - activity_summary: 活动摘要
        - recent_actions: 最近操作
        - risk_score: 风险评分
    """
    try:
        days = int(request.args.get('days', 7))
        
        api_logger.info(f'获取用户活动：user_id={user_id}, days={days}')
        
        # 获取用户活动
        activity = _get_user_activity(user_id, days)
        
        return jsonify({
            'status': 'success',
            'data': activity,
            'user_id': user_id
        })
        
    except Exception as e:
        api_logger.error(f'获取用户活动失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'ACTIVITY_ERROR'
        }), 500


# ==================== 审计装饰器 ====================

def audit_log(action: str, resource: str = None, log_request: bool = True):
    """
    审计日志装饰器
    
    用法:
        @audit_log(action='CREATE', resource='diagnosis_report')
        def create_report():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 执行原函数
            result = f(*args, **kwargs)
            
            # 记录审计日志
            if log_request and has_request_context():
                try:
                    user_id = get_current_user_id() or 'anonymous'
                    
                    # 提取详细信息
                    details = {}
                    if request.is_json:
                        data = request.get_json(silent=True)
                        if data:
                            # 过滤敏感信息
                            details = {k: v for k, v in data.items() 
                                      if k not in ['password', 'token', 'secret', 'api_key']}
                    
                    # 异步记录审计日志（不阻塞主流程）
                    _queue_audit_log(
                        user_id=user_id,
                        action=action,
                        resource=resource,
                        details=details,
                        status='success' if hasattr(result, 'status_code') and result.status_code < 400 else 'failure'
                    )
                except Exception as e:
                    api_logger.warning(f'审计日志记录失败：{e}')
            
            return result
        return decorated_function
    return decorator


# ==================== 辅助函数 ====================

def _create_audit_record(user_id: str, action: str, resource: str = None,
                         resource_id: str = None, details: Dict = None,
                         severity: str = 'info') -> Dict[str, Any]:
    """创建审计记录"""
    timestamp = datetime.now().isoformat()
    
    # 生成唯一 ID
    audit_id = hashlib.md5(
        f"{user_id}:{action}:{timestamp}:{time.time()}".encode()
    ).hexdigest()[:16]
    
    # 获取请求上下文
    context = {}
    if has_request_context():
        context = {
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'path': request.path,
            'method': request.method,
            'referer': request.headers.get('Referer', '')
        }
    
    return {
        'audit_id': audit_id,
        'timestamp': timestamp,
        'user_id': user_id,
        'action': action,
        'resource': resource,
        'resource_id': resource_id,
        'severity': severity,
        'details': details or {},
        'context': context,
        'status': 'success',
        'version': '1.0'
    }


def _save_audit_log(audit_record: Dict[str, Any]):
    """保存审计日志"""
    global _audit_logs, _audit_indexes
    
    # 添加到日志列表
    index = len(_audit_logs)
    _audit_logs.append(audit_record)
    
    # 更新索引
    _update_audit_index(index, audit_record)
    
    # 限制存储数量
    if len(_audit_logs) > 100000:
        _audit_logs = _audit_logs[-100000:]
        _rebuild_index()


def _update_audit_index(index: int, audit_record: Dict[str, Any]):
    """更新索引"""
    global _audit_indexes
    
    # 按用户 ID 索引
    user_id = audit_record.get('user_id', 'unknown')
    if user_id not in _audit_indexes:
        _audit_indexes[user_id] = []
    _audit_indexes[user_id].append(index)
    
    # 按操作类型索引
    action = audit_record.get('action', 'unknown')
    if action not in _audit_indexes:
        _audit_indexes[action] = []
    _audit_indexes[action].append(index)


def _rebuild_index():
    """重建索引"""
    global _audit_indexes
    _audit_indexes = {}
    
    for index, record in enumerate(_audit_logs):
        _update_audit_index(index, record)


def _query_audit_logs(user_id: str = None, action: str = None,
                      resource: str = None, severity: str = None,
                      start_time: str = None, end_time: str = None) -> List[Dict[str, Any]]:
    """查询审计日志"""
    results = []
    
    for record in _audit_logs:
        # 过滤条件
        if user_id and record.get('user_id') != user_id:
            continue
        if action and record.get('action') != action:
            continue
        if resource and record.get('resource') != resource:
            continue
        if severity and record.get('severity') != severity:
            continue
        if start_time and record.get('timestamp', '') < start_time:
            continue
        if end_time and record.get('timestamp', '') > end_time:
            continue
        
        results.append(record)
    
    # 按时间倒序排列
    results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return results


def _queue_audit_log(user_id: str, action: str, resource: str = None,
                     details: Dict = None, status: str = 'success'):
    """异步记录审计日志（队列方式）"""
    # 简化实现，实际应使用消息队列
    audit_record = _create_audit_record(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
        severity='info'
    )
    audit_record['status'] = status
    
    _save_audit_log(audit_record)


def _calculate_audit_date_range(period: str, start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> Dict[str, str]:
    """计算审计日期范围"""
    today = datetime.now().date()
    
    if period == 'today':
        return {'start': today.isoformat(), 'end': today.isoformat()}
    elif period == 'week':
        start = today - timedelta(days=7)
        return {'start': start.isoformat(), 'end': today.isoformat()}
    elif period == 'month':
        start = today - timedelta(days=30)
        return {'start': start.isoformat(), 'end': today.isoformat()}
    elif period == 'custom' and start_date and end_date:
        return {'start': start_date, 'end': end_date}
    else:
        return {'start': today.isoformat(), 'end': today.isoformat()}


def _generate_audit_report(date_range: Dict[str, str], group_by: str) -> Dict[str, Any]:
    """生成审计报告"""
    # 过滤日期范围内的日志
    filtered_logs = [
        log for log in _audit_logs
        if date_range['start'] <= log.get('timestamp', '')[:10] <= date_range['end']
    ]
    
    # 摘要统计
    summary = {
        'total_events': len(filtered_logs),
        'unique_users': len(set(log.get('user_id') for log in filtered_logs)),
        'severity_breakdown': _count_by_field(filtered_logs, 'severity'),
        'action_breakdown': _count_by_field(filtered_logs, 'action'),
        'resource_breakdown': _count_by_field(filtered_logs, 'resource')
    }
    
    # 分组统计
    breakdown = _group_by_field(filtered_logs, group_by)
    
    # 趋势数据（按天）
    trends = _calculate_daily_trends(filtered_logs)
    
    # 活跃用户
    user_counts = _count_by_field(filtered_logs, 'user_id')
    top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # 安全事件
    security_events = [
        log for log in filtered_logs
        if log.get('severity') in ['warning', 'error', 'critical']
    ]
    
    return {
        'summary': summary,
        'breakdown': breakdown,
        'trends': trends,
        'top_users': [{'user_id': u, 'count': c} for u, c in top_users],
        'security_events': security_events[:50],  # 最多 50 条
        'date_range': date_range
    }


def _count_by_field(logs: List[Dict], field: str) -> Dict[str, int]:
    """按字段计数"""
    counts = {}
    for log in logs:
        value = log.get(field, 'unknown')
        counts[value] = counts.get(value, 0) + 1
    return counts


def _group_by_field(logs: List[Dict], field: str) -> Dict[str, Any]:
    """按字段分组"""
    groups = {}
    for log in logs:
        value = log.get(field, 'unknown')
        if value not in groups:
            groups[value] = []
        groups[value].append(log)
    return {k: {'count': len(v), 'items': v[:10]} for k, v in groups.items()}


def _calculate_daily_trends(logs: List[Dict]) -> List[Dict[str, Any]]:
    """计算每日趋势"""
    daily_counts = {}
    
    for log in logs:
        date = log.get('timestamp', '')[:10]
        daily_counts[date] = daily_counts.get(date, 0) + 1
    
    return [
        {'date': date, 'count': count}
        for date, count in sorted(daily_counts.items())
    ]


def _perform_compliance_check(check_type: str) -> Dict[str, Any]:
    """执行合规性检查"""
    issues = []
    recommendations = []
    
    # 检查敏感操作
    sensitive_actions = ['DELETE', 'PERMISSION_CHANGE', 'CONFIG_CHANGE']
    sensitive_logs = [log for log in _audit_logs if log.get('action') in sensitive_actions]
    
    if len(sensitive_logs) > 100:
        issues.append({
            'type': 'high_sensitive_activity',
            'severity': 'warning',
            'description': f'检测到 {len(sensitive_logs)} 次敏感操作',
            'recommendation': '建议审查敏感操作日志'
        })
    
    # 检查失败登录
    failed_logins = [log for log in _audit_logs 
                     if log.get('action') == 'LOGIN' and log.get('status') == 'failure']
    
    if len(failed_logins) > 10:
        issues.append({
            'type': 'multiple_failed_logins',
            'severity': 'warning',
            'description': f'检测到 {len(failed_logins)} 次失败登录',
            'recommendation': '建议检查是否存在暴力破解'
        })
    
    # 检查非工作时间操作
    non_business_hours = [
        log for log in _audit_logs
        if _is_non_business_hours(log.get('timestamp', ''))
    ]
    
    if len(non_business_hours) > 50:
        issues.append({
            'type': 'non_business_hours_activity',
            'severity': 'info',
            'description': f'检测到 {len(non_business_hours)} 次非工作时间操作',
            'recommendation': '建议确认是否为正常操作'
        })
    
    return {
        'compliant': len(issues) == 0,
        'issue_count': len(issues),
        'issues': issues,
        'recommendations': [i['recommendation'] for i in issues],
        'check_type': check_type
    }


def _is_non_business_hours(timestamp: str) -> bool:
    """判断是否为非工作时间"""
    try:
        dt = datetime.fromisoformat(timestamp)
        # 周末或工作时间外（9-18 点）
        return dt.weekday() >= 5 or dt.hour < 9 or dt.hour > 18
    except Exception as e:

        pass  # TODO: 添加适当的错误处理
        return False


def _get_user_activity(user_id: str, days: int) -> Dict[str, Any]:
    """获取用户活动"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    user_logs = [
        log for log in _audit_logs
        if log.get('user_id') == user_id and log.get('timestamp', '') >= cutoff
    ]
    
    # 活动摘要
    summary = {
        'total_actions': len(user_logs),
        'unique_actions': len(set(log.get('action') for log in user_logs)),
        'unique_resources': len(set(log.get('resource') for log in user_logs if log.get('resource'))),
        'days_active': len(set(log.get('timestamp', '')[:10] for log in user_logs))
    }
    
    # 最近操作
    recent_actions = user_logs[:20]
    
    # 风险评分（简单实现）
    risk_score = _calculate_risk_score(user_logs)
    
    return {
        'user_id': user_id,
        'period_days': days,
        'activity_summary': summary,
        'recent_actions': recent_actions,
        'risk_score': risk_score,
        'risk_level': _get_risk_level(risk_score)
    }


def _calculate_risk_score(logs: List[Dict]) -> int:
    """计算风险评分"""
    score = 0
    
    # 敏感操作加分
    sensitive_actions = ['DELETE', 'PERMISSION_CHANGE', 'CONFIG_CHANGE']
    for log in logs:
        if log.get('action') in sensitive_actions:
            score += 5
        if log.get('severity') == 'warning':
            score += 3
        if log.get('severity') == 'error':
            score += 5
        if log.get('severity') == 'critical':
            score += 10
    
    return min(score, 100)  # 最高 100 分


def _get_risk_level(score: int) -> str:
    """获取风险等级"""
    if score >= 80:
        return 'critical'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'medium'
    elif score >= 20:
        return 'low'
    else:
        return 'minimal'


# 注册 Blueprint
def register_blueprints(app):
    """注册审计 Blueprint"""
    from wechat_backend.logging_config import api_logger
    app.register_blueprint(audit_full_bp)
    api_logger.info('Audit Blueprint registered')
