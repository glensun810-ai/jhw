#!/usr/bin/env python3
"""
安全架构升级工具
此脚本用于实现安全的API密钥管理和网络请求安全增强
"""

import os
import sys
from pathlib import Path
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib
import json


def create_secure_config_module():
    """创建安全配置管理模块"""
    
    secure_config_content = '''"""
安全配置管理模块
提供加密存储和管理敏感配置信息的功能
"""

import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmt.primitives import hashes
from cryptography.hazmt.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureConfig:
    """安全配置管理类"""
    
    def __init__(self, password: str = None):
        """
        初始化安全配置管理器
        :param password: 用于加密/解密的密码，如果未提供则使用环境变量
        """
        self.password = password or os.getenv('SECURE_CONFIG_PASSWORD', 'default_password_for_dev')
        self.password_bytes = self.password.encode()
        
    def _get_cipher(self, salt: bytes) -> Fernet:
        """根据盐值获取加密器"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password_bytes))
        return Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """加密单个值"""
        salt = os.urandom(16)
        cipher = self._get_cipher(salt)
        encrypted_value = cipher.encrypt(value.encode())
        # 将盐和加密值一起编码
        return base64.b64encode(salt + encrypted_value).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """解密单个值"""
        try:
            encrypted_data = base64.b64decode(encrypted_value.encode())
            salt = encrypted_data[:16]
            encrypted_part = encrypted_data[16:]
            cipher = self._get_cipher(salt)
            decrypted = cipher.decrypt(encrypted_part)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")
    
    def encrypt_config_dict(self, config_dict: dict) -> str:
        """加密整个配置字典"""
        json_str = json.dumps(config_dict)
        return self.encrypt_value(json_str)
    
    def decrypt_config_dict(self, encrypted_config: str) -> dict:
        """解密配置字典"""
        json_str = self.decrypt_value(encrypted_config)
        return json.loads(json_str)


# 全局配置管理器实例
_config_manager = None


def get_config_manager(password: str = None) -> SecureConfig:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfig(password)
    return _config_manager


def load_secure_config_from_file(file_path: str, password: str = None) -> dict:
    """从加密文件加载配置"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"配置文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        encrypted_content = f.read().strip()
    
    manager = get_config_manager(password)
    return manager.decrypt_config_dict(encrypted_content)


def save_secure_config_to_file(config_dict: dict, file_path: str, password: str = None) -> None:
    """保存配置到加密文件"""
    manager = get_config_manager(password)
    encrypted_content = manager.encrypt_config_dict(config_dict)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(encrypted_content)
    
    # 设置文件权限，只允许所有者读写
    os.chmod(file_path, 0o600)
    print(f"已安全保存配置到: {file_path}")


# 便捷函数
def encrypt_sensitive_value(value: str, password: str = None) -> str:
    """便捷函数：加密敏感值"""
    manager = get_config_manager(password)
    return manager.encrypt_value(value)


def decrypt_sensitive_value(encrypted_value: str, password: str = None) -> str:
    """便捷函数：解密敏感值"""
    manager = get_config_manager(password)
    return manager.decrypt_value(encrypted_value)
'''
    
    # 创建目录结构
    wechat_backend_dir = Path('wechat_backend')
    security_dir = wechat_backend_dir / 'security'
    security_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入安全配置模块
    with open(security_dir / 'secure_config.py', 'w', encoding='utf-8') as f:
        f.write(secure_config_content)
    
    # 创建__init__.py文件
    with open(security_dir / '__init__.py', 'w', encoding='utf-8') as f:
        f.write('"""安全模块初始化"""')
    
    print("✓ 已创建安全配置管理模块: wechat_backend/security/secure_config.py")


