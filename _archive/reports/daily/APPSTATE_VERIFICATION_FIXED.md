# appState 迁移 - 验证脚本（修复版）

## 🐛 问题定位

**错误**: `Uncaught SyntaxError: Identifier 'page' has already been declared`

**根因**: 在微信开发者工具 Console 中多次运行脚本时，`const page` 会重复声明导致报错。

**解决方案**: 
1. 使用 IIFE（立即执行函数表达式）包裹代码
2. 使用 `var` 代替 `const`（函数作用域，允许重复声明）
3. 或者先清除变量再声明

---

## ✅ 修复后的验证脚本

### 方法 1: 使用 var 声明（推荐）

```javascript
// ===== 验证脚本 1: 初始状态检查（修复版）=====
(function() {
  console.log('=== 验证 1: 初始状态检查 ===');
  
  var page = getCurrentPages()[0];
  
  if (!page) {
    console.error('❌ 无法获取页面实例');
    return;
  }
  
  var checks = [
    { name: 'appState', actual: page.data.appState, expected: 'idle' },
    { name: 'isTesting', actual: page.data.isTesting, expected: false },
    { name: 'testCompleted', actual: page.data.testCompleted, expected: false },
    { name: 'hasLastReport', actual: page.data.hasLastReport, expected: false }
  ];
  
  var allPassed = true;
  checks.forEach(function(check) {
    var passed = check.actual === check.expected;
    console.log((passed ? '✅' : '❌') + ' ' + check.name + ': ' + check.actual + ' (期望：' + check.expected + ')');
    if (!passed) allPassed = false;
  });
  
  // 测试辅助函数
  if (typeof page.getStateText === 'function') {
    var stateText = page.getStateText();
    console.log('✅ getStateText(): ' + stateText);
  } else {
    console.error('❌ getStateText() 函数不存在');
    allPassed = false;
  }
  
  if (typeof page.isButtonDisabled === 'function') {
    var disabled = page.isButtonDisabled();
    console.log('✅ isButtonDisabled(): ' + disabled);
  } else {
    console.error('❌ isButtonDisabled() 函数不存在');
    allPassed = false;
  }
  
  console.log(allPassed ? '✅ 初始状态验证通过' : '❌ 初始状态验证失败');
  console.log('');
})();
```

### 方法 2: 使用 delete 清除变量（备选）

```javascript
// 如果仍然报错，先执行这行清除变量
try { delete page; } catch(e) {}

// 然后再运行原脚本
var page = getCurrentPages()[0];
// ... 后续代码
```

### 方法 3: 完全隔离的验证脚本（最安全）

```javascript
// ===== 完整验证脚本（一次性运行所有检查）=====
(function verifyAll() {
  console.log('╔════════════════════════════════════════╗');
  console.log('║   appState 迁移 - 完整验证脚本         ║');
  console.log('╚════════════════════════════════════════╝');
  console.log('');
  
  var page = getCurrentPages()[0];
  if (!page) {
    console.error('❌ 无法获取页面实例');
    return;
  }
  
  var report = {
    passed: 0,
    failed: 0,
    items: []
  };
  
  function check(name, actual, expected) {
    var passed = actual === expected;
    report.items.push({ name: name, passed: passed, actual: actual, expected: expected });
    if (passed) report.passed++;
    else report.failed++;
    console.log((passed ? '✅' : '❌') + ' ' + name + ': ' + actual + ' (期望：' + expected + ')');
  }
  
  // ========== 初始状态检查 ==========
  console.log('━━━ 初始状态检查 ━━━');
  check('appState', page.data.appState, 'idle');
  check('isTesting', page.data.isTesting, false);
  check('testCompleted', page.data.testCompleted, false);
  check('hasLastReport', page.data.hasLastReport, false);
  
  // ========== 辅助函数检查 ==========
  console.log('━━━ 辅助函数检查 ━━━');
  
  if (typeof page.getStateText === 'function') {
    var stateText = page.getStateText();
    check('getStateText()', stateText, 'AI 品牌战略诊断');
  } else {
    check('getStateText 存在', false, true);
  }
  
  if (typeof page.isButtonDisabled === 'function') {
    var disabled = page.isButtonDisabled();
    check('isButtonDisabled()', disabled, false);
  } else {
    check('isButtonDisabled 存在', false, true);
  }
  
  if (typeof page.isLoading === 'function') {
    var loading = page.isLoading();
    check('isLoading()', loading, false);
  } else {
    check('isLoading 存在', false, true);
  }
  
  if (typeof page.shouldShowViewReport === 'function') {
    var showReport = page.shouldShowViewReport();
    check('shouldShowViewReport()', showReport, false);
  } else {
    check('shouldShowViewReport 存在', false, true);
  }
  
  // ========== 状态一致性检查 ==========
  console.log('━━━ 状态一致性检查 ━━━');
  
  var appState = page.data.appState;
  var isTesting = page.data.isTesting;
  var testCompleted = page.data.testCompleted;
  
  check(
    'appState=idle 时 isTesting=false',
    appState === 'idle' ? !isTesting : true,
    true
  );
  
  check(
    'appState=testing 时 isTesting=true',
    appState === 'testing' ? isTesting : true,
    true
  );
  
  check(
    'appState=completed 时 testCompleted=true',
    appState === 'completed' ? testCompleted : true,
    true
  );
  
  check(
    'appState=error 时 isTesting=false',
    appState === 'error' ? !isTesting : true,
    true
  );
  
  // ========== 汇总报告 ==========
  console.log('');
  console.log('╔════════════════════════════════════════╗');
  console.log('║           验证结果汇总                 ║');
  console.log('╚════════════════════════════════════════╝');
  console.log('✅ 通过：' + report.passed + ' 项');
  console.log('❌ 失败：' + report.failed + ' 项');
  console.log('');
  
  if (report.failed === 0) {
    console.log('🎉 所有验证通过！appState 迁移成功！');
  } else {
    console.log('⚠️  有 ' + report.failed + ' 项验证失败，请检查代码');
  }
  
  // 返回报告对象，方便在 Console 中查看
  console.log('验证报告对象:', report);
  return report;
})();
```

