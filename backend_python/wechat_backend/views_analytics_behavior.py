#!/usr/bin/env python3
"""
用户行为分析 API 接口
记录和分析用户操作轨迹

功能:
1. 行为事件记录 (Event Tracking)
2. 用户轨迹查询 (User Journey)
3. 行为统计分析 (Analytics)
4. 热力图数据 (Heatmap Data)
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from flask import Blueprint, request, jsonify, g
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth_optional, get_current_user_id
from wechat_backend.security.rate_limiting import rate_limit

# 创建 Blueprint
analytics_bp = Blueprint('analytics', __name__)

# 内存存储（生产环境应使用数据库）
_user_events: Dict[str, List[Dict[str, Any]]] = {}
_session_data: Dict[str, Dict[str, Any]] = {}
_daily_stats: Dict[str, Dict[str, Any]] = {}


@analytics_bp.route('/api/analytics/track', methods=['POST'])
@require_auth_optional
@rate_limit(limit=100, window=60, per='endpoint')
def track_event():
    """
    追踪用户行为事件
    
    Request Body:
        - event: 事件名称 (required)
        - category: 事件分类 (optional)
        - properties: 事件属性 (optional)
        - timestamp: 时间戳 (optional, 默认当前时间)
        - sessionId: 会话 ID (optional)
    
    支持的事件类型:
        - page_view: 页面浏览
        - button_click: 按钮点击
        - api_call: API 调用
        - form_submit: 表单提交
        - error: 错误事件
        - custom: 自定义事件
    """
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id() or 'anonymous'
        
        event = data.get('event')
        if not event:
            return jsonify({
                'status': 'error',
                'error': 'event is required',
                'code': 'MISSING_EVENT'
            }), 400
        
        # 构建事件记录
        event_record = {
            'event_id': f"evt_{user_id}_{int(time.time() * 1000)}",
            'user_id': user_id,
            'event': event,
            'category': data.get('category', 'custom'),
            'properties': data.get('properties', {}),
            'timestamp': data.get('timestamp') or datetime.now().isoformat(),
            'session_id': data.get('sessionId') or _get_or_create_session(user_id),
            'platform': data.get('platform', 'wechat_miniprogram'),
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # 添加请求上下文信息
        event_record['context'] = {
            'ip': request.remote_addr,
            'path': request.path,
            'method': request.method,
            'referer': request.headers.get('Referer', '')
        }
        
        # 保存事件
        _save_event(user_id, event_record)
        
        # 更新统计数据
        _update_daily_stats(user_id, event_record)
        
        api_logger.debug(f'行为事件记录：user_id={user_id}, event={event}')
        
        return jsonify({
            'status': 'success',
            'event_id': event_record['event_id'],
            'message': '事件记录成功'
        })
        
    except Exception as e:
        api_logger.error(f'行为事件记录失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'TRACK_ERROR'
        }), 500


@analytics_bp.route('/api/analytics/user-journey', methods=['GET'])
@require_auth_optional
def get_user_journey():
    """
    获取用户操作轨迹
    
    Query Parameters:
        - user_id: 用户 ID（可选，默认当前用户）
        - start_time: 开始时间（可选）
        - end_time: 结束时间（可选）
        - limit: 返回数量限制（默认 100）
    
    Response:
        - events: 事件列表
        - sessions: 会话列表
        - summary: 摘要统计
    """
    try:
        user_id = request.args.get('user_id') or get_current_user_id() or 'anonymous'
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = int(request.args.get('limit', 100))
        
        api_logger.info(f'获取用户轨迹：user_id={user_id}')
        
        # 获取用户事件
        events = _get_user_events(user_id, start_time, end_time, limit)
        
        # 按会话分组
        sessions = _group_events_by_session(events)
        
        # 生成摘要
        summary = _generate_journey_summary(events)
        
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': user_id,
                'events': events,
                'sessions': sessions,
                'summary': summary,
                'total_count': len(events)
            }
        })
        
    except Exception as e:
        api_logger.error(f'获取用户轨迹失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'JOURNEY_ERROR'
        }), 500


@analytics_bp.route('/api/analytics/statistics', methods=['GET'])
@require_auth_optional
def get_analytics_statistics():
    """
    获取行为统计数据
    
    Query Parameters:
        - period: 统计周期 (today, week, month, custom)
        - start_date: 开始日期（custom 周期需要）
        - end_date: 结束日期（custom 周期需要）
    
    Response:
        - total_events: 总事件数
        - unique_users: 独立用户数
        - event_breakdown: 事件分类统计
        - hourly_distribution: 小时分布
        - popular_events: 热门事件
    """
    try:
        period = request.args.get('period', 'today')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 计算日期范围
        date_range = _calculate_date_range(period, start_date, end_date)
        
        # 获取统计数据
        statistics = _calculate_statistics(date_range)
        
        api_logger.info(f'获取统计数据：period={period}')
        
        return jsonify({
            'status': 'success',
            'data': statistics,
            'period': period,
            'date_range': date_range
        })
        
    except Exception as e:
        api_logger.error(f'获取统计数据失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'STATS_ERROR'
        }), 500


@analytics_bp.route('/api/analytics/heatmap', methods=['GET'])
@require_auth_optional
def get_heatmap_data():
    """
    获取热力图数据
    
    Query Parameters:
        - page: 页面路径
        - period: 统计周期
    
    Response:
        - clicks: 点击数据
        - scrolls: 滚动数据
        - hovers: 悬停数据
    """
    try:
        page = request.args.get('page', '')
        period = request.args.get('period', 'week')
        
        # 生成模拟热力图数据（实际应从数据库查询）
        heatmap_data = _generate_heatmap_data(page, period)
        
        return jsonify({
            'status': 'success',
            'data': heatmap_data,
            'page': page,
            'period': period
        })
        
    except Exception as e:
        api_logger.error(f'获取热力图数据失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'HEATMAP_ERROR'
        }), 500


@analytics_bp.route('/api/analytics/funnel', methods=['GET'])
@require_auth_optional
def get_funnel_data():
    """
    获取漏斗分析数据
    
    Query Parameters:
        - funnel_name: 漏斗名称
        - period: 统计周期
    
    Response:
        - stages: 漏斗阶段
        - conversion_rates: 转化率
    """
    try:
        funnel_name = request.args.get('funnel_name', 'diagnosis')
        period = request.args.get('period', 'week')
        
        # 生成漏斗数据
        funnel_data = _generate_funnel_data(funnel_name, period)
        
        return jsonify({
            'status': 'success',
            'data': funnel_data,
            'funnel_name': funnel_name,
            'period': period
        })
        
    except Exception as e:
        api_logger.error(f'获取漏斗数据失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'FUNNEL_ERROR'
        }), 500


# ==================== 辅助函数 ====================

def _save_event(user_id: str, event: Dict[str, Any]):
    """保存事件"""
    if user_id not in _user_events:
        _user_events[user_id] = []
    
    _user_events[user_id].append(event)
    
    # 限制存储数量
    if len(_user_events[user_id]) > 10000:
        _user_events[user_id] = _user_events[user_id][-10000:]


def _get_user_events(user_id: str, start_time: Optional[str] = None, 
                     end_time: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """获取用户事件"""
    events = _user_events.get(user_id, [])
    
    # 时间过滤
    if start_time:
        events = [e for e in events if e.get('timestamp', '') >= start_time]
    if end_time:
        events = [e for e in events if e.get('timestamp', '') <= end_time]
    
    # 按时间倒序排列
    events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return events[:limit]


def _get_or_create_session(user_id: str) -> str:
    """获取或创建会话"""
    session_key = f"{user_id}_{datetime.now().strftime('%Y-%m-%d')}"
    
    if session_key not in _session_data:
        _session_data[session_key] = {
            'session_id': f"sess_{user_id}_{int(time.time())}",
            'user_id': user_id,
            'start_time': datetime.now().isoformat(),
            'event_count': 0
        }
    
    return _session_data[session_key]['session_id']


def _group_events_by_session(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按会话分组事件"""
    sessions = defaultdict(list)
    
    for event in events:
        session_id = event.get('session_id', 'unknown')
        sessions[session_id].append(event)
    
    result = []
    for session_id, session_events in sessions.items():
        if session_events:
            result.append({
                'session_id': session_id,
                'events': session_events,
                'event_count': len(session_events),
                'start_time': session_events[-1].get('timestamp'),
                'end_time': session_events[0].get('timestamp'),
                'duration': _calculate_session_duration(session_events)
            })
    
    return result


