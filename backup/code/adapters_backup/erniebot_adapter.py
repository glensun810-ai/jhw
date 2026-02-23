import time
import requests
from typing import Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from wechat_backend.network.request_wrapper import get_ai_request_wrapper
from wechat_backend.monitoring.metrics_collector import record_api_call, record_error
from wechat_backend.monitoring.logging_enhancements import log_api_request, log_api_response
from config_manager import Config as PlatformConfigManager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from wechat_backend.utils.ai_response_wrapper import log_detailed_response

class ErnieBotAdapter(AIClient):
    """
    百度文心一言 AI 平台的适配器
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
        
        api_logger.info(f"ErnieBotAdapter initialized for model: {model_name} with unified request wrapper")

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
                api_logger.info(f"ErnieBot response success. Tokens: {tokens_used}, Latency: {latency:.2f}s")
                
                # Log response to enhanced logger with context
                try:
                    execution_id = kwargs.get('execution_id', 'unknown')
                    log_detailed_response(
                        question=prompt,
                        response=content,
                        platform=self.platform_type.value,
                        model=self.model_name,
                        success=True,
                        latency_ms=int(latency * 1000),  # Convert to milliseconds
                        tokens_used=tokens_used,
                        execution_id=execution_id,
                        **kwargs  # Pass any additional context from kwargs
                    )
                except Exception as log_error:
                    # Don't let logging errors affect the main response
                    api_logger.warning(f"Failed to log response to enhanced logger: {log_error}")
                
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
                error_message = response_data.get("error_msg", "Unknown ErnieBot API error")
                error_code = response_data.get("error_code", 0)
                error_type = self._map_error_code(error_code)
                api_logger.error(f"ErnieBot API returned error: {error_message}")
                
                # Log failed response to enhanced logger with context
                try:
                    execution_id = kwargs.get('execution_id', 'unknown')
                    log_detailed_response(
                        question=prompt,
                        response="",  # No content in case of failure
                        platform=self.platform_type.value,
                        model=self.model_name,
                        success=False,
                        error_message=error_message,
                        error_type=error_type if error_type else AIErrorType.UNKNOWN_ERROR,
                        latency_ms=int(latency * 1000),  # Convert to milliseconds
                        execution_id=execution_id,
                        **kwargs  # Pass any additional context from kwargs
                    )
                except Exception as log_error:
                    # Don't let logging errors affect the main response
                    api_logger.warning(f"Failed to log failed response to enhanced logger: {log_error}")
                
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=error_type,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

        except requests.exceptions.RequestException as e:
            error_message = f"ErnieBot API request failed: {e}"
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

            # Log failed response to enhanced logger with context
            try:
                execution_id = kwargs.get('execution_id', 'unknown')
                log_detailed_response(
                    question=prompt,
                    response="",  # No content in case of failure
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=error_type if error_type else AIErrorType.REQUEST_EXCEPTION,
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log request exception to enhanced logger: {log_error}")
            
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
            error_message = f"An unexpected error occurred with ErnieBot API: {e}"
            api_logger.error(error_message)
            latency = time.time() - start_time
            
            # Log failed response to enhanced logger with context
            try:
                execution_id = kwargs.get('execution_id', 'unknown')
                log_detailed_response(
                    question=prompt,
                    response="",  # No content in case of failure
                    platform=self.platform_type.value,
                    model=self.model_name,
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.UNEXPECTED_ERROR,
                    latency_ms=int(latency * 1000),  # Convert to milliseconds
                    execution_id=execution_id,
                    **kwargs  # Pass any additional context from kwargs
                )
            except Exception as log_error:
                # Don't let logging errors affect the main response
                api_logger.warning(f"Failed to log unexpected error to enhanced logger: {log_error}")
            
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
