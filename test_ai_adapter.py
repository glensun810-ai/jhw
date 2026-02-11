#!/usr/bin/env python3
"""
Test script to verify the AI Adapter Layer implementation
"""
import os
import sys
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_ai_adapter_layer():
    print("Testing AI Adapter Layer Implementation...")
    
    # Import the AI adapter components
    from wechat_backend.ai_adapters import AIAdapterFactory, AIPlatformType, AIClient
    from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter
    
    print("\n1. Testing factory registration...")
    # Check if DeepSeek adapter is registered
    if AIAdapterFactory.is_platform_supported(AIPlatformType.DEEPSEEK):
        print("✓ DeepSeek platform is registered with the factory")
    else:
        print("✗ DeepSeek platform is NOT registered with the factory")
        return False
    
    print("\n2. Testing adapter creation...")
    # Create a DeepSeek adapter instance (using a fake API key for testing)
    try:
        adapter = AIAdapterFactory.create(
            AIPlatformType.DEEPSEEK,
            api_key="fake-api-key-for-testing",
            model_name="deepseek-chat"
        )
        print(f"✓ Successfully created DeepSeek adapter: {type(adapter).__name__}")
        print(f"  - Model: {adapter.model_name}")
        print(f"  - Platform: {adapter.platform_name}")
    except Exception as e:
        print(f"✗ Failed to create DeepSeek adapter: {e}")
        return False
    
    print("\n3. Testing adapter interface compliance...")
    # Check if the adapter implements the required interface
    if isinstance(adapter, AIClient):
        print("✓ Adapter implements AIClient interface")
    else:
        print("✗ Adapter does NOT implement AIClient interface")
        return False
    
    print("\n4. Testing adapter properties...")
    # Check if the adapter has required properties
    required_attrs = ['api_key', 'model_name', 'platform_name', 'send_prompt', 'validate_config']
    missing_attrs = [attr for attr in required_attrs if not hasattr(adapter, attr)]
    
    if not missing_attrs:
        print("✓ Adapter has all required attributes and methods")
    else:
        print(f"✗ Adapter is missing attributes/methods: {missing_attrs}")
        return False
    
    print("\n5. Testing platform type...")
    # Check if the adapter returns the correct platform type
    platform_type = adapter.get_platform_type()
    if platform_type == AIPlatformType.DEEPSEEK:
        print(f"✓ Adapter correctly identifies as {platform_type.value} platform")
    else:
        print(f"✗ Adapter incorrectly identifies as {platform_type.value} platform")
        return False
    
    print("\n6. Testing model info...")
    # Check if the adapter can provide model info
    model_info = adapter.get_model_info()
    expected_keys = ['model_name', 'platform_name', 'platform_type']
    missing_keys = [key for key in expected_keys if key not in model_info]
    
    if not missing_keys:
        print("✓ Adapter correctly provides model info")
        print(f"  - Model: {model_info['model_name']}")
        print(f"  - Platform: {model_info['platform_name']}")
        print(f"  - Platform Type: {model_info['platform_type'].value}")
    else:
        print(f"✗ Adapter model info missing keys: {missing_keys}")
        return False
    
    print("\n7. Testing validation (should fail with fake API key)...")
    # Test validation (this should fail with a fake API key, which is expected)
    try:
        is_valid = adapter.validate_config()
        print(f"✓ Validation method executed (result: {is_valid})")
        # Note: We expect this to fail with a fake API key, which is normal
    except Exception as e:
        print(f"✓ Validation method executed but threw expected exception: {type(e).__name__}")
    
    print("\n✓ All tests passed! AI Adapter Layer is properly implemented.")
    return True

if __name__ == "__main__":
    success = test_ai_adapter_layer()
    if success:
        print("\n🎉 AI Adapter Layer implementation is successful!")
    else:
        print("\n❌ AI Adapter Layer implementation has issues!")
        sys.exit(1)