def create_network_security_module():
    """创建网络安全模块"""
    
    network_security_content = '''"""
网络安全模块
提供安全的HTTP请求和证书验证功能
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ssl
import certifi
import hashlib
import hmac
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SecureHttpClient:
    """安全HTTP客户端"""
    
    def __init__(self, 
                 verify_ssl: bool = True, 
                 timeout: int = 30,
                 max_retries: int = 3,
                 cert_file: Optional[str] = None):
        """
        初始化安全HTTP客户端
        :param verify_ssl: 是否验证SSL证书
        :param timeout: 请求超时时间
        :param max_retries: 最大重试次数
        :param cert_file: 自定义证书文件路径
        """
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.cert_file = cert_file or certifi.where()  # 使用certifi提供的证书包
        
        # 创建会话
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置默认头部
        self.session.headers.update({
            'User-Agent': 'GEO-Validator-Secure-Client/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def _prepare_headers(self, additional_headers: Optional[Dict] = None) -> Dict:
        """准备请求头部"""
        headers = self.session.headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers
    
    def get(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全GET请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('GET', url, headers=headers, **kwargs)
    
    def post(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全POST请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('POST', url, headers=headers, **kwargs)
    
    def put(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全PUT请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('PUT', url, headers=headers, **kwargs)
    
    def delete(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """安全DELETE请求"""
        headers = self._prepare_headers(headers)
        return self._make_request('DELETE', url, headers=headers, **kwargs)
    
    def _make_request(self, method: str, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """执行安全请求"""
        # 确保使用HTTPS（除非明确指定不验证SSL）
        if self.verify_ssl and not url.startswith('https://'):
            logger.warning(f"尝试对非HTTPS URL 进行安全请求: {url}")
        
        # 设置默认参数
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('verify', self.cert_file if self.verify_ssl else False)
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            
            # 记录请求指标
            logger.info(f"API请求: {method} {url} -> {response.status_code} ({response.elapsed.total_seconds():.2f}s)")
            
            # 验证响应
            self._validate_response(response)
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {method} {url} - {str(e)}")
            raise
    
    def _validate_response(self, response: requests.Response) -> None:
        """验证响应的安全性"""
        # 检查内容类型是否符合预期
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/json' in content_type:
            # 尝试解析JSON以验证响应完整性
            try:
                response.json()
            except ValueError:
                raise ValueError("响应不是有效的JSON格式")
        
        # 检查是否有安全相关的头部
        if 'server' in response.headers:
            server_header = response.headers['server']
            logger.debug(f"Server: {server_header}")
    
    def close(self):
        """关闭会话"""
        self.session.close()


class CertificatePinner:
    """证书固定器"""
    
    def __init__(self, pinned_certificates: Dict[str, str]):
        """
        初始化证书固定器
        :param pinned_certificates: 主机名到证书指纹的映射
        """
        self.pinned_certificates = pinned_certificates
    
    def verify_certificate(self, hostname: str, certificate_der: bytes) -> bool:
        """验证证书是否与固定的指纹匹配"""
        if hostname not in self.pinned_certificates:
            return True  # 如果没有固定证书，则跳过验证
        
        expected_fingerprint = self.pinned_certificates[hostname]
        actual_fingerprint = hashlib.sha256(certificate_der).hexdigest()
        
        return hmac.compare_digest(expected_fingerprint, actual_fingerprint)


# 全局HTTP客户端实例
_http_client = None


def get_http_client(**kwargs) -> SecureHttpClient:
    """获取安全HTTP客户端实例"""
    global _http_client
    if _http_client is None:
        _http_client = SecureHttpClient(**kwargs)
    return _http_client


def reset_http_client():
    """重置HTTP客户端实例"""
    global _http_client
    if _http_client:
        _http_client.close()
    _http_client = None
'''
    
    # 获取或创建网络安全目录
    wechat_backend_dir = Path('wechat_backend')
    network_dir = wechat_backend_dir / 'network'
    network_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入网络安全模块
    with open(network_dir / 'security.py', 'w', encoding='utf-8') as f:
        f.write(network_security_content)
    
    # 创建__init__.py文件
    with open(network_dir / '__init__.py', 'w', encoding='utf-8') as f:
        f.write('"""网络安全模块初始化"""')
    
    print("✓ 已创建网络安全模块: wechat_backend/network/security.py")


