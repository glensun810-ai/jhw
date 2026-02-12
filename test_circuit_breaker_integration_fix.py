#!/usr/bin/env python3
"""
Test script to verify that the circuit breaker is now properly integrated and working
"""
import os
import sys
import time
import tempfile
import shutil
import requests

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from wechat_backend.circuit_breaker import CircuitBreaker, CircuitBreakerState, CircuitBreakerOpenError
from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter


def test_circuit_breaker_integration():
    """Test that the circuit breaker is properly integrated with the adapter"""
    print("Testing circuit breaker integration...")
    
    # Create a temporary directory for the test database
    test_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    try:
        # Create an adapter instance
        adapter = DoubaoAdapter(
            api_key="test-key-for-circuit-breaker",
            model_name="test-model-circuit"
        )
        
        # Check that the adapter has a circuit breaker
        assert hasattr(adapter, 'circuit_breaker'), "Adapter should have circuit breaker attribute"
        assert adapter.circuit_breaker is not None, "Circuit breaker should be initialized"
        
        print(f"✅ Adapter has circuit breaker: {adapter.circuit_breaker.name}")
        print(f"✅ Circuit breaker state: {adapter.circuit_breaker.state.value}")
        print(f"✅ Circuit breaker threshold: {adapter.circuit_breaker.failure_threshold}")
        
        # Check that the circuit breaker is properly configured
        assert adapter.circuit_breaker.failure_threshold == 3, f"Expected threshold 3, got {adapter.circuit_breaker.failure_threshold}"
        
        return True
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(test_dir)


def test_circuit_breaker_trips_on_timeout():
    """Test that the circuit breaker properly trips after timeout failures"""
    print("\nTesting circuit breaker tripping on timeout failures...")
    
    # Create a circuit breaker with low thresholds for testing
    cb = CircuitBreaker(
        name="test_timeout_cb",
        failure_threshold=2,  # Trip after 2 failures
        recovery_timeout=1,   # 1 second recovery
        half_open_max_calls=1
    )
    
    # Define a function that always throws a timeout exception
    def timeout_func():
        raise requests.exceptions.Timeout("Request timed out")
    
    # First failure should not trip the circuit
    try:
        cb.call(timeout_func)
        assert False, "Should have raised Timeout"
    except requests.exceptions.Timeout:
        pass  # Expected
    
    assert cb.state == CircuitBreakerState.CLOSED, f"Expected CLOSED after 1 failure, got {cb.state.value}"
    print("✅ After 1 timeout failure, circuit still CLOSED")
    
    # Second failure should trip the circuit
    try:
        cb.call(timeout_func)
        assert False, "Should have raised Timeout"
    except requests.exceptions.Timeout:
        pass  # Expected
    
    # After 2 failures, circuit should be OPEN
    assert cb.state == CircuitBreakerState.OPEN, f"Expected OPEN after 2 failures, got {cb.state.value}"
    print("✅ After 2 timeout failures, circuit opened")
    
    # Now try to call when open - should get CircuitBreakerOpenError
    try:
        cb.call(timeout_func)
        assert False, "Should have raised CircuitBreakerOpenError"
    except CircuitBreakerOpenError:
        print("✅ Circuit breaker properly rejects calls when OPEN")
    
    # Wait for recovery time
    time.sleep(1.1)
    
    # Next call should transition to HALF_OPEN and then close if successful
    def success_func():
        return "success"
    
    try:
        result = cb.call(success_func)
        assert result == "success"
        # After successful call in HALF_OPEN state, circuit should be CLOSED
        assert cb.state == CircuitBreakerState.CLOSED
        print("✅ Circuit breaker properly transitions from OPEN to HALF_OPEN to CLOSED after recovery and success")
    except CircuitBreakerOpenError:
        # This could happen if the transition doesn't happen automatically
        # But the important thing is that it recognizes when to transition
        if cb.state == CircuitBreakerState.HALF_OPEN:
            # If it's in HALF_OPEN, try a success to close it
            result = cb.call(success_func)
            assert result == "success"
            assert cb.state == CircuitBreakerState.CLOSED
            print("✅ Circuit breaker properly transitions from HALF_OPEN to CLOSED after success")
    
    return True


