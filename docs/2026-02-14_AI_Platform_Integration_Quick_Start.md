# AI平台集成快速上手指南

**文档日期**: 2026年2月14日  
**项目**: 云程企航 - AI平台集成项目  

## 概述

本文档提供新集成的AI平台（DeepSeek、通义千问、智谱AI）的快速上手指导，帮助您快速启动和使用新功能。

## 环境准备

### 1. 配置API密钥

确保您的 `.env` 文件包含以下配置：

```env
# 豆包(Doubao) API 配置
DOUBAO_API_KEY=2a376e32-8877-4df8-9865-7eb3e99c9f92
DOUBAO_MODEL_ID=ep-20260212000000-gd5tq
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_TIMEOUT=90

# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-13908093890f46fb82c52a01c8dfc464
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL_ID=deepseek-chat
DEEPSEEK_TIMEOUT=30

# 通义千问(Qwen) API 配置
QWEN_API_KEY=sk-5261a4dfdf964a5c9a6364128cc4c653
QWEN_BASE_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
QWEN_MODEL_ID=qwen-max
QWEN_TIMEOUT=45

# 智谱AI API配置
ZHIPU_API_KEY=504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL_ID=glm-4
ZHIPU_TIMEOUT=45
```

### 2. 后端服务启动

启动后端Flask服务：

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
export FLASK_APP=wechat_backend.app:app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

或者使用Python直接运行：

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python -m flask --app wechat_backend.app:app run --host=0.0.0.0 --port=5000
```

## 前端使用

### 1. 微信开发者工具

1. 打开微信开发者工具
2. 导入项目根目录 `/Users/sgl/PycharmProjects/PythonProject`
3. 编译并预览项目

### 2. 平台选择器页面

新功能可通过以下路径访问：

```
/pages/mvp-platform-selector/mvp-platform-selector
```

在该页面中，您可以：

- 选择不同的AI平台（豆包、DeepSeek、通义千问、智谱AI）
- 输入品牌名称和竞品名称
- 自定义分析问题
- 查看不同平台的分析结果

## API接口说明

### 1. DeepSeek MVP接口

```
POST /api/mvp/deepseek-test
```

请求参数：
```json
{
  "brand_list": ["品牌名称"],
  "customQuestions": ["问题1", "问题2"]
}
```

### 2. 通义千问 MVP接口

```
POST /api/mvp/qwen-test
```

请求参数：
```json
{
  "brand_list": ["品牌名称"],
  "customQuestions": ["问题1", "问题2"]
}
```

### 3. 智谱AI MVP接口

```
POST /api/mvp/zhipu-test
```

请求参数：
```json
{
  "brand_list": ["品牌名称"],
  "customQuestions": ["问题1", "问题2"]
}
```

### 4. 豆包 MVP接口（原有）

```
POST /api/mvp/brand-test
```

## 使用示例

### 1. API调用示例

使用curl测试DeepSeek接口：

```bash
curl -X POST http://localhost:5000/api/mvp/deepseek-test \
  -H "Content-Type: application/json" \
  -d '{
    "brand_list": ["小米"],
    "customQuestions": ["介绍一下小米", "小米的主要产品是什么"]
  }'
```

### 2. 前端页面使用

1. 打开 `/pages/mvp-platform-selector/`
2. 选择想要使用的AI平台
3. 输入品牌名称（如"小米"）
4. 输入竞品名称（可选，如"华为"）
5. 设置自定义问题
6. 点击"开始分析"按钮
7. 查看分析结果

## 故障排除

### 1. API密钥错误

如果收到API密钥错误，请检查：

- `.env` 文件中的API密钥是否正确
- 环境变量是否正确加载
- 重启Flask服务使配置生效

### 2. 接口访问错误

如果无法访问MVP接口，请检查：

- Flask服务是否正常运行
- 接口路径是否正确
- 跨域配置是否正确

### 3. 前端页面错误

如果前端页面无法正常显示，请检查：

- 页面路径是否正确注册
- 服务层文件是否正确引入
- API端点是否可正常访问

## 技术支持

如遇到问题，请参考以下资源：

- 完整报告: `2026-02-14_AI_Platform_Integration_Completion_Report.md`
- 系统架构文档: `2026-02-14_GEO_System_Interface_Audit_Report.md`
- 联系开发团队获取进一步支持

---

**文档版本**: 1.0  
**最后更新**: 2026年2月14日