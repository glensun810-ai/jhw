# appState 迁移 - 自检与验证报告

## 📋 实施状态总结

| 步骤 | 内容 | 状态 | 验证结果 |
|------|------|------|----------|
| Step 1 | 引入 appState 变量 | ✅ 已完成 | 待验证 |
| Step 2 | startBrandTest 同步设置 | ✅ 已完成 | 待验证 |
| Step 3 | 轮询回调同步 | ✅ 已完成 | 待验证 |
| Step 4 | WXML 双轨运行 | ✅ 已完成 | 待验证 |
| Step 5 | 添加辅助函数 | ✅ 已完成 | 待验证 |
| Step 6 | WXML 优先使用 appState | ⏳ 待执行 | - |
| Step 7 | JS 优先使用 appState | ⏳ 待执行 | - |
| Step 8 | 清理旧变量 | ⏳ 待执行 | - |

---

## 🔍 自检清单

### 代码存在性检查

#### 1. index.js 检查项

- [ ] `data` 对象中包含 `appState: 'idle'`
- [ ] `startBrandTest` 函数中设置了 `appState: 'testing'`
- [ ] `onComplete` 回调中设置了 `appState: 'completed'`
- [ ] `onError` 回调中设置了 `appState: 'error'`
- [ ] 包含 `getStateText()` 辅助函数
- [ ] 包含 `isButtonDisabled()` 辅助函数
- [ ] 包含 `isLoading()` 辅助函数
- [ ] 包含 `shouldShowViewReport()` 辅助函数

#### 2. index.wxml 检查项

- [ ] 按钮 `disabled` 属性包含 `appState === 'testing'` 判断
- [ ] 按钮文字包含 `appState` 条件判断
- [ ] 组件 `loading` 属性包含 `appState === 'testing'` 判断
- [ ] 保留了旧变量作为后备（双轨运行）

---

## 🧪 验证脚本

### 方法 1: 微信开发者工具 Console 验证

在微信开发者工具的 Console 中依次运行以下代码：

