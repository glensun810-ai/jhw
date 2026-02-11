import time
from typing import Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType

# 尝试导入 google.generativeai，如果失败（如Python版本不兼容），则优雅降级
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except Exception as e:
    api_logger.error(f"Failed to import google.generativeai: {e}. Gemini adapter will be disabled.")
    HAS_GEMINI = False

class GeminiAdapter(AIClient):
    """
    Google Gemini AI 平台的适配器
    """
    def __init__(self, api_key: str, model_name: str = "gemini-pro", **kwargs):
        super().__init__(AIPlatformType.GEMINI, model_name, api_key)
        
        if not HAS_GEMINI:
            api_logger.warning("Gemini SDK not available. Requests to Gemini will fail.")
            self.model = None
            return

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            api_logger.info(f"GeminiAdapter initialized for model: {model_name}")
        except Exception as e:
            api_logger.error(f"Failed to configure Gemini client: {e}")
            # 不抛出异常，允许系统启动，但在调用时报错
            self.model = None

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        向 Gemini API 发送请求
        """
        if not HAS_GEMINI or not self.model:
            return AIResponse(
                success=False,
                error_message="Gemini SDK is not available in this environment (Python 3.14 compatibility issue).",
                error_type=AIErrorType.SERVER_ERROR,
                model=self.model_name,
                platform=self.platform_type.value
            )

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
        if not HAS_GEMINI:
            return AIErrorType.UNKNOWN_ERROR

        try:
            from google.api_core import exceptions as google_exceptions
            
            if isinstance(error, google_exceptions.PermissionDenied):
                return AIErrorType.INVALID_API_KEY
            if isinstance(error, google_exceptions.ResourceExhausted):
                return AIErrorType.INSUFFICIENT_QUOTA
            if isinstance(error, google_exceptions.InvalidArgument):
                return AIErrorType.CONTENT_SAFETY
            if isinstance(error, google_exceptions.InternalServerError):
                return AIErrorType.SERVER_ERROR
        except ImportError:
            pass

        return AIErrorType.UNKNOWN_ERROR
