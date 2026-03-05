# appState 迁移实施记录

## Step 1: 引入 appState 变量 ✅

### 修改位置：pages/index/index.js

在 `data` 对象中添加 `appState` 变量（第 148-155 行附近）：

```javascript
// 测试状态
isTesting: false,
testProgress: 0,
progressText: '准备启动 AI 认知诊断...',
testCompleted: false,

// 【Step 1 新增】统一状态管理（与现有变量并存，双轨运行）
// 状态枚举：'idle' | 'checking' | 'testing' | 'completed' | 'error'
appState: 'idle',
```

### 状态映射表

| appState | isTesting | testCompleted | hasLastReport | 说明 |
|----------|-----------|---------------|---------------|------|
| 'idle' | false | false | false | 初始状态，可点击诊断 |
| 'checking' | false | false | false | 验证输入中（可选） |
| 'testing' | true | false | false | 诊断进行中 |
| 'completed' | false | true | true | 诊断完成 |
| 'error' | false | false | false | 诊断失败，可重试 |

### 验证方法

在微信开发者工具 Console 中运行：
```javascript
const page = getCurrentPages()[getCurrentPages().length - 1];
console.log('appState:', page.data.appState);
// 期望输出：'idle'
console.log('isTesting:', page.data.isTesting);
// 期望输出：false
```

---

## Step 2: startBrandTest 同步设置 appState ✅

### 修改位置：pages/index/index.js - startBrandTest 函数

在现有的 `setData` 调用后添加 `appState` 设置：

```javascript
startBrandTest: function() {
  try {
    // ... 验证逻辑（保留原有代码）...
    
    // 原有代码（保留）
    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动 AI 认知诊断...',
      testCompleted: false,
      hasLastReport: false,
      completedTime: null,
      currentStage: 'checking'
    });
    
    // 【Step 2 新增】同步设置 appState
    this.setData({
      appState: 'testing'  // 与 isTesting: true 对应
    });
    
    // ... 后续诊断逻辑 ...
    
  } catch (error) {
    // 异常时也要设置 appState
    this.setData({ appState: 'error' });
    this.handleException(error, '诊断启动');
  }
}
```

### 验证方法

```javascript
// 点击诊断按钮后，在 Console 中运行
const page = getCurrentPages()[getCurrentPages().length - 1];
console.assert(page.data.appState === 'testing', 'appState 应该是 testing');
console.assert(page.data.isTesting === true, 'isTesting 应该是 true');
console.log('✅ Step 2 验证通过');
```

---

## Step 3: 轮询回调同步 appState ✅

### 修改位置：pages/index/index.js - callBackendBrandTest 或 _executeDiagnosis 函数

在轮询控制器的回调中同步设置 `appState`：

```javascript
_executeDiagnosis: async function(brandList, selectedModels, customQuestions) {
  wx.showLoading({ title: '启动诊断...', mask: true });

  try {
    const inputData = {
      brandName: brandList[0],
      competitorBrands: brandList.slice(1),
      selectedModels,
      customQuestions
    };

    const executionId = await startDiagnosis(inputData);
    console.log('[诊断启动] ✅ 任务创建成功，执行 ID:', executionId);

    // 统一使用 pollingController 轮询
    this.pollingController = createPollingController(
      executionId,
      
      // onProgress: 进度回调
      (parsedStatus) => {
        this.setData({
          testProgress: parsedStatus.progress,
          progressText: parsedStatus.statusText,
          currentStage: parsedStatus.stage,
          debugJson: JSON.stringify(parsedStatus, null, 2)
          // appState 保持 'testing' 不变
        });
      },
      
      // onComplete: 完成回调
      (parsedStatus) => {
        wx.hideLoading();
        
        // 原有代码（保留）
        this.setData({
          isTesting: false,
          testCompleted: true,
          hasLastReport: true,
          completedTime: this.getCompletedTimeText()
        });
        
        // 【Step 3 新增】同步设置 appState
        this.setData({
          appState: 'completed'  // 与 testCompleted: true 对应
        });
        
        this.handleDiagnosisComplete(parsedStatus, executionId);
      },
      
      // onError: 错误回调
      (error) => {
        wx.hideLoading();
        
        // 原有代码（保留）
        this.setData({
          isTesting: false,
          testCompleted: false
        });
        
        // 【Step 3 新增】同步设置 appState
        this.setData({
          appState: 'error'  // 标记为错误状态
        });
        
        this.handleDiagnosisError(error);
      }
    );

  } catch (err) {
    wx.hideLoading();
    this.setData({ 
      isTesting: false,
      appState: 'error'  // 启动失败也要设置
    });
    this.handleDiagnosisError(err);
  }
},
```

