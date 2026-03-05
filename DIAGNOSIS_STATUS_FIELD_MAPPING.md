# 诊断状态字段映射分析与统一方案

## 一、后端返回的核心字段

根据 `taskStatusService.js` 和 `api/home.js` 分析，后端 `/test/status/<executionId>` 返回以下字段：

### 1. 核心状态字段（优先级从高到低）

| 字段名 | 类型 | 说明 | 优先级 |
|--------|------|------|--------|
| `should_stop_polling` | boolean | **后端明确的轮询终止信号** | ⭐⭐⭐ 最高 |
| `is_completed` | boolean | 任务是否完成 | ⭐⭐ 高 |
| `status` | string | 任务状态机状态 | ⭐⭐ 高 |
| `stage` | string | 当前执行阶段 | ⭐ 中 |
| `progress` | number | 进度百分比 (0-100) | ⭐ 中 |

### 2. 结果数据字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `results` | Array | 简化结果列表 |
| `detailed_results` | Array | 详细结果列表（推荐使用） |
| `competitive_analysis` | Object | 竞争分析数据 |
| `semantic_drift_data` | Object | 语义偏移数据 |
| `recommendation_data` | Object | 优化建议数据 |

### 3. 错误相关字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `error` | string | 错误信息 |
| `message` | string | 附加消息 |
| `warning` | string | 警告信息 |
| `missing_count` | number | 缺失结果数量 |

---

## 二、前端状态变量分析

### 当前 `index.js` 中使用的状态变量

```javascript
data: {
  // 诊断状态
  isTesting: false,        // 是否正在诊断中
  testProgress: 0,         // 进度百分比
  testCompleted: false,    // 诊断是否完成
  completedTime: null,     // 完成时间文本
  
  // 报告标记
  hasLastReport: false,    // 是否有上次报告
  hasLatestDiagnosis: false, // 是否有最新诊断
  
  // UI 显示
  currentStage: 'init',    // 当前阶段
  progressText: '',        // 进度文本
  debugJson: '',           // 调试信息
}
```

---

## 三、字段映射关系（当前实际使用）

### 从后端到前端的数据流

```
后端 API 响应
    ↓
parseTaskStatus() 解析
    ↓
brandTestService 轮询回调
    ↓
index.js setData()
    ↓
index.wxml 渲染
```

### 具体映射表

| 后端字段 | 解析后字段 | 前端 data 变量 | WXML 使用位置 |
|----------|------------|---------------|---------------|
| `progress` | `parsed.progress` | `testProgress` | `{{isTesting ? '诊断中... ' + testProgress + '%' : ...}}` |
| `stage` / `status` | `parsed.stage` | `currentStage` | `<analysis-card status="{{currentStage}}">` |
| `parsed.statusText` | - | `progressText` | (备用) |
| `is_completed=true` | `parsed.is_completed` | `testCompleted` | `{{testCompleted && !hasLastReport ? '' : 'hidden'}}` |
| `should_stop_polling` | `parsed.should_stop_polling` | (间接影响) | 通过 `testCompleted` 体现 |
| `detailed_results` | - | `reportData` | 报告展示组件 |

---

## 四、当前存在的问题

### 问题 1: 状态判断分散

**现状**: 多个地方使用不同字段判断完成状态

```javascript
// 问题点 1: parseTaskStatus 中
if (backendShouldStopPolling) {
  parsed.should_stop_polling = true;
  // ...
}

if (backendIsCompleted) {
  parsed.is_completed = true;
  // ...
}

switch(lowerCaseStatus) {
  case TASK_STAGES.COMPLETED:
    parsed.is_completed = true;
    // ...
}

// 问题点 2: brandTestService 轮询中
if (parsedStatus.should_stop_polling === true) {
  controller.stop();
  onComplete(parsedStatus);  // ← 这里触发完成
}

if (isTerminalStatus(status)) {
  controller.stop();
  onComplete(parsedStatus);  // ← 这里也触发完成
}
```

### 问题 2: 前端 setData 时机不一致

```javascript
// 现状：轮询回调中只更新进度
onProgress: (parsedStatus) => {
  this.setData({
    testProgress: parsedStatus.progress,
    progressText: parsedStatus.statusText,
    currentStage: parsedStatus.stage,
    // ❌ 没有更新 isTesting
  });
}

// 完成回调中才更新状态
onComplete: (parsedStatus) => {
  this.setData({
    isTesting: false,    // ← 这里才设置
    testCompleted: true, // ← 这里才设置
    // ...
  });
}
```

