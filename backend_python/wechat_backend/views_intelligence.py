#!/usr/bin/env python3
"""
情报流水线 API 接口
提供实时情报流、信源分析、影响力评分等接口
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any
from flask import Blueprint, request, jsonify, Response
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth_optional
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.monitoring.logging_enhancements import log_api_request, log_api_response

# 创建 Blueprint
intelligence_bp = Blueprint('intelligence', __name__, url_prefix='/api')

# 内存存储（生产环境应使用 Redis 或数据库）
_intelligence_cache: Dict[str, List[Dict[str, Any]]] = {}
_pipeline_subscribers: Dict[str, List] = {}


@intelligence_bp.route('/api/intelligence/pipeline', methods=['GET'])
@require_auth_optional
@rate_limit(limit=30, window=60, per='endpoint')
def get_intelligence_pipeline():
    """
    获取情报流水线数据
    
    Query Parameters:
        - executionId: 执行 ID（必填）
        - brandName: 品牌名称
        - limit: 返回数量限制（默认 50）
    
    Returns:
        情报流水线数据，包含：
        - items: 情报项列表
        - stats: 统计数据
        - metadata: 元数据
    """
    try:
        execution_id = request.args.get('executionId')
        brand_name = request.args.get('brandName', '')
        limit = int(request.args.get('limit', 50))
        
        if not execution_id:
            return jsonify({
                'status': 'error',
                'error': 'executionId is required',
                'code': 'MISSING_EXECUTION_ID'
            }), 400
        
        api_logger.info(f'获取情报流水线数据：executionId={execution_id}')
        
        # 从缓存获取数据
        items = _intelligence_cache.get(execution_id, [])
        
        # 如果没有数据，生成模拟数据（用于演示）
        if not items and brand_name:
            items = _generate_mock_intelligence_data(brand_name, limit)
            _intelligence_cache[execution_id] = items
        
        # 限制返回数量
        items = items[:limit]
        
        # 计算统计数据
        stats = _calculate_pipeline_stats(items)
        
        # 构建响应
        response_data = {
            'status': 'success',
            'data': {
                'executionId': execution_id,
                'items': items,
                'stats': stats,
                'metadata': {
                    'totalCount': len(items),
                    'lastUpdated': datetime.now().isoformat(),
                    'brandName': brand_name
                }
            }
        }
        
        api_logger.info(f'情报流水线数据获取成功：{len(items)} 条记录')
        
        return jsonify(response_data)
        
    except Exception as e:
        api_logger.error(f'获取情报流水线数据失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'PIPELINE_FETCH_ERROR'
        }), 500


@intelligence_bp.route('/api/intelligence/stream', methods=['GET'])
@require_auth_optional
def stream_intelligence_updates():
    """
    Server-Sent Events (SSE) 实时情报流
    
    使用 SSE 技术推送实时情报更新
    """
    execution_id = request.args.get('executionId')
    
    if not execution_id:
        return Response(
            json.dumps({'error': 'executionId required'}),
            status=400,
            mimetype='application/json'
        )
    
    api_logger.info(f'客户端连接 SSE 流：executionId={execution_id}')
    
    def event_stream():
        """生成 SSE 事件流"""
        try:
            # 订阅该执行 ID 的更新
            subscriber_queue = []
            _pipeline_subscribers[execution_id] = subscriber_queue
            
            # 发送初始连接确认
            yield f"data: {json.dumps({'type': 'connected', 'executionId': execution_id})}\n\n"
            
            # 保持连接，等待新数据
            last_check = time.time()
            while True:
                # 检查客户端是否仍连接
                if time.time() - last_check > 300:  # 5 分钟超时
                    api_logger.info(f'SSE 连接超时：executionId={execution_id}')
                    break
                
                # 检查是否有新数据
                if subscriber_queue:
                    item = subscriber_queue.pop(0)
                    yield f"data: {json.dumps(item)}\n\n"
                    last_check = time.time()
                else:
                    # 发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                    time.sleep(5)  # 每 5 秒检查一次
            
        except GeneratorExit:
            api_logger.info(f'SSE 客户端断开连接：executionId={execution_id}')
        except Exception as e:
            api_logger.error(f'SSE 流错误：{e}', exc_info=True)
        finally:
            # 清理订阅
            if execution_id in _pipeline_subscribers:
                _pipeline_subscribers[execution_id].remove(subscriber_queue)
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Nginx: 禁用缓冲
        }
    )


@intelligence_bp.route('/api/intelligence/add', methods=['POST'])
@require_auth_optional
def add_intelligence_item():
    """
    添加情报项到流水线
    
    Request Body:
        - executionId: 执行 ID
        - question: 问题内容
        - model: 模型名称
        - status: 状态 (pending/processing/success/error)
        - brand: 品牌名称
        - latency: 延迟（毫秒）
        - preview: 响应预览
        - error: 错误信息
    
    Returns:
        添加结果
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'error': 'Request body is required',
                'code': 'MISSING_BODY'
            }), 400
        
        execution_id = data.get('executionId')
        if not execution_id:
            return jsonify({
                'status': 'error',
                'error': 'executionId is required',
                'code': 'MISSING_EXECUTION_ID'
            }), 400
        
        # 构建情报项
        item = {
            'id': data.get('id', str(int(time.time() * 1000))),
            'question': data.get('question', ''),
            'model': data.get('model', 'Unknown'),
            'status': data.get('status', 'pending'),
            'time': data.get('time', datetime.now().strftime('%H:%M:%S')),
            'timestamp': data.get('timestamp', time.time()),
            'latency': data.get('latency'),
            'brand': data.get('brand', ''),
            'preview': data.get('preview', ''),
            'error': data.get('error'),
            'metadata': data.get('metadata', {})
        }
        
        # 添加到缓存
        if execution_id not in _intelligence_cache:
            _intelligence_cache[execution_id] = []
        
        _intelligence_cache[execution_id].append(item)
        
        api_logger.info(f'添加情报项：executionId={execution_id}, model={item["model"]}, status={item["status"]}')
        
        # 通知订阅者（SSE）
        if execution_id in _pipeline_subscribers:
            for subscriber_queue in _pipeline_subscribers[execution_id]:
                subscriber_queue.append({
                    'type': 'new_item',
                    'item': item
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'itemId': item['id'],
                'executionId': execution_id
            }
        })
        
    except Exception as e:
        api_logger.error(f'添加情报项失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'ADD_ITEM_ERROR'
        }), 500


