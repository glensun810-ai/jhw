# API密钥配置说明

## 问题分析

您遇到的"启动任务失败，创建任务失败"错误是由于后端缺少必要的API密钥配置导致的。后端在接收品牌诊断请求时会检查所选AI模型是否已配置API密钥，如果未配置，会返回400错误。

## 解决步骤

### 1. 创建/更新 .env 文件

在项目根目录下创建或更新 `.env` 文件，包含以下内容：

```bash
# AI Platform API Keys
# 请替换为你自己的API密钥
DEEPSEEK_API_KEY="your-deepseek-api-key-here"
QWEN_API_KEY="your-qwen-api-key-here"
DOUBAO_API_KEY="your-doubao-api-key-here"
CHATGPT_API_KEY="your-chatgpt-api-key-here"
GEMINI_API_KEY="your-gemini-api-key-here"
ZHIPU_API_KEY="your-zhipu-api-key-here"

# 微信小程序配置
WECHAT_APP_ID="your-wechat-app-id"
WECHAT_APP_SECRET="your-wechat-app-secret"
WECHAT_TOKEN="your-wechat-token"

# Flask配置
SECRET_KEY="your-secret-key-for-production-here"
```

### 2. 获取API密钥

#### DeepSeek API密钥
1. 访问 [DeepSeek平台](https://platform.deepseek.com/)
2. 注册账号并登录
3. 在API密钥管理页面创建新的API密钥
4. 复制密钥并填入上述配置文件中

#### 豆包(Doubao) API密钥
1. 访问 [豆包开发者平台](https://www.doubao.com/)
2. 注册账号并登录
3. 在API密钥管理页面获取API密钥
4. 复制密钥并填入上述配置文件中

#### 其他平台API密钥
- 通义千问: [阿里云百炼平台](https://bailian.aliyun.com/)
- ChatGPT: [OpenAI平台](https://platform.openai.com/)
- Gemini: [Google AI Studio](https://aistudio.google.com/)
- 智谱AI: [智谱AI平台](https://open.bigmodel.cn/)

### 3. 启动后端服务

确保在设置了环境变量后启动后端服务：

```bash
cd backend_python
python run.py
```

### 4. 前端配置验证

前端会自动从本地存储或环境变量获取服务器地址，确保后端服务在 http://127.0.0.1:5000 上运行。

## 重要注意事项

1. **API密钥安全**: 不要将包含真实API密钥的`.env`文件提交到版本控制系统
2. **重启服务**: 修改环境变量后需要重启后端服务
3. **模型名称映射**: 系统支持多种模型名称变体（如"豆包"、"doubao"、"Doubao"等都会被正确映射）
4. **熔断机制**: 系统内置了熔断机制，如果某个平台持续失败会被暂时禁用

## 故障排除

如果配置后仍然遇到问题：

1. 检查API密钥是否正确复制（不要包含引号）
2. 确认后端服务已重启
3. 查看后端日志文件 `logs/app.log` 获取详细错误信息
4. 确保网络可以访问相应的AI服务提供商