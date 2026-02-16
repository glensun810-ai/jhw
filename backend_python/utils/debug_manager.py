"""
调试日志管理模块
提供统一的日志记录接口，用于调试和监控
"""

import logging
from datetime import datetime
from typing import Any, Optional


def debug_log(category: str, execution_id: str, message: str) -> None:
    """
    记录调试日志
    
    Args:
        category: 日志类别
        execution_id: 执行ID
        message: 日志消息
    """
    logger = logging.getLogger('debug')
    logger.info(f"[{category}] [{execution_id}] {message}")


def ai_io_log(execution_id: str, platform: str, question: str, response: str) -> None:
    """
    记录AI输入输出日志
    
    Args:
        execution_id: 执行ID
        platform: AI平台名称
        question: 问题
        response: 响应
    """
    logger = logging.getLogger('ai_io')
    logger.info(f"[{execution_id}] [{platform}] Question: {question[:100]}... Response: {response[:200]}...")


def status_flow_log(execution_id: str, stage: str, status: str, details: Optional[str] = None) -> None:
    """
    记录状态流转日志
    
    Args:
        execution_id: 执行ID
        stage: 阶段
        status: 状态
        details: 详细信息
    """
    logger = logging.getLogger('status_flow')
    msg = f"[{execution_id}] Stage: {stage}, Status: {status}"
    if details:
        msg += f", Details: {details}"
    logger.info(msg)


def exception_log(execution_id: str, error_type: str, error_message: str, traceback_info: Optional[str] = None) -> None:
    """
    记录异常日志
    
    Args:
        execution_id: 执行ID
        error_type: 错误类型
        error_message: 错误消息
        traceback_info: 堆栈跟踪信息
    """
    logger = logging.getLogger('exception')
    msg = f"[{execution_id}] {error_type}: {error_message}"
    if traceback_info:
        msg += f"\nTraceback: {traceback_info}"
    logger.error(msg)


def results_log(execution_id: str, results: Any) -> None:
    """
    记录结果日志
    
    Args:
        execution_id: 执行ID
        results: 结果数据
    """
    logger = logging.getLogger('results')
    logger.info(f"[{execution_id}] Results: {str(results)[:500]}...")


def enable_debug_logging():
    """
    启用调试日志记录
    """
    # 设置日志级别
    for name in ['debug', 'ai_io', 'status_flow', 'exception', 'results']:
        logging.getLogger(name).setLevel(logging.INFO)


def disable_debug_logging():
    """
    禁用调试日志记录
    """
    # 设置日志级别
    for name in ['debug', 'ai_io', 'status_flow', 'exception', 'results']:
        logging.getLogger(name).setLevel(logging.WARNING)