# WXML 编译错误修复报告

**修复日期**: 2026-03-10  
**问题**: WXML 中 class 属性使用了复杂的 JS 表达式  
**状态**: ✅ 已修复  

---

## 问题描述

**错误信息**:
```
Bad attr `class` with message: unexpected `>` at pos18.
  196 | class="action-btn favorite-btn {{favorites.some(f => f.executionId === item.executionId) ? 'favorited' : ''}}"
```

**根本原因**:
- 微信小程序 WXML **不支持在 class 属性中使用复杂 JavaScript 表达式**
- `favorites.some(f => ...)` 箭头函数语法在 WXML 中无法解析
- WXML 只支持简单的数据绑定和三元表达式

---

## 修复方案

### 方案 1: 在 JS 中预处理数据 ✅ (已采用)

**步骤**:
1. 在加载数据时，为每条记录添加 `isFavorited` 字段
2. WXML 中使用简单的 `{{item.isFavorited ? 'favorited' : ''}}`

**JS 代码**:
```javascript
// 在 loadHistory() 中
const favorites = wx.getStorageSync('favorites') || [];

const processedReports = reports.map(report => ({
  ...report,
  // 添加收藏状态标记
  isFavorited: favorites.some(f => 
    f.executionId === (report.execution_id || report.executionId)
  )
}));
```

**WXML 代码**:
```xml
<button 
  class="action-btn favorite-btn {{item.isFavorited ? 'favorited' : ''}}" 
  bindtap="toggleFavorite"
  data-execution-id="{{item.executionId}}"
>
  ★
</button>
```

### 方案 2: 使用多个 class 绑定 ❌ (不推荐)

```xml
<!-- 不推荐：代码复杂，难以维护 -->
<view class="{{classes}}"></view>
```

---

## 修复文件清单

| 文件 | 修复内容 | 状态 |
|-----|---------|------|
| `pages/history/history.js` | 添加 isFavorited 字段、更新收藏状态 | ✅ |
| `pages/history/history.wxml` | 简化 class 表达式 | ✅ |

---

## 修复对比

### 修复前 (❌ 复杂表达式)

```xml
<button 
  class="action-btn favorite-btn {{favorites.some(f => f.executionId === item.executionId) ? 'favorited' : ''}}" 
>
```

### 修复后 (✅ 简单表达式)

```xml
<button 
  class="action-btn favorite-btn {{item.isFavorited ? 'favorited' : ''}}" 
>
```

---

## 相关修复

### 收藏状态同步

**添加收藏时更新列表**:
```javascript
addFavorite: function(executionId, brandName) {
  // ... 添加收藏逻辑
  
  // 更新列表中对应项的收藏状态
  const { historyList } = this.data;
  const updatedList = historyList.map(item => {
    if (item.executionId === executionId) {
      return { ...item, isFavorited: true };
    }
    return item;
  });
  this.setData({ historyList, filteredList: updatedList });
}
```

**移除收藏时更新列表**:
```javascript
removeFavorite: function(executionId) {
  // ... 移除收藏逻辑
  
  // 更新列表中对应项的收藏状态
  const { historyList } = this.data;
  const updatedList = historyList.map(item => {
    if (item.executionId === executionId) {
      return { ...item, isFavorited: false };
    }
    return item;
  });
  this.setData({ historyList, filteredList: updatedList });
}
```

---

## WXML 语法规范

### ✅ 支持的语法

```xml
<!-- 简单数据绑定 -->
<view class="{{className}}"></view>

<!-- 三元表达式 -->
<view class="{{isActive ? 'active' : ''}}"></view>

<!-- 多个 class -->
<view class="base {{extraClass}}"></view>

<!-- 数组形式 (部分基础库支持) -->
<view class="{{['a', 'b']}}"></view>
```

### ❌ 不支持的语法

```xml
<!-- 箭头函数 -->
<view class="{{items.some(i => i.id === 1)}}"></view>

<!-- 复杂对象方法 -->
<view class="{{obj.method()}}"></view>

<!-- 链式调用 -->
<view class="{{array.map(i => i.id).join(' ')}}"></view>
```

---

## 编译测试

**预期结果**:
```
✅ 编译成功
✅ 无 WXML 错误
✅ 无 class 属性错误
```

---

## 最佳实践建议

### 数据预处理原则

1. **在 JS 中处理复杂逻辑**
   - 数据过滤、映射、计算都在 JS 中完成
   - WXML 只做简单展示

2. **为视图准备专用字段**
   - 如 `isFavorited`、`formattedTime`、`scoreLevel`
   - 避免在模板中计算

3. **保持数据同步**
   - 数据变更时，及时更新相关字段
   - 如收藏后更新 `isFavorited`

### 代码组织

```javascript
// ✅ 推荐：在数据处理阶段添加视图字段
processData(rawData) {
  return rawData.map(item => ({
    ...item,
    isFavorited: this.checkFavorite(item.id),
    formattedTime: this.formatTime(item.time),
    scoreLevel: this.calculateLevel(item.score)
  }));
}

// ❌ 不推荐：在模板中计算
// <view class="{{checkFavorite(item.id) ? 'fav' : ''}}"></view>
```

---

**修复完成时间**: 2026-03-10  
**修复人**: 产品架构优化项目组  
**下一步**: 清除缓存，重新编译测试
