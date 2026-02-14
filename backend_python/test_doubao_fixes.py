#!/usr/bin/env python3
"""
Test script to verify Doubao adapter fixes
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_doubao_adapter_import():
    """Test that the Doubao adapter can be imported without errors"""
    print("Testing Doubao adapter import...")
    try:
        from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
        print("✅ Doubao adapter imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Doubao adapter: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing Doubao adapter: {e}")
        return False

def test_doubao_adapter_initialization():
    """Test that the Doubao adapter can be initialized without errors"""
    print("\nTesting Doubao adapter initialization...")
    try:
        from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # Try to initialize with dummy values
        adapter = DoubaoAdapter(
            api_key="dummy_key",
            model_name="Doubao-pro"
        )
        print("✅ Doubao adapter initialized successfully")
        print(f"   Model: {adapter.model_name}")
        print(f"   Platform: {adapter.platform_type.value}")
        return True
    except Exception as e:
        print(f"❌ Error initializing Doubao adapter: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_mapping():
    """Test that model names are mapped correctly"""
    print("\nTesting model name mapping...")
    try:
        from wechat_backend.test_engine.scheduler import TestScheduler
        
        scheduler = TestScheduler()
        
        # Test various model name mappings
        test_cases = [
            ("豆包", "doubao"),
            ("doubao", "doubao"),
            ("Doubao", "doubao"),
            ("DeepSeek", "deepseek"),
            ("通义千问", "qwen")
        ]
        
        all_passed = True
        for model_name, expected_platform in test_cases:
            result = scheduler._map_model_to_platform(model_name)
            if result == expected_platform:
                print(f"   ✅ '{model_name}' -> '{result}'")
            else:
                print(f"   ❌ '{model_name}' -> '{result}' (expected '{expected_platform}')")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ Error testing model mapping: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_id_mapping():
    """Test that model IDs are mapped correctly"""
    print("\nTesting model ID mapping...")
    try:
        from wechat_backend.test_engine.scheduler import TestScheduler
        
        scheduler = TestScheduler()
        
        # Test Doubao model ID mapping
        result = scheduler._get_actual_model_id("豆包", "doubao")
        print(f"   Doubao model ID: {result}")
        
        if result and result != "豆包":  # Should be mapped to actual model ID
            print("   ✅ Doubao model ID mapped correctly")
            return True
        else:
            print("   ❌ Doubao model ID not mapped correctly")
            return False
    except Exception as e:
        print(f"❌ Error testing model ID mapping: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("Testing Doubao Adapter Fixes")
    print("="*60)
    
    tests = [
        test_doubao_adapter_import,
        test_doubao_adapter_initialization,
        test_model_mapping,
        test_model_id_mapping
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Doubao adapter fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)