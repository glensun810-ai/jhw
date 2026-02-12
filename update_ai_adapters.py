#!/usr/bin/env python3
"""
批量更新AI适配器以应用安全改进措施
"""

import os
from pathlib import Path


def update_chatgpt_adapter():
    """更新ChatGPT适配器以应用安全功能"""
    
    chatgpt_content = '''import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager

class ChatGPTAdapter(AIClient):
    """
    ChatGPT (OpenAI) AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.CHATGPT, model_name, api_key)
        
        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="chatgpt",
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"ChatGPTAdapter initialized for model: {model_name} with unified request wrapper")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 ChatGPT API 发送请求
        """
        messages = [{"role": "user", "content": prompt}]

        platform_config_manager = PlatformConfigManager()
        chatgpt_config = platform_config_manager.get_platform_config('chatgpt')

        temperature = kwargs.get('temperature', chatgpt_config.default_temperature if chatgpt_config else 0.7)
        max_tokens = kwargs.get('max_tokens', chatgpt_config.default_max_tokens if chatgpt_config else 1000)
        timeout = kwargs.get('timeout', chatgpt_config.timeout if chatgpt_config else 30)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        start_time = time.time()

        try:
            # 使用统一请求封装器发送请求
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=timeout
            )

            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            if response_data and response_data.get("choices"):
                content = response_data["choices"][0]["message"]["content"]
                tokens_used = response_data["usage"]["total_tokens"] if response_data.get("usage") else 0
                api_logger.info(f"ChatGPT response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=tokens_used,
                    latency=latency,
                    metadata=response_data
                )
            else:
                error_message = response_data.get("error", {}).get("message", "Unknown ChatGPT API error")
                error_type = self._map_error_message(error_message)
                api_logger.error(f"ChatGPT API returned no choices: {error_message}")
                return AIResponse(
                    success=False, 
                    error_message=error_message, 
                    error_type=error_type, 
                    model=self.model_name, 
                    platform=self.platform_type.value, 
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            error_message = f"ChatGPT API request failed: {e}"
            error_type = AIErrorType.UNKNOWN_ERROR
            latency = time.time() - start_time
            
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 401:
                    error_type = AIErrorType.INVALID_API_KEY
                elif status_code == 429:
                    error_type = AIErrorType.RATE_LIMIT_EXCEEDED
                elif status_code >= 500:
                    error_type = AIErrorType.SERVER_ERROR
                elif status_code == 403:
                    error_type = AIErrorType.INVALID_API_KEY

            api_logger.error(error_message)
            record_error("chatgpt", error_type.value, str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=error_type, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )
        except Exception as e:
            error_message = f"An unexpected error occurred with ChatGPT API: {e}"
            latency = time.time() - start_time
            api_logger.error(error_message)
            record_error("chatgpt", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=AIErrorType.UNKNOWN_ERROR, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )

    def _map_error_message(self, error_message: str) -> AIErrorType:
        """将ChatGPT的错误信息映射到标准错误类型"""
        error_message_lower = error_message.lower()
        if "incorrect api key" in error_message_lower:
            return AIErrorType.INVALID_API_KEY
        if "quota" in error_message_lower:
            return AIErrorType.INSUFFICIENT_QUOTA
        if "content policy" in error_message_lower:
            return AIErrorType.CONTENT_SAFETY
        return AIErrorType.UNKNOWN_ERROR
'''
    
    # 更新ChatGPT适配器
    adapter_path = Path('wechat_backend/ai_adapters/chatgpt_adapter.py')
    with open(adapter_path, 'w', encoding='utf-8') as f:
        f.write(chatgpt_content)
    
    print("✓ 已更新ChatGPT适配器以应用安全功能")


def update_qwen_adapter():
    """更新Qwen适配器以应用安全功能"""
    
    qwen_content = '''import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager

class QwenAdapter(AIClient):
    """
    Qwen (Alibaba Tongyi) AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "qwen-max", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.QWEN, model_name, api_key)
        
        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="qwen",
            base_url=base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"QwenAdapter initialized for model: {model_name} with unified request wrapper")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Qwen API 发送请求
        """
        messages = [{"role": "user", "content": prompt}]

        platform_config_manager = PlatformConfigManager()
        qwen_config = platform_config_manager.get_platform_config('qwen')

        temperature = kwargs.get('temperature', qwen_config.default_temperature if qwen_config else 0.7)

        payload = {
            "model": self.model_name,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": temperature,
            }
        }

        start_time = time.time()
        try:
            # 使用统一请求封装器发送请求
            response = self.request_wrapper.make_ai_request(
                endpoint="",  # Qwen API endpoint is specified in base_url
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            if response_data and response_data.get("output"):
                content = response_data["output"]["text"]
                tokens_used = response_data["usage"]["total_tokens"] if response_data.get("usage") else 0
                api_logger.info(f"Qwen response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=tokens_used,
                    latency=latency,
                    metadata=response_data
                )
            else:
                error_code = response_data.get("code", "")
                error_message = response_data.get("message", "Unknown Qwen API error")
                error_type = self._map_error_code(error_code)

                api_logger.error(f"Qwen API returned no output: {error_code} - {error_message}")
                return AIResponse(
                    success=False, 
                    error_message=error_message, 
                    error_type=error_type, 
                    model=self.model_name, 
                    platform=self.platform_type.value, 
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            error_message = f"Qwen API request failed: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            record_error("qwen", "REQUEST_EXCEPTION", str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=AIErrorType.UNKNOWN_ERROR, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )
        except Exception as e:
            error_message = f"An unexpected error occurred with Qwen API: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            record_error("qwen", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=AIErrorType.UNKNOWN_ERROR, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )

    def _map_error_code(self, error_code: str) -> AIErrorType:
        """将Qwen的错误码映射到标准错误类型"""
        if error_code == "InvalidAPIKey":
            return AIErrorType.INVALID_API_KEY
        if error_code == "QuotaExhausted":
            return AIErrorType.INSUFFICIENT_QUOTA
        if error_code == "OperationDenied.ContentRisk":
            return AIErrorType.CONTENT_SAFETY
        if "Throttling" in error_code:
            return AIErrorType.RATE_LIMIT_EXCEEDED
        return AIErrorType.UNKNOWN_ERROR
'''
    
    # 更新Qwen适配器
    adapter_path = Path('wechat_backend/ai_adapters/qwen_adapter.py')
    with open(adapter_path, 'w', encoding='utf-8') as f:
        f.write(qwen_content)
    
    print("✓ 已更新Qwen适配器以应用安全功能")


