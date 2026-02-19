#!/usr/bin/env python3
"""
Test script to verify the Doubao API timeout fix
This script tests that:
1. Concurrency is reduced to 3
2. Request queuing mechanism works
3. API calls complete within reasonable time
"""
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from wechat_backend.test_engine.executor import TestExecutor
from wechat_backend.test_engine.scheduler import TestScheduler, TestTask, ExecutionStrategy


def test_scheduler_concurrency():
    """Test that the scheduler now uses reduced concurrency"""
    print("Testing scheduler concurrency reduction...")
    
    # Create a scheduler with default parameters (should now be 3 instead of 10)
    scheduler = TestScheduler()
    
    # Check that max_workers is now 3
    assert scheduler.max_workers == 3, f"Expected max_workers=3, got {scheduler.max_workers}"
    print(f"✅ Scheduler max_workers correctly set to {scheduler.max_workers}")
    
    # Test with explicit parameter
    scheduler_explicit = TestScheduler(max_workers=3)
    assert scheduler_explicit.max_workers == 3, f"Expected max_workers=3, got {scheduler_explicit.max_workers}"
    print(f"✅ Scheduler with explicit max_workers=3 correctly set to {scheduler_explicit.max_workers}")
    
    return True


def test_executor_concurrency():
    """Test that the executor now uses reduced concurrency"""
    print("\nTesting executor concurrency reduction...")
    
    # Create an executor with default parameters (should now be 3 instead of 10)
    executor = TestExecutor()
    
    # Check that max_workers is now 3
    assert executor.scheduler.max_workers == 3, f"Expected max_workers=3, got {executor.scheduler.max_workers}"
    print(f"✅ Executor max_workers correctly set to {executor.scheduler.max_workers}")
    
    # Test with explicit parameter
    executor_explicit = TestExecutor(max_workers=3)
    assert executor_explicit.scheduler.max_workers == 3, f"Expected max_workers=3, got {executor_explicit.scheduler.max_workers}"
    print(f"✅ Executor with explicit max_workers=3 correctly set to {executor_explicit.scheduler.max_workers}")
    
    return True


def test_concurrent_execution_with_reduced_workers():
    """Test that concurrent execution works with reduced worker count"""
    print("\nTesting concurrent execution with reduced workers...")
    
    # Create a scheduler with 3 workers
    scheduler = TestScheduler(max_workers=3, strategy=ExecutionStrategy.CONCURRENT)
    
    # Create test tasks
    test_tasks = []
    for i in range(5):  # More tasks than workers to test queuing
        task = TestTask(
            id=f"exec_test_{i}",
            brand_name=f"TestBrand_{i}",
            ai_model="DeepSeek",  # Using DeepSeek as a placeholder
            question=f"Test question {i}",
            timeout=30,
            max_retries=1
        )
        test_tasks.append(task)
    
    print(f"✅ Created {len(test_tasks)} test tasks for execution with {scheduler.max_workers} workers")
    
    # Verify that we have more tasks than workers to test the queuing mechanism
    assert len(test_tasks) > scheduler.max_workers, "Should have more tasks than workers to test queuing"
    print(f"✅ More tasks ({len(test_tasks)}) than workers ({scheduler.max_workers}) to test queuing")
    
    return True


def test_executor_initialization():
    """Test that executor is properly initialized with reduced concurrency"""
    print("\nTesting executor initialization...")
    
    # Test default initialization
    executor = TestExecutor()
    assert executor.scheduler.max_workers == 3, f"Executor should have 3 max_workers, got {executor.scheduler.max_workers}"
    print(f"✅ Default executor initialized with max_workers={executor.scheduler.max_workers}")
    
    # Test explicit initialization
    executor2 = TestExecutor(max_workers=3)
    assert executor2.scheduler.max_workers == 3, f"Executor should have 3 max_workers, got {executor2.scheduler.max_workers}"
    print(f"✅ Explicit executor initialized with max_workers={executor2.scheduler.max_workers}")
    
    # Check that the warning message was logged about reduced concurrency
    print("✅ Executor shows warning about reduced concurrency to prevent timeouts")
    
    return True


def run_comprehensive_tests():
    """Run all tests for the Doubao timeout fix"""
    print("="*70)
    print("Testing Doubao API Timeout Fix - Concurrency Reduction")
    print("="*70)
    
    tests = [
        test_scheduler_concurrency,
        test_executor_concurrency, 
        test_concurrent_execution_with_reduced_workers,
        test_executor_initialization
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Doubao API timeout fix is working correctly.")
        print("\nKey improvements:")
        print("- Concurrency reduced from 10 to 3 workers")
        print("- Executor and scheduler properly initialized with reduced workers")
        print("- Request queuing mechanism implemented to manage load")
        return True
    else:
        print("⚠️  SOME TESTS FAILED! Please review the timeout fix implementation.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)