# 前端诊断报告 API 修复报告

**创建日期**: 2026-03-13  
**版本**: 1.0  
**问题**: `diagnosisService.getFullReport is not a function`

---

## 问题描述

在报告页面 (`report-v2.js`) 加载时，出现以下错误：

```
[ReportPageV2] ❌ API 加载失败：TypeError: 
_diagnosisService.default.getFullReport is not a function
```

**原因**: `diagnosisService.js` 中缺少 `getFullReport()` 方法

---

## 解决方案

### 1. 添加缺失的 API 方法

**文件**: `miniprogram/services/diagnosisService.js`

**新增方法**:

#### 1.1 `getFullReport(executionId)` - 获取完整报告

```javascript
async getFullReport(executionId) {
  const res = await wx.cloud.callFunction({
    name: 'getDiagnosisReport',
    data: { executionId: executionId }
  });
  
  const result = res.result;
  
  // 处理云函数返回格式：{ success: true, data: report }
  let report;
  if (result.success && result.data) {
    report = result.data;
  } else if (result.report) {
    report = result;
  } else {
    report = result;
  }
  
  return this._normalizeReport(report);
}
```

**功能**:
- 调用 `getDiagnosisReport` 云函数
- 处理云函数返回的不同格式
- 标准化报告数据（snake_case 转 camelCase）
- 错误处理和抛出

#### 1.2 `getHistoryReport(executionId)` - 获取历史报告

```javascript
async getHistoryReport(executionId) {
  const res = await wx.cloud.callFunction({
    name: 'getDiagnosisReport',
    data: { 
      executionId: executionId,
      isHistory: true 
    }
  });
  
  // 处理返回结果（与 getFullReport 相同）
  ...
}
```

**功能**:
- 调用 `getDiagnosisReport` 云函数，传入 `isHistory: true`
- 云函数根据参数调用不同的后端 API 端点
- 其他处理与 `getFullReport` 相同

#### 1.3 `_normalizeReport(report)` - 标准化报告格式

```javascript
_normalizeReport(report) {
  // 如果已经是 camelCase，直接返回
  if (report.brandDistribution && report.sentimentDistribution) {
    return report;
  }

  // 将 snake_case 转换为 camelCase
  const normalized = {};
  for (const key in report) {
    if (report.hasOwnProperty(key)) {
      const camelKey = this._toCamelCase(key);
      normalized[camelKey] = report[key];
    }
  }
  return normalized;
}
```

**功能**:
- 检查报告是否已经是 camelCase 格式
- 将 snake_case 字段名转换为 camelCase
- 确保返回数据格式一致

#### 1.4 `_toCamelCase(str)` - 字符串转换工具

```javascript
_toCamelCase(str) {
  return str.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
}
```

---

### 2. 更新云函数

**文件**: `miniprogram/cloudfunctions/getDiagnosisReport/index.js`

**更新内容**:

#### 2.1 支持历史报告查询

```javascript
exports.main = async (event, context) => {
  const { executionId, isHistory } = event;
  
  // 根据 isHistory 参数选择不同 API 端点
  let apiUrl;
  if (isHistory) {
    apiUrl = `${API_BASE_URL}/api/diagnosis/report/${executionId}/history`;
  } else {
    apiUrl = `${API_BASE_URL}/api/diagnosis/report/${executionId}`;
  }
  
  const response = await axios.get(apiUrl, {...});
  return { success: true, data: response.data };
};
```

**改进**:
- 支持 `isHistory` 参数
- 根据参数调用不同的后端 API
  - 普通报告：`/api/diagnosis/report/{executionId}`
  - 历史报告：`/api/diagnosis/report/{executionId}/history`

---

## API 端点说明

### 后端 API

| 端点 | 方法 | 用途 | 返回格式 |
|------|------|------|----------|
| `/api/diagnosis/report/{executionId}` | GET | 获取完整诊断报告 | `{ report, results, brandDistribution, ... }` |
| `/api/diagnosis/report/{executionId}/history` | GET | 获取历史诊断报告 | `{ report, results, brandDistribution, ... }` |

### 云函数

| 名称 | 输入参数 | 返回格式 |
|------|----------|----------|
| `getDiagnosisReport` | `{ executionId, isHistory? }` | `{ success: boolean, data: Object }` |

---

## 数据格式转换

### 后端返回 (snake_case)

```json
{
  "brand_distribution": {
    "data": { "品牌 A": 10, "品牌 B": 5 },
    "total_count": 15
  },
  "sentiment_distribution": {
    "data": { "positive": 8, "neutral": 5, "negative": 2 }
  },
  "detailed_results": [...]
}
```

### 前端期望 (camelCase)

```json
{
  "brandDistribution": {
    "data": { "品牌 A": 10, "品牌 B": 5 },
    "total_count": 15
  },
  "sentimentDistribution": {
    "data": { "positive": 8, "neutral": 5, "negative": 2 }
  },
  "detailedResults": [...]
}
```

### 转换逻辑

