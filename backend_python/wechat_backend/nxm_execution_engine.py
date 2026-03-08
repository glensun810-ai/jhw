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
- P0-TRACE: 添加 TraceID 结构化日志追踪 (2026-03-07)
- P0-VALIDATE: 添加字段完整性验证 (2026-03-07)
"""

import time
import threading
import os
import asyncio
import json
import traceback
import pickle
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE, OBJECTIVE_QUESTION_TEMPLATE
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
# 【重构】单模型调用与优先级评估
from wechat_backend.multi_model_executor import get_single_model_executor, get_priority_evaluator

# 配置导入
from legacy_config import Config


# ==================== P0-001 修复：异步执行辅助函数 ====================

def run_async_in_thread(coro):
    """
    在线程中安全运行异步代码

    问题：asyncio.run() 在已有事件循环的线程中会抛出 RuntimeError
    解决：创建新的事件循环并在线程中运行

    参数:
        coro: 异步协程对象

    返回:
        协程执行结果
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ==================== P0-004 修复：预写日志（WAL）机制 ====================

WAL_DIR = '/tmp/nxm_wal'
os.makedirs(WAL_DIR, exist_ok=True)


def write_wal(execution_id: str, results: List[Dict], completed: int, total: int, brand: str = None, model: str = None):
    """
    预写日志 - 在内存持久化前写入磁盘
    
    问题：实时持久化是"最佳努力"模式，失败时只记录日志
    解决：每次 AI 调用成功后立即写入 WAL，服务重启后可恢复
    
    参数:
        execution_id: 执行 ID
        results: 结果列表
        completed: 已完成任务数
        total: 总任务数
        brand: 当前品牌（可选）
        model: 当前模型（可选）
    """
    try:
        wal_path = os.path.join(WAL_DIR, f'nxm_wal_{execution_id}.pkl')
        wal_data = {
            'execution_id': execution_id,
            'results': results,
            'completed': completed,
            'total': total,
            'brand': brand,
            'model': model,
            'timestamp': time.time(),
            'last_updated': datetime.now().isoformat()
        }
        with open(wal_path, 'wb') as f:
            pickle.dump(wal_data, f)
        api_logger.info(f"[WAL] ✅ 已写入：{wal_path} (完成：{completed}/{total})")
    except Exception as e:
        api_logger.error(f"[WAL] ⚠️ 写入失败：{e}")


def read_wal(execution_id: str) -> Optional[Dict]:
    """
    读取预写日志
    
    参数:
        execution_id: 执行 ID
    
    返回:
        WAL 数据，如果不存在则返回 None
    """
    try:
        wal_path = os.path.join(WAL_DIR, f'nxm_wal_{execution_id}.pkl')
        if os.path.exists(wal_path):
            with open(wal_path, 'rb') as f:
                data = pickle.load(f)
            api_logger.info(f"[WAL] ✅ 已读取：{wal_path}")
            return data
    except Exception as e:
        api_logger.error(f"[WAL] ⚠️ 读取失败：{e}")
    return None


def cleanup_expired_wal(max_age_hours: int = 24):
    """
    清理过期 WAL 文件
    
    参数:
        max_age_hours: 最大保留小时数
    """
    try:
        import glob
        now = time.time()
        wal_files = glob.glob(os.path.join(WAL_DIR, 'nxm_wal_*.pkl'))
        cleaned_count = 0
        for wal_file in wal_files:
            try:
                mtime = os.path.getmtime(wal_file)
                if (now - mtime) > (max_age_hours * 3600):
                    os.remove(wal_file)
                    cleaned_count += 1
                    api_logger.info(f"[WAL] 🗑️ 清理过期文件：{wal_file}")
            except Exception:
                pass
        if cleaned_count > 0:
            api_logger.info(f"[WAL] 清理完成，共清理 {cleaned_count} 个文件")
    except Exception as e:
        api_logger.error(f"[WAL] 清理失败：{e}")