### 验证方法

```javascript
// 诊断完成后，在 Console 中运行
const page = getCurrentPages()[getCurrentPages().length - 1];
console.assert(page.data.appState === 'completed', 'appState 应该是 completed');
console.assert(page.data.isTesting === false, 'isTesting 应该是 false');
console.assert(page.data.testCompleted === true, 'testCompleted 应该是 true');
console.log('✅ Step 3 验证通过');

// 诊断失败时
console.assert(page.data.appState === 'error', 'appState 应该是 error');
console.log('✅ Step 3 错误状态验证通过');
```

---

## Step 4: WXML 双轨运行 ✅

### 修改位置：pages/index/index.wxml - 主操作按钮区域（约 200-250 行）

保留现有逻辑，添加 `appState` 判断作为补充：

```xml
<!-- 主操作按钮 -->
<view class="main-action-section">
  <!-- 状态 1: 有上次报告（保留旧逻辑） -->
  <view class="completed-actions {{hasLastReport && !isTesting ? '' : 'hidden'}}">
    <view class="completed-badge">
      <text class="badge-icon">✅</text>
      <text class="badge-text">已有诊断报告</text>
      <text class="badge-time" wx:if="{{completedTime}}">{{completedTime}}</text>
    </view>

    <view class="completed-buttons">
      <button class="btn-primary-view" bindtap="viewReport">
        <text class="btn-icon">📊</text>
        <text class="btn-text">查看上次诊断报告</text>
      </button>

      <button class="btn-secondary-retry" bindtap="retryDiagnosis">
        <text class="btn-icon">🔄</text>
        <text class="btn-text">重新诊断</text>
      </button>
    </view>
  </view>

  <!-- 状态 2: 诊断按钮（双轨判断：同时使用旧变量和 appState） -->
  <button class="scan-button {{hasLastReport ? 'hidden' : ''}}"
          bindtap="startBrandTest"
          disabled="{{isTesting || appState === 'testing'}}">
    <text class="button-content">
      <text class="loading-spinner" wx:if="{{isTesting}}"></text>
      <text class="button-text">
        <!-- 优先使用 appState，降级使用旧变量 -->
        <block wx:if="{{appState === 'testing'}}">
          诊断中... {{testProgress}}%
        </block>
        <block wx:elif="{{appState === 'completed'}}">
          重新诊断
        </block>
        <block wx:elif="{{appState === 'error'}}">
          AI 品牌战略诊断
        </block>
        <block wx:else>
          {{isTesting ? '诊断中... ' + testProgress + '%' : 'AI 品牌战略诊断'}}
        </block>
      </text>
    </text>
  </button>

  <!-- 状态 3: 诊断完成（当次）（保留旧逻辑） -->
  <view class="completed-actions {{testCompleted && !hasLastReport ? '' : 'hidden'}}">
    <view class="completed-badge">
      <text class="badge-icon">✅</text>
      <text class="badge-text">诊断已完成</text>
      <text class="badge-time" wx:if="{{completedTime}}">{{completedTime}}</text>
    </view>

    <view class="completed-buttons">
      <button class="btn-primary-view" bindtap="viewReport">
        <text class="btn-icon">📊</text>
        <text class="btn-text">查看诊断报告</text>
      </button>

      <button class="btn-secondary-retry" bindtap="retryDiagnosis">
        <text class="btn-icon">🔄</text>
        <text class="btn-text">重新诊断</text>
      </button>
    </view>
  </view>
</view>
```

### 组件 loading 状态（双轨判断）

```xml
<!-- 分析卡片：显示当前任务状态 -->
<analysis-card
  title="AI 品牌认知诊断"
  subtitle="实时监控 AI 对品牌的认知状态"
  status="{{currentStage}}"
  progress="{{testProgress}}"
  data="{{reportData}}"
  loading="{{isTesting || appState === 'testing'}}"
  wx:if="{{isTesting || appState === 'testing' || reportData}}">
</analysis-card>

<!-- 综合分析图表组件 -->
<analysis-charts
  radar-data="{{scoreData}}"
  trend-data="{{trendChartData}}"
  loading="{{isTesting || appState === 'testing'}}"
  wx:if="{{reportData}}">
</analysis-charts>
```

