# 详情页死循环问题 - API 格式修复报告

**修复日期**: 2026-03-15 02:25  
**问题**: 点击历史记录后详情页卡死  
**根因**: API 返回格式与前端期望不匹配  
**修复状态**: ✅ 已完成

---

## 一、问题根因

### 后端日志

```
✅ 获取完整报告成功：06b3ed04-..., 结果数：1
[报告数据检查] keys=['report', 'results', 'analysis', 'brandDistribution', ...]
[报告数据详情] brandDistribution.totalCount=1, keywords_count=0
```

### API 实际返回格式

```json
{
  "success": true,
  "data": {              // ← 实际报告数据在这里
    "results": [...],
    "brandDistribution": {...},
    ...
  },
  "hasPartialData": true,
  "warnings": [...]
}
```

### 前端期望格式

```javascript
// ❌ 前端代码期望
const report = res.data;  // 直接访问
if (report.results || report.brandDistribution) { ... }

// ✅ API 实际返回
const report = res.data.data;  // 需要多一层
```

### 问题链路

```
前端请求 /api/diagnosis/report/{id}
    ↓
后端返回：{success: true, data: {...}}
    ↓
前端访问：res.data.results → undefined ❌
    ↓
条件判断失败：if (report && report.results) → false
    ↓
降级到本地缓存 → 本地也没有 → 卡死
```

---

## 二、修复方案

### 修复内容

**文件**: `pages/history-detail/history-detail.js`  
**修改位置**: Line 189-218 (`loadFromServer` 函数)

**修复前**:
```javascript
success: (res) => {
  const report = res.data;  // ❌ 错误：直接访问
  if (report && (report.results || report.brandDistribution)) {
    this.processHistoryDataFromApi(report);
  }
}
```

**修复后**:
```javascript
success: (res) => {
  console.log('[第 2 层] 请求成功:', {
    statusCode: res.statusCode,
    dataKeys: Object.keys(res.data || {}),
    hasResults: !!(res.data?.data?.results || res.data?.results)
  });

  // 【P21 修复 - 修复 API 返回格式不匹配问题】
  // API 返回格式：{success: true, data: {...}, ...}
  // 需要访问 res.data.data 获取实际报告数据
  const apiResponse = res.data;
  const report = apiResponse.data || apiResponse;  // ✅ 优先使用 apiResponse.data
  
  console.log('[报告详情页] 提取报告数据:', {
    hasData: !!report,
    resultsCount: (report.results || report.result || []).length
  });
  
  if (report && (report.results || report.result || report.brandDistribution)) {
    this.processHistoryDataFromApi(report);
    return;
  }
  
  // 降级到本地缓存
  this.loadHistoryRecordLocal(executionId);
}
```

---

## 三、验证步骤

### 步骤 1：重新编译

```
微信开发者工具 → 编译
```

### 步骤 2：测试流程

1. **进入历史记录页面**
   - 应显示 20 条记录

2. **点击任意记录**
   - 应跳转到详情页
   - 应显示"加载中..."（不超过 5 秒）

3. **观察控制台日志**
   ```
   [第 2 层] 请求成功：{statusCode: 200, dataKeys: ['success', 'data', ...]}
   [报告详情页] 提取报告数据：{hasData: true, resultsCount: 1}
   [报告详情页] ✅ 服务器数据加载成功，有完整报告数据
   [报告详情页] 第 1 层加载完成，loading=false
   ```

4. **验证页面显示**
   - 应显示品牌名称
   - 应显示总体评分
   - 应显示详细数据

---

## 四、API 格式说明

### 后端 API 返回格式

```json
{
  "success": true,
  "data": {
    "report": {...},
    "results": [...],
    "brandDistribution": {...},
    "sentimentDistribution": {...},
    "keywords": [...],
    "analysis": {...}
  },
  "hasPartialData": true,
  "warnings": [...]
}
```

### 前端数据处理

```javascript
// 正确访问方式
const apiResponse = res.data;
const report = apiResponse.data;  // ← 访问 .data 字段

// 访问具体字段
const results = report.results || report.result || [];
const brandDistribution = report.brandDistribution || {};
const analysis = report.analysis || {};
```

---

## 五、修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `pages/history-detail/history-detail.js` | 修复 API 返回格式解析逻辑 |

---

## 六、相关修复汇总

| 问题 | 修复文件 | 状态 |
|------|---------|------|
| 历史列表显示 0 条 | `pages/history/history.js` | ✅ 已修复 |
| 详情页死循环（超时） | `pages/history-detail/history-detail.js` | ✅ 已修复 |
| 详情页死循环（数据验证） | `pages/history-detail/history-detail.js` | ✅ 已修复 |
| 详情页死循环（API 格式） | `pages/history-detail/history-detail.js` | ✅ 已修复 |

---

## 七、完整测试流程

### 步骤 1：清除缓存

```javascript
wx.clearStorageSync()
```

### 步骤 2：重新编译

```
微信开发者工具 → 编译
```

### 步骤 3：测试历史列表

```
进入"诊断记录" → 应显示 20 条记录
```

### 步骤 4：测试详情页

```
点击任意记录 → 跳转详情页
观察控制台 → 应显示加载成功日志
验证页面 → 应显示完整报告数据
```

---

**修复工程师**: 首席全栈工程师 (AI)  
**修复时间**: 2026-03-15 02:25  
**状态**: ✅ 待用户验证
