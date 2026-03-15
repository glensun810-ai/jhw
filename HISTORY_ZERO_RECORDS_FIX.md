# 历史列表显示 0 条问题修复报告

**修复日期**: 2026-03-15 01:45  
**问题**: 清除缓存后历史列表显示 0 条（应为 20 条）  
**页面**: `pages/history/history` (tabBar 配置的页面)  
**修复状态**: ✅ 已添加调试日志，待验证

---

## 一、问题根因

### 用户操作流程

1. 进入"诊断记录"页面（tabBar → `pages/history/history`）
2. 执行 `wx.clearStorageSync()` 清除缓存
3. 页面显示 0 条历史记录

### 数据流分析

```
onLoad → refreshHistory → loadHistory
    ↓
从本地存储加载 (getDiagnosisHistory)
    ↓
返回空数组（因为已清除缓存）
    ↓
historyList.length === 0
    ↓
应该从 API 加载 ✅
    ↓
但用户看到 0 条 ❌
```

### 可能原因

1. **API 调用失败** - `getTestHistory()` 返回错误
2. **数据处理错误** - API 返回格式与预期不符
3. **页面未更新** - `setData` 未正确调用

---

## 二、修复方案

### 修复内容

**文件**: `pages/history/history.js`

**修改位置**: Line 172-220 (`loadHistory` 函数)

**添加的调试日志**:

```javascript
// 【P21 修复 - 2026-03-15】如果没有本地数据，尝试从 API 加载
if (historyList.length === 0) {
  console.log('[历史记录] 本地数据为空，开始从 API 加载...');
  try {
    // 构建 API 请求参数
    const params = { ... };
    
    console.log('[历史记录] API 请求参数:', params);
    
    // 调用 API
    const result = await getTestHistory(params);
    console.log('[历史记录] API 返回结果:', result);
    
    const reports = result.reports || result.data || [];
    console.log('[历史记录] 提取 reports:', reports.length, '条');
    
    // 处理数据
    historyList = reports.map(...);
    totalCount = result.total || ...;
    
    console.log(`[历史记录] 从 API 加载 ${historyList.length} 条记录，totalCount=${totalCount}`);
  } catch (apiError) {
    console.error('[历史记录] API 加载失败:', apiError);
    console.error('[历史记录] 错误堆栈:', apiError.stack);
  }
} else {
  console.log('[历史记录] 使用本地数据，不从 API 加载');
}
```

---

## 三、验证步骤

### 步骤 1：重新编译

```
微信开发者工具 → 编译
```

### 步骤 2：清除缓存

```javascript
// 微信开发者工具控制台
wx.clearStorageSync()
console.log('✅ 缓存已清除')
```

### 步骤 3：刷新页面

```
点击"诊断记录" tab
或下拉刷新
```

### 步骤 4：查看控制台日志

**预期日志**:
```
[历史记录] 从本地存储加载 0 条记录
[历史记录] 本地数据为空，开始从 API 加载...
[历史记录] API 请求参数：{page: 1, limit: 20, ...}
[历史记录] API 返回结果：{status: 'success', history: [...]}
[历史记录] 提取 reports: 20 条
[历史记录] 从 API 加载 20 条记录，totalCount=20
```

### 步骤 5：验证页面显示

**预期结果**:
- 页面显示 20 条历史记录
- 每条记录显示品牌名称、时间、分数

---

## 四、后端 API 验证

### API 测试

```bash
curl "http://127.0.0.1:5001/api/test-history?userOpenid=anonymous&limit=20"
```

**预期响应**:
```json
{
  "status": "success",
  "history": [
    {
      "id": 99,
      "execution_id": "06b3ed04-...",
      "brandName": "趣车良品",
      "healthScore": 100,
      ...
    }
  ],
  "count": 20
}
```

**实际结果**: ✅ API 返回 20 条记录

---

## 五、可能的问题和解决方案

### 问题 1：API 调用失败

**日志**:
```
[历史记录] API 加载失败：Error: ...
```

**解决方案**:
1. 检查后端服务是否运行
2. 检查网络请求权限（微信小程序后台配置）
3. 检查 API 地址是否正确

### 问题 2：返回格式不符

**日志**:
```
[历史记录] 提取 reports: 0 条
```

**解决方案**:
检查 API 返回格式，修改 `result.reports || result.data` 逻辑

### 问题 3：setData 未调用

**日志**:
```
[历史记录] 从 API 加载 20 条记录，totalCount=20
```
但页面仍然显示 0 条

**解决方案**:
检查 `setData` 调用是否在 try-catch 外部

---

## 六、长期解决方案

### 方案 1：统一历史记录页面（推荐）

**问题**: 现在有 2 套历史记录系统
- `pages/history/history` → 旧系统
- `pages/report/history` → 新系统（推荐）

**解决**: 修改 `app.json` tabBar 配置

```json
"tabBar": {
  "list": [
    {
      "pagePath": "pages/report/history/index",
      "text": "诊断记录"
    }
  ]
}
```

### 方案 2：强制从 API 加载

修改 `pages/history/history.js` Line 172：

**修复前**:
```javascript
if (historyList.length === 0) {
```

**修复后**:
```javascript
// 如果本地数据少于 10 条，强制从 API 加载
if (historyList.length === 0 || historyList.length < 10) {
```

---

## 七、调试技巧

### 查看网络请求

```
微信开发者工具 → 调试器 → Network
// 查看 /api/test-history 请求和响应
```

### 查看本地存储

```javascript
// 微信开发者工具控制台
wx.getStorageSync('diagnosis_history_list')
// 应返回数组
```

### 手动触发 API 调用

```javascript
// 微信开发者工具控制台
const { getTestHistory } = require('../../api/history')
getTestHistory({page: 1, limit: 20}).then(console.log).catch(console.error)
```

---

**修复工程师**: 首席全栈工程师 (AI)  
**修复时间**: 2026-03-15 01:45  
**状态**: ⏳ 待用户验证
