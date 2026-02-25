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

改造记录:
- M001: 修复 AI 调用方法 (generate_response → send_prompt)
- M002: 添加容错包裹 (引入 FaultTolerantExecutor)
- M003: 实时持久化 (save_dimension_result)
"""

import time
import threading
import os
import asyncio
import json
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE
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
from wechat_backend.ai_timeout import get_timeout_manager, AITimeoutError

# 配置导入
from config import Config


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
    执行 NxM 测试（M001-M003 改造后版本）
    
    改造内容:
    - M001: 使用 send_prompt 替代 generate_response
    - M002: 使用 FaultTolerantExecutor 统一包裹 AI 调用
    - M003: 实时持久化维度结果到数据库
    """

    # 创建调度器
    scheduler = create_scheduler(execution_id, execution_store)

    # 计算总任务数
    total_tasks = (1 + len(competitor_brands or [])) * len(raw_questions) * len(selected_models)
    scheduler.initialize_execution(total_tasks)

    # BUG-008 修复：统一超时配置
    def on_timeout():
        scheduler.fail_execution(f"执行超时 ({timeout_seconds}秒)")

    scheduler.start_timeout_timer(timeout_seconds, on_timeout)

    # 在后台线程中执行
    def run_execution():
        # 【修复 P0-4】在 try 块外先导入 execution_store，避免作用域问题
        try:
            from wechat_backend.views.diagnosis_views import execution_store
        except ImportError:
            execution_store = {}
            api_logger.error(f"[NxM] 无法导入 execution_store，使用空字典")

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

                            # M002 改造：使用 FaultTolerantExecutor 统一包裹 AI 调用
                            # 创建容错执行器实例（每个调用独立）
                            ai_executor = FaultTolerantExecutor(timeout_seconds=timeout)

                            # P0-4 修复：在后台线程中使用 asyncio.run() 是安全的
                            # 因为 run_execution() 在独立线程中运行，没有现成事件循环
                            ai_result = asyncio.run(
                                ai_executor.execute_with_fallback(
                                    task_func=client.send_prompt,
                                    task_name=f"{brand}-{model_name}",
                                    source=model_name,
                                    prompt=prompt  # 直接传递参数
                                )
                            )
                            
                            # 检查 AI 调用结果
                            geo_data = None
                            parse_error = None

                            if ai_result.status == "success":
                                # AI 调用成功，解析 GEO 数据
                                scheduler.record_model_success(model_name)

                                # 解析 GEO 数据
                                geo_data, parse_error = parse_geo_with_validation(
                                    ai_result.data,
                                    execution_id,
                                    q_idx,
                                    model_name
                                )

                                # 检查解析结果
                                if parse_error or geo_data.get('_error'):
                                    # 解析失败，记录错误
                                    api_logger.warning(f"[NxM] 解析失败：{model_name}, Q{q_idx}: {parse_error or geo_data.get('_error')}")
                                    # P0-4 修复：直接使用字典收集结果
                                    # P3 修复：确保所有字段都是可序列化的
                                    result = {
                                        'brand': brand,
                                        'question': question,
                                        'model': model_name,
                                        'response': str(ai_result.data) if hasattr(ai_result, 'data') else str(ai_result),  # 修复：确保可序列化
                                        'geo_data': geo_data,
                                        'error': str(parse_error or geo_data.get('_error', '解析失败')),
                                        'error_type': str(ai_result.error_type.value) if hasattr(ai_result, 'error_type') and ai_result.error_type else 'parse_error'
                                    }
                                    results.append(result)
                                else:
                                    # 解析成功，收集结果
                                    # P3 修复：确保所有字段都是可序列化的
                                    result = {
                                        'brand': brand,
                                        'question': question,
                                        'model': model_name,
                                        'response': str(ai_result.data) if hasattr(ai_result, 'data') else str(ai_result),  # 修复：确保可序列化
                                        'geo_data': geo_data,
                                        'error': None,
                                        'error_type': None
                                    }
                                    results.append(result)
                            else:
                                # AI 调用失败，记录错误并继续（不中断流程）
                                scheduler.record_model_failure(model_name)
                                api_logger.error(f"[NxM] AI 调用失败：{model_name}, Q{q_idx}: {ai_result.error_message}")

                                # P0-4 修复：收集失败结果（保证报告完整）
                                # P3 修复：确保所有字段都是可序列化的
                                result = {
                                    'brand': brand,
                                    'question': question,
                                    'model': model_name,
                                    'response': None,
                                    'geo_data': None,
                                    'error': str(ai_result.error_message),
                                    'error_type': str(ai_result.error_type.value) if hasattr(ai_result, 'error_type') and ai_result.error_type else 'unknown'
                                }
                                results.append(result)
                            
                            # M003 改造：实时持久化维度结果
                            # 原有问题：结果仅在内存中，服务重启后丢失
                            # 改造后：每个维度结果立即保存到数据库，支持进度查询和历史追溯
                            try:
                                from wechat_backend.repositories import save_dimension_result, save_task_status

                                # 确定维度状态和分数
                                dim_status = "success" if (ai_result.status == "success" and geo_data and not geo_data.get('_error')) else "failed"
                                dim_score = None
                                if dim_status == "success" and geo_data:
                                    # 从 GEO 数据中提取排名作为分数参考
                                    rank = geo_data.get("rank", -1)
                                    if rank > 0:
                                        dim_score = max(0, 100 - (rank - 1) * 10)  # 排名第 1 得 100 分，每降 1 名减 10 分

                                # 保存维度结果
                                save_dimension_result(
                                    execution_id=execution_id,
                                    dimension_name=f"{brand}-{model_name}",
                                    dimension_type="ai_analysis",
                                    source=model_name,
                                    status=dim_status,
                                    score=dim_score,
                                    data=geo_data if dim_status == "success" else None,
                                    error_message=ai_result.error_message if dim_status == "failed" else (parse_error if parse_error else None)
                                )

                                # 实时更新进度
                                save_task_status(
                                    task_id=execution_id,
                                    stage='ai_fetching',
                                    progress=int((completed / total_tasks) * 100) if total_tasks > 0 else 0,
                                    status_text=f'已完成 {completed}/{total_tasks}',
                                    completed_count=completed,
                                    total_count=total_tasks
                                )

                                api_logger.info(f"[NxM] ✅ 维度结果持久化成功：{brand}-{model_name}, 状态：{dim_status}")

                            except Exception as persist_err:
                                # 持久化失败不影响主流程，仅记录错误
                                api_logger.error(f"[NxM] ⚠️ 维度结果持久化失败：{brand}-{model_name}, 错误：{persist_err}")

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

                            # P1-2 修复：使用数据库存储错误详情，避免导入问题
                            try:
                                from wechat_backend.repositories import save_task_status
                                
                                # 累积错误信息到数据库
                                save_task_status(
                                    task_id=execution_id,
                                    stage='failed',
                                    progress=int((completed / total_tasks) * 100) if total_tasks > 0 else 0,
                                    status_text=f'{error_message}',
                                    completed_count=completed,
                                    total_count=total_tasks
                                )
                            except Exception as store_error:
                                api_logger.error(f"[NxM] 更新任务状态失败：{store_error}")

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
                scorer = get_quality_scorer()
                
                # 计算完成率
                completion_rate = int(len(deduplicated) * 100 / max(total_tasks, 1))
                
                # P3 修复：使用正确的方法名 calculate 而不是 evaluate
                quality_score = scorer.calculate(deduplicated, completion_rate)

                # 聚合结果 - 遍历所有品牌
                # P3 修复：aggregate_results_by_brand 需要 brand_name 参数
                all_brands = list(set(r.get('brand', '') for r in deduplicated if r.get('brand')))
                aggregated = []
                for brand in all_brands:
                    brand_data = aggregate_results_by_brand(deduplicated, brand)
                    aggregated.append(brand_data)
                api_logger.info(f"[NxM] 聚合结果：{len(aggregated)} 个品牌")

                # P3 修复：保存测试汇总记录到 test_records 表
                # 这是历史记录功能的数据源
                try:
                    from wechat_backend.database_repositories import save_test_record
                    import json
                    import gzip

                    # 计算综合分数
                    overall_score = quality_score.get('overall_score', 0) if quality_score else 0

                    # 构建结果摘要
                    results_summary = {
                        'total_tasks': total_tasks,
                        'completed_tasks': len(deduplicated),
                        'success_rate': len(deduplicated) / total_tasks if total_tasks > 0 else 0,
                        'quality_score': overall_score,
                        'brands': list(set(r.get('brand', '') for r in deduplicated if r.get('brand'))),
                        'models': list(set(r.get('model', '') for r in deduplicated if r.get('model'))),
                    }

                    # 保存测试记录
                    save_test_record(
                        user_openid=user_id or 'anonymous',
                        brand_name=main_brand,
                        ai_models_used=','.join(m.get('name', '') for m in selected_models),
                        questions_used=';'.join(raw_questions),
                        overall_score=overall_score,
                        total_tasks=len(deduplicated),
                        results_summary=gzip.compress(json.dumps(results_summary, ensure_ascii=False).encode()).decode('latin-1'),
                        detailed_results=gzip.compress(json.dumps(deduplicated, ensure_ascii=False).encode()).decode('latin-1'),
                        execution_id=execution_id
                    )

                    api_logger.info(f"[NxM] ✅ 测试汇总记录保存成功：{execution_id}")

                except Exception as save_err:
                    api_logger.error(f"[NxM] ⚠️ 测试汇总记录保存失败：{execution_id}, 错误：{save_err}")

                # 返回成功结果
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'formula': f"{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求",
                    'total_tasks': total_tasks,
                    'completed_tasks': len(deduplicated),
                    'results': deduplicated,
                    'aggregated': aggregated,
                    'quality_score': quality_score
                }
            else:
                # 完全失败（无任何结果）
                api_logger.error(f"[NxM] 执行完全失败：{execution_id}, 无有效结果")
                scheduler.fail_execution("未获取任何有效结果")

                # 返回失败结果
                return {
                    'success': False,
                    'execution_id': execution_id,
                    'error': '所有 AI 调用均失败，未获取任何有效结果',
                    'formula': f"{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求",
                    'total_tasks': total_tasks,
                    'completed_tasks': 0,
                    'results': [],
                    'aggregated': [],
                    'quality_score': None
                }

        except Exception as e:
            # 执行器崩溃（极罕见情况）
            api_logger.error(f"[NxM] 执行器崩溃：{execution_id}, 错误：{e}\n{traceback.format_exc()}")
            scheduler.fail_execution(f"执行器崩溃：{str(e)}")

            # 返回错误结果
            return {
                'success': False,
                'execution_id': execution_id,
                'error': f'执行器崩溃：{str(e)}',
                'traceback': traceback.format_exc()
            }
        
        # P3 修复：确保 run_execution 总是返回结果
        # 如果上面的代码都没有返回（理论上不应该），返回一个空结果
        return {
            'success': False,
            'execution_id': execution_id,
            'error': '执行流程异常，未返回结果',
            'results': []
        }

    # 启动执行（同步方式，由上层调度器管理超时）
    # P3 修复：捕获 run_execution 的返回值，确保实际结果被返回
    execution_result = run_execution()

    # 返回执行结果（不是初始结果）
    return execution_result if execution_result else {
        'success': True,
        'execution_id': execution_id,
        'formula': f"{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求",
        'total_tasks': total_tasks
    }


def verify_nxm_execution(result: Dict[str, Any]) -> bool:
    """
    验证 NxM 执行结果

    参数：
        result: NxM 执行结果

    返回：
        是否验证通过
    """
    if not result:
        return False

    if not result.get('success'):
        api_logger.warning(f"[NxM] 验证失败：{result.get('error')}")
        return False

    results = result.get('results', [])
    if not results:
        api_logger.warning(f"[NxM] 验证警告：结果为空")

    return True


# 导出给其他模块使用
__all__ = ['execute_nxm_test', 'verify_nxm_execution']
