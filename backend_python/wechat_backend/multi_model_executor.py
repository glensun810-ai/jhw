"""
多模型冗余调用执行器

P1-2 修复：多模型冗余调用机制

功能：
1. 并发调用多个 AI 模型
2. 返回第一个有效结果
3. 自动故障转移
4. 支持优先级配置

核心原则：
1. 提高诊断成功率
2. 降低单模型失败影响
3. 保持响应速度
4. 节省成本（返回第一个有效结果）

使用场景：
- 单模型调用失败时自动切换到备用模型
- 重要诊断任务需要高成功率
- 用户指定多个模型时的冗余执行

@author: 系统架构组
@date: 2026-02-28
@version: 1.0.0
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import AIResponse, AIErrorType
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor, FaultTolerantResult, ErrorType


class MultiModelExecutor:
    """
    多模型冗余调用执行器
    
    执行策略：
    1. 并发调用所有可用模型
    2. 返回第一个成功的有效结果
    3. 如果所有模型都失败，返回最佳错误信息
    """
    
    # 默认备用模型配置（P0-DIAG 修复：确保备用模型列表完整且按优先级排序）
    DEFAULT_FALLBACK_MODELS = {
        'doubao': ['qwen', 'deepseek'],  # 豆包的备用：通义、深度求索
        'qwen': ['doubao', 'deepseek'],  # 通义的备用：豆包、深度求索
        'deepseek': ['qwen', 'doubao'],  # 深度求索的备用：通义、豆包
        'wenxin': ['qwen', 'doubao', 'deepseek'],  # 文心的备用
    }
    
    # 模型优先级（数字越小优先级越高）
    MODEL_PRIORITY = {
        'doubao': 1,
        'qwen': 2,
        'deepseek': 3,
        'wenxin': 4,
        'zhipu': 5,
        'kimi': 6,
    }
    
    def __init__(self, timeout_seconds: int = 10, max_concurrent: int = 3):
        """
        初始化多模型执行器
        
        参数：
            timeout_seconds: 单个模型的超时时间
            max_concurrent: 最大并发模型数
        """
        self.timeout_seconds = timeout_seconds
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def execute_with_redundancy(
        self,
        prompt: str,
        primary_model: str,
        fallback_models: List[str] = None,
        execution_id: str = None,
        q_idx: int = None
    ) -> Tuple[AIResponse, str]:
        """
        带冗余的模型调用（P0-DIAG 修复：顺序尝试版本）

        策略：
        1. 首先尝试主模型
        2. 主模型失败时，按顺序尝试备用模型
        3. 返回第一个成功的有效结果
        4. 所有模型失败时，返回详细错误报告

        参数：
            prompt: 提示词
            primary_model: 主模型名称
            fallback_models: 备用模型列表（为 None 时使用默认配置）
            execution_id: 执行 ID（用于日志）
            q_idx: 问题索引（用于日志）

        返回：
            (AIResponse, model_name): AI 响应和实际使用的模型名称
        """
        log_context = f"exec={execution_id}, Q={q_idx}" if execution_id else ""

        # 确定备用模型列表
        if fallback_models is None:
            fallback_models = self.DEFAULT_FALLBACK_MODELS.get(
                primary_model,
                [m for m in self.MODEL_PRIORITY.keys() if m != primary_model]
            )

        # 所有待尝试的模型（主模型 + 备用模型）
        all_models = [primary_model] + fallback_models

        # P0-DIAG-1 修复：记录尝试计划
        api_logger.info(
            f"[MultiModel] 启动冗余调用：{log_context}, "
            f"主模型={primary_model}, 备用模型={fallback_models}"
        )

        # 记录每个模型的失败原因
        failure_log = []

        # P0-DIAG-1 修复：按顺序尝试每个模型
        for i, model_name in enumerate(all_models):
            is_primary = (i == 0)
            attempt_msg = "主模型" if is_primary else f"备用模型#{i}"
            api_logger.info(
                f"[MultiModel] 尝试 {attempt_msg} {model_name}: {log_context} "
                f"({i+1}/{len(all_models)})"
            )

            try:
                result = await self._call_single_model(model_name, prompt, log_context)

                # 检查是否成功
                if result.success and self._validate_ai_response(result):
                    api_logger.info(
                        f"[MultiModel] ✅ {attempt_msg} {model_name} 调用成功"
                    )
                    return result, model_name
                else:
                    # 模型返回失败响应
                    error_msg = result.error_message or "未知错误"
                    error_type = result.error_type.value if result.error_type else "unknown"
                    failure_log.append({
                        'model': model_name,
                        'error': error_msg,
                        'type': error_type,
                        'attempt': attempt_msg
                    })
                    api_logger.warning(
                        f"[MultiModel] ⚠️ {attempt_msg} {model_name} 调用失败：{error_type} - {error_msg}"
                    )

            except Exception as e:
                # 模型调用异常
                error_msg = str(e)
                failure_log.append({
                    'model': model_name,
                    'error': error_msg,
                    'type': 'exception',
                    'attempt': attempt_msg
                })
                api_logger.warning(
                    f"[MultiModel] ⚠️ {attempt_msg} {model_name} 调用异常：{error_msg}"
                )

        # P0-DIAG-1 修复：所有模型都失败，返回详细错误报告
        api_logger.error(
            f"[MultiModel] ❌ 所有 {len(all_models)} 个模型调用失败：{log_context}"
        )

        # 构建详细错误信息
        error_details = []
        for failure in failure_log:
            error_details.append(
                f"{failure['attempt']}({failure['model']}): {failure['type']} - {failure['error'][:100]}"
            )

        detailed_error = "所有模型调用失败:\n" + "\n".join(error_details)
        api_logger.error(f"[MultiModel] 详细错误:\n{detailed_error}")

        # 返回第一个错误（保持向后兼容）
        first_failure = failure_log[0] if failure_log else None
        if first_failure:
            return AIResponse(
                success=False,
                error_message=detailed_error,
                error_type=AIErrorType.SERVICE_UNAVAILABLE,
                model=first_failure['model']
            ), first_failure['model']
        else:
            return AIResponse(
                success=False,
                error_message="所有模型调用失败",
                model=primary_model
            ), primary_model
    
    async def _call_single_model(
        self,
        model_name: str,
        prompt: str,
        log_context: str
    ) -> AIResponse:
        """
        调用单个模型（带限流保护和 API Key 检测）

        参数：
            model_name: 模型名称
            prompt: 提示词
            log_context: 日志上下文

        返回：
            AIResponse: AI 响应
        """
        async with self._semaphore:
            try:
                # P0-DIAG-2 修复：检查 API Key 是否配置
                from config import Config
                if not Config.is_api_key_configured(model_name):
                    api_logger.warning(
                        f"[MultiModel] 模型 {model_name} 未配置 API Key，跳过：{log_context}"
                    )
                    return AIResponse(
                        success=False,
                        error_message=f"模型 {model_name} 未配置 API Key",
                        error_type=AIErrorType.INVALID_API_KEY,
                        model=model_name
                    )

                # 创建 AI 客户端
                client = AIAdapterFactory.create(model_name)

                # 调用模型
                api_logger.debug(
                    f"[MultiModel] 调用模型 {model_name}: {log_context}"
                )

                result = client.send_prompt(prompt)

                # 记录结果
                if result and result.success:
                    api_logger.debug(
                        f"[MultiModel] 模型 {model_name} 成功：{log_context}"
                    )
                else:
                    api_logger.debug(
                        f"[MultiModel] 模型 {model_name} 失败：{result.error_message if result else 'No response'}"
                    )

                return result

            except Exception as e:
                api_logger.error(
                    f"[MultiModel] 模型 {model_name} 异常：{e}, {log_context}"
                )
                return AIResponse(
                    success=False,
                    error_message=str(e),
                    model=model_name,
                    error_type=self._identify_error_type(e)
                )
    
    def _validate_ai_response(self, response: AIResponse) -> bool:
        """
        验证 AI 响应是否有效
        
        参数：
            response: AI 响应
            
        返回：
            bool: 是否有效
        """
        if not response or not response.success:
            return False
        
        # 检查响应内容
        if not response.content:
            return False
        
        # 检查内容长度（太短可能是无效响应）
        if len(response.content.strip()) < 10:
            return False
        
        return True
    
    def _identify_error_type(self, exception: Exception) -> AIErrorType:
        """
        识别错误类型
        
        参数：
            exception: 异常对象
            
        返回：
            AIErrorType: 错误类型
        """
        error_str = str(exception).lower()
        
        # 错误类型映射
        if any(kw in error_str for kw in ['quota', '配额', 'limit']):
            return AIErrorType.INSUFFICIENT_QUOTA
        elif any(kw in error_str for kw in ['api key', 'authentication', '401']):
            return AIErrorType.INVALID_API_KEY
        elif any(kw in error_str for kw in ['rate limit', 'frequency', '频繁']):
            return AIErrorType.RATE_LIMIT_EXCEEDED
        elif any(kw in error_str for kw in ['timeout', 'time out']):
            return AIErrorType.SERVICE_UNAVAILABLE
        else:
            return AIErrorType.UNKNOWN
    
    def get_optimal_model_order(
        self,
        preferred_model: str,
        available_models: List[str] = None
    ) -> List[str]:
        """
        获取最优模型调用顺序
        
        参数：
            preferred_model: 首选模型
            available_models: 可用模型列表
            
        返回：
            List[str]: 模型调用顺序
        """
        if available_models is None:
            available_models = list(self.MODEL_PRIORITY.keys())
        
        # 按优先级排序
        sorted_models = sorted(
            available_models,
            key=lambda m: self.MODEL_PRIORITY.get(m, 999)
        )
        
        # 将首选模型移到最前面
        if preferred_model in sorted_models:
            sorted_models.remove(preferred_model)
            sorted_models.insert(0, preferred_model)
        
        return sorted_models


class ConcurrentMultiModelExecutor:
    """
    并发多模型执行器（同时调用多个模型，收集所有结果）
    
    使用场景：
    - 需要对比多个模型的回答
    - 提高结果质量（选择最佳答案）
    - 数据分析需要多个视角
    """
    
    def __init__(self, timeout_seconds: int = 15, max_concurrent: int = 5):
        """
        初始化并发多模型执行器
        
        参数：
            timeout_seconds: 单个模型的超时时间
            max_concurrent: 最大并发模型数
        """
        self.timeout_seconds = timeout_seconds
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_all_models(
        self,
        prompt: str,
        models: List[str],
        execution_id: str = None,
        q_idx: int = None
    ) -> List[Tuple[str, AIResponse]]:
        """
        并发调用所有指定模型
        
        参数：
            prompt: 提示词
            models: 模型列表
            execution_id: 执行 ID
            q_idx: 问题索引
            
        返回：
            List[Tuple[str, AIResponse]]: [(模型名，响应), ...]
        """
        log_context = f"exec={execution_id}, Q={q_idx}" if execution_id else ""
        
        api_logger.info(
            f"[ConcurrentMultiModel] 并发调用 {len(models)} 个模型：{log_context}"
        )
        
        # 创建任务
        tasks = [
            self._call_single_model(model, prompt, log_context)
            for model in models
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        model_results = []
        for i, result in enumerate(results):
            model_name = models[i]
            
            if isinstance(result, Exception):
                model_results.append((
                    model_name,
                    AIResponse(
                        success=False,
                        error_message=str(result),
                        model=model_name
                    )
                ))
            elif isinstance(result, AIResponse):
                model_results.append((model_name, result))
            else:
                model_results.append((
                    model_name,
                    AIResponse(
                        success=False,
                        error_message="Unknown error",
                        model=model_name
                    )
                ))
        
        # 统计成功情况
        success_count = sum(1 for _, r in model_results if r.success)
        api_logger.info(
            f"[ConcurrentMultiModel] 完成：{success_count}/{len(models)} 成功"
        )
        
        return model_results
    
    async def _call_single_model(
        self,
        model_name: str,
        prompt: str,
        log_context: str
    ) -> AIResponse:
        """调用单个模型（与 MultiModelExecutor 相同）"""
        async with self._semaphore:
            try:
                client = AIAdapterFactory.create(model_name)
                result = client.send_prompt(prompt)
                
                if result and result.success:
                    api_logger.debug(
                        f"[ConcurrentMultiModel] 模型 {model_name} 成功：{log_context}"
                    )
                else:
                    api_logger.debug(
                        f"[ConcurrentMultiModel] 模型 {model_name} 失败：{result.error_message if result else 'No response'}"
                    )
                
                return result
                
            except Exception as e:
                api_logger.error(
                    f"[ConcurrentMultiModel] 模型 {model_name} 异常：{e}, {log_context}"
                )
                return AIResponse(
                    success=False,
                    error_message=str(e),
                    model=model_name
                )


# 便捷函数
def get_multi_model_executor(timeout: int = 10) -> MultiModelExecutor:
    """获取多模型执行器实例"""
    return MultiModelExecutor(timeout_seconds=timeout)


def get_concurrent_executor(timeout: int = 15) -> ConcurrentMultiModelExecutor:
    """获取并发多模型执行器实例"""
    return ConcurrentMultiModelExecutor(timeout_seconds=timeout)
