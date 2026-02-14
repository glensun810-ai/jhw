"""
Utility functions for managing AI adapters and running tests
"""
from typing import List, Dict, Any
from .ai_adapters.base_adapter import AIPlatformType, AIClient, AIResponse
from .ai_adapters.factory import AIAdapterFactory


def get_ai_client(platform_name: str, api_key: str, model_name: str, **kwargs) -> AIClient:
    """
    Get an AI client for the specified platform

    Args:
        platform_name: Name of the AI platform
        api_key: API key for the platform
        model_name: Name of the model to use
        **kwargs: Additional configuration options

    Returns:
        AIClient instance for the specified platform
    """
    # Map platform names to AIPlatformType
    platform_map = {
        'deepseek': AIPlatformType.DEEPSEEK,
        'deepseekr1': AIPlatformType.DEEPSEEKR1,  # New DeepSeek R1 platform
        'doubao': AIPlatformType.DOUBAO,
        'yuanbao': AIPlatformType.YUANBAO,
        'qwen': AIPlatformType.QWEN,
        'wenxin': AIPlatformType.WENXIN,
        'kimi': AIPlatformType.KIMI,
        'chatgpt': AIPlatformType.CHATGPT,
        'claude': AIPlatformType.CLAUDE,
        'gemini': AIPlatformType.GEMINI,
        'spark': AIPlatformType.SPARK,
        'zhipu': AIPlatformType.ZHIPU,
        '智谱ai': AIPlatformType.ZHIPU
    }

    platform_type = platform_map.get(platform_name.lower())
    if not platform_type:
        raise ValueError(f"Unsupported platform: {platform_name}")

    # For factory creation, we need to pass the platform type enum directly
    return AIAdapterFactory.create(platform_type, api_key, model_name, **kwargs)


def run_brand_test_with_ai(client: AIClient, brand_name: str, question: str) -> AIResponse:
    """
    Run a brand test with a specific AI client

    Args:
        client: The AI client to use
        brand_name: The brand name to test
        question: The question to ask about the brand

    Returns:
        AIResponse from the AI platform
    """
    prompt = f"Please provide detailed information about {brand_name}. {question}"
    return client.send_prompt(prompt)


def evaluate_response_accuracy(response_content: str, brand_name: str) -> Dict[str, float]:
    """
    Evaluate the accuracy and completeness of an AI response
    This is a simplified evaluation - in a real system, you might use more sophisticated methods

    Args:
        response_content: The response content from the AI
        brand_name: The brand name that was tested

    Returns:
        Dictionary with accuracy metrics
    """
    # Simple evaluation metrics
    contains_brand = brand_name.lower() in response_content.lower()
    response_length = len(response_content.strip())

    # Calculate basic metrics
    accuracy = 0.7 if contains_brand else 0.3  # Higher if brand is mentioned
    completeness = min(response_length / 100.0, 1.0)  # Scale response length to 0-1

    # Adjust scores based on content quality indicators
    if len(response_content.split()) > 20:  # At least 20 words
        completeness = min(completeness * 1.2, 1.0)

    # Final score is average of accuracy and completeness
    score = (accuracy + completeness) / 2

    return {
        'accuracy': accuracy * 100,
        'completeness': completeness * 100,
        'score': score * 100
    }