```javascript
// diagnosisService._toCamelCase()
"brand_distribution" -> "brandDistribution"
"sentiment_distribution" -> "sentimentDistribution"
"detailed_results" -> "detailedResults"
```

---

## 使用示例

### 在报告页面中使用

```javascript
// pages/report-v2/report-v2.js

import diagnosisService from '../../services/diagnosisService';

Page({
  async onLoad(options) {
    const executionId = options.executionId;
    
    try {
      // 从 API 加载完整报告
      const report = await diagnosisService.getFullReport(executionId);
      
      // 设置页面数据
      this.setData({
        brandDistribution: report.brandDistribution,
        sentimentDistribution: report.sentimentDistribution,
        keywords: report.keywords,
        brandScores: report.brandScores
      });
      
    } catch (error) {
      console.error('加载报告失败:', error);
      this._handleLoadError(error);
    }
  }
});
```

### 获取历史报告

```javascript
// 从历史页面加载报告
const report = await diagnosisService.getHistoryReport(executionId);

// 使用返回的报告数据
console.log('历史报告:', report);
```

---

## 错误处理

### 云函数错误

```javascript
// getDiagnosisReport/index.js

if (error.code === 'ECONNREFUSED') {
  return createEmptyReport('后端服务不可连接', 'server_error', executionId);
} else if (error.code === 'ETIMEDOUT') {
  return createEmptyReport('请求超时，请稍后重试', 'timeout', executionId);
} else if (error.response?.status === 404) {
  return createEmptyReport('报告不存在或尚未生成', 'not_found', executionId);
}
```

### 前端错误处理

```javascript
// diagnosisService.js

try {
  const report = await this.getFullReport(executionId);
  return report;
} catch (error) {
  console.error('Failed to get full report:', error);
  throw error;  // 向上抛出，由调用方处理
}

// report-v2.js
try {
  await this._loadFromAPI(executionId);
} catch (error) {
  this._handleLoadError(error);  // 显示错误提示
}
```

---

## 测试验证

### 1. 单元测试

```javascript
// test/diagnosisService.test.js

test('getFullReport should fetch report from cloud function', async () => {
  const mockReport = {
    brandDistribution: { data: { '品牌 A': 10 } },
    sentimentDistribution: { data: { positive: 5 } }
  };
  
  wx.cloud.callFunction.mockResolvedValue({
    result: { success: true, data: mockReport }
  });
  
  const service = require('../services/diagnosisService');
  const report = await service.getFullReport('test-execution-id');
  
  expect(report.brandDistribution).toEqual(mockReport.brandDistribution);
});
```

### 2. 集成测试

1. 创建测试诊断任务
2. 等待诊断完成
3. 调用 `getFullReport(executionId)`
4. 验证返回数据包含：
   - `brandDistribution`
   - `sentimentDistribution`
   - `keywords`
   - `results` / `detailedResults`

---

## 兼容性说明

### 向后兼容

- ✅ 支持旧的返回格式（直接返回 result）
- ✅ 支持新的返回格式（`{ success: true, data: report }`）
- ✅ 支持 snake_case 和 camelCase 混合格式
- ✅ 自动转换字段命名风格

### 云函数部署

**注意**: 云函数需要重新部署才能生效

```bash
# 在微信开发者工具中
1. 右键点击 cloudfunctions/getDiagnosisReport
2. 选择"上传并部署：云端安装依赖"
3. 等待部署完成
```

---

## 性能优化

### 1. 缓存策略

```javascript
// 可以在 diagnosisService 中添加缓存
const reportCache = new Map();

async getFullReport(executionId) {
  // 检查缓存
  if (reportCache.has(executionId)) {
    return reportCache.get(executionId);
  }
  
  const report = await this._fetchReport(executionId);
  reportCache.set(executionId, report);
  return report;
}
```

### 2. 请求去重

```javascript
// 防止重复请求同一个报告
const pendingRequests = new Map();

async getFullReport(executionId) {
  if (pendingRequests.has(executionId)) {
    return pendingRequests.get(executionId);
  }
  
  const promise = this._fetchReport(executionId);
  pendingRequests.set(executionId, promise);
  
  try {
    const report = await promise;
    return report;
  } finally {
    pendingRequests.delete(executionId);
  }
}
```

---

## 总结

### 修复内容

1. ✅ 添加 `getFullReport()` 方法
2. ✅ 添加 `getHistoryReport()` 方法
3. ✅ 添加 `_normalizeReport()` 工具方法
4. ✅ 添加 `_toCamelCase()` 字符串转换
5. ✅ 更新云函数支持历史报告查询

### 影响范围

- **前端文件**: `miniprogram/services/diagnosisService.js`
- **云函数**: `miniprogram/cloudfunctions/getDiagnosisReport/index.js`
- **使用页面**: `pages/report-v2/report-v2.js`, `pages/history/history.js`

### 部署步骤

1. 保存修改的文件
2. 在微信开发者工具中上传云函数
3. 编译小程序
4. 测试报告加载功能

---

**文档版本**: 1.0  
**最后更新**: 2026-03-13  
**维护者**: 首席全栈工程师
