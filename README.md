# 微信小程序AI品牌战略诊断系统

本项目是一个集成了多个AI大模型平台的微信小程序，提供品牌认知度和市场竞争力分析功能。

## 项目概述

### 功能背景
在数字化营销时代，品牌认知度和市场竞争力分析对于企业制定有效的品牌战略至关重要。传统的品牌分析方法往往耗时费力且难以全面覆盖多维度评价指标。本项目利用先进的AI大模型技术，为用户提供快速、全面、智能化的品牌战略诊断服务。

### 核心功能
- **AI品牌战略诊断**: 使用多个AI平台对品牌进行全面分析
- **多平台支持**: 集成豆包、通义千问、ChatGPT、Gemini、智谱AI、DeepSeek等多个AI平台
- **实时分析**: 提供品牌认知度、权威性、可见度、情感倾向等多维度分析
- **对比分析**: 支持多品牌对比和竞品分析
- **智能评估**: 基于AI模型对品牌进行综合评分和等级评定
- **可视化报告**: 生成直观的品牌分析报告和图表展示

### 效果与价值
- **高效性**: 传统品牌分析需要数天甚至数周，AI分析只需几分钟即可完成
- **全面性**: 多维度评估品牌在市场上的表现，涵盖认知度、权威性、可见度等指标
- **准确性**: 利用多个AI平台的结果进行交叉验证，提高分析准确性
- **成本效益**: 降低品牌分析的人力和时间成本
- **实时性**: 可随时对品牌进行重新评估，跟踪品牌表现变化
- **可扩展性**: 支持接入更多AI平台，持续提升分析能力

### 技术架构

#### 1. 前端架构 (`/pages/`, `/components/`, `/api/`, `/utils/`)
- **Pages 层**: UI逻辑和页面生命周期管理
  - 位置: `/pages/`
  - 职责: 负责UI渲染和用户交互
- **Components 层**: 可复用UI组件
  - 位置: `/components/`
  - 职责: 提供可复用的界面组件
- **API 层**: 与后端服务的接口定义
  - 位置: `/api/`
  - 职责: 定义网络请求接口
  - 规范: 所有网络请求必须通过API层，函数命名规范为`[动作][对象]Api`
- **Utils 层**: 通用工具函数和配置
  - 位置: `/utils/`
  - 职责: 提供通用工具函数和配置管理
  - 包含: `request.js` (统一请求工具), `config.js` (配置管理)

#### 2. 后端架构 (`/backend_python/`)
- **API 层**: Flask RESTful API服务
  - 位置: `/backend_python/wechat_backend/views.py`
  - 职责: 处理HTTP请求，提供RESTful API
- **Service 层**: 业务逻辑处理
  - 位置: `/backend_python/wechat_backend/services/`
  - 职责: 实现核心业务逻辑
- **AI Adapters 层**: AI平台适配器
  - 位置: `/backend_python/wechat_backend/ai_adapters/`
  - 职责: 适配不同AI平台的API接口
- **Config 层**: 配置管理
  - 位置: `/backend_python/config.py`
  - 职责: 管理API密钥和系统配置

### 支持的AI平台
- **豆包 (Doubao)**: 字节跳动推出的AI助手
- **通义千问 (Qwen)**: 阿里巴巴大模型
- **ChatGPT**: OpenAI的GPT系列模型
- **Gemini**: Google的AI模型
- **智谱AI (Zhipu)**: 智谱AI大模型
- **DeepSeek**: DeepSeek大模型

## 架构分层

### 1. API 层 (`/api/`)
- **职责**: 定义与后端服务的接口
- **位置**: `/api/`
- **规范**:
  - 所有网络请求必须通过 API 层
  - 使用统一的 request 底座
  - 函数命名规范: `[动作][对象]Api` (如 `getUserInfoApi`, `postMessageApi`)
  - 必须添加 JSDoc 注释说明参数和返回值

