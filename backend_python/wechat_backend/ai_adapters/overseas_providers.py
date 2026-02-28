"""
海外 AI 平台提供者实现

包含：
- ChatGPTProvider (OpenAI)
- GeminiProvider (Google)
- ZhipuProvider (智谱 AI)
- WenxinProvider (百度文心一言)

这些 provider 都遵循 OpenAI 兼容格式或各自的标准 API 格式
"""
import time
import requests
import json
import re
from typing import Dict, Any, List
from urllib.parse import urlparse
from wechat_backend.ai_adapters.base_provider import BaseAIProvider
from wechat_backend.logging_config import api_logger
from wechat_backend.network.request_wrapper import get_ai_request_wrapper


# ==================== ChatGPT Provider (OpenAI) ====================

class ChatGPTProvider(BaseAIProvider):
    """
    ChatGPT/OpenAI 平台提供者
    使用 OpenAI 标准 API 格式
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://api.openai.com/v1"
    ):
        super().__init__(api_key, model_name)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="chatgpt",
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"ChatGPTProvider initialized for model: {model_name}")

    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """发送问题到 OpenAI API"""
        start_time = time.time()
        
        try:
            if not self.api_key:
                raise ValueError("ChatGPT API Key 未设置")
            
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30
            )
            
            latency = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    'error': f"API 请求失败：{response.status_code}",
                    'status_code': response.status_code,
                    'success': False,
                    'latency': latency
                }
            
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = response_data.get("usage", {})
            
            return {
                'content': content,
                'model': response_data.get("model", self.model_name),
                'platform': 'chatgpt',
                'tokens_used': usage.get("total_tokens", 0),
                'latency': latency,
                'raw_response': response_data,
                'success': True
            }
            
        except Exception as e:
            latency = time.time() - start_time
            api_logger.error(f"ChatGPTProvider error: {e}")
            return {
                'error': str(e),
                'success': False,
                'latency': latency
            }

    def extract_citations(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """提取引用链接"""
        return self._extract_urls_from_response(raw_response)

    def to_standard_format(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """转换为标准格式"""
        return {
            'ranking_list': [],
            'brand_details': {},
            'unlisted_competitors': []
        }

    def _extract_urls_from_response(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """从响应中提取 URL"""
        citations = []
        response_text = self._get_response_text(raw_response)
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, response_text)
        
        for url in urls:
            try:
                parsed = urlparse(url)
                citations.append({
                    'url': url,
                    'domain': parsed.netloc,
                    'title': f'Link to {parsed.netloc}',
                    'type': 'external_link'
                })
            except Exception:
                continue
        
        return citations


# ==================== Gemini Provider (Google) ====================

class GeminiProvider(BaseAIProvider):
    """
    Gemini/Google 平台提供者
    使用 Google Generative AI API 格式
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-pro",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    ):
        super().__init__(api_key, model_name)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        
        api_logger.info(f"GeminiProvider initialized for model: {model_name}")

    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """发送问题到 Google Gemini API"""
        start_time = time.time()
        
        try:
            if not self.api_key:
                raise ValueError("Gemini API Key 未设置")
            
            # Gemini API 格式
            url = f"{self.base_url}/models/{self.model_name}:generateContent"
            headers = {"Content-Type": "application/json"}
            params = {"key": self.api_key}
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens
                }
            }
            
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=30
            )
            
            latency = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    'error': f"API 请求失败：{response.status_code}",
                    'status_code': response.status_code,
                    'success': False,
                    'latency': latency
                }
            
            response_data = response.json()
            content = ""
            if "candidates" in response_data and response_data["candidates"]:
                content = response_data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            return {
                'content': content,
                'model': self.model_name,
                'platform': 'gemini',
                'latency': latency,
                'raw_response': response_data,
                'success': True
            }
            
        except Exception as e:
            latency = time.time() - start_time
            api_logger.error(f"GeminiProvider error: {e}")
            return {
                'error': str(e),
                'success': False,
                'latency': latency
            }

    def extract_citations(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """提取引用链接"""
        return self._extract_urls_from_response(raw_response)

    def to_standard_format(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """转换为标准格式"""
        return {
            'ranking_list': [],
            'brand_details': {},
            'unlisted_competitors': []
        }

    def _extract_urls_from_response(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """从响应中提取 URL"""
        citations = []
        content = ""
        if "candidates" in raw_response and raw_response["candidates"]:
            content = raw_response["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        for url in urls:
            try:
                parsed = urlparse(url)
                citations.append({
                    'url': url,
                    'domain': parsed.netloc,
                    'title': f'Link to {parsed.netloc}',
                    'type': 'external_link'
                })
            except Exception:
                continue
        
        return citations


# ==================== Zhipu Provider (智谱 AI) ====================

class ZhipuProvider(BaseAIProvider):
    """
    智谱 AI 平台提供者
    使用智谱 AI API 格式（兼容 OpenAI 格式）
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "glm-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    ):
        super().__init__(api_key, model_name)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        
        self.request_wrapper = get_ai_request_wrapper(
            platform_name="zhipu",
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3
        )
        
        api_logger.info(f"ZhipuProvider initialized for model: {model_name}")

    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """发送问题到智谱 AI API"""
        start_time = time.time()
        
        try:
            if not self.api_key:
                raise ValueError("Zhipu API Key 未设置")
            
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            
            response = self.request_wrapper.make_ai_request(
                endpoint="/chat/completions",
                prompt=prompt,
                model=self.model_name,
                json=payload,
                timeout=30
            )
            
            latency = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    'error': f"API 请求失败：{response.status_code}",
                    'status_code': response.status_code,
                    'success': False,
                    'latency': latency
                }
            
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = response_data.get("usage", {})
            
            return {
                'content': content,
                'model': response_data.get("model", self.model_name),
                'platform': 'zhipu',
                'tokens_used': usage.get("total_tokens", 0),
                'latency': latency,
                'raw_response': response_data,
                'success': True
            }
            
        except Exception as e:
            latency = time.time() - start_time
            api_logger.error(f"ZhipuProvider error: {e}")
            return {
                'error': str(e),
                'success': False,
                'latency': latency
            }

    def extract_citations(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """提取引用链接"""
        return self._extract_urls_from_response(raw_response)

    def to_standard_format(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """转换为标准格式"""
        return {
            'ranking_list': [],
            'brand_details': {},
            'unlisted_competitors': []
        }

    def _extract_urls_from_response(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """从响应中提取 URL"""
        citations = []
        response_text = self._get_response_text(raw_response)
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, response_text)
        
        for url in urls:
            try:
                parsed = urlparse(url)
                citations.append({
                    'url': url,
                    'domain': parsed.netloc,
                    'title': f'Link to {parsed.netloc}',
                    'type': 'external_link'
                })
            except Exception:
                continue
        
        return citations


# ==================== Wenxin Provider (百度文心一言) ====================

class WenxinProvider(BaseAIProvider):
    """
    百度文心一言平台提供者
    使用百度千帆大模型 API 格式
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "ernie-bot-4.0",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1"
    ):
        super().__init__(api_key, model_name)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        
        api_logger.info(f"WenxinProvider initialized for model: {model_name}")

    def ask_question(self, prompt: str) -> Dict[str, Any]:
        """发送问题到百度文心一言 API"""
        start_time = time.time()
        
        try:
            if not self.api_key:
                raise ValueError("Wenxin API Key 未设置")
            
            # 文心一言 API 需要 access_token
            access_token = self._get_access_token()
            if not access_token:
                raise ValueError("无法获取文心一言 access_token")
            
            url = f"{self.base_url}/wenxinworkshop/chat/completions?access_token={access_token}"
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            latency = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    'error': f"API 请求失败：{response.status_code}",
                    'status_code': response.status_code,
                    'success': False,
                    'latency': latency
                }
            
            response_data = response.json()
            content = response_data.get("result", "")
            
            return {
                'content': content,
                'model': self.model_name,
                'platform': 'wenxin',
                'latency': latency,
                'raw_response': response_data,
                'success': True
            }
            
        except Exception as e:
            latency = time.time() - start_time
            api_logger.error(f"WenxinProvider error: {e}")
            return {
                'error': str(e),
                'success': False,
                'latency': latency
            }

    def _get_access_token(self) -> str:
        """获取文心一言 access_token"""
        # 智谱 AI 使用 API Key 认证，这里简化处理
        # 实际实现需要根据百度 API 文档进行完善
        return self.api_key

    def extract_citations(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """提取引用链接"""
        return self._extract_urls_from_response(raw_response)

    def to_standard_format(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """转换为标准格式"""
        return {
            'ranking_list': [],
            'brand_details': {},
            'unlisted_competitors': []
        }

    def _extract_urls_from_response(self, raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """从响应中提取 URL"""
        citations = []
        response_text = raw_response.get("result", "")
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, response_text)
        
        for url in urls:
            try:
                parsed = urlparse(url)
                citations.append({
                    'url': url,
                    'domain': parsed.netloc,
                    'title': f'Link to {parsed.netloc}',
                    'type': 'external_link'
                })
            except Exception:
                continue
        
        return citations
