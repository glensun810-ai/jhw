"""
NxM 并发执行引擎

功能:
- 使用 ThreadPoolExecutor 并发执行所有诊断任务
- 支持动态超时配置
- 支持智能熔断
- 实时持久化结果

性能目标:
- 8 个任务并发执行
- 总耗时 ≤35 秒
- 成功率 ≥99%

作者：后端开发 李工
日期：2026-03-06
"""

import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE
from wechat_backend.logging_config import api_logger
from wechat_backend.nxm_result_aggregator import parse_geo_with_validation
from wechat_backend.ai_timeout import get_timeout_manager
from wechat_backend.smart_circuit_breaker import circuit_breaker
from wechat_backend.repositories import save_dimension_result, save_task_status, save_dimension_results_batch
from legacy_config import Config


# 并发配置
MAX_CONCURRENT_WORKERS = 8  # 最大并发数
EXECUTION_TIMEOUT = 35  # 总执行超时 (秒)


def execute_single_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行单个诊断任务
    
    参数:
        task: 任务字典 {brand, competitors, question, model, execution_id, q_idx}
    
    返回:
        任务结果字典
    """
    start_time = time.time()
    brand = task.get('brand', '')
    competitors = task.get('competitors', [])
    question = task.get('question', '')
    model_name = task.get('model', '')
    execution_id = task.get('execution_id', '')
    q_idx = task.get('q_idx', 0)
    
    try:
        # 1. 检查熔断器
        if not circuit_breaker.is_available(model_name, brand):
            api_logger.warning(f"[并发执行] {brand}-{model_name} 已熔断，跳过")
            return {
                "brand": brand,
                "question": question,
                "model": model_name,
                "status": "failed",
                "error": "模型已熔断",
                "elapsed": time.time() - start_time
            }
        
        # 2. 创建 AI 客户端
        client = AIAdapterFactory.create(model_name)
        api_key = Config.get_api_key(model_name)
        
        if not api_key:
            raise ValueError(f"模型 {model_name} API Key 未配置")
        
        # 3. 构建提示词
        prompt = GEO_PROMPT_TEMPLATE.format(
            brand_name=brand,
            competitors=', '.join(competitors) if competitors else '无',
            question=question
        )
        
        # 4. 获取超时配置 (动态)
        timeout_manager = get_timeout_manager()
        timeout = timeout_manager.get_timeout(model_name)
        
        # 5. 调用 AI (带超时)
        api_logger.debug(f"[并发执行] 开始调用 {brand}-{model_name}, 超时：{timeout}秒")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ai_result = loop.run_until_complete(
                asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: client.send_prompt(prompt=prompt)
                    ),
                    timeout=timeout
                )
            )
        finally:
            loop.close()
        
        elapsed = time.time() - start_time

        # 6. 处理结果
        # P0-STATUS-1 修复：AIResponse 使用 success 属性而非 status 属性
        if ai_result.success:
            # AI 调用成功，解析 GEO 数据
            geo_data, parse_error = parse_geo_with_validation(
                ai_result.content,
                execution_id,
                q_idx,
                model_name
            )
            
            circuit_breaker.record_success(model_name, brand)
            
            if parse_error or geo_data.get('_error'):
                # 解析失败
                api_logger.warning(f"[并发执行] {brand}-{model_name} 解析失败：{parse_error or geo_data.get('_error')}")
                return {
                    "brand": brand,
                    "question": question,
                    "model": model_name,
                    "status": "failed",
                    "error": parse_error or geo_data.get('_error', '解析失败'),
                    "data": None,
                    "elapsed": elapsed
                }
            else:
                # 解析成功
                api_logger.info(f"[并发执行] {brand}-{model_name} 成功，耗时：{elapsed:.2f}秒")
                return {
                    "brand": brand,
                    "question": question,
                    "model": model_name,
                    "status": "success",
                    "data": geo_data,
                    "elapsed": elapsed
                }
        else:
            # AI 调用失败
            circuit_breaker.record_failure(model_name, brand)
            api_logger.error(f"[并发执行] {brand}-{model_name} 失败：{ai_result.error_message}")
            return {
                "brand": brand,
                "question": question,
                "model": model_name,
                "status": "failed",
                "error": ai_result.error_message,
                "data": None,
                "elapsed": elapsed
            }
            
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        circuit_breaker.record_failure(model_name, brand)
        api_logger.error(f"[并发执行] {brand}-{model_name} 超时 ({timeout}秒)")
        return {
            "brand": brand,
            "question": question,
            "model": model_name,
            "status": "failed",
            "error": f"AI 调用超时 ({timeout}秒)",
            "data": None,
            "elapsed": elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        circuit_breaker.record_failure(model_name, brand)
        api_logger.error(f"[并发执行] {brand}-{model_name} 异常：{e}")
        return {
            "brand": brand,
            "question": question,
            "model": model_name,
            "status": "failed",
            "error": str(e),
            "data": None,
            "elapsed": elapsed
        }


def execute_nxm_test_concurrent(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str,
    user_level: str,
    execution_store: Dict[str, Any],
    max_workers: int = MAX_CONCURRENT_WORKERS,
    timeout: int = EXECUTION_TIMEOUT
) -> Dict[str, Any]:
    """
    并发执行 NxM 测试
    
    参数:
        execution_id: 执行 ID
        main_brand: 主品牌
        competitor_brands: 竞品品牌列表
        selected_models: 选择的 AI 模型列表
        raw_questions: 原始问题列表
        user_id: 用户 ID
        user_level: 用户等级
        execution_store: 执行状态存储
        max_workers: 最大并发数 (默认 8)
        timeout: 总超时时间 (默认 35 秒)
    
    返回:
        执行结果字典
    """
    start_time = time.time()
    results = []
    
    # 1. 创建任务列表
    tasks = []
    all_brands = [main_brand] + (competitor_brands or [])
    
    for brand in all_brands:
        for q_idx, question in enumerate(raw_questions):
            for model_info in selected_models:
                model_name = model_info.get('name', '')
                
                # 检查熔断器
                if not circuit_breaker.is_available(model_name, brand):
                    api_logger.warning(f"[并发执行] {brand}-{model_name} 已熔断，跳过任务创建")
                    continue
                
                task = {
                    "brand": brand,
                    "competitors": [b for b in all_brands if b != brand],
                    "question": question,
                    "model": model_name,
                    "execution_id": execution_id,
                    "q_idx": q_idx
                }
                tasks.append(task)
    
    total_tasks = len(tasks)
    api_logger.info(f"[并发执行] 创建 {total_tasks} 个任务，最大并发：{max_workers}")
    
    # 2. 初始化执行状态
    scheduler = type('obj', (object,), {
        'update_progress': lambda s, c, t, stage: save_task_status(
            task_id=execution_id,
            stage=stage,
            progress=int((c / t) * 100) if t > 0 else 0,
            status_text=f'已完成 {c}/{t}',
            completed_count=c,
            total_count=t
        ),
        'complete_execution': lambda s: save_task_status(
            task_id=execution_id,
            stage='completed',
            progress=100,
            status_text='执行完成',
            completed_count=total_tasks,
            total_count=total_tasks,
            is_completed=True
        ),
        'record_model_failure': lambda s, m: circuit_breaker.record_failure(m, 'global')
    })()
    
    scheduler.update_progress(0, total_tasks, 'ai_fetching')
    
    # 3. 并发执行
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {
            executor.submit(execute_single_task, task): task
            for task in tasks
        }
        
        # 收集结果 (带超时)
        completed = 0
        try:
            for future in as_completed(future_to_task, timeout=timeout):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    # 实时持久化维度结果
                    if result.get('status') == 'success' and result.get('data'):
                        geo_data = result['data']
                        rank = geo_data.get('rank', -1)
                        score = max(0, 100 - (rank - 1) * 10) if rank > 0 else None
                        
                        save_dimension_result(
                            execution_id=execution_id,
                            dimension_name=f"{result['brand']}-{result['model']}",
                            dimension_type='ai_analysis',
                            source=result['model'],
                            status='success',
                            score=score,
                            data=geo_data,
                            error_message=None
                        )
                    
                    # 更新进度
                    scheduler.update_progress(completed, total_tasks, 'ai_fetching')
                    
                except Exception as e:
                    api_logger.error(f"任务执行失败：{task}, 错误：{e}")
                    results.append({
                        "task": task,
                        "error": str(e),
                        "status": "failed"
                    })
                    completed += 1
                    
        except TimeoutError:
            api_logger.error(f"并发执行超时 ({timeout}秒)")
            scheduler.update_progress(completed, total_tasks, 'failed')
    
    # 4. 验证结果
    elapsed = time.time() - start_time
    success_count = len([r for r in results if r.get('status') == 'success'])
    
    api_logger.info(f"[并发执行] 完成：{success_count}/{total_tasks}, 耗时：{elapsed:.2f}秒")
    
    # 5. 返回结果
    if success_count > 0:
        scheduler.complete_execution()
        
        return {
            'success': True,
            'execution_id': execution_id,
            'formula': f"{len(raw_questions)} 问题 × {len(selected_models)} 模型 = {total_tasks} 次请求",
            'total_tasks': total_tasks,
            'completed_tasks': success_count,
            'results': results,
            'elapsed': elapsed
        }
    else:
        return {
            'success': False,
            'execution_id': execution_id,
            'error': f'所有任务失败 (耗时：{elapsed:.2f}秒)',
            'total_tasks': total_tasks,
            'completed_tasks': 0,
            'results': [],
            'elapsed': elapsed
        }


# 导出
__all__ = ['execute_nxm_test_concurrent', 'execute_single_task', 'MAX_CONCURRENT_WORKERS', 'EXECUTION_TIMEOUT']
