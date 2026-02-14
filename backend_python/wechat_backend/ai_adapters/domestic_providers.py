"""
国内AI提供商适配器集合
整合了多家国内AI服务提供商的适配器
"""

import time
import requests
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.request_wrapper import get_ai_request_wrapper
from ..monitoring.metrics_collector import record_api_call, record_error
from ..monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager


class TongyiAdapter(AIClient):
    """
    通义千问 AI 平台适配器
    """
    def __init__(self, api_key: str, model_name: str = "qwen-max", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.QWEN, model_name, api_key)
        
        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="tongyi",
            base_url=base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"TongyiAdapter initialized for model: {model_name} with unified request wrapper")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 通义千问 API 发送请求
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
                endpoint="",  # 通义千问API endpoint在base_url中指定
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
                api_logger.info(f"Tongyi response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
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
                error_message = response_data.get("message", "Unknown Tongyi API error")
                error_type = self._map_error_code(error_code)

                api_logger.error(f"Tongyi API returned no output: {error_code} - {error_message}")
                return AIResponse(
                    success=False, 
                    error_message=error_message, 
                    error_type=error_type, 
                    model=self.model_name, 
                    platform=self.platform_type.value, 
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            error_message = f"Tongyi API request failed: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            record_error("tongyi", "REQUEST_EXCEPTION", str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=AIErrorType.UNKNOWN_ERROR, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )
        except Exception as e:
            error_message = f"An unexpected error occurred with Tongyi API: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            record_error("tongyi", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False, 
                error_message=error_message, 
                error_type=AIErrorType.UNKNOWN_ERROR, 
                model=self.model_name, 
                platform=self.platform_type.value, 
                latency=latency
            )

    def _map_error_code(self, error_code: str) -> AIErrorType:
        """将通义千问的错误码映射到标准错误类型"""
        if error_code == "InvalidAPIKey":
            return AIErrorType.INVALID_API_KEY
        if error_code == "QuotaExhausted":
            return AIErrorType.INSUFFICIENT_QUOTA
        if error_code == "OperationDenied.ContentRisk":
            return AIErrorType.CONTENT_SAFETY
        if "Throttling" in error_code:
            return AIErrorType.RATE_LIMIT_EXCEEDED
        return AIErrorType.UNKNOWN_ERROR


class WenxinAdapter(AIClient):
    """
    文心一言 AI 平台适配器
    """
    def __init__(self, api_key: str, secret_key: str, model_name: str = "ernie-bot-4.5", base_url: Optional[str] = None):
        super().__init__(AIPlatformType.WENXIN, model_name, api_key)
        self.secret_key = secret_key
        self.access_token = None
        self.token_expires_at = 0
        
        # 使用统一请求封装器
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="wenxin",
            base_url=base_url or "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"WenxinAdapter initialized for model: {model_name} with unified request wrapper")

    def _get_access_token(self):
        """获取访问令牌"""
        import time
        current_time = time.time()
        
        # 如果令牌未过期，直接返回
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token
            
        # 请求新的访问令牌
        token_url = f"https://aip.baidubce.com/oauth/2.0/token"
        token_params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(token_url, params=token_params)
            response.raise_for_status()
            data = response.json()
            
            self.access_token = data.get("access_token")
            expires_in = data.get("expires_in", 2592000)  # 默认30天
            self.token_expires_at = current_time + expires_in - 3600  # 提前1小时刷新
            
            return self.access_token
        except Exception as e:
            api_logger.error(f"Failed to get access token: {e}")
            raise

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 文心一言 API 发送请求
        """
        # 获取访问令牌
        access_token = self._get_access_token()
        
        messages = [{"role": "user", "content": prompt}]

        platform_config_manager = PlatformConfigManager()
        wenxin_config = platform_config_manager.get_platform_config('wenxin')

        temperature = kwargs.get('temperature', wenxin_config.default_temperature if wenxin_config else 0.7)
        max_tokens = kwargs.get('max_tokens', wenxin_config.default_max_tokens if wenxin_config else 1000)
        timeout = kwargs.get('timeout', wenxin_config.timeout if wenxin_config else 30)

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_output_tokens": max_tokens
        }

        start_time = time.time()
        try:
            # 使用统一请求封装器发送请求
            headers = {"Authorization": f"Bearer {access_token}"}
            response = self.request_wrapper.make_ai_request(
                endpoint=f"/completions?access_token={access_token}",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                headers=headers,
                timeout=timeout
            )

            response.raise_for_status()
            response_data = response.json()
            latency = time.time() - start_time

            if response_data and "result" in response_data:
                content = response_data["result"]
                tokens_used = (response_data.get("usage", {}).get("total_tokens", 0) 
                              if response_data.get("usage") else 0)
                api_logger.info(f"Wenxin response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
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
                error_message = response_data.get("error_msg", "Unknown Wenxin API error")
                error_code = response_data.get("error_code", 0)
                error_type = self._map_error_code(error_code)
                api_logger.error(f"Wenxin API returned error: {error_message}")
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=error_type,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            error_message = f"Wenxin API request failed: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            error_type = AIErrorType.UNKNOWN_ERROR
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 401:
                    error_type = AIErrorType.INVALID_API_KEY
                elif status_code == 429:
                    error_type = AIErrorType.RATE_LIMIT_EXCEEDED
                elif status_code >= 500:
                    error_type = AIErrorType.SERVER_ERROR

            record_error("wenxin", error_type.value, str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )
        except Exception as e:
            error_message = f"An unexpected error occurred with Wenxin API: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            record_error("wenxin", "UNKNOWN_ERROR", str(e))
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_error_code(self, error_code: int) -> AIErrorType:
        """将文心一言的错误码映射到标准错误类型"""
        if error_code in [110, 111]:  # Invalid API key
            return AIErrorType.INVALID_API_KEY
        elif error_code == 18:  # Quota exceeded
            return AIErrorType.INSUFFICIENT_QUOTA
        elif error_code in [336003, 336100]:  # Content safety
            return AIErrorType.CONTENT_SAFETY
        elif error_code == 17:  # Rate limit
            return AIErrorType.RATE_LIMIT_EXCEEDED
        return AIErrorType.UNKNOWN_ERROR
