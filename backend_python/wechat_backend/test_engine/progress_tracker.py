"""
Progress tracker for test execution
Manages the status and progress of test executions
"""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
import uuid
from ..logging_config import api_logger


class TestStatus(Enum):
    """Status of a test execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PARTIAL = "partial"  # For tests that partially completed


@dataclass
class TestProgress:
    """Represents the progress of a test execution"""
    execution_id: str
    total_tests: int
    completed_tests: int = 0
    failed_tests: int = 0
    running_tests: int = 0
    status: TestStatus = TestStatus.PENDING
    start_time: datetime = None
    end_time: datetime = None
    progress_percentage: float = 0.0
    results: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.results is None:
            self.results = []
        if self.metadata is None:
            self.metadata = {}


class ProgressTracker:
    """Tracks progress of test executions"""
    
    def __init__(self):
        self.executions: Dict[str, TestProgress] = {}
        self.lock = threading.Lock()
        api_logger.info("Initialized ProgressTracker")
    
    def create_execution(self, execution_id: str, total_tests: int, metadata: Dict[str, Any] = None) -> TestProgress:
        """Create a new test execution tracking record"""
        with self.lock:
            progress = TestProgress(
                execution_id=execution_id,
                total_tests=total_tests,
                metadata=metadata or {}
            )
            self.executions[execution_id] = progress
            api_logger.info(f"Created execution tracking for {execution_id} with {total_tests} tests")
            return progress
    
    def update_running(self, execution_id: str, increment: int = 1) -> TestProgress:
        """Update the number of running tests"""
        with self.lock:
            if execution_id not in self.executions:
                raise ValueError(f"Execution {execution_id} not found")
            
            execution = self.executions[execution_id]
            execution.running_tests += increment
            execution.status = TestStatus.RUNNING
            
            # Calculate progress percentage
            completed_or_failed = execution.completed_tests + execution.failed_tests
            execution.progress_percentage = (completed_or_failed / execution.total_tests) * 100.0
            
            api_logger.debug(f"Updated running tests for {execution_id}: {execution.running_tests} running")
            return execution
    
    def update_completed(self, execution_id: str, result: Dict[str, Any] = None, increment: int = 1) -> TestProgress:
        """Update the number of completed tests"""
        with self.lock:
            if execution_id not in self.executions:
                raise ValueError(f"Execution {execution_id} not found")
            
            execution = self.executions[execution_id]
            execution.completed_tests += increment
            execution.running_tests = max(0, execution.running_tests - increment)
            
            # Add result if provided
            if result:
                execution.results.append(result)
            
            # Calculate progress percentage
            completed_or_failed = execution.completed_tests + execution.failed_tests
            execution.progress_percentage = (completed_or_failed / execution.total_tests) * 100.0
            
            # Update status based on completion
            if execution.completed_tests + execution.failed_tests >= execution.total_tests:
                if execution.failed_tests == 0:
                    execution.status = TestStatus.COMPLETED
                    execution.end_time = datetime.now()
                elif execution.failed_tests > 0 and execution.completed_tests > 0:
                    execution.status = TestStatus.PARTIAL
                    execution.end_time = datetime.now()
                else:
                    execution.status = TestStatus.FAILED
                    execution.end_time = datetime.now()
            else:
                execution.status = TestStatus.RUNNING
            
            api_logger.info(f"Updated completed tests for {execution_id}: {execution.completed_tests}/{execution.total_tests} ({execution.progress_percentage:.1f}%)")
            return execution
    
    def update_failed(self, execution_id: str, error: str = None, increment: int = 1) -> TestProgress:
        """Update the number of failed tests"""
        with self.lock:
            if execution_id not in self.executions:
                raise ValueError(f"Execution {execution_id} not found")
            
            execution = self.executions[execution_id]
            execution.failed_tests += increment
            execution.running_tests = max(0, execution.running_tests - increment)
            
            # Calculate progress percentage
            completed_or_failed = execution.completed_tests + execution.failed_tests
            execution.progress_percentage = (completed_or_failed / execution.total_tests) * 100.0
            
            # Update status based on completion
            if execution.completed_tests + execution.failed_tests >= execution.total_tests:
                if execution.failed_tests == 0:
                    execution.status = TestStatus.COMPLETED
                    execution.end_time = datetime.now()
                elif execution.failed_tests > 0 and execution.completed_tests > 0:
                    execution.status = TestStatus.PARTIAL
                    execution.end_time = datetime.now()
                else:
                    execution.status = TestStatus.FAILED
                    execution.end_time = datetime.now()
            else:
                execution.status = TestStatus.RUNNING
            
            api_logger.warning(f"Updated failed tests for {execution_id}: {execution.failed_tests} failed, {execution.progress_percentage:.1f}% complete")
            return execution
    
    def get_progress(self, execution_id: str) -> Optional[TestProgress]:
        """Get the progress of a specific execution"""
        with self.lock:
            return self.executions.get(execution_id)
    
    def get_all_executions(self) -> List[TestProgress]:
        """Get all tracked executions"""
        with self.lock:
            return list(self.executions.values())
    
    def remove_execution(self, execution_id: str) -> bool:
        """Remove an execution from tracking"""
        with self.lock:
            if execution_id in self.executions:
                del self.executions[execution_id]
                api_logger.info(f"Removed execution tracking for {execution_id}")
                return True
            return False
    
    def reset_execution(self, execution_id: str) -> bool:
        """Reset an execution to initial state"""
        with self.lock:
            if execution_id not in self.executions:
                return False
            
            execution = self.executions[execution_id]
            execution.completed_tests = 0
            execution.failed_tests = 0
            execution.running_tests = 0
            execution.status = TestStatus.PENDING
            execution.progress_percentage = 0.0
            execution.results = []
            execution.start_time = datetime.now()
            execution.end_time = None
            
            api_logger.info(f"Reset execution {execution_id} to initial state")
            return True
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all executions"""
        with self.lock:
            total_executions = len(self.executions)
            status_counts = {}
            
            for execution in self.executions.values():
                status = execution.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                'total_executions': total_executions,
                'status_breakdown': status_counts,
                'executions': [self._execution_to_dict(ex) for ex in self.executions.values()]
            }
    
    def _execution_to_dict(self, execution: TestProgress) -> Dict[str, Any]:
        """Convert execution to dictionary for serialization"""
        return {
            'execution_id': execution.execution_id,
            'total_tests': execution.total_tests,
            'completed_tests': execution.completed_tests,
            'failed_tests': execution.failed_tests,
            'running_tests': execution.running_tests,
            'status': execution.status.value,
            'progress_percentage': execution.progress_percentage,
            'start_time': execution.start_time.isoformat() if execution.start_time else None,
            'end_time': execution.end_time.isoformat() if execution.end_time else None,
            'metadata': execution.metadata
        }