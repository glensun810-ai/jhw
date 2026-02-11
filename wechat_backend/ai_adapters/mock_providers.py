"""
Mock providers for testing purposes
"""
from .base import BaseAIProvider, StandardAIResponse, AIProviderType
import asyncio
import time


class MockProvider(BaseAIProvider):
    """Mock provider for testing purposes"""
    
    def __init__(self, api_key: str, model_name: str = "mock-model", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
    
    async def query(self, prompt: str, **kwargs) -> StandardAIResponse:
        # Simulate API call delay
        await asyncio.sleep(0.5)
        return StandardAIResponse(
            content=f"Mock response for: {prompt[:50]}... This is a simulated response from {self.provider_name}.",
            sources=[
                "https://example.com/source1", 
                "https://example.com/source2",
                "https://example.com/brand-info"
            ],
            usage={
                "input_tokens": 20, 
                "output_tokens": 50, 
                "total_tokens": 70
            },
            latency=0.5,
            success=True,
            provider=self.provider_name,
            model=self.model_name,
            metadata={"mock": True, "test": True}
        )
    
    def validate_config(self) -> bool:
        return bool(self.api_key)
    
    def get_provider_type(self) -> AIProviderType:
        # Return a default type, in real usage this would be set appropriately
        return AIProviderType.CHATGPT  # Just for testing purposes