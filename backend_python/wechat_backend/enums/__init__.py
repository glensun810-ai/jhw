"""
枚举类型包

P2 优化：统一状态定义
"""

from .task_status import (
    TaskStatus,
    TaskStage,
    STATUS_STAGE_MAP,
    STAGE_STATUS_MAP,
    STATUS_PROGRESS_MAP,
    STATUS_DISPLAY_TEXT,
    TERMINAL_STATUSES,
    FAILED_STATUSES,
    get_stage_from_status,
    get_status_from_stage,
    get_progress_from_status,
    get_display_text,
    is_terminal_status,
    is_failed_status,
    parse_status,
    parse_stage,
)

__all__ = [
    'TaskStatus',
    'TaskStage',
    'STATUS_STAGE_MAP',
    'STAGE_STATUS_MAP',
    'STATUS_PROGRESS_MAP',
    'STATUS_DISPLAY_TEXT',
    'TERMINAL_STATUSES',
    'FAILED_STATUSES',
    'get_stage_from_status',
    'get_status_from_stage',
    'get_progress_from_status',
    'get_display_text',
    'is_terminal_status',
    'is_failed_status',
    'parse_status',
    'parse_stage',
]
