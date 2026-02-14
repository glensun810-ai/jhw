"""
Test Scheduler with execution strategies
Handles scheduling of tests with different execution approaches
"""
import os
import queue
from enum import Enum
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import uuid
from ..logging_config import api_logger
from ..ai_adapters.factory import AIAdapterFactory
from config_manager import Config as PlatformConfigManager


class ExecutionStrategy(Enum):
    """Different strategies for executing tests"""
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    BATCH = "batch"


@dataclass
class TestTask:
    """Represents a single test task to be executed"""
    id: str
    brand_name: str
    ai_model: str
    question: str
    priority: int = 0
    timeout: int = 90  # 增加默认超时到90秒，适配豆包等慢速API
    max_retries: int = 3
    metadata: Dict[str, Any] = None


class TestScheduler:
    """Manages scheduling and execution of test tasks"""

    def __init__(self, max_workers: int = 3, strategy: ExecutionStrategy = ExecutionStrategy.CONCURRENT):
        self.max_workers = max_workers
        self.strategy = strategy
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.platform_config_manager = PlatformConfigManager()
        self.task_queue = queue.Queue()  # Add task queue for controlled execution
        api_logger.warning(f"TestScheduler initialized with strategy {strategy.value}, max_workers {max_workers} - REDUCED CONCURRENCY TO PREVENT TIMEOUT")
    
    def schedule_tests(
        self, 
        test_tasks: List[TestTask], 
        callback: Callable[[TestTask, Dict[str, Any]], None] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        if self.strategy == ExecutionStrategy.CONCURRENT:
            results = self._execute_concurrent(test_tasks, callback)
        else: # Default to sequential for simplicity
            results = self._execute_sequential(test_tasks, callback)
        
        total_time = time.time() - start_time
        
        stats = {
            'total_tasks': len(test_tasks),
            'completed_tasks': len([r for r in results if r.get('success', False)]),
            'failed_tasks': len([r for r in results if not r.get('success', False)]),
            'execution_time': total_time,
            'strategy': self.strategy.value,
            'results': results
        }
        
        api_logger.info(f"Test execution completed. Success: {stats['completed_tasks']}, Failed: {stats['failed_tasks']}, Time: {total_time:.2f}s")
        return stats
    
    def _execute_sequential(
        self, 
        test_tasks: List[TestTask], 
        callback: Callable[[TestTask, Dict[str, Any]], None] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for task in test_tasks:
            result = self._execute_single_task(task)
            results.append(result)
            if callback:
                callback(task, result)
        return results
    
    def _execute_concurrent(
        self,
        test_tasks: List[TestTask],
        callback: Callable[[TestTask, Dict[str, Any]], None] = None
    ) -> List[Dict[str, Any]]:
        results = []

        # Add tasks to queue for controlled execution
        for task in test_tasks:
            self.task_queue.put(task)

        api_logger.info(f"Queued {len(test_tasks)} test cases for execution with max_workers={self.max_workers}")

        # Submit tasks to executor with controlled concurrency
        futures = []
        for i in range(min(len(test_tasks), self.max_workers)):  # Only submit up to max_workers initially
            if not self.task_queue.empty():
                task = self.task_queue.get()
                future = self.executor.submit(self._execute_single_task_with_queue, task)
                futures.append((future, task))

        # Process completed tasks and submit new ones as they finish
        while futures:
            # Wait for at least one task to complete
            completed_futures = []
            for future, task in futures:
                if future.done():
                    completed_futures.append((future, task))

            # Process completed tasks
            for future, task in completed_futures:
                futures.remove((future, task))
                try:
                    result = future.result()
                    results.append(result)
                    if callback:
                        callback(task, result)
                except Exception as e:
                    api_logger.error(f"Error executing task {task.id}: {str(e)}")
                    results.append({'task_id': task.id, 'success': False, 'error': str(e), 'result': None})

            # Submit new tasks if available and we have capacity
            while len(futures) < self.max_workers and not self.task_queue.empty():
                task = self.task_queue.get()
                future = self.executor.submit(self._execute_single_task_with_queue, task)
                futures.append((future, task))

        return results

    def _execute_single_task_with_queue(self, task: TestTask) -> Dict[str, Any]:
        """Executes a single test task with retry mechanism using real AI clients."""
        api_logger.debug(f"Executing task {task.id} for model {task.ai_model}")

        last_error = "Max retries reached"
        platform_name = None
        actual_model_id = None

        for attempt in range(task.max_retries):
            try:
                platform_name = self._map_model_to_platform(task.ai_model)
                config = self.platform_config_manager.get_platform_config(platform_name)

                if not config or not config.api_key:
                    raise ValueError(f"API key for platform '{platform_name}' is not configured.")

                # Get the actual model ID instead of using display name
                actual_model_id = self._get_actual_model_id(task.ai_model, platform_name)

                ai_client = AIAdapterFactory.create(platform_name, config.api_key, actual_model_id)

                # Use synchronous send_prompt method instead of async query
                # 【修复】根据平台类型设置合适的超时时间，豆包需要更长的超时
                if platform_name == 'doubao':
                    api_timeout = 90  # 豆包API响应慢，使用90秒超时
                    api_logger.info(f"[TimeoutConfig] Task {task.id} using 90s timeout for Doubao API call")
                else:
                    api_timeout = task.timeout  # 其他平台使用任务配置的超时
                
                start_time = time.time()
                ai_response = ai_client.send_prompt(task.question, timeout=api_timeout)
                latency = time.time() - start_time

                # Log response time for monitoring
                api_logger.info(f"Task {task.id} for model {task.ai_model} completed in {latency:.2f}s")

                # 【新增】记录AI响应到日志（所有平台通用）
                try:
                    from utils.ai_response_logger_v2 import log_ai_response
                    log_ai_response(
                        question=task.question,
                        response=ai_response.content if ai_response.success else '',
                        platform=task.ai_model,  # 使用显示名称
                        model=actual_model_id or platform_name,  # 使用实际模型ID
                        brand=task.brand_name,
                        latency_ms=round(latency * 1000),
                        tokens_used=getattr(ai_response, 'tokens_used', None),
                        success=ai_response.success,
                        error_message=ai_response.error_message if not ai_response.success else None,
                        metadata={
                            'source': 'main_system_scheduler',
                            'task_id': task.id,
                            'attempt': attempt + 1,
                            'platform_name': platform_name,
                            'max_retries': task.max_retries
                        }
                    )
                    api_logger.info(f"[AIResponseLogger] Task {task.id} response logged successfully")
                except Exception as log_error:
                    # 记录失败不应影响主流程
                    api_logger.warning(f"[AIResponseLogger] Failed to log task {task.id}: {log_error}")

                if ai_response.success:
                    api_logger.info(f"Task {task.id} completed successfully on attempt {attempt + 1}")
                    return {
                        'task_id': task.id,
                        'success': True,
                        'result': ai_response.to_dict(),  # AIResponse has to_dict method
                        'attempt': attempt + 1,
                        'model': task.ai_model,
                        'question': task.question,
                        'brand_name': task.brand_name,
                        'latency': latency
                    }
                else:
                    last_error = ai_response.error_message
                    api_logger.warning(f"Task {task.id} failed on attempt {attempt + 1}: {last_error}")

            except Exception as e:
                last_error = str(e)
                api_logger.error(f"Task {task.id} failed on attempt {attempt + 1} with exception: {last_error}")

            time.sleep(2 ** attempt) # Exponential backoff

        api_logger.error(f"All {task.max_retries} attempts failed for task {task.id}. Last error: {last_error}")
        
        # 【新增】记录失败的调用
        try:
            from utils.ai_response_logger_v2 import log_ai_response
            log_ai_response(
                question=task.question,
                response='',
                platform=task.ai_model,
                model=actual_model_id or platform_name or 'unknown',
                brand=task.brand_name,
                success=False,
                error_message=last_error,
                metadata={
                    'source': 'main_system_scheduler',
                    'task_id': task.id,
                    'failed_after': task.max_retries,
                    'platform_name': platform_name
                }
            )
        except Exception:
            pass  # 忽略记录失败的错误
        
        return {
            'task_id': task.id,
            'success': False,
            'error': last_error,
            'attempt': task.max_retries,
            'model': task.ai_model,
            'question': task.question,
            'brand_name': task.brand_name,
            'latency': -1  # Indicates failure
        }
    
    def _get_actual_model_id(self, display_model_name: str, platform_name: str) -> str:
        """Maps display model name to actual model ID for the platform."""
        # Map display names to actual model IDs
        # 优先从环境变量读取，确保使用正确的模型ID
        model_id_map = {
            'doubao': os.getenv('DOUBAO_MODEL_ID') or 'ep-20260212000000-gd5tq',  # 必须配置正确的模型ID
            'deepseek': os.getenv('DEEPSEEK_MODEL_ID', 'deepseek-chat'),
            'qwen': os.getenv('QWEN_MODEL_ID', 'qwen-turbo'),
            'wenxin': os.getenv('WENXIN_MODEL_ID', 'ernie-bot-4.5'),
            'zhipu': os.getenv('ZHIPU_MODEL_ID', 'glm-4'),
            'openai': os.getenv('OPENAI_MODEL_ID', 'gpt-3.5-turbo'),
            'anthropic': os.getenv('ANTHROPIC_MODEL_ID', 'claude-3-haiku-20240307'),
            'google': os.getenv('GOOGLE_MODEL_ID', 'gemini-pro'),
        }

        actual_model_id = model_id_map.get(platform_name, display_model_name)
        api_logger.info(f"[ModelMapping] {display_model_name} ({platform_name}) -> {actual_model_id}")
        return actual_model_id

    def _execute_single_task(self, task: TestTask) -> Dict[str, Any]:
        """Executes a single test task with retry mechanism using real AI clients."""
        api_logger.debug(f"Executing task {task.id} for model {task.ai_model}")

        last_error = "Max retries reached"
        platform_name = None
        actual_model_id = None

        for attempt in range(task.max_retries):
            try:
                platform_name = self._map_model_to_platform(task.ai_model)
                config = self.platform_config_manager.get_platform_config(platform_name)

                if not config or not config.api_key:
                    raise ValueError(f"API key for platform '{platform_name}' is not configured.")

                # Get the actual model ID instead of using display name
                actual_model_id = self._get_actual_model_id(task.ai_model, platform_name)

                ai_client = AIAdapterFactory.create(platform_name, config.api_key, actual_model_id)

                # Use synchronous send_prompt method instead of async query
                # 【修复】根据平台类型设置合适的超时时间，豆包需要更长的超时
                if platform_name == 'doubao':
                    api_timeout = 90  # 豆包API响应慢，使用90秒超时
                    api_logger.info(f"[TimeoutConfig] Task {task.id} using 90s timeout for Doubao API call (sequential)")
                else:
                    api_timeout = task.timeout  # 其他平台使用任务配置的超时
                
                start_time = time.time()
                ai_response = ai_client.send_prompt(task.question, timeout=api_timeout)
                latency = time.time() - start_time

                # 【新增】记录AI响应到日志（所有平台通用）
                try:
                    from utils.ai_response_logger_v2 import log_ai_response
                    log_ai_response(
                        question=task.question,
                        response=ai_response.content if ai_response.success else '',
                        platform=task.ai_model,
                        model=actual_model_id or platform_name,
                        brand=task.brand_name,
                        latency_ms=round(latency * 1000),
                        tokens_used=getattr(ai_response, 'tokens_used', None),
                        success=ai_response.success,
                        error_message=ai_response.error_message if not ai_response.success else None,
                        metadata={
                            'source': 'main_system_sequential',
                            'task_id': task.id,
                            'attempt': attempt + 1,
                            'platform_name': platform_name
                        }
                    )
                except Exception as log_error:
                    api_logger.warning(f"[AIResponseLogger] Failed to log task {task.id}: {log_error}")

                if ai_response.success:
                    api_logger.info(f"Task {task.id} completed successfully on attempt {attempt + 1}")
                    return {
                        'task_id': task.id,
                        'success': True,
                        'result': ai_response.to_dict(),
                        'attempt': attempt + 1,
                        'model': task.ai_model,
                        'question': task.question,
                        'brand_name': task.brand_name,
                        'latency': latency
                    }
                else:
                    last_error = ai_response.error_message
                    api_logger.warning(f"Task {task.id} failed on attempt {attempt + 1}: {last_error}")

            except Exception as e:
                last_error = str(e)
                api_logger.error(f"Task {task.id} failed on attempt {attempt + 1} with exception: {last_error}")

            time.sleep(2 ** attempt) # Exponential backoff

        api_logger.error(f"All {task.max_retries} attempts failed for task {task.id}. Last error: {last_error}")
        
        # 【新增】记录失败的调用
        try:
            from utils.ai_response_logger_v2 import log_ai_response
            log_ai_response(
                question=task.question,
                response='',
                platform=task.ai_model,
                model=actual_model_id or platform_name or 'unknown',
                brand=task.brand_name,
                success=False,
                error_message=last_error,
                metadata={
                    'source': 'main_system_sequential',
                    'task_id': task.id,
                    'failed_after': task.max_retries
                }
            )
        except Exception:
            pass
        
        return {
            'task_id': task.id,
            'success': False,
            'error': last_error,
            'attempt': task.max_retries,
            'model': task.ai_model,
            'question': task.question,
            'brand_name': task.brand_name
        }

    def _map_model_to_platform(self, model_name: str) -> str:
        """Maps a model name to its platform name."""
        # Handle exact matches first to avoid substring conflicts
        exact_matches = {
            'DeepSeek': 'deepseek',
            '豆包': 'doubao',
            'doubao': 'doubao',
            'Doubao': 'doubao',
            '元宝': 'yuanbao',
            'yuanbao': 'yuanbao',
            'hunyuan': 'yuanbao',
            '通义千问': 'qwen',
            'TongyiQianwen': 'qwen',
            '智谱AI': 'zhipu',
            'zhipu': 'zhipu',
            'glm': 'zhipu',
            '文心一言': 'wenxin',
            'ernie': 'wenxin',
            'Kimi': 'kimi',
            'kimi': 'kimi',
            'moonshot': 'kimi',
            '月之暗面': 'kimi',
            '讯飞星火': 'spark',
            'spark': 'spark'
        }

        if model_name in exact_matches:
            return exact_matches[model_name]

        # Handle partial matches with specific keywords
        model_name_lower = model_name.lower()
        if 'deepseek' in model_name_lower:
            return 'deepseek'
        if '豆包' in model_name or 'doubao' in model_name_lower:
            return 'doubao'
        if '元宝' in model_name or 'hunyuan' in model_name_lower:
            return 'yuanbao'
        if '通义千问' in model_name or 'qwen' in model_name_lower:
            return 'qwen'
        if '文心一言' in model_name:
            return 'wenxin'
        if 'ernie' in model_name_lower:
            return 'wenxin'
        if 'kimi' in model_name_lower or '月之暗面' in model_name or 'moonshot' in model_name_lower:
            return 'kimi'
        if '讯飞星火' in model_name or 'spark' in model_name_lower:
            return 'spark'
        if 'doubao' in model_name_lower:
            return 'doubao'
        if 'yuanbao' in model_name_lower:
            return 'yuanbao'
        if '智谱' in model_name or 'zhipu' in model_name_lower or 'glm' in model_name_lower:
            return 'zhipu'
        if 'gpt' in model_name_lower:
            return 'openai'
        if 'claude' in model_name_lower:
            return 'anthropic'
        if 'gemini' in model_name_lower:
            return 'google'

        return 'unknown'

    def shutdown(self):
        self.executor.shutdown(wait=True)
        api_logger.info("TestScheduler shut down successfully")