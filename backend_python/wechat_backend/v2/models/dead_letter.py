"""
死信队列数据模型

用于存储和管理无法自动恢复的失败任务。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class DeadLetter:
    """
    死信数据模型
    
    Attributes:
        execution_id: 任务执行 ID
        task_type: 任务类型（ai_call, analysis, report_generation）
        status: 状态（pending, processing, resolved, ignored）
        priority: 优先级（0-10，越高越优先）
        error_type: 错误类型
        error_message: 错误信息
        error_stack: 完整堆栈跟踪
        task_context: 任务上下文（原始参数）
        retry_count: 已重试次数
        max_retries: 最大重试次数
        failed_at: 首次失败时间
        last_retry_at: 最后重试时间
        resolved_at: 解决时间
        handled_by: 处理人
        resolution_notes: 处理说明
        id: 数据库记录 ID
    """
    
    # 基本信息
    execution_id: str
    task_type: str
    status: str = 'pending'
    priority: int = 0
    
    # 失败信息
    error_type: str = ''
    error_message: str = ''
    error_stack: Optional[str] = None
    
    # 任务上下文
    task_context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    
    # 时间信息
    failed_at: Optional[datetime] = None
    last_retry_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # 处理信息
    handled_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    
    # 数据库 ID
    id: Optional[int] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.failed_at is None:
            self.failed_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于 API 响应）
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'task_type': self.task_type,
            'status': self.status,
            'priority': self.priority,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'error_stack': self.error_stack,
            'task_context': self.task_context,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'last_retry_at': self.last_retry_at.isoformat() if self.last_retry_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'handled_by': self.handled_by,
            'resolution_notes': self.resolution_notes,
        }
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'DeadLetter':
        """
        从数据库行记录创建对象
        
        Args:
            row: 数据库行记录
        
        Returns:
            DeadLetter: 死信对象
        """
        return cls(
            id=row['id'],
            execution_id=row['execution_id'],
            task_type=row['task_type'],
            status=row['status'],
            priority=row['priority'],
            error_type=row['error_type'],
            error_message=row['error_message'],
            error_stack=row['error_stack'],
            task_context=json.loads(row['task_context']) if row['task_context'] else {},
            retry_count=row['retry_count'],
            max_retries=row['max_retries'],
            failed_at=datetime.fromisoformat(row['failed_at']) if row['failed_at'] else None,
            last_retry_at=datetime.fromisoformat(row['last_retry_at']) if row['last_retry_at'] else None,
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None,
            handled_by=row['handled_by'],
            resolution_notes=row['resolution_notes'],
        )
