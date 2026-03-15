"""
单模型执行器与评估专用 LLM 调用器

重构说明：
- 移除多模型冗余调用功能
- 用户选择哪个模型就使用哪个模型进行诊断
- 评估反馈使用独立的优先级调用器（DeepSeek → 豆包 → 通义千问）

@author: 系统架构组
@date: 2026-03-01
@version: 2.0.0
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import AIResponse, AIErrorType
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from legacy_config import Config


class SingleModelExecutor:
    """
    单模型执行器（增强版 - 2026-03-13 第 16 次修复）

    核心原则：
    1. 用户选择哪个模型就使用哪个模型
    2. 【P0 关键修复】API Key 错误时自动故障转移到其他已配置的平台
    3. 故障转移优先级：DeepSeek → 豆包 → 通义千问
    """

    # 故障转移优先级列表
    FAILOVER_PRIORITY = [
        'deepseek',  # 首选：DeepSeek（性价比高）
        'doubao',    # 次选：豆包（稳定性好）
        'qwen',      # 第三：通义千问（备用）
    ]

    def __init__(self, timeout_seconds: int = 30):
        """
        初始化单模型执行器

        参数：
            timeout_seconds: 单个模型的超时时间
        """
        self.timeout_seconds = timeout_seconds

    async def execute(
        self,
        prompt: str,
        model_name: str,
        execution_id: str = None,
        q_idx: int = None
    ) -> Tuple[AIResponse, str]:
        """
        执行单模型调用（增强版 - 支持故障转移）

        策略：
        1. 优先调用用户指定的模型
        2. 【P0 关键修复】API Key 错误时自动故障转移到其他平台
        3. 故障转移优先级：DeepSeek → 豆包 → 通义千问

        参数：
            prompt: 提示词
            model_name: 模型名称（用户选择的模型）
            execution_id: 执行 ID（用于日志）
            q_idx: 问题索引（用于日志）

        返回：
            (AIResponse, model_name): AI 响应和实际使用的模型名称
        """
        log_context = f"exec={execution_id}, Q={q_idx}" if execution_id else ""

        api_logger.info(
            f"[SingleModel] 调用模型 {model_name}: {log_context}"
        )

        # 【P0 关键修复】构建故障转移列表
        failover_models = self._build_failover_list(model_name)

        # 按优先级尝试每个模型
        for attempt_idx, attempt_model in enumerate(failover_models):
            attempt_msg = f"尝试 #{attempt_idx + 1}"
            api_logger.info(
                f"[SingleModel] {attempt_msg} {attempt_model}: {log_context}"
            )

            try:
                # 提取平台名称，支持 doubao-xxx, deepseek-xxx 等格式
                platform_name = attempt_model.split('-')[0] if '-' in attempt_model else attempt_model
                if not Config.is_api_key_configured(platform_name):
                    api_logger.warning(
                        f"[SingleModel] {attempt_msg} {attempt_model} (平台：{platform_name}) 未配置 API Key，跳过"
                    )
                    continue  # 尝试下一个模型

                # 创建 AI 客户端
                client = AIAdapterFactory.create(attempt_model)

                # 调用模型
                result = client.send_prompt(prompt)

                # 记录结果
                if result and result.success:
                    api_logger.info(
                        f"[SingleModel] ✅ {attempt_msg} {attempt_model} 调用成功：{log_context}"
                    )
                    return result, attempt_model
                else:
                    # 模型返回失败响应
                    error_msg = result.error_message if result else 'No response'
                    error_type = result.error_type if result else AIErrorType.UNKNOWN_ERROR

                    # 【P0 关键】如果是 API Key 错误，立即尝试下一个模型
                    if error_type == AIErrorType.INVALID_API_KEY:
                        api_logger.warning(
                            f"[SingleModel] ⚠️ {attempt_msg} {attempt_model} API Key 无效，尝试下一个模型"
                        )
                        continue  # 尝试下一个模型
                    else:
                        # 其他错误直接返回
                        api_logger.warning(
                            f"[SingleModel] ❌ {attempt_msg} {attempt_model} 调用失败：{error_type.value} - {error_msg}"
                        )
                        return result, attempt_model

            except Exception as e:
                error_str = str(e).lower()
                is_api_key_error = any(kw in error_str for kw in ['api key', 'authentication', '401', 'invalid'])

                # 【P0 关键】如果是 API Key 错误，尝试下一个模型
                if is_api_key_error:
                    api_logger.warning(
                        f"[SingleModel] ⚠️ {attempt_msg} {attempt_model} API Key 错误：{e}，尝试下一个模型"
                    )
                    continue  # 尝试下一个模型
                else:
                    # 其他异常直接返回
                    api_logger.error(
                        f"[SingleModel] ❌ {attempt_msg} {attempt_model} 异常：{e}: {log_context}"
                    )
                    return AIResponse(
                        success=False,
                        error_message=str(e),
                        model=attempt_model,
                        error_type=self._identify_error_type(e)
                    ), attempt_model

        # 【P0 关键修复】所有模型都失败，返回详细错误
        api_logger.error(
            f"[SingleModel] ❌ 所有 {len(failover_models)} 个模型调用失败：{log_context}"
        )

        return AIResponse(
            success=False,
            error_message=f"所有 AI 平台调用失败（已尝试：{', '.join(failover_models)}）",
            model=model_name,
            error_type=AIErrorType.SERVICE_UNAVAILABLE
        ), model_name

    def _build_failover_list(self, primary_model: str) -> List[str]:
        """
        【P0 新增 - 2026-03-13】构建故障转移列表

        参数：
            primary_model: 用户选择的主模型

        返回：
            List[str]: 故障转移模型列表
        """
        # 提取主模型的平台名称
        primary_platform = primary_model.split('-')[0] if '-' in primary_model else primary_model

        # 构建故障转移列表：主模型 + 其他已配置的平台
        failover_list = [primary_model]  # 首先尝试用户选择的模型

        # 按优先级添加其他平台
        for platform in self.FAILOVER_PRIORITY:
            if platform != primary_platform:
                # 检查该平台是否已配置
                if Config.is_api_key_configured(platform):
                    failover_list.append(platform)

        api_logger.info(
            f"[SingleModel] 故障转移列表：{failover_list}"
        )

        return failover_list

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
            return AIErrorType.UNKNOWN_ERROR


class PriorityLLMEvaluator:
    """
    评估专用 LLM 调用器（带优先级顺序）
    
    使用场景：
    - AI Judge 评估回答质量
    - 需要高可靠性的评估任务
    
    优先级顺序：
    1. DeepSeek（首选）
    2. 豆包（次选）
    3. 通义千问（第三选择）
    """

    # 评估专用模型优先级
    EVAL_MODEL_PRIORITY = [
        'deepseek',  # 首选：DeepSeek
        'doubao',    # 次选：豆包
        'qwen',      # 第三：通义千问
    ]

    def __init__(self, timeout_seconds: int = 30):
        """
        初始化评估专用 LLM 调用器

        参数：
            timeout_seconds: 单个模型的超时时间
        """
        self.timeout_seconds = timeout_seconds

    def execute_with_priority(
        self,
        prompt: str,
        custom_priority_list: List[str] = None,
        execution_id: str = None
    ) -> Tuple[AIResponse, str]:
        """
        按优先级顺序调用 LLM（同步版本）
        
        策略：
        1. 按优先级顺序尝试模型
        2. 返回第一个成功的结果
        3. 所有模型失败时返回详细错误

        参数：
            prompt: 提示词
            custom_priority_list: 自定义优先级列表（为 None 时使用默认）
            execution_id: 执行 ID（用于日志）

        返回：
            (AIResponse, model_name): AI 响应和实际使用的模型名称
        """
        # 确定优先级列表
        priority_list = custom_priority_list or self.EVAL_MODEL_PRIORITY

        log_context = f"exec={execution_id}" if execution_id else ""

        api_logger.info(
            f"[PriorityEval] 启动优先级调用：{log_context}, 优先级={priority_list}"
        )

        # 记录每个模型的失败原因
        failure_log = []

        # 按优先级顺序尝试每个模型
        for i, model_name in enumerate(priority_list):
            attempt_msg = f"优先级#{i+1}"
            api_logger.info(
                f"[PriorityEval] 尝试 {attempt_msg} {model_name}: {log_context}"
            )

            try:
                result = self._call_single_model(model_name, prompt, log_context)

                # 检查是否成功
                if result.success and self._validate_ai_response(result):
                    api_logger.info(
                        f"[PriorityEval] ✅ {attempt_msg} {model_name} 调用成功"
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
                        f"[PriorityEval] ⚠️ {attempt_msg} {model_name} 调用失败：{error_type} - {error_msg}"
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
                    f"[PriorityEval] ⚠️ {attempt_msg} {model_name} 调用异常：{error_msg}"
                )

        # 所有模型都失败，返回详细错误报告
        api_logger.error(
            f"[PriorityEval] ❌ 所有 {len(priority_list)} 个模型调用失败：{log_context}"
        )

        # 构建详细错误信息
        error_details = []
        for failure in failure_log:
            error_details.append(
                f"{failure['attempt']}({failure['model']}): {failure['type']} - {failure['error'][:100]}"
            )

        detailed_error = "所有评估模型调用失败:\n" + "\n".join(error_details)
        api_logger.error(f"[PriorityEval] 详细错误:\n{detailed_error}")

        # 返回第一个错误
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
                error_message="所有评估模型调用失败",
                model=priority_list[0] if priority_list else 'unknown'
            ), priority_list[0] if priority_list else 'unknown'

    def _call_single_model(
        self,
        model_name: str,
        prompt: str,
        log_context: str
    ) -> AIResponse:
        """
        调用单个模型

        参数：
            model_name: 模型名称
            prompt: 提示词
            log_context: 日志上下文

        返回：
            AIResponse: AI 响应
        """
        try:
            # 检查 API Key 是否配置
            if not Config.is_api_key_configured(model_name):
                api_logger.warning(
                    f"[PriorityEval] 模型 {model_name} 未配置 API Key，跳过：{log_context}"
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
                f"[PriorityEval] 调用模型 {model_name}: {log_context}"
            )

            result = client.send_prompt(prompt)

            # 记录结果
            if result and result.success:
                api_logger.debug(
                    f"[PriorityEval] 模型 {model_name} 成功：{log_context}"
                )
            else:
                api_logger.debug(
                    f"[PriorityEval] 模型 {model_name} 失败：{result.error_message if result else 'No response'}"
                )

            return result

        except Exception as e:
            api_logger.error(
                f"[PriorityEval] 模型 {model_name} 异常：{e}: {log_context}"
            )
            return AIResponse(
                success=False,
                error_message=str(e),
                model=model_name,
                error_type=self._identify_error_type(e)
            )

    def _identify_error_type(self, exception: Exception) -> AIErrorType:
        """识别错误类型"""
        error_str = str(exception).lower()

        if any(kw in error_str for kw in ['quota', '配额', 'limit']):
            return AIErrorType.INSUFFICIENT_QUOTA
        elif any(kw in error_str for kw in ['api key', 'authentication', '401']):
            return AIErrorType.INVALID_API_KEY
        elif any(kw in error_str for kw in ['rate limit', 'frequency', '频繁']):
            return AIErrorType.RATE_LIMIT_EXCEEDED
        elif any(kw in error_str for kw in ['timeout', 'time out']):
            return AIErrorType.SERVICE_UNAVAILABLE
        else:
            return AIErrorType.UNKNOWN_ERROR

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


# 便捷函数
def get_single_model_executor(timeout: int = 30) -> SingleModelExecutor:
    """获取单模型执行器实例"""
    return SingleModelExecutor(timeout_seconds=timeout)


def get_priority_evaluator(timeout: int = 30) -> PriorityLLMEvaluator:
    """获取评估专用 LLM 调用器实例"""
    return PriorityLLMEvaluator(timeout_seconds=timeout)
