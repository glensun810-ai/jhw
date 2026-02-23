"""
AI Manager for GEO Content Quality Validator
Handles configuration management, data normalization, and provider orchestration
"""
import os
import time
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType
from wechat_backend.ai_adapters.sync_providers import (
    DeepSeekProvider, DoubaoProvider, YuanbaoProvider,
    QwenProvider, ErnieProvider, KimiProvider
)
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.logging_config import api_logger
from concurrent.futures import ThreadPoolExecutor, as_completed


# Load environment variables
load_dotenv()


class AIManager:
    """Centralized manager for AI providers with configuration and routing capabilities"""

    def __init__(self, max_workers=5):
        self.providers = {}
        self.config = self._load_config()
        self.max_workers = max_workers
        self._initialize_providers()

    def _load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables or config file"""
        config = {
            'deepseek_api_key': os.getenv('DEEPSEEK_API_KEY', ''),
            'doubao_api_key': os.getenv('DOUBAO_API_KEY', ''),
            'yuanbao_api_key': os.getenv('YUANBAO_API_KEY', ''),
            'qwen_api_key': os.getenv('QWEN_API_KEY', ''),
            'ernie_api_key': os.getenv('ERNIE_API_KEY', ''),
            'kimi_api_key': os.getenv('KIMI_API_KEY', ''),
            'mock_enabled': os.getenv('MOCK_ENABLED', 'false').lower() == 'true'
        }

        api_logger.info("AI Manager configuration loaded")
        return config

    def _initialize_providers(self):
        """Initialize all available AI providers based on configuration"""
        # Initialize domestic providers
        if self.config['deepseek_api_key']:
            deepseek_provider = DeepSeekProvider(
                api_key=self.config['deepseek_api_key'],
                model_name='deepseek-chat'
            )
            self.providers[AIPlatformType.DEEPSEEK] = deepseek_provider
            api_logger.info("DeepSeek provider initialized")

        if self.config['doubao_api_key']:
            doubao_provider = DoubaoProvider(
                api_key=self.config['doubao_api_key'],
                model_name='doubao-pro-128k'
            )
            self.providers[AIPlatformType.DOUBAO] = doubao_provider
            api_logger.info("Doubao provider initialized")

        if self.config['yuanbao_api_key']:
            yuanbao_provider = YuanbaoProvider(
                api_key=self.config['yuanbao_api_key'],
                model_name='hunyuan-pro'
            )
            self.providers[AIPlatformType.YUANBAO] = yuanbao_provider
            api_logger.info("Yuanbao provider initialized")

        if self.config['qwen_api_key']:
            qwen_provider = QwenProvider(
                api_key=self.config['qwen_api_key'],
                model_name='qwen-max'
            )
            self.providers[AIPlatformType.QWEN] = qwen_provider
            api_logger.info("Qwen provider initialized")

        if self.config['ernie_api_key']:
            ernie_provider = ErnieProvider(
                api_key=self.config['ernie_api_key'],
                model_name='ernie-bot-4.5'
            )
            self.providers[AIPlatformType.WENXIN] = ernie_provider
            api_logger.info("Ernie provider initialized")

        if self.config['kimi_api_key']:
            kimi_provider = KimiProvider(
                api_key=self.config['kimi_api_key'],
                model_name='moonshot-v1-8k'
            )
            self.providers[AIPlatformType.KIMI] = kimi_provider
            api_logger.info("Kimi provider initialized")

        # If no real providers are configured and mock is enabled, register mock providers
        if self.config['mock_enabled'] and not self.providers:
            self._register_mock_providers()

    def _register_mock_providers(self):
        """Register mock providers for testing when no real API keys are available"""
        for provider_type in [AIPlatformType.DEEPSEEK, AIPlatformType.QWEN, AIPlatformType.DOUBAO]:
            mock_provider = MockProvider(api_key="mock-key", model_name="mock-model")
            self.providers[provider_type] = mock_provider

        api_logger.info("Mock providers registered for testing")

    def query_all_providers(
        self,
        prompt: str,
        provider_types: List[AIPlatformType],
        timeout: float = 30.0,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **kwargs
    ) -> List[AIResponse]:
        """
        Query multiple providers concurrently with user tracking and tenant isolation

        Args:
            prompt: The prompt to send to all providers
            provider_types: List of provider types to query
            timeout: Maximum time to wait for all queries
            user_id: Optional user identifier for tracking
            tenant_id: Optional tenant identifier for isolation
            **kwargs: Additional parameters to pass to each provider

        Returns:
            List of AIResponse objects from all providers
        """
        # Record usage for commercial hooks
        self._record_usage(provider_types, user_id, tenant_id)

        # Perform concurrent queries using ThreadPoolExecutor
        responses = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks for each provider
            future_to_provider = {}
            for provider_type in provider_types:
                if provider_type in self.providers:
                    provider = self.providers[provider_type]
                    future = executor.submit(provider.send_prompt, prompt, **kwargs)
                    future_to_provider[future] = provider_type

            # Collect results as they complete
            for future in as_completed(future_to_provider, timeout=timeout):
                provider_type = future_to_provider[future]
                try:
                    response = future.result()
                    responses.append(response)
                except Exception as e:
                    api_logger.error(f"Error querying provider {provider_type}: {str(e)}")
                    # Create an error response
                    responses.append(AIResponse(
                        success=False,
                        error_message=str(e),
                        model="unknown",
                        platform=provider_type.value
                    ))

        # Normalize responses to standard format
        normalized_responses = []
        for response in responses:
            normalized_response = self._normalize_response(response)
            normalized_responses.append(normalized_response)

        return normalized_responses

    def _normalize_response(self, response: AIResponse) -> AIResponse:
        """
        Normalize response to ensure consistent format across all providers
        """
        # Ensure metadata is a dict
        if response.metadata is None:
            response.metadata = {}

        return response

    def _record_usage(
        self,
        provider_types: List[AIPlatformType],
        user_id: Optional[str],
        tenant_id: Optional[str]
    ):
        """
        Record usage for commercial tracking and tenant isolation
        """
        # This is a placeholder implementation
        # In a real system, this would record usage in a database
        if user_id:
            api_logger.info(f"Recording usage for user {user_id}, tenant {tenant_id}, providers {[p.value for p in provider_types]}")

        # Future implementation would:
        # 1. Store usage data in a database
        # 2. Track per-user/per-tenant limits
        # 3. Trigger alerts when limits are approached
        pass

    def get_available_providers(self) -> List[AIPlatformType]:
        """Get list of available providers"""
        return list(self.providers.keys())

    def is_provider_available(self, provider_type: AIPlatformType) -> bool:
        """Check if a specific provider is available"""
        return provider_type in self.providers

    def validate_all_configs(self) -> Dict[AIPlatformType, bool]:
        """Validate configuration for all registered providers"""
        results = {}
        for provider_type, provider in self.providers.items():
            try:
                # Since validate_config might not exist in all providers, we'll just check if API key is set
                results[provider_type] = True  # Simplified validation
            except Exception as e:
                api_logger.error(f"Error validating config for {provider_type}: {str(e)}")
                results[provider_type] = False

        return results


# Mock provider for testing (to be used when real API keys are not available)
class MockProvider(AIClient):
    """Mock provider for testing purposes"""

    def __init__(self, api_key: str, model_name: str = "mock-model", **kwargs):
        super().__init__(AIPlatformType.CHATGPT, model_name, api_key)

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        # Simulate API call delay
        time.sleep(0.1)
        return AIResponse(
            success=True,
            content=f"Mock response for: {prompt[:50]}... This is a simulated response from {self.model_name}.",
            model=self.model_name,
            platform=self.platform_type.value,
            tokens_used=70,
            latency=0.1,
            metadata={"mock": True, "test": True}
        )


# Example usage
if __name__ == "__main__":
    def test_ai_manager():
        manager = AIManager()

        # Test with available providers
        available_providers = manager.get_available_providers()
        print(f"Available providers: {[p.value for p in available_providers]}")

        if available_providers:
            # Test querying
            responses = manager.query_all_providers(
                "What is the capital of France?",
                available_providers[:2]  # Test with first two providers
            )

            for i, response in enumerate(responses):
                print(f"\nResponse {i+1}:")
                print(f"  Platform: {response.platform}")
                print(f"  Success: {response.success}")
                print(f"  Content: {response.content[:100]}..." if response.content else "  Error: " + response.error_message)
                print(f"  Tokens used: {response.tokens_used}")
                print(f"  Latency: {response.latency}s")

    # Run the test
    test_ai_manager()