@intelligence_bp.route('/api/intelligence/update', methods=['POST'])
@require_auth_optional
def update_intelligence_item():
    """
    更新情报项状态
    
    Request Body:
        - executionId: 执行 ID
        - itemId: 情报项 ID
        - status: 新状态
        - preview: 响应预览（可选）
        - error: 错误信息（可选）
        - latency: 延迟（可选）
    
    Returns:
        更新结果
    """
    try:
        data = request.get_json()
        
        execution_id = data.get('executionId')
        item_id = data.get('itemId')
        new_status = data.get('status')
        
        if not execution_id or not item_id or not new_status:
            return jsonify({
                'status': 'error',
                'error': 'executionId, itemId, and status are required',
                'code': 'MISSING_PARAMS'
            }), 400
        
        # 查找并更新情报项
        items = _intelligence_cache.get(execution_id, [])
        updated = False
        
        for item in items:
            if item['id'] == item_id:
                item['status'] = new_status
                
                if 'preview' in data:
                    item['preview'] = data['preview']
                if 'error' in data:
                    item['error'] = data['error']
                if 'latency' in data:
                    item['latency'] = data['latency']
                
                updated = True
                api_logger.info(f'更新情报项：executionId={execution_id}, itemId={item_id}, status={new_status}')
                break
        
        if not updated:
            return jsonify({
                'status': 'error',
                'error': 'Item not found',
                'code': 'ITEM_NOT_FOUND'
            }), 404
        
        # 通知订阅者（SSE）
        if execution_id in _pipeline_subscribers:
            for subscriber_queue in _pipeline_subscribers[execution_id]:
                subscriber_queue.append({
                    'type': 'item_updated',
                    'itemId': item_id,
                    'status': new_status
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'itemId': item_id,
                'executionId': execution_id,
                'status': new_status
            }
        })
        
    except Exception as e:
        api_logger.error(f'更新情报项失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'UPDATE_ITEM_ERROR'
        }), 500


