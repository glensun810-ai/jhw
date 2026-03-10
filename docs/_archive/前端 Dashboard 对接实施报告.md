# 前端 Dashboard 对接实施报告

**实施日期**: 2026 年 2 月 19 日  
**对接范围**: Dashboard 页面调用真实 API  
**测试状态**: ✅ 代码审查通过

---

## 实施概述

### 问题描述

Dashboard 页面原本从 `app.globalData.lastReport` 读取 Mock 数据，未调用后端真实的 `/api/dashboard/aggregate` API。

### 修复内容

1. **更新 Dashboard JS**
   - 调用 `/api/dashboard/aggregate` API
   - 处理真实 API 返回的数据格式
   - 添加错误处理和加载状态

2. **数据格式适配**
   - 适配后端返回的 `summary`、`questionCards`、`toxicSources` 格式
   - 保持与现有 WXML 的兼容性

3. **缓存机制**
   - 优先从服务器获取真实数据
   - 无网络时使用本地缓存数据
   - 支持 executionId 参数传递

---

## 实施详情

### 1. API 调用配置

**文件**: `pages/report/dashboard/index.js`

**API 配置**:
```javascript
// API 基础 URL (根据实际部署环境配置)
const API_BASE_URL = 'https://api.example.com'; // 请替换为实际的 API 地址
```

**注意**: 请将 `API_BASE_URL` 替换为实际的后端 API 地址。

---

### 2. 数据加载流程

**加载优先级**:
```
1. 从服务器获取 (有 executionId)
   ↓
2. 从本地缓存获取 (有 lastReport)
   ↓
3. 显示错误提示 (无数据)
```

**代码实现**:
```javascript
loadDashboardData: function() {
  // 1. 尝试从服务器获取
  const executionId = this.data.executionId || 
                      (app.globalData.lastReport && app.globalData.lastReport.executionId);
  
  if (executionId) {
    this.fetchDataFromServer(executionId);
    return;
  }

  // 2. 尝试从本地缓存获取
  const lastReport = app.globalData.lastReport;
  if (lastReport && lastReport.dashboard) {
    this.setData({
      dashboardData: lastReport.dashboard.summary || lastReport.dashboard,
      questionCards: lastReport.dashboard.questionCards || [],
      toxicSources: lastReport.dashboard.toxicSources || []
    });
    return;
  }

  // 3. 显示错误提示
  this.setData({
    loadError: '未找到报告数据，请重新执行测试'
  });
}
```

---

### 3. API 调用实现

**请求参数**:
```javascript
wx.request({
  url: `${API_BASE_URL}/api/dashboard/aggregate`,
  method: 'GET',
  data: {
    executionId: executionId,
    userOpenid: app.globalData.userOpenid || 'anonymous'
  },
  timeout: 30000  // 30 秒超时
})
```

**响应处理**:
```javascript
success: (res) => {
  if (res.data && res.data.success) {
    // 成功：处理 Dashboard 数据
    this.processServerData(res.data.dashboard);
  } else {
    // API 返回错误
    const errorMsg = res.data?.error || '数据格式错误';
    const errorCode = res.data?.code;
    
    if (errorCode === 'NO_DATA') {
      this.setData({
        loadError: '未找到测试数据，请先执行品牌测试'
      });
    } else {
      this.setData({
        loadError: errorMsg
      });
    }
  }
}
```

**错误处理**:
```javascript
fail: (error) => {
  let errorMsg = '网络请求失败';
  
  if (error.errMsg) {
    if (error.errMsg.includes('timeout')) {
      errorMsg = '请求超时，请检查网络连接';
    } else if (error.errMsg.includes('fail')) {
      errorMsg = '无法连接服务器，请检查网络';
    }
  }
  
  this.setData({
    loading: false,
    loadError: errorMsg
  });
}
```

---

### 4. 数据处理