### 问题 3: WXML 状态判断冗余

```xml
<!-- 当前 WXML 有 3 个互斥的状态块 -->
<!-- 状态 1: 有上次报告 -->
<view class="completed-actions {{hasLastReport && !isTesting ? '' : 'hidden'}}">

<!-- 状态 2: 诊断按钮 -->
<button class="scan-button {{hasLastReport ? 'hidden' : ''}}" disabled="{{isTesting}}">

<!-- 状态 3: 诊断完成（当次） -->
<view class="completed-actions {{testCompleted && !hasLastReport ? '' : 'hidden'}}">
```

---

## 五、统一方案（推荐）

### 方案 1: 以后端 `should_stop_polling` 为唯一终止信号 ✅

**核心原则**:
1. 轮询期间：只更新进度，不改变 `isTesting`
2. 收到 `should_stop_polling=true`：立即设置 `isTesting: false`
3. 根据 `status` 字段区分成功/失败

**修改后的数据流**:

```javascript
// index.js - 重构后的轮询控制器
this.pollingController = createPollingController(
  executionId,
  
  // onProgress: 只更新进度显示
  (parsedStatus) => {
    this.setData({
      testProgress: parsedStatus.progress,
      progressText: parsedStatus.statusText,
      currentStage: parsedStatus.stage,
      // ⚠️ 关键：不在这里改变 isTesting
    });
  },
  
  // onComplete: 统一处理完成状态
  (parsedStatus) => {
    wx.hideLoading();
    
    // ✅ 关键修复：立即更新按钮状态
    this.setData({
      isTesting: false,        // 停止加载
      testCompleted: true,     // 标记完成
      hasLastReport: true,     // 标记有报告
      currentStage: 'completed'
    });
    
    // 保存数据并跳转
    this._onDiagnosisComplete(parsedStatus, executionId);
  },
  
  // onError: 统一处理错误
  (error) => {
    wx.hideLoading();
    
    // ✅ 关键修复：确保按钮恢复
    this.setData({
      isTesting: false,
      testCompleted: false,
      currentStage: 'error'
    });
    
    this._onDiagnosisError(error);
  }
);
```

### 方案 2: 统一使用 `appState` 枚举 ⭐⭐⭐

**推荐使用**: 用单一状态变量控制所有 UI 变化

```javascript
// index.js
data: {
  appState: 'idle',  // 'idle' | 'checking' | 'testing' | 'completed' | 'error'
  testProgress: 0,
  reportData: null
}

// 状态流转
startBrandTest() {
  this.setData({ appState: 'checking' });
  // 验证通过后
  this.setData({ appState: 'testing' });
}

// 轮询回调
onProgress: (parsedStatus) => {
  // testing 状态保持不变，只更新进度
  this.setData({ testProgress: parsedStatus.progress });
}

onComplete: (parsedStatus) => {
  this.setData({ 
    appState: 'completed',
    testProgress: 100
  });
}

onError: (error) => {
  this.setData({ appState: 'error' });
}
```

```xml
<!-- index.wxml - 简化后的按钮逻辑 -->
<button 
  class="scan-button"
  bindtap="startBrandTest"
  disabled="{{appState === 'testing'}}">
  
  <text class="button-content">
    <text class="loading-spinner" wx:if="{{appState === 'testing'}}"></text>
    <text class="button-text">
      <block wx:if="{{appState === 'testing'}}">
        诊断中... {{testProgress}}%
      </block>
      <block wx:elif="{{appState === 'completed'}}">
        重新诊断
      </block>
      <block wx:elif="{{appState === 'error'}}">
        诊断失败，重试
      </block>
      <block wx:else>
        AI 品牌战略诊断
      </block>
    </text>
  </text>
</button>

<!-- 查看报告入口 -->
<view class="view-report-entry" 
      bindtap="viewReport"
      wx:if="{{appState === 'completed'}}">
  <text>📊 查看诊断报告</text>
</view>
```

---

## 六、具体修改建议

### 1. 修改 `parseTaskStatus` 返回值

