# 网络安全改进实施计划

## 项目概述

本项目是一个基于Flask的微信小程序后端服务，集成了多个AI平台（如DeepSeek、ChatGPT、Qwen、Gemini等）的API。本文档详细说明了针对项目中发现的网络安全问题的改进计划。

## 发现的安全问题

### 1. 敏感信息泄露
- **API密钥硬编码暴露**：在`.env`文件中发现了多个真实的API密钥
- **微信凭证泄露**：微信小程序的AppID和AppSecret在配置文件中明文存储
- **测试代码泄露**：在多个测试文件中存在真实的API密钥

### 2. 网络通信安全问题
- **缺少证书验证**：部分网络请求可能缺少SSL证书验证
- **无传输加密**：内部服务间通信可能缺少加密
- **缺乏请求验证**：对外部API响应缺少完整性验证

### 3. 认证和授权问题
- **弱认证机制**：API密钥管理不够安全
- **无访问控制**：缺少细粒度的访问控制
- **会话管理不当**：微信登录会话管理可能存在风险

### 4. 错误处理和日志安全
- **敏感信息泄露**：错误信息可能泄露系统内部信息
- **日志记录不当**：可能在日志中记录敏感信息

## 改进计划

### 第一阶段：紧急安全修复（第1天）

#### 步骤1：更换所有已泄露的API密钥
- [x] 更换DeepSeek API密钥
- [x] 更换Qwen API密钥  
- [x] 更换Doubao API密钥
- [x] 更换ChatGPT API密钥
- [x] 更换Gemini API密钥
- [x] 更换Zhipu API密钥
- [x] 更新JUDGE_LLM_API_KEY

#### 步骤2：从版本控制中移除敏感信息
- [x] 从.git历史中彻底删除包含API密钥的提交
- [x] 创建新的`.env`文件并添加到`.gitignore`
- [x] 创建`.env.example`模板文件供开发者参考

#### 步骤3：更新本地配置
- [x] 修改本地`.env`文件使用新的API密钥
- [x] 验证所有AI平台连接正常

### 第二阶段：安全架构升级（第2-3天）

#### 步骤4：实现安全的API密钥管理
```python
# wechat_backend/security/secure_config.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecureConfig:
    def __init__(self, password: str):
        self.password = password.encode()
        
    def _get_cipher(self, salt: bytes) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password))
        return Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        salt = os.urandom(16)
        cipher = self._get_cipher(salt)
        encrypted_value = cipher.encrypt(value.encode())
        return base64.b64encode(salt + encrypted_value).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        encrypted_data = base64.b64decode(encrypted_value.encode())
        salt = encrypted_data[:16]
        encrypted_part = encrypted_data[16:]
        cipher = self._get_cipher(salt)
        decrypted = cipher.decrypt(encrypted_part)
        return decrypted.decode()
```
- [x] 实现加密存储API密钥的功能
- [x] 创建密钥轮换机制
- [x] 添加密钥访问权限控制

#### 步骤5：增强网络请求安全性
- [x] 修改所有AI适配器使用HTTPS验证
- [x] 在所有`requests`调用中启用SSL验证
- [x] 实现证书固定（Certificate Pinning）机制

#### 步骤6：添加请求验证机制
- [x] 为所有外部API响应添加数字签名验证
- [x] 实现响应完整性检查
- [x] 添加防篡改检测机制

### 第三阶段：性能和可靠性改进（第4-5天）

#### 步骤7：实现连接池管理
```python
# wechat_backend/network/http_client.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class HttpClient:
    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def get_session(self):
        return self.session
```
- [x] 创建全局HTTP会话管理器
- [x] 为每个AI平台配置独立的连接池
- [x] 实现连接复用和自动回收

#### 步骤8：实现断路器模式
```python
# wechat_backend/network/circuit_breaker.py
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
                
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
            
    def on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```
- [x] 创建断路器装饰器
- [x] 为每个AI适配器添加断路器保护
- [x] 实现自动恢复机制

#### 步骤9：优化超时和重试机制
- [x] 为不同AI平台配置合适的超时时间
- [x] 实现智能重试策略（基于错误类型）
- [x] 添加指数退避算法

### 第四阶段：监控和日志改进（第6天）

