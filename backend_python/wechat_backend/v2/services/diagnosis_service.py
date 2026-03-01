"""
诊断服务

诊断任务的核心业务逻辑层，集成状态机、超时管理等功能。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import logging
from typing import Dict, Any, Optional
from wechat_backend.v2.state_machine.diagnosis_state_machine import DiagnosisStateMachine
from wechat_backend.v2.state_machine.states import DiagnosisState
from wechat_backend.v2.services.timeout_service import TimeoutManager
from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
from wechat_backend.logging_config import api_logger

logger = logging.getLogger(__name__)


class DiagnosisService:
    """
    诊断服务
    
    职责:
    1. 管理诊断任务的完整生命周期
    2. 集成超时保护机制
    3. 集成状态机管理
    4. 提供诊断任务启动、完成接口
    
    使用示例:
        >>> service = DiagnosisService()
        >>> service.start_diagnosis("exec-123", config)
        >>> service.complete_diagnosis("exec-123")
    """
    
    def __init__(self, repository: Optional[DiagnosisRepository] = None):
        """
        初始化诊断服务
        
        Args:
            repository: 数据仓库实例（可选，默认创建新实例）
        """
        self._repository = repository or DiagnosisRepository()
        self._timeout_manager = TimeoutManager()
        
        api_logger.info(
            "diagnosis_service_initialized",
            extra={
                'event': 'diagnosis_service_initialized',
                'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
            }
        )
    
    @property
    def timeout_manager(self) -> TimeoutManager:
        """获取超时管理器实例"""
        return self._timeout_manager
    
    def start_diagnosis(
        self,
        execution_id: str,
        config: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """
        启动诊断任务
        
        Args:
            execution_id: 任务执行 ID
            config: 诊断配置（品牌、模型、问题等）
            timeout_seconds: 超时时间（秒），默认使用 MAX_EXECUTION_TIME
            
        Raises:
            ValueError: 如果 execution_id 为空
            RuntimeError: 如果任务已存在
            
        Example:
            >>> service = DiagnosisService()
            >>> config = {
            ...     'brand_name': '品牌 A',
            ...     'selected_models': ['deepseek', 'doubao'],
            ... }
            >>> service.start_diagnosis("exec-123", config)
        """
        if not execution_id:
            raise ValueError("execution_id cannot be empty")
        
        api_logger.info(
            "diagnosis_started",
            extra={
                'event': 'diagnosis_started',
                'execution_id': execution_id,
                'brand_name': config.get('brand_name', 'unknown'),
                'model_count': len(config.get('selected_models', [])),
            }
        )
        
        # 1. 初始化状态机
        state_machine = DiagnosisStateMachine(
            execution_id=execution_id,
            repository=self._repository,
        )
        
        # 2. 启动超时计时器
        self._timeout_manager.start_timer(
            execution_id=execution_id,
            on_timeout=self._handle_timeout,
            timeout_seconds=timeout_seconds,
        )
        
        # 3. 状态流转到 AI_FETCHING
        state_machine.transition(
            event='succeed',
            progress=10,
            config=config,
        )
        
        api_logger.info(
            "diagnosis_start_completed",
            extra={
                'event': 'diagnosis_start_completed',
                'execution_id': execution_id,
                'state': state_machine.get_current_state().value,
                'progress': state_machine.get_progress(),
            }
        )
    
    def complete_diagnosis(
        self,
        execution_id: str,
        progress: int = 100,
    ) -> None:
        """
        完成诊断任务
        
        Args:
            execution_id: 任务执行 ID
            progress: 完成进度（默认 100）
            
        Example:
            >>> service.complete_diagnosis("exec-123")
        """
        api_logger.info(
            "diagnosis_completing",
            extra={
                'event': 'diagnosis_completing',
                'execution_id': execution_id,
            }
        )
        
        # 1. 取消超时计时器
        self._timeout_manager.cancel_timer(execution_id)
        
        # 2. 获取状态机并流转到 COMPLETED
        state_machine = DiagnosisStateMachine(
            execution_id=execution_id,
            repository=self._repository,
        )
        
        # 尝试流转到 COMPLETED
        state_machine.transition(
            event='succeed',
            progress=progress,
        )
        
        api_logger.info(
            "diagnosis_completed",
            extra={
                'event': 'diagnosis_completed',
                'execution_id': execution_id,
                'state': state_machine.get_current_state().value,
                'progress': state_machine.get_progress(),
            }
        )
    
    def fail_diagnosis(
        self,
        execution_id: str,
        error_message: str,
        progress: Optional[int] = None,
    ) -> None:
        """
        标记诊断任务为失败
        
        Args:
            execution_id: 任务执行 ID
            error_message: 错误信息
            progress: 当前进度（可选）
        """
        api_logger.info(
            "diagnosis_failing",
            extra={
                'event': 'diagnosis_failing',
                'execution_id': execution_id,
                'error_message': error_message,
            }
        )
        
        # 1. 取消超时计时器
        self._timeout_manager.cancel_timer(execution_id)
        
        # 2. 获取状态机并流转到 FAILED
        state_machine = DiagnosisStateMachine(
            execution_id=execution_id,
            repository=self._repository,
        )
        
        current_state = state_machine.get_current_state()
        
        # 根据当前状态选择合适的事件
        if current_state == DiagnosisState.INITIALIZING:
            event = 'fail'
        elif current_state == DiagnosisState.AI_FETCHING:
            event = 'all_fail'
        elif current_state == DiagnosisState.ANALYZING:
            event = 'fail'
        else:
            # 终态不需要再流转
            api_logger.warning(
                "diagnosis_already_terminal",
                extra={
                    'event': 'diagnosis_already_terminal',
                    'execution_id': execution_id,
                    'current_state': current_state.value,
                }
            )
            return
        
        state_machine.transition(
            event=event,
            progress=progress or state_machine.get_progress(),
            error_message=error_message,
        )
        
        api_logger.info(
            "diagnosis_failed",
            extra={
                'event': 'diagnosis_failed',
                'execution_id': execution_id,
                'state': state_machine.get_current_state().value,
            }
        )
    
    def _handle_timeout(self, execution_id: str) -> None:
        """
        处理超时事件

        该方法会被 TimeoutManager 在超时时调用。

        Args:
            execution_id: 任务执行 ID
        """
        api_logger.warning(
            "diagnosis_timeout",
            extra={
                'event': 'diagnosis_timeout',
                'execution_id': execution_id,
                'timeout_seconds': TimeoutManager.MAX_EXECUTION_TIME,
            }
        )

        state_machine: Optional[DiagnosisStateMachine] = None
        try:
            state_machine = self._get_state_machine(execution_id)
            
            if self._is_terminal_state(state_machine, execution_id):
                return
            
            event = self._determine_timeout_event(state_machine)
            self._transition_timeout_state(
                state_machine=state_machine,
                execution_id=execution_id,
                event=event,
            )

        except Exception as e:
            self._log_timeout_error(
                execution_id=execution_id,
                error=e,
                state_machine=state_machine,
            )

    def _get_state_machine(
        self,
        execution_id: str,
    ) -> DiagnosisStateMachine:
        """
        获取状态机实例

        Args:
            execution_id: 任务执行 ID

        Returns:
            DiagnosisStateMachine: 状态机实例
        """
        return DiagnosisStateMachine(
            execution_id=execution_id,
            repository=self._repository,
        )

    def _is_terminal_state(
        self,
        state_machine: DiagnosisStateMachine,
        execution_id: str,
    ) -> bool:
        """
        检查是否为终态

        Args:
            state_machine: 状态机实例
            execution_id: 任务执行 ID

        Returns:
            bool: True 表示终态
        """
        current_state = state_machine.get_current_state()
        
        if current_state.is_terminal:
            api_logger.warning(
                "diagnosis_timeout_already_terminal",
                extra={
                    'event': 'diagnosis_timeout_already_terminal',
                    'execution_id': execution_id,
                    'current_state': current_state.value,
                }
            )
            return True
        return False

    def _determine_timeout_event(
        self,
        state_machine: DiagnosisStateMachine,
    ) -> str:
        """
        确定超时事件类型

        Args:
            state_machine: 状态机实例

        Returns:
            str: 事件名称 ('timeout' 或 'fail')
        """
        current_state = state_machine.get_current_state()
        
        if current_state == DiagnosisState.AI_FETCHING:
            return 'timeout'
        elif current_state == DiagnosisState.ANALYZING:
            return 'fail'
        else:
            return 'fail'

    def _transition_timeout_state(
        self,
        state_machine: DiagnosisStateMachine,
        execution_id: str,
        event: str,
    ) -> None:
        """
        执行超时状态流转

        Args:
            state_machine: 状态机实例
            execution_id: 任务执行 ID
            event: 事件名称
        """
        current_progress = state_machine.get_progress()
        
        state_machine.transition(
            event=event,
            progress=current_progress,
            error_message=f"诊断任务执行超时（>{TimeoutManager.MAX_EXECUTION_TIME}秒）",
        )

        api_logger.info(
            "diagnosis_timeout_handled",
            extra={
                'event': 'diagnosis_timeout_handled',
                'execution_id': execution_id,
                'progress': current_progress,
                'state': state_machine.get_current_state().value,
            }
        )

    def _log_timeout_error(
        self,
        execution_id: str,
        error: Exception,
        state_machine: Optional[DiagnosisStateMachine],
    ) -> None:
        """
        记录超时处理错误日志

        Args:
            execution_id: 任务执行 ID
            error: 异常对象
            state_machine: 状态机实例（可选）
        """
        state_value: Optional[str] = None
        progress_value: Optional[int] = None
        
        if state_machine is not None:
            try:
                state_value = state_machine.get_current_state().value
                progress_value = state_machine.get_progress()
            except Exception:
                state_value = 'unknown'
                progress_value = None

        api_logger.error(
            "diagnosis_timeout_handler_error",
            extra={
                'event': 'diagnosis_timeout_handler_error',
                'execution_id': execution_id,
                'error': str(error),
                'error_type': type(error).__name__,
                'state_machine_state': state_value,
                'state_machine_progress': progress_value,
            }
        )
    
    def get_diagnosis_state(self, execution_id: str) -> Dict[str, Any]:
        """
        获取诊断任务状态
        
        Args:
            execution_id: 任务执行 ID
            
        Returns:
            Dict[str, Any]: 状态字典
        """
        state_machine = DiagnosisStateMachine(
            execution_id=execution_id,
            repository=self._repository,
        )
        
        state_dict = state_machine.to_dict()
        state_dict['remaining_time'] = self._timeout_manager.get_remaining_time(execution_id)
        state_dict['is_timer_active'] = self._timeout_manager.is_timer_active(execution_id)
        
        return state_dict
    
    def cancel_diagnosis(self, execution_id: str) -> bool:
        """
        取消诊断任务
        
        Args:
            execution_id: 任务执行 ID
            
        Returns:
            bool: 是否成功取消
        """
        api_logger.info(
            "diagnosis_cancelling",
            extra={
                'event': 'diagnosis_cancelling',
                'execution_id': execution_id,
            }
        )
        
        # 取消超时计时器
        self._timeout_manager.cancel_timer(execution_id)
        
        # 流转到 FAILED
        state_machine = DiagnosisStateMachine(
            execution_id=execution_id,
            repository=self._repository,
        )
        
        if state_machine.is_terminal_state():
            api_logger.warning(
                "diagnosis_already_terminal",
                extra={
                    'event': 'diagnosis_already_terminal',
                    'execution_id': execution_id,
                    'state': state_machine.get_current_state().value,
                }
            )
            return False
        
        state_machine.transition(
            event='fail',
            error_message='用户取消诊断任务',
        )
        
        api_logger.info(
            "diagnosis_cancelled",
            extra={
                'event': 'diagnosis_cancelled',
                'execution_id': execution_id,
            }
        )
        return True
