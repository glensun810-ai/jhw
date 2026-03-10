"""
NxM 并发执行引擎 v3 - 并行优化版

颠覆性重构：
1. 从串行执行改为并行执行（问题×模型同时调用）
2. 使用信号量控制并发度，避免 API 限流
3. 实时进度推送（WebSocket）
4. 智能熔断和重试
5. 【P0 优化 - 2026-03-05】令牌桶速率限制，避免死等

性能提升：
- 串行：1 问题×1 模型 = 21 秒 → 总耗时 35 秒
- 并行：3 问题×3 模型 = 21 秒（并发执行）→ 总耗时预计 12-15 秒

架构参考：
- Google Cloud Dataflow: 并行任务调度
- AWS Step Functions: 状态机 + 并行执行
- 阿里云函数计算：弹性并发控制

@author: 系统架构组
@date: 2026-03-02
@version: 3.0.0 (颠覆性重构版)
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import OBJECTIVE_QUESTION_TEMPLATE
from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor
from wechat_backend.ai_timeout import get_timeout_manager
from wechat_backend.multi_model_executor import get_single_model_executor
from wechat_backend.rate_limiter import acquire_rate_limit  # 【P0 新增】速率限制
from wechat_backend.error_recovery import RetryHandler, PresetRetryConfigs  # 【P2 修复】重试机制
from legacy_config import Config


class NxMParallelExecutor:
    """
    NxM 并行执行器
    
    功能：
    1. 问题×模型并行调用
    2. 并发度控制（信号量）
    3. 实时进度推送
    4. 智能熔断
    """
    
    def __init__(
        self,
        execution_id: str,
        max_concurrent: int = 6,
        enable_realtime_push: bool = True
    ):
        """
        初始化并行执行器
        
        参数：
            execution_id: 执行 ID
            max_concurrent: 最大并发数（默认 6，避免 API 限流）
            enable_realtime_push: 启用实时推送
        """
        self.execution_id = execution_id
        self.max_concurrent = max_concurrent
        self.enable_realtime_push = enable_realtime_push
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 进度追踪
        self._total_tasks = 0
        self._completed_tasks = 0
        self._results = []
        self._errors = []
        
        # 实时推送服务
        self._push_service = None
        if enable_realtime_push:
            try:
                from wechat_backend.services.realtime_push_service import get_realtime_push_service
                self._push_service = get_realtime_push_service()
            except ImportError:
                api_logger.warning(f"[NxM] 实时推送服务不可用")
    
    async def execute(
        self,
        main_brand: str,
        competitor_brands: List[str],
        selected_models: List[Dict[str, Any]],
        raw_questions: List[str],
        user_id: str,
        user_level: str
    ) -> Dict[str, Any]:
        """
        执行并行诊断
        
        参数：
            main_brand: 主品牌
            competitor_brands: 竞品品牌列表
            selected_models: 选中的 AI 模型列表
            raw_questions: 问题列表
            user_id: 用户 ID
            user_level: 用户等级
            
        返回：
            执行结果
        """
        start_time = time.time()
        
        # 1. 初始化任务
        tasks = []
        self._total_tasks = len(raw_questions) * len(selected_models)
        
        api_logger.info(
            f"[NxM-Parallel] 🚀 开始并行执行 - execution_id={self.execution_id}, "
            f"问题数={len(raw_questions)}, 模型数={len(selected_models)}, "
            f"总任务数={self._total_tasks}, 最大并发={self.max_concurrent}"
        )
        
        # 2. 立即推送启动通知
        await self._push_progress(0, "ai_fetching", "正在启动 AI 调用")
        
        # 3. 创建所有任务（不等待）
        for q_idx, question in enumerate(raw_questions):
            for model_info in selected_models:
                model_name = model_info.get('name', '')

                # 创建异步任务
                task = self._execute_single_task(
                    question=question,
                    model_name=model_name,
                    q_idx=q_idx,
                    model_idx=selected_models.index(model_info),
                    main_brand=main_brand  # 【P2 修复 - 2026-03-07】传递 main_brand 参数
                )
                tasks.append(task)
        
        # 4. 并发执行所有任务（使用 gather）
        api_logger.info(f"[NxM-Parallel] ⚡ 并发执行 {len(tasks)} 个任务...")
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            api_logger.error(f"[NxM-Parallel] ❌ 执行失败：{e}")
            return self._build_error_result(f"执行失败：{str(e)}")
        
        # 5. 处理结果
        valid_results = []
        failed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                api_logger.error(f"[NxM-Parallel] ❌ 任务 {i} 异常：{result}")
                self._errors.append({
                    'task_index': i,
                    'error': str(result)
                })
            elif isinstance(result, dict) and result.get('success'):
                # 【P0 关键修复 - 2026-03-06】只收集成功的结果
                valid_results.append(result['data'])
            elif isinstance(result, dict):
                # 【P0 关键修复】失败的结果单独收集，不混入有效结果
                failed_results.append(result)
                api_logger.warning(
                    f"[NxM-Parallel] ⚠️ 任务 {i} 失败：{result.get('error', '未知错误')}"
                )
            else:
                api_logger.error(f"[NxM-Parallel] ❌ 任务 {i} 返回未知类型：{type(result)}")
                self._errors.append({
                    'task_index': i,
                    'error': f'未知返回类型：{type(result)}'
                })

        # 6. 推送完成通知
        elapsed_time = time.time() - start_time
        api_logger.info(
            f"[NxM-Parallel] ✅ 执行完成 - execution_id={self.execution_id}, "
            f"有效结果={len(valid_results)}/{self._total_tasks}, "
            f"失败={len(failed_results)}/{self._total_tasks}, "
            f"耗时={elapsed_time:.2f}秒"
        )

        await self._push_complete(len(valid_results))

        # 7. 构建返回结果
        return self._build_success_result(valid_results, elapsed_time)
    
    async def _execute_single_task(
        self,
        question: str,
        model_name: str,
        q_idx: int,
        model_idx: int,
        main_brand: str  # 【P2 修复 - 2026-03-07】添加 main_brand 参数
    ) -> Dict[str, Any]:
        """
        执行单个任务（问题×模型，带超时保护）

        参数：
            question: 问题
            model_name: 模型名称
            q_idx: 问题索引
            model_idx: 模型索引
            main_brand: 主品牌名称

        返回：
            任务结果
        """
        # 获取信号量（控制并发度）
        async with self._semaphore:
            task_start = time.time()

            try:
                api_logger.debug(
                    f"[NxM-Parallel] 🔧 开始任务 Q{q_idx + 1}×{model_name}"
                )

                # 【P0 优化 - 2026-03-05】速率限制（令牌桶算法）
                # 如果距离上次请求已超过，则无等待；否则智能等待
                wait_time = await acquire_rate_limit(model_name)
                if wait_time > 0.01:  # 超过 10ms 才记录
                    api_logger.info(
                        f"[NxM-Parallel] ⏳ 频率控制等待：Q{q_idx + 1}×{model_name}, "
                        f"wait={wait_time:.3f}s"
                    )

                # 1. 构建提示词
                prompt = OBJECTIVE_QUESTION_TEMPLATE.format(question=question)

                # 2. 获取超时配置（默认 60 秒）
                timeout_manager = get_timeout_manager()
                timeout = timeout_manager.get_timeout(model_name) or 60  # 默认 60 秒

                # 3. 创建 AI 客户端并验证 API Key
                # 【P0 关键修复 - 2026-03-06】使用平台名称而非具体模型名称获取 API Key
                # 对于 doubao-seed-2-0-mini-260215 这样的模型，需要使用 'doubao' 平台名称
                platform_name = 'doubao' if 'doubao' in model_name.lower() else model_name
                api_key = Config.get_api_key(platform_name)

                if not api_key:
                    raise ValueError(f"模型 {model_name} API Key 未配置（平台：{platform_name}）")

                client = AIAdapterFactory.create(model_name)

                # 4. 执行 AI 调用（使用单模型执行器，带超时保护 + 重试机制）
                # 【P2 修复 - 2026-03-07】添加重试机制
                ai_retry_handler = RetryHandler(PresetRetryConfigs.AI_CALL_RETRY)
                
                async def _execute_ai_call():
                    """执行 AI 调用的闭包函数"""
                    # 注意：execute() 返回 tuple: (AIResponse, actual_model)
                    return await asyncio.wait_for(
                        get_single_model_executor(timeout=timeout).execute(
                            prompt=prompt,
                            model_name=model_name,
                            execution_id=self.execution_id,
                            q_idx=q_idx
                        ),
                        timeout=timeout
                    )

                try:
                    # 使用重试机制执行 AI 调用
                    retry_result = await ai_retry_handler.execute_with_retry_async(
                        _execute_ai_call,
                        execution_id=f"{self.execution_id}_Q{q_idx + 1}x{model_name}"
                    )

                    if retry_result.success:
                        # 【P2 修复 - 2026-03-07】处理返回值 tuple
                        ai_call_result = retry_result.result
                        if isinstance(ai_call_result, tuple):
                            ai_result, actual_model = ai_call_result
                        else:
                            ai_result = ai_call_result
                    else:
                        # 重试失败
                        task_elapsed = time.time() - task_start
                        api_logger.error(
                            f"[NxM-Parallel] ❌ Q{q_idx + 1}×{model_name} 重试失败 "
                            f"({task_elapsed:.2f}秒): {retry_result.error}"
                        )
                        
                        return {
                            'success': False,
                            'error': f'AI 调用失败（已重试{len(retry_result.attempts)}次）: {str(retry_result.error)}',
                            'brand': main_brand,
                            'question': question,
                            'model': model_name,
                            'latency': task_elapsed,
                            'retry_attempts': len(retry_result.attempts)
                        }
                        
                except asyncio.TimeoutError:
                    # 【P0 关键修复】AI 调用超时，返回错误结果但不阻塞其他任务
                    task_elapsed = time.time() - task_start
                    api_logger.error(
                        f"[NxM-Parallel] ⏰ 任务超时：Q{q_idx + 1}×{model_name} "
                        f"({task_elapsed:.2f}秒 > {timeout}秒)"
                    )

                    return {
                        'success': False,
                        'error': f'AI 调用超时（{timeout}秒）',
                        'brand': main_brand,  # 【P0 修复 - 2026-03-07】添加 brand 字段
                        'question': question,
                        'model': model_name,
                        'timeout': True,
                        'latency': task_elapsed
                    }

                # 5. 处理结果
                if ai_result.success:
                    # AI 调用成功
                    task_elapsed = time.time() - task_start

                    api_logger.info(
                        f"[NxM-Parallel] ✅ Q{q_idx + 1}×{model_name} 成功 "
                        f"({task_elapsed:.2f}秒，tokens={ai_result.tokens_used})"
                    )

                    # 推送进度更新
                    await self._increment_progress("ai_fetching")

                    # 【P1 修复 - 2026-03-07】传递 tokens_used 到结果字典
                    return {
                        'success': True,
                        'data': {
                            'brand': main_brand,  # 【P0 修复 - 2026-03-07】添加 brand 字段
                            'question': question,
                            'model': actual_model,
                            'response': {
                                'content': str(ai_result.content),
                                'latency': task_elapsed,
                                'metadata': ai_result.metadata or {}
                            },
                            'geo_data': self._parse_geo_data(ai_result.content),
                            'error': None,
                            'error_type': None,
                            'is_objective': True,
                            'tokens_used': ai_result.tokens_used,  # 【P1 修复】添加 tokens_used
                            'prompt_tokens': (ai_result.metadata or {}).get('prompt_tokens', 0),  # 【P1 修复】添加 prompt_tokens
                            'completion_tokens': (ai_result.metadata or {}).get('completion_tokens', 0),  # 【P1 修复】添加 completion_tokens
                            'cached_tokens': (ai_result.metadata or {}).get('cached_tokens', 0)  # 【P1 修复】添加 cached_tokens
                        }
                    }
                else:
                    # AI 调用失败
                    task_elapsed = time.time() - task_start

                    api_logger.warning(
                        f"[NxM-Parallel] ⚠️ Q{q_idx + 1}×{model_name} 失败 "
                        f"({task_elapsed:.2f}秒): {ai_result.error_message}"
                    )

                    # 推送进度更新
                    await self._increment_progress("ai_fetching")

                    # 【P1 修复 - 2026-03-07】失败时也传递 tokens_used（如果有部分响应）
                    return {
                        'success': False,
                        'data': {
                            'brand': main_brand,  # 【P0 修复 - 2026-03-07】添加 brand 字段
                            'question': question,
                            'model': model_name,
                            'response': {
                                'content': None,
                                'latency': task_elapsed,
                                'metadata': ai_result.metadata or {}
                            },
                            'geo_data': None,
                            'error': ai_result.error_message,
                            'error_type': str(ai_result.error_type.value) if hasattr(ai_result, 'error_type') else 'unknown',
                            'is_objective': True,
                            'tokens_used': ai_result.tokens_used if ai_result.tokens_used > 0 else 0,  # 【P1 修复】
                            'prompt_tokens': (ai_result.metadata or {}).get('prompt_tokens', 0),  # 【P1 修复】
                            'completion_tokens': (ai_result.metadata or {}).get('completion_tokens', 0),  # 【P1 修复】
                            'cached_tokens': (ai_result.metadata or {}).get('cached_tokens', 0)  # 【P1 修复】
                        }
                    }

            except Exception as e:
                task_elapsed = time.time() - task_start

                api_logger.error(
                    f"[NxM-Parallel] ❌ Q{q_idx + 1}×{model_name} 异常 "
                    f"({task_elapsed:.2f}秒): {e}"
                )

                # 推送进度更新
                await self._increment_progress("ai_fetching")

                return {
                    'success': False,
                    'data': {
                        'brand': main_brand,  # 【P0 修复 - 2026-03-07】添加 brand 字段
                        'question': question,
                        'model': model_name,
                        'response': {
                            'content': None,
                            'latency': task_elapsed,
                            'metadata': {}
                        },
                        'geo_data': None,
                        'error': str(e),
                        'error_type': 'execution_error',
                        'is_objective': True,
                        'tokens_used': 0,  # 异常情况下无 token 消耗
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'cached_tokens': 0
                    }
                }
    
    def _parse_geo_data(self, content: str) -> Optional[Dict[str, Any]]:
        """解析 GEO 数据"""
        try:
            from wechat_backend.nxm_result_aggregator import parse_geo_with_validation
            
            geo_data, parse_error = parse_geo_with_validation(
                content=content,
                execution_id=self.execution_id,
                q_idx=0,  # 实际使用时应该传入正确的 q_idx
                model_name="unknown"
            )
            
            if parse_error or geo_data.get('_error'):
                return None
            
            return geo_data
            
        except Exception as e:
            api_logger.debug(f"[NxM-Parallel] GEO 解析失败：{e}")
            return None
    
    async def _push_progress(
        self,
        progress: int,
        stage: str,
        status_text: str
    ) -> None:
        """推送进度更新"""
        if not self._push_service:
            return
        
        try:
            await self._push_service.send_progress(
                execution_id=self.execution_id,
                progress=progress,
                stage=stage,
                status="running",
                status_text=status_text
            )
        except Exception as e:
            api_logger.debug(f"[NxM-Parallel] 推送进度失败：{e}")
    
    async def _increment_progress(
        self,
        stage: str,
        status_text: str = ""
    ) -> None:
        """增加进度并推送"""
        self._completed_tasks += 1
        progress = int((self._completed_tasks / self._total_tasks) * 100)
        
        if not status_text:
            status_text = f"已完成 {self._completed_tasks}/{self._total_tasks}"
        
        await self._push_progress(progress, stage, status_text)
    
    async def _push_complete(self, results_count: int) -> None:
        """推送完成通知"""
        if not self._push_service:
            return
        
        try:
            await self._push_service.send_complete(
                execution_id=self.execution_id,
                result={
                    'results_count': results_count,
                    'total_tasks': self._total_tasks,
                    'errors_count': len(self._errors)
                }
            )
        except Exception as e:
            api_logger.debug(f"[NxM-Parallel] 推送完成失败：{e}")
    
    def _build_success_result(
        self,
        valid_results: List[Dict],
        elapsed_time: float
    ) -> Dict[str, Any]:
        """构建成功结果"""
        return {
            'success': True,
            'execution_id': self.execution_id,
            'results': valid_results,
            'total_tasks': self._total_tasks,
            'completed_tasks': len(valid_results),
            'failed_tasks': self._total_tasks - len(valid_results),
            'errors': self._errors,
            'elapsed_time': elapsed_time,
            'formula': f"{len(valid_results)}/{self._total_tasks}",
            'performance': {
                'parallel': True,
                'max_concurrent': self.max_concurrent,
                'avg_task_time': elapsed_time / max(self._total_tasks, 1)
            }
        }
    
    def _build_error_result(self, error_message: str) -> Dict[str, Any]:
        """构建错误结果"""
        return {
            'success': False,
            'execution_id': self.execution_id,
            'error': error_message,
            'results': [],
            'total_tasks': self._total_tasks,
            'completed_tasks': 0
        }


# 工厂函数
def get_parallel_executor(
    execution_id: str,
    max_concurrent: int = 6,
    enable_realtime_push: bool = True
) -> NxMParallelExecutor:
    """
    获取并行执行器实例
    
    参数：
        execution_id: 执行 ID
        max_concurrent: 最大并发数
        enable_realtime_push: 启用实时推送
        
    返回：
        并行执行器实例
    """
    return NxMParallelExecutor(
        execution_id=execution_id,
        max_concurrent=max_concurrent,
        enable_realtime_push=enable_realtime_push
    )


# 便捷函数：并行执行诊断
async def execute_parallel_nxm(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str,
    user_level: str,
    max_concurrent: int = 6
) -> Dict[str, Any]:
    """
    并行执行 NxM 诊断（便捷函数）
    
    参数：
        execution_id: 执行 ID
        main_brand: 主品牌
        competitor_brands: 竞品品牌列表
        selected_models: 选中的 AI 模型列表
        raw_questions: 问题列表
        user_id: 用户 ID
        user_level: 用户等级
        max_concurrent: 最大并发数
        
    返回：
        执行结果
    """
    executor = get_parallel_executor(
        execution_id=execution_id,
        max_concurrent=max_concurrent
    )
    
    return await executor.execute(
        main_brand=main_brand,
        competitor_brands=competitor_brands,
        selected_models=selected_models,
        raw_questions=raw_questions,
        user_id=user_id,
        user_level=user_level
    )
