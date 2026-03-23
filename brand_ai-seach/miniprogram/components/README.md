# 品牌洞察报告模块 - 可复用组件文档

**文档版本**: v1.0  
**创建日期**: 2026-03-08  
**最后更新**: 2026-03-08

---

## 目录

1. [组件列表](#组件列表)
2. [quality-indicator 组件](#quality-indicator-组件)
3. [error-display 组件](#error-display-组件)
4. [使用指南](#使用指南)
5. [最佳实践](#最佳实践)

---

## 组件列表

| 组件名称 | 描述 | 版本 | 状态 |
|----------|------|------|------|
| quality-indicator | 质量指示器，显示报告质量评分和等级 | 1.0.0 | ✅ 已发布 |
| error-display | 错误显示器，显示错误信息和操作建议 | 1.0.0 | ✅ 已发布 |
| brand-distribution | 品牌分布图表 | 1.0.0 | ✅ 已发布 |
| sentiment-chart | 情感分布图表 | 1.0.0 | ✅ 已发布 |
| keyword-cloud | 关键词云 | 1.0.0 | ✅ 已发布 |
| skeleton | 骨架屏 | 1.0.0 | ✅ 已发布 |

---

## quality-indicator 组件

### 功能描述

显示报告质量评分和等级，支持点击交互和详细信息展示。

### 属性列表

| 属性名 | 类型 | 默认值 | 必填 | 描述 |
|--------|------|--------|------|------|
| quality-score | Number | 0 | 是 | 质量评分 (0-100) |
| quality-level | Object | null | 否 | 质量等级信息（包含 level、label、color、description、recommendation） |
| show-detail | Boolean | false | 否 | 是否显示详细信息 |
| clickable | Boolean | true | 否 | 是否可点击 |
| custom-class | String | '' | 否 | 自定义样式类名 |

### 事件列表

| 事件名 | 参数 | 描述 |
|--------|------|------|
| bind:qualityClick | `{score, level}` | 点击质量指示器时触发 |
| bind:viewDetail | `{score, level}` | 点击查看详情时触发 |

### 使用示例

```xml
<!-- 基础用法 -->
<quality-indicator 
  quality-score="{{85}}" 
/>

<!-- 带等级信息 -->
<quality-indicator 
  quality-score="{{qualityScore}}" 
  quality-level="{{qualityLevel}}"
  show-detail="{{true}}"
  bind:qualityClick="handleQualityClick"
/>

<!-- 自定义样式 -->
<quality-indicator 
  quality-score="{{75}}" 
  custom-class="my-custom-class"
/>
```

```javascript
// Page 代码
Page({
  data: {
    qualityScore: 85,
    qualityLevel: {
      level: 'excellent',
      label: '优秀',
      color: '#28a745',
      description: '报告质量优秀，数据完整可靠',
      recommendation: '可以直接使用报告结果进行决策'
    }
  },
  
  handleQualityClick(e) {
    console.log('质量评分:', e.detail.score);
    console.log('质量等级:', e.detail.level);
  }
});
```

### 质量等级说明

| 等级 | 分数范围 | 颜色 | 图标 |
|------|----------|------|------|
| excellent | 80-100 | #28a745 | star |
| good | 60-79 | #17a2b8 | thumb-up |
| fair | 40-59 | #ffc107 | info |
| poor | 20-39 | #fd7e14 | warning |
| critical | 0-19 | #dc3545 | error |

---

## error-display 组件

### 功能描述

显示错误信息和操作建议，支持自定义操作按钮。

### 属性列表

| 属性名 | 类型 | 默认值 | 必填 | 描述 |
|--------|------|--------|------|------|
| error-type | String | 'error' | 是 | 错误类型 (error, not_found, timeout, no_results) |
| error-message | String | '发生未知错误' | 否 | 错误消息 |
| fallback-info | Object | null | 否 | 降级信息（包含 title, description, icon, actions） |
| show-retry | Boolean | true | 否 | 是否显示重试按钮 |
| custom-class | String | '' | 否 | 自定义样式类名 |

### 事件列表

| 事件名 | 参数 | 描述 |
|--------|------|------|
| bind:retry | - | 点击重试按钮时触发 |
| bind:action | `{action}` | 点击操作按钮时触发 |

### 使用示例

```xml
<!-- 基础用法 -->
<error-display 
  error-type="not_found"
  error-message="报告不存在，请检查执行 ID"
/>

<!-- 带降级信息 -->
<error-display 
  error-type="{{errorType}}"
  error-message="{{errorMessage}}"
  fallback-info="{{fallbackInfo}}"
  bind:retry="handleRetry"
  bind:action="handleAction"
/>

<!-- 隐藏重试按钮 -->
<error-display 
  error-type="timeout"
  show-retry="{{false}}"
/>
```

```javascript
// Page 代码
Page({
  data: {
    errorType: 'not_found',
    errorMessage: '报告不存在',
    fallbackInfo: {
      title: '报告不存在',
      description: '未找到对应的诊断报告',
      icon: 'search',
      actions: [
        { text: '重新诊断', type: 'navigate', url: '/pages/diagnosis/diagnosis' },
        { text: '查看历史', type: 'navigate', url: '/pages/history/history' }
      ]
    }
  },
  
  handleRetry() {
    console.log('用户点击重试');
    // 执行重试逻辑
  },
  
  handleAction(e) {
    console.log('用户点击操作:', e.detail.action);
  }
});
```

### 错误类型说明

| 类型 | 标题 | 描述 | 图标颜色 |
|------|------|------|----------|
| error | 发生错误 | 系统遇到意外错误 | #dc3545 |
| not_found | 未找到 | 请求的内容不存在 | #ffc107 |
| timeout | 请求超时 | 请求处理时间过长 | #fd7e14 |
| no_results | 无结果 | 未找到相关结果 | #6c757d |

---

## 使用指南

### 1. 引入组件

在页面的 JSON 配置文件中引入组件：

```json
{
  "usingComponents": {
    "quality-indicator": "/components/quality-indicator/quality-indicator",
    "error-display": "/components/error-display/error-display"
  }
}
```

### 2. 在 WXML 中使用

```xml
<!-- 报告页面 -->
<view wx:if="{{report}}">
  <quality-indicator 
    quality-score="{{report.validation.quality_score}}"
    quality-level="{{report.validation.quality_level}}"
    show-detail="{{true}}"
  />
</view>

<!-- 错误页面 -->
<view wx:if="{{error}}">
  <error-display 
    error-type="{{error.type}}"
    error-message="{{error.message}}"
    fallback-info="{{error.fallbackInfo}}"
    bind:retry="handleRetry"
  />
</view>
```

### 3. 在 JS 中处理事件

```javascript
Page({
  data: {
    report: null,
    error: null
  },
  
  onLoad(options) {
    // 加载报告或错误信息
    this.loadData(options.id);
  },
  
  async loadData(id) {
    try {
      const report = await reportService.getFullReport(id);
      this.setData({ report });
    } catch (error) {
      this.setData({
        error: {
          type: 'error',
          message: error.message,
          fallbackInfo: {
            title: '加载失败',
            description: '无法加载报告数据',
            actions: [
              { text: '重试', type: 'retry' }
            ]
          }
        }
      });
    }
  },
  
  handleRetry() {
    this.loadData(this.options.id);
  }
});
```

---

## 最佳实践

### 1. 组件复用

- 优先使用现有组件，避免重复开发
- 组件功能保持单一职责
- 组件之间通过事件通信

### 2. 样式定制

- 使用 `custom-class` 属性添加自定义样式
- 使用 CSS 变量实现主题切换
- 避免在组件内部硬编码样式值

### 3. 性能优化

- 避免频繁更新组件属性
- 使用 `wx:if` 控制组件渲染
- 大数据列表使用虚拟滚动

### 4. 错误处理

- 始终提供友好的错误提示
- 使用 `error-display` 组件统一错误展示
- 提供明确的操作建议

### 5. 可访问性

- 为组件添加适当的 ARIA 属性
- 确保文字对比度符合 WCAG 标准
- 支持键盘导航

---

## 更新日志

### v1.0.0 (2026-03-08)

- ✅ 新增 quality-indicator 组件
- ✅ 新增 error-display 组件
- ✅ 完善组件文档
- ✅ 添加使用示例

---

**文档结束**