def _calculate_session_duration(events: List[Dict[str, Any]]) -> int:
    """计算会话时长（秒）"""
    if len(events) < 2:
        return 0
    
    try:
        first_time = datetime.fromisoformat(events[-1].get('timestamp', ''))
        last_time = datetime.fromisoformat(events[0].get('timestamp', ''))
        return int((last_time - first_time).total_seconds())
    except:
        return 0


def _generate_journey_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成轨迹摘要"""
    if not events:
        return {
            'total_events': 0,
            'unique_sessions': 0,
            'avg_session_duration': 0,
            'most_frequent_event': None,
            'categories': {}
        }
    
    # 事件分类统计
    categories = defaultdict(int)
    event_counts = defaultdict(int)
    
    for event in events:
        categories[event.get('category', 'unknown')] += 1
        event_counts[event.get('event', 'unknown')] += 1
    
    # 最频繁事件
    most_frequent = max(event_counts.items(), key=lambda x: x[1])[0] if event_counts else None
    
    # 会话统计
    sessions = set(e.get('session_id') for e in events)
    
    return {
        'total_events': len(events),
        'unique_sessions': len(sessions),
        'avg_session_duration': 0,  # 需要更复杂计算
        'most_frequent_event': most_frequent,
        'categories': dict(categories),
        'event_distribution': dict(event_counts)
    }


def _update_daily_stats(user_id: str, event: Dict[str, Any]):
    """更新每日统计"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    if today not in _daily_stats:
        _daily_stats[today] = {
            'date': today,
            'total_events': 0,
            'unique_users': set(),
            'event_breakdown': defaultdict(int),
            'hourly_distribution': defaultdict(int)
        }
    
    stats = _daily_stats[today]
    stats['total_events'] += 1
    stats['unique_users'].add(user_id)
    stats['event_breakdown'][event.get('event', 'unknown')] += 1
    
    # 小时分布
    try:
        hour = datetime.fromisoformat(event.get('timestamp', '')).hour
        stats['hourly_distribution'][hour] += 1
    except:
        pass