```javascript
// services/taskStatusService.js
const parseTaskStatus = (statusData, startTime = Date.now()) => {
  const parsed = {
    // 核心状态字段
    status: statusData?.status || 'unknown',
    stage: statusData?.stage || 'init',
    progress: statusData?.progress || 0,
    
    // ✅ 统一使用 is_done 作为完成标志
    is_done: statusData?.should_stop_polling === true || 
             statusData?.is_completed === true ||
             ['completed', 'finished', 'done', 'failed'].includes(statusData?.status),
    
    // 结果数据
    results: statusData?.results || [],
    detailed_results: statusData?.detailed_results || [],
    
    // 错误信息
    error: statusData?.error || null,
    warning: statusData?.warning || null,
    
    // 显示文本
    statusText: '',
    detailText: ''
  };
  
  // ✅ 根据 status 字段生成显示文本
  switch(statusData?.status) {
    case 'completed':
      parsed.statusText = '诊断完成！';
      parsed.progress = 100;
      break;
    case 'failed':
      parsed.statusText = '诊断失败';
      break;
    // ... 其他状态
  }
  
  return parsed;
};
```

### 2. 修改 `index.js` 状态管理

```javascript
// pages/index/index.js
data: {
  // ✅ 统一使用 appState 控制 UI
  appState: 'idle',  // idle | testing | completed | error
  
  // 进度显示
  testProgress: 0,
  progressText: '',
  
  // 报告数据
  reportData: null,
  hasLastReport: false
},

// 启动诊断
startBrandTest: function() {
  // 验证通过后
  this.setData({ 
    appState: 'testing',
    testProgress: 0
  });
  
  this._executeDiagnosis(brandList, selectedModels, customQuestions);
},

// 轮询回调
onProgress: (parsedStatus) => {
  this.setData({
    testProgress: parsedStatus.progress,
    progressText: parsedStatus.statusText
    // ✅ appState 保持 testing 不变
  });
},

onComplete: (parsedStatus) => {
  this.setData({ 
    appState: 'completed',
    testProgress: 100,
    hasLastReport: true
  });
  this._onDiagnosisComplete(parsedStatus, executionId);
},

onError: (error) => {
  this.setData({ 
    appState: 'error',
    testProgress: 0
  });
  this._onDiagnosisError(error);
}
```

### 3. 修改 `index.wxml` 按钮逻辑

```xml
<!-- 简化为单一按钮，根据 appState 切换文案 -->
<button 
  class="scan-button {{appState}}"
  bindtap="startBrandTest"
  disabled="{{appState === 'testing'}}">
  
  <text class="button-content">
    <text class="loading-spinner" wx:if="{{appState === 'testing'}}"></text>
    
    <text class="button-text">
      <block wx:if="{{appState === 'testing'}}">
        诊断中... {{testProgress}}%
      </block>
      <block wx:elif="{{appState === 'completed'}}">
        重新诊断
      </block>
      <block wx:elif="{{appState === 'error'}}">
        诊断失败，点击重试
      </block>
      <block wx:else>
        AI 品牌战略诊断
      </block>
    </text>
  </text>
</button>

<!-- 查看报告入口（仅在 completed 状态显示） -->
<view class="view-report-entry" 
      bindtap="viewReport"
      wx:if="{{appState === 'completed'}}">
  <text class="entry-icon">📊</text>
  <text class="entry-text">查看诊断报告</text>
  <text class="entry-time" wx:if="{{completedTime}}">{{completedTime}}</text>
</view>
```

---

## 七、字段统一对照表（最终版）

| 后端字段 | 解析字段 | 前端 data | WXML 绑定 | 说明 |
|----------|----------|-----------|-----------|------|
| `should_stop_polling` | `is_done` | `appState` | `{{appState}}` | 轮询终止信号 |
| `status` | `status` | `currentStage` | `status="{{currentStage}}"` | 状态机状态 |
| `progress` | `progress` | `testProgress` | `{{testProgress}}%` | 进度百分比 |
| `is_completed` | `is_done` | `appState` | (间接) | 完成标志 |
| `detailed_results` | `detailed_results` | `reportData` | `data="{{reportData}}"` | 详细结果 |
| `error` | `error` | (弹窗显示) | - | 错误信息 |

---

## 八、执行建议

1. **立即修改**: 优先统一 `should_stop_polling` 的判断逻辑
2. **渐进重构**: 先保持现有 `isTesting`/`testCompleted` 变量，逐步迁移到 `appState`
3. **测试覆盖**: 确保以下场景都能正确切换状态：
   - ✅ 正常诊断完成
   - ✅ 后端返回 500 错误
   - ✅ 网络超时
   - ✅ 认证失败 (403)
   - ✅ 部分完成 (有警告)
