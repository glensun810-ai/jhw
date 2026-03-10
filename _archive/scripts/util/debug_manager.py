import functools
import sys
from datetime import datetime

# Global debug mode switch
GEO_DEBUG_MODE = True


def debug_log(tag, message):
    """
    Unified debug logging function that outputs messages with a consistent format.
    
    Args:
        tag (str): The stage label for the debug message
        message (str): The actual debug message content
    """
    if GEO_DEBUG_MODE:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        formatted_message = f"[GEO-DEBUG][{tag}] {message}"
        print(f"[{timestamp}] {formatted_message}")
        sys.stdout.flush()


def debug_log_with_tags(tag):
    """
    Decorator to add debug logging to functions with a specific tag.
    
    Args:
        tag (str): The stage label for the debug message
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            debug_log(tag, f"Entering {func.__name__}")
            try:
                result = func(*args, **kwargs)
                debug_log(tag, f"Exiting {func.__name__} successfully")
                return result
            except Exception as e:
                debug_log("EXCEPTION", f"Exception in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator


# Convenience functions for specific tags
def ai_io_log(message):
    """Log AI I/O related messages"""
    debug_log("AI_IO", message)


def status_flow_log(message):
    """Log status flow related messages"""
    debug_log("STATUS_FLOW", message)


def exception_log(message):
    """Log exception related messages"""
    debug_log("EXCEPTION", message)