#!/usr/bin/env python3
"""
数据同步 API 接口
提供增量同步、数据上传下载、删除等功能

功能:
1. 增量同步 (Incremental Sync)
2. 数据下载 (Data Download)
3. 结果上传 (Result Upload)
4. 结果删除 (Result Delete)
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, g
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth_optional, get_current_user_id
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.models import db, SyncResult

# 创建 Blueprint
sync_bp = Blueprint('sync', __name__)

# 内存存储（生产环境应使用数据库）
_sync_results: Dict[str, List[Dict[str, Any]]] = {}
_sync_timestamps: Dict[str, str] = {}


@sync_bp.route('/api/sync/data', methods=['POST'])
@require_auth_optional
@rate_limit(limit=10, window=60, per='endpoint')
def sync_data():
    """
    增量同步数据
    
    Request Body:
        - lastSyncTimestamp: 上次同步时间戳（可选）
        - localResults: 本地结果列表（可选）
    
    Response:
        - status: 状态
        - last_sync_timestamp: 最后同步时间戳
        - uploaded_count: 上传数量
        - cloud_results: 云端结果列表
    """
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id() or 'anonymous'
        
        last_sync_timestamp = data.get('lastSyncTimestamp')
        local_results = data.get('localResults', [])
        
        api_logger.info(f'数据同步请求：user_id={user_id}, local_count={len(local_results)}')
        
        # 处理上传的结果
        uploaded_count = 0
        if local_results:
            for result in local_results:
                result_id = result.get('result_id')
                if result_id:
                    # 保存到数据库或缓存
                    _save_sync_result(user_id, result)
                    uploaded_count += 1
        
        # 获取需要同步的云端结果
        cloud_results = _get_cloud_results(user_id, last_sync_timestamp)
        
        # 生成新的同步时间戳
        current_timestamp = datetime.now().isoformat()
        _sync_timestamps[user_id] = current_timestamp
        
        api_logger.info(f'数据同步完成：uploaded={uploaded_count}, downloaded={len(cloud_results)}')
        
        return jsonify({
            'status': 'success',
            'last_sync_timestamp': current_timestamp,
            'uploaded_count': uploaded_count,
            'cloud_results': cloud_results,
            'message': f'同步成功：上传 {uploaded_count} 条，下载 {len(cloud_results)} 条'
        })
        
    except Exception as e:
        api_logger.error(f'数据同步失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'SYNC_ERROR'
        }), 500


@sync_bp.route('/api/sync/download', methods=['POST'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
def download_data():
    """
    增量下载数据
    
    Request Body:
        - lastSyncTimestamp: 上次同步时间戳（可选）
    
    Response:
        - status: 状态
        - last_sync_timestamp: 最后同步时间戳
        - results: 结果列表
        - has_more: 是否有更多数据
    """
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id() or 'anonymous'
        
        last_sync_timestamp = data.get('lastSyncTimestamp')
        limit = int(data.get('limit', 50))
        
        api_logger.info(f'数据下载请求：user_id={user_id}, last_sync={last_sync_timestamp}')
        
        # 获取云端结果
        cloud_results = _get_cloud_results(user_id, last_sync_timestamp, limit)
        
        # 生成新的同步时间戳
        current_timestamp = datetime.now().isoformat()
        
        api_logger.info(f'数据下载完成：count={len(cloud_results)}')
        
        return jsonify({
            'status': 'success',
            'last_sync_timestamp': current_timestamp,
            'results': cloud_results,
            'has_more': len(cloud_results) >= limit,
            'count': len(cloud_results)
        })
        
    except Exception as e:
        api_logger.error(f'数据下载失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'DOWNLOAD_ERROR'
        }), 500


@sync_bp.route('/api/sync/upload-result', methods=['POST'])
@require_auth_optional
@rate_limit(limit=30, window=60, per='endpoint')
def upload_result():
    """
    上传单个测试结果
    
    Request Body:
        - result: 测试结果对象
            - result_id: 结果 ID
            - executionId: 执行 ID
            - brandName: 品牌名称
            - aiModelsUsed: 使用的 AI 模型
            - overallScore: 总体得分
            - detailedResults: 详细结果
            - testDate: 测试日期
    
    Response:
        - status: 状态
        - result_id: 结果 ID
        - sync_timestamp: 同步时间戳
    """
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id() or 'anonymous'
        
        result = data.get('result', {})
        if not result:
            return jsonify({
                'status': 'error',
                'error': 'result is required',
                'code': 'MISSING_RESULT'
            }), 400
        
        # 生成或获取 result_id
        result_id = result.get('result_id') or f"result_{user_id}_{int(time.time())}"
        result['result_id'] = result_id
        result['user_id'] = user_id
        result['sync_timestamp'] = datetime.now().isoformat()
        
        # 保存结果
        _save_sync_result(user_id, result)
        
        api_logger.info(f'结果上传成功：result_id={result_id}, user_id={user_id}')
        
        return jsonify({
            'status': 'success',
            'result_id': result_id,
            'sync_timestamp': result['sync_timestamp'],
            'message': '结果上传成功'
        })
        
    except Exception as e:
        api_logger.error(f'结果上传失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'UPLOAD_ERROR'
        }), 500


@sync_bp.route('/api/sync/delete-result', methods=['POST'])
@require_auth_optional
@rate_limit(limit=20, window=60, per='endpoint')
def delete_result():
    """
    删除结果
    
    Request Body:
        - result_id: 结果 ID
    
    Response:
        - status: 状态
        - result_id: 结果 ID
        - message: 消息
    """
    try:
        data = request.get_json() or {}
        user_id = get_current_user_id() or 'anonymous'
        
        result_id = data.get('result_id')
        if not result_id:
            return jsonify({
                'status': 'error',
                'error': 'result_id is required',
                'code': 'MISSING_RESULT_ID'
            }), 400
        
        # 删除结果
        deleted = _delete_sync_result(user_id, result_id)
        
        if deleted:
            api_logger.info(f'结果删除成功：result_id={result_id}')
            return jsonify({
                'status': 'success',
                'result_id': result_id,
                'message': '结果删除成功'
            })
        else:
            return jsonify({
                'status': 'error',
                'error': 'Result not found',
                'code': 'RESULT_NOT_FOUND'
            }), 404
        
    except Exception as e:
        api_logger.error(f'结果删除失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'DELETE_ERROR'
        }), 500


@sync_bp.route('/api/sync/status', methods=['GET'])
@require_auth_optional
def get_sync_status():
    """
    获取同步状态
    
    Response:
        - status: 状态
        - last_sync_timestamp: 最后同步时间戳
        - pending_count: 待同步数量
        - total_count: 总结果数
    """
    try:
        user_id = get_current_user_id() or 'anonymous'
        
        last_sync_timestamp = _sync_timestamps.get(user_id)
        results = _sync_results.get(user_id, [])
        
        return jsonify({
            'status': 'success',
            'data': {
                'last_sync_timestamp': last_sync_timestamp,
                'pending_count': 0,  # 内存存储，无待同步
                'total_count': len(results),
                'storage_used': len(results) * 10,  # 估算 KB
                'storage_limit': 5120  # 5MB limit
            }
        })
        
    except Exception as e:
        api_logger.error(f'获取同步状态失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'STATUS_ERROR'
        }), 500


def _save_sync_result(user_id: str, result: Dict[str, Any]):
    """保存同步结果"""
    if user_id not in _sync_results:
        _sync_results[user_id] = []
    
    result_id = result.get('result_id')
    
    # 查找是否已存在
    found = False
    for i, existing in enumerate(_sync_results[user_id]):
        if existing.get('result_id') == result_id:
            _sync_results[user_id][i] = result
            found = True
            break
    
    if not found:
        _sync_results[user_id].append(result)
    
    # 限制存储数量
    if len(_sync_results[user_id]) > 1000:
        _sync_results[user_id] = _sync_results[user_id][-1000:]


def _get_cloud_results(user_id: str, last_sync_timestamp: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """获取云端结果"""
    results = _sync_results.get(user_id, [])
    
    if last_sync_timestamp:
        # 过滤出上次同步之后的结果
        filtered_results = [
            r for r in results 
            if r.get('sync_timestamp', '') > last_sync_timestamp
        ]
        return filtered_results[:limit]
    
    # 返回最新的结果
    return results[-limit:]


def _delete_sync_result(user_id: str, result_id: str) -> bool:
    """删除同步结果"""
    results = _sync_results.get(user_id, [])
    
    for i, result in enumerate(results):
        if result.get('result_id') == result_id:
            del results[i]
            return True
    
    return False


# 注册 Blueprint
def register_blueprints(app):
    """注册数据同步 Blueprint"""
    from wechat_backend.logging_config import api_logger
    app.register_blueprint(sync_bp)
    api_logger.info('Sync Blueprint registered')
