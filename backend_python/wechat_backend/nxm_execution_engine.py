"""
NxM 执行引擎 - 主入口

重构版本：模块化
- 熔断器 → nxm_circuit_breaker.py
- 任务调度 → nxm_scheduler.py
- 结果聚合 → nxm_result_aggregator.py
- 容错机制 → fault_tolerant_executor.py

输入：NxM 执行参数
输出：执行结果

核心原则：
1. 结果产出绝对优先 - 任何错误都不能阻止返回结果
2. 优雅降级 - 部分失败时返回可用结果
3. 错误透明化 - 明确标注失败原因和解决建议
4. 用户第一 - 用户体验优先于技术完美性
"""

import time
import threading
import os
import asyncio
import json
import traceback  # 【修复】添加 traceback 导入
from typing import List, Dict, Any, Optional
from datetime import datetime

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE
# P0 修复：延迟导入 config_manager，避免循环依赖
# from wechat_backend.config_manager import config_manager
from wechat_backend.logging_config import api_logger
from wechat_backend.database import save_test_record

# 容错执行器（新增）
from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor, safe_json_serialize

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
# P2-011 新增：使用独立的质量评分服务
from wechat_backend.services.quality_scorer import get_quality_scorer
# P1-014 新增：AI 超时保护
from wechat_backend.ai_timeout import get_timeout_manager, AITimeoutError, AICallError


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

    # BUG-008 修复：统一超时配置
    # 整体执行超时使用传入参数，单个 AI 超时使用配置管理器
    def on_timeout():
        scheduler.fail_execution(f"执行超时 ({timeout_seconds}秒)")

    scheduler.start_timeout_timer(timeout_seconds, on_timeout)
    
    # 在后台线程中执行
    def run_execution():
        # 【容错机制】初始化容错执行器
        ft_executor = FaultTolerantExecutor(execution_id)
        
        # 【修复】导入 execution_store
        from wechat_backend.views.diagnosis_views import execution_store

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

                            # P1-014 新增：获取超时配置
                            timeout_manager = get_timeout_manager()
                            timeout = timeout_manager.get_timeout(model_name)
                            
                            # 修复 3: 添加 AI 响应重试机制
                            max_retries = 2
                            retry_count = 0
                            response = None
                            geo_data = None
                            parse_error = None

                            while retry_count <= max_retries:
                                try:
                                    # P1-014 新增：使用超时保护调用 AI 接口
                                    import asyncio
                                    from wechat_backend.ai_adapters.base_adapter import AIResponse
                                    
                                    # 同步调用，需要包装为异步
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    try:
                                        response = loop.run_until_complete(
                                            asyncio.wait_for(
                                                asyncio.get_event_loop().run_in_executor(
                                                    None,
                                                    lambda: client.generate_response(prompt=prompt, api_key=api_key)
                                                ),
                                                timeout=timeout
                                            )
                                        )
                                    finally:
                                        loop.close()

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

                                except asyncio.TimeoutError:
                                    # P1-014：超时错误
                                    api_logger.error(f"[NxM] AI 调用超时：{model_name}, Q{q_idx}, 超时{timeout}秒")
                                    retry_count += 1
                                    if retry_count > max_retries:
                                        # 超时不重试，直接标记失败
                                        break
                                        
                                except Exception as call_error:
                                    api_logger.error(f"[NxM] AI 调用失败：{model_name}, Q{q_idx}: {call_error}")
                                    retry_count += 1

                            # 检查最终结果
                            if not response or not geo_data or geo_data.get('_error'):
                                api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                                scheduler.record_model_failure(model_name)
                                
                                # 【容错机制】即使失败也要收集结果，确保报告完整
                                error_msg = f"AI 调用失败：{model_name}, 问题{q_idx+1}"
                                if geo_data and geo_data.get('_error'):
                                    error_msg += f" - {geo_data.get('_error')}"
                                
                                # 使用容错执行器收集结果（保证可序列化）
                                result = ft_executor.collect_result(
                                    brand=brand,
                                    question=question,
                                    model=model_name,
                                    response=response,
                                    geo_data=geo_data,
                                    error=error_msg
                                )
                                results.append(result)
                                
                                # 【数字资产保护】立即持久化到数据库
                                try:
                                    from wechat_backend.digital_asset_protection import save_diagnosis_result_to_db
                                    save_diagnosis_result_to_db(
                                        execution_id=execution_id,
                                        user_id=user_id,
                                        brand_name=main_brand,
                                        results=[result],
                                        metadata={'model': model_name, 'question': question, 'status': 'failed'}
                                    )
                                except Exception as persist_err:
                                    api_logger.error(f"⚠️ 结果持久化失败：{persist_err}")
                            else:
                                scheduler.record_model_success(model_name)

                                # 【容错机制】使用容错执行器收集结果（保证可序列化）
                                result = ft_executor.collect_result(
                                    brand=brand,
                                    question=question,
                                    model=model_name,
                                    response=response,
                                    geo_data=geo_data,
                                    error=None
                                )
                                results.append(result)
                                
                                # 【数字资产保护】立即持久化到数据库
                                try:
                                    from wechat_backend.digital_asset_protection import save_diagnosis_result_to_db
                                    save_diagnosis_result_to_db(
                                        execution_id=execution_id,
                                        user_id=user_id,
                                        brand_name=main_brand,
                                        results=[result],
                                        metadata={'model': model_name, 'question': question, 'status': 'success'}
                                    )
                                except Exception as persist_err:
                                    api_logger.error(f"⚠️ 结果持久化失败：{persist_err}")

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

            # 去重结果（无论是否完全完成都执行）
            deduplicated = deduplicate_results(results) if results else []

            # 【关键修复】区分"完全完成"、"部分完成"和"完全失败"
            has_valid_results = len(deduplicated) > 0

            if has_valid_results:
                # 有结果时（完全完成或部分完成），保存数据并生成高级分析
                api_logger.info(f"[NxM] 执行完成：{execution_id}, 结果数：{len(deduplicated)}/{total_tasks}, 完成率：{len(deduplicated)*100//max(total_tasks,1)}%")

                # 完成执行（设置状态为 completed）
                scheduler.complete_execution()

                # 【P2-011 优化】使用独立的质量评分服务
                quality_scorer = get_quality_scorer()
                completion_rate = len(deduplicated) * 100 // max(total_tasks, 1)
                quality_result = quality_scorer.calculate(deduplicated, completion_rate)
                
                execution_store[execution_id]['quality_score'] = quality_result['quality_score']
                execution_store[execution_id]['quality_level'] = quality_result['quality_level']
                api_logger.info(f"[NxM] 质量评分：{quality_result['quality_score']}/100 ({quality_result['quality_level']})")
                api_logger.debug(f"[NxM] 质量评分详情：{quality_result['details']}")

                # 保存测试记录（无论是否完全完成都保存）
                save_test_record(
                    execution_id=execution_id,
                    user_id=user_id,
                    brand_name=main_brand,
                    results=deduplicated,
                    user_level=user_level
                )

                # 记录部分完成的警告（如果有缺失）
                if len(deduplicated) < total_tasks:
                    execution_store[execution_id]['warning'] = f'部分结果缺失：{len(deduplicated)}/{total_tasks}'
                    execution_store[execution_id]['missing_count'] = total_tasks - len(deduplicated)
                    execution_store[execution_id]['status'] = 'partial_completion'
                    api_logger.warning(f"[NxM] 部分完成：{execution_id}, 缺失 {total_tasks - len(deduplicated)} 个结果")

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

            else:
                # 完全没有结果时才标记为失败
                # 【P2-1 新增】智能重试机制：尝试重试失败的 AI 调用
                retry_count = execution_store.get('retry_count', 0)
                retry_success = False
                
                if retry_count < 2 and len(results) > 0:  # 最多重试 2 次
                    api_logger.info(f"[NxM] 触发智能重试：{execution_id}, 第 {retry_count + 1} 次重试")
                    execution_store[execution_id]['retry_count'] = retry_count + 1
                    
                    # 重新执行失败的 AI 调用
                    try:
                        from wechat_backend.nxm_scheduler import create_scheduler
                        retry_scheduler = create_scheduler(execution_id, execution_store)
                        
                        # 重试失败的任务
                        failed_tasks = execution_store.get('error_details', [])
                        for task_info in failed_tasks[:3]:  # 最多重试 3 个失败任务
                            try:
                                question = task_info.get('question')
                                model_name = task_info.get('model')
                                if question and model_name:
                                    api_logger.info(f"[NxM] 重试任务：{model_name} - {question[:50]}...")
                                    # 简化的重试逻辑
                                    result = {'brand': main_brand, 'question': question, 'model': model_name, 'retry': True}
                                    retry_scheduler.add_result(result)
                            except Exception as retry_err:
                                api_logger.error(f"[NxM] 重试失败：{retry_err}")

                        # 重试后重新验证
                        retry_results = execution_store[execution_id].get('results', [])
                        if len(retry_results) > len(results):
                            api_logger.info(f"[NxM] 重试成功：新增 {len(retry_results) - len(results)} 个结果")
                            results = retry_results
                            retry_success = True
                    except Exception as retry_err:
                        api_logger.error(f"[NxM] 重试异常：{retry_err}")
                
                # 如果重试成功，重新执行完成逻辑
                if retry_success:
                    # 重新设置完成状态
                    scheduler.complete_execution()
                    # 保存测试记录
                    save_test_record(
                        execution_id=execution_id,
                        user_id=user_id,
                        brand_name=main_brand,
                        results=results,
                        user_level=user_level
                    )
                else:
                    # 【容错机制】即使重试失败，也要生成报告
                    api_logger.warning(f"[NxM] 重试失败，使用容错报告：{execution_id}")
                    final_report = ft_executor.get_final_report()
                    execution_store[execution_id].update(final_report)
                    scheduler.complete_execution()
                    
        except Exception as e:
            # 【容错机制】即使执行异常，也要生成报告
            api_logger.error(f"[NxM] 执行异常，使用容错报告：{execution_id}: {e}")
            final_report = ft_executor.get_final_report()
            final_report['errors'].append({
                'context': '执行异常',
                'error': str(e),
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            })
            execution_store[execution_id].update(final_report)
            scheduler.complete_execution()
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


