"""
Cleaning Pipeline Error Definitions

Custom exception classes for the cleaning pipeline.
"""


class CleaningError(Exception):
    """Base exception for cleaning pipeline errors"""

    def __init__(self, message: str, execution_id: str, step: str = None):
        self.message = message
        self.execution_id = execution_id
        self.step = step
        super().__init__(f"[{execution_id}][{step or 'unknown'}] {message}")


class TextExtractionError(CleaningError):
    """Exception raised when text extraction fails"""
    pass


class EntityRecognitionError(CleaningError):
    """Exception raised when entity recognition fails"""
    pass


class ValidationError(CleaningError):
    """Exception raised when validation fails"""
    pass


class QualityScoringError(CleaningError):
    """Exception raised when quality scoring fails"""
    pass


class PipelineConfigurationError(CleaningError):
    """Exception raised when pipeline configuration is invalid"""
    pass


class StepExecutionError(CleaningError):
    """Exception raised when a cleaning step execution fails"""
    pass
