"""
多模型 Fallback 装饰器

功能：
1. 当主模型调用失败时，自动尝试备用模型
2. 支持配置备用模型列表
3. 记录每次 fallback 事件
4. 与重试机制协同工作

@author: 系统架构组
@date: 2026-03-07
@version: 1.0.0
"""

import asyncio
import time
from typing import Callable, Any, Optional, List, Dict, Tuple
from functools import wraps
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIResponse


# 【P2 修复 - 2026-03-07】备用模型配置
FALLBACK_MODEL_CONFIG = {
    # 主模型 -> [备用模型列表]
    'doubao': ['qwen', 'deepseek'],
    'qwen': ['doubao', 'deepseek'],
    'deepseek': ['doubao', 'qwen'],
    'doubao-pro': ['doubao', 'qwen', 'deepseek'],
}


class FallbackResult:
    """Fallback 结果"""
    
    def __init__(
        self,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        attempted_models: List[str] = None,
        successful_model: Optional[str] = None
    ):
        self.success = success
        self.result = result
        self.error = error
        self.attempted_models = attempted_models or []
        self.successful_model = successful_model
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'attempted_models': self.attempted_models,
            'successful_model': self.successful_model
        }


def with_model_fallback(
    primary_model: str,
    fallback_models: Optional[List[str]] = None,
    max_fallbacks: int = 3
):
    """
    多模型 Fallback 装饰器
    
    用法:
        @with_model_fallback('doubao', fallback_models=['qwen', 'deepseek'])
        async def call_ai(model_name, prompt, **kwargs):
            # AI 调用逻辑
            pass
    
    参数:
        primary_model: 主模型名称
        fallback_models: 备用模型列表（可选，默认从 FALLBACK_MODEL_CONFIG 获取）
        max_fallbacks: 最大 fallback 次数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> FallbackResult:
            # 确定备用模型列表
            if fallback_models is None:
                fallback_models = FALLBACK_MODEL_CONFIG.get(primary_model, [])
            
            # 构建模型尝试列表：主模型 + 备用模型
            model_queue = [primary_model] + fallback_models[:max_fallbacks]
            
            attempted_models = []
            last_error = None
            
            for model_name in model_queue:
                attempted_models.append(model_name)
                
                try:
                    api_logger.info(
                        f"[ModelFallback] 尝试模型：{model_name} "
                        f"(attempt={len(attempted_models)}/{len(model_queue)})"
                    )
                    
                    # 调用原函数
                    result = await func(model_name=model_name, *args, **kwargs)
                    
                    # 检查返回结果
                    if isinstance(result, AIResponse):
                        if result.success:
                            # 成功
                            api_logger.info(
                                f"[ModelFallback] ✅ 模型 {model_name} 调用成功"
                            )
                            return FallbackResult(
                                success=True,
                                result=result,
                                attempted_models=attempted_models,
                                successful_model=model_name
                            )
                        else:
                            # AI 响应失败
                            last_error = result.error_message
                            api_logger.warning(
                                f"[ModelFallback] ⚠️ 模型 {model_name} 响应失败：{last_error}"
                            )
                    elif isinstance(result, dict):
                        if result.get('success'):
                            # 成功
                            api_logger.info(
                                f"[ModelFallback] ✅ 模型 {model_name} 调用成功"
                            )
                            return FallbackResult(
                                success=True,
                                result=result,
                                attempted_models=attempted_models,
                                successful_model=model_name
                            )
                        else:
                            # 返回失败
                            last_error = result.get('error', '未知错误')
                            api_logger.warning(
                                f"[ModelFallback] ⚠️ 模型 {model_name} 调用失败：{last_error}"
                            )
                    else:
                        # 其他类型，假设成功
                        api_logger.info(
                            f"[ModelFallback] ✅ 模型 {model_name} 调用完成"
                        )
                        return FallbackResult(
                            success=True,
                            result=result,
                            attempted_models=attempted_models,
                            successful_model=model_name
                        )
                    
                except Exception as e:
                    # 异常
                    last_error = str(e)
                    api_logger.error(
                        f"[ModelFallback] ❌ 模型 {model_name} 异常：{last_error}"
                    )
                    # 继续尝试下一个模型
            
            # 所有模型都失败
            api_logger.error(
                f"[ModelFallback] ❌ 所有模型调用失败："
                f"attempted={attempted_models}, last_error={last_error}"
            )
            
            return FallbackResult(
                success=False,
                error=last_error,
                attempted_models=attempted_models,
                successful_model=None
            )
        
        return wrapper
    return decorator


# 【P2 修复 - 2026-03-07】异步 Fallback 执行器
class ModelFallbackExecutor:
    """
    模型 Fallback 执行器
    
    用法:
        executor = ModelFallbackExecutor(primary_model='doubao')
        result = await executor.execute(call_ai_func, prompt, **kwargs)
    """
    
    def __init__(
        self,
        primary_model: str,
        fallback_models: Optional[List[str]] = None,
        max_fallbacks: int = 3
    ):
        self.primary_model = primary_model
        self.fallback_models = fallback_models or FALLBACK_MODEL_CONFIG.get(primary_model, [])
        self.max_fallbacks = max_fallbacks
    
    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> FallbackResult:
        """
        执行带 fallback 的调用
        
        参数:
            func: 要执行的函数（异步）
            *args: 位置参数
            **kwargs: 关键字参数
        
        返回:
            FallbackResult
        """
        # 构建模型尝试列表
        model_queue = [self.primary_model] + self.fallback_models[:self.max_fallbacks]
        
        attempted_models = []
        last_error = None
        
        for model_name in model_queue:
            attempted_models.append(model_name)
            
            try:
                api_logger.info(
                    f"[ModelFallback] 尝试模型：{model_name} "
                    f"(attempt={len(attempted_models)}/{len(model_queue)})"
                )
                
                # 调用函数
                result = await func(model_name=model_name, *args, **kwargs)
                
                # 检查返回结果
                if self._is_success(result):
                    api_logger.info(f"[ModelFallback] ✅ 模型 {model_name} 调用成功")
                    return FallbackResult(
                        success=True,
                        result=result,
                        attempted_models=attempted_models,
                        successful_model=model_name
                    )
                else:
                    last_error = self._get_error(result)
                    api_logger.warning(
                        f"[ModelFallback] ⚠️ 模型 {model_name} 调用失败：{last_error}"
                    )
                    
            except Exception as e:
                last_error = str(e)
                api_logger.error(
                    f"[ModelFallback] ❌ 模型 {model_name} 异常：{last_error}"
                )
        
        # 所有模型都失败
        api_logger.error(
            f"[ModelFallback] ❌ 所有模型调用失败："
            f"attempted={attempted_models}, last_error={last_error}"
        )
        
        return FallbackResult(
            success=False,
            error=last_error,
            attempted_models=attempted_models,
            successful_model=None
        )
    
    def _is_success(self, result: Any) -> bool:
        """检查结果是否成功"""
        if isinstance(result, AIResponse):
            return result.success
        elif isinstance(result, dict):
            return result.get('success', False)
        else:
            # 其他类型，假设成功
            return True
    
    def _get_error(self, result: Any) -> str:
        """获取错误信息"""
        if isinstance(result, AIResponse):
            return result.error_message or '未知错误'
        elif isinstance(result, dict):
            return result.get('error', '未知错误')
        else:
            return '未知错误'


# 【P2 修复 - 2026-03-07】便捷的 fallback 调用函数
async def call_with_fallback(
    func: Callable,
    primary_model: str,
    *args,
    fallback_models: Optional[List[str]] = None,
    max_fallbacks: int = 3,
    **kwargs
) -> FallbackResult:
    """
    便捷的 fallback 调用函数
    
    用法:
        result = await call_with_fallback(
            call_ai_func,
            'doubao',
            prompt='...',
            fallback_models=['qwen', 'deepseek']
        )
    """
    executor = ModelFallbackExecutor(
        primary_model=primary_model,
        fallback_models=fallback_models,
        max_fallbacks=max_fallbacks
    )
    return await executor.execute(func, *args, **kwargs)
