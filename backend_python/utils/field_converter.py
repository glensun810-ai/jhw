"""
Field Converter Utility

Convert snake_case (Python/Database convention) to camelCase (JavaScript/API convention)

Usage:
    from utils.field_converter import convert_response_to_camel, to_camel_case

Examples:
    >>> to_camel_case('execution_id')
    'executionId'
    
    >>> convert_response_to_camel({'brand_name': 'Test', 'selected_models': ['a', 'b']})
    {'brandName': 'Test', 'selectedModels': ['a', 'b']}

Author: Chief Full-Stack Engineer
Date: 2026-03-04
Version: 1.0
"""

from typing import Any, Dict, List, Union
from functools import lru_cache


@lru_cache(maxsize=256)
def to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case to camelCase
    
    Uses LRU cache for performance optimization
    
    Args:
        snake_str: snake_case string
        
    Returns:
        camelCase string
        
    Examples:
        >>> to_camel_case('execution_id')
        'executionId'
        >>> to_camel_case('brand_name')
        'brandName'
        >>> to_camel_case('is_completed')
        'isCompleted'
    """
    if not snake_str:
        return snake_str
    
    # Check if already camelCase (optimization)
    if '_' not in snake_str:
        return snake_str
    
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_response_to_camel(data: Any) -> Any:
    """
    Recursively convert dictionary keys from snake_case to camelCase
    
    Handles:
    - Dictionaries (converts keys)
    - Lists (recursively processes items)
    - Nested structures
    - Non-dict/list values (returns as-is)
    
    Args:
        data: Input data (dict, list, or any type)
        
    Returns:
        Converted data with camelCase keys
        
    Examples:
        >>> convert_response_to_camel({'execution_id': '123'})
        {'executionId': '123'}
        
        >>> convert_response_to_camel({
        ...     'brand_name': 'Test',
        ...     'selected_models': [{'model_name': 'a'}]
        ... })
        {'brandName': 'Test', 'selectedModels': [{'modelName': 'a'}]}
    """
    if isinstance(data, dict):
        return {
            to_camel_case(key): convert_response_to_camel(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            convert_response_to_camel(item) if isinstance(item, (dict, list)) else item
            for item in data
        ]
    else:
        # Primitive types (str, int, float, bool, None) - return as-is
        return data


def convert_request_to_snake(data: Any) -> Any:
    """
    Recursively convert dictionary keys from camelCase to snake_case
    
    Used for converting frontend requests to backend internal format
    
    Args:
        data: Input data (dict, list, or any type)
        
    Returns:
        Converted data with snake_case keys
    """
    if isinstance(data, dict):
        return {
            to_snake_case(key): convert_request_to_snake(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            convert_request_to_snake(item) if isinstance(item, (dict, list)) else item
            for item in data
        ]
    else:
        return data


@lru_cache(maxsize=256)
def to_snake_case(camel_str: str) -> str:
    """
    Convert camelCase to snake_case
    
    Args:
        camel_str: camelCase string
        
    Returns:
        snake_case string
        
    Examples:
        >>> to_snake_case('executionId')
        'execution_id'
        >>> to_snake_case('brandName')
        'brand_name'
    """
    if not camel_str:
        return camel_str
    
    # Check if already snake_case (optimization)
    if '_' in camel_str:
        return camel_str
    
    result = []
    for i, char in enumerate(camel_str):
        if char.isupper():
            if i > 0:
                result.append('_')
            result.append(char.lower())
        else:
            result.append(char)
    
    return ''.join(result)


def convert_api_response(data: Dict[str, Any], preserve_keys: List[str] = None) -> Dict[str, Any]:
    """
    Convert API response to camelCase with optional key preservation
    
    Args:
        data: Response data dictionary
        preserve_keys: List of keys to preserve as-is (not convert)
        
    Returns:
        Converted data with camelCase keys
        
    Example:
        >>> convert_api_response({
        ...     'execution_id': '123',
        ...     'data': {'brand_name': 'Test'}
        ... })
        {'executionId': '123', 'data': {'brandName': 'Test'}}
    """
    if preserve_keys is None:
        preserve_keys = []
    
    result = {}
    for key, value in data.items():
        if key in preserve_keys:
            result[key] = value
        else:
            result[to_camel_case(key)] = convert_response_to_camel(value)
    
    return result


# Convenience functions for specific use cases

def convert_state_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert state manager response to camelCase
    
    Args:
        state: State dictionary
        
    Returns:
        Converted state with camelCase keys
    """
    return convert_response_to_camel(state)


def convert_report_data(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert report data to camelCase
    
    Args:
        report: Report dictionary
        
    Returns:
        Converted report with camelCase keys
    """
    return convert_response_to_camel(report)


def convert_config_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert configuration data to camelCase
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Converted configuration with camelCase keys
    """
    return convert_response_to_camel(config)
