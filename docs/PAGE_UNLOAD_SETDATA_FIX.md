# 页面卸载后 setData 错误修复报告

**创建日期**: 2026-03-13  
**问题**: `Cannot read property '__subPageFrameEndTime__' of null`

---

## 问题描述

在微信开发者工具中出现以下错误：

```
TypeError: Cannot read property '__subPageFrameEndTime__' of null
    at t.<anonymous> (<anonymous>:1:1735325)
    at :14853/appservice/<setInterval callback function>
```

**根本原因**:
1. 页面卸载后，`setInterval` 定时器仍在运行
2. 定时器回调中调用 `setData()` 时访问已卸载的页面实例
3. 微信开发者工具的性能监控尝试访问已销毁的页面对象

---

## 解决方案

### 1. 添加页面卸载标志

**文件**: `miniprogram/pages/report-v2/report-v2.js`

**修改内容**:

```javascript
data: {
  // ... 其他数据
  // 【P0 修复 - 2026-03-13】页面卸载标志
  _isPageUnloaded: false
},
```

### 2. 增强 onUnload 清理逻辑

```javascript
onUnload() {
  console.log('[ReportPageV2] onUnload, cleaning up...');
  
  // 标记页面已卸载，防止后续 setData
  this._isPageUnloaded = true;
  
  // 停止所有监听和定时器
  this.stopListening();
  this.stopElapsedTimer();
  
  // 清理可能的延迟回调
  if (this._pendingTimeout) {
    clearTimeout(this._pendingTimeout);
    this._pendingTimeout = null;
  }
  
  console.log('[ReportPageV2] ✅ Cleanup completed');
}
```

**改进点**:
- ✅ 设置页面卸载标志
- ✅ 停止所有监听器
- ✅ 清除所有定时器
- ✅ 清理延迟回调

### 3. 添加安全的 setData 方法

```javascript
/**
 * 【P0 修复 - 2026-03-13】安全的 setData 方法
 * 防止在页面卸载后调用 setData
 * @param {Object} data 要设置的数据
 * @param {Function} callback 回调函数
 */
safeSetData(data, callback) {
  if (this._isPageUnloaded) {
    console.warn('[ReportPageV2] ⚠️ 页面已卸载，跳过 setData');
    if (callback) callback();
    return;
  }
  
  this.setData(data, callback);
}
```

**使用方式**:
```javascript
// 在定时器回调中使用
this.safeSetData({
  elapsedTime: this.data.elapsedTime + 1
});
```

### 4. 增强定时器安全检查

```javascript
startElapsedTimer() {
  this.stopElapsedTimer();

  this.elapsedTimer = setInterval(() => {
    // 安全检查：页面已卸载则停止计时器
    if (this._isPageUnloaded) {
      this.stopElapsedTimer();
      return;
    }
    
    this.setData({
      elapsedTime: this.data.elapsedTime + 1
    });
  }, 1000);
}
```

---

## 错误说明

### __subPageFrameEndTime__ 错误

这是微信开发者工具的内部性能监控错误，通常发生在以下场景：

1. **页面卸载后定时器仍在运行**
   - `setInterval` 或 `setTimeout` 未正确清理
   - 回调函数尝试访问页面实例

2. **异步操作完成后访问已销毁的页面**
   - Promise 回调
   - 网络请求回调
   - 事件监听器

3. **微信开发者工具性能监控 bug**
   - 工具尝试访问已销毁页面的性能指标
   - 通常是误报，不影响实际功能

### 影响评估

| 错误类型 | 影响范围 | 严重程度 |
|----------|----------|----------|
| setData 在卸载后调用 | 控制台错误，可能内存泄漏 | ⚠️ 中等 |
| __subPageFrameEndTime__ | 仅开发者工具，不影响真机 | ✅ 低 |
| 定时器未清理 | 内存泄漏，性能问题 | ⚠️ 中等 |

---

## 最佳实践

### 1. 页面生命周期管理

```javascript
Page({
  data: {
    _isPageUnloaded: false
  },
  
  onUnload() {
    this._isPageUnloaded = true;
    this._cleanupAllTimers();
    this._cleanupAllListeners();
  },
  
  _cleanupAllTimers() {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }
    if (this._timeout) {
      clearTimeout(this._timeout);
      this._timeout = null;
    }
  },
  
  _cleanupAllListeners() {
    // 移除所有事件监听器
  }
});
```

### 2. 安全的异步操作

