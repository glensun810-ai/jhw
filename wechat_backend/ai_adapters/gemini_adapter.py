import time
import google.generativeai as genai
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType

class GeminiAdapter(AIClient):
    """
    Google Gemini AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "gemini-pro", **kwargs):
        super().__init__(AIPlatformType.GEMINI, model_name, api_key)
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            api_logger.info(f"GeminiAdapter initialized for model: {model_name}")
        except Exception as e:
            api_logger.error(f"Failed to configure Gemini client: {e}")
            raise

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Gemini API 发送请求
        """
        start_time = time.time()
        try:
            response = self.model.generate_content(prompt)
            latency = time.time() - start_time
            
            content = response.text
            
            # Gemini API 不直接返回 token 数量，可以估算或留空
            tokens_used = len(prompt.split()) + len(content.split()) 

            api_logger.info(f"Gemini response success. Latency: {latency:.2f}s")
            return AIResponse(
                success=True,
                content=content,
                model=self.model_name,
                platform=self.platform_type.value,
                tokens_used=tokens_used,
                latency=latency,
                metadata={'response_id': str(response.candidates[0].citation_metadata)} if response.candidates and response.candidates[0].citation_metadata else {}
            )
        except Exception as e:
            latency = time.time() - start_time
            error_message = f"An unexpected error occurred with Gemini API: {e}"
            error_type = self._map_error(e)
            api_logger.error(error_message)
            return AIResponse(
                success=False,
                error_message=error_message,
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

    def _map_error(self, error: Exception) -> AIErrorType:
        """将Gemini的异常映射到标准错误类型"""
        from google.api_core import exceptions as google_exceptions
        
        if isinstance(error, google_exceptions.PermissionDenied):
            return AIErrorType.INVALID_API_KEY
        if isinstance(error, google_exceptions.ResourceExhausted):
            return AIErrorType.INSUFFICIENT_QUOTA
        if isinstance(error, google_exceptions.InvalidArgument):
            return AIErrorType.CONTENT_SAFETY
        if isinstance(error, google_exceptions.InternalServerError):
            return AIErrorType.SERVER_ERROR
        return AIErrorType.UNKNOWN_ERROR
