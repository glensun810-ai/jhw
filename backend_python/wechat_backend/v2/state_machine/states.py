"""
诊断状态枚举

定义诊断任务的所有可能状态，严格按照重构基线中的状态定义。

状态说明:
- INITIALIZING: 任务初始化中（数据库记录创建）
- AI_FETCHING: AI 调用进行中（执行 NxM 测试）
- ANALYZING: 数据分析中（统计计算）
- COMPLETED: 任务成功完成（终态）
- PARTIAL_SUCCESS: 部分成功（终态）
- FAILED: 任务失败（终态）
- TIMEOUT: 任务超时（终态）
"""

from enum import Enum


class DiagnosisState(Enum):
    """诊断状态枚举
    
    所有状态分为两类:
    1. 中间状态 (intermediate states): INITIALIZING, AI_FETCHING, ANALYZING
    2. 终态 (terminal states): COMPLETED, PARTIAL_SUCCESS, FAILED, TIMEOUT
    
    Attributes:
        value: 状态值（字符串，与数据库存储一致）
        is_terminal: 是否为终态
        should_stop_polling: 是否应该停止轮询
    """
    
    # 中间状态
    INITIALIZING = 'initializing'  # 任务初始化中
    AI_FETCHING = 'ai_fetching'    # AI 调用进行中
    ANALYZING = 'analyzing'        # 数据分析中
    
    # 终态
    COMPLETED = 'completed'        # 任务成功完成
    PARTIAL_SUCCESS = 'partial_success'  # 部分成功
    FAILED = 'failed'              # 任务失败
    TIMEOUT = 'timeout'            # 任务超时
    
    @property
    def is_terminal(self) -> bool:
        """
        判断是否为终态
        
        Returns:
            bool: True 表示终态，False 表示中间状态
        """
        return self in [
            DiagnosisState.COMPLETED,
            DiagnosisState.PARTIAL_SUCCESS,
            DiagnosisState.FAILED,
            DiagnosisState.TIMEOUT,
        ]
    
    @property
    def should_stop_polling(self) -> bool:
        """
        判断是否应该停止轮询
        
        终态都应该停止轮询。
        
        Returns:
            bool: True 表示应该停止轮询
        """
        return self.is_terminal
    
    @property
    def is_completed(self) -> bool:
        """
        判断是否视为"完成"（包含成功和部分成功）
        
        Returns:
            bool: True 表示完成
        """
        return self in [
            DiagnosisState.COMPLETED,
            DiagnosisState.PARTIAL_SUCCESS,
        ]