```javascript
// ===== 验证脚本 1: 初始状态检查 =====
(function verifyInitialState() {
  console.log('=== 验证 1: 初始状态检查 ===');
  const page = getCurrentPages()[0];
  
  if (!page) {
    console.error('❌ 无法获取页面实例');
    return;
  }
  
  const checks = [
    { name: 'appState', actual: page.data.appState, expected: 'idle' },
    { name: 'isTesting', actual: page.data.isTesting, expected: false },
    { name: 'testCompleted', actual: page.data.testCompleted, expected: false },
    { name: 'hasLastReport', actual: page.data.hasLastReport, expected: false }
  ];
  
  let allPassed = true;
  checks.forEach(check => {
    const passed = check.actual === check.expected;
    console.log(`${passed ? '✅' : '❌'} ${check.name}: ${check.actual} (期望：${check.expected})`);
    if (!passed) allPassed = false;
  });
  
  // 测试辅助函数
  if (typeof page.getStateText === 'function') {
    const stateText = page.getStateText();
    console.log(`✅ getStateText(): ${stateText}`);
  } else {
    console.error('❌ getStateText() 函数不存在');
    allPassed = false;
  }
  
  if (typeof page.isButtonDisabled === 'function') {
    const disabled = page.isButtonDisabled();
    console.log(`✅ isButtonDisabled(): ${disabled}`);
  } else {
    console.error('❌ isButtonDisabled() 函数不存在');
    allPassed = false;
  }
  
  console.log(allPassed ? '✅ 初始状态验证通过' : '❌ 初始状态验证失败');
  console.log('');
})();

// ===== 验证脚本 2: 诊断中状态检查（需要点击诊断按钮后运行） =====
(function verifyTestingState() {
  console.log('=== 验证 2: 诊断中状态检查 ===');
  console.log('⚠️ 请先点击"AI 品牌战略诊断"按钮，然后运行此脚本');
  
  const page = getCurrentPages()[0];
  
  if (!page) {
    console.error('❌ 无法获取页面实例');
    return;
  }
  
  const checks = [
    { name: 'appState', actual: page.data.appState, expected: 'testing' },
    { name: 'isTesting', actual: page.data.isTesting, expected: true },
    { name: 'testCompleted', actual: page.data.testCompleted, expected: false },
    { name: 'testProgress > 0', actual: page.data.testProgress > 0, expected: true }
  ];
  
  let allPassed = true;
  checks.forEach(check => {
    const passed = check.actual === check.expected;
    console.log(`${passed ? '✅' : '❌'} ${check.name}: ${check.actual} (期望：${check.expected})`);
    if (!passed) allPassed = false;
  });
  
  if (typeof page.getStateText === 'function') {
    const stateText = page.getStateText();
    const hasProgress = stateText.includes('诊断中') && stateText.includes('%');
    console.log(`${hasProgress ? '✅' : '❌'} getStateText(): ${stateText}`);
  }
  
  if (typeof page.isButtonDisabled === 'function') {
    const disabled = page.isButtonDisabled();
    console.log(`${disabled ? '✅' : '❌'} isButtonDisabled(): ${disabled} (期望：true)`);
  }
  
  console.log(allPassed ? '✅ 诊断中状态验证通过' : '❌ 诊断中状态验证失败');
  console.log('');
})();

// ===== 验证脚本 3: 诊断完成状态检查（需等待诊断完成后运行） =====
(function verifyCompletedState() {
  console.log('=== 验证 3: 诊断完成状态检查 ===');
  console.log('⚠️ 请等待诊断完成后运行此脚本');
  
  const page = getCurrentPages()[0];
  
  if (!page) {
    console.error('❌ 无法获取页面实例');
    return;
  }
  
  const checks = [
    { name: 'appState', actual: page.data.appState, expected: 'completed' },
    { name: 'isTesting', actual: page.data.isTesting, expected: false },
    { name: 'testCompleted', actual: page.data.testCompleted, expected: true },
    { name: 'hasLastReport', actual: page.data.hasLastReport, expected: true }
  ];
  
  let allPassed = true;
  checks.forEach(check => {
    const passed = check.actual === check.expected;
    console.log(`${passed ? '✅' : '❌'} ${check.name}: ${check.actual} (期望：${check.expected})`);
    if (!passed) allPassed = false;
  });
  
  if (typeof page.getStateText === 'function') {
    const stateText = page.getStateText();
    console.log(`${stateText === '重新诊断' ? '✅' : '❌'} getStateText(): ${stateText} (期望：重新诊断)`);
  }
  
  if (typeof page.shouldShowViewReport === 'function') {
    const showReport = page.shouldShowViewReport();
    console.log(`${showReport ? '✅' : '❌'} shouldShowViewReport(): ${showReport} (期望：true)`);
  }
  
  console.log(allPassed ? '✅ 诊断完成状态验证通过' : '❌ 诊断完成状态验证失败');
  console.log('');
})();

// ===== 验证脚本 4: 状态流转一致性检查 =====
(function verifyStateTransition() {
  console.log('=== 验证 4: 状态流转一致性检查 ===');
  
  const page = getCurrentPages()[0];
  if (!page) {
    console.error('❌ 无法获取页面实例');
    return;
  }
  
  const { appState, isTesting, testCompleted, hasLastReport } = page.data;
  
  // 检查状态一致性
  const consistencyChecks = [
    {
      name: 'appState=idling 时 isTesting=false',
      passed: appState === 'idle' ? !isTesting : true
    },
    {
      name: 'appState=testing 时 isTesting=true',
      passed: appState === 'testing' ? isTesting : true
    },
    {
      name: 'appState=completed 时 testCompleted=true',
      passed: appState === 'completed' ? testCompleted : true
    },
    {
      name: 'appState=error 时 isTesting=false',
      passed: appState === 'error' ? !isTesting : true
    },
    {
      name: 'appState=error 时 testCompleted=false',
      passed: appState === 'error' ? !testCompleted : true
    }
  ];
  
  let allPassed = true;
  consistencyChecks.forEach(check => {
    console.log(`${check.passed ? '✅' : '❌'} ${check.name}`);
    if (!check.passed) allPassed = false;
  });
  
  console.log(allPassed ? '✅ 状态流转一致性验证通过' : '❌ 状态流转一致性验证失败');
  console.log('');
})();

// ===== 验证脚本 5: WXML 双轨运行检查 =====
(function verifyDualTrack() {
  console.log('=== 验证 5: WXML 双轨运行检查 ===');
  
  const page = getCurrentPages()[0];
  if (!page) {
    console.error('❌ 无法获取页面实例');
    return;
  }
  
  const { appState, isTesting, testCompleted } = page.data;
  
  // 检查双轨判断是否正确
  console.log('当前状态:', { appState, isTesting, testCompleted });
  
  // 按钮禁用状态
  const buttonDisabled = isTesting || appState === 'testing';
  console.log(`按钮禁用判断：${buttonDisabled} (isTesting=${isTesting} || appState==='testing'=${appState === 'testing'})`);
  
  // 加载状态
  const isLoading = isTesting || appState === 'testing';
  console.log(`加载状态判断：${isLoading}`);
  
  // 查看报告入口
  const showViewReport = (testCompleted && !page.data.hasLastReport) || appState === 'completed';
  console.log(`查看报告入口：${showViewReport}`);
  
  console.log('✅ 双轨运行检查完成');
  console.log('');
})();
```

