"""
增强日志系统
提供结构化日志记录和安全审计功能
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
from enum import Enum

# 定义专门的日志记录器
audit_logger = logging.getLogger("audit")
security_logger = logging.getLogger("security")
api_logger = logging.getLogger("api")


class LogEventType(Enum):
    """日志事件类型"""
    API_CALL = "api_call"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    SECURITY_EVENT = "security_event"
    SYSTEM_ERROR = "system_error"


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_structured(self, level: int, event_type: LogEventType, message: str, **kwargs):
        """记录结构化日志"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "message": message,
            "details": kwargs
        }
        
        self.logger.log(level, json.dumps(log_entry, ensure_ascii=False))
    
    def info(self, event_type: LogEventType, message: str, **kwargs):
        """信息级别日志"""
        self._log_structured(logging.INFO, event_type, message, **kwargs)
    
    def warning(self, event_type: LogEventType, message: str, **kwargs):
        """警告级别日志"""
        self._log_structured(logging.WARNING, event_type, message, **kwargs)
    
    def error(self, event_type: LogEventType, message: str, **kwargs):
        """错误级别日志"""
        self._log_structured(logging.ERROR, event_type, message, **kwargs)
    
    def critical(self, event_type: LogEventType, message: str, **kwargs):
        """严重级别日志"""
        self._log_structured(logging.CRITICAL, event_type, message, **kwargs)


class AuditLogger(StructuredLogger):
    """审计日志记录器"""
    
    def __init__(self):
        super().__init__("audit")
    
    def log_api_access(self, user_id: str, ip_address: str, endpoint: str, method: str, status_code: int):
        """记录API访问"""
        self.info(
            LogEventType.API_CALL,
            "API访问记录",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            method=method,
            status_code=status_code
        )
    
    def log_authentication(self, username: str, success: bool, ip_address: str = None, reason: str = None):
        """记录身份验证"""
        self.info(
            LogEventType.AUTHENTICATION,
            f"身份验证{'成功' if success else '失败'}",
            username=username,
            success=success,
            ip_address=ip_address,
            reason=reason
        )
    
    def log_authorization(self, user_id: str, resource: str, action: str, granted: bool, reason: str = None):
        """记录授权"""
        self.info(
            LogEventType.AUTHORIZATION,
            f"授权{'通过' if granted else '拒绝'}",
            user_id=user_id,
            resource=resource,
            action=action,
            granted=granted,
            reason=reason
        )
    
    def log_data_access(self, user_id: str, resource: str, action: str, success: bool):
        """记录数据访问"""
        self.info(
            LogEventType.DATA_ACCESS,
            f"数据访问{'成功' if success else '失败'}",
            user_id=user_id,
            resource=resource,
            action=action,
            success=success
        )
    
    def log_config_change(self, user_id: str, config_key: str, old_value: str, new_value: str):
        """记录配置变更"""
        self.info(
            LogEventType.CONFIG_CHANGE,
            "配置变更",
            user_id=user_id,
            config_key=config_key,
            old_value=old_value,
            new_value=new_value
        )


class SecurityLogger(StructuredLogger):
    """安全日志记录器"""
    
    def __init__(self):
        super().__init__("security")
    
    def log_security_event(self, event_type: str, severity: str, description: str, **details):
        """记录安全事件"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            f"安全事件: {description}",
            event_type=event_type,
            severity=severity,
            **details
        )
    
    def log_potential_attack(self, attack_type: str, ip_address: str, user_agent: str = None, **details):
        """记录潜在攻击"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            f"检测到潜在{attack_type}攻击",
            attack_type=attack_type,
            ip_address=ip_address,
            user_agent=user_agent,
            **details
        )
    
    def log_brute_force_attempt(self, username: str, ip_address: str, attempts: int):
        """记录暴力破解尝试"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            "暴力破解尝试",
            username=username,
            ip_address=ip_address,
            attempts=attempts
        )
    
    def log_unauthorized_access(self, user_id: str, resource: str, ip_address: str):
        """记录未授权访问"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            "未授权访问尝试",
            user_id=user_id,
            resource=resource,
            ip_address=ip_address
        )
    
    def log_privilege_escalation(self, user_id: str, attempted_privilege: str, ip_address: str):
        """记录权限提升尝试"""
        self.warning(
            LogEventType.SECURITY_EVENT,
            "权限提升尝试",
            user_id=user_id,
            attempted_privilege=attempted_privilege,
            ip_address=ip_address
        )


class APILogger(StructuredLogger):
    """API日志记录器"""
    
    def __init__(self):
        super().__init__("api")
    
    def log_request(self, 
                   method: str, 
                   endpoint: str, 
                   user_id: str = None, 
                   ip_address: str = None, 
                   request_size: int = 0):
        """记录API请求"""
        self.info(
            LogEventType.API_CALL,
            "API请求接收",
            method=method,
            endpoint=endpoint,
            user_id=user_id,
            ip_address=ip_address,
            request_size=request_size
        )
    
    def log_response(self, 
                    endpoint: str, 
                    status_code: int, 
                    response_time: float, 
                    response_size: int = 0,
                    user_id: str = None):
        """记录API响应"""
        self.info(
            LogEventType.API_CALL,
            "API响应发送",
            endpoint=endpoint,
            status_code=status_code,
            response_time=response_time,
            response_size=response_size,
            user_id=user_id
        )
    
    def log_error(self, 
                  endpoint: str, 
                  status_code: int, 
                  error_message: str, 
                  user_id: str = None,
                  traceback_info: str = None):
        """记录API错误"""
        self.error(
            LogEventType.SYSTEM_ERROR,
            "API错误",
            endpoint=endpoint,
            status_code=status_code,
            error_message=error_message,
            user_id=user_id,
            traceback=traceback_info
        )


# 全局日志记录器实例
_audit_logger = None
_security_logger = None
_api_logger = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志记录器"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_security_logger() -> SecurityLogger:
    """获取安全日志记录器"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger


def get_api_logger() -> APILogger:
    """获取API日志记录器"""
    global _api_logger
    if _api_logger is None:
        _api_logger = APILogger()
    return _api_logger


# 便捷函数
def log_api_access(user_id: str, ip_address: str, endpoint: str, method: str, status_code: int):
    """便捷函数：记录API访问"""
    logger = get_audit_logger()
    logger.log_api_access(user_id, ip_address, endpoint, method, status_code)


def log_security_event(event_type: str, severity: str, description: str, **details):
    """便捷函数：记录安全事件"""
    logger = get_security_logger()
    logger.log_security_event(event_type, severity, description, **details)


def log_api_request(method: str, endpoint: str, user_id: str = None, ip_address: str = None, request_size: int = 0):
    """便捷函数：记录API请求"""
    logger = get_api_logger()
    logger.log_request(method, endpoint, user_id, ip_address, request_size)


def log_api_response(endpoint: str, status_code: int, response_time: float, response_size: int = 0, user_id: str = None):
    """便捷函数：记录API响应"""
    logger = get_api_logger()
    logger.log_response(endpoint, status_code, response_time, response_size, user_id)
