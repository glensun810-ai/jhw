"""
Cleaning Pipeline Context

Data structure for passing data and state during pipeline execution.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class PipelineContext:
    """
    Cleaning pipeline context

    Data and state passed during pipeline execution
    """
    # Input data
    execution_id: str
    report_id: int
    brand: str
    question: str
    model: str

    # Raw response
    raw_response: Dict[str, Any]                # From AIResponse.raw_response
    response_content: str                        # From AIResponse.content

    # Intermediate data during cleaning
    intermediate_data: Dict[str, Any] = field(default_factory=dict)

    # Current cleaning step
    current_step: str = ''
    steps_completed: List[str] = field(default_factory=list)

    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # Start time
    started_at: datetime = field(default_factory=datetime.now)

    def add_step_result(self, step_name: str, data: Dict[str, Any]):
        """Add step result to intermediate data"""
        self.intermediate_data[step_name] = data
        self.steps_completed.append(step_name)
        self.current_step = step_name

    def add_warning(self, message: str):
        """Add warning"""
        self.warnings.append(f"[{self.current_step}] {message}")

    def add_error(self, message: str):
        """Add error"""
        self.errors.append(f"[{self.current_step}] {message}")

    def get_intermediate(self, step_name: str, key: str, default=None):
        """Get intermediate data"""
        step_data = self.intermediate_data.get(step_name, {})
        return step_data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for logging)"""
        return {
            'execution_id': self.execution_id,
            'report_id': self.report_id,
            'brand': self.brand,
            'model': self.model,
            'current_step': self.current_step,
            'steps_completed': self.steps_completed,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'duration_ms': (datetime.now() - self.started_at).total_seconds() * 1000,
        }
