"""
Cleaning Step Base Class

Abstract base class for all cleaning steps.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import logging

from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext
from wechat_backend.v2.cleaning.errors import StepExecutionError

logger = logging.getLogger(__name__)


class CleaningStep(ABC):
    """
    Cleaning step base class

    All specific cleaning steps must inherit from this class
    and implement the process method.
    Each step should be:
    1. Idempotent - same result on multiple executions
    2. No side effects - does not modify original data
    3. Configurable - behavior controlled by configuration
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize cleaning step

        Args:
            name: Step name (for logging and tracing)
            config: Step-specific configuration
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        Execute cleaning step

        Args:
            context: Pipeline context (contains current state and intermediate data)

        Returns:
            Updated pipeline context

        Raises:
            StepExecutionError: Step execution failed
        """
        pass

    def validate_input(self, context: PipelineContext) -> bool:
        """
        Validate input data meets step requirements

        Subclasses can override to add specific validation logic
        """
        return True

    def should_skip(self, context: PipelineContext) -> bool:
        """
        Determine if this step should be skipped

        Subclasses can override to implement conditional execution
        """
        return False

    def get_step_result(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Get this step's result from context

        Used for data passing between steps
        """
        return context.intermediate_data.get(self.name, {})

    def save_step_result(self, context: PipelineContext, data: Dict[str, Any]):
        """
        Save this step's result to context
        """
        context.add_step_result(self.name, data)

    def log_step_start(self, context: PipelineContext):
        """Record step start (structured logging)"""
        logger.info(
            "cleaning_step_started",
            extra={
                'step': self.name,
                'execution_id': context.execution_id,
                'config': self.config
            }
        )

    def log_step_complete(self, context: PipelineContext, duration_ms: float):
        """Record step completion"""
        logger.info(
            "cleaning_step_completed",
            extra={
                'step': self.name,
                'execution_id': context.execution_id,
                'duration_ms': duration_ms,
                'warning_count': len(context.warnings),
                'error_count': len(context.errors),
            }
        )

    def log_step_error(self, context: PipelineContext, error: Exception):
        """Record step error"""
        logger.error(
            "cleaning_step_failed",
            extra={
                'step': self.name,
                'execution_id': context.execution_id,
                'error': str(error),
                'error_type': type(error).__name__,
            }
        )
