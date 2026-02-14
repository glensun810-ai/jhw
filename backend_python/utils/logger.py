import sys
import traceback
from datetime import datetime

# Global switch for debug logging
ENABLE_DEBUG_AI_CODE = True


def debug_log(module_name, execution_id=None, message=""):
    """
    Unified debug logging function that outputs messages with a consistent format.
    
    Format: 2026-02-14 18:30:05 [DEBUG_AI_CODE] [<module_name>] [ID:<execution_id>] <message>
    
    Args:
        module_name (str): Name of the module where the log is called from
        execution_id (str, optional): Unique execution identifier for tracking
        message (str): The actual debug message content
    """
    if not ENABLE_DEBUG_AI_CODE:
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Build the log message
    log_parts = [
        timestamp,
        "[DEBUG_AI_CODE]",
        f"[{module_name}]"
    ]
    
    if execution_id:
        log_parts.append(f"[ID:{execution_id}]")
    
    log_parts.append(message)
    
    formatted_message = " ".join(log_parts)
    print(formatted_message)
    sys.stdout.flush()


def debug_log_ai_io(module_name, execution_id, prompt_summary, response_summary):
    """
    Specialized function for logging AI I/O operations.
    
    Args:
        module_name (str): Name of the module
        execution_id (str): Unique execution identifier
        prompt_summary (str): Summary of the input prompt
        response_summary (str): Summary of the AI response
    """
    if not ENABLE_DEBUG_AI_CODE:
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Log input prompt
    input_msg = f"{timestamp} [DEBUG_AI_CODE] [{module_name}] [ID:{execution_id}] INPUT PROMPT: {prompt_summary}"
    print(input_msg)
    
    # Log AI response
    output_msg = f"{timestamp} [DEBUG_AI_CODE] [{module_name}] [ID:{execution_id}] AI RESPONSE: {response_summary}"
    print(output_msg)
    
    sys.stdout.flush()


def debug_log_exception(module_name, execution_id, error_message):
    """
    Specialized function for logging exceptions with traceback.
    
    Args:
        module_name (str): Name of the module
        execution_id (str): Unique execution identifier
        error_message (str): The error message with traceback
    """
    if not ENABLE_DEBUG_AI_CODE:
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add ERROR_TRACE identifier as requested
    formatted_message = f"{timestamp} [DEBUG_AI_CODE] [{module_name}] [ID:{execution_id}] [ERROR_TRACE] {error_message}"
    print(formatted_message)
    sys.stdout.flush()


def debug_log_status_flow(module_name, execution_id, old_stage, new_stage, progress_value):
    """
    Specialized function for logging status flow transitions.
    
    Args:
        module_name (str): Name of the module
        execution_id (str): Unique execution identifier
        old_stage (str): Previous stage
        new_stage (str): New stage
        progress_value (int): Progress percentage
    """
    if not ENABLE_DEBUG_AI_CODE:
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    formatted_message = f"{timestamp} [DEBUG_AI_CODE] [{module_name}] [ID:{execution_id}] STAGE CHANGE: {old_stage} -> {new_stage}, PROGRESS: {progress_value}%"
    print(formatted_message)
    sys.stdout.flush()


def debug_log_results(module_name, execution_id, results_length, first_element_summary=""):
    """
    Specialized function for logging results data.
    
    Args:
        module_name (str): Name of the module
        execution_id (str): Unique execution identifier
        results_length (int): Length of results array
        first_element_summary (str): Summary of first element
    """
    if not ENABLE_DEBUG_AI_CODE:
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    formatted_message = f"{timestamp} [DEBUG_AI_CODE] [{module_name}] [ID:{execution_id}] RESULTS COUNT: {results_length}, FIRST ELEMENT: {first_element_summary}"
    print(formatted_message)
    sys.stdout.flush()