# 微信小程序架构重构指南

本文档介绍了项目重构后的架构分层和开发规范，所有新功能开发必须遵循此架构。

## 架构分层

### 1. API 层 (`/api/`)
- **职责**: 定义与后端服务的接口
- **位置**: `/miniprogram/api/`
- **规范**:
  - 所有网络请求必须通过 API 层
  - 使用统一的 request 底座
  - 函数命名规范: `[动作][对象]Api` (如 `getUserInfoApi`, `postMessageApi`)
  - 必须添加 JSDoc 注释说明参数和返回值

### 2. Service 层 (`/services/`)
- **职责**: 处理业务逻辑和数据加工
- **位置**: `/miniprogram/services/`
- **规范**:
  - 复杂的数据处理逻辑必须提取到 Service 层
  - 不包含 UI 相关代码
  - 提供纯业务逻辑函数

### 3. Utils 层 (`/utils/`)
- **职责**: 提供通用工具函数和底层服务
- **位置**: `/miniprogram/utils/`
- **规范**:
  - `request.js`: 统一请求工具，包含拦截器、错误处理等
  - `config.js`: 统一配置管理，包含 API 端点、环境配置等
  - 其他工具函数应为纯函数

### 4. Pages 层 (`/pages/`)
- **职责**: UI 逻辑和页面生命周期管理
- **位置**: `/miniprogram/pages/`
- **规范**:
  - 只负责调用 Service -> 拿到结果 -> setData
  - 不包含复杂的数据处理逻辑
  - 不直接调用 wx.request

## 开发新功能的标准步骤

### 1. API 层开发
```javascript
// /miniprogram/api/newFeature.js
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
// /miniprogram/services/newFeatureService.js
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
// /miniprogram/pages/new-feature/new-feature.js
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

## 错误处理

- 所有请求自动携带 Token（从本地存储获取）
- 401 错误自动清理缓存并跳转登录页
- 可通过 `showError: false` 选项禁用自动错误提示

## 注意事项

1. 任何新的网络请求都必须通过 API 层，禁止在页面中直接使用 `wx.request`
2. 复杂的数据处理逻辑必须提取到 Service 层
3. 保持函数签名不变，确保向后兼容
4. 所有 API 函数必须有适当的 JSDoc 注释