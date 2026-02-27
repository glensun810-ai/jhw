"""
AI Platform Standardized Data Models

This module defines the standardized request/response models for AI platform interactions.
All AI adapters must use these models for consistent data exchange.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AIProvider(str, Enum):
    """AI Provider enumeration"""
    DEEPSEEK = 'deepseek'
    DOUBAO = 'doubao'
    QWEN = 'qwen'
    # Extensible for future providers


@dataclass
class AIRequest:
    """
    Standardized AI Request

    Business layer uses this model uniformly, adapters are responsible for
    converting to platform-specific formats.
    """
    # Core parameters
    prompt: str                                 # Prompt text
    model: str                                  # Model name (e.g., deepseek-chat)

    # Optional parameters
    temperature: float = 0.7                    # Temperature (0-2)
    max_tokens: int = 2000                       # Maximum output tokens
    top_p: float = 1.0                           # Nucleus sampling
    frequency_penalty: float = 0.0                # Frequency penalty
    presence_penalty: float = 0.0                 # Presence penalty

    # Metadata
    request_id: Optional[str] = None             # Request ID for tracking
    timeout: int = 60                             # Timeout in seconds

    # Context for conversation scenarios
    messages: Optional[List[Dict[str, str]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for logging)"""
        return {
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'prompt_preview': self.prompt[:100] + '...' if len(self.prompt) > 100 else self.prompt,
            'request_id': self.request_id,
        }


@dataclass
class AIResponse:
    """
    Standardized AI Response

    Platform-specific responses are converted to this format.
    """
    # Core response
    content: str                                # Generated text content
    model: str                                   # Actual model used

    # Performance metrics
    latency_ms: int                              # Response latency in milliseconds

    # Token usage
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Finish reason
    finish_reason: Optional[str] = None          # stop, length, content_filter, etc.

    # Raw response (preserved for debugging and auditing)
    raw_response: Optional[Dict[str, Any]] = None

    # Error information
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Metadata
    request_id: Optional[str] = None
    provider: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for logging)"""
        return {
            'model': self.model,
            'latency_ms': self.latency_ms,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'finish_reason': self.finish_reason,
            'error': self.error,
            'error_code': self.error_code,
            'provider': self.provider,
            'content_preview': self.content[:100] + '...' if self.content and len(self.content) > 100 else self.content,
        }

    @property
    def is_success(self) -> bool:
        """Whether the request was successful"""
        return self.error is None

    @property
    def text_length(self) -> int:
        """Length of response text"""
        return len(self.content) if self.content else 0


@dataclass
class AIStreamChunk:
    """
    Streaming Response Chunk

    Used for streaming output (future extension)
    """
    content: str
    is_finished: bool = False
    finish_reason: Optional[str] = None
    index: int = 0