---

### 方法 2: 自动化测试脚本

创建测试文件 `tests/appState_migration.test.js`:

```javascript
/**
 * appState 迁移自动化测试
 * 运行：npm test -- tests/appState_migration.test.js
 */

const assert = require('assert');

// 模拟 Page 实例
const mockPage = {
  data: {
    appState: 'idle',
    isTesting: false,
    testProgress: 0,
    testCompleted: false,
    hasLastReport: false
  },
  
  setData: function(newData) {
    Object.assign(this.data, newData);
  },
  
  // 辅助函数
  getStateText: function() {
    const { appState, testProgress } = this.data;
    switch(appState) {
      case 'testing': return `诊断中... ${testProgress}%`;
      case 'completed': return '重新诊断';
      case 'error': return 'AI 品牌战略诊断';
      default: return 'AI 品牌战略诊断';
    }
  },
  
  isButtonDisabled: function() {
    const { appState, isTesting } = this.data;
    return isTesting || appState === 'testing';
  },
  
  isLoading: function() {
    const { appState, isTesting } = this.data;
    return isTesting || appState === 'testing';
  },
  
  shouldShowViewReport: function() {
    const { appState, testCompleted, hasLastReport } = this.data;
    return (testCompleted && !hasLastReport) || appState === 'completed';
  }
};

// 测试用例
describe('appState 迁移测试', () => {
  
  describe('初始状态', () => {
    it('应该是 idle 状态', () => {
      assert.strictEqual(mockPage.data.appState, 'idle');
      assert.strictEqual(mockPage.data.isTesting, false);
      assert.strictEqual(mockPage.data.testCompleted, false);
    });
    
    it('辅助函数应该返回正确文本', () => {
      assert.strictEqual(mockPage.getStateText(), 'AI 品牌战略诊断');
      assert.strictEqual(mockPage.isButtonDisabled(), false);
      assert.strictEqual(mockPage.isLoading(), false);
      assert.strictEqual(mockPage.shouldShowViewReport(), false);
    });
  });
  
  describe('诊断中状态', () => {
    before(() => {
      mockPage.setData({
        appState: 'testing',
        isTesting: true,
        testProgress: 50
      });
    });
    
    it('应该是 testing 状态', () => {
      assert.strictEqual(mockPage.data.appState, 'testing');
      assert.strictEqual(mockPage.data.isTesting, true);
    });
    
    it('辅助函数应该返回正确文本', () => {
      assert.strictEqual(mockPage.getStateText(), '诊断中... 50%');
      assert.strictEqual(mockPage.isButtonDisabled(), true);
      assert.strictEqual(mockPage.isLoading(), true);
      assert.strictEqual(mockPage.shouldShowViewReport(), false);
    });
  });
  
  describe('诊断完成状态', () => {
    before(() => {
      mockPage.setData({
        appState: 'completed',
        isTesting: false,
        testCompleted: true,
        hasLastReport: true
      });
    });
    
    it('应该是 completed 状态', () => {
      assert.strictEqual(mockPage.data.appState, 'completed');
      assert.strictEqual(mockPage.data.isTesting, false);
      assert.strictEqual(mockPage.data.testCompleted, true);
    });
    
    it('辅助函数应该返回正确文本', () => {
      assert.strictEqual(mockPage.getStateText(), '重新诊断');
      assert.strictEqual(mockPage.isButtonDisabled(), false);
      assert.strictEqual(mockPage.isLoading(), false);
      assert.strictEqual(mockPage.shouldShowViewReport(), true);
    });
  });
  
  describe('诊断失败状态', () => {
    before(() => {
      mockPage.setData({
        appState: 'error',
        isTesting: false,
        testCompleted: false
      });
    });
    
    it('应该是 error 状态', () => {
      assert.strictEqual(mockPage.data.appState, 'error');
      assert.strictEqual(mockPage.data.isTesting, false);
    });
    
    it('辅助函数应该返回正确文本', () => {
      assert.strictEqual(mockPage.getStateText(), 'AI 品牌战略诊断');
      assert.strictEqual(mockPage.isButtonDisabled(), false);
      assert.strictEqual(mockPage.isLoading(), false);
      assert.strictEqual(mockPage.shouldShowViewReport(), false);
    });
  });
  
  describe('状态一致性检查', () => {
    it('appState=idle 时 isTesting 应该为 false', () => {
      mockPage.setData({ appState: 'idle', isTesting: false });
      assert.strictEqual(mockPage.data.appState === 'idle' ? !mockPage.data.isTesting : true, true);
    });
    
    it('appState=testing 时 isTesting 应该为 true', () => {
      mockPage.setData({ appState: 'testing', isTesting: true });
      assert.strictEqual(mockPage.data.appState === 'testing' ? mockPage.data.isTesting : true, true);
    });
    
    it('appState=completed 时 testCompleted 应该为 true', () => {
      mockPage.setData({ appState: 'completed', testCompleted: true });
      assert.strictEqual(mockPage.data.appState === 'completed' ? mockPage.data.testCompleted : true, true);
    });
    
    it('appState=error 时 isTesting 应该为 false', () => {
      mockPage.setData({ appState: 'error', isTesting: false });
      assert.strictEqual(mockPage.data.appState === 'error' ? !mockPage.data.isTesting : true, true);
    });
  });
});
```

