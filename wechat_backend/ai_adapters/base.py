"""
Base AI Provider Module for GEO Content Quality Validator
Defines the abstract base class and core infrastructure for AI model integration
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
import asyncio
import aiohttp
import time
import os
from enum import Enum


class AIProviderType(Enum):
    """Enumeration of supported AI provider types"""
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"
    YUANBAO = "yuanbao"
    QWEN = "qwen"
    WENXIN = "wenxin"
    KIMI = "kimi"
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    GEMINI = "gemini"


@dataclass
class StandardAIResponse:
    """Standardized response structure from AI providers"""
    content: str  # The main response text
    sources: List[str]  # Reference links/sources mentioned in the response
    usage: Dict[str, int]  # Token usage information (input_tokens, output_tokens, total_tokens)
    latency: float  # Time taken to generate response in seconds
    success: bool  # Whether the request was successful
    error_message: Optional[str] = None  # Error message if request failed
    provider: str = ""  # Name of the AI provider
    model: str = ""  # Model name that generated the response
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata specific to the provider


class BaseAIProvider(ABC):
    """Abstract base class for all AI providers implementing the unified interface"""
    
    def __init__(self, api_key: str, model_name: str, **kwargs):
        """
        Initialize the AI provider
        
        Args:
            api_key: API key for the provider
            model_name: Name of the model to use
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.model_name = model_name
        self.provider_name = self.__class__.__name__.replace('Provider', '').lower()
        self.extra_config = kwargs
        self.session = None  # Will be initialized when needed
    
    async def initialize_session(self):
        """Initialize the aiohttp session for async requests"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.extra_config.get('timeout', 30))
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    @abstractmethod
    async def query(self, prompt: str, **kwargs) -> StandardAIResponse:
        """
        Query the AI provider with a prompt
        
        Args:
            prompt: The input prompt to send to the AI
            **kwargs: Additional provider-specific parameters
            
        Returns:
            StandardAIResponse: Standardized response object
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the configuration for this AI provider
        
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
            'provider_name': self.provider_name,
            'provider_type': self.get_provider_type()
        }
    
    @abstractmethod
    def get_provider_type(self) -> AIProviderType:
        """
        Get the type of AI provider this adapter supports
        
        Returns:
            AIProviderType: The type of AI provider
        """
        pass


class AsyncAIManager:
    """Manages multiple AI providers with async concurrency and error handling"""
    
    def __init__(self):
        self.providers = {}
        self.active_sessions = []
    
    def register_provider(self, provider_type: AIProviderType, provider_instance: BaseAIProvider):
        """Register an AI provider instance"""
        self.providers[provider_type] = provider_instance
    
    async def query_all_concurrent(self, prompt: str, provider_types: List[AIProviderType], 
                                  timeout: float = 30.0, **kwargs) -> List[StandardAIResponse]:
        """
        Query multiple providers concurrently with timeout and error handling
        
        Args:
            prompt: The prompt to send to all providers
            provider_types: List of provider types to query
            timeout: Maximum time to wait for all queries
            **kwargs: Additional parameters to pass to each provider
            
        Returns:
            List of StandardAIResponse objects from all providers
        """
        # Create tasks for all providers
        tasks = []
        for provider_type in provider_types:
            if provider_type in self.providers:
                provider = self.providers[provider_type]
                task = asyncio.create_task(self._query_with_timeout(provider, prompt, timeout, **kwargs))
                tasks.append(task)
        
        if not tasks:
            return []
        
        # Wait for all tasks to complete (with timeout)
        try:
            responses = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
        except asyncio.TimeoutError:
            # Even if timeout occurs, return whatever responses we got
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            responses = [None] * len(tasks)  # Placeholder for cancelled tasks
        
        # Process responses and handle exceptions
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                # Handle exception from the task
                processed_responses.append(StandardAIResponse(
                    content="",
                    sources=[],
                    usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    latency=0.0,
                    success=False,
                    error_message=f"Query failed: {str(response)}"
                ))
            elif response is None:
                # Timeout case
                processed_responses.append(StandardAIResponse(
                    content="",
                    sources=[],
                    usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    latency=timeout,
                    success=False,
                    error_message="Query timed out"
                ))
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    async def _query_with_timeout(self, provider: BaseAIProvider, prompt: str, timeout: float, **kwargs):
        """Helper method to query a provider with timeout"""
        try:
            return await provider.query(prompt, **kwargs)
        except Exception as e:
            return StandardAIResponse(
                content="",
                sources=[],
                usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                latency=0.0,
                success=False,
                error_message=f"Provider error: {str(e)}"
            )
    
    async def close_all_sessions(self):
        """Close all active provider sessions"""
        for provider in self.providers.values():
            await provider.close_session()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    # Example implementation of a mock provider for testing
    class MockProvider(BaseAIProvider):
        def __init__(self, api_key: str, model_name: str = "mock-model", **kwargs):
            super().__init__(api_key, model_name, **kwargs)
        
        async def query(self, prompt: str, **kwargs) -> StandardAIResponse:
            # Simulate API call delay
            await asyncio.sleep(1)
            return StandardAIResponse(
                content=f"Mock response for: {prompt[:50]}...",
                sources=["https://example.com/source1", "https://example.com/source2"],
                usage={"input_tokens": 20, "output_tokens": 50, "total_tokens": 70},
                latency=1.0,
                success=True,
                provider=self.provider_name,
                model=self.model_name
            )
        
        def validate_config(self) -> bool:
            return bool(self.api_key)
        
        def get_provider_type(self) -> AIProviderType:
            return AIProviderType.CHATGPT  # Just for testing
    
    async def test_async_manager():
        manager = AsyncAIManager()
        
        # Register mock providers
        for i in range(3):
            provider = MockProvider(f"key_{i}", f"model_{i}")
            manager.register_provider(AIProviderType(f"chatgpt"), provider)  # Using same type for simplicity
        
        # Test concurrent querying
        responses = await manager.query_all_concurrent(
            "Test prompt for concurrent querying",
            [AIProviderType.CHATGPT] * 3
        )
        
        print(f"Got {len(responses)} responses:")
        for i, resp in enumerate(responses):
            print(f"Response {i}: Success={resp.success}, Content='{resp.content[:50]}...'")
    
    # Run the test
    asyncio.run(test_async_manager())