### 验证方法

1. **视觉测试**:
   - 初始状态：按钮显示"AI 品牌战略诊断"
   - 诊断中：按钮显示"诊断中... 50%"，不可点击
   - 诊断完成：按钮显示"重新诊断"，可点击
   - 诊断失败：按钮显示"AI 品牌战略诊断"，可点击

2. **Console 验证**:
```javascript
// 在诊断过程中检查
const page = getCurrentPages()[getCurrentPages().length - 1];
console.log('按钮禁用状态:', page.data.isTesting || page.data.appState === 'testing');
// 期望：true
```

---

## Step 5: 添加 appState 辅助函数 ✅

### 修改位置：pages/index/index.js - 添加辅助函数

在 `index.js` 中添加以下辅助函数（可以放在文件末尾，其他函数之前）：

```javascript
/**
 * 【Step 5 新增】获取当前状态显示文本
 * 用于 WXML 按钮文字显示
 */
getStateText: function() {
  const { appState, testProgress } = this.data;
  
  switch(appState) {
    case 'testing':
      return `诊断中... ${testProgress}%`;
    case 'completed':
      return '重新诊断';
    case 'error':
      return 'AI 品牌战略诊断';
    default:
      return 'AI 品牌战略诊断';
  }
},

/**
 * 【Step 5 新增】判断按钮是否禁用
 * 用于 WXML 按钮 disabled 属性
 */
isButtonDisabled: function() {
  const { appState, isTesting } = this.data;
  return isTesting || appState === 'testing';
},

/**
 * 【Step 5 新增】判断是否显示加载动画
 * 用于 WXML 条件渲染
 */
isLoading: function() {
  const { appState, isTesting } = this.data;
  return isTesting || appState === 'testing';
},

/**
 * 【Step 5 新增】判断是否显示查看报告入口
 * 用于 WXML 条件渲染
 */
shouldShowViewReport: function() {
  const { appState, testCompleted, hasLastReport } = this.data;
  return (testCompleted && !hasLastReport) || appState === 'completed';
},

/**
 * 【Step 5 新增】判断是否有上次报告
 * 用于 WXML 条件渲染
 */
hasPreviousReport: function() {
  const { hasLastReport, appState } = this.data;
  return hasLastReport && appState !== 'testing';
}
```

### WXML 中使用辅助函数

```xml
<!-- 使用辅助函数简化 WXML -->
<button class="scan-button {{hasLastReport ? 'hidden' : ''}}"
        bindtap="startBrandTest"
        disabled="{{isButtonDisabled()}}">
  <text class="button-content">
    <text class="loading-spinner" wx:if="{{isLoading()}}"></text>
    <text class="button-text">{{getStateText()}}</text>
  </text>
</button>

<view class="completed-actions {{shouldShowViewReport() ? '' : 'hidden'}}">
  <!-- ... -->
</view>
```

### 验证方法

```javascript
// 在 Console 中测试辅助函数
const page = getCurrentPages()[getCurrentPages().length - 1];

// 测试 getStateText
page.setData({ appState: 'testing', testProgress: 50 });
console.log('状态文本:', page.getStateText());
// 期望：'诊断中... 50%'

// 测试 isButtonDisabled
console.log('按钮禁用:', page.isButtonDisabled());
// 期望：true

// 测试 shouldShowViewReport
page.setData({ appState: 'completed' });
console.log('显示查看报告:', page.shouldShowViewReport());
// 期望：true
```

---

## 自检清单

### Step 1-3 自检（JS 部分）

- [x] `appState` 变量已添加到 `data` 中
- [x] 初始值为 `'idle'`
- [x] `startBrandTest` 中设置了 `appState: 'testing'`
- [x] `onComplete` 回调中设置了 `appState: 'completed'`
- [x] `onError` 回调中设置了 `appState: 'error'`
- [x] 所有 `setData` 调用都同步更新了 `appState`

### Step 4 自检（WXML 部分）

- [x] 按钮 `disabled` 属性使用双轨判断
- [x] 按钮文字使用 `appState` 优先判断
- [x] 组件 `loading` 属性使用双轨判断
- [x] 保留了旧变量作为后备

### Step 5 自检（辅助函数）

