# AI适配器配置指南

## 问题说明

从日志可以看到，当前只有 `deepseekr1` 适配器成功注册，而其他常用的AI平台（如豆包、通义千问、智谱AI等）没有注册或缺少API密钥配置。这导致当用户选择这些平台时，API返回400错误。

## 当前已注册的AI平台

根据日志输出：
- ✅ DeepSeek R1 - 已注册（需要在`.env`文件中配置`DEEPSEEK_API_KEY`）

## 未注册或缺少API密钥的平台

- ❌ 豆包 (Doubao) - 需要配置`DOUBAO_API_KEY`
- ❌ 通义千问 (Qwen) - 需要配置`QWEN_API_KEY`
- ❌ 智谱AI (Zhipu) - 需要配置`ZHIPU_API_KEY`
- ❌ ChatGPT - 需要配置`CHATGPT_API_KEY`
- ❌ 文心一言 (Wenxin) - 需要配置`ERNIE_API_KEY`

## 解决方案

### 1. 配置API密钥

1. 在项目根目录复制 `.env.example` 为 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入相应的API密钥：
   ```bash
   DEEPSEEK_API_KEY="your-deepseek-api-key-here"
   QWEN_API_KEY="your-qwen-api-key-here"
   DOUBAO_API_KEY="your-doubao-api-key-here"
   CHATGPT_API_KEY="your-chatgpt-api-key-here"
   ZHIPU_API_KEY="your-zhipu-api-key-here"
   ```

### 2. 验证配置

配置API密钥后重启后端服务，适配器预热日志应该显示更多平台已成功注册。

### 3. 前端模型选择建议

在API密钥配置完成前，建议在前端只选择已成功注册的AI模型（目前是DeepSeek相关模型），以避免400错误。

## 测试可用的AI模型

当前环境下，您可以尝试在前端选择以下模型之一：
- DeepSeek（如果已配置API密钥）
- DeepSeek R1（如果已配置API密钥）

## 故障排除

如果配置API密钥后仍遇到问题：

1. 确保`.env`文件位于正确的目录中
2. 检查API密钥是否正确无误
3. 重启后端服务以加载新的环境变量
4. 检查适配器导入错误（某些适配器可能存在导入问题）

## 注意事项

- API密钥不应提交到版本控制系统，请确保`.env`文件在`.gitignore`中
- 部署时需要在服务器上设置相应的环境变量
- 某些AI平台可能需要特殊的网络配置或代理设置