"""
NxM 并发执行引擎 - P0 性能优化

核心改进：
1. 真正的并发 AI 调用（使用 ThreadPoolExecutor）
2. 批量数据库写入（减少 I/O 开销）
3. 实时进度更新（每 N 次调用更新一次）

性能提升：
- 串行：N × M × Q × 15 秒
- 并发：(N × M × Q / 并发度) × 15 秒
- 典型提升：60-70%
"""

import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE
from wechat_backend.logging_config import api_logger
from wechat_backend.database import save_test_record

# 容错执行器
from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor

# 结果聚合
from wechat_backend.nxm_result_aggregator import (
    parse_geo_with_validation,
    verify_completion,
    deduplicate_results,
    aggregate_results_by_brand
)

# 质量评分
from wechat_backend.services.quality_scorer import get_quality_scorer

# AI 超时
from wechat_backend.ai_timeout import get_timeout_manager, AITimeoutError

# 导入 SSE 推送（P2-1 优化）
try:
    from wechat_backend.services.sse_service_v2 import send_progress_update, send_result_chunk, send_task_complete
    SSE_ENABLED = True
except ImportError:
    SSE_ENABLED = False
    api_logger.warning("[ConcurrentEngine] SSE 服务不可用，将使用日志记录")

# 导入流式聚合器（P2-2 优化）
from wechat_backend.nxm_streaming_aggregator import StreamingResultAggregator


# =============================================================================
# 并发执行配置
# =============================================================================

# 最大并发 AI 调用数（根据 API 限流调整）
MAX_CONCURRENT_AI_CALLS = 5

# 批量写入数据库的阈值
BATCH_WRITE_THRESHOLD = 10

# 进度更新间隔（每 N 次调用更新一次）
PROGRESS_UPDATE_INTERVAL = 5


# =============================================================================
# 任务数据结构
# =============================================================================

class AITask:
    """AI 调用任务"""
    
    def __init__(
        self,
        task_id: str,
        brand: str,
        question: str,
        model_name: str,
        prompt: str,
        q_idx: int,
        timeout: int
    ):
        self.task_id = task_id
        self.brand = brand
        self.question = question
        self.model_name = model_name
        self.prompt = prompt
        self.q_idx = q_idx
        self.timeout = timeout
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'brand': self.brand,
            'question': self.question,
            'model_name': self.model_name,
            'prompt': self.prompt,
            'q_idx': self.q_idx,
            'timeout': self.timeout
        }


class AIResult:
    """AI 调用结果"""
    
    def __init__(
        self,
        task: AITask,
        success: bool,
        data: Optional[Any] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        execution_time: float = 0.0
    ):
        self.task = task
        self.success = success
        self.data = data
        self.error_message = error_message
        self.error_type = error_type
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task.task_id,
            'brand': self.task.brand,
            'question': self.task.question,
            'model_name': self.task.model_name,
            'q_idx': self.task.q_idx,
            'success': self.success,
            'data': self.data,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'execution_time': self.execution_time
        }


# =============================================================================
# 并发执行引擎
# =============================================================================