---

## 📋 使用指南

### 步骤 1: 复制完整验证脚本

复制上面的 **方法 3: 完全隔离的验证脚本** 全部代码。

### 步骤 2: 在微信开发者工具中运行

1. 打开微信开发者工具
2. 切换到 **Console** 标签
3. 粘贴完整脚本
4. 按 Enter 运行

### 步骤 3: 查看结果

**期望输出**（初始状态）:
```
╔════════════════════════════════════════╗
║   appState 迁移 - 完整验证脚本         ║
╚════════════════════════════════════════╝

━━━ 初始状态检查 ━━━
✅ appState: idle (期望：idle)
✅ isTesting: false (期望：false)
✅ testCompleted: false (期望：false)
✅ hasLastReport: false (期望：false)
━━━ 辅助函数检查 ━━━
✅ getStateText(): AI 品牌战略诊断 (期望：AI 品牌战略诊断)
✅ isButtonDisabled(): false (期望：false)
✅ isLoading(): false (期望：false)
✅ shouldShowViewReport(): false (期望：false)
━━━ 状态一致性检查 ━━━
✅ appState=idle 时 isTesting=false: true (期望：true)
✅ appState=testing 时 isTesting=true: true (期望：true)
✅ appState=completed 时 testCompleted=true: true (期望：true)
✅ appState=error 时 isTesting=false: true (期望：true)

╔════════════════════════════════════════╗
║           验证结果汇总                 ║
╚════════════════════════════════════════╝
✅ 通过：12 项
❌ 失败：0 项

🎉 所有验证通过！appState 迁移成功！
验证报告对象：{passed: 12, failed: 0, items: [...]}
```

---

## 🔧 如果仍然报错

### 错误 1: `getCurrentPages is not defined`

**原因**: 不在小程序上下文中运行

**解决**: 
1. 确保在微信开发者工具中运行
2. 确保已经打开了首页

### 错误 2: `无法获取页面实例`

**原因**: 页面未加载完成

**解决**:
```javascript
// 等待 1 秒后重试
setTimeout(function() {
  var page = getCurrentPages()[0];
  console.log('页面实例:', page);
}, 1000);
```

### 错误 3: `page.getStateText is not a function`

**原因**: 辅助函数未正确添加到 Page 中

**解决**: 检查 `pages/index/index.js` 中是否添加了以下代码：
```javascript
Page({
  // ...
  
  getStateText: function() {
    // ...
  },
  
  isButtonDisabled: function() {
    // ...
  },
  
  // ...
})
```

---

## 📊 验证结果记录表

运行验证脚本后，填写以下表格：

| 验证项 | 期望值 | 实际值 | 状态 |
|--------|--------|--------|------|
| appState | 'idle' | | ⏳ |
| isTesting | false | | ⏳ |
| testCompleted | false | | ⏳ |
| hasLastReport | false | | ⏳ |
| getStateText() | 'AI 品牌战略诊断' | | ⏳ |
| isButtonDisabled() | false | | ⏳ |
| isLoading() | false | | ⏳ |
| shouldShowViewReport() | false | | ⏳ |

**验证结果**: ⏳ 待验证 / ✅ 通过 / ❌ 失败

---

## 🚨 常见问题排查

### Q1: 辅助函数不存在

**症状**: `getStateText is not a function`

**排查步骤**:
1. 检查 `pages/index/index.js` 中是否添加了辅助函数
2. 确保函数在 `Page({...})` 对象内部
3. 确保函数名拼写正确

**修复代码位置**:
```javascript
// pages/index/index.js - 文件中部或末尾
Page({
  // ... 其他代码 ...
  
  /**
   * 【Step 5 新增】获取当前状态显示文本
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
  
  // ... 其他辅助函数 ...
})
```

### Q2: appState 值不正确

**症状**: `appState` 不是 `'idle'`

**排查步骤**:
1. 检查 `data` 中是否设置了 `appState: 'idle'`
2. 检查是否有其他地方修改了 `appState`
3. 刷新页面重新测试

### Q3: 状态不一致

**症状**: `appState='testing'` 但 `isTesting=false`

**排查步骤**:
1. 检查 `startBrandTest` 中是否同时设置了 `isTesting: true` 和 `appState: 'testing'`
2. 检查 `setData` 调用是否完整
3. 查看 Console 日志确认状态流转

---

**验证脚本版本**: v1.1 (修复版)  
**最后更新**: 2026-02-28  
**兼容性**: 微信开发者工具 v2.01+