def recover_from_wal(execution_id: str) -> Optional[Dict]:
    """
    从 WAL 恢复未完成的执行
    
    参数:
        execution_id: 执行 ID
    
    返回:
        恢复的数据，如果不存在或已完成则返回 None
    """
    wal_data = read_wal(execution_id)
    if wal_data:
        # 检查是否过期（超过 24 小时）
        wal_age_hours = (time.time() - wal_data.get('timestamp', 0)) / 3600
        if wal_age_hours > 24:
            api_logger.warning(f"[WAL] ⚠️ WAL 文件已过 {wal_age_hours:.1f} 小时，忽略")
            return None
        
        # 检查是否已完成
        if wal_data.get('completed', 0) >= wal_data.get('total', 0):
            api_logger.info(f"[WAL] ✅ 执行已完成，无需恢复")
            return None
        
        api_logger.info(f"[WAL] 🔄 恢复执行：{execution_id}, 进度：{wal_data.get('completed')}/{wal_data.get('total')}")
        return wal_data
    return None


# ==================== 单模型调用辅助函数（移除多模型冗余） ====================

async def _execute_single_model(
    prompt: str,
    model_name: str,
    timeout: int,
    execution_id: str = None,
    q_idx: int = None
):
    """
    执行单模型调用（用户选择哪个模型就用哪个）

    策略：
    1. 只调用用户指定的模型
    2. 失败时直接返回错误，不自动尝试其他模型
    3. 由上层决定如何处理失败

    参数：
        prompt: 提示词
        model_name: 模型名称（用户选择的模型）
        timeout: 超时时间（秒）
        execution_id: 执行 ID
        q_idx: 问题索引

    返回：
        (AIResponse, model_name): AI 响应和实际使用的模型名称
    """
    from wechat_backend.multi_model_executor import get_single_model_executor

    # 获取单模型执行器
    executor = get_single_model_executor(timeout=timeout)

    # 执行单模型调用
    result, actual_model = await executor.execute(
        prompt=prompt,
        model_name=model_name,
        execution_id=execution_id,
        q_idx=q_idx
    )

    return result, actual_model


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
    - P0-TRACE: 添加 TraceID 结构化日志追踪
    - P0-VALIDATE: 添加字段完整性验证
    """
    
    # 【P0-TRACE】生成 TraceID（贯穿整个请求链路）
    trace_id = str(uuid.uuid4())[:8]
    
    # 【P0-TRACE】结构化日志上下文
    log_context = {
        'trace_id': trace_id,
        'execution_id': execution_id,
        'main_brand': main_brand,
        'question_count': len(raw_questions),
        'model_count': len(selected_models)
    }

    # 创建调度器
    scheduler = create_scheduler(execution_id, execution_store)

    # P0 修复：客观提问模式下，请求次数 = 问题数 × AI 平台数（不包含品牌遍历）
    total_tasks = len(raw_questions) * len(selected_models)
    scheduler.initialize_execution(total_tasks)

    # BUG-008 修复：统一超时配置
    def on_timeout():
        scheduler.fail_execution(f"执行超时 ({timeout_seconds}秒)")

    scheduler.start_timeout_timer(timeout_seconds, on_timeout)

    # 【P0-TRACE】记录执行开始日志（结构化）
    api_logger.info(
        f"[NxM] 🚀 执行开始",
        extra={
            **log_context,
            'event': 'nxm_execution_start',
            'total_tasks': total_tasks,
            'timeout_seconds': timeout_seconds
        }
    )

    # 在后台线程中执行
    def run_execution():
        # 【修复 P0-4】在 try 块外先导入 execution_store，避免作用域问题
        try:
            from wechat_backend.views.diagnosis_views import execution_store
        except ImportError:
            execution_store = {}
            api_logger.error(
                f"[NxM] 无法导入 execution_store，使用空字典",
                extra={**log_context, 'event': 'execution_store_import_failed'}
            )

        try:
            results = []
            completed = 0

            # P0 修复：只遍历问题和模型，不遍历品牌（获取客观回答）
            api_logger.info(
                f"[NxM] 📋 任务初始化完成",
                extra={
                    **log_context,
                    'event': 'nxm_task_initialized',
                    'total_tasks': total_tasks
                }
            )

            # 【P0 颠覆性修复】立即更新 stage 为 ai_fetching，避免前端一直看到 init
            try:
                scheduler.update_progress(0, total_tasks, 'ai_fetching')
                api_logger.info(
                    f"[NxM] ✅ 状态已更新为 ai_fetching",
                    extra={**log_context, 'event': 'stage_updated', 'stage': 'ai_fetching'}
                )

                # 【P0 增强】同时写入数据库，确保状态立即持久化
                from wechat_backend.repositories.task_status_repository import save_task_status
                save_task_status(
                    task_id=execution_id,
                    stage='ai_fetching',
                    progress=0,
                    status_text='正在初始化 AI 连接',
                    completed_count=0,
                    total_count=total_tasks,
                    is_completed=False
                )
                api_logger.info(
                    f"[NxM] ✅ 数据库状态已同步",
                    extra={**log_context, 'event': 'database_state_synced', 'stage': 'ai_fetching'}
                )
            except Exception as e:
                api_logger.warning(
                    f"[NxM] ⚠️ 初始状态更新失败：{e}",
                    extra={**log_context, 'event': 'initial_state_update_failed', 'error': str(e)}
                )

            # 外层循环：遍历问题
            for q_idx, question in enumerate(raw_questions):
                # 【P0-TRACE】结构化日志
                question_context = {
                    **log_context,
                    'question_index': q_idx + 1,
                    'question_preview': question[:50] + '...' if len(question) > 50 else question
                }
                
                api_logger.info(
                    f"[NxM] ❓ 开始处理问题 {q_idx + 1}/{len(raw_questions)}",
                    extra={
                        **question_context,
                        'event': 'question_start'
                    }
                )

                # 内层循环：遍历模型
                for model_info in selected_models:
                    model_name = model_info.get('name', '')

                    # 【P0-TRACE】结构化日志
                    task_context = {
                        **question_context,
                        'model_name': model_name,
                        'task_id': f"Q{q_idx + 1}×{model_name}"
                    }
                    
                    api_logger.debug(
                        f"[NxM] 🔧 开始任务 Q{q_idx + 1}×{model_name}",
                        extra={
                            **task_context,
                            'event': 'task_start'
                        }
                    )

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

                        # P0 修复：构建客观问题提示词（不带品牌倾向）
                        prompt = OBJECTIVE_QUESTION_TEMPLATE.format(
                            question=question
                        )

                        # P1-014 新增：获取超时配置
                        timeout_manager = get_timeout_manager()
                        timeout = timeout_manager.get_timeout(model_name)

                        # M002 改造：使用 FaultTolerantExecutor 统一包裹 AI 调用
                        # 创建容错执行器实例（每个调用独立）
                        ai_executor = FaultTolerantExecutor(timeout_seconds=timeout)

                        # 【P1-2 新增】多模型冗余调用机制
                        # 策略：
                        # 1. 首先尝试主模型
                        # 2. 主模型失败时，自动尝试备用模型
                        # 3. 返回第一个成功的有效结果
                        
                        # P0-001 修复：使用线程安全的异步执行方式
                        # 原代码问题：asyncio.run() 在已有事件循环的线程中会抛出 RuntimeError
                        # 修复方案：使用 run_async_in_thread() 创建新的事件循环

                        # 【重构】使用单模型调用（用户选择哪个模型就用哪个）
                        api_logger.info(f"[NxM] 使用用户选择的模型：{model_name}, Q{q_idx}")

                        ai_result, actual_model = run_async_in_thread(
                            _execute_single_model(
                                prompt=prompt,
                                model_name=model_name,
                                timeout=timeout,
                                execution_id=execution_id,
                                q_idx=q_idx
                            )
                        )

                        # 用户选择的模型应该与实际使用的模型一致
                        if actual_model != model_name:
                            api_logger.warning(
                                f"[NxM] 实际使用模型与选择不同：选择={model_name}, 实际={actual_model}, Q{q_idx}"
                            )
                            model_name = actual_model  # 更新模型名为实际使用的模型
                        
                        # 检查 AI 调用结果
                        geo_data = None
                        parse_error = None

                        # P0-STATUS-1 修复：AIResponse 使用 success 属性而非 status 属性
                        if ai_result.success:
                            # AI 调用成功，解析 GEO 数据
                            scheduler.record_model_success(model_name)

                            # 解析 GEO 数据（修复：使用 content 而非 data）
                            geo_data, parse_error = parse_geo_with_validation(
                                ai_result.content,
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
                                # 【P0 关键修复】response 改为字典格式，兼容存储层要求
                                # 【P0 关键修复 - 2026-03-07】添加 brand 和 tokens_used 字段
                                result = {
                                    'brand': main_brand,  # 【P0 修复】添加品牌字段
                                    'question': question,
                                    'model': model_name,
                                    'response': {  # 字典格式：{content, latency, metadata}
                                        'content': str(ai_result.content) if hasattr(ai_result, 'content') else str(ai_result),
                                        'latency': None,
                                        'metadata': {}
                                    },
                                    'geo_data': geo_data,
                                    'error': str(parse_error or geo_data.get('_error', '解析失败')),
                                    'error_type': str(ai_result.error_type.value) if hasattr(ai_result, 'error_type') and ai_result.error_type else 'parse_error',
                                    'is_objective': True,  # 标记为客观回答
                                    'tokens_used': ai_result.tokens_used if hasattr(ai_result, 'tokens_used') and ai_result.tokens_used > 0 else 0,  # 【P1 修复】添加 tokens_used
                                    'prompt_tokens': (ai_result.metadata or {}).get('prompt_tokens', 0) if hasattr(ai_result, 'metadata') else 0,  # 【P1 修复】
                                    'completion_tokens': (ai_result.metadata or {}).get('completion_tokens', 0) if hasattr(ai_result, 'metadata') else 0,  # 【P1 修复】
                                    'cached_tokens': (ai_result.metadata or {}).get('cached_tokens', 0) if hasattr(ai_result, 'metadata') else 0  # 【P1 修复】
                                }
                                results.append(result)
                            else:
                                # 解析成功，收集结果
                                # P3 修复：确保所有字段都是可序列化的
                                # 【P0 关键修复】response 改为字典格式，兼容存储层要求
                                # 【P0 关键修复 - 2026-03-07】添加 brand 和 tokens_used 字段
                                result = {
                                    'brand': main_brand,  # 【P0 修复】添加品牌字段
                                    'question': question,
                                    'model': model_name,
                                    'response': {  # 字典格式：{content, latency, metadata}
                                        'content': str(ai_result.content) if hasattr(ai_result, 'content') else str(ai_result),
                                        'latency': None,
                                        'metadata': {}
                                    },
                                    'geo_data': geo_data,
                                    'error': None,
                                    'error_type': None,
                                    'is_objective': True,  # 标记为客观回答
                                    'tokens_used': ai_result.tokens_used if hasattr(ai_result, 'tokens_used') and ai_result.tokens_used > 0 else 0,  # 【P1 修复】添加 tokens_used
                                    'prompt_tokens': (ai_result.metadata or {}).get('prompt_tokens', 0) if hasattr(ai_result, 'metadata') else 0,  # 【P1 修复】
                                    'completion_tokens': (ai_result.metadata or {}).get('completion_tokens', 0) if hasattr(ai_result, 'metadata') else 0,  # 【P1 修复】
                                    'cached_tokens': (ai_result.metadata or {}).get('cached_tokens', 0) if hasattr(ai_result, 'metadata') else 0  # 【P1 修复】
                                }
                                results.append(result)
                        else:
                            # AI 调用失败，记录错误并继续（不中断流程）
                            scheduler.record_model_failure(model_name)
                            api_logger.error(f"[NxM] AI 调用失败：{model_name}, Q{q_idx}: {ai_result.error_message}")

                            # P0-4 修复：收集失败结果（保证报告完整）
                            # P3 修复：确保所有字段都是可序列化的
                            # 【P0 关键修复】response 改为字典格式，兼容存储层要求
                            # 【P0 关键修复 - 2026-03-07】添加 brand 和 tokens_used 字段
                            result = {
                                'brand': main_brand,  # 【P0 修复】添加品牌字段
                                'question': question,
                                'model': model_name,
                                'response': {  # 字典格式：{content, latency, metadata}
                                    'content': None,
                                    'latency': None,
                                    'metadata': {}
                                },
                                'geo_data': None,
                                'error': str(ai_result.error_message),
                                'error_type': str(ai_result.error_type.value) if hasattr(ai_result, 'error_type') and ai_result.error_type else 'unknown',
                                'is_objective': True,  # 标记为客观回答
                                'tokens_used': 0,  # 【P1 修复】失败时无 token 消耗
                                'prompt_tokens': 0,
                                'completion_tokens': 0,
                                'cached_tokens': 0
                            }
                            results.append(result)

                        # 【P0-VALIDATE】字段完整性验证（关键！）
                        try:
                            from wechat_backend.validators import ResultValidator
                            validator = ResultValidator(strict_mode=False)  # 非严格模式，仅记录日志
                            is_valid, errors, warnings = validator.validate(result, execution_id)
                            
                            # 记录验证结果（结构化日志）
                            validation_context = {
                                **task_context,
                                'event': 'result_validated',
                                'is_valid': is_valid,
                                'error_count': len(errors),
                                'warning_count': len(warnings),
                                'brand': result.get('brand', 'MISSING'),
                                'tokens_used': result.get('tokens_used', 'MISSING')
                            }
                            
                            if not is_valid:
                                api_logger.error(
                                    f"[NxM] ❌ 结果验证失败：{errors[0] if errors else '未知错误'}",
                                    extra={**validation_context, 'errors': errors}
                                )
                            elif warnings:
                                api_logger.warning(
                                    f"[NxM] ⚠️ 结果验证通过但有警告：{warnings[0]}",
                                    extra={**validation_context, 'warnings': warnings}
                                )
                            else:
                                api_logger.debug(
                                    f"[NxM] ✅ 结果验证通过",
                                    extra={
                                        **validation_context,
                                        'message': f"brand={result.get('brand')}, tokens_used={result.get('tokens_used')}"
                                    }
                                )
                        except Exception as validate_err:
                            api_logger.error(
                                f"[NxM] ❌ 字段验证异常：{validate_err}",
                                extra={**task_context, 'event': 'result_validation_failed'}
                            )

                        # M003 改造：实时持久化维度结果
                        # 原有问题：结果仅在内存中，服务重启后丢失
                        # 改造后：每个维度结果立即保存到数据库，支持进度查询和历史追溯
                        try:
                            from wechat_backend.repositories import save_dimension_result, save_task_status

                            # P0-STATUS-1 修复：AIResponse 使用 success 属性而非 status 属性
                            dim_status = "success" if (ai_result.success and geo_data and not geo_data.get('_error')) else "failed"
                            dim_score = None
                            if dim_status == "success" and geo_data:
                                # 从 GEO 数据中提取排名作为分数参考
                                rank = geo_data.get("rank", -1)
                                if rank > 0:
                                    dim_score = max(0, 100 - (rank - 1) * 10)  # 排名第 1 得 100 分，每降 1 名减 10 分

                            # 保存维度结果
                            # 此处brand参数应调整，因为改为客观提问，品牌不在请求中指定。
                            # 可能需要调整数据库结构或在聚合阶段处理。
                            # 这里暂时保留brand变量，但P0修复计划中提示词已移除brand引用。
                            # 需要上层代码确保brand变量的正确上下文或在此处使用占位。
                            save_dimension_result(
                                execution_id=execution_id,
                                dimension_name=f"{main_brand}-{model_name}", # P0修复：使用main_brand作为维度维度标识
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

                            api_logger.info(f"[NxM] ✅ 维度结果持久化成功：{main_brand}-{model_name}, 状态：{dim_status}")

                        except Exception as persist_err:
                            # 持久化失败不影响主流程，仅记录错误
                            api_logger.error(f"[NxM] ⚠️ 维度结果持久化失败：{main_brand}-{model_name}, 错误：{persist_err}")
                            
                            # P1-018 新增：数据库持久化告警机制
                            try:
                                from wechat_backend.alert_system import record_persistence_error, check_persistence_alert
                                
                                # 记录持久化错误
                                alert_triggered = record_persistence_error(
                                    execution_id=execution_id,
                                    error_type='dimension_result',
                                    error_message=str(persist_err)
                                )
                                
                                # 如果触发告警，记录详细日志
                                if alert_triggered:
                                    api_logger.error(
                                        f"[P1-018 告警] 数据库持久化失败达到阈值！"
                                        f"execution_id={execution_id}, 错误：{persist_err}"
                                    )
                                    # 可以添加额外的告警通知逻辑（如发送邮件、短信等）
                            except Exception as alert_err:
                                api_logger.error(f"[P1-018] 告警记录失败：{alert_err}")

                        # 【P0-004 修复】写入 WAL（预写日志），确保服务重启后数据不丢失
                        # WAL 写入在数据库持久化之后，作为双重保障
                        try:
                            # WAL写入需传入brand信息以作保障，这里brand信息需要明确上下文。
                            # 这里暂时使用main_brand。
                            write_wal(execution_id, results, completed, total_tasks, main_brand, model_name)
                        except Exception as wal_err:
                            api_logger.error(f"[WAL] ⚠️ 写入失败：{wal_err}")

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

                # 【P0 修复】后置品牌提及分析（客观提问模式的核心）
                # 从 AI 客观回答中提取用户品牌提及情况和竞品对比
                aggregated = []
                brand_analysis = None
                try:
                    from wechat_backend.services.brand_analysis_service import get_brand_analysis_service

                    # 提取用户选择的模型名称列表
                    user_model_names = [m.get('name', '') for m in selected_models if m.get('name')]
                    
                    # 获取品牌分析服务（动态选择裁判模型，优先使用用户选择的模型）
                    analysis_service = get_brand_analysis_service(
                        judge_model=None,  # 不指定，让服务自动选择
                        user_selected_models=user_model_names  # 传入用户选择的模型列表
                    )

                    # 执行品牌提及分析
                    brand_analysis = analysis_service.analyze_brand_mentions(
                        results=deduplicated,
                        user_brand=main_brand,
                        competitor_brands=competitor_brands  # 可为 None，自动从回答中提取
                    )
                    
                    # 构建聚合结果（基于品牌分析）
                    if brand_analysis:
                        aggregated = [{
                            'brand': main_brand,
                            'is_user_brand': True,
                            'mention_rate': brand_analysis['user_brand_analysis']['mention_rate'],
                            'average_rank': brand_analysis['user_brand_analysis']['average_rank'],
                            'average_sentiment': brand_analysis['user_brand_analysis']['average_sentiment'],
                            'is_top3': brand_analysis['user_brand_analysis']['is_top3'],
                            'mentioned_count': brand_analysis['user_brand_analysis']['mentioned_count'],
                            'total_responses': brand_analysis['user_brand_analysis']['total_responses'],
                            'comparison': brand_analysis['comparison']
                        }]
                        
                        # 添加竞品分析
                        for comp in brand_analysis.get('competitor_analysis', []):
                            aggregated.append({
                                'brand': comp['brand'],
                                'is_user_brand': False,
                                'mention_rate': comp['mention_rate'],
                                'average_rank': comp['average_rank'],
                                'average_sentiment': comp['average_sentiment'],
                                'is_top3': comp['is_top3'],
                                'mentioned_count': comp['mentioned_count'],
                                'total_responses': len(comp['mentions']),
                                'comparison': None
                            })
                        
                        api_logger.info(
                            f"[P0 修复] ✅ 品牌分析完成：{main_brand}, "
                            f"提及率={brand_analysis['user_brand_analysis']['mention_rate']:.1%}, "
                            f"竞品数={len(brand_analysis['competitor_analysis'])}"
                        )
                    
                except Exception as analysis_err:
                    api_logger.error(f"[P0 修复] ⚠️ 品牌分析失败：{analysis_err}")
                    # 降级：返回空聚合结果
                    aggregated = []

                # 【P0-TRACE】记录执行完成汇总日志（结构化）
                api_logger.info(
                    f"[NxM] 🎉 执行完成",
                    extra={
                        **log_context,
                        'event': 'nxm_execution_completed',
                        'total_tasks': total_tasks,
                        'completed_tasks': len(deduplicated),
                        'success_rate': f"{len(deduplicated) / total_tasks:.2%}" if total_tasks > 0 else 'N/A',
                        'quality_score': quality_score.get('overall_score', 0) if quality_score else 0,
                        'has_brand_analysis': brand_analysis is not None,
                        'trace_id': trace_id
                    }
                )

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
                        # 品牌信息需要后置分析，此处brands置空。
                        # 品牌信息（来自后置分析）
                        'brands': [main_brand] + [c['brand'] for c in brand_analysis.get('competitor_analysis', [])] if brand_analysis else [],
                        'models': list(set(r.get('model', '') for r in deduplicated if r.get('model'))),
                        'user_brand_analysis': brand_analysis.get('user_brand_analysis') if brand_analysis else None,
                        'comparison': brand_analysis.get('comparison') if brand_analysis else None,
                        'models': list(set(r.get('model', '') for r in deduplicated if r.get('model'))),
                    }

                    # 保存测试记录
                    save_test_record(
                        user_openid=user_id or 'anonymous',
                        brand_name=main_brand,
                        ai_models_used=','.join(m.get('name', '') for m in selected_models),
                        questions_used=';'.join(raw_questions),
                        overall_score=overall_score,
                        total_tests=len(deduplicated),  # 修复：使用 total_tests 而非 total_tasks
                        results_summary=gzip.compress(json.dumps(results_summary, ensure_ascii=False).encode()).decode('latin-1'),
                        detailed_results=gzip.compress(json.dumps(deduplicated, ensure_ascii=False).encode()).decode('latin-1')
                    )

                    api_logger.info(f"[NxM] ✅ 测试汇总记录保存成功：{execution_id}")

                except Exception as save_err:
                    api_logger.error(f"[NxM] ⚠️ 测试汇总记录保存失败：{execution_id}, 错误：{save_err}")

                # P2-020 新增：记录监控指标
                # quota_exhausted_models, partial_warning 需要处理
                try:
                    from wechat_backend.services.diagnosis_monitor_service import record_diagnosis_metric
                    import time
                    
                    # 计算执行时长（从 scheduler 获取或估算）
                    execution_duration = scheduler.get_execution_duration() if hasattr(scheduler, 'get_execution_duration') else 0
                    
                    # 记录诊断指标
                    record_diagnosis_metric(
                        execution_id=execution_id,
                        user_id=user_id or 'anonymous',
                        total_tasks=total_tasks,
                        completed_tasks=len(deduplicated),
                        success=True,
                        duration_seconds=execution_duration,
                         quota_exhausted_models=[],
                         error_type=None,
                         error_message=None
                    )
                    
                    api_logger.info(f"[P2-020 监控] 诊断指标已记录：{execution_id}")
                except Exception as monitor_err:
                    api_logger.error(f"[P2-020 监控] 记录失败：{monitor_err}")

                # 后置分析需配合方案三实现。此处返回暂无 aggregated 的数据结构。
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'formula': f"{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求",
                    'total_tasks': total_tasks,
                    'completed_tasks': len(deduplicated),
                    'completion_rate': completion_rate,
                    'results': deduplicated,
                    'aggregated': aggregated,
                    'brand_analysis': brand_analysis,
                    'quality_score': quality_score,
                    # P0-007, P1-016 相关字段置空
                    'quota_exhausted_models': [],
                    'partial_warning': None,
                    'has_partial_results': len(deduplicated) < total_tasks,
                    'quota_warnings': [],
                    'quota_recovery_suggestions': []
                }
            else:
                # 完全失败（无任何结果）
                api_logger.error(f"[NxM] 执行完全失败：{execution_id}, 无有效结果")
                scheduler.fail_execution("未获取任何有效结果")

                # 【P0 修复 - 2026-03-07】即使失败也返回执行元数据，让用户看到发生了什么
                # 获取执行日志（如果调度器支持）
                execution_log = []
                if hasattr(scheduler, 'get_execution_log'):
                    execution_log = scheduler.get_execution_log()
                elif hasattr(scheduler, 'task_results'):
                    # 从任务结果构建日志
                    for task_id, task_result in getattr(scheduler, 'task_results', {}).items():
                        execution_log.append({
                            'task_id': task_id,
                            'status': 'failed',
                            'error': task_result.get('error', '未知错误') if isinstance(task_result, dict) else str(task_result),
                            'timestamp': datetime.now().isoformat()
                        })

                # 返回失败结果（但包含元数据）
                return {
                    'success': False,
                    'execution_id': execution_id,
                    'status': 'failed',  # 明确状态
                    'error': '所有 AI 调用均失败，未获取任何有效结果',
                    'error_details': {  # 新增：详细错误信息
                        'type': 'all_ai_calls_failed',
                        'message': '所有 AI 调用均失败，未获取任何有效结果',
                        'suggestion': '请检查 AI 平台配置（API Key、模型名称）或网络设置，然后重新运行诊断',
                        'possible_causes': [
                            'AI 平台 API Key 无效或已过期',
                            'AI 平台服务不可用',
                            '网络连接异常',
                            '所有模型的配额均已用尽'
                        ]
                    },
                    'formula': f"{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求",
                    'total_tasks': total_tasks,
                    'completed_tasks': 0,
                    'completion_rate': 0,
                    'results': [],
                    'aggregated': [],
                    'quality_score': None,
                    # 【P0 修复】返回执行元数据，让用户看到配置和日志
                    'execution_metadata': {
                        'selected_models': selected_models,  # 使用的 AI 模型
                        'custom_questions': raw_questions,   # 诊断问题
                        'main_brand': main_brand,            # 主品牌
                        'competitor_brands': competitor_brands if 'competitor_brands' in locals() else [],
                        'execution_log': execution_log,      # 执行日志
                        'failure_reason': 'all_ai_calls_failed',
                        'timestamp': datetime.now().isoformat()
                    },
                    # 兼容性字段
                    'selected_models': selected_models,
                    'custom_questions': raw_questions,
                    'brand_name': main_brand
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
        api_logger.warning(f"[NxM] 执行流程异常 - execution_id={execution_id}, 未返回结果")
        return {
            'success': False,
            'execution_id': execution_id,
            'error': '执行流程异常，未返回结果',
            'results': []
        }

    # 启动执行（同步方式，由上层调度器管理超时）
    # P3 修复：捕获 run_execution 的返回值，确保实际结果被返回
    # 【P0 修复 - 2026-03-02】添加执行日志
    api_logger.info(f"[NxM] 开始执行 run_execution - execution_id={execution_id}")
    try:
        execution_result = run_execution()
        api_logger.info(f"[NxM] 执行完成 - execution_id={execution_id}, success={execution_result.get('success', False)}")
    except Exception as e:
        # 【P0 修复】捕获 run_execution 的异常
        api_logger.error(f"[NxM] 执行异常 - execution_id={execution_id}, error={e}")
        import traceback
        execution_result = {
            'success': False,
            'execution_id': execution_id,
            'error': f'执行异常：{str(e)}',
            'traceback': traceback.format_exc()
        }

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


