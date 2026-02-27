"""
死信队列管理 API

提供死信队列的查询、处理和统计功能。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from wechat_backend.v2.services.dead_letter_queue import DeadLetterQueue
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import DeadLetterQueueError

logger = logging.getLogger(__name__)

# 创建 Blueprint
dead_letter_bp = Blueprint('dead_letter', __name__, url_prefix='/api/v2/dead-letters')

# 死信队列实例
dlq = DeadLetterQueue()


@dead_letter_bp.route('', methods=['GET'])
def list_dead_letters() -> Dict[str, Any]:
    """
    获取死信列表（支持分页和过滤）
    
    Query Parameters:
        status: 过滤状态（pending/processing/resolved/ignored）
        task_type: 过滤任务类型（ai_call/analysis/report_generation）
        limit: 每页数量（默认 100，最大 1000）
        offset: 偏移量（默认 0）
        sort_by: 排序方式（默认 'priority DESC, failed_at ASC'）
    
    Returns:
        {
            "data": [...],
            "pagination": {
                "total": 100,
                "limit": 100,
                "offset": 0,
                "has_more": false
            }
        }
    """
    try:
        status = request.args.get('status')
        task_type = request.args.get('task_type')
        
        try:
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return jsonify({'error': 'Invalid limit or offset'}), 400
        
        sort_by = request.args.get('sort_by', 'priority DESC, failed_at ASC')
        
        # 参数验证
        if limit > 1000:
            return jsonify({'error': 'limit cannot exceed 1000'}), 400
        
        if limit < 1:
            limit = 100
        
        if offset < 0:
            offset = 0
        
        letters = dlq.list_dead_letters(
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
        )
        
        total = dlq.count_dead_letters(status=status, task_type=task_type)
        
        return jsonify({
            'data': letters,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total,
            },
        })
        
    except DeadLetterQueueError as e:
        api_logger.error(
            "list_dead_letters_error",
            extra={
                'event': 'list_dead_letters_error',
                'error': str(e),
                'error_type': type(e).__name__,
            }
        )
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        api_logger.error(
            "list_dead_letters_error",
            extra={
                'event': 'list_dead_letters_error',
                'error': str(e),
                'error_type': type(e).__name__,
            }
        )
        return jsonify({'error': 'Internal server error'}), 500


@dead_letter_bp.route('/<int:dead_letter_id>', methods=['GET'])
def get_dead_letter(dead_letter_id: int) -> Dict[str, Any]:
    """
    获取单个死信详情
    
    Path Parameters:
        dead_letter_id: 死信记录 ID
    
    Returns:
        死信记录详情
    """
    letter = dlq.get_dead_letter(dead_letter_id)
    
    if not letter:
        return jsonify({'error': 'Dead letter not found'}), 404
    
    return jsonify(letter)


@dead_letter_bp.route('/<int:dead_letter_id>/resolve', methods=['POST'])
def resolve_dead_letter(dead_letter_id: int) -> Dict[str, Any]:
    """
    标记死信为已解决
    
    Path Parameters:
        dead_letter_id: 死信记录 ID
    
    Request Body:
        handled_by: 处理人（可选，默认 'api_user'）
        resolution_notes: 处理说明（可选）
    
    Returns:
        {"status": "resolved"}
    """
    try:
        data = request.get_json() or {}
        handled_by = data.get('handled_by', 'api_user')
        resolution_notes = data.get('resolution_notes', '')
        
        success = dlq.mark_as_resolved(
            dead_letter_id,
            handled_by=handled_by,
            resolution_notes=resolution_notes,
        )
        
        if not success:
            return jsonify({'error': 'Failed to resolve dead letter'}), 400
        
        return jsonify({'status': 'resolved'})
        
    except Exception as e:
        api_logger.error(
            "resolve_dead_letter_error",
            extra={
                'event': 'resolve_dead_letter_error',
                'dead_letter_id': dead_letter_id,
                'error': str(e),
            }
        )
        return jsonify({'error': str(e)}), 500


@dead_letter_bp.route('/<int:dead_letter_id>/ignore', methods=['POST'])
def ignore_dead_letter(dead_letter_id: int) -> Dict[str, Any]:
    """
    标记死信为忽略
    
    Path Parameters:
        dead_letter_id: 死信记录 ID
    
    Request Body:
        handled_by: 处理人（可选）
        resolution_notes: 处理说明（可选）
    
    Returns:
        {"status": "ignored"}
    """
    try:
        data = request.get_json() or {}
        handled_by = data.get('handled_by', 'api_user')
        resolution_notes = data.get('resolution_notes', '')
        
        success = dlq.mark_as_ignored(
            dead_letter_id,
            handled_by=handled_by,
            resolution_notes=resolution_notes,
        )
        
        if not success:
            return jsonify({'error': 'Failed to ignore dead letter'}), 400
        
        return jsonify({'status': 'ignored'})
        
    except Exception as e:
        api_logger.error(
            "ignore_dead_letter_error",
            extra={
                'event': 'ignore_dead_letter_error',
                'dead_letter_id': dead_letter_id,
                'error': str(e),
            }
        )
        return jsonify({'error': str(e)}), 500


@dead_letter_bp.route('/<int:dead_letter_id>/retry', methods=['POST'])
def retry_dead_letter(dead_letter_id: int) -> Dict[str, Any]:
    """
    重试死信任务
    
    注意：此 API 只更新状态为 'processing'，实际重试逻辑需要调用方实现
    
    Path Parameters:
        dead_letter_id: 死信记录 ID
    
    Request Body:
        handled_by: 处理人（可选）
    
    Returns:
        {"status": "processing"}
    """
    try:
        data = request.get_json() or {}
        handled_by = data.get('handled_by', 'api_user')
        
        success = dlq.retry_dead_letter(dead_letter_id, handled_by=handled_by)
        
        if not success:
            return jsonify({'error': 'Failed to retry dead letter'}), 400
        
        return jsonify({'status': 'processing'})
        
    except Exception as e:
        api_logger.error(
            "retry_dead_letter_error",
            extra={
                'event': 'retry_dead_letter_error',
                'dead_letter_id': dead_letter_id,
                'error': str(e),
            }
        )
        return jsonify({'error': str(e)}), 500


@dead_letter_bp.route('/statistics', methods=['GET'])
def get_statistics() -> Dict[str, Any]:
    """
    获取死信队列统计信息
    
    Returns:
        {
            "total": 100,
            "by_status": {
                "pending": 50,
                "processing": 10,
                "resolved": 35,
                "ignored": 5
            },
            "by_task_type": {
                "ai_call": 30,
                "analysis": 15,
                "report_generation": 5
            },
            "last_24h": 20,
            "oldest_pending": "2026-02-27T10:00:00"
        }
    """
    try:
        stats = dlq.get_statistics()
        return jsonify(stats)
    except Exception as e:
        api_logger.error(
            "get_statistics_error",
            extra={
                'event': 'get_statistics_error',
                'error': str(e),
            }
        )
        return jsonify({'error': str(e)}), 500


@dead_letter_bp.route('/cleanup', methods=['POST'])
def cleanup_resolved() -> Dict[str, Any]:
    """
    清理已解决的死信
    
    Request Body:
        days: 保留天数（默认 30，范围 1-365）
    
    Returns:
        {
            "deleted": 50,
            "message": "Cleaned up 50 records older than 30 days"
        }
    """
    try:
        data = request.get_json() or {}
        
        try:
            days = int(data.get('days', 30))
        except ValueError:
            return jsonify({'error': 'Invalid days value'}), 400
        
        if days < 1 or days > 365:
            return jsonify({'error': 'days must be between 1 and 365'}), 400
        
        deleted = dlq.cleanup_resolved(days=days)
        
        return jsonify({
            'deleted': deleted,
            'message': f'Cleaned up {deleted} records older than {days} days',
        })
        
    except Exception as e:
        api_logger.error(
            "cleanup_resolved_error",
            extra={
                'event': 'cleanup_resolved_error',
                'error': str(e),
            }
        )
        return jsonify({'error': str(e)}), 500