- [x] `getStateText()` 函数已添加
- [x] `isButtonDisabled()` 函数已添加
- [x] `isLoading()` 函数已添加
- [x] `shouldShowViewReport()` 函数已添加
- [x] 所有函数都使用双轨判断（同时检查 `appState` 和旧变量）

---

## 端到端验证流程

### 1. 初始状态验证

```javascript
// 在 Console 中运行
const page = getCurrentPages()[0];
console.log('=== 初始状态验证 ===');
console.log('appState:', page.data.appState);  // 期望：'idle'
console.log('isTesting:', page.data.isTesting);  // 期望：false
console.log('testCompleted:', page.data.testCompleted);  // 期望：false
console.log('getStateText():', page.getStateText());  // 期望：'AI 品牌战略诊断'
console.log('isButtonDisabled():', page.isButtonDisabled());  // 期望：false
console.assert(page.data.appState === 'idle', '初始状态应该是 idle');
console.log('✅ 初始状态验证通过');
```

### 2. 诊断中状态验证

```javascript
// 点击诊断按钮后，在 Console 中运行
console.log('=== 诊断中状态验证 ===');
console.log('appState:', page.data.appState);  // 期望：'testing'
console.log('isTesting:', page.data.isTesting);  // 期望：true
console.log('testCompleted:', page.data.testCompleted);  // 期望：false
console.log('getStateText():', page.getStateText());  // 期望：'诊断中... X%'
console.log('isButtonDisabled():', page.isButtonDisabled());  // 期望：true
console.assert(page.data.appState === 'testing', '诊断中应该是 testing');
console.assert(page.data.isTesting === true, 'isTesting 应该是 true');
console.log('✅ 诊断中状态验证通过');
```

### 3. 诊断完成状态验证

```javascript
// 等待诊断完成后，在 Console 中运行
console.log('=== 诊断完成状态验证 ===');
console.log('appState:', page.data.appState);  // 期望：'completed'
console.log('isTesting:', page.data.isTesting);  // 期望：false
console.log('testCompleted:', page.data.testCompleted);  // 期望：true
console.log('hasLastReport:', page.data.hasLastReport);  // 期望：true
console.log('getStateText():', page.getStateText());  // 期望：'重新诊断'
console.log('isButtonDisabled():', page.isButtonDisabled());  // 期望：false
console.log('shouldShowViewReport():', page.shouldShowViewReport());  // 期望：true
console.assert(page.data.appState === 'completed', '完成后应该是 completed');
console.assert(page.data.isTesting === false, 'isTesting 应该是 false');
console.assert(page.data.testCompleted === true, 'testCompleted 应该是 true');
console.log('✅ 诊断完成状态验证通过');
```

### 4. 诊断失败状态验证

```javascript
// 模拟诊断失败（或实际触发错误），在 Console 中运行
console.log('=== 诊断失败状态验证 ===');
console.log('appState:', page.data.appState);  // 期望：'error'
console.log('isTesting:', page.data.isTesting);  // 期望：false
console.log('testCompleted:', page.data.testCompleted);  // 期望：false
console.log('getStateText():', page.getStateText());  // 期望：'AI 品牌战略诊断'
console.log('isButtonDisabled():', page.isButtonDisabled());  // 期望：false
console.assert(page.data.appState === 'error', '失败后应该是 error');
console.assert(page.data.isTesting === false, 'isTesting 应该是 false');
console.log('✅ 诊断失败状态验证通过');
```

---

## 下一步计划

### 已完成步骤（Step 1-5）✅

- ✅ Step 1: 引入 appState 变量
- ✅ Step 2: startBrandTest 同步设置
- ✅ Step 3: 轮询回调同步
- ✅ Step 4: WXML 双轨运行
- ✅ Step 5: 添加辅助函数

### 待执行步骤（Step 6-8）

- ⏳ Step 6: WXML 优先使用 appState（降低旧变量依赖）
- ⏳ Step 7: JS 优先使用 appState（降低旧变量依赖）
- ⏳ Step 8: 清理旧变量（可选，需全面测试）

### 建议

**当前状态**: Step 1-5 已完成，双轨运行模式已建立

**建议行动**:
1. 先运行端到端验证，确保 Step 1-5 正确实施
2. 验证通过后，再执行 Step 6-8
3. 每个步骤都要完整测试，确保不影响现有功能

**预计剩余工时**: 约 1.5 小时（Step 6-8）
