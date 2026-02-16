#!/usr/bin/env python3
"""
优化进度跟踪系统，实现智能轮询和资源管理
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class OptimizedProgressTracker:
    """
    优化的进度跟踪器
    - 实现智能轮询策略
    - 添加超时控制
    - 优化资源管理
    """
    
    def __init__(self, max_poll_interval: int = 10, timeout_seconds: int = 1800):  # 30分钟超时
        self.execution_store: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.max_poll_interval = max_poll_interval
        self.timeout_seconds = timeout_seconds

    def create_execution(self, execution_id: str, total_tests: int, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建新的执行记录"""
        with self.lock:
            self.execution_store[execution_id] = {
                'progress': 0,
                'completed': 0,
                'total': total_tests,
                'status': ExecutionStatus.PENDING.value,
                'results': [],
                'start_time': datetime.now().isoformat(),
                'last_update': time.time(),
                'poll_count': 0,
                'metadata': metadata or {},
                'should_stop_polling': False
            }
            return self.execution_store[execution_id]

    def update_progress(self, execution_id: str, progress_data: Dict[str, Any]) -> bool:
        """更新进度"""
        with self.lock:
            if execution_id in self.execution_store:
                current = self.execution_store[execution_id]
                current.update(progress_data)
                current['last_update'] = time.time()
                
                # 检查是否完成或失败，如果是则设置停止轮询标志
                if current['status'] in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value, ExecutionStatus.TIMEOUT.value]:
                    current['should_stop_polling'] = True
                
                return True
            return False

    def get_progress(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取进度信息，包含智能轮询建议"""
        with self.lock:
            if execution_id not in self.execution_store:
                return None
            
            current = self.execution_store[execution_id]
            
            # 检查是否超时
            elapsed = time.time() - datetime.fromisoformat(current['start_time']).timestamp()
            if elapsed > self.timeout_seconds and current['status'] == ExecutionStatus.PROCESSING.value:
                current['status'] = ExecutionStatus.TIMEOUT.value
                current['should_stop_polling'] = True
                current['error'] = f"Execution timed out after {self.timeout_seconds} seconds"
            
            # 计算建议的轮询间隔
            poll_count = current.get('poll_count', 0)
            suggested_interval = self._calculate_poll_interval(poll_count)
            
            # 更新轮询计数
            current['poll_count'] = poll_count + 1
            
            # 添加轮询建议
            current['suggested_next_poll_seconds'] = suggested_interval
            current['time_elapsed'] = elapsed
            
            return current.copy()

    def _calculate_poll_interval(self, poll_count: int) -> int:
        """计算建议的轮询间隔（智能轮询策略）"""
        if poll_count <= 5:
            return 2  # 前5次每2秒轮询
        elif poll_count <= 15:
            return 3  # 接下来每3秒轮询
        elif poll_count <= 30:
            return 5  # 再接下来每5秒轮询
        else:
            return min(10, self.max_poll_interval)  # 最大不超过10秒

    def complete_execution(self, execution_id: str, final_results: Dict[str, Any]) -> bool:
        """完成执行"""
        with self.lock:
            if execution_id in self.execution_store:
                current = self.execution_store[execution_id]
                current.update(final_results)
                current['status'] = ExecutionStatus.COMPLETED.value
                current['should_stop_polling'] = True
                current['completion_time'] = datetime.now().isoformat()
                return True
            return False

    def fail_execution(self, execution_id: str, error_message: str) -> bool:
        """标记执行失败"""
        with self.lock:
            if execution_id in self.execution_store:
                current = self.execution_store[execution_id]
                current['status'] = ExecutionStatus.FAILED.value
                current['error'] = error_message
                current['should_stop_polling'] = True
                current['completion_time'] = datetime.now().isoformat()
                return True
            return False

    def cleanup_old_executions(self, max_age_seconds: int = 3600) -> int:  # 1小时
        """清理旧的执行记录"""
        with self.lock:
            current_time = time.time()
            to_remove = []
            
            for exec_id, data in self.execution_store.items():
                start_time = datetime.fromisoformat(data['start_time']).timestamp()
                if current_time - start_time > max_age_seconds:
                    to_remove.append(exec_id)
            
            for exec_id in to_remove:
                del self.execution_store[exec_id]
            
            return len(to_remove)


# 全局实例
optimized_progress_tracker = OptimizedProgressTracker()


def get_optimized_progress_tracker():
    """获取优化的进度跟踪器实例"""
    return optimized_progress_tracker