"""
诊断报告重试 API

功能：
- 支持单个维度结果的重试
- 支持报告重新生成
- 支持错误恢复

路由：
- POST /api/diagnosis/retry-dimension - 重试单个维度
- POST /api/diagnosis/regenerate - 重新生成报告
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from wechat_backend.logging_config import api_logger
from wechat_backend.security.auth import require_auth_optional
from wechat_backend.security.rate_limiting import rate_limit
from wechat_backend.monitoring.monitoring_decorator import monitored_endpoint
from wechat_backend.error_handler import handle_api_exceptions
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE
from wechat_backend.repositories import save_dimension_result, save_report_snapshot
from legacy_config import Config
import asyncio

# 创建蓝图
diagnosis_retry_bp = Blueprint('diagnosis_retry', __name__, url_prefix='/api/diagnosis')


@diagnosis_retry_bp.route('/retry-dimension', methods=['POST'])
@handle_api_exceptions
@require_auth_optional
@rate_limit(limit=5, window=60, per='endpoint')
@monitored_endpoint('/api/diagnosis/retry-dimension', require_auth=False, validate_inputs=True)
def retry_dimension():
    """
    重试单个维度
    
    请求参数:
    {
        "executionId": "exec_123",
        "dimensionName": "社交媒体影响力",
        "source": "doubao",
        "brand": "华为",
        "question": "介绍一下华为",
        "competitors": ["小米", "OPPO"]
    }
    
    响应:
    {
        "success": true,
        "data": {
            "dimension_name": "社交媒体影响力",
            "source": "doubao",
            "status": "success",
            "score": 85,
            "data": {...}
        }
    }
    """
    from wechat_backend.views.diagnosis_views import execution_store
    
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    # 提取参数
    execution_id = data.get('executionId')
    dimension_name = data.get('dimensionName')
    source = data.get('source')
    brand = data.get('brand', '')
    question = data.get('question', '')
    competitors = data.get('competitors', [])
    
    if not execution_id or not dimension_name or not source:
        return jsonify({'error': 'Missing required parameters: executionId, dimensionName, source'}), 400
    
    if not brand or not question:
        # 尝试从 execution_store 获取
        if execution_id in execution_store:
            store_data = execution_store[execution_id]
            if not brand:
                brand = store_data.get('brand_name', '')
            if not question:
                questions = store_data.get('questions', [])
                question = questions[0] if questions else ''
    
    if not brand or not question:
        return jsonify({'error': 'Missing brand or question, please provide them in the request'}), 400
    
    try:
        api_logger.info(f"[Retry] 开始重试维度：{dimension_name}, source: {source}, brand: {brand}")
        
        # 创建 AI 客户端
        client = AIAdapterFactory.create(source)
        api_key = Config.get_api_key(source)
        
        if not api_key:
            raise ValueError(f"模型 {source} API Key 未配置")
        
        # 构建提示词
        prompt = GEO_PROMPT_TEMPLATE.format(
            brand_name=brand,
            competitors=', '.join(competitors) if competitors else '无',
            question=question
        )
        
        # 使用超时保护调用 AI 接口
        from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor
        
        executor = FaultTolerantExecutor(timeout_seconds=30)
        
        # 同步调用（在后台线程中执行）
        def call_ai():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: client.send_prompt(prompt=prompt)
                        ),
                        timeout=30
                    )
                )
                return result
            finally:
                loop.close()
        
        import threading
        result_container = {'result': None, 'error': None}
        
        def run_in_thread():
            try:
                result_container['result'] = call_ai()
            except Exception as e:
                result_container['error'] = str(e)
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=35)  # 30 秒 AI 调用 + 5 秒缓冲
        
        if thread.is_alive():
            raise TimeoutError("AI 调用超时（35 秒）")
        
        if result_container['error']:
            raise Exception(result_container['error'])

        ai_result = result_container['result']

        # P0-STATUS-1 修复：AIResponse 使用 success 属性而非 status 属性
        if not ai_result.success:
            # AI 调用失败，返回错误
            return jsonify({
                'success': False,
                'error': ai_result.error_message
            }), 400
        
        # 解析 GEO 数据
        from wechat_backend.nxm_result_aggregator import parse_geo_with_validation
        
        geo_data, parse_error = parse_geo_with_validation(
            ai_result.data,
            execution_id,
            0,  # q_idx
            source
        )
        
        if parse_error or geo_data.get('_error'):
            return jsonify({
                'success': False,
                'error': parse_error or geo_data.get('_error', '解析失败')
            }), 400
        
        # 计算分数
        rank = geo_data.get('rank', -1)
        score = max(0, 100 - (rank - 1) * 10) if rank > 0 else None
        
        # 保存维度结果
        save_dimension_result(
            execution_id=execution_id,
            dimension_name=dimension_name,
            dimension_type='ai_analysis',
            source=source,
            status='success',
            score=score,
            data=geo_data,
            error_message=None
        )
        
        api_logger.info(f"[Retry] ✅ 维度重试成功：{dimension_name}, source: {source}")
        
        return jsonify({
            'success': True,
            'data': {
                'dimension_name': dimension_name,
                'source': source,
                'status': 'success',
                'score': score,
                'data': geo_data
            }
        })
        
    except TimeoutError as e:
        api_logger.error(f"[Retry] ❌ 维度重试超时：{dimension_name}, {e}")
        return jsonify({
            'success': False,
            'error': f'重试超时：{str(e)}'
        }), 408
    
    except Exception as e:
        api_logger.error(f"[Retry] ❌ 维度重试失败：{dimension_name}, {e}")
        return jsonify({
            'success': False,
            'error': f'重试失败：{str(e)}'
        }), 500


@diagnosis_retry_bp.route('/regenerate', methods=['POST'])
@handle_api_exceptions
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/api/diagnosis/regenerate', require_auth=False, validate_inputs=True)
def regenerate_report():
    """
    重新生成报告
    
    请求参数:
    {
        "executionId": "exec_123",
        "brandList": ["华为", "小米"],
        "selectedModels": [{"name": "doubao", "checked": true}],
        "customQuestions": ["介绍一下华为"]
    }
    
    响应:
    {
        "success": true,
        "executionId": "exec_new_123",
        "message": "报告重新生成中"
    }
    """
    from wechat_backend.views.diagnosis_views import perform_brand_test, execution_store
    import uuid
    
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    # 提取参数
    brand_list = data.get('brandList', [])
    selected_models = data.get('selectedModels', [])
    custom_questions = data.get('customQuestions', [])
    
    if not brand_list or not selected_models:
        return jsonify({'error': 'Missing required parameters: brandList, selectedModels'}), 400
    
    try:
        api_logger.info(f"[Regenerate] 开始重新生成报告，品牌：{brand_list[0]}")
        
        # 调用原有的 perform_brand_test 逻辑（但不返回响应，而是返回新的 execution_id）
        execution_id = str(uuid.uuid4())
        
        # 初始化执行存储
        execution_store[execution_id] = {
            'progress': 0,
            'completed': 0,
            'total': 0,
            'status': 'initializing',
            'stage': 'init',
            'results': [],
            'start_time': datetime.now().isoformat(),
            'regenerated_from': data.get('executionId')  # 记录是从哪个报告重新生成的
        }
        
        # 在后台线程中执行
        from wechat_backend.nxm_execution_engine import execute_nxm_test
        
        def run_async_test():
            try:
                result = execute_nxm_test(
                    execution_id=execution_id,
                    main_brand=brand_list[0],
                    competitor_brands=brand_list[1:] if len(brand_list) > 1 else [],
                    selected_models=selected_models,
                    raw_questions=custom_questions,
                    user_id='anonymous',
                    user_level='Free',
                    execution_store=execution_store
                )
                
                if result.get('success'):
                    api_logger.info(f"[Regenerate] ✅ 报告重新生成成功：{execution_id}")
                else:
                    api_logger.error(f"[Regenerate] ❌ 报告重新生成失败：{execution_id}")
                    
            except Exception as e:
                api_logger.error(f"[Regenerate] ❌ 报告重新生成异常：{execution_id}, {e}")
                execution_store[execution_id].update({
                    'status': 'failed',
                    'error': str(e)
                })
        
        import threading
        thread = threading.Thread(target=run_async_test)
        thread.start()
        
        return jsonify({
            'success': True,
            'executionId': execution_id,
            'message': '报告重新生成中'
        })
        
    except Exception as e:
        api_logger.error(f"[Regenerate] ❌ 报告重新生成异常：{e}")
        return jsonify({
            'success': False,
            'error': f'重新生成失败：{str(e)}'
        }), 500


# 导出蓝图
__all__ = ['diagnosis_retry_bp']
