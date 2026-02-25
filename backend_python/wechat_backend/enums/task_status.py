"""
任务状态枚举定义

P2 优化：统一状态定义，避免魔法字符串
"""

from enum import Enum


class TaskStatus(Enum):
    """
    任务状态枚举
    
    定义诊断任务的所有可能状态
    """
    INITIALIZING = 'initializing'  # 初始化中
    AI_FETCHING = 'ai_fetching'    # AI 调用中
    ANALYZING = 'analyzing'        # 分析中
    COMPLETED = 'completed'        # 已完成
    PARTIAL_COMPLETED = 'partial_completed'  # 部分完成
    FAILED = 'failed'              # 失败


class TaskStage(Enum):
    """
    任务阶段枚举
    
    与 TaskStatus 一一对应，用于前端展示
    """
    INIT = 'init'                          # 初始化
    AI_FETCHING = 'ai_fetching'           # AI 调用中
    ANALYZING = 'analyzing'               # 分析中
    COMPLETED = 'completed'               # 已完成
    FAILED = 'failed'                     # 失败


# 状态与阶段的映射关系
STATUS_STAGE_MAP = {
    TaskStatus.INITIALIZING: TaskStage.INIT,
    TaskStatus.AI_FETCHING: TaskStage.AI_FETCHING,
    TaskStatus.ANALYZING: TaskStage.ANALYZING,
    TaskStatus.COMPLETED: TaskStage.COMPLETED,
    TaskStatus.PARTIAL_COMPLETED: TaskStage.COMPLETED,  # 部分完成也视为完成
    TaskStatus.FAILED: TaskStage.FAILED,
}

# 阶段与状态的映射关系（反向）
STAGE_STATUS_MAP = {
    TaskStage.INIT: TaskStatus.INITIALIZING,
    TaskStage.AI_FETCHING: TaskStatus.AI_FETCHING,
    TaskStage.ANALYZING: TaskStatus.ANALYZING,
    TaskStage.COMPLETED: TaskStatus.COMPLETED,
    TaskStage.FAILED: TaskStatus.FAILED,
}

# 状态与进度的映射关系
STATUS_PROGRESS_MAP = {
    TaskStatus.INITIALIZING: 0,
    TaskStatus.AI_FETCHING: 50,
    TaskStatus.ANALYZING: 80,
    TaskStatus.COMPLETED: 100,
    TaskStatus.PARTIAL_COMPLETED: 100,
    TaskStatus.FAILED: 0,
}

# 状态展示文本（中文）
STATUS_DISPLAY_TEXT = {
    TaskStatus.INITIALIZING: '正在初始化',
    TaskStatus.AI_FETCHING: '正在连接 AI 平台',
    TaskStatus.ANALYZING: '正在分析数据',
    TaskStatus.COMPLETED: '诊断完成',
    TaskStatus.PARTIAL_COMPLETED: '诊断部分完成',
    TaskStatus.FAILED: '诊断失败',
}

# 前端轮询终止状态（这些状态表示任务结束，无需继续轮询）
TERMINAL_STATUSES = [
    TaskStatus.COMPLETED,
    TaskStatus.PARTIAL_COMPLETED,
]

# 前端需要特殊处理的失败状态
FAILED_STATUSES = [
    TaskStatus.FAILED,
]


def get_stage_from_status(status: TaskStatus) -> TaskStage:
    """
    根据状态获取阶段
    
    Args:
        status: 任务状态
    
    Returns:
        对应的任务阶段
    """
    return STATUS_STAGE_MAP.get(status, TaskStage.FAILED)


def get_status_from_stage(stage: TaskStage) -> TaskStatus:
    """
    根据阶段获取状态
    
    Args:
        stage: 任务阶段
    
    Returns:
        对应的任务状态
    """
    return STAGE_STATUS_MAP.get(stage, TaskStatus.FAILED)


def get_progress_from_status(status: TaskStatus) -> int:
    """
    根据状态获取默认进度
    
    Args:
        status: 任务状态
    
    Returns:
        默认进度值（0-100）
    """
    return STATUS_PROGRESS_MAP.get(status, 0)


def get_display_text(status: TaskStatus) -> str:
    """
    获取状态的展示文本
    
    Args:
        status: 任务状态
    
    Returns:
        中文展示文本
    """
    return STATUS_DISPLAY_TEXT.get(status, '未知状态')


def is_terminal_status(status: TaskStatus) -> bool:
    """
    判断是否为终止状态
    
    Args:
        status: 任务状态
    
    Returns:
        是否为终止状态
    """
    return status in TERMINAL_STATUSES


def is_failed_status(status: TaskStatus) -> bool:
    """
    判断是否为失败状态
    
    Args:
        status: 任务状态
    
    Returns:
        是否为失败状态
    """
    return status in FAILED_STATUSES


def parse_status(status_str: str) -> TaskStatus:
    """
    解析状态字符串为枚举
    
    Args:
        status_str: 状态字符串
    
    Returns:
        TaskStatus 枚举值
    """
    try:
        return TaskStatus(status_str)
    except ValueError:
        # 兼容旧数据
        status_map = {
            'running': TaskStatus.AI_FETCHING,
            'processing': TaskStatus.AI_FETCHING,
            'done': TaskStatus.COMPLETED,
            'finished': TaskStatus.COMPLETED,
        }
        return status_map.get(status_str, TaskStatus.FAILED)


def parse_stage(stage_str: str) -> TaskStage:
    """
    解析阶段字符串为枚举
    
    Args:
        stage_str: 阶段字符串
    
    Returns:
        TaskStage 枚举值
    """
    try:
        return TaskStage(stage_str)
    except ValueError:
        # 兼容旧数据
        stage_map = {
            'running': TaskStage.AI_FETCHING,
            'processing': TaskStage.AI_FETCHING,
            'done': TaskStage.COMPLETED,
            'finished': TaskStage.COMPLETED,
        }
        return stage_map.get(stage_str, TaskStage.FAILED)
