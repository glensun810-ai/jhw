# appState 迁移 - 问题诊断与修复

## 🔍 问题诊断

**当前状态**: 3 项通过，5 项失败

**需要收集的信息**: 请运行以下代码查看详细失败项

```javascript
(function diagnoseFailures() {
  var page = getCurrentPages()[0];
  
  console.log('=== 详细诊断报告 ===');
  console.log('');
  
  // 1. 检查 data 中的 appState
  console.log('1. data 中的 appState:');
  console.log('   page.data.appState =', page.data.appState);
  console.log('   page.data.isTesting =', page.data.isTesting);
  console.log('   page.data.testCompleted =', page.data.testCompleted);
  console.log('   page.data.hasLastReport =', page.data.hasLastReport);
  console.log('');
  
  // 2. 检查辅助函数是否存在
  console.log('2. 辅助函数检查:');
  console.log('   getStateText:', typeof page.getStateText);
  console.log('   isButtonDisabled:', typeof page.isButtonDisabled);
  console.log('   isLoading:', typeof page.isLoading);
  console.log('   shouldShowViewReport:', typeof page.shouldShowViewReport);
  console.log('');
  
  // 3. 尝试调用辅助函数
  console.log('3. 辅助函数调用结果:');
  try {
    if (typeof page.getStateText === 'function') {
      console.log('   getStateText() =', page.getStateText());
    } else {
      console.log('   getStateText 不是函数');
    }
  } catch(e) {
    console.log('   getStateText() 调用失败:', e.message);
  }
  
  try {
    if (typeof page.isButtonDisabled === 'function') {
      console.log('   isButtonDisabled() =', page.isButtonDisabled());
    } else {
      console.log('   isButtonDisabled 不是函数');
    }
  } catch(e) {
    console.log('   isButtonDisabled() 调用失败:', e.message);
  }
  
  try {
    if (typeof page.isLoading === 'function') {
      console.log('   isLoading() =', page.isLoading());
    } else {
      console.log('   isLoading 不是函数');
    }
  } catch(e) {
    console.log('   isLoading() 调用失败:', e.message);
  }
  
  try {
    if (typeof page.shouldShowViewReport === 'function') {
      console.log('   shouldShowViewReport() =', page.shouldShowViewReport());
    } else {
      console.log('   shouldShowViewReport 不是函数');
    }
  } catch(e) {
    console.log('   shouldShowViewReport() 调用失败:', e.message);
  }
  
  console.log('');
  console.log('=== 诊断完成 ===');
})();
```

---

## 🔧 最可能的问题及修复

根据经验，5 项失败很可能是**辅助函数未添加**到 `pages/index/index.js` 中。

### 问题 1: 辅助函数不存在

**症状**: `getStateText`, `isButtonDisabled` 等函数类型为 `undefined`

**修复**: 在 `pages/index/index.js` 的 `Page({...})` 中添加辅助函数

**代码位置**: 在 `Page` 对象内部，其他函数旁边（如 `onLoad`, `startBrandTest` 等同级）

```javascript
Page({
  // ... data, onLoad, onShow 等 ...
  
  // ========== 添加以下辅助函数 ==========
  
  /**
   * 【Step 5 新增】获取当前状态显示文本
   */
  getStateText: function() {
    var appState = this.data.appState;
    var testProgress = this.data.testProgress;
    
    switch(appState) {
      case 'testing':
        return '诊断中... ' + testProgress + '%';
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
   */
  isButtonDisabled: function() {
    var appState = this.data.appState;
    var isTesting = this.data.isTesting;
    return isTesting || appState === 'testing';
  },
  
  /**
   * 【Step 5 新增】判断是否显示加载动画
   */
  isLoading: function() {
    var appState = this.data.appState;
    var isTesting = this.data.isTesting;
    return isTesting || appState === 'testing';
  },
  
  /**
   * 【Step 5 新增】判断是否显示查看报告入口
   */
  shouldShowViewReport: function() {
    var appState = this.data.appState;
    var testCompleted = this.data.testCompleted;
    var hasLastReport = this.data.hasLastReport;
    return (testCompleted && !hasLastReport) || appState === 'completed';
  },
  
  // ========== 辅助函数结束 ==========
  
  // ... 其他函数 ...
})
```

### 问题 2: appState 未正确初始化

**症状**: `appState` 值为 `undefined`

**修复**: 检查 `pages/index/index.js` 的 `data` 对象中是否包含 `appState: 'idle'`

```javascript
Page({
  data: {
    // ... 其他变量 ...
    
    // 【Step 1 新增】统一状态管理
    appState: 'idle',  // ← 确保这行存在
    
    isTesting: false,
    testProgress: 0,
    // ...
  },
  
  // ...
})
```

### 问题 3: appState 未同步设置