def update_ai_adapters_for_security():
    """更新AI适配器以使用安全的网络请求"""
    
    # 更新DeepSeek适配器
    deepseek_adapter_content = '''import time
from typing import Dict, Any, Optional
from ..logging_config import api_logger
from .base_adapter import AIClient, AIResponse, AIPlatformType, AIErrorType
from ..network.security import get_http_client
from config_manager import Config as PlatformConfigManager


class DeepSeekAdapter(AIClient):
    """
    DeepSeek AI 平台适配器
    用于将 DeepSeek API 接入 GEO 内容质量验证系统
    支持两种模式：普通对话模式（deepseek-chat）和搜索/推理模式（deepseek-reasoner）
    包含内部 Prompt 约束逻辑，可配置是否启用中文回答及事实性约束
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        mode: str = "chat",  # 新增 mode 参数，支持 "chat" 或 "reasoner"
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: str = "https://api.deepseek.com/v1",
        enable_chinese_constraint: bool = True  # 新增参数：是否启用中文约束
    ):
        """
        初始化 DeepSeek 适配器

        Args:
            api_key: DeepSeek API 密钥
            model_name: 使用的模型名称，默认为 "deepseek-chat"
            mode: 调用模式，"chat" 表示普通对话模式，"reasoner" 表示搜索/推理模式
            temperature: 温度参数，控制生成内容的随机性
            max_tokens: 最大生成 token 数
            base_url: API 基础 URL
            enable_chinese_constraint: 是否启用中文回答约束，默认为 True
        """
        super().__init__(AIPlatformType.DEEPSEEK, model_name, api_key)
        self.mode = mode  # 存储模式
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.enable_chinese_constraint = enable_chinese_constraint  # 存储中文约束开关
        api_logger.info(f"DeepSeekAdapter initialized for model: {model_name}")

    def send_prompt(self, prompt: str, **kwargs) -> AIResponse:
        """
        发送提示到 DeepSeek 并返回标准化响应

        Args:
            prompt: 用户输入的提示文本

        Returns:
            AIResponse: 包含 DeepSeek 响应的统一数据结构
        """
        # 记录请求开始时间以计算延迟
        start_time = time.time()

        try:
            # 验证 API Key 是否存在
            if not self.api_key:
                raise ValueError("DeepSeek API Key 未设置")

            # 如果启用了中文约束，在原始 prompt 基础上添加约束指令
            # 这样做不会影响上层传入的原始 prompt，仅在发送给 AI 时附加约束
            processed_prompt = prompt
            if self.enable_chinese_constraint:
                constraint_instruction = (
                    "请严格按照以下要求作答：\\n"
                    "1. 必须使用中文回答\\n"
                    "2. 基于事实和公开信息作答\\n"
                    "3. 避免在不确定时胡编乱造\\n"
                    "4. 输出结构清晰（分点或分段）\\n\\n"
                )
                processed_prompt = constraint_instruction + prompt

            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 根据模式构建不同的请求体
            # 普通对话模式 (chat): 适用于日常对话和一般性问题解答
            # 搜索/推理模式 (reasoner): 适用于需要深度分析和推理的问题
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": processed_prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            # 如果是推理模式，添加额外参数
            if self.mode == "reasoner":
                payload["reasoner"] = "search"  # 启用搜索推理能力

            # 使用安全HTTP客户端发送请求到 DeepSeek API
            http_client = get_http_client()
            response = http_client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get('timeout', 30)  # 设置请求超时时间为30秒
            )

            # 计算请求延迟
            latency = time.time() - start_time

            # 检查响应状态码
            if response.status_code != 200:
                error_message = f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                return AIResponse(
                    success=False,
                    error_message=error_message,
                    error_type=AIErrorType.SERVER_ERROR,
                    model=self.model_name,
                    platform=self.platform_type.value,
                    latency=latency
                )

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

            # 返回成功的 AIResponse，包含模式信息
            return AIResponse(
                success=True,
                content=content,
                model=response_data.get("model", self.model_name),
                platform=self.platform_type.value,
                tokens_used=usage.get("total_tokens", 0),
                latency=latency,
                metadata=response_data
            )

        except requests.exceptions.Timeout:
            # 处理请求超时异常
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message="请求超时",
                error_type=AIErrorType.SERVER_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except requests.exceptions.RequestException as e:
            # 处理其他请求相关异常
            latency = time.time() - start_time
            error_type = self._map_request_exception(e)
            return AIResponse(
                success=False,
                error_message=f"请求异常: {str(e)}",
                error_type=error_type,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except ValueError as e:
            # 处理 API Key 验证等值错误
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message=str(e),
                error_type=AIErrorType.INVALID_API_KEY,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )

        except Exception as e:
            # 处理其他未预期的异常
            latency = time.time() - start_time
            return AIResponse(
                success=False,
                error_message=f"未知错误: {str(e)}",
                error_type=AIErrorType.UNKNOWN_ERROR,
                model=self.model_name,
                platform=self.platform_type.value,
                latency=latency
            )
    
    def _map_request_exception(self, e: requests.exceptions.RequestException) -> AIErrorType:
        """将请求异常映射到标准错误类型"""
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                return AIErrorType.INVALID_API_KEY
            elif status_code == 429:
                return AIErrorType.RATE_LIMIT_EXCEEDED
            elif status_code >= 500:
                return AIErrorType.SERVER_ERROR
            elif status_code == 403:
                return AIErrorType.INVALID_API_KEY
        return AIErrorType.UNKNOWN_ERROR

    def health_check(self) -> bool:
        """
        检查 DeepSeek 客户端的健康状态
        通过发送一个简单的测试请求来验证连接

        Returns:
            bool: 客户端是否健康可用
        """
        try:
            # 发送一个简单的测试请求
            test_response = self.send_prompt("你好，请回复'正常'。")
            return test_response.success
        except Exception:
            return False
'''
    
    # 更新AI适配器目录
    ai_adapters_dir = Path('wechat_backend/ai_adapters')
    
    # 保存更新后的DeepSeek适配器
    with open(ai_adapters_dir / 'deepseek_adapter.py', 'w', encoding='utf-8') as f:
        f.write(deepseek_adapter_content)
    
    print("✓ 已更新DeepSeek适配器以使用安全网络请求")


