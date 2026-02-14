"""
Factory for creating and managing AI adapters
"""
from typing import Dict, Type, Union
from .base import AIClient, AIPlatformType


class AIAdapterFactory:
    """
    Factory class for creating AI adapters based on platform type.
    Provides a centralized way to instantiate different AI platform adapters.
    """
    
    _adapters: Dict[AIPlatformType, Type[AIClient]] = {}
    
    @classmethod
    def register(cls, platform_type: AIPlatformType, adapter_class: Type[AIClient]):
        """
        Register an AI adapter class for a specific platform type
        
        Args:
            platform_type: The AI platform type
            adapter_class: The adapter class to register
        """
        cls._adapters[platform_type.value] = adapter_class
        cls._adapters[platform_type] = adapter_class
    
    @classmethod
    def create(cls, platform_type: Union[AIPlatformType, str], api_key: str, model_name: str, **kwargs) -> AIClient:
        """
        Create an instance of an AI adapter for the specified platform
        
        Args:
            platform_type: The AI platform type or string name
            api_key: API key for the platform
            model_name: Name of the model to use
            **kwargs: Additional configuration parameters
            
        Returns:
            An instance of the appropriate AIClient subclass
            
        Raises:
            ValueError: If the platform type is not registered
        """
        # Convert string to AIPlatformType if needed
        if isinstance(platform_type, str):
            try:
                platform_type = AIPlatformType(platform_type.lower())
            except ValueError:
                raise ValueError(f"Unknown platform type: {platform_type}")
        
        if platform_type not in cls._adapters:
            raise ValueError(f"No adapter registered for platform: {platform_type}")
        
        adapter_class = cls._adapters[platform_type]
        return adapter_class(api_key, model_name, **kwargs)
    
    @classmethod
    def get_available_platforms(cls) -> list:
        """
        Get a list of available platform types
        
        Returns:
            List of available AI platform types
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def is_platform_supported(cls, platform_type: Union[AIPlatformType, str]) -> bool:
        """
        Check if a platform is supported
        
        Args:
            platform_type: The platform type to check
            
        Returns:
            True if the platform is supported, False otherwise
        """
        if isinstance(platform_type, str):
            try:
                platform_type = AIPlatformType(platform_type.lower())
            except ValueError:
                return False
        
        return platform_type in cls._adapters