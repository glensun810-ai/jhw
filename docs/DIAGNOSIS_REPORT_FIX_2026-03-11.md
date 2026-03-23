# 诊断报告详情页空数据问题修复报告

## 修复日期
2026-03-11

## 问题描述
诊断任务完成后，报告详情页（report-v2）显示空数据，尽管后端已返回完整的诊断结果。

### 问题现象
- ✅ 诊断任务成功完成（`status: completed, progress: 100%`）
- ✅ 后端返回了 `brandScores` 数据
- ❌ 报告页显示 `[generateDashboardData] ⚠️ 没有可用的原始结果数据`
- ❌ 图表组件收到空数据：`BrandDistribution: {}`, `SentimentChart: {}`, `KeywordCloud: count: 0`

---

## 根本原因分析

### 1. 多个轮询实例并存（P0 关键问题）
**问题位置**: `services/brandTestService.js` + `miniprogram/services/diagnosisService.js`

**原因**: 
- WebSocket 错误回调 `onError` 和 `onFallback` 被多次触发
- 每次触发都创建新的轮询实例
- 单例模式被绕过（`pollingInstance = null` 被过早清除）

**日志证据**:
```
[轮询响应] 第 6 次，耗时：44ms, 状态：report_aggregating, 进度：90%
[轮询响应] 第 10 次，耗时：41ms, 状态：report_aggregating, 进度：90%
[轮询响应] 第 13 次，耗时：44ms, 状态：report_aggregating, 进度：90%
```

### 2. 数据流断裂（P0 关键问题）
**问题位置**: `pages/index/index.js` + `services/brandTestService.js`

**原因**:
- 后端 `/test/status/{id}?fields=full` 返回的数据**不包含** `detailed_results` 数组
- `generateDashboardData` 期望接收 `detailed_results` 数组
- 数据格式不匹配导致返回空数据

### 3. 报告页数据加载策略单一（P1 问题）
**问题位置**: `miniprogram/pages/report-v2/report-v2.js`

**原因**:
- 报告页仅依赖云函数 `getFullReport()` 获取数据
- 当云函数返回空数据时，没有 fallback 方案
- 没有利用诊断完成时已处理的数据

---

## 修复方案

### 修复 1: 防止轮询重复启动
**文件**: `services/brandTestService.js` (行 278-314)

```javascript
onError: (error) => {
  // 【P0 关键修复 - 2026-03-11】检查轮询是否已在运行，防止重复启动
  if (pollingInstance && pollingInstance.isActive) {
    console.warn('[onError] ⚠️ 轮询已在运行中，跳过重复启动');
    return;
  }
  // ...
},

onFallback: () => {
  // 【P0 关键修复 - 2026-03-11】检查轮询是否已在运行，防止重复启动
  if (pollingInstance && pollingInstance.isActive) {
    console.warn('[onFallback] ⚠️ 轮询已在运行中，跳过重复启动');
    return;
  }
  // ...
}
```

**文件**: `miniprogram/services/diagnosisService.js` (行 156-246)

```javascript
_connectWebSocket(executionId, callbacks) {
  // 【P0 关键修复 - 2026-03-11】添加轮询启动标志，防止重复启动
  this.isPollingStarted = false;
  
  // ...
  onError: (error) => {
    if (this.isPollingStarted) {
      console.warn('[onError] ⚠️ 轮询已启动，跳过重复降级');
      return;
    }
  },
  
  onFallback: () => {
    if (this.isPollingStarted) {
      console.warn('[onFallback] ⚠️ 轮询已启动，跳过重复降级');
      return;
    }
  }
}

_startPolling(executionId, callbacks) {
  // 【P0 关键修复 - 2026-03-11】设置轮询启动标志，防止重复降级
  this.isPollingStarted = true;
  // ...
}
```

---

### 修复 2: 报告页多数据源加载策略
**文件**: `miniprogram/pages/report-v2/report-v2.js` (行 598-720)

```javascript
async loadReportData(executionId, reportId) {
  // 【P0 关键修复 - 2026-03-11】多数据源加载策略
  // 1. 优先从全局变量获取（诊断完成时传递）
  // 2. 其次从云函数获取完整报告
  // 3. 最后从 Storage 读取备份数据

  // Step 1: 检查全局变量
  const app = getApp();
  if (app && app.globalData && app.globalData.pendingReport) {
    if (pendingReport.executionId === id) {
      report = { /* 从全局变量获取 */ };
      dataSource = 'globalData';
    }
  }

  // Step 2: 从云函数获取
  if (!report || !report.brandDistribution) {
    const cloudReport = await reportService.getFullReport(id);
    if (cloudReport.brandDistribution) {
      report = { /* 从云函数获取 */ };
      dataSource = 'cloudFunction';
    }
  }

  // Step 3: 从 Storage 读取备份
  if (!report || !report.brandDistribution) {
    const storageData = wx.getStorageSync('last_diagnostic_results');
    if (storageData) {
      report = { /* 从 Storage 获取 */ };
      dataSource = 'storage';
    }
  }
}
```

