"""
容错执行器

功能：
- 为所有外部调用提供统一的 try-catch 包裹
- 将技术异常转换为用户友好的错误信息
- 支持超时控制
- 记录详细错误日志但不中断主流程

核心原则：
1. 任何外部调用都不能中断主流程
2. 错误信息必须对用户友好
3. 详细错误必须记录到日志供调试
4. 支持超时控制，防止卡死
"""

import asyncio
import traceback
from typing import Callable, Any, Dict, Optional, List
from datetime import datetime
from enum import Enum

from wechat_backend.logging_config import api_logger


class ErrorType(Enum):
    """错误类型枚举"""
    TIMEOUT = "timeout"
    QUOTA_EXHAUSTED = "quota_exhausted"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"  # P0-3 新增：独立的频率限制错误类型
    INVALID_API_KEY = "invalid_api_key"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"


class FaultTolerantResult:
    """容错执行结果"""
    
    def __init__(
        self,
        status: str = "failed",
        data: Optional[Any] = None,
        error_message: Optional[str] = None,
        error_type: Optional[ErrorType] = None,
        error_details: Optional[str] = None,
        source: Optional[str] = None,
        execution_time: Optional[float] = None
    ):
        self.status = status  # "success" or "failed"
        self.data = data
        self.error_message = error_message  # 用户友好的错误信息
        self.error_type = error_type  # 错误类型
        self.error_details = error_details  # 详细错误信息（用于日志）
        self.source = source  # 数据源
        self.execution_time = execution_time  # 执行耗时
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "data": self.data,
            "error_message": self.error_message,
            "error_type": self.error_type.value if self.error_type else None,
            "error_details": self.error_details,
            "source": self.source,
            "execution_time": self.execution_time
        }
    
    @classmethod
    def success(cls, data: Any, source: str = None, execution_time: float = None) -> 'FaultTolerantResult':
        """创建成功结果"""
        return cls(
            status="success",
            data=data,
            source=source,
            execution_time=execution_time
        )
    
    @classmethod
    def failed(
        cls,
        error_message: str,
        error_type: ErrorType = ErrorType.UNKNOWN,
        error_details: str = None,
        source: str = None
    ) -> 'FaultTolerantResult':
        """创建失败结果"""
        return cls(
            status="failed",
            error_message=error_message,
            error_type=error_type,
            error_details=error_details,
            source=source
        )


