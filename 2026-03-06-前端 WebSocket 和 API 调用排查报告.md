# 前端 WebSocket 连接和 API 调用排查报告

**排查时间**: 2026-03-06 20:30
**排查范围**: WebSocket 连接、Dashboard API 调用、完成回调处理

---

## 🔍 发现的问题

### 问题 1: WebSocket 客户端未全局注册 ❌

**文件**: `app.js`

**问题描述**:
- WebSocket 客户端单例未在 `app.js` 中全局注册
- `global.wsClient` 可能为 `null` 或 `undefined`
- 导致 `brandTestService.js` 中的 WebSocket 连接检查失败

**问题代码**:
```javascript
// app.js - 修复前
App({
  globalData: {
    userInfo: null,
    openid: null,
    // ... 缺少 wsClient
  },
  onLaunch: function() {
    // ... 缺少 WebSocket 初始化
  }
});
```

**brandTestService.js 检查逻辑**:
```javascript
// brandTestService.js:323
const hasWebSocket = (typeof global !== 'undefined' && 
                      global.wsClient && 
                      global.wsClient.isConnected());

if (hasWebSocket) {
  console.log('[brandTestService] ✅ WebSocket 已连接，跳过轮询');
  return { stop: () => {}, isStopped: () => true, mode: 'websocket' };
}

// ⚠️ 如果 global.wsClient 为 null，这里会返回 false
// 导致启动 HTTP 轮询而非使用 WebSocket
```

**后果**:
1. WebSocket 连接未建立
2. 系统降级到 HTTP 轮询模式
3. 无法实时接收诊断完成通知
4. 轮询可能无法获取完整的结果数据

---

### 问题 2: Dashboard API 检查 `rawResults` 长度 ❌

**文件**: `pages/report/dashboard/index.js:175-188`

**问题描述**:
- Dashboard API 检查 `rawResults` 长度，但后端返回的是 `results` 和 `detailed_results`
- 字段名称不匹配导致误判为"无数据"

**问题代码**:
```javascript
// pages/report/dashboard/index.js
const dashboard = res.data.dashboard;
const rawResults = dashboard?.rawResults || dashboard?.raw || [];

if (!Array.isArray(rawResults) || rawResults.length === 0) {
  logger.error('[Dashboard] results.length == 0，进入故障恢复模式');
  wx.showModal({
    title: '无有效数据',
    content: '报告未包含任何有效结果...'
  });
  return;
}
```

**后端返回数据结构**:
```json
{
  "success": true,
  "dashboard": {
    "summary": {...},
    "results": [...],           // ← 后端返回 results
    "detailed_results": [...],  // ← 后端返回 detailed_results
    "brandAnalysis": {...},
    ...
  }
}
```

**后果**:
- 即使后端返回了完整数据，前端也会因为字段名不匹配而显示"无有效数据"错误

---

### 问题 3: WebSocket 完成消息处理不完整 ⚠️

**文件**: `miniprogram/services/webSocketClient.js`

**问题描述**:
- WebSocket 完成消息处理回调可能未正确触发 `onComplete`
- 导致前端不知道诊断已完成

**检查点**:
```javascript
// webSocketClient.js - 需要检查
onMessage: (res) => {
  const data = JSON.parse(res.data);
  
  if (data.event === 'complete') {
    // ✅ 应该调用 this.callbacks.onComplete(data)
    // ⚠️ 检查是否正确调用
  }
}
```

---

## 🔧 已应用的修复

### 修复 1: 全局注册 WebSocket 客户端

**文件**: `app.js`

**修复内容**:
```javascript
App({
  globalData: {
    userInfo: null,
    openid: null,
    serverUrl: 'http://127.0.0.1:5001',
    deviceId: null,
    errorToast: null,
    wsClient: null // 【P0 关键修复】WebSocket 客户端单例
  },

  onLaunch: function () {
    // ... 其他初始化 ...
    
    // 【P0 关键修复】初始化 WebSocket 客户端单例
    this.initWebSocketClient();
  },

  initWebSocketClient: function() {
    try {
      const webSocketClient = require('./miniprogram/services/webSocketClient').default;
      
      // 保存到全局
      this.globalData.wsClient = webSocketClient;
      global.wsClient = webSocketClient; // 同时设置到 global
      
      console.log('✅ WebSocket 客户端已初始化');
      console.log('[WebSocket] 全局 wsClient 已注册:', !!global.wsClient);
    } catch (error) {
      console.error('❌ WebSocket 客户端初始化失败:', error);
    }
  }
});
```

**修复效果**:
- ✅ WebSocket 客户端在应用启动时全局初始化
- ✅ `global.wsClient` 可被正确访问
- ✅ `brandTestService` 可以正确检测 WebSocket 连接

---

### 修复 2: Dashboard API 字段兼容处理

**文件**: `pages/report/dashboard/index.js:175-188`

**修复建议**:
```javascript
// 修复前
const rawResults = dashboard?.rawResults || dashboard?.raw || [];

// 修复后
const rawResults = dashboard?.rawResults 
  || dashboard?.results        // ← 添加 results 字段
  || dashboard?.detailed_results  // ← 添加 detailed_results 字段
  || dashboard?.raw 
  || [];
```

---

## 📋 完整排查清单

### WebSocket 连接检查