def install_required_packages():
    """输出需要安装的安全相关包"""
    
    requirements_content = '''
# 安全相关的依赖包
cryptography>=41.0.0  # 用于加密操作
certifi>=2023.0.0     # 用于SSL证书验证
requests>=2.31.0      # HTTP请求库
urllib3>=2.0.0        # 底层HTTP库
'''
    
    # 读取现有的requirements.txt
    req_file = Path('requirements.txt')
    if req_file.exists():
        with open(req_file, 'r', encoding='utf-8') as f:
            existing_reqs = f.read()
    else:
        existing_reqs = ""
    
    # 添加安全相关的包（如果不存在）
    if 'cryptography' not in existing_reqs:
        with open(req_file, 'a', encoding='utf-8') as f:
            f.write(requirements_content)
        print("✓ 已将安全相关包添加到 requirements.txt")
    else:
        print("- 安全相关包已在 requirements.txt 中")


def main():
    print("🚀 开始执行安全改进计划 - 第二步：安全架构升级")
    print("=" * 60)
    
    print("\n1. 创建安全配置管理模块...")
    create_secure_config_module()
    
    print("\n2. 创建网络安全模块...")
    create_network_security_module()
    
    print("\n3. 更新AI适配器以使用安全网络请求...")
    update_ai_adapters_for_security()
    
    print("\n4. 添加安全相关依赖包...")
    install_required_packages()
    
    print("\n" + "=" * 60)
    print("✅ 第二步完成！")
    print("\n已完成：")
    print("• 创建了安全配置管理模块")
    print("• 创建了网络安全模块，包含证书验证等功能")
    print("• 更新了AI适配器以使用安全的网络请求")
    print("• 添加了安全相关的依赖包")
    print("\n下一步：")
    print("• 部署安全配置管理器到生产环境")
    print("• 配置加密密钥管理")
    print("• 测试安全网络请求功能")


if __name__ == "__main__":
    main()