def update_gemini_adapter():
    """更新Gemini适配器以应用安全功能"""
    
    gemini_content = '''import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager

class GeminiAdapter(AIClient):
    """
    Google Gemini AI 平台的适配器 - 使用 REST API 避免 Python 版本兼容性问题
    """
    def __init__(self, api_key: str, model_name: str = "gemini-pro", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.GEMINI, model_name, api_key)

        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="gemini",
            base_url=base_url or f"https://generativelanguage.googleapis.com/v1beta/models",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )

        api_logger.info(f"GeminiAdapter initialized for model: {model_name} using REST API with unified request wrapper")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Gemini API 发送请求 - 使用 REST API
        """
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": kwargs.get('temperature', 0.7),
                "maxOutputTokens": kwargs.get('max_tokens', 2048)
            }
        }

        start_time = time.time()
        try:
            # 使用统一请求封装器发送请求
            url_suffix = f"/{self.model_name}:generateContent?key={self.api_key}"
            response = self.request_wrapper.make_ai_request(
                endpoint=url_suffix,
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            # 解析响应
            candidates = response_data.get("candidates", [])
            if candidates:
                content = candidates[0]["content"]["parts"][0]["text"]

                # 估算 token 数量
                tokens_used = len(prompt.split()) + len(content.split())

                api_logger.info(f"Gemini response success. Tokens: ~{tokens_used}, Latency: {latency:.2f}s")
                return AIResponse(
                    success=True,
                    content=content,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    tokens_used=tokens_used,
                    latency=latency,
                    metadata=response_data
                )
            else:
                error_details = response_data.get("error", {})
                error_message = error_details.get("message", "Unknown Gemini API error")
                error_type = self._map_error_code(error_details.get("code", 0))

                api_logger.error(f"Gemini API returned no candidates: {error_message}")
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=error_type,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            latency = time.time() - start_time
            error_message = f"Gemini API request failed: {e}"
            error_type = AIErrorType.UNKNOWN_ERROR

            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 400:
                    error_type = AIErrorType.CONTENT_SAFETY  # Often safety issues return 400
                elif status_code == 401 or status_code == 403:
                    error_type = AIErrorType.INVALID_API_KEY
                elif status_code == 429:
                    error_type = AIErrorType.INSUFFICIENT_QUOTA  # Quota issues often return 429
                elif status_code >= 500:
                    error_type = AIErrorType.SERVER_ERROR

            api_logger.error(error_message)
            record_error("gemini", error_type.value, str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )
        except Exception as e:
            latency = time.time() - start_time
            error_message = f"An unexpected error occurred with Gemini API: {e}"
            api_logger.error(error_message)
            record_error("gemini", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_error_code(self, error_code: int) -> AIErrorType:
        """将Gemini的错误码映射到标准错误类型"""
        if error_code == 3:  # Invalid argument (often means invalid API key)
            return AIErrorType.INVALID_API_KEY
        if error_code == 7:  # Permission denied
            return AIErrorType.INVALID_API_KEY
        if error_code == 8:  # Resource exhausted (quota)
            return AIErrorType.INSUFFICIENT_QUOTA
        if error_code == 10:  # Failed precondition (could be safety)
            return AIErrorType.CONTENT_SAFETY
        if error_code == 13:  # Internal server error
            return AIErrorType.SERVER_ERROR
        if error_code == 14:  # Service unavailable
            return AIErrorType.SERVER_ERROR
        return AIErrorType.UNKNOWN_ERROR
'''
    
    # 更新Gemini适配器
    adapter_path = Path('wechat_backend/ai_adapters/gemini_adapter.py')
    with open(adapter_path, 'w', encoding='utf-8') as f:
        f.write(gemini_content)
    
    print("✓ 已更新Gemini适配器以应用安全功能")


def main():
    print("🔄 开始批量更新AI适配器以应用安全改进措施")
    print("=" * 60)
    
    print("\n1. 更新ChatGPT适配器...")
    update_chatgpt_adapter()
    
    print("\n2. 更新Qwen适配器...")
    update_qwen_adapter()
    
    print("\n3. 更新Gemini适配器...")
    update_gemini_adapter()
    
    print("\n" + "=" * 60)
    print("✅ 批量更新完成！")
    print("\n已更新的适配器：")
    print("• ChatGPT适配器 - 现在使用统一请求封装器")
    print("• Qwen适配器 - 现在使用统一请求封装器") 
    print("• Gemini适配器 - 现在使用统一请求封装器")
    print("\n所有更新的适配器现在都具备：")
    print("• 统一请求封装")
    print("• 断路器保护")
    print("• 重试机制")
    print("• 速率限制")
    print("• 指标收集")
    print("• 结构化日志记录")


if __name__ == "__main__":
    main()