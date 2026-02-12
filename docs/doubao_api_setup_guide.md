# 豆包(Doubao) API 集成完整指南

## 概述
本文档详细介绍如何在GEO内容质量验证器项目中集成字节跳动的豆包(Doubao)API。

## API端点信息
- **基础URL**: `https://ark.cn-beijing.volces.com`
- **API端点**: `/api/v3/chat/completions`
- **完整URL**: `https://ark.cn-beijing.volces.com/api/v3/chat/completions`

## 获取API密钥

### 1. 注册豆包开发者账号
- 访问豆包开发者平台
- 注册并登录账号
- 创建新项目以获取API密钥

### 2. 配置API密钥
在项目根目录的 `.env` 文件中添加：

```bash
# 豆包API配置
DOUBAO_API_KEY=your_actual_doubao_api_key_here
```

## 模型ID获取
豆包使用特定的模型ID格式，通常为 `ep-YYYYMMDD-HASH` 形式。您需要在豆包开发者控制台获取实际的模型ID。

## 配置文件设置

### 环境变量配置
```bash
# 豆包API配置
DOUBAO_API_KEY=your_doubao_api_key_here
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com  # 可选，默认值
DOUBAO_TEMPERATURE=0.7  # 可选，默认为0.7
DOUBAO_MAX_TOKENS=1000  # 可选，默认为1000
DOUBAO_TIMEOUT=30       # 可选，默认为30秒
DOUBAO_RETRY_TIMES=3    # 可选，默认为3次
```

## 适配器实现详解

### DoubaoAdapter 类
位于 `wechat_backend/ai_adapters/doubao_adapter.py`

#### 初始化参数
- `api_key`: 豆包API密钥
- `model_name`: 模型名称 (默认: 'ep-20240520111905-bavcb')
- `base_url`: 基础URL (默认: 'https://ark.cn-beijing.volces.com')

#### 主要方法
- `send_prompt(prompt, **kwargs)`: 发送提示词到豆包API
- `_map_error_message(error_message)`: 错误消息映射

## 请求格式
适配器使用标准的OpenAI兼容格式：

```json
{
  "model": "your-model-id",
  "messages": [
    {
      "role": "user",
      "content": "your prompt here"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

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

### 1. 通过工厂创建适配器
```python
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType

# 创建豆包适配器
adapter = AIAdapterFactory.create(
    AIPlatformType.DOUBAO, 
    api_key=os.getenv('DOUBAO_API_KEY'), 
    model_name='your-actual-model-id'
)

# 发送请求
response = adapter.send_prompt("你好，请简单介绍一下自己。")

if response.success:
    print(f"响应内容: {response.content}")
else:
    print(f"请求失败: {response.error_message}")
```

### 2. 直接使用适配器
```python
from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter

adapter = DoubaoAdapter(
    api_key=os.getenv('DOUBAO_API_KEY'),
    model_name='your-actual-model-id'
)

response = adapter.send_prompt(
    "你好，请简单介绍一下自己。",
    temperature=0.7,
    max_tokens=100
)
```

## 故障排除

### 常见问题

#### 1. 404错误
- 检查API端点是否正确
- 确认模型ID是否有效
- 验证API密钥是否正确配置

#### 2. 401错误 (认证失败)
- 检查API密钥是否正确
- 确认API密钥未过期
- 验证API密钥权限

#### 3. 配额不足
- 检查账户余额
- 申请提高配额限制
- 监控API使用量

### 调试步骤
1. 确认环境变量已正确设置
2. 验证API密钥的有效性
3. 检查网络连接
4. 查看详细错误日志

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

## 测试验证
运行以下命令验证集成：

```bash
python verify_doubao_integration.py
```

## 注意事项
1. 确保API密钥安全存储，不要硬编码在代码中
2. 根据实际需求调整模型参数
3. 监控API使用量，避免超出配额限制
4. 处理好错误情况，提供良好的用户体验
5. 定期更新模型ID以使用最新的模型版本