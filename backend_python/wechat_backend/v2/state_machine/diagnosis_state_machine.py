"""
诊断任务状态机核心实现

核心原则:
1. 状态流转必须明确定义
2. 所有状态变更必须持久化
3. 终态不可逆转
4. 进度与状态同步更新

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

from datetime import datetime
from typing import Dict, Any, Optional, Set
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.state_machine.states import DiagnosisState
from wechat_backend.v2.exceptions import DiagnosisStateError, DatabaseError


class DiagnosisStateMachine:
    """
    诊断任务状态机
    
    职责:
    1. 管理诊断任务的状态流转
    2. 跟踪任务进度 (0-100)
    3. 持久化状态到数据库
    4. 提供状态查询接口
    
    状态流转图:
        INITIALIZING -> AI_FETCHING -> ANALYZING -> COMPLETED
                          |              |
                          |              +-> PARTIAL_SUCCESS
                          |              |
                          |              +-> FAILED
                          |
                          +-> all_fail -> FAILED
                          +-> timeout -> TIMEOUT
    
    使用示例:
        >>> state_machine = DiagnosisStateMachine('execution-123')
        >>> state_machine.transition('succeed', progress=10)
        True
        >>> state_machine.get_current_state()
        <DiagnosisState.AI_FETCHING: 'ai_fetching'>
        >>> state_machine.get_progress()
        10
    """
    
    # ==================== 状态流转定义 ====================
    
    # 状态流转表：当前状态 -> {事件 -> 下一状态}
    TRANSITIONS: Dict[DiagnosisState, Dict[str, DiagnosisState]] = {
        # INITIALIZING 状态
        DiagnosisState.INITIALIZING: {
            'succeed': DiagnosisState.AI_FETCHING,      # 数据库记录创建成功
            'fail': DiagnosisState.FAILED,               # 创建失败
        },
        
        # AI_FETCHING 状态
        DiagnosisState.AI_FETCHING: {
            'all_complete': DiagnosisState.ANALYZING,    # 所有 AI 调用完成
            'partial_complete': DiagnosisState.ANALYZING, # 部分 AI 调用完成
            'all_fail': DiagnosisState.FAILED,           # 所有调用失败
            'timeout': DiagnosisState.TIMEOUT,           # 超时
        },
        
        # ANALYZING 状态
        DiagnosisState.ANALYZING: {
            'succeed': DiagnosisState.COMPLETED,         # 分析完成
            'partial_succeed': DiagnosisState.PARTIAL_SUCCESS,  # 部分分析完成
            'fail': DiagnosisState.FAILED,               # 分析失败
        },
        
        # 终态：无流转
        DiagnosisState.COMPLETED: {},
        DiagnosisState.PARTIAL_SUCCESS: {},
        DiagnosisState.FAILED: {},
        DiagnosisState.TIMEOUT: {},
    }
    
    def __init__(
        self,
        execution_id: str,
        repository: Optional[Any] = None,
    ):
        """
        初始化状态机
        
        Args:
            execution_id: 执行 ID（任务唯一标识）
            repository: 数据仓库实例（用于持久化，可选）
        
        Raises:
            DiagnosisValidationError: execution_id 为空
        """
        if not execution_id or not isinstance(execution_id, str):
            raise ValueError("execution_id 必须是非空字符串")
        
        self._execution_id: str = execution_id
        self._current_state: DiagnosisState = DiagnosisState.INITIALIZING
        self._progress: int = 0
        self._metadata: Dict[str, Any] = {}
        self._repository = repository
        
        api_logger.info(
            "state_machine_initialized",
            extra={
                'event': 'state_machine_initialized',
                'execution_id': execution_id,
                'initial_state': self._current_state.value,
            }
        )
    
    @property
    def execution_id(self) -> str:
        """获取执行 ID"""
        return self._execution_id
    
    def get_current_state(self) -> DiagnosisState:
        """
        获取当前状态
        
        Returns:
            DiagnosisState: 当前状态
        """
        return self._current_state
    
    def get_progress(self) -> int:
        """
        获取当前进度
        
        Returns:
            int: 进度值 (0-100)
        """
        return self._progress
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取元数据
        
        Returns:
            Dict[str, Any]: 元数据字典
        """
        return self._metadata.copy()
    
    def should_stop_polling(self) -> bool:
        """
        判断是否应该停止轮询
        
        当状态为终态时，应该停止轮询。
        
        Returns:
            bool: True 表示应该停止轮询
        """
        return self._current_state.should_stop_polling
    
    def is_terminal_state(self) -> bool:
        """
        判断是否为终态
        
        Returns:
            bool: True 表示终态
        """
        return self._current_state.is_terminal
    
    def transition(
        self,
        event: str,
        progress: Optional[int] = None,
        **kwargs: Any,
    ) -> bool:
        """
        执行状态流转

        Args:
            event: 触发事件（如 'succeed', 'fail', 'timeout' 等）
            progress: 新进度值 (0-100)，可选
            **kwargs: 其他元数据（如 error_message, results_count 等）

        Returns:
            bool: True 表示流转成功，False 表示流转失败（非法事件）

        Raises:
            DiagnosisStateError: 状态流转异常（如终态尝试流转）

        Example:
            >>> state_machine = DiagnosisStateMachine('exec-123')
            >>> state_machine.transition('succeed', progress=10)
            True
            >>> state_machine.transition('invalid_event')  # 非法事件
            False
        """
        # 1. 检查终态
        if self._is_terminal_state():
            return False

        # 2. 检查事件合法性
        allowed_transitions = self._get_allowed_transitions()
        if not self._is_valid_event(event, allowed_transitions):
            return False

        # 3. 执行状态流转
        old_state = self._current_state
        next_state = allowed_transitions[event]
        self._current_state = next_state

        # 4. 更新进度和元数据
        self._update_progress_if_provided(progress)
        self._update_metadata(event, kwargs)

        # 5. 持久化状态
        self.persist_state()

        return True

    def _is_terminal_state(self) -> bool:
        """
        检查是否为终态

        Returns:
            bool: True 表示终态
        """
        if self._current_state.is_terminal:
            api_logger.warning(
                "state_machine_terminal_state_transition_attempt",
                extra={
                    'event': 'state_machine_terminal_state_transition_attempt',
                    'execution_id': self._execution_id,
                    'current_state': self._current_state.value,
                    'attempted_event': 'transition',
                }
            )
            return True
        return False

    def _get_allowed_transitions(
        self,
    ) -> Dict[str, 'DiagnosisState']:
        """
        获取当前状态允许的流转

        Returns:
            Dict[str, DiagnosisState]: 允许的流转字典
        """
        return self.TRANSITIONS.get(self._current_state, {})

    def _is_valid_event(
        self,
        event: str,
        allowed_transitions: Dict[str, 'DiagnosisState'],
    ) -> bool:
        """
        检查事件是否合法

        Args:
            event: 触发事件
            allowed_transitions: 允许的流转字典

        Returns:
            bool: True 表示事件合法
        """
        if event not in allowed_transitions:
            api_logger.warning(
                "state_machine_invalid_transition",
                extra={
                    'event': 'state_machine_invalid_transition',
                    'execution_id': self._execution_id,
                    'current_state': self._current_state.value,
                    'attempted_event': event,
                    'allowed_events': list(allowed_transitions.keys()),
                }
            )
            return False
        return True

    def _update_progress_if_provided(
        self,
        progress: Optional[int],
    ) -> None:
        """
        更新进度（如果提供）

        Args:
            progress: 新进度值
        """
        if progress is not None:
            self._progress = self._validate_progress(progress)

        if self._current_state == DiagnosisState.COMPLETED:
            self._progress = 100

    def _update_metadata(
        self,
        event: str,
        kwargs: Dict[str, Any],
    ) -> None:
        """
        更新元数据

        Args:
            event: 触发事件
            kwargs: 其他元数据
        """
        self._metadata.update(kwargs)
        self._metadata['last_event'] = event
        self._metadata['last_transition_time'] = datetime.now().isoformat()

        api_logger.info(
            "state_machine_transitioned",
            extra={
                'event': 'state_machine_transitioned',
                'execution_id': self._execution_id,
                'old_state': self._current_state.value,
                'new_state': self._current_state.value,
                'trigger_event': event,
                'progress': self._progress,
                'is_terminal': self._current_state.is_terminal,
            }
        )
    
    def _validate_progress(self, progress: int) -> int:
        """
        验证进度值
        
        Args:
            progress: 进度值
        
        Returns:
            int: 验证后的进度值 (0-100)
        
        Raises:
            ValueError: 进度值超出范围
        """
        if not isinstance(progress, int):
            raise ValueError(f"进度必须是整数，得到：{type(progress)}")
        
        if progress < 0 or progress > 100:
            raise ValueError(f"进度必须在 0-100 之间，得到：{progress}")
        
        # 进度只能增加，不能减少（除非重置）
        if progress < self._progress:
            api_logger.warning(
                "state_machine_progress_decreased",
                extra={
                    'event': 'state_machine_progress_decreased',
                    'execution_id': self._execution_id,
                    'old_progress': self._progress,
                    'new_progress': progress,
                }
            )
        
        return progress
    
    def update_progress(self, progress: int) -> None:
        """
        更新进度（不改变状态）
        
        Args:
            progress: 新进度值 (0-100)
        
        Raises:
            ValueError: 进度值超出范围
        """
        self._progress = self._validate_progress(progress)
        
        api_logger.debug(
            "state_machine_progress_updated",
            extra={
                'event': 'state_machine_progress_updated',
                'execution_id': self._execution_id,
                'progress': self._progress,
                'state': self._current_state.value,
            }
        )
        
        # 持久化进度
        self.persist_state()
    
    def persist_state(self) -> None:
        """
        持久化状态到数据库
        
        更新 diagnosis_reports 表的以下字段:
        - status: 状态值
        - stage: 与 status 保持一致
        - progress: 当前进度
        - is_completed: 是否完成
        - should_stop_polling: 是否停止轮询
        - updated_at: 更新时间
        
        Raises:
            DatabaseError: 数据库操作失败
        """
        if self._repository is None:
            api_logger.warning(
                "state_machine_no_repository",
                extra={
                    'event': 'state_machine_no_repository',
                    'execution_id': self._execution_id,
                }
            )
            return
        
        try:
            # 调用仓库层更新状态
            self._repository.update_state(
                execution_id=self._execution_id,
                status=self._current_state.value,
                stage=self._current_state.value,  # stage 与 status 保持一致
                progress=self._progress,
                is_completed=self._current_state.is_completed,
                should_stop_polling=self._current_state.should_stop_polling,
                metadata=self._metadata,
            )
            
            api_logger.info(
                "state_machine_persisted",
                extra={
                    'event': 'state_machine_persisted',
                    'execution_id': self._execution_id,
                    'status': self._current_state.value,
                    'progress': self._progress,
                    'is_completed': self._current_state.is_completed,
                    'should_stop_polling': self._current_state.should_stop_polling,
                }
            )
            
        except Exception as e:
            api_logger.error(
                "state_machine_persist_failed",
                extra={
                    'event': 'state_machine_persist_failed',
                    'execution_id': self._execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DatabaseError(
                f"状态持久化失败：{e}",
                operation='update_state',
                original_error=str(e),
            ) from e
    
    def reset(self) -> None:
        """
        重置状态机到初始状态
        
        注意：这会清除所有状态和进度，谨慎使用。
        """
        old_state = self._current_state
        self._current_state = DiagnosisState.INITIALIZING
        self._progress = 0
        self._metadata = {}
        
        api_logger.info(
            "state_machine_reset",
            extra={
                'event': 'state_machine_reset',
                'execution_id': self._execution_id,
                'old_state': old_state.value,
            }
        )
        
        self.persist_state()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将状态机状态转换为字典
        
        Returns:
            Dict[str, Any]: 状态字典
        """
        return {
            'execution_id': self._execution_id,
            'status': self._current_state.value,
            'stage': self._current_state.value,
            'progress': self._progress,
            'is_completed': self._current_state.is_completed,
            'should_stop_polling': self._current_state.should_stop_polling,
            'is_terminal': self._current_state.is_terminal,
            'metadata': self._metadata.copy(),
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"DiagnosisStateMachine("
            f"execution_id={self._execution_id}, "
            f"state={self._current_state.value}, "
            f"progress={self._progress}"
            f")"
        )
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"DiagnosisStateMachine(execution_id='{self._execution_id}', "
            f"state=DiagnosisState.{self._current_state.name}, "
            f"progress={self._progress})"
        )
