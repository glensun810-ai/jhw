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
    priority: int = 0  # Lower number means higher priority
    timeout: int = 30  # Timeout in seconds
    max_retries: int = 3  # Maximum number of retries
    metadata: Dict[str, Any] = None


class TestScheduler:
    """Manages scheduling and execution of test tasks"""
    
    def __init__(self, max_workers: int = 10, strategy: ExecutionStrategy = ExecutionStrategy.CONCURRENT):
        """
        Initialize the test scheduler
        
        Args:
            max_workers: Maximum number of concurrent workers
            strategy: Execution strategy to use
        """
        self.max_workers = max_workers
        self.strategy = strategy
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = Lock()
        self.active_tasks = {}
        
        api_logger.info(f"Initialized TestScheduler with strategy {strategy.value}, max_workers {max_workers}")
    
    def schedule_tests(
        self, 
        test_tasks: List[TestTask], 
        callback: Callable[[TestTask, Dict[str, Any]], None] = None
    ) -> Dict[str, Any]:
        """
        Schedule and execute tests based on the configured strategy
        
        Args:
            test_tasks: List of test tasks to execute
            callback: Optional callback function to call when each task completes
            
        Returns:
            Dict with execution results and statistics
        """
        start_time = time.time()
        
        if self.strategy == ExecutionStrategy.SEQUENTIAL:
            results = self._execute_sequential(test_tasks, callback)
        elif self.strategy == ExecutionStrategy.CONCURRENT:
            results = self._execute_concurrent(test_tasks, callback)
        elif self.strategy == ExecutionStrategy.BATCH:
            results = self._execute_batch(test_tasks, callback)
        else:
            raise ValueError(f"Unknown execution strategy: {self.strategy}")
        
        total_time = time.time() - start_time
        
        stats = {
            'total_tasks': len(test_tasks),
            'completed_tasks': len([r for r in results if r.get('success', False)]),
            'failed_tasks': len([r for r in results if not r.get('success', False)]),
            'execution_time': total_time,
            'strategy': self.strategy.value,
            'results': results
        }
        
        api_logger.info(f"Test execution completed. Strategy: {self.strategy.value}, "
                       f"Total: {stats['total_tasks']}, Success: {stats['completed_tasks']}, "
                       f"Failed: {stats['failed_tasks']}, Time: {total_time:.2f}s")
        
        return stats
    
    def _execute_sequential(
        self, 
        test_tasks: List[TestTask], 
        callback: Callable[[TestTask, Dict[str, Any]], None] = None
    ) -> List[Dict[str, Any]]:
        """Execute tests sequentially"""
        api_logger.info(f"Executing {len(test_tasks)} tests sequentially")
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
        """Execute tests concurrently using ThreadPoolExecutor"""
        api_logger.info(f"Executing {len(test_tasks)} tests concurrently with {self.max_workers} workers")
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._execute_single_task, task): task 
                for task in test_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if callback:
                        callback(task, result)
                except Exception as e:
                    api_logger.error(f"Error executing task {task.id}: {str(e)}")
                    results.append({
                        'task_id': task.id,
                        'success': False,
                        'error': str(e),
                        'result': None
                    })
        
        return results
    
    def _execute_batch(
        self, 
        test_tasks: List[TestTask], 
        callback: Callable[[TestTask, Dict[str, Any]], None] = None
    ) -> List[Dict[str, Any]]:
        """Execute tests in batches"""
        api_logger.info(f"Executing {len(test_tasks)} tests in batches of {self.max_workers}")
        results = []
        
        # Sort tasks by priority (higher priority first)
        sorted_tasks = sorted(test_tasks, key=lambda t: t.priority)
        
        # Process in batches
        for i in range(0, len(sorted_tasks), self.max_workers):
            batch = sorted_tasks[i:i + self.max_workers]
            batch_results = self._execute_concurrent(batch, callback)
            results.extend(batch_results)
        
        return results
    
    def _execute_single_task(self, task: TestTask) -> Dict[str, Any]:
        """Execute a single test task with retry mechanism"""
        api_logger.debug(f"Executing task {task.id} for model {task.ai_model}")
        
        last_error = None
        result = None
        
        # Attempt to execute the task up to max_retries times
        for attempt in range(task.max_retries + 1):
            try:
                # This would normally call the AI adapter
                # For now, we'll simulate the execution
                result = self._simulate_ai_call(task)
                
                if result['success']:
                    api_logger.info(f"Task {task.id} completed successfully on attempt {attempt + 1}")
                    return {
                        'task_id': task.id,
                        'success': True,
                        'result': result,
                        'attempt': attempt + 1,
                        'model': task.ai_model,
                        'question': task.question
                    }
                else:
                    api_logger.warning(f"Task {task.id} failed on attempt {attempt + 1}: {result.get('error', 'Unknown error')}")
                    last_error = result.get('error', 'Unknown error')
                    
            except Exception as e:
                api_logger.error(f"Task {task.id} failed on attempt {attempt + 1} with exception: {str(e)}")
                last_error = str(e)
            
            # If not the last attempt, wait before retrying
            if attempt < task.max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        # If all attempts failed
        api_logger.error(f"All {task.max_retries + 1} attempts failed for task {task.id}")
        return {
            'task_id': task.id,
            'success': False,
            'error': last_error,
            'attempt': task.max_retries + 1,
            'model': task.ai_model,
            'question': task.question
        }
    
    def _simulate_ai_call(self, task: TestTask) -> Dict[str, Any]:
        """Simulate calling an AI platform - this would be replaced with actual AI adapter call"""
        # In a real implementation, this would call the AI adapter
        # For now, we'll return a simulated response
        import random
        import time
        
        # Simulate API call delay
        time.sleep(random.uniform(0.5, 2.0))
        
        # Simulate occasional failures
        if random.random() < 0.1:  # 10% failure rate for simulation
            return {
                'success': False,
                'error': 'Simulated API error',
                'content': '',
                'tokens_used': 0,
                'latency': 0
            }
        
        # Simulate successful response
        return {
            'success': True,
            'content': f"This is a simulated response for the question: {task.question}",
            'model': task.ai_model,
            'platform': 'simulated',
            'tokens_used': random.randint(50, 200),
            'latency': random.uniform(0.5, 2.0)
        }
    
    def shutdown(self):
        """Shutdown the scheduler and cleanup resources"""
        self.executor.shutdown(wait=True)
        api_logger.info("TestScheduler shut down successfully")