class FaultTolerantExecutor:
    """
    容错执行器
    
    用法：
        executor = FaultTolerantExecutor(timeout_seconds=10)
        result = await executor.execute_with_fallback(
            task_func=some_api_call,
            task_name="社交媒体分析",
            source="weibo",
            *args,
            **kwargs
        )
        
        if result.status == "success":
            # 处理成功数据
            process(result.data)
        else:
            # 处理失败情况
            log_error(result.error_message)
    """
    
    # 错误关键词映射（用于识别错误类型）
    ERROR_KEYWORDS = {
        ErrorType.QUOTA_EXHAUSTED: ["quota", "配额", "limit", "限制", "insufficient"],
        ErrorType.INVALID_API_KEY: ["api key", "authentication", "unauthorized", "401", "密钥", "认证"],
        ErrorType.SERVICE_UNAVAILABLE: ["503", "unavailable", "maintenance", "维护"],
        ErrorType.NETWORK_ERROR: ["network", "connection", "timeout", "connect", "网络", "连接"],
    }
    
    def __init__(self, timeout_seconds: int = 10):
        """
        初始化容错执行器
        
        参数：
            timeout_seconds: 单个任务的超时时间（秒）
        """
        self.timeout_seconds = timeout_seconds
    
    async def execute_with_fallback(
        self,
        task_func: Callable,
        task_name: str,
        source: str = None,
        *args,
        **kwargs
    ) -> FaultTolerantResult:
        """
        带降级的执行
        
        参数：
            task_func: 要执行的任务函数（可以是同步或异步）
            task_name: 任务名称（用于错误提示）
            source: 数据源（用于错误提示）
            *args: 传递给 task_func 的位置参数
            **kwargs: 传递给 task_func 的关键字参数
        
        返回：
            FaultTolerantResult: 执行结果（永远不抛出异常）
        """
        start_time = datetime.now()
        
        try:
            # 判断是同步函数还是异步函数
            if asyncio.iscoroutinefunction(task_func):
                # 异步函数
                data = await asyncio.wait_for(
                    task_func(*args, **kwargs),
                    timeout=self.timeout_seconds
                )
            else:
                # 同步函数，在线程池中执行
                loop = asyncio.get_event_loop()
                data = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: task_func(*args, **kwargs)),
                    timeout=self.timeout_seconds
                )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 成功
            api_logger.info(f"[FaultTolerant] ✅ {task_name} 执行成功，耗时：{execution_time:.2f}s")
            return FaultTolerantResult.success(
                data=data,
                source=source,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"【{task_name}】数据源响应超时（{self.timeout_seconds}秒），请稍后重试"
            
            api_logger.warning(f"[FaultTolerant] ⚠️ {task_name} 执行超时，耗时：{execution_time:.2f}s")
            
            return FaultTolerantResult.failed(
                error_message=error_msg,
                error_type=ErrorType.TIMEOUT,
                error_details=f"Task '{task_name}' timed out after {self.timeout_seconds}s",
                source=source
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 识别错误类型
            error_type = self._identify_error_type(e)
            
            # 生成用户友好的错误信息
            user_friendly_msg = self._generate_user_friendly_error(
                error_type=error_type,
                task_name=task_name,
                original_error=str(e)
            )
            
            # 记录详细错误日志
            error_details = self._format_error_details(e, task_name, source)
            api_logger.error(f"[FaultTolerant] ❌ {task_name} 执行失败：{error_details}")
            
            return FaultTolerantResult.failed(
                error_message=user_friendly_msg,
                error_type=error_type,
                error_details=error_details,
                source=source
            )
    
    def collect_result(
        self,
        brand: str,
        question: str,
        model: str,
        response: Any,
        geo_data: Dict[str, Any],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        收集诊断结果
        
        参数:
            brand: 品牌名称
            question: 问题
            model: AI 模型名称
            response: AI 响应
            geo_data: GEO 解析数据
            error: 错误信息（如果有）
        
        返回:
            结果字典
        """
        return {
            "brand": brand,
            "question": question,
            "model": model,
            "response": response,
            "geo_data": geo_data,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
    
    def _identify_error_type(self, exception: Exception) -> ErrorType:
        """识别错误类型"""
        error_str = str(exception).lower()
        
        # 检查是否为 AI 响应对象
        if hasattr(exception, 'error_type'):
            # 如果是 AIResponse 错误，直接返回对应的错误类型
            from wechat_backend.ai_adapters.base_adapter import AIErrorType
            if isinstance(exception.error_type, AIErrorType):
                return self._map_ai_error_to_fault_tolerant_error(exception.error_type)
        
        # 根据关键词匹配错误类型
        for error_type, keywords in self.ERROR_KEYWORDS.items():
            if any(keyword in error_str for keyword in keywords):
                return error_type
        
        # 默认为未知错误
        return ErrorType.UNKNOWN
    
    def _map_ai_error_to_fault_tolerant_error(self, ai_error_type) -> ErrorType:
        """将 AI 错误类型映射到容错错误类型"""
        from wechat_backend.ai_adapters.base_adapter import AIErrorType

        # P0-3 修复：保持 RATE_LIMIT_EXCEEDED 独立，不丢失错误信息
        mapping = {
            AIErrorType.INVALID_API_KEY: ErrorType.INVALID_API_KEY,
            AIErrorType.INSUFFICIENT_QUOTA: ErrorType.QUOTA_EXHAUSTED,
            AIErrorType.RATE_LIMIT_EXCEEDED: ErrorType.RATE_LIMIT_EXCEEDED,  # 保持独立类型
            AIErrorType.SERVER_ERROR: ErrorType.SERVICE_UNAVAILABLE,
            AIErrorType.SERVICE_UNAVAILABLE: ErrorType.SERVICE_UNAVAILABLE,
        }

        return mapping.get(ai_error_type, ErrorType.UNKNOWN)
    
    def _generate_user_friendly_error(
        self,
        error_type: ErrorType,
        task_name: str,
        original_error: str
    ) -> str:
        """生成用户友好的错误信息"""

        error_templates = {
            ErrorType.TIMEOUT: f"【{task_name}】数据源响应超时，请稍后重试",
            ErrorType.QUOTA_EXHAUSTED: f"【{task_name}】AI 平台配额已用尽，此部分结果暂缺。请提醒管理员充值。",
            ErrorType.RATE_LIMIT_EXCEEDED: f"【{task_name}】请求过于频繁，请稍后重试",  # P0-3 新增
            ErrorType.INVALID_API_KEY: f"【{task_name}】API 密钥配置错误，请联系技术支持。",
            ErrorType.NETWORK_ERROR: f"【{task_name}】网络连接中断，请检查网络后重试。",
            ErrorType.SERVICE_UNAVAILABLE: f"【{task_name}】服务暂时不可用，请稍后重试。",
            ErrorType.PARSE_ERROR: f"【{task_name}】数据解析失败，技术团队已收到通知。",
            ErrorType.UNKNOWN: f"【{task_name}】数据获取或处理时发生未知错误，已跳过。",
        }

        return error_templates.get(error_type, error_templates[ErrorType.UNKNOWN])
    
    def _format_error_details(
        self,
        exception: Exception,
        task_name: str,
        source: str
    ) -> str:
        """格式化详细错误信息（用于日志）"""
        error_details = [
            f"Task: {task_name}",
            f"Source: {source or 'unknown'}",
            f"Error Type: {type(exception).__name__}",
            f"Error Message: {str(exception)}",
            f"Traceback:\n{traceback.format_exc()}"
        ]
        
        return " | ".join(error_details)


class BatchFaultTolerantExecutor:
    """
    批量容错执行器
    
    用于并发执行多个任务，每个任务都有独立的容错保护
    
    用法：
        executor = BatchFaultTolerantExecutor(timeout_seconds=10, max_concurrent=5)
        tasks = [
            {"func": task1, "name": "任务 1", "source": "source1"},
            {"func": task2, "name": "任务 2", "source": "source2"},
        ]
        results = await executor.execute_batch(tasks)
        
        for result in results:
            if result.status == "success":
                process(result.data)
            else:
                log_error(result.error_message)
    """
    
    def __init__(self, timeout_seconds: int = 10, max_concurrent: int = 5):
        """
        初始化批量容错执行器
        
        参数：
            timeout_seconds: 单个任务的超时时间
            max_concurrent: 最大并发数
        """
        self.executor = FaultTolerantExecutor(timeout_seconds)
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[FaultTolerantResult]:
        """
        批量执行任务
        
        参数：
            tasks: 任务列表，每个任务是一个字典：
                   {"func": task_func, "name": task_name, "source": source, "args": [...], "kwargs": {...}}
        
        返回：
            List[FaultTolerantResult]: 所有任务的执行结果
        """
        async def execute_with_semaphore(task: Dict[str, Any]) -> FaultTolerantResult:
            async with self._semaphore:
                return await self.executor.execute_with_fallback(
                    task_func=task["func"],
                    task_name=task["name"],
                    source=task.get("source"),
                    *task.get("args", []),
                    **task.get("kwargs", {})
                )
        
        # 并发执行所有任务
        results = await asyncio.gather(*[
            execute_with_semaphore(task) for task in tasks
        ])
        
        return results
    
    def get_statistics(self, results: List[FaultTolerantResult]) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        参数：
            results: 执行结果列表
        
        返回：
            统计信息字典
        """
        total = len(results)
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = total - success_count
        
        # 按错误类型分组
        error_by_type = {}
        for result in results:
            if result.status == "failed" and result.error_type:
                error_type = result.error_type.value
                error_by_type[error_type] = error_by_type.get(error_type, 0) + 1
        
        # 平均执行时间
        successful_times = [r.execution_time for r in results if r.status == "success" and r.execution_time]
        avg_execution_time = sum(successful_times) / len(successful_times) if successful_times else 0
        
        return {
            "total": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "success_rate": success_count / total if total > 0 else 0,
            "error_by_type": error_by_type,
            "avg_execution_time": avg_execution_time
        }


# 便捷函数
def safe_json_serialize(obj: Any, default_value: Any = None) -> Any:
    """
    安全的 JSON 序列化
    
    参数：
        obj: 要序列化的对象
        default_value: 序列化失败时的默认值
    
    返回：
        序列化后的对象，或默认值
    """
    import json
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False, default=str))
    except Exception as e:
        api_logger.error(f"[safe_json_serialize] 序列化失败：{e}")
        return default_value


# 全局执行器实例（方便直接使用）
_global_executor = FaultTolerantExecutor(timeout_seconds=10)

async def execute_with_fallback(task_func: Callable, task_name: str, source: str = None, *args, **kwargs) -> FaultTolerantResult:
    """
    便捷函数：使用全局执行器执行任务
    
    用法：
        result = await execute_with_fallback(some_api_call, "任务名称", "数据源")
    """
    return await _global_executor.execute_with_fallback(task_func, task_name, source, *args, **kwargs)
