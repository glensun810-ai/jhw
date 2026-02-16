import time
import threading
from enum import Enum
from typing import Optional, Callable, Any, Tuple
from .logging_config import api_logger


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Tripped, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker"""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Advanced Circuit Breaker Implementation for AI API calls
    """
    def __init__(
        self, 
        name="default",
        failure_threshold=3,           # 连续3次失败就熔断
        recovery_timeout=30,          # 30秒后尝试恢复
        half_open_max_calls=1,        # 半开状态只放行1个请求
        expected_exceptions=None      # 需要熔断的异常类型
    ):
        """
        Initialize circuit breaker
        
        Args:
            name: Name of the circuit breaker instance
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Time in seconds before allowing test requests
            half_open_max_calls: Max calls allowed in half-open state
            expected_exceptions: Tuple of exception types that count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        # Default exceptions that should trigger circuit breaker
        if expected_exceptions is None:
            import requests
            self.expected_exceptions = (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectTimeout,
                ConnectionError,
                TimeoutError,
                requests.exceptions.HTTPError,
                requests.exceptions.RequestException
            )
        else:
            self.expected_exceptions = expected_exceptions
            
        # State tracking
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        
        # Thread safety
        self._lock = threading.RLock()  # Using RLock for recursive locking if needed
        
        api_logger.info(f"CircuitBreaker '{name}' initialized: threshold={failure_threshold}, "
                       f"recovery_timeout={recovery_timeout}s, expected_exceptions={len(self.expected_exceptions)}")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to call
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Result of function call

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception if function fails
        """
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._allow_recovery():
                    self._to_half_open()
                    api_logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN for recovery test")
                else:
                    remaining_time = self._get_remaining_time()
                    api_logger.warning(f"Circuit breaker '{self.name}' OPEN - rejecting request for {remaining_time:.1f}s")
                    raise CircuitBreakerOpenError(
                        f"断路器 '{self.name}' 已打开，将在 {remaining_time:.1f} 秒后尝试恢复"
                    )

            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    api_logger.warning(f"Circuit breaker '{self.name}' in HALF_OPEN state, max calls reached")
                    raise CircuitBreakerOpenError(
                        f"断路器 '{self.name}' 在半开状态，已达到最大调用次数"
                    )
                self.half_open_calls += 1

        try:
            result = func(*args, **kwargs)

            # Call success handler outside the lock to avoid deadlocks
            self._on_success()
            return result

        except Exception as e:
            # Check if exception should trigger circuit breaker
            should_trigger = any(isinstance(e, exc_type) for exc_type in self.expected_exceptions)

            if should_trigger:
                self._on_failure(e)
            else:
                api_logger.debug(f"Exception {type(e).__name__} does not trigger circuit breaker for '{self.name}'")

            raise e

    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Success in half-open state closes the circuit
                self._to_closed()
                api_logger.info(f"Circuit breaker '{self.name}' CLOSED after success in HALF_OPEN state")
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in closed state
                self.failure_count = 0
                self.half_open_calls = 0

    def _on_failure(self, exception: Exception):
        """Handle failed call"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            api_logger.warning(f"Circuit breaker '{self.name}' failure #{self.failure_count}/{self.failure_threshold}: "
                             f"{type(exception).__name__}: {str(exception)[:100]}...")  # Limit log length
            
            if self.failure_count >= self.failure_threshold:
                self._to_open()
                api_logger.error(f"断路器 '{self.name}' 已打开！将在 {self.recovery_timeout} 秒后尝试恢复")

    def _to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitBreakerState.OPEN
        self.failure_count = 0  # Reset for next cycle
        self.half_open_calls = 0

    def _to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.half_open_calls = 0

    def _to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0
        self.last_failure_time = None

    def _allow_recovery(self) -> bool:
        """Check if enough time has passed to allow recovery"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _get_remaining_time(self) -> float:
        """Get remaining time until recovery attempt"""
        if self.last_failure_time is None:
            return self.recovery_timeout
        elapsed = time.time() - self.last_failure_time
        return max(0, self.recovery_timeout - elapsed)

    def get_state_info(self) -> dict:
        """Get current state information"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'remaining_time': self._get_remaining_time() if self.state == CircuitBreakerState.OPEN else 0,
            'recovery_timeout': self.recovery_timeout,
            'half_open_calls': self.half_open_calls,
            'half_open_max_calls': self.half_open_max_calls
        }

    def force_open(self):
        """Force the circuit breaker to OPEN state"""
        with self._lock:
            self._to_open()
            api_logger.warning(f"Circuit breaker '{self.name}' forced to OPEN state")

    def force_close(self):
        """Force the circuit breaker to CLOSED state"""
        with self._lock:
            self._to_closed()
            api_logger.info(f"Circuit breaker '{self.name}' forced to CLOSED state")


# Global circuit breaker instances for different AI platforms
_circuit_breakers = {}


def get_circuit_breaker(platform_name: str, model_name: str = None) -> CircuitBreaker:
    """
    Get or create a circuit breaker for a specific platform/model combination
    
    Args:
        platform_name: Name of the AI platform
        model_name: Name of the model (optional)
        
    Returns:
        CircuitBreaker instance for the platform/model
    """
    # Create a unique name for the circuit breaker
    name = f"{platform_name}_{model_name}" if model_name else platform_name
    
    if name not in _circuit_breakers:
        # Different platforms might have different thresholds
        if platform_name.lower() in ['doubao', 'doubao', 'bean']:
            # Doubao might be more sensitive to failures
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=3,    # Lower threshold for Doubao
                recovery_timeout=30,    # 30 second recovery time
                half_open_max_calls=1   # Only allow 1 test call in half-open state
            )
        elif platform_name.lower() in ['deepseek', 'deepseek', 'deepseek-coder']:
            # DeepSeek might have different characteristics
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=5,
                recovery_timeout=60,
                half_open_max_calls=1
            )
        else:
            # Default configuration
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=3,  # Lower threshold for better protection
                recovery_timeout=30,
                half_open_max_calls=1
            )
    
    return _circuit_breakers[name]


def reset_circuit_breaker(platform_name: str, model_name: str = None):
    """
    Reset the circuit breaker for a specific platform/model

    Args:
        platform_name: Name of the AI platform
        model_name: Name of the model (optional)
    """
    name = f"{platform_name}_{model_name}" if model_name else platform_name
    if name in _circuit_breakers:
        _circuit_breakers[name]._to_closed()  # Use internal method to transition to closed state
        api_logger.info(f"Circuit breaker for {name} reset to CLOSED state")


def reset_all_circuit_breakers():
    """
    Reset all circuit breakers to CLOSED state
    """
    for name, circuit_breaker in _circuit_breakers.items():
        circuit_breaker._to_closed()
        api_logger.info(f"Circuit breaker '{name}' reset to CLOSED state")
    api_logger.info(f"All {len(_circuit_breakers)} circuit breakers have been reset")


def get_all_circuit_breaker_states():
    """
    Get the state of all circuit breakers
    
    Returns:
        dict: Dictionary containing state information for all circuit breakers
    """
    states = {}
    for name, circuit_breaker in _circuit_breakers.items():
        states[name] = circuit_breaker.get_state_info()
    return states


# Decorator for easy integration
def circuit_breaker(platform_name: str, model_name: str = None):
    """
    Decorator to add circuit breaker protection to functions
    
    Args:
        platform_name: Name of the AI platform
        model_name: Name of the model (optional)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cb = get_circuit_breaker(platform_name, model_name)
            return cb.call(func, *args, **kwargs)
        return wrapper
    return decorator