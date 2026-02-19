"""
DoubaoProvider - 豆包平台提供者
继承自BaseAIProvider，实现豆包平台的特定逻辑
"""
import time
import requests
import json
from typing import Dict, Any, List
from urllib.parse import urlparse
import re
from .base_provider import BaseAIProvider
from ..logging_config import api_logger
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error


class DoubaoProvider(BaseAIProvider):
    """
    豆包 AI 平台提供者，实现BaseAIProvider接口
    用于将 豆包 API 接入 GEO 内容质量验证系统
    支持两种模式：普通对话模式和深度推理模式
    包含内部 Prompt 约束逻辑，可配置是否启用中文回答及事实性约束
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = None,  # 默认使用配置管理器的值
        mode: str = "chat",  # 新增 mode 参数，支持 "chat" 或 "reasoner"
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ):
        """
        初始化 豆包 提供者

        Args:
            api_key: 豆包 API 密钥
            model_name: 使用的模型名称，默认从配置管理器获取
            mode: 调用模式，"chat" 表示普通对话模式，"reasoner" 表示深度推理模式
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
        """
        super().__init__(api_key, model_name)
        self.mode = mode  # 存储模式
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url

        # 初始化统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="doubao",
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3
        )

        api_logger.info(f"DoubaoProvider initialized for model: {model_name} with unified request wrapper")

    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """
        向 豆包 发送问题并返回原生响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            Dict: 包含 豆包 原生响应的字典
        """
        start_time = time.time()

        try:
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("豆包 API Key 未设置")

            # 根据模式构建不同的请求体
            # 普通对话模式 (chat): 适用于日常对话和一般性问题解答
            # 深度推理模式 (reasoner): 适用于需要深度分析和推理的问题
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            # 如果是推理模式，添加额外参数
            if self.mode == "reasoner":
                payload["reasoner"] = "search"  # 启用搜索推理能力

            # 使用统一请求封装器发送请求到 豆包 API
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30  # 设置请求超时时间为30秒
            )

            # 计算请求延迟
            latency = time.time() - start_time

            if response.status_code != 200:
                error_message = f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                api_logger.error(error_message)
                return {
                    'error': error_message,
                    'status_code': response.status_code,
                    'success': False,
                    'latency': latency
                }

            # 解析响应数据
            response_data = response.json()

            # 提取所需信息
            content = ""
            usage = {}

            # 从响应中提取实际回答文本
            choices = response_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")

            # 从响应中提取使用情况信息
            usage = response_data.get("usage", {})

            # 返回成功的响应，包含模式信息
            return {
                'content': content,
                'model': response_data.get("model", self.model_name),
                'platform': 'doubao',
                'tokens_used': usage.get("total_tokens", 0),
                'latency': latency,
                'raw_response': response_data,
                'mode_used': self.mode,  # 包含使用的模式信息
                'success': True
            }

        except requests.exceptions.Timeout:
            # 处理请求超时异常
            latency = time.time() - start_time
            error_msg = "请求超时"
            api_logger.error(error_msg)
            return {
                'error': error_msg,
                'success': False,
                'latency': latency
            }

        except requests.exceptions.RequestException as e:
            # 处理其他请求相关异常
            latency = time.time() - start_time
            error_msg = f"请求异常: {str(e)}"
            api_logger.error(error_msg)
            return {
                'error': error_msg,
                'success': False,
                'latency': latency
            }

        except ValueError as e:
            # 处理 API Key 验证等值错误
            latency = time.time() - start_time
            api_logger.error(f"Value error: {str(e)}")
            return {
                'error': str(e),
                'success': False,
                'latency': latency
            }

        except Exception as e:
            # 处理其他未预期的异常
            latency = time.time() - start_time
            error_msg = f"未知错误: {str(e)}"
            api_logger.error(error_msg)
            return {
                'error': error_msg,
                'success': False,
                'latency': latency
            }

    def health_check(self) -> bool:
        """
        检查 豆包 提供者的健康状态
        通过发送一个简单的测试请求来验证连接

        Returns:
            bool: 提供者是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.ask_question("你好，请回复'正常'。")
            return test_response.get('success', False)
        except Exception:
            return False