@intelligence_bp.route('/api/intelligence/clear', methods=['POST'])
@require_auth_optional
def clear_intelligence_pipeline():
    """
    清空情报流水线
    
    Request Body:
        - executionId: 执行 ID
    
    Returns:
        清空结果
    """
    try:
        data = request.get_json()
        execution_id = data.get('executionId')
        
        if not execution_id:
            return jsonify({
                'status': 'error',
                'error': 'executionId is required',
                'code': 'MISSING_EXECUTION_ID'
            }), 400
        
        # 清空缓存
        if execution_id in _intelligence_cache:
            count = len(_intelligence_cache[execution_id])
            del _intelligence_cache[execution_id]
            api_logger.info(f'清空情报流水线：executionId={execution_id}, 共{count}条记录')
        else:
            api_logger.info(f'情报流水线为空：executionId={execution_id}')
        
        # 通知订阅者
        if execution_id in _pipeline_subscribers:
            for subscriber_queue in _pipeline_subscribers[execution_id]:
                subscriber_queue.append({
                    'type': 'cleared',
                    'executionId': execution_id
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'executionId': execution_id,
                'cleared': True
            }
        })
        
    except Exception as e:
        api_logger.error(f'清空情报流水线失败：{e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'CLEAR_ERROR'
        }), 500


def _calculate_pipeline_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算流水线统计数据
    """
    stats = {
        'totalCount': len(items),
        'successCount': 0,
        'processingCount': 0,
        'errorCount': 0,
        'pendingCount': 0,
        'avgLatency': 0,
        'successRate': 0
    }
    
    total_latency = 0
    completed_count = 0
    
    for item in items:
        status = item.get('status', 'pending')
        
        if status == 'success':
            stats['successCount'] += 1
            completed_count += 1
        elif status == 'processing':
            stats['processingCount'] += 1
        elif status == 'error':
            stats['errorCount'] += 1
            completed_count += 1
        elif status == 'pending':
            stats['pendingCount'] += 1
        
        if item.get('latency'):
            total_latency += item['latency']
    
    if completed_count > 0:
        stats['successRate'] = round(stats['successCount'] / completed_count * 100, 2)
    
    if stats['successCount'] > 0:
        stats['avgLatency'] = round(total_latency / stats['successCount'], 2)
    
    return stats


def _generate_mock_intelligence_data(brand_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    生成模拟情报数据（用于演示）
    """
    import random
    
    models = ['doubao', 'qwen', 'deepseek', 'deepseekr1', 'chatgpt', 'gemini', 'zhipu', 'wenxin']
    statuses = ['success', 'success', 'success', 'processing', 'error']  # 成功概率更高
    questions = [
        f'{brand_name}的核心竞争优势是什么？',
        f'{brand_name}在消费者心中的定位如何？',
        f'{brand_name}与竞品的主要差异在哪里？',
        f'{brand_name}的品牌形象有哪些关键词？',
        f'{brand_name}在社交媒体上的声量如何？',
        f'{brand_name}的用户群体特征是什么？',
        f'{brand_name}的市场占有率趋势如何？',
        f'{brand_name}的主要营销渠道有哪些？'
    ]
    
    items = []
    for i in range(limit):
        model = random.choice(models)
        status = random.choice(statuses)
        
        item = {
            'id': str(int(time.time() * 1000) + i),
            'question': random.choice(questions),
            'model': model,
            'status': status,
            'time': datetime.now().strftime('%H:%M:%S'),
            'timestamp': time.time() - random.randint(0, 3600),
            'brand': brand_name,
            'latency': random.randint(200, 2000) if status == 'success' else None,
            'preview': f'{model} 对{brand_name}的分析结果...' if status == 'success' else None,
            'error': '请求超时' if status == 'error' else None,
            'metadata': {
                'tokens_used': random.randint(100, 500) if status == 'success' else 0,
                'platform': model
            }
        }
        
        items.append(item)
    
    # 按时间戳倒序排列
    items.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return items


# 注册 Blueprint
def register_blueprints(app):
    """注册情报流水线 Blueprint"""
    from wechat_backend.logging_config import api_logger
    app.register_blueprint(intelligence_bp)
    api_logger.info('Intelligence Blueprint registered')
