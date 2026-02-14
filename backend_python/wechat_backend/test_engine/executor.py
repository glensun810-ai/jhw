"""
Test Executor - Main entry point for test execution
Integrates scheduler, progress tracking, and AI adapters
"""
from typing import List, Dict, Any, Callable
from datetime import datetime
import uuid
from ..ai_adapters import AIAdapterFactory
from ..question_system import TestCase
from .scheduler import TestScheduler, TestTask, ExecutionStrategy
from .progress_tracker import ProgressTracker, TestProgress
from ..logging_config import api_logger


class TestExecutor:
    """Main executor that coordinates test execution with progress tracking"""

    def __init__(self, max_workers: int = 3, strategy: ExecutionStrategy = ExecutionStrategy.CONCURRENT):
        """
        Initialize the test executor

        Args:
            max_workers: Maximum number of concurrent workers (reduced to 3 to prevent API timeouts)
            strategy: Execution strategy to use
        """
        self.scheduler = TestScheduler(max_workers=max_workers, strategy=strategy)
        self.progress_tracker = ProgressTracker()
        self.ai_adapter_factory = AIAdapterFactory

        api_logger.warning(f"Initialized TestExecutor with strategy {strategy.value}, max_workers {max_workers} - REDUCED CONCURRENCY TO PREVENT TIMEOUT")
    
    def execute_tests(
        self,
        test_cases: List[TestCase],
        api_key: str = "",
        on_progress_update: Callable[[str, TestProgress], None] = None,
        timeout: int = 300  # 5分钟默认超时
    ) -> Dict[str, Any]:
        """
        Execute a list of test cases with progress tracking
        
        Args:
            test_cases: List of test cases to execute
            api_key: API key for AI platforms
            on_progress_update: Callback function to call when progress updates
            
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
        
        # Define callback for progress updates
        def progress_callback(task: TestTask, result: Dict[str, Any]):
            if result.get('success', False):
                self.progress_tracker.update_completed(execution_id, result)
            else:
                self.progress_tracker.update_failed(execution_id, result.get('error', 'Unknown error'))
            
            # Call the external progress update callback if provided
            current_progress = self.progress_tracker.get_progress(execution_id)
            if on_progress_update:
                on_progress_update(execution_id, current_progress)
        
        import threading
        import concurrent.futures
        from functools import partial

        # Execute the tests with timeout using ThreadPoolExecutor
        if timeout > 0:
            # Create a partial function with the arguments
            execute_func = partial(self.scheduler.schedule_tests, test_tasks, progress_callback)

            # Use ThreadPoolExecutor with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(execute_func)
                try:
                    results = future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
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
    from ..question_system import TestCaseGenerator

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