### 2. Service 层 (`/services/`)
- **职责**: 处理业务逻辑和数据加工
- **位置**: `/services/`
- **规范**:
  - 复杂的数据处理逻辑必须提取到 Service 层
  - 不包含 UI 相关代码
  - 提供纯业务逻辑函数

### 3. Utils 层 (`/utils/`)
- **职责**: 提供通用工具函数和底层服务
- **位置**: `/utils/`
- **规范**:
  - `request.js`: 统一请求工具，包含拦截器、错误处理等
  - `config.js`: 统一配置管理，包含 API 端点、环境配置等
  - 其他工具函数应为纯函数

### 4. Pages 层 (`/pages/`)
- **职责**: UI 逻辑和页面生命周期管理
- **位置**: `/pages/`
- **规范**:
  - 只负责调用 Service -> 拿到结果 -> setData
  - 不包含复杂的数据处理逻辑
  - 不直接调用 wx.request

## 开发新功能的标准步骤

### 1. API 层开发
```javascript
// /api/newFeature.js
const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 获取新功能数据
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
const getNewFeatureData = (params) => {
  return get(API_ENDPOINTS.NEW_FEATURE.LIST, params);
};

module.exports = {
  getNewFeatureData
};
```

### 2. Service 层开发（如需要）
```javascript
// /services/newFeatureService.js
/**
 * 处理新功能数据
 * @param {Object} rawData - 原始数据
 * @returns {Object} 处理后的数据
 */
const processNewFeatureData = (rawData) => {
  // 数据处理逻辑
  return processedData;
};

module.exports = {
  processNewFeatureData
};
```

### 3. 页面层开发
```javascript
// /pages/new-feature/new-feature.js
const { getNewFeatureData } = require('../../api/newFeature.js');
const { processNewFeatureData } = require('../../services/newFeatureService.js');

Page({
  async onLoad() {
    try {
      const rawData = await getNewFeatureData({ /* params */ });
      const processedData = processNewFeatureData(rawData);
      this.setData({ data: processedData });
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  }
});
```

## 环境配置

项目支持多环境配置，通过 `wx.getAccountInfoSync().miniProgram.envVersion` 自动识别：

- `develop`: 开发环境
- `trial`: 体验环境  
- `release`: 生产环境

后端服务通过 `.env` 文件管理环境变量，包括各AI平台的API密钥。

## AI平台配置

### 配置文件
- **`.env`**: 存储各AI平台的API密钥
- **`config.py`**: 后端配置管理
- **`wechat_backend/ai_adapters/factory.py`**: AI平台适配器工厂

### 支持的平台配置
- **DEEPSEEK_API_KEY**: DeepSeek平台API密钥
- **QWEN_API_KEY**: 通义千问API密钥
- **DOUBAO_API_KEY**: 豆包API密钥
- **CHATGPT_API_KEY**: ChatGPT API密钥
- **GEMINI_API_KEY**: Gemini API密钥
- **ZHIPU_API_KEY**: 智谱AI API密钥

## 错误处理

- 所有请求自动携带 Token（从本地存储获取）
- 401 错误自动清理缓存并跳转登录页
- 可通过 `showError: false` 选项禁用自动错误提示
- AI平台调用失败时提供降级方案

## 部署说明

### 后端部署
1. 安装依赖: `pip install -r requirements.txt`
2. 配置环境变量: 复制 `.env.example` 为 `.env` 并填入API密钥
3. 启动服务: `python run.py`

### 前端部署
1. 使用微信开发者工具打开项目
2. 上传代码至微信小程序平台

## 注意事项

1. 任何新的网络请求都必须通过 API 层，禁止在页面中直接使用 `wx.request`
2. 复杂的数据处理逻辑必须提取到 Service 层
3. 保持函数签名不变，确保向后兼容
4. 所有 API 函数必须有适当的 JSDoc 注释
5. AI平台调用需注意API调用频率限制
6. 敏感信息如API密钥不得硬编码在前端代码中