```javascript
// ❌ 不安全
async fetchData() {
  const data = await api.call();
  this.setData({ data });  // 页面可能已卸载
}

// ✅ 安全
async fetchData() {
  const data = await api.call();
  if (!this._isPageUnloaded) {
    this.setData({ data });
  }
}
```

### 3. 定时器管理

```javascript
// ❌ 不安全
startTimer() {
  setInterval(() => {
    this.setData({ count: this.data.count + 1 });
  }, 1000);
}

// ✅ 安全
startTimer() {
  this._timer = setInterval(() => {
    if (this._isPageUnloaded) {
      clearInterval(this._timer);
      return;
    }
    this.setData({ count: this.data.count + 1 });
  }, 1000);
}

onUnload() {
  if (this._timer) {
    clearInterval(this._timer);
    this._timer = null;
  }
}
```

---

## 测试验证

### 1. 单元测试

```javascript
// test/reportPage.test.js

test('should cleanup timers on unload', () => {
  const page = createPage();
  
  // 启动定时器
  page.startElapsedTimer();
  expect(page.elapsedTimer).toBeTruthy();
  
  // 模拟页面卸载
  page.onUnload();
  
  // 验证定时器已清理
  expect(page.elapsedTimer).toBeNull();
  expect(page._isPageUnloaded).toBe(true);
});

test('should not setData after unload', () => {
  const page = createPage();
  
  // 模拟页面卸载
  page.onUnload();
  
  // 验证 setData 被跳过
  const warnSpy = jest.spyOn(console, 'warn');
  page.safeSetData({ test: 'value' });
  expect(warnSpy).toHaveBeenCalledWith(
    expect.stringContaining('页面已卸载')
  );
});
```

### 2. 手动测试步骤

1. **打开报告页面**
   ```
   导航至 /pages/report-v2/report-v2?executionId=xxx
   ```

2. **等待数据加载**
   - 观察进度条
   - 等待数据展示

3. **快速离开页面**
   - 在数据加载过程中点击返回
   - 或在轮询期间关闭页面

4. **检查控制台**
   - 应看到 `[ReportPageV2] ✅ Cleanup completed`
   - 不应看到 `__subPageFrameEndTime__` 错误

5. **重复测试**
   - 多次打开/关闭页面
   - 验证无内存泄漏

---

## 相关文件

### 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `miniprogram/pages/report-v2/report-v2.js` | 添加页面卸载标志和安全检查 |

### 新增的方法

| 方法 | 用途 |
|------|------|
| `safeSetData(data, callback)` | 安全的 setData 包装方法 |

### 增强的方法

| 方法 | 增强内容 |
|------|----------|
| `onUnload()` | 添加清理逻辑和卸载标志 |
| `startElapsedTimer()` | 添加卸载检查 |

---

## 性能优化建议

### 1. 使用防抖和节流

```javascript
// 防抖：避免频繁 setData
debounceSetData(data, delay = 300) {
  if (this._debounceTimer) {
    clearTimeout(this._debounceTimer);
  }
  
  this._debounceTimer = setTimeout(() => {
    this.safeSetData(data);
  }, delay);
}
```

### 2. 批量更新

```javascript
// 批量 setData 调用
batchSetData(updates) {
  if (this._isPageUnloaded) return;
  
  // 合并多个更新
  this.setData({
    ...this.data,
    ...updates
  });
}
```

### 3. 避免大数据量更新

```javascript
// ❌ 避免：更新整个大对象
this.setData({ largeObject: newData });

// ✅ 推荐：只更新变化的字段
this.setData({
  'largeObject.field1': newData.field1,
  'largeObject.field2': newData.field2
});
```

---

## 总结

### 修复内容

1. ✅ 添加页面卸载标志 `_isPageUnloaded`
2. ✅ 增强 `onUnload()` 清理逻辑
3. ✅ 实现 `safeSetData()` 安全方法
4. ✅ 增强定时器安全检查

### 影响范围

- **前端文件**: `miniprogram/pages/report-v2/report-v2.js`
- **影响页面**: 报告页面、历史记录页面

### 预期效果

- ✅ 消除 `__subPageFrameEndTime__` 错误
- ✅ 防止页面卸载后的 setData 调用
- ✅ 改善内存管理
- ✅ 提升用户体验

### 部署步骤

1. 保存修改的文件
2. 编译小程序
3. 在微信开发者工具中测试
4. 验证错误已消除

---

**文档版本**: 1.0  
**最后更新**: 2026-03-13  
**维护者**: 首席全栈工程师