def _calculate_statistics(date_range: Dict[str, str]) -> Dict[str, Any]:
    """计算统计数据"""
    # 聚合指定日期范围内的数据
    total_events = 0
    unique_users = set()
    event_breakdown = defaultdict(int)
    hourly_distribution = defaultdict(int)
    
    for date_str, stats in _daily_stats.items():
        if date_range['start'] <= date_str <= date_range['end']:
            total_events += stats['total_events']
            unique_users.update(stats['unique_users'])
            
            for event, count in stats['event_breakdown'].items():
                event_breakdown[event] += count
            
            for hour, count in stats['hourly_distribution'].items():
                hourly_distribution[hour] += count
    
    # 热门事件
    popular_events = sorted(event_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'total_events': total_events,
        'unique_users': len(unique_users),
        'event_breakdown': dict(event_breakdown),
        'hourly_distribution': dict(hourly_distribution),
        'popular_events': [{'event': e, 'count': c} for e, c in popular_events],
        'avg_events_per_user': total_events / len(unique_users) if unique_users else 0
    }


def _calculate_date_range(period: str, start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> Dict[str, str]:
    """计算日期范围"""
    today = datetime.now().date()
    
    if period == 'today':
        return {
            'start': today.isoformat(),
            'end': today.isoformat()
        }
    elif period == 'week':
        start = today - timedelta(days=7)
        return {
            'start': start.isoformat(),
            'end': today.isoformat()
        }
    elif period == 'month':
        start = today - timedelta(days=30)
        return {
            'start': start.isoformat(),
            'end': today.isoformat()
        }
    elif period == 'custom' and start_date and end_date:
        return {
            'start': start_date,
            'end': end_date
        }
    else:
        return {
            'start': today.isoformat(),
            'end': today.isoformat()
        }


def _generate_heatmap_data(page: str, period: str) -> Dict[str, Any]:
    """生成热力图数据（模拟）"""
    import random
    
    # 生成模拟点击数据
    clicks = []
    for _ in range(50):
        clicks.append({
            'x': random.randint(0, 100),
            'y': random.randint(0, 100),
            'intensity': random.randint(1, 10)
        })
    
    return {
        'clicks': clicks,
        'scrolls': [{'depth': random.randint(0, 100)} for _ in range(20)],
        'hovers': [{'x': random.randint(0, 100), 'y': random.randint(0, 100), 'duration': random.randint(100, 5000)} for _ in range(30)]
    }


def _generate_funnel_data(funnel_name: str, period: str) -> Dict[str, Any]:
    """生成漏斗数据（模拟）"""
    # 品牌诊断漏斗
    if funnel_name == 'diagnosis':
        stages = [
            {'name': '访问首页', 'count': 1000, 'rate': 100},
            {'name': '点击诊断', 'count': 600, 'rate': 60},
            {'name': '输入品牌', 'count': 450, 'rate': 75},
            {'name': '选择模型', 'count': 400, 'rate': 89},
            {'name': '开始测试', 'count': 350, 'rate': 88},
            {'name': '查看报告', 'count': 300, 'rate': 86}
        ]
    else:
        stages = []
    
    return {
        'funnel_name': funnel_name,
        'period': period,
        'stages': stages,
        'overall_conversion_rate': stages[-1]['rate'] / 100 if stages else 0
    }


# 注册 Blueprint
def register_blueprints(app):
    """注册行为分析 Blueprint"""
    from wechat_backend.logging_config import api_logger
    app.register_blueprint(analytics_bp)
    api_logger.info('Analytics Blueprint registered')