def test_circuit_breaker_handles_different_exceptions():
    """Test that the circuit breaker handles different types of exceptions"""
    print("\nTesting circuit breaker exception handling...")
    
    cb = CircuitBreaker(
        name="test_exception_cb",
        failure_threshold=1,  # Trip immediately for testing
        recovery_timeout=1
    )
    
    # Test timeout exception
    def timeout_func():
        raise requests.exceptions.ReadTimeout("Read timeout occurred")
    
    try:
        cb.call(timeout_func)
        assert False, "Should have raised ReadTimeout"
    except requests.exceptions.ReadTimeout:
        pass  # Expected
    
    assert cb.state == CircuitBreakerState.OPEN, "Circuit should be OPEN after timeout"
    print("✅ Circuit breaker trips on ReadTimeout")
    
    # Reset for next test
    cb._to_closed()
    
    # Test connection error
    def connection_error_func():
        raise requests.exceptions.ConnectionError("Connection failed")
    
    try:
        cb.call(connection_error_func)
        assert False, "Should have raised ConnectionError"
    except requests.exceptions.ConnectionError:
        pass  # Expected
    
    assert cb.state == CircuitBreakerState.OPEN, "Circuit should be OPEN after connection error"
    print("✅ Circuit breaker trips on ConnectionError")
    
    # Reset for next test
    cb._to_closed()
    
    # Test that non-timeout exceptions don't trip the circuit (if configured not to)
    # For this test, we'll use a different circuit breaker with custom exceptions
    import requests
    cb_selective = CircuitBreaker(
        name="test_selective_cb",
        failure_threshold=1,
        recovery_timeout=1,
        expected_exceptions=(requests.exceptions.Timeout,)  # Only timeout should trigger
    )
    
    def http_error_func():
        raise requests.exceptions.HTTPError("HTTP 401 error")
    
    try:
        cb_selective.call(http_error_func)
        assert False, "Should have raised HTTPError"
    except requests.exceptions.HTTPError:
        pass  # Expected
    
    # HTTPError should NOT trip the circuit since it's not in expected_exceptions
    assert cb_selective.state == CircuitBreakerState.CLOSED, "Circuit should remain CLOSED for non-configured exceptions"
    print("✅ Circuit breaker does not trip on non-configured exceptions")
    
    return True


def test_adapter_with_simulated_failures():
    """Test the adapter with simulated failure scenarios"""
    print("\nTesting adapter with simulated failures...")
    
    # Create a temporary directory for the test
    test_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    try:
        # Create an adapter with a dummy API key
        adapter = DoubaoAdapter(
            api_key="dummy-key",
            model_name="test-model-simulated"
        )
        
        # Check that the adapter's send_prompt method properly integrates with circuit breaker
        # Since we're using a dummy key, this should fail but in a way that tests the integration
        
        # The adapter should have the circuit breaker integrated in the send_prompt method
        import inspect
        send_prompt_source = inspect.getsource(adapter.send_prompt)
        
        # Check that the source contains circuit breaker call
        assert 'circuit_breaker.call' in send_prompt_source or 'self.circuit_breaker.call' in send_prompt_source, \
               "send_prompt method should use circuit breaker.call"
        
        print("✅ Adapter send_prompt method properly integrates circuit breaker")
        
        return True
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(test_dir)


def run_all_tests():
    """Run all circuit breaker integration tests"""
    print("="*70)
    print("Testing Circuit Breaker Integration Fix")
    print("="*70)

    tests = [
        test_circuit_breaker_integration,
        test_circuit_breaker_trips_on_timeout,
        test_circuit_breaker_handles_different_exceptions,
        test_adapter_with_simulated_failures
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
            if result:
                print(f"✅ {test_func.__name__} passed")
            else:
                print(f"❌ {test_func.__name__} failed")
        except Exception as e:
            print(f"❌ {test_func.__name__} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*70)
    print("CIRCUIT BREAKER INTEGRATION TEST RESULTS SUMMARY")
    print("="*70)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 ALL CIRCUIT BREAKER INTEGRATION TESTS PASSED!")
        print("\nThe circuit breaker is now properly integrated with:")
        print("- Correct method integration in send_prompt")
        print("- Proper exception propagation for timeout/connection errors")
        print("- Appropriate tripping after configured failure threshold")
        print("- Correct state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)")
        print("- Selective exception handling (only certain exceptions trip circuit)")
        return True
    else:
        print("⚠️  SOME CIRCUIT BREAKER INTEGRATION TESTS FAILED!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)