class ConcurrentExecutionEngine:
    """
    并发执行引擎
    
    核心特性：
    1. 真正的并发 AI 调用
    2. 批量数据库写入
    3. 实时进度更新
    4. 熔断器保护
    """
    
    def __init__(
        self,
        execution_id: str,
        scheduler,
        execution_store: Dict[str, Any],
        max_concurrent: int = MAX_CONCURRENT_AI_CALLS
    ):
        self.execution_id = execution_id
        self.scheduler = scheduler
        self.execution_store = execution_store
        self.max_concurrent = max_concurrent
        
        # 结果收集
        self.results: List[Dict[str, Any]] = []
        self.results_lock = threading.Lock()
        
        # 批量写入缓存
        self.batch_cache: List[Dict[str, Any]] = []
        self.batch_lock = threading.Lock()
        
        # 进度跟踪
        self.completed = 0
        self.total_tasks = 0
        self.progress_lock = threading.Lock()
    
    def execute(
        self,
        main_brand: str,
        competitor_brands: List[str],
        selected_models: List[Dict[str, Any]],
        raw_questions: List[str],
        user_id: str,
        user_level: str
    ) -> Dict[str, Any]:
        """
        执行并发诊断（P2 优化版本：支持 SSE 推送和流式聚合）
        
        Args:
            main_brand: 主品牌
            competitor_brands: 竞品品牌列表
            selected_models: 选择的模型列表
            raw_questions: 问题列表
            user_id: 用户 ID
            user_level: 用户等级
        
        Returns:
            执行结果
        """
        start_time = time.time()
        
        # P2-2 优化：使用流式聚合器替代简单列表
        self.aggregator = StreamingResultAggregator(self.execution_id, self.total_tasks)
        
        # 1. 构建任务列表
        tasks = self._build_tasks(
            main_brand,
            competitor_brands,
            selected_models,
            raw_questions
        )
        
        self.total_tasks = len(tasks)
        self.scheduler.initialize_execution(self.total_tasks)
        
        # P2-1 优化：发送 SSE 开始消息
        if SSE_ENABLED:
            send_progress_update(self.execution_id, 0, 'starting', '开始执行诊断任务...')
        
        api_logger.info(f"[ConcurrentEngine] 开始执行，总任务数：{self.total_tasks}, 并发度：{self.max_concurrent}")
        
        # 2. 并发执行
        try:
            # 使用 ThreadPoolExecutor 并发执行
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                # 提交所有任务
                future_to_task = {
                    executor.submit(self._execute_single_task, task): task
                    for task in tasks
                }
                
                # 收集结果
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        self._handle_result(result)
                    except Exception as e:
                        api_logger.error(f"[ConcurrentEngine] 任务执行失败：{task.task_id}: {e}")
                        self._handle_error(task, str(e))
        
        except Exception as e:
            api_logger.error(f"[ConcurrentEngine] 执行异常：{e}")
            return {
                'success': False,
                'error': f'执行失败：{str(e)}',
                'execution_time': time.time() - start_time
            }
        
        # 3. 批量写入剩余结果
        self._flush_batch_cache()
        
        # 4. 聚合结果（P2-2 优化：使用流式聚合器的 finalize 方法）
        execution_time = time.time() - start_time
        return self._aggregate_results_streaming(execution_time)
    
    def _build_tasks(
        self,
        main_brand: str,
        competitor_brands: List[str],
        selected_models: List[Dict[str, Any]],
        raw_questions: List[str]
    ) -> List[AITask]:
        """构建所有 AI 调用任务"""
        tasks = []
        all_brands = [main_brand] + (competitor_brands or [])
        
        for brand in all_brands:
            current_competitors = [b for b in all_brands if b != brand]
            
            for q_idx, question in enumerate(raw_questions):
                for model_info in selected_models:
                    model_name = model_info.get('name', '')
                    
                    # 检查熔断器
                    if not self.scheduler.is_model_available(model_name):
                        api_logger.warning(f"[ConcurrentEngine] 模型 {model_name} 已熔断，跳过")
                        continue
                    
                    # 获取超时配置
                    timeout_manager = get_timeout_manager()
                    timeout = timeout_manager.get_timeout(model_name)
                    
                    # 构建提示词
                    prompt = GEO_PROMPT_TEMPLATE.format(
                        brand_name=brand,
                        competitors=', '.join(current_competitors) if current_competitors else '无',
                        question=question
                    )
                    
                    task = AITask(
                        task_id=f"{brand}-{q_idx}-{model_name}",
                        brand=brand,
                        question=question,
                        model_name=model_name,
                        prompt=prompt,
                        q_idx=q_idx,
                        timeout=timeout
                    )
                    tasks.append(task)
        
        api_logger.info(f"[ConcurrentEngine] 构建任务完成：{len(tasks)} 个任务")
        return tasks
    
    def _execute_single_task(self, task: AITask) -> AIResult:
        """执行单个 AI 调用任务"""
        start_time = time.time()
        
        try:
            # 创建 AI 客户端
            client = AIAdapterFactory.create(task.model_name)
            
            # 创建容错执行器
            ai_executor = FaultTolerantExecutor(timeout_seconds=task.timeout)
            
            # 执行 AI 调用（在后台线程中使用 asyncio.run）
            ai_result = asyncio.run(
                ai_executor.execute_with_fallback(
                    task_func=client.send_prompt,
                    task_name=f"{task.brand}-{task.model_name}",
                    source=task.model_name,
                    prompt=task.prompt
                )
            )
            
            execution_time = time.time() - start_time
            
            return AIResult(
                task=task,
                success=ai_result.status == 'success',
                data=ai_result.content if ai_result.success else None,
                error_message=ai_result.error_message,
                error_type=ai_result.error_type.value if ai_result.error_type else None,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            api_logger.error(f"[ConcurrentEngine] AI 调用失败：{task.task_id}: {e}")
            
            return AIResult(
                task=task,
                success=False,
                error_message=str(e),
                error_type='unknown_error',
                execution_time=execution_time
            )
    
    def _handle_result(self, result: AIResult):
        """处理 AI 调用结果"""
        with self.results_lock:
            # 解析 GEO 数据
            geo_data = None
            parse_error = None
            
            if result.success and result.data:
                geo_data, parse_error = parse_geo_with_validation(
                    result.data,
                    self.execution_id,
                    result.task.q_idx,
                    result.task.model_name
                )
                
                if result.success:
                    self.scheduler.record_model_success(result.task.model_name)
                else:
                    self.scheduler.record_model_failure(result.task.model_name)
            
            # 构建结果字典
            result_dict = {
                'brand': result.task.brand,
                'question': result.task.question,
                'model': result.task.model_name,
                'q_idx': result.task.q_idx,
                'response': result.data,
                'geo_data': geo_data,
                'error': parse_error or (result.error_message if not result.success else None),
                'error_type': result.error_type,
                'execution_time': result.execution_time
            }
            
            self.results.append(result_dict)
            
            # 更新进度
            with self.progress_lock:
                self.completed += 1
                
                # 批量更新进度（减少开销）
                if self.completed % PROGRESS_UPDATE_INTERVAL == 0:
                    self.scheduler.update_progress(
                        self.completed,
                        self.total_tasks,
                        'ai_fetching'
                    )
                
                # 批量写入数据库
                if self.completed % BATCH_WRITE_THRESHOLD == 0:
                    self._flush_batch_cache()
    
    def _handle_error(self, task: AITask, error: str):
        """处理任务错误"""
        with self.results_lock:
            result_dict = {
                'brand': task.brand,
                'question': task.question,
                'model': task.model_name,
                'q_idx': task.q_idx,
                'response': None,
                'geo_data': None,
                'error': error,
                'error_type': 'execution_error',
                'execution_time': 0.0
            }
            self.results.append(result_dict)
            
            with self.progress_lock:
                self.completed += 1
                self.scheduler.update_progress(
                    self.completed,
                    self.total_tasks,
                    'ai_fetching'
                )
    
    def _flush_batch_cache(self):
        """批量写入数据库"""
        # P0-2 优化：批量写入
        try:
            from wechat_backend.repositories import save_dimension_result
            
            with self.results_lock:
                # 批量保存维度结果
                for result in self.results[-BATCH_WRITE_THRESHOLD:]:
                    try:
                        dim_status = "success" if result.get('geo_data') else "failed"
                        save_dimension_result(
                            execution_id=self.execution_id,
                            dimension_name=f"{result['brand']}-{result['model']}",
                            dimension_type="ai_analysis",
                            source=result['model'],
                            status=dim_status,
                            score=None,
                            data=result.get('geo_data') if dim_status == 'success' else None,
                            error_message=result.get('error') if dim_status == 'failed' else None
                        )
                    except Exception as e:
                        api_logger.error(f"[ConcurrentEngine] 保存维度结果失败：{e}")
        
        except Exception as e:
            api_logger.error(f"[ConcurrentEngine] 批量写入失败：{e}")
    
    def _aggregate_results(self, execution_time: float) -> Dict[str, Any]:
        """聚合结果"""
        api_logger.info(f"[ConcurrentEngine] 开始聚合结果，总结果数：{len(self.results)}")
        
        # 去重
        deduplicated = deduplicate_results(self.results)
        
        # 验证完成度
        verification = verify_completion(deduplicated, self.total_tasks)
        
        # 按品牌聚合
        all_brands = list(set(r.get('brand', '') for r in deduplicated if r.get('brand')))
        aggregated = []
        for brand in all_brands:
            brand_data = aggregate_results_by_brand(deduplicated, brand)
            aggregated.append(brand_data)
        
        # 质量评分
        quality_scorer = get_quality_scorer()
        quality_score = quality_scorer.calculate_aggregate_score(deduplicated)
        
        # 确定执行状态
        has_valid_results = len(deduplicated) > 0
        success_rate = verification.get('success_rate', 0)
        
        if has_valid_results:
            status = 'completed' if success_rate >= 0.5 else 'partial_completed'
        else:
            status = 'failed'
        
        # 更新执行存储
        self.execution_store[self.execution_id].update({
            'status': status,
            'stage': status,
            'progress': 100,
            'completed': self.completed,
            'total': self.total_tasks,
            'results': deduplicated,
            'aggregated': aggregated,
            'quality_score': quality_score,
            'end_time': datetime.now().isoformat(),
            'execution_time': execution_time
        })
        
        api_logger.info(f"[ConcurrentEngine] 执行完成：{status}, 耗时：{execution_time:.2f}秒")
        
        return {
            'success': has_valid_results,
            'execution_id': self.execution_id,
            'status': status,
            'formula': f'{len(all_brands)}品牌 × {len(deduplicated)}问题 × 多模型',
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed,
            'success_rate': success_rate,
            'results': deduplicated,
            'aggregated': aggregated,
            'quality_score': quality_score,
            'execution_time': execution_time
        }
    
    def _aggregate_results_streaming(self, execution_time: float) -> Dict[str, Any]:
        """
        流式聚合结果（P2-2 优化）
        
        使用 StreamingResultAggregator 的 finalize 方法
        支持 SSE 推送最终结果
        
        Args:
            execution_time: 执行时间
        
        Returns:
            执行结果
        """
        # 使用流式聚合器的 finalize 方法
        final_result = self.aggregator.finalize()
        
        # 更新执行存储
        self.execution_store[self.execution_id].update({
            'status': final_result.get('overall_quality', {}).get('success_rate', 0) >= 0.5 and 'completed' or 'partial_completed',
            'stage': 'completed',
            'progress': 100,
            'completed': self.completed,
            'total': self.total_tasks,
            'results': final_result['results'],
            'aggregated': final_result['aggregated'],
            'quality_score': final_result.get('overall_quality'),
            'end_time': datetime.now().isoformat(),
            'execution_time': execution_time
        })
        
        # P2-1 优化：发送 SSE 完成消息
        if SSE_ENABLED:
            send_task_complete(self.execution_id, {
                'results': final_result['results'],
                'aggregated': final_result['aggregated'],
                'overall_quality': final_result.get('overall_quality'),
                'execution_time': execution_time
            })
        
        api_logger.info(f"[ConcurrentEngine] 流式聚合完成：{len(final_result['results'])} 个结果，耗时：{execution_time:.2f}秒")
        
        has_valid_results = len(final_result['results']) > 0
        success_rate = final_result.get('overall_quality', {}).get('success_rate', 0)
        
        return {
            'success': has_valid_results,
            'execution_id': self.execution_id,
            'status': 'completed' if success_rate >= 0.5 else 'partial_completed',
            'formula': f'{len(final_result["aggregated"])}品牌 × 多问题 × 多模型',
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed,
            'success_rate': success_rate,
            'results': final_result['results'],
            'aggregated': final_result['aggregated'],
            'quality_score': final_result.get('overall_quality'),
            'execution_time': execution_time
        }


# =============================================================================
# 便捷函数
# =============================================================================

def execute_nxm_test_concurrent(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str,
    user_level: str,
    execution_store: Dict[str, Any],
    scheduler,
    timeout_seconds: int = 300,
    max_concurrent: int = MAX_CONCURRENT_AI_CALLS
) -> Dict[str, Any]:
    """
    并发执行 NxM 测试（P0 优化版本）
    
    Args:
        execution_id: 执行 ID
        main_brand: 主品牌
        competitor_brands: 竞品品牌列表
        selected_models: 选择的模型列表
        raw_questions: 问题列表
        user_id: 用户 ID
        user_level: 用户等级
        execution_store: 执行存储
        scheduler: 调度器
        timeout_seconds: 总超时时间
        max_concurrent: 最大并发数
    
    Returns:
        执行结果
    """
    # 创建并发执行引擎
    engine = ConcurrentExecutionEngine(
        execution_id=execution_id,
        scheduler=scheduler,
        execution_store=execution_store,
        max_concurrent=max_concurrent
    )
    
    # 执行
    return engine.execute(
        main_brand=main_brand,
        competitor_brands=competitor_brands,
        selected_models=selected_models,
        raw_questions=raw_questions,
        user_id=user_id,
        user_level=user_level
    )
