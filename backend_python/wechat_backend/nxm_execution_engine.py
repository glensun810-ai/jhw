"""
NxM 执行引擎 - 主入口

重构版本：模块化
- 熔断器 → nxm_circuit_breaker.py
- 任务调度 → nxm_scheduler.py
- 结果聚合 → nxm_result_aggregator.py

输入：NxM 执行参数
输出：执行结果
"""

import time
import threading
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE
# P0 修复：延迟导入 config_manager，避免循环依赖
# from wechat_backend.config_manager import config_manager
from wechat_backend.logging_config import api_logger
from wechat_backend.database import save_test_record

# BUG-NEW-002 修复：异步执行引擎
from wechat_backend.performance.async_execution_engine import execute_async

# 导入模块
from wechat_backend.nxm_circuit_breaker import get_circuit_breaker
from wechat_backend.nxm_scheduler import NxMScheduler, create_scheduler
from wechat_backend.nxm_result_aggregator import (
    parse_geo_with_validation,
    verify_completion,
    deduplicate_results,
    aggregate_results_by_brand
)


def execute_nxm_test(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str,
    user_level: str,
    execution_store: Dict[str, Any],
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    执行 NxM 测试
    
    参数:
    - execution_id: 执行 ID
    - main_brand: 主品牌
    - competitor_brands: 竞品品牌列表
    - selected_models: 选中的 AI 模型列表
    - raw_questions: 原始问题列表
    - user_id: 用户 ID
    - user_level: 用户等级
    - execution_store: 执行状态存储
    - timeout_seconds: 超时时间（秒）
    
    返回:
    - success: 是否成功
    - execution_id: 执行 ID
    - formula: 执行公式描述
    """
    
    # 创建调度器
    scheduler = create_scheduler(execution_id, execution_store)
    
    # 计算总任务数
    total_tasks = (1 + len(competitor_brands or [])) * len(raw_questions) * len(selected_models)
    scheduler.initialize_execution(total_tasks)
    
    # 启动超时计时器
    def on_timeout():
        scheduler.fail_execution(f"执行超时 ({timeout_seconds}秒)")
    
    scheduler.start_timeout_timer(timeout_seconds, on_timeout)
    
    # 在后台线程中执行
    def run_execution():
        try:
            results = []
            completed = 0

            # P0-2 修复：遍历所有品牌（主品牌 + 竞品）
            all_brands = [main_brand] + (competitor_brands or [])
            api_logger.info(f"[NxM] 执行品牌数：{len(all_brands)}, 品牌列表：{all_brands}")

            # 外层循环：遍历品牌
            for brand in all_brands:
                # 中层循环：遍历问题
                for q_idx, question in enumerate(raw_questions):
                    # 内层循环：遍历模型
                    for model_info in selected_models:
                        model_name = model_info.get('name', '')

                        # 检查模型是否可用（熔断器）
                        if not scheduler.is_model_available(model_name):
                            api_logger.warning(f"[NxM] 模型 {model_name} 已熔断，跳过")
                            completed += 1
                            scheduler.update_progress(completed, total_tasks, 'ai_fetching')
                            continue

                        try:
                            # P0 修复：直接使用 Config 类获取 API Key，避免循环依赖
                            from config import Config

                            # 创建 AI 客户端
                            client = AIAdapterFactory.create(model_name)
                            api_key = Config.get_api_key(model_name)

                            if not api_key:
                                raise ValueError(f"模型 {model_name} API Key 未配置")

                            # 构建提示词
                            # P0-2 修复：使用当前品牌和其竞争对手
                            current_competitors = [b for b in all_brands if b != brand]
                            prompt = GEO_PROMPT_TEMPLATE.format(
                                brand_name=brand,
                                competitors=', '.join(current_competitors) if current_competitors else '无',
                                question=question
                            )

                            # 修复 3: 添加 AI 响应重试机制
                            max_retries = 2
                            retry_count = 0
                            response = None
                            geo_data = None
                            parse_error = None

                            while retry_count <= max_retries:
                                try:
                                    # 调用 AI 接口
                                    response = client.generate_response(
                                        prompt=prompt,
                                        api_key=api_key
                                    )

                                    # 解析 GEO 数据
                                    geo_data, parse_error = parse_geo_with_validation(
                                        response,
                                        execution_id,
                                        q_idx,
                                        model_name
                                    )

                                    # 如果解析成功，跳出重试循环
                                    if not parse_error and not geo_data.get('_error'):
                                        break

                                    # 解析失败，记录日志并准备重试
                                    api_logger.warning(f"[NxM] 解析失败，准备重试：{model_name}, Q{q_idx}, 尝试 {retry_count + 1}/{max_retries}")
                                    retry_count += 1

                                except Exception as call_error:
                                    api_logger.error(f"[NxM] AI 调用失败：{model_name}, Q{q_idx}: {call_error}")
                                    retry_count += 1

                            # 检查最终结果
                            if not response or not geo_data or geo_data.get('_error'):
                                api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                                scheduler.record_model_failure(model_name)
                                # 仍然添加结果，但标记为失败
                                result = {
                                    'brand': brand,
                                    'question': question,
                                    'model': model_name,
                                    'response': response,
                                    'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                    'timestamp': datetime.now().isoformat(),
                                    '_failed': True
                                }
                                scheduler.add_result(result)
                                results.append(result)
                            else:
                                scheduler.record_model_success(model_name)

                                # 构建结果
                                result = {
                                    'brand': brand,
                                    'question': question,
                                    'model': model_name,
                                    'response': response,
                                    'geo_data': geo_data,
                                    'timestamp': datetime.now().isoformat()
                                }

                                scheduler.add_result(result)
                                results.append(result)

                            # 更新进度
                            completed += 1
                            scheduler.update_progress(completed, total_tasks, 'ai_fetching')

                        except Exception as e:
                            # P1-2 修复：完善错误处理，记录详细错误信息
                            error_message = f"AI 调用失败：{model_name}, 问题{q_idx+1}: {str(e)}"
                            api_logger.error(f"[NxM] {error_message}")

                            # 记录模型失败
                            scheduler.record_model_failure(model_name)

                            # 更新进度，包含错误信息
                            completed += 1
                            scheduler.update_progress(completed, total_tasks, 'ai_fetching')

                            # P1-2 修复：在 execution_store 中记录错误详情
                            try:
                                from wechat_backend.views import execution_store
                                if execution_id in execution_store:
                                    # 累积错误信息
                                    if 'error_details' not in execution_store[execution_id]:
                                        execution_store[execution_id]['error_details'] = []

                                    execution_store[execution_id]['error_details'].append({
                                        'model': model_name,
                                        'question_index': q_idx,
                                        'error_type': type(e).__name__,
                                        'error_message': str(e),
                                        'timestamp': datetime.now().isoformat()
                                    })

                                    # 更新状态为部分失败
                                    execution_store[execution_id].update({
                                        'status': 'partial_failure' if completed < total_tasks else 'completed_with_errors',
                                        'error': f'{len(execution_store[execution_id]["error_details"])} 个 AI 调用失败'
                                    })
                            except Exception as store_error:
                                api_logger.error(f"[NxM] 更新 execution_store 失败：{store_error}")
            
            # 验证执行完成
            verification = verify_completion(results, total_tasks)
            
            if verification['success']:
                # 去重结果
                deduplicated = deduplicate_results(results)
                
                # 完成执行
                scheduler.complete_execution()
                
                # 保存测试记录
                save_test_record(
                    execution_id=execution_id,
                    user_id=user_id,
                    brand_name=main_brand,
                    results=deduplicated,
                    user_level=user_level
                )

                # 【P0 修复】生成高级分析数据
                try:
                    api_logger.info(f"[NxM] 开始生成高级分析数据：{execution_id}")
                    
                    # 0. 记录缺失的品牌
                    executed_brands = set(r.get('brand') for r in deduplicated if r.get('brand'))
                    all_expected_brands = set([main_brand] + (competitor_brands or []))
                    missing_brands = list(all_expected_brands - executed_brands)
                    if missing_brands:
                        api_logger.warning(f"[NxM] 以下品牌数据缺失：{missing_brands}")
                        execution_store[execution_id]['missing_brands'] = missing_brands
                    
                    # 1. 生成核心洞察
                    try:
                        api_logger.info(f"[NxM] 开始生成核心洞察：{execution_id}")
                        target_brand_scores = brand_scores.get(main_brand, {})
                        authority = target_brand_scores.get('overallAuthority', 50)
                        visibility = target_brand_scores.get('overallVisibility', 50)
                        purity = target_brand_scores.get('overallPurity', 50)
                        consistency = target_brand_scores.get('overallConsistency', 50)
                        dimensions = {'权威度': authority, '可见度': visibility, '纯净度': purity, '一致性': consistency}
                        advantage_dim = max(dimensions, key=dimensions.get)
                        risk_dim = min(dimensions, key=dimensions.get)
                        insights = {
                            'advantage': f"{advantage_dim}表现突出，得分{dimensions[advantage_dim]}分",
                            'risk': f"{risk_dim}相对薄弱，得分{dimensions[risk_dim]}分，需重点关注",
                            'opportunity': f"{risk_dim}有较大提升空间，建议优先优化"
                        }
                        execution_store[execution_id]['insights'] = insights
                        api_logger.info(f"[NxM] 核心洞察生成完成：{execution_id}")
                    except Exception as e:
                        api_logger.error(f"[NxM] 核心洞察生成失败：{e}")
                    
                    # 2. 生成信源纯净度分析
                    try:
                        api_logger.info(f"[NxM] 开始生成信源纯净度分析：{execution_id}")
                        from wechat_backend.analytics.source_intelligence_processor import SourceIntelligenceProcessor
                        processor = SourceIntelligenceProcessor()
                        source_purity_data = processor.process(main_brand, deduplicated)
                        execution_store[execution_id]['source_purity_data'] = source_purity_data
                        api_logger.info(f"[NxM] 信源纯净度分析完成：{execution_id}")
                    except Exception as e:
                        api_logger.error(f"[NxM] 信源纯净度分析失败：{e}")
                    
                    # 3. 生成信源情报图谱
                    try:
                        api_logger.info(f"[NxM] 开始生成信源情报图谱：{execution_id}")
                        nodes = []
                        node_id = 0
                        for result in deduplicated:
                            geo_data = result.get('geo_data', {})
                            cited_sources = geo_data.get('cited_sources', [])
                            for source in cited_sources:
                                nodes.append({
                                    'id': f'source_{node_id}',
                                    'name': source.get('site_name', '未知信源'),
                                    'value': source.get('weight', 50),
                                    'sentiment': source.get('attitude', 'neutral'),
                                    'category': source.get('category', 'general'),
                                    'url': source.get('url', '')
                                })
                                node_id += 1
                        source_intelligence_map = {'nodes': nodes, 'links': []}
                        execution_store[execution_id]['source_intelligence_map'] = source_intelligence_map
                        api_logger.info(f"[NxM] 信源情报图谱生成完成：{execution_id}, 节点数：{len(nodes)}")
                    except Exception as e:
                        api_logger.error(f"[NxM] 信源情报图谱生成失败：{e}")
                    
                    api_logger.info(f"[NxM] 高级分析数据生成完成：{execution_id}")
                except Exception as e:
                    api_logger.error(f"[NxM] 生成高级分析数据失败：{e}")

                api_logger.info(f"[NxM] 执行成功：{execution_id}, 结果数：{len(deduplicated)}")
            else:
                scheduler.fail_execution(verification['message'])
            
        except Exception as e:
            api_logger.error(f"[NxM] 执行异常：{execution_id}: {e}")
            scheduler.fail_execution(str(e))
        finally:
            scheduler.cancel_timeout_timer()
    
    # 启动后台线程
    thread = threading.Thread(target=run_execution)
    thread.daemon = True
    thread.start()
    
    return {
        'success': True,
        'execution_id': execution_id,
        'formula': f'{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求',
        'total_tasks': total_tasks
    }


def verify_nxm_execution(
    execution_id: str,
    execution_store: Dict[str, Any]
) -> Dict[str, Any]:
    """
    验证 NxM 执行结果
    
    参数:
    - execution_id: 执行 ID
    - execution_store: 执行状态存储
    
    返回:
    - verified: 是否验证通过
    - message: 消息
    """
    if execution_id not in execution_store:
        return {
            'verified': False,
            'message': f'执行 ID 不存在：{execution_id}'
        }
    
    store = execution_store[execution_id]
    results = store.get('results', [])
    total = store.get('total', 0)
    
    verification = verify_completion(results, total)
    
    return {
        'verified': verification['success'],
        'message': verification['message'] if not verification['success'] else '验证通过'
    }


# =============================================================================
# BUG-NEW-002 修复：异步执行支持
# =============================================================================

def call_ai_api_wrapper(
    question: str,
    model_name: str,
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    **kwargs
) -> Dict[str, Any]:
    """
    AI 调用包装函数（适配异步引擎）
    
    Args:
        question: 问题
        model_name: 模型名称
        execution_id: 执行 ID
        main_brand: 主品牌
        competitor_brands: 竞品品牌列表
        **kwargs: 其他参数
    
    Returns:
        AI 调用结果
    """
    from config import Config
    
    try:
        # 创建 AI 客户端
        client = AIAdapterFactory.create(model_name)
        api_key = Config.get_api_key(model_name)
        
        if not api_key:
            raise ValueError(f"模型 {model_name} API Key 未配置")
        
        # 构建提示词
        prompt = GEO_PROMPT_TEMPLATE.format(
            brand_name=main_brand,
            competitors=', '.join(competitor_brands) if competitor_brands else '无',
            question=question
        )
        
        # 调用 AI（带重试）
        max_retries = 2
        retry_count = 0
        response = None
        geo_data = None
        
        while retry_count <= max_retries:
            try:
                response = client.generate_response(
                    prompt=prompt,
                    api_key=api_key
                )
                
                geo_data, parse_error = parse_geo_with_validation(
                    response,
                    execution_id,
                    0,  # q_idx
                    model_name
                )
                
                if not parse_error and not geo_data.get('_error'):
                    break
                    
            except Exception as e:
                api_logger.error(f"AI 调用失败：{model_name}: {e}")
                retry_count += 1
        
        # 返回结果
        return {
            'brand': brand,
            'question': question,
            'model': model_name,
            'response': response,
            'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
            'timestamp': datetime.now().isoformat(),
            '_failed': not geo_data or geo_data.get('_error')
        }
        
    except Exception as e:
        api_logger.error(f"AI 调用异常：{model_name}: {e}")
        return {
            'brand': brand,
            'question': question,
            'model': model_name,
            'response': None,
            'geo_data': {'_error': str(e)},
            'timestamp': datetime.now().isoformat(),
            '_failed': True
        }


async def execute_nxm_test_async(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str,
    user_level: str,
    execution_store: Dict[str, Any],
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    异步执行 NxM 测试（BUG-NEW-002 修复）
    
    Args:
        execution_id: 执行 ID
        main_brand: 主品牌
        competitor_brands: 竞品品牌列表
        selected_models: 选中的模型列表
        raw_questions: 问题列表
        user_id: 用户 ID
        user_level: 用户等级
        execution_store: 执行状态存储
        timeout_seconds: 超时时间（秒）
    
    Returns:
        执行结果
    """
    # 获取最大并发数
    max_concurrent = int(os.getenv('ASYNC_MAX_CONCURRENT', '3'))
    
    api_logger.info(f"[Async] 开始异步执行：{len(raw_questions)}问题 × {len(selected_models)}模型，并发数：{max_concurrent}")
    
    # 使用异步引擎执行
    results = await execute_async(
        questions=raw_questions,
        models=[m['name'] for m in selected_models],
        execute_func=call_ai_api_wrapper,
        max_concurrent=max_concurrent,
        execution_id=execution_id,
        main_brand=main_brand,
        competitor_brands=competitor_brands
    )
    
    # 更新执行状态
    if execution_store and execution_id in execution_store:
        execution_store[execution_id].update({
            'progress': 100,
            'status': 'completed',
            'results': results,
            'completed': len([r for r in results if not r.get('_failed')]),
            'total': len(results)
        })
    
    # 统计结果
    success_count = len([r for r in results if not r.get('_failed')])
    failed_count = len([r for r in results if r.get('_failed')])
    
    api_logger.info(f"[Async] 异步执行完成：成功 {success_count}/{len(results)}, 失败 {failed_count}/{len(results)}")
    
    return {
        'success': True,
        'execution_id': execution_id,
        'results': results,
        'formula': f'{len(raw_questions)}问题 × {len(selected_models)}模型 = {len(results)}次请求 (异步执行，并发数={max_concurrent})',
        'success_count': success_count,
        'failed_count': failed_count
    }