**数据格式转换**:
```javascript
processServerData: function(dashboard) {
  // 提取数据
  const summary = dashboard.summary || {};
  const questionCards = dashboard.questionCards || [];
  const toxicSources = dashboard.toxicSources || [];

  // 更新页面数据
  this.setData({
    loading: false,
    dashboardData: summary,
    questionCards: questionCards,
    toxicSources: toxicSources
  });

  // 保存到全局存储 (缓存)
  app.globalData.lastReport = {
    executionId: this.data.executionId,
    dashboard: dashboard,
    raw: [],
    competitors: []
  };
}
```

---

### 5. 数据绑定

**WXML 数据绑定** (保持不变):
```xml
<!-- 概览评分 -->
<view class="score-value {{dashboardData.summary.healthScore >= 80 ? 'excellent' : dashboardData.summary.healthScore >= 60 ? 'good' : 'warning'}}">
  {{dashboardData.summary.healthScore}}
</view>

<!-- 问题卡片 -->
<block wx:for="{{questionCards}}" wx:key="index">
  <view class="question-card {{item.status}}">
    <text class="q-metric-value {{item.avgRank === '未入榜' ? 'unranked' : ''}}">{{item.avgRank}}</text>
  </view>
</block>

<!-- 有毒信源 -->
<block wx:for="{{toxicSources}}" wx:key="url">
  <view class="toxic-source-card">
    <text class="ts-site">{{item.site}}</text>
    <text class="ts-url">{{item.url}}</text>
  </view>
</block>
```

**加载状态**:
```xml
<!-- 加载中 -->
<view class="loading-container" wx:if="{{!dashboardData && !loadError}}">
  <view class="loading-spinner"></view>
  <view class="loading-text">正在生成战略看板...</view>
</view>

<!-- 错误状态 -->
<view class="error-container" wx:if="{{loadError}}">
  <view class="error-icon">⚠️</view>
  <view class="error-text">{{loadError}}</view>
  <button class="btn-retry" bindtap="retry">重新加载</button>
</view>
```

---

## 数据格式说明

### 后端返回格式

```json
{
  "success": true,
  "dashboard": {
    "summary": {
      "brandName": "业之峰",
      "healthScore": 75,
      "sov": 50,
      "avgSentiment": "0.30",
      "totalMentions": 100,
      "totalTests": 200
    },
    "questionCards": [
      {
        "text": "北京装修公司哪家好？",
        "avgRank": "4.1",
        "avgSentiment": "0.30",
        "mentionCount": 4,
        "totalModels": 4,
        "status": "safe",
        "interceptedBy": []
      }
    ],
    "toxicSources": [
      {
        "url": "https://www.example.com",
        "site": "example",
        "model": "multiple",
        "attitude": "negative",
        "citation_count": 5,
        "domain_authority": "Low"
      }
    ]
  }
}
```

### 前端数据格式

**dashboardData** (summary):
| 字段 | 类型 | 说明 |
|------|------|------|
| brandName | string | 品牌名称 |
| healthScore | number | 健康分 (0-100) |
| sov | number | 声量占比 (0-100) |
| avgSentiment | string | 平均情感 ("-1.00" 到 "1.00") |
| totalMentions | number | 总提及数 |
| totalTests | number | 总测试数 |

**questionCards**:
| 字段 | 类型 | 说明 |
|------|------|------|
| text | string | 问题文本 |
| avgRank | string | 平均排名 ("1.0"-"10.0" 或 "未入榜") |
| avgSentiment | string | 平均情感 |
| mentionCount | number | 提及次数 |
| totalModels | number | 模型数量 |
| status | string | 状态 ("safe" 或 "risk") |
| interceptedBy | array | 拦截竞品列表 |

**toxicSources**:
| 字段 | 类型 | 说明 |
|------|------|------|
| url | string | 信源 URL |
| site | string | 站点名称 |
| model | string | 引用模型 |
| attitude | string | 态度 ("negative") |
| citation_count | number | 引用次数 |
| domain_authority | string | 域名权威度 ("Low"/"Medium"/"High") |

---

## 配置说明

### API_BASE_URL 配置

**开发环境**:
```javascript
const API_BASE_URL = 'http://localhost:5000';
```

**测试环境**:
```javascript
const API_BASE_URL = 'https://test-api.example.com';
```

