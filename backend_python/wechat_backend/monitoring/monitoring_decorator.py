#!/usr/bin/env python3
"""
增强的监控装饰器
提供API端点的自动监控和日志记录功能
"""

import time
import functools
from flask import request, g
from typing import Callable, Any
from wechat_backend.logging_config import api_logger
from wechat_backend.monitoring.metrics_collector import record_api_call, record_error
from wechat_backend.monitoring.logging_enhancements import (
    log_api_request,
    log_api_response,
    log_api_access,
    log_security_event
)
from wechat_backend.security.input_validation import validate_safe_text


def monitored_endpoint(
    endpoint_name: str,
    require_auth: bool = False,
    validate_inputs: bool = True,
    record_metrics: bool = True
):
    """
    监控装饰器，自动记录API请求、响应和错误指标
    
    :param endpoint_name: 端点名称
    :param require_auth: 是否需要身份验证
    :param validate_inputs: 是否验证输入
    :param record_metrics: 是否记录指标
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取用户ID（如果已认证）
            user_id = getattr(g, 'user_id', None)
            
            # 记录API请求
            log_api_request(
                method=request.method,
                endpoint=endpoint_name,
                user_id=user_id,
                ip_address=request.remote_addr,
                request_size=len(str(request.data))
            )
            
            start_time = time.time()
            
            try:
                # 验证输入（如果需要）
                if validate_inputs and request.is_json:
                    data = request.get_json()
                    if data:
                        # 验证数据安全性
                        if not validate_request_data(data):
                            log_security_event(
                                'INPUT_VALIDATION_FAILED', 
                                'HIGH', 
                                f'Unsafe input detected in {endpoint_name}',
                                user_id=user_id,
                                ip_address=request.remote_addr
                            )
                            return {'error': 'Invalid input data'}, 400
                
                # 执行原函数
                result = func(*args, **kwargs)
                
                # 确定响应状态码
                status_code = 200
                if isinstance(result, tuple):
                    response_data = result[0]
                    if len(result) > 1:
                        status_code = result[1]
                else:
                    response_data = result
                
                response_time = time.time() - start_time
                
                # 记录API响应
                response_size = len(str(response_data)) if response_data else 0
                log_api_response(
                    endpoint=endpoint_name,
                    status_code=status_code,
                    response_time=response_time,
                    response_size=response_size,
                    user_id=user_id
                )
                
                # 记录API调用指标
                if record_metrics:
                    record_api_call(
                        platform='api',
                        endpoint=endpoint_name,
                        status_code=status_code,
                        response_time=response_time,
                        request_size=len(str(request.data))
                    )
                
                # 记录访问日志
                log_api_access(
                    user_id=user_id or 'anonymous',
                    ip_address=request.remote_addr,
                    endpoint=endpoint_name,
                    method=request.method,
                    status_code=status_code
                )
                
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                
                # 记录错误
                log_api_response(
                    endpoint=endpoint_name,
                    status_code=500,
                    response_time=response_time
                )
                
                record_error('api', 'UNHANDLED_EXCEPTION', str(e))
                
                # 记录安全事件
                log_security_event(
                    'UNHANDLED_EXCEPTION', 
                    'MEDIUM', 
                    f'Unhandled exception in {endpoint_name}: {str(e)}',
                    user_id=user_id,
                    ip_address=request.remote_addr,
                    error=str(e)
                )
                
                # 重新抛出异常或返回错误响应
                api_logger.error(f"Unhandled exception in {endpoint_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator


def validate_request_data(data: dict) -> bool:
    """
    验证请求数据的安全性
    """
    if not isinstance(data, dict):
        return False
    
    # 递归验证字典中的所有字符串值
    def validate_recursive(obj):
        if isinstance(obj, str):
            return validate_safe_text(obj, max_length=10000)
        elif isinstance(obj, dict):
            return all(validate_recursive(v) for v in obj.values())
        elif isinstance(obj, list):
            return all(validate_recursive(item) for item in obj)
        else:
            # 非字符串、字典或列表的值被认为是安全的
            return True
    
    return validate_recursive(data)


def setup_default_alerts():
    """
    设置默认的告警规则
    """
    from .monitoring.alert_system import get_alert_system, Alert, AlertCondition, AlertSeverity

    alert_system = get_alert_system()

    # API错误率过高告警
    error_rate_condition = AlertCondition(
        metric_name="errors_total_api",
        threshold=0.1,  # 错误率超过10%
        comparison=">",
        time_window_minutes=5,
        consecutive_violations=2
    )

    error_rate_alert = Alert(
        name="high_error_rate",
        condition=error_rate_condition,
        severity=AlertSeverity.HIGH,
        description="API错误率过高",
        notification_targets=["admin@example.com"]
    )

    alert_system.add_alert(error_rate_alert)

    # 响应时间过长告警
    slow_response_condition = AlertCondition(
        metric_name="response_time_api",
        threshold=5.0,  # 响应时间超过5秒
        comparison=">",
        time_window_minutes=5,
        consecutive_violations=2
    )

    slow_response_alert = Alert(
        name="slow_response_time",
        condition=slow_response_condition,
        severity=AlertSeverity.MEDIUM,
        description="API平均响应时间过长",
        notification_targets=["admin@example.com"]
    )

    alert_system.add_alert(slow_response_alert)

    # 安全事件告警
    security_event_condition = AlertCondition(
        metric_name="security_events",
        threshold=5,  # 安全事件超过5次
        comparison=">",
        time_window_minutes=10,
        consecutive_violations=1
    )

    security_event_alert = Alert(
        name="high_severity_security_events",
        condition=security_event_condition,
        severity=AlertSeverity.CRITICAL,
        description="安全事件过多",
        notification_targets=["security@example.com"]
    )

    alert_system.add_alert(security_event_alert)

    print("✓ 已设置默认告警规则")


# 便捷函数
def log_api_call_metric(platform: str, endpoint: str, status_code: int, response_time: float):
    """便捷函数：记录API调用指标"""
    record_api_call(platform, endpoint, status_code, response_time)


def log_error_metric(platform: str, error_type: str, error_message: str = ""):
    """便捷函数：记录错误指标"""
    record_error(platform, error_type, error_message)


def start_monitoring_system():
    """启动监控系统"""
    from .monitoring.alert_system import start_alert_monitoring
    setup_default_alerts()
    start_alert_monitoring()
    print("✓ 监控系统已启动")