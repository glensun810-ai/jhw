"""
Base abstract class for AI clients
Defines the common interface for all AI platform adapters
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class AIPlatformType(Enum):
    """Enumeration of supported AI platform types"""
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    WENXIN = "wenxin"
    DOUBAO = "doubao"
    KIMI = "kimi"
    YUANBAO = "yuanbao"
    SPARK = "spark"


@dataclass
class AIResponse:
    """Standardized response structure from AI platforms"""
    content: str  # The main response text
    model: str  # Model name that generated the response
    platform: str  # Platform name
    tokens_used: Optional[int] = None  # Number of tokens used (if available)
    prompt_tokens: Optional[int] = None  # Number of tokens in the prompt (if available)
    completion_tokens: Optional[int] = None  # Number of tokens in the completion (if available)
    total_tokens: Optional[int] = None  # Total tokens used (if available)
    latency: Optional[float] = None  # Time taken to generate response in seconds
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata specific to the platform
    success: bool = True  # Whether the request was successful
    error_message: Optional[str] = None  # Error message if request failed


class AIClient(ABC):
    """
    Abstract base class for all AI platform adapters.
    Defines the common interface that all AI platform implementations must follow.
    """
    
    def __init__(self, api_key: str, model_name: str, **kwargs):
        """
        Initialize the AI client
        
        Args:
            api_key: API key for the AI platform
            model_name: Name of the model to use
            **kwargs: Additional platform-specific configuration
        """
        self.api_key = api_key
        self.model_name = model_name
        self.platform_name = self.__class__.__name__.replace('Adapter', '').lower()
        self.extra_config = kwargs
    
    @abstractmethod
    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        Send a prompt to the AI platform and return a standardized response
        
        Args:
            prompt: The input prompt to send to the AI
            **kwargs: Additional platform-specific parameters
            
        Returns:
            AIResponse: Standardized response object
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the configuration for this AI client
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model being used
        
        Returns:
            Dict containing model information
        """
        return {
            'model_name': self.model_name,
            'platform_name': self.platform_name,
            'platform_type': self.get_platform_type()
        }
    
    @abstractmethod
    def get_platform_type(self) -> AIPlatformType:
        """
        Get the type of AI platform this adapter supports
        
        Returns:
            AIPlatformType: The type of AI platform
        """
        pass