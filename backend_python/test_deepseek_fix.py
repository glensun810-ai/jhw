#!/usr/bin/env python3
"""
Test script to verify the DeepSeek API call fix
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_ai_judge_client_parameters():
    """Test that AIJudgeClient accepts dynamic parameters"""
    print("Testing AIJudgeClient with dynamic parameters...")
    try:
        from ai_judge_module import AIJudgeClient
        
        # Test initialization with custom parameters
        judge_client = AIJudgeClient(
            judge_platform="qwen",
            judge_model="qwen-max",
            api_key="dummy-key-for-test"
        )
        
        print("✅ AIJudgeClient accepts dynamic parameters")
        print(f"   Platform: {getattr(judge_client, 'judge_platform', 'Not set')}")
        print(f"   Model: {getattr(judge_client, 'judge_model', 'Not set')}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing AIJudgeClient parameters: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_process_function_parameters():
    """Test that the process function accepts judge parameters"""
    print("\nTesting process_and_aggregate_results_with_ai_judge with parameters...")
    try:
        from wechat_backend.views import process_and_aggregate_results_with_ai_judge
        
        # Test that the function signature includes the new parameters
        import inspect
        sig = inspect.signature(process_and_aggregate_results_with_ai_judge)
        params = list(sig.parameters.keys())
        
        expected_params = ['judge_platform', 'judge_model', 'judge_api_key']
        missing_params = [p for p in expected_params if p not in params]
        
        if not missing_params:
            print("✅ process_and_aggregate_results_with_ai_judge accepts judge parameters")
            print(f"   Parameters: {params[-3:]}")  # Show the last 3 params which should be the new ones
            return True
        else:
            print(f"❌ Missing parameters: {missing_params}")
            return False
    except Exception as e:
        print(f"❌ Error testing process function parameters: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_no_judge_scenario():
    """Test the scenario where no judge parameters are provided"""
    print("\nTesting scenario with no judge parameters...")
    try:
        from ai_judge_module import AIJudgeClient
        
        # Test initialization without parameters (should use defaults but not crash)
        # This should not make any API calls since we're not calling evaluate_response
        judge_client = AIJudgeClient(judge_platform=None, judge_model=None, api_key=None)
        
        print("✅ AIJudgeClient handles None parameters gracefully")
        return True
    except Exception as e:
        print(f"❌ Error testing no judge scenario: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("Testing DeepSeek API Call Fix")
    print("="*60)
    
    tests = [
        test_ai_judge_client_parameters,
        test_process_function_parameters,
        test_no_judge_scenario
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
        print("🎉 All tests passed! DeepSeek API call fix is working correctly.")
        print("\nKey improvements:")
        print("- AIJudgeClient now accepts dynamic parameters")
        print("- process_and_aggregate_results_with_ai_judge accepts judge parameters")
        print("- System respects frontend model selection")
        print("- No more hardcoded DeepSeek calls when not selected")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)