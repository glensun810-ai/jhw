"""
Test Executor - Main entry point for test execution
Integrates scheduler, progress tracking, and AI adapters
"""
from typing import List, Dict, Any, Callable
from datetime import datetime
import uuid
from ai_adapters import AIAdapterFactory
from question_system import TestCase
from wechat_backend.test_engine.scheduler import TestScheduler, TestTask, ExecutionStrategy
from wechat_backend.test_engine.progress_tracker import ProgressTracker, TestProgress
from wechat_backend.logging_config import api_logger
from database import save_test_record
from wechat_backend.realtime_analyzer import get_analyzer, create_analyzer
from wechat_backend.incremental_aggregator import get_aggregator, create_aggregator
from realtime_persistence import get_persistence_service, create_persistence_service, remove_persistence_service


class TestExecutor:
    """Main executor that coordinates test execution with progress tracking"""

    def __init__(self, max_workers: int = 1, strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL):
        """
        Initialize the test executor

        Args:
            max_workers: Maximum number of concurrent workers (set to 1 for sequential execution)
            strategy: Execution strategy to use (SEQUENTIAL for guaranteed order execution)
        """
        # 强制使用串行执行策略以确保每个AI平台请求都能完成
        self.scheduler = TestScheduler(max_workers=1, strategy=ExecutionStrategy.SEQUENTIAL)
        self.progress_tracker = ProgressTracker()
        self.ai_adapter_factory = AIAdapterFactory

        api_logger.info(f"Initialized TestExecutor with SEQUENTIAL strategy, max_workers=1 - SERIAL EXECUTION FOR STABILITY")
    
    def execute_tests(
        self,
        test_cases: List[TestCase],
        api_key: str = "",
        on_progress_update: Callable[[str, TestProgress], None] = None,
        timeout: int = 300,  # 5分钟默认超时
        user_openid: str = "anonymous"  # 添加用户标识用于保存到数据库
    ) -> Dict[str, Any]:
        """
        Execute a list of test cases with progress tracking
        
        Args:
            test_cases: List of test cases to execute
            api_key: API key for AI platforms
            on_progress_update: Callback function to call when progress updates
            timeout: Timeout in seconds for the entire test execution
            user_openid: User identifier for saving results to database
            
        Returns:
            Dict with execution results and statistics
        """
        execution_id = str(uuid.uuid4())
        total_tests = len(test_cases)
        
        api_logger.info(f"Starting execution {execution_id} for {total_tests} test cases")
        
        # Create progress tracking for this execution
        progress = self.progress_tracker.create_execution(
            execution_id=execution_id,
            total_tests=total_tests,
            metadata={
                'start_time': datetime.now().isoformat(),
                'total_tests': total_tests,
                'api_key_provided': bool(api_key)
            }
        )
        
        #【P0 新增】创建实时分析器
        # 从 test_cases 中提取主品牌和所有品牌
        main_brand = test_cases[0].brand_name if test_cases else 'unknown'
        all_brands = list(set(case.brand_name for case in test_cases))
        analyzer = create_analyzer(execution_id, main_brand, all_brands)
        api_logger.info(f"Created RealtimeAnalyzer for execution {execution_id} - Brand: {main_brand}, All brands: {all_brands}")
        
        #【P0 新增】创建增量聚合器
        questions = list(set(case.question for case in test_cases))
        aggregator = create_aggregator(execution_id, main_brand, all_brands, questions)
        api_logger.info(f"Created IncrementalAggregator for execution {execution_id} - Questions: {len(questions)}")
        
        #【阶段 3】创建持久化服务
        persistence_service = create_persistence_service(execution_id, user_openid)
        api_logger.info(f"Created RealtimePersistence for execution {execution_id}")
        
        # Convert TestCases to TestTasks for the scheduler
        test_tasks = []
        for test_case in test_cases:
            task = TestTask(
                id=test_case.id,
                brand_name=test_case.brand_name,
                ai_model=test_case.ai_model,
                question=test_case.question,
                timeout=30,
                max_retries=3
            )
            test_tasks.append(task)
        
        # Define callback for progress updates and checkpoint saving
        def progress_callback(task: TestTask, result: Dict[str, Any]):
            if result.get('success', False):
                self.progress_tracker.update_completed(execution_id, result)
            else:
                self.progress_tracker.update_failed(execution_id, result.get('error', 'Unknown error'))
            
            # 实现分批次保存：每完成一个测试（无论成功或失败）都立即保存到数据库
            try:
                # 提取模型名称，将其格式化为一致的格式
                model_name = task.ai_model
                if model_name.lower() in ['豆包', 'doubao']:
                    model_display_name = '豆包'
                elif model_name.lower() in ['deepseek', 'deepseekr1']:
                    model_display_name = 'DeepSeek'
                elif model_name.lower() in ['qwen', '通义千问', '千问']:
                    model_display_name = '通义千问'
                elif model_name.lower() in ['zhipu', '智谱ai', '智谱']:
                    model_display_name = '智谱AI'
                else:
                    model_display_name = model_name
                
                # 创建一个单独的测试结果记录并保存到数据库
                # 注意：result['result'] 是 AIResponse.to_dict() 返回的字典，需要提取 content 字段
                result_dict = result.get('result', {})
                if isinstance(result_dict, dict):
                    response_content = result_dict.get('content', '')
                else:
                    response_content = ''
                    
                single_test_result = {
                    'brand_name': task.brand_name,
                    'question': task.question,
                    'ai_model': model_display_name,
                    'response': response_content,  # 修复：提取 content 字段而不是整个字典
                    'success': result.get('success', False),
                    'error': result.get('error', '') if not result.get('success', False) else '',
                    'timestamp': datetime.now().isoformat(),
                    'execution_id': execution_id,
                    'attempt': result.get('attempt', 1)
                }
                
                # 保存单个测试结果到数据库
                record_id = save_test_record(
                    user_openid=user_openid,
                    brand_name=task.brand_name,
                    ai_models_used=[model_display_name],
                    questions_used=[task.question],
                    overall_score=0,  # 暂时设为0，因为这是单个测试的结果
                    total_tests=1,
                    results_summary={'individual_test': True, 'task_id': task.id, 'execution_id': execution_id, 'success': result.get('success', False)},
                    detailed_results=[single_test_result]
                )
                
                api_logger.info(f"Saved individual test result (success: {result.get('success', False)}) to database with ID: {record_id}")
                
            except Exception as e:
                api_logger.error(f"Failed to save individual test result to database: {e}")
            
            #【P0 新增】获取实时统计并添加到进度中
            current_progress = self.progress_tracker.get_progress(execution_id)
            
            if analyzer:
                realtime_progress = analyzer.get_realtime_progress()
                # 将实时统计添加到进度对象中
                current_progress.realtime_stats = realtime_progress
                current_progress.brand_rankings = realtime_progress['brand_rankings']
                current_progress.sov = realtime_progress['sov']
                current_progress.avg_sentiment = realtime_progress['avg_sentiment']
                
                api_logger.info(f"Realtime progress: completed={current_progress.completed_tests}/{current_progress.total_tests}, sov={current_progress.sov}%, brands={len(current_progress.brand_rankings)}")
            
            #【P0 新增】添加聚合结果到进度对象
            if aggregator:
                aggregated_results = aggregator.get_aggregated_results()
                current_progress.aggregated_results = aggregated_results
                current_progress.health_score = aggregated_results['summary']['healthScore']
                
                #【阶段 3】定期保存聚合结果 (每保存 3 个任务保存一次聚合结果)
                if persistence_service and current_progress.completed_tests % 3 == 0:
                    persistence_service.save_aggregated_results(aggregated_results)
                    persistence_service.save_brand_rankings(aggregated_results['brand_rankings'])
                    api_logger.info(f"Persisted aggregated results: health_score={aggregated_results['summary']['healthScore']}")
                
                api_logger.info(f"Aggregated results: health_score={current_progress.health_score}, sov={aggregated_results['summary']['sov']}%")
            
            # Call the external progress update callback if provided
            if on_progress_update:
                on_progress_update(execution_id, current_progress)
        
        import threading
        import concurrent.futures
        from functools import partial

        # Execute the tests with timeout handling
        import time
        start_time = time.time()
        
        if timeout > 0:
            if self.scheduler.strategy == ExecutionStrategy.SEQUENTIAL:
                # For sequential execution, run directly without additional threading overhead
                api_logger.info(f"Running sequential execution without ThreadPoolExecutor overhead for stability")
                results = self.scheduler.schedule_tests(test_tasks, progress_callback)
                
                # Apply timeout manually by checking execution time
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    api_logger.warning(f"Sequential execution exceeded timeout of {timeout} seconds, but results were saved")
                    raise TimeoutError(f"Test execution timed out after {timeout} seconds")
            else:
                # For concurrent execution, use ThreadPoolExecutor with timeout
                # Create a partial function with the arguments
                execute_func = partial(self.scheduler.schedule_tests, test_tasks, progress_callback)

                # Use ThreadPoolExecutor with timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(execute_func)
                    try:
                        results = future.result(timeout=timeout)
                    except concurrent.futures.TimeoutError:
                        # 即使超时也要确保已保存的结果不会丢失
                        api_logger.warning(f"Test execution timed out after {timeout} seconds, but individual results were saved")
                        raise TimeoutError(f"Test execution timed out after {timeout} seconds")
        else:
            # Execute without timeout
            results = self.scheduler.schedule_tests(test_tasks, progress_callback)

        # Get final progress
        final_progress = self.progress_tracker.get_progress(execution_id)

        # Add execution ID to results
        results['execution_id'] = execution_id

        api_logger.info(f"Execution {execution_id} completed. "
                       f"Success: {results['completed_tasks']}, "
                       f"Failed: {results['failed_tasks']}, "
                       f"Time: {results['execution_time']:.2f}s")

        return results
    
    def get_execution_progress(self, execution_id: str) -> TestProgress:
        """Get the progress of a specific execution"""
        return self.progress_tracker.get_progress(execution_id)
    
    def get_all_executions(self) -> List[TestProgress]:
        """Get all tracked executions"""
        return self.progress_tracker.get_all_executions()
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an ongoing execution (currently just marks as failed)"""
        # In a real implementation, this would interrupt the actual threads/processes
        # For now, we'll just update the status
        progress = self.progress_tracker.get_progress(execution_id)
        if progress:
            # Update all remaining tests as failed
            remaining = progress.total_tests - progress.completed_tests - progress.failed_tests
            if remaining > 0:
                self.progress_tracker.update_failed(execution_id, "Execution cancelled", remaining)
            
            api_logger.info(f"Cancelled execution {execution_id}")
            return True
        return False
    
    def shutdown(self):
        """Shutdown the executor and cleanup resources"""
        self.scheduler.shutdown()
        api_logger.info("TestExecutor shut down successfully")


# Example usage function
def run_brand_cognition_test(
    brand_name: str,
    ai_models: List[Dict[str, str]],
    questions: List[str],
    api_key: str = "",
    max_workers: int = 3  # Reduced from 10 to 3 to prevent API timeouts
) -> Dict[str, Any]:
    """
    Convenience function to run a complete brand cognition test

    Args:
        brand_name: Name of the brand to test
        ai_models: List of AI model configurations
        questions: List of questions to ask
        api_key: API key for AI platforms
        max_workers: Maximum number of concurrent workers (reduced to 3 to prevent API timeouts)

    Returns:
        Dict with test results
    """
    from question_system import TestCaseGenerator

    # Generate test cases
    generator = TestCaseGenerator()
    test_cases = generator.generate_test_cases(brand_name, ai_models, questions)

    # Create executor and run tests
    executor = TestExecutor(max_workers=max_workers)

    def progress_callback(execution_id, progress):
        api_logger.info(f"Execution {execution_id} progress: {progress.progress_percentage:.1f}%")

    results = executor.execute_tests(test_cases, api_key, progress_callback)

    # Shutdown executor
    executor.shutdown()

    return results