---

## 📊 验证结果记录

### 验证时间

- 验证执行人：___________
- 验证时间：2026-02-28
- 验证环境：微信开发者工具 v____

### 验证结果

| 验证项 | 状态 | 备注 |
|--------|------|------|
| 初始状态检查 | ⏳ 待验证 | |
| 诊断中状态检查 | ⏳ 待验证 | |
| 诊断完成状态检查 | ⏳ 待验证 | |
| 诊断失败状态检查 | ⏳ 待验证 | |
| 状态流转一致性 | ⏳ 待验证 | |
| WXML 双轨运行 | ⏳ 待验证 | |
| 辅助函数功能 | ⏳ 待验证 | |

### 问题记录

| 编号 | 问题描述 | 严重程度 | 修复状态 |
|------|----------|----------|----------|
| 1 | | 🔴 高 / 🟡 中 / 🟢 低 | ⏳ 待修复 / ✅ 已修复 |

---

## ✅ 完成标准

所有以下条件必须满足才能标记为完成：

- [x] Step 1-5 代码已实施
- [ ] 所有验证脚本运行通过
- [ ] 无 🔴 高优先级问题
- [ ] 所有 🟡 中优先级问题已修复或有修复计划
- [ ] 端到端测试通过（完整诊断流程）

---

## 🚦 下一步行动

1. **立即行动**: 运行验证脚本，记录结果
2. **问题修复**: 修复验证中发现的问题
3. **继续迁移**: 验证通过后执行 Step 6-8
4. **文档更新**: 更新迁移状态文档

---

**验证报告生成时间**: 2026-02-28  
**下次验证时间**: 完成 Step 6-8 后
