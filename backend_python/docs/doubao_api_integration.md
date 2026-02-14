# 豆包(Doubao) API 集成文档

## 概述
本文档详细介绍了如何在GEO内容质量验证器项目中集成字节跳动的豆包(Doubao)API。

## API端点
- **基础URL**: `https://ark.cn-beijing.volces.com`
- **API端点**: `/api/v3/chat/completions`
- **完整URL**: `https://ark.cn-beijing.volces.com/api/v3/chat/completions`

## 配置要求

### 环境变量
在 `.env` 文件中添加以下配置：

```bash
# 豆包API配置
DOUBAO_API_KEY=your_doubao_api_key_here
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com  # 可选，默认为上述URL
DOUBAO_TEMPERATURE=0.7  # 可选，默认为0.7
DOUBAO_MAX_TOKENS=1000  # 可选，默认为1000
DOUBAO_TIMEOUT=30       # 可选，默认为30秒
DOUBAO_RETRY_TIMES=3    # 可选，默认为3次
```

### 模型配置
豆包API支持多种模型，常见的模型ID格式为：
- `ep-20240520111905-bavcb` (示例模型ID)
- 具体模型ID需要在豆包开发者平台获取

## 适配器实现

### DoubaoAdapter 类
位于 `wechat_backend/ai_adapters/doubao_adapter.py`

#### 主要功能
1. **初始化**: 配置API密钥、模型名称和基础URL
2. **请求发送**: 通过统一请求封装器发送请求
3. **错误处理**: 映射API错误到标准错误类型
4. **参数配置**: 支持温度、最大token数等参数

#### 关键方法
- `send_prompt(prompt, **kwargs)`: 发送提示词到豆包API
- `_map_error_message(error_message)`: 将错误消息映射到标准错误类型

## 错误处理

### 标准错误类型
- `INVALID_API_KEY`: API密钥无效或认证失败
- `INSUFFICIENT_QUOTA`: 配额不足或信用额度超限
- `CONTENT_SAFETY`: 内容安全审查不通过
- `RATE_LIMIT_EXCEEDED`: 请求频率超限
- `SERVER_ERROR`: 平台服务器错误
- `UNKNOWN_ERROR`: 未知错误

### 错误映射逻辑
- 包含 "invalid api" 或 "authentication" → `INVALID_API_KEY`
- 包含 "quota" 或 "credit" → `INSUFFICIENT_QUOTA`
- 包含 "content" 且包含 "policy" 或 "safety" → `CONTENT_SAFETY`
- 包含 "safety" 或 "policy" → `CONTENT_SAFETY`
- 其他情况 → `UNKNOWN_ERROR`

## 使用示例

### 通过工厂创建适配器
```python
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType

# 创建豆包适配器
adapter = AIAdapterFactory.create(
    AIPlatformType.DOUBAO, 
    api_key=os.getenv('DOUBAO_API_KEY'), 
    model_name='ep-20240520111905-bavcb'
)

# 发送请求
response = adapter.send_prompt("你好，请简单介绍一下自己。")

if response.success:
    print(f"响应内容: {response.content}")
else:
    print(f"请求失败: {response.error_message}")
```

### 直接使用适配器
```python
from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter

adapter = DoubaoAdapter(
    api_key=os.getenv('DOUBAO_API_KEY'),
    model_name='ep-20240520111905-bavcb'
)

response = adapter.send_prompt(
    "你好，请简单介绍一下自己。",
    temperature=0.7,
    max_tokens=100
)
```

## 安全特性
- **统一请求封装**: 使用统一的请求封装器处理认证、重试、错误处理
- **输入验证**: 对所有输入进行验证和净化
- **错误处理**: 完善的错误处理和日志记录
- **速率限制**: 内置速率限制机制
- **断路器**: 防止级联故障

## 监控与日志
- 所有API调用都会被记录到日志系统
- 包含请求大小、响应时间、状态码等指标
- 错误会被记录并触发相应的监控告警

## 测试
项目包含专门的测试文件 `test_doubao_integration.py` 用于验证豆包API集成的正确性。

## 注意事项
1. 确保API密钥安全存储，不要硬编码在代码中
2. 根据实际需求调整模型参数
3. 监控API使用量，避免超出配额限制
4. 处理好错误情况，提供良好的用户体验