---

### 修复 3: 诊断完成时传递数据到报告页
**文件**: `pages/index/index.js` (行 1779-1878)

```javascript
handleDiagnosisComplete(parsedStatus, executionId) {
  // 【P0 关键修复 - 2026-03-11】先处理数据，再跳转，确保报告页有数据可用
  let dashboardData = null;
  let processedReportData = null;

  try {
    const rawResults = parsedStatus.detailed_results || parsedStatus.results || [];
    
    if (rawResults && rawResults.length > 0) {
      dashboardData = generateDashboardData(rawResults, {...});
      processedReportData = processReportData({...});
      
      // 更新当前页面数据
      this.setData({ dashboardData, ... });
      
      // 【P0 关键修复】保存到全局变量，供报告页使用
      const app = getApp();
      if (app && app.globalData) {
        app.globalData.pendingReport = {
          executionId: executionId,
          dashboardData: dashboardData,
          processedReportData: processedReportData,
          rawResults: rawResults,
          timestamp: Date.now()
        };
      }
    }
  } catch (error) {
    console.error('数据处理失败:', error);
  }

  // 跳转到报告页
  setTimeout(() => {
    wx.navigateTo({ url: `/pages/report-v2/report-v2?executionId=${executionId}` });
  }, 500);
}
```

---

### 修复 4: 增强调试日志
**文件**: `services/brandTestService.js` (行 1078-1174)

```javascript
const generateDashboardData = (processedReportData, pageContext) => {
  console.log('[generateDashboardData] ========== 开始生成看板数据 ==========');
  console.log('[generateDashboardData] 输入参数:', {
    isArray: Array.isArray(processedReportData),
    keys: processedReportData ? Object.keys(processedReportData) : [],
    pageContext
  });
  
  // ... 详细的数据验证和日志输出
  
  console.log('[generateDashboardData] rawResults:', {
    length: rawResults ? rawResults.length : 'null',
    firstItem: rawResults?.[0] ? '...' : 'none'
  });
  
  // ...
}
```

---

## 修复效果验证

### 预期行为
1. ✅ 诊断完成后，数据同步处理并保存到 `globalData.pendingReport`
2. ✅ 跳转到报告页后，优先从 `globalData` 加载数据
3. ✅ 如果 `globalData` 无数据，回退到云函数或 Storage
4. ✅ 不再出现多个轮询实例并存的情况
5. ✅ 报告页正确显示品牌分布、情感分析、关键词云等图表

### 调试日志关键词
- `[ReportData] ✅ 数据已保存到 globalData.pendingReport`
- `[ReportPageV2] ✅ 从全局变量获取报告数据` 或
- `[ReportPageV2] ✅ 从云函数获取报告数据` 或
- `[ReportPageV2] ✅ 从 Storage 获取报告数据`
- `[generateDashboardData] ✅ 看板数据生成成功`

---

## 修改文件清单

| 文件 | 修改行数 | 修改内容 |
|------|---------|---------|
| `services/brandTestService.js` | 278-314, 1078-1174 | 防止轮询重复启动 + 增强调试日志 |
| `miniprogram/services/diagnosisService.js` | 156-287 | 防止轮询重复启动 |
| `miniprogram/pages/report-v2/report-v2.js` | 598-720 | 多数据源加载策略 |
| `pages/index/index.js` | 1779-1878 | 诊断完成时传递数据 |

---

## 后续优化建议

1. **后端优化**: 确保 `/test/status/{id}?fields=full` 接口返回 `detailed_results` 数组
2. **性能优化**: 考虑使用 IndexedDB 替代 Storage 存储大数据量
3. **错误监控**: 集成错误监控系统，追踪数据流断裂的根本原因
4. **单元测试**: 为 `generateDashboardData` 和 `loadReportData` 添加单元测试

---

## 测试步骤

1. 清除小程序缓存（删除 Storage）
2. 重新发起品牌诊断
3. 观察控制台日志：
   - 确认只有一个轮询实例在运行
   - 确认数据保存到 `globalData.pendingReport`
   - 确认报告页从正确的数据源加载数据
4. 验证报告页图表正常显示

---

*修复完成时间：2026-03-11*