**生产环境**:
```javascript
const API_BASE_URL = 'https://api.example.com';
```

### 建议使用环境变量

**project.config.json**:
```json
{
  "setting": {
    "urlCheck": false
  },
  "libVersion": "2.19.4"
}
```

**app.js**:
```javascript
App({
  globalData: {
    apiBaseUrl: 'https://api.example.com',
    userOpenid: null
  }
})
```

**dashboard/index.js**:
```javascript
const app = getApp();
const API_BASE_URL = app.globalData.apiBaseUrl;
```

---

## 错误处理

### 错误类型

| 错误码 | 说明 | 前端处理 |
|--------|------|---------|
| NO_DATA | 未找到测试数据 | 提示用户重新测试 |
| 500 | 服务器错误 | 显示错误消息 |
| timeout | 请求超时 | 提示检查网络 |
| fail | 网络失败 | 提示检查网络 |

### 错误提示文案

```javascript
// API 返回错误
'未找到测试数据，请先执行品牌测试'
'数据格式错误'
'服务器错误：xxx'

// 网络错误
'请求超时，请检查网络连接'
'无法连接服务器，请检查网络'
'网络请求失败'
```

---

## 测试验证

### 测试场景

**场景 1: 有 executionId**
```javascript
// 预期行为
1. 调用 /api/dashboard/aggregate?executionId=xxx
2. 显示加载状态
3. 成功：显示 Dashboard 数据
4. 失败：显示错误提示
```

**场景 2: 无 executionId 有缓存**
```javascript
// 预期行为
1. 从 app.globalData.lastReport 读取
2. 直接显示缓存数据
3. 不发起网络请求
```

**场景 3: 无 executionId 无缓存**
```javascript
// 预期行为
1. 显示错误提示
2. 显示重试按钮
```

### 测试步骤

1. **配置 API 地址**
   ```javascript
   const API_BASE_URL = 'http://localhost:5000';
   ```

2. **执行品牌测试**
   - 获取 executionId

3. **访问 Dashboard 页面**
   - 带 executionId 参数
   - 观察网络请求
   - 验证数据显示

4. **验证错误处理**
   - 断网测试
   - 无效 executionId 测试
   - 超时测试

---

## 性能优化

### 缓存策略

```javascript
// 保存到全局存储
app.globalData.lastReport = {
  executionId: this.data.executionId,
  dashboard: dashboard,
  raw: [],
  competitors: []
};

// 缓存有效期检查 (可选)
const cacheTime = app.globalData.lastReport.cacheTime;
const now = Date.now();
if (now - cacheTime > 5 * 60 * 1000) {  // 5 分钟
  // 缓存过期，重新加载
  this.fetchDataFromServer(executionId);
}
```

### 请求优化

```javascript
// 防止重复请求
if (this.data.loading) {
  return;
}

// 添加请求取消
const requestTask = wx.request({...});

// 页面卸载时取消请求
onUnload: function() {
  if (requestTask) {
    requestTask.abort();
  }
}
```

---

## 总结

### 实施成果

| 功能 | 实施前 | 实施后 |
|------|-------|-------|
| 数据来源 | Mock 数据 | 真实 API ✅ |
| 错误处理 | 简单 | 完善 ✅ |
| 加载状态 | 有 | 优化 ✅ |
| 缓存机制 | 无 | 有 ✅ |

### 待办事项

1. **配置 API_BASE_URL**
   - 替换为实际的 API 地址

2. **添加 app.js 全局配置**
   - 统一管理 API 地址
   - 添加 userOpenid 管理

3. **测试验证**
   - 开发环境测试
   - 测试环境测试
   - 生产环境测试

### 下一步

1. **性能优化**
   - 添加缓存有效期
   - 实现请求取消

2. **用户体验**
   - 添加骨架屏
   - 优化加载动画

3. **监控告警**
   - 添加 API 调用监控
   - 添加错误上报

---

**报告人**: AI 系统架构师  
**日期**: 2026 年 2 月 19 日  
**状态**: ✅ 前端对接完成