**症状**: `appState` 始终为 `'idle'`，不随诊断状态变化

**修复**: 检查 `startBrandTest` 和回调中是否设置了 `appState`

**检查点 1**: `startBrandTest` 函数中
```javascript
startBrandTest: function() {
  // ... 验证逻辑 ...
  
  this.setData({
    isTesting: true,
    testProgress: 0,
    testCompleted: false,
    hasLastReport: false,
    completedTime: null,
    appState: 'testing'  // ← 确保这行存在
  });
  
  // ...
}
```

**检查点 2**: 轮询回调中
```javascript
// onComplete 回调
(parsingStatus) => {
  wx.hideLoading();
  
  this.setData({
    isTesting: false,
    testCompleted: true,
    hasLastReport: true,
    completedTime: this.getCompletedTimeText(),
    appState: 'completed'  // ← 确保这行存在
  });
  
  this.handleDiagnosisComplete(parsedStatus, executionId);
}

// onError 回调
(error) => {
  wx.hideLoading();
  
  this.setData({
    isTesting: false,
    testCompleted: false,
    appState: 'error'  // ← 确保这行存在
  });
  
  this.handleDiagnosisError(error);
}
```

---

## 📋 快速修复步骤

### 步骤 1: 添加辅助函数

打开 `pages/index/index.js`，找到 `Page({...})`，在合适位置（如 `onLoad` 函数之后）添加：

```javascript
/**
 * 【Step 5 新增】辅助函数集合
 */
getStateText: function() {
  var appState = this.data.appState;
  var testProgress = this.data.testProgress;
  
  switch(appState) {
    case 'testing':
      return '诊断中... ' + testProgress + '%';
    case 'completed':
      return '重新诊断';
    case 'error':
      return 'AI 品牌战略诊断';
    default:
      return 'AI 品牌战略诊断';
  }
},

isButtonDisabled: function() {
  return this.data.isTesting || this.data.appState === 'testing';
},

isLoading: function() {
  return this.data.isTesting || this.data.appState === 'testing';
},

shouldShowViewReport: function() {
  return (this.data.testCompleted && !this.data.hasLastReport) || 
         this.data.appState === 'completed';
},
```

### 步骤 2: 保存并刷新

1. 保存 `pages/index/index.js`
2. 在微信开发者工具中点击"编译"刷新页面

### 步骤 3: 重新运行验证脚本

```javascript
(function verifyAll() {
  var page = getCurrentPages()[0];
  if (!page) { console.error('无法获取页面实例'); return; }
  
  var passed = 0, failed = 0;
  
  function check(name, actual, expected) {
    var ok = actual === expected;
    console.log((ok ? '✅' : '❌') + ' ' + name + ': ' + actual + ' (期望：' + expected + ')');
    if (ok) passed++; else failed++;
  }
  
  check('appState', page.data.appState, 'idle');
  check('isTesting', page.data.isTesting, false);
  check('testCompleted', page.data.testCompleted, false);
  check('hasLastReport', page.data.hasLastReport, false);
  
  if (typeof page.getStateText === 'function') {
    check('getStateText()', page.getStateText(), 'AI 品牌战略诊断'); passed++;
  } else { console.log('❌ getStateText 不是函数'); failed++; }
  
  if (typeof page.isButtonDisabled === 'function') {
    check('isButtonDisabled()', page.isButtonDisabled(), false); passed++;
  } else { console.log('❌ isButtonDisabled 不是函数'); failed++; }
  
  if (typeof page.isLoading === 'function') {
    check('isLoading()', page.isLoading(), false); passed++;
  } else { console.log('❌ isLoading 不是函数'); failed++; }
  
  if (typeof page.shouldShowViewReport === 'function') {
    check('shouldShowViewReport()', page.shouldShowViewReport(), false); passed++;
  } else { console.log('❌ shouldShowViewReport 不是函数'); failed++; }
  
  console.log('✅ 通过：' + passed + ' 项，❌ 失败：' + failed + ' 项');
})();
```

---

## 🎯 预期结果

修复后应该看到：
```
✅ appState: idle (期望：idle)
✅ isTesting: false (期望：false)
✅ testCompleted: false (期望：false)
✅ hasLastReport: false (期望：false)
✅ getStateText(): AI 品牌战略诊断 (期望：AI 品牌战略诊断)
✅ isButtonDisabled(): false (期望：false)
✅ isLoading(): false (期望：false)
✅ shouldShowViewReport(): false (期望：false)
✅ 通过：8 项，❌ 失败：0 项
```

---

## 📞 如果仍然失败

请提供以下信息：

1. **详细诊断报告**的输出（运行第一个诊断脚本）
2. **pages/index/index.js** 中 `data` 对象的截图或代码
3. **pages/index/index.js** 中是否已添加辅助函数

我可以进一步帮助定位问题。