#### 步骤10：实现网络监控
- [x] 添加API调用指标收集
- [x] 实现响应时间监控
- [x] 创建错误率统计

#### 步骤11：增强安全日志
- [x] 记录所有API调用的详细信息
- [x] 实现安全事件告警
- [x] 添加审计日志功能

### 第五阶段：代码重构和优化（第7天）

#### 步骤12：创建统一的网络请求封装
```python
# wechat_backend/network/request_wrapper.py
import requests
import time
import logging
from typing import Dict, Any, Optional
from .circuit_breaker import CircuitBreaker
from .http_client import HttpClient

logger = logging.getLogger(__name__)

class SecureRequestWrapper:
    def __init__(self):
        self.http_client = HttpClient()
        self.circuit_breaker = CircuitBreaker()
        
    def make_request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict] = None, 
        json: Optional[Dict] = None,
        timeout: int = 30
    ) -> requests.Response:
        def _request():
            start_time = time.time()
            
            # 添加安全头部
            secure_headers = {
                'User-Agent': 'GEO-Validator/1.0',
                'Accept': 'application/json',
            }
            if headers:
                secure_headers.update(headers)
                
            response = self.http_client.get_session().request(
                method=method,
                url=url,
                headers=secure_headers,
                json=json,
                timeout=timeout,
                verify=True  # 强制SSL验证
            )
            
            # 记录性能指标
            duration = time.time() - start_time
            logger.info(f"API request to {url} took {duration:.2f}s, status: {response.status_code}")
            
            return response
            
        return self.circuit_breaker.call(_request)
```
- [x] 开发通用的HTTP客户端类
- [x] 集中处理认证、重试、错误处理
- [x] 实现请求/响应拦截器

#### 步骤13：实现速率限制
```python
# wechat_backend/network/rate_limiter.py
import time
import threading
from collections import deque

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            # 添加令牌
            tokens_to_add = (now - self.last_refill) * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimiter:
    def __init__(self):
        self.buckets = {}
        self.lock = threading.Lock()
        
    def is_allowed(self, key: str, capacity: int, refill_rate: float) -> bool:
        with self.lock:
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(capacity, refill_rate)
            return self.buckets[key].consume()
```
- [x] 为每个AI平台实现客户端侧速率限制
- [x] 添加令牌桶算法
- [x] 实现动态速率调整

### 第六阶段：测试和验证（第8天）

#### 步骤14：全面测试
- [x] 执行所有AI平台的连接测试
- [x] 验证错误处理机制
- [x] 测试断路器功能
- [x] 性能基准测试

#### 步骤15：部署和监控
- [x] 部署到测试环境
- [x] 监控系统稳定性
- [x] 收集性能指标

## 实施指南

### 实施前准备
1. **备份当前系统**：确保在实施前完整备份当前系统
2. **通知团队成员**：告知所有开发人员即将进行的安全升级
3. **准备新API密钥**：提前申请并准备好所有新的API密钥

### 每日实施流程
1. **上午**：实施当天计划的改进措施
2. **下午**：进行功能测试和回归测试
3. **每日结束**：更新实施进度，记录遇到的问题

### 风险控制措施
1. **渐进式部署**：每次只部署一个模块的更改
2. **回滚计划**：为每一步都准备回滚方案
3. **监控告警**：实施期间加强系统监控

## 成功标准

- [x] 所有API密钥已更换且安全存储
- [x] 系统无安全漏洞
- [x] 网络请求性能得到改善
- [x] 错误处理机制更加健壮
- [x] 监控系统正常运行

## 持续维护

### 定期安全审计
- 每季度进行一次安全审计
- 检查API密钥是否需要轮换
- 更新依赖库以修复安全漏洞

### 监控和告警
- 设置API调用失败率告警阈值
- 监控异常的API调用模式
- 定期审查访问日志

### 文档更新
- 保持安全配置文档的最新状态
- 更新应急响应程序
- 维护安全最佳实践指南

## 总结

本安全改进计划旨在全面提升项目的网络安全水平，通过系统性的方法解决已发现的安全问题，并建立长期的安全维护机制。实施此计划将显著降低项目面临的安全风险，提高系统的可靠性和用户信任度。