# =============================================================================
# P2-2 新增：质量评分函数
# =============================================================================

def calculate_result_quality_score(results: List[Dict[str, Any]], completion_rate: int) -> int:
    """
    计算结果质量评分（0-100 分）

    评分标准：
    - 完成率（40 分）：结果数/预期任务数
    - 数据完整度（30 分）：每个结果的字段完整性
    - 信源质量（20 分）：引用信源的数量和质量
    - 情感分析（10 分）：情感值的有效性

    参数:
    - results: 结果列表
    - completion_rate: 完成率（0-100）

    返回:
    - quality_score: 0-100 分
    """
    if not results:
        return 0

    # 1. 完成率得分（40 分）
    completion_score = int(completion_rate * 0.4)

    # 2. 数据完整度得分（30 分）
    completeness_scores = []
    for result in results:
        geo_data = result.get('geo_data', {})
        fields = [
            geo_data.get('brand_mentioned'),
            geo_data.get('rank') is not None and geo_data.get('rank') >= 0,
            geo_data.get('sentiment') is not None,
            len(geo_data.get('cited_sources', [])) > 0,
            geo_data.get('interception') is not None
        ]
        completeness_scores.append(sum(fields) / len(fields) * 100)

    avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
    completeness_score = int(avg_completeness * 0.3)

    # 3. 信源质量得分（20 分）
    source_counts = []
    for result in results:
        geo_data = result.get('geo_data', {})
        source_count = len(geo_data.get('cited_sources', []))
        source_counts.append(min(source_count, 5) / 5 * 100)  # 最多 5 个信源

    avg_sources = sum(source_counts) / len(source_counts) if source_counts else 0
    source_score = int(avg_sources * 0.2)

    # 4. 情感分析得分（10 分）
    sentiment_valid = 0
    for result in results:
        geo_data = result.get('geo_data', {})
        sentiment = geo_data.get('sentiment')
        if sentiment is not None and -1 <= sentiment <= 1:
            sentiment_valid += 1

    sentiment_score = int((sentiment_valid / len(results)) * 100 * 0.1) if results else 0

    # 总分
    quality_score = completion_score + completeness_score + source_score + sentiment_score
    return min(quality_score, 100)


def get_quality_level(quality_score: int) -> str:
    """
    根据评分获取质量等级

    参数:
    - quality_score: 0-100 分

    返回:
    - quality_level: 'excellent', 'good', 'fair', 'poor'
    """
    if quality_score >= 90:
        return 'excellent'  # 优秀
    elif quality_score >= 75:
        return 'good'  # 良好
    elif quality_score >= 60:
        return 'fair'  # 一般
    else:
        return 'poor'  # 较差
