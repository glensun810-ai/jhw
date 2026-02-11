"""
Test Scheduler with execution strategies
Handles scheduling of tests with different execution approaches
"""
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
    timeout: int = 30
    max_retries: int = 3
    metadata: Dict[str, Any] = None


class TestScheduler:
    """Manages scheduling and execution of test tasks"""
    
    def __init__(self, max_workers: int = 10, strategy: ExecutionStrategy = ExecutionStrategy.CONCURRENT):
        self.max_workers = max_workers
        self.strategy = strategy
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.platform_config_manager = PlatformConfigManager()
        api_logger.info(f"Initialized TestScheduler with strategy {strategy.value}, max_workers {max_workers}")
    
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
        future_to_task = {self.executor.submit(self._execute_single_task, task): task for task in test_tasks}
        
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                if callback:
                    callback(task, result)
            except Exception as e:
                api_logger.error(f"Error executing task {task.id}: {str(e)}")
                results.append({'task_id': task.id, 'success': False, 'error': str(e), 'result': None})
        return results
    
    def _execute_single_task(self, task: TestTask) -> Dict[str, Any]:
        """Executes a single test task with retry mechanism using real AI clients."""
        api_logger.debug(f"Executing task {task.id} for model {task.ai_model}")

        last_error = "Max retries reached"

        for attempt in range(task.max_retries):
            try:
                platform_name = self._map_model_to_platform(task.ai_model)
                config = self.platform_config_manager.get_platform_config(platform_name)

                if not config or not config.api_key:
                    raise ValueError(f"API key for platform '{platform_name}' is not configured.")

                ai_client = AIAdapterFactory.create(platform_name, config.api_key, task.ai_model)

                # Use synchronous send_prompt method instead of async query
                ai_response = ai_client.send_prompt(task.question)

                if ai_response.success:
                    api_logger.info(f"Task {task.id} completed successfully on attempt {attempt + 1}")
                    return {
                        'task_id': task.id,
                        'success': True,
                        'result': ai_response.to_dict(),  # AIResponse has to_dict method
                        'attempt': attempt + 1,
                        'model': task.ai_model,
                        'question': task.question,
                        'brand_name': task.brand_name
                    }
                else:
                    last_error = ai_response.error_message
                    api_logger.warning(f"Task {task.id} failed on attempt {attempt + 1}: {last_error}")

            except Exception as e:
                last_error = str(e)
                api_logger.error(f"Task {task.id} failed on attempt {attempt + 1} with exception: {last_error}")

            time.sleep(2 ** attempt) # Exponential backoff

        api_logger.error(f"All {task.max_retries} attempts failed for task {task.id}. Last error: {last_error}")
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
        if '豆包' in model_name:
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