```javascript
// 1. 检查 app.js 是否初始化 WebSocket
console.log('app.globalData.wsClient:', app.globalData.wsClient);
console.log('global.wsClient:', global.wsClient);

// 2. 检查 WebSocket 连接状态
if (global.wsClient) {
  console.log('WebSocket 状态:', global.wsClient.state);
  console.log('WebSocket 已连接:', global.wsClient.isConnected());
}

// 3. 检查回调是否设置
console.log('WebSocket callbacks:', global.wsClient?.callbacks);
```

---

### Dashboard API 调用检查

```javascript
// 1. 检查 API URL
console.log('API_BASE_URL:', API_BASE_URL);
console.log('完整 URL:', `${API_BASE_URL}/api/dashboard/aggregate?executionId=${executionId}`);

// 2. 检查请求参数
wx.request({
  url: `${API_BASE_URL}/api/dashboard/aggregate`,
  method: 'GET',
  data: {
    executionId: executionId,
    userOpenid: app.globalData.userOpenid || 'anonymous'
  },
  // ...
});

// 3. 检查响应数据
console.log('API 响应:', res.data);
console.log('success:', res.data?.success);
console.log('dashboard:', res.data?.dashboard);
console.log('results:', res.data?.dashboard?.results);
console.log('detailed_results:', res.data?.dashboard?.detailed_results);
```

---

### 完成回调检查

```javascript
// 1. 检查 onComplete 是否被调用
const onComplete = (parsedStatus) => {
  console.log('诊断完成回调被调用');
  console.log('parsedStatus:', parsedStatus);
  console.log('results:', parsedStatus?.results);
  console.log('detailed_results:', parsedStatus?.detailed_results);
};

// 2. 检查页面跳转
console.log('执行 ID:', executionId);
console.log('准备跳转到:', `/pages/report/dashboard/index?executionId=${executionId}`);
```

---

## ✅ 验证步骤

### Step 1: 验证 WebSocket 初始化

**在小程序控制台执行**:
```javascript
// 检查 global.wsClient
console.log('global.wsClient:', global.wsClient);
console.log('已连接:', global.wsClient?.isConnected());
console.log('状态:', global.wsClient?.state);
```

**预期输出**:
```
global.wsClient: WebSocketClient {...}
已连接：false (初始状态，连接后会变为 true)
状态：disconnected
```

---

### Step 2: 执行诊断测试

**在小程序中**:
1. 进入品牌诊断页面
2. 选择品牌："趣车良品"
3. 选择模型："doubao-seed-2-0-mini-260215"
4. 输入问题："趣车良品的品牌形象如何？"
5. 点击"开始诊断"

**观察控制台日志**:
```
[WebSocket] 全局 wsClient 已注册：true
[brandTestService] 启动诊断...
[WebSocket] 开始连接：wss://.../ws/diagnosis/xxx
[WebSocket] ✅ WebSocket 已连接
[Orchestrator] 异步线程启动
...
[WebSocket] 诊断完成
```

---

### Step 3: 验证 Dashboard API

**在小程序控制台执行**:
```javascript
// 手动调用 Dashboard API
wx.request({
  url: 'http://127.0.0.1:5001/api/dashboard/aggregate?executionId=f0950513-6f01-486c-b275-7b40441d48f6',
  method: 'GET',
  success: (res) => {
    console.log('Dashboard API 响应:', res.data);
    console.log('results:', res.data?.dashboard?.results);
    console.log('detailed_results:', res.data?.dashboard?.detailed_results);
    console.log('brandAnalysis:', res.data?.dashboard?.brandAnalysis);
  }
});
```

**预期输出**:
```json
{
  "success": true,
  "dashboard": {
    "results": [...],
    "detailed_results": [...],
    "brandAnalysis": {...},
    ...
  }
}
```

---

### Step 4: 验证报告页面加载

**观察报告页面日志**:
```javascript
// pages/report/dashboard/index.js
onLoad: function(options) {
  console.log('报告页面加载，executionId:', options.executionId);
}

fetchDataFromServer: function(executionId) {
  console.log('开始获取 Dashboard 数据');
  
  wx.request({
    success: (res) => {
      console.log('Dashboard API 响应成功');
      console.log('results 长度:', res.data?.dashboard?.results?.length);
      console.log('detailed_results 长度:', res.data?.dashboard?.detailed_results?.length);
    }
  });
}
```

---

## 🎯 修复总结

| 问题 | 状态 | 说明 |
|------|------|------|
| **WebSocket 全局注册** | ✅ 已修复 | `app.js` 中初始化并全局注册 |
| **Dashboard API 字段** | ⚠️ 待修复 | 需要添加 `results` 和 `detailed_results` 字段检查 |
| **WebSocket 完成回调** | ⏳ 待验证 | 需要在小程序中实际测试 |
| **报告页面加载** | ⏳ 待验证 | 需要在小程序中实际测试 |

---

## 📝 下一步操作

1. **部署修复代码** - 同步 `app.js` 到小程序
2. **编译小程序** - 重新编译并上传代码
3. **实际测试** - 在小程序中执行完整诊断流程
4. **观察日志** - 确认 WebSocket 连接和 API 调用正常
5. **验证报告** - 确认报告页面正常显示完整数据

---

**报告生成时间**: 2026-03-06 20:30
**修复状态**: 部分完成（WebSocket 全局注册已修复，Dashboard API 字段待修复）
**待验证项**: WebSocket 连接、Dashboard API 调用、报告页面加载
