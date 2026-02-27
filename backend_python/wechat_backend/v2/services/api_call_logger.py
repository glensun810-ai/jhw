"""
API 调用日志记录器

提供装饰器和直接调用方式，自动记录所有 AI 平台 API 调用。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import time
import traceback
import inspect
import logging
from datetime import datetime
from typing import Callable, Dict, Any, Optional, Awaitable, TypeVar
from functools import wraps

from wechat_backend.v2.models.api_call_log import APICallLog
from wechat_backend.v2.repositories.api_call_log_repository import APICallLogRepository
from wechat_backend.v2.utils.sanitizer import DataSanitizer
from wechat_backend.logging_config import api_logger

logger = logging.getLogger(__name__)

# 类型变量
T = TypeVar('T')


class APICallLogger:
    """
    API 调用日志记录器
    
    职责：
    1. 记录每次 API 调用的完整信息
    2. 提供装饰器方便自动记录
    3. 处理敏感信息脱敏
    4. 性能指标收集
    
    使用示例:
        >>> logger = APICallLogger()
        >>> 
        >>> # 方式 1: 直接记录
        >>> logger.log_success(
        ...     execution_id='exec-123',
        ...     brand='品牌 A',
        ...     question='问题',
        ...     model='deepseek',
        ...     request_data={'prompt': '...'},
        ...     response_data={'content': '...'},
        ...     latency_ms=1234
        ... )
        >>> 
        >>> # 方式 2: 使用装饰器
        >>> @logger.log_call(execution_id, brand, question, model, request_data)
        >>> async def call_ai_api(prompt: str) -> Dict:
        ...     pass
    """
    
    def __init__(self, repository: Optional[APICallLogRepository] = None):
        """
        初始化日志记录器
        
        Args:
            repository: 日志仓库实例（可选，默认创建新实例）
        """
        self.repository = repository or APICallLogRepository()
        
        api_logger.info(
            "api_call_logger_initialized",
            extra={
                'event': 'api_call_logger_initialized',
            }
        )
    
    def log_success(
        self,
        execution_id: str,
        brand: str,
        question: str,
        model: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        latency_ms: int,
        request_headers: Optional[Dict[str, str]] = None,
        response_headers: Optional[Dict[str, str]] = None,
        report_id: Optional[int] = None,
        retry_count: int = 0,
        api_version: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> int:
        """
        记录成功的 API 调用
        
        Args:
            execution_id: 执行 ID
            brand: 品牌名称
            question: 问题内容
            model: AI 模型名称
            request_data: 请求数据
            response_data: 响应数据
            latency_ms: 延迟（毫秒）
            request_headers: 请求头（可选）
            response_headers: 响应头（可选）
            report_id: 报告 ID（可选）
            retry_count: 重试次数
            api_version: API 版本
            request_id: 请求 ID
        
        Returns:
            int: 日志记录 ID
        """
        # 脱敏处理
        sanitized_request = DataSanitizer.sanitize_dict(request_data)
        sanitized_response = DataSanitizer.sanitize_dict(response_data)
        sanitized_request_headers = DataSanitizer.sanitize_headers(request_headers)
        sanitized_response_headers = DataSanitizer.sanitize_headers(response_headers)
        
        # 检查是否包含敏感信息
        has_sensitive = DataSanitizer.contains_sensitive_data(request_data) or \
                       DataSanitizer.contains_sensitive_data(response_data)
        
        # 创建日志对象
        log = APICallLog(
            execution_id=execution_id,
            brand=brand,
            question=question,
            model=model,
            request_data=sanitized_request,
            request_timestamp=datetime.now(),
            request_headers=sanitized_request_headers,
            response_data=sanitized_response,
            response_timestamp=datetime.now(),
            response_headers=sanitized_response_headers,
            status_code=200,
            success=True,
            latency_ms=latency_ms,
            report_id=report_id,
            retry_count=retry_count,
            api_version=api_version,
            request_id=request_id,
            has_sensitive_data=has_sensitive,
        )
        
        # 保存到数据库
        log_id = self.repository.create(log)
        
        api_logger.info(
            "api_call_logged_success",
            extra={
                'event': 'api_call_logged_success',
                'log_id': log_id,
                'execution_id': execution_id,
                'model': model,
                'latency_ms': latency_ms,
            }
        )
        
        return log_id
    
    def log_failure(
        self,
        execution_id: str,
        brand: str,
        question: str,
        model: str,
        request_data: Dict[str, Any],
        error: Exception,
        latency_ms: int,
        status_code: int = 500,
        request_headers: Optional[Dict[str, str]] = None,
        report_id: Optional[int] = None,
        retry_count: int = 0,
    ) -> int:
        """
        记录失败的 API 调用
        
        Args:
            execution_id: 执行 ID
            brand: 品牌名称
            question: 问题内容
            model: AI 模型名称
            request_data: 请求数据
            error: 异常对象
            latency_ms: 延迟（毫秒）
            status_code: HTTP 状态码
            request_headers: 请求头（可选）
            report_id: 报告 ID（可选）
            retry_count: 重试次数
        
        Returns:
            int: 日志记录 ID
        """
        # 脱敏处理
        sanitized_request = DataSanitizer.sanitize_dict(request_data)
        sanitized_request_headers = DataSanitizer.sanitize_headers(request_headers)
        
        # 检查是否包含敏感信息
        has_sensitive = DataSanitizer.contains_sensitive_data(request_data)
        
        # 创建日志对象
        log = APICallLog(
            execution_id=execution_id,
            brand=brand,
            question=question,
            model=model,
            request_data=sanitized_request,
            request_timestamp=datetime.now(),
            request_headers=sanitized_request_headers,
            status_code=status_code,
            success=False,
            error_message=str(error),
            error_stack=traceback.format_exc(),
            latency_ms=latency_ms,
            report_id=report_id,
            retry_count=retry_count,
            has_sensitive_data=has_sensitive,
        )
        
        # 保存到数据库
        log_id = self.repository.create(log)
        
        api_logger.warning(
            "api_call_logged_failure",
            extra={
                'event': 'api_call_logged_failure',
                'log_id': log_id,
                'execution_id': execution_id,
                'model': model,
                'error': str(error),
                'latency_ms': latency_ms,
            }
        )
        
        return log_id
    
    def log_call(
        self,
        execution_id: str,
        brand: str,
        question: str,
        model: str,
        request_data: Dict[str, Any],
        request_headers: Optional[Dict[str, str]] = None,
        report_id: Optional[int] = None,
        retry_count: int = 0,
    ) -> Callable:
        """
        记录 API 调用的装饰器工厂
        
        用法:
            @logger.log_call(execution_id, brand, question, model, request_data)
            async def call_ai_api():
                ...
        
        Args:
            execution_id: 执行 ID
            brand: 品牌名称
            question: 问题内容
            model: AI 模型名称
            request_data: 请求数据
            request_headers: 请求头（可选）
            report_id: 报告 ID（可选）
            retry_count: 重试次数
        
        Returns:
            Callable: 装饰器函数
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            if inspect.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    return await self._record_call_async(
                        func, execution_id, brand, question, model,
                        request_data, request_headers, report_id, retry_count,
                        *args, **kwargs
                    )
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self._record_call_sync(
                        func, execution_id, brand, question, model,
                        request_data, request_headers, report_id, retry_count,
                        *args, **kwargs
                    )
                return sync_wrapper
        
        return decorator
    
    async def _record_call_async(
        self,
        func: Callable[..., Awaitable[Dict[str, Any]]],
        execution_id: str,
        brand: str,
        question: str,
        model: str,
        request_data: Dict[str, Any],
        request_headers: Optional[Dict[str, str]],
        report_id: Optional[int],
        retry_count: int,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """记录异步 API 调用"""
        start_time = time.time()
        request_timestamp = datetime.now()
        
        # 脱敏请求数据
        sanitized_request = DataSanitizer.sanitize_dict(request_data)
        sanitized_headers = DataSanitizer.sanitize_headers(request_headers or {})
        has_sensitive = DataSanitizer.contains_sensitive_data(request_data)
        
        try:
            # 执行实际的 API 调用
            result = await func(*args, **kwargs)
            
            # 记录成功响应
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            # 提取响应信息
            response_data = result.get('data') if isinstance(result, dict) else result
            status_code = result.get('status_code', 200) if isinstance(result, dict) else 200
            request_id = result.get('request_id') if isinstance(result, dict) else None
            api_version = result.get('api_version') if isinstance(result, dict) else None
            response_headers = result.get('headers') if isinstance(result, dict) else None
            
            self.log_success(
                execution_id=execution_id,
                brand=brand,
                question=question,
                model=model,
                request_data=sanitized_request,
                response_data=response_data or {},
                latency_ms=latency_ms,
                request_headers=sanitized_headers,
                response_headers=response_headers,
                report_id=report_id,
                retry_count=retry_count,
                api_version=api_version,
                request_id=request_id,
            )
            
            return result
            
        except Exception as e:
            # 记录失败响应
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            self.log_failure(
                execution_id=execution_id,
                brand=brand,
                question=question,
                model=model,
                request_data=sanitized_request,
                error=e,
                latency_ms=latency_ms,
                status_code=getattr(e, 'status_code', 500),
                request_headers=sanitized_headers,
                report_id=report_id,
                retry_count=retry_count,
            )
            
            # 重新抛出异常
            raise
    
    def _record_call_sync(
        self,
        func: Callable[..., Dict[str, Any]],
        execution_id: str,
        brand: str,
        question: str,
        model: str,
        request_data: Dict[str, Any],
        request_headers: Optional[Dict[str, str]],
        report_id: Optional[int],
        retry_count: int,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """记录同步 API 调用"""
        start_time = time.time()
        request_timestamp = datetime.now()
        
        # 脱敏请求数据
        sanitized_request = DataSanitizer.sanitize_dict(request_data)
        sanitized_headers = DataSanitizer.sanitize_headers(request_headers or {})
        
        try:
            # 执行实际的 API 调用
            result = func(*args, **kwargs)
            
            # 记录成功响应
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            response_data = result.get('data') if isinstance(result, dict) else result
            status_code = result.get('status_code', 200) if isinstance(result, dict) else 200
            
            self.log_success(
                execution_id=execution_id,
                brand=brand,
                question=question,
                model=model,
                request_data=sanitized_request,
                response_data=response_data or {},
                latency_ms=latency_ms,
                request_headers=sanitized_headers,
                report_id=report_id,
                retry_count=retry_count,
            )
            
            return result
            
        except Exception as e:
            # 记录失败响应
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            self.log_failure(
                execution_id=execution_id,
                brand=brand,
                question=question,
                model=model,
                request_data=sanitized_request,
                error=e,
                latency_ms=latency_ms,
                status_code=getattr(e, 'status_code', 500),
                request_headers=sanitized_headers,
                report_id=report_id,
                retry_count=retry_count,
            )
            
            # 重新抛出异常
            raise
    
    def get_logs_for_execution(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """
        获取某次诊断的所有日志
        
        Args:
            execution_id: 执行 ID
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[APICallLog]: 日志列表
        """
        return self.repository.get_by_execution_id(execution_id, limit, offset)
    
    def get_statistics(
        self,
        execution_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取调用统计
        
        Args:
            execution_id: 执行 ID（可选）
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return self.repository.get_statistics(execution_id=execution_id)
