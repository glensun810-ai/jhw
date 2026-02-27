# 统一错误提示组件使用文档

## 概述

统一错误提示组件 (`error-toast`) 提供友好的错误提示展示，支持多种错误类型、自定义操作按钮和自动关闭功能。

## 组件特性

- **多种错误类型**: 网络错误、服务器错误、业务错误、权限错误、超时错误
- **友好的 UI**: 带图标、标题、消息、详情的完整展示
- **自定义操作**: 支持重试、取消、确认等按钮
- **自动关闭**: 可配置倒计时自动关闭
- **开发模式**: 显示错误代码便于调试
- **暗黑模式**: 支持系统暗黑主题

## 快速开始

### 1. 在页面 JSON 中注册组件

```json
{
  "usingComponents": {
    "error-toast": "/miniprogram/components/error-toast/error-toast"
  }
}
```

### 2. 在页面 WXML 中添加组件

```xml
<error-toast
  id="errorToast"
  visible="{{showErrorToast}}"
  error-type="{{errorType}}"
  title="{{errorTitle}}"
  message="{{errorMessage}}"
  show-retry="{{showRetry}}"
  bind:close="onErrorClose"
  bind:retry="onRetry"
></error-toast>
```

### 3. 在页面 JS 中控制显示

```javascript
import { handleApiError } from '../../utils/errorHandler';

Page({
  data: {
    showErrorToast: false,
    errorType: 'default',
    errorTitle: '',
    errorMessage: '',
    showRetry: false
  },

  // 显示错误
  handleError(error) {
    const handled = handleApiError(error);
    
    this.setData({
      showErrorToast: true,
      errorType: handled.type,
      errorTitle: handled.title,
      errorMessage: handled.message,
      showRetry: handled.retryable
    });
  },

  // 关闭错误提示
  onErrorClose() {
    this.setData({ showErrorToast: false });
  },

  // 重试操作
  onRetry() {
    this.setData({ showErrorToast: false });
    // 执行重试逻辑
    this.loadData();
  }
});
```

## 组件属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| visible | Boolean | false | 是否显示 |
| errorType | String | 'default' | 错误类型：network, server, business, auth, timeout, default |
| title | String | '' | 错误标题 |
| message | String | '' | 错误消息 |
| detail | String | '' | 错误详情 |
| errorCode | String | '' | 错误代码 |
| showDetail | Boolean | false | 是否显示详情按钮 |
| showCancel | Boolean | false | 是否显示取消按钮 |
| showRetry | Boolean | false | 是否显示重试按钮 |
| showConfirm | Boolean | false | 是否显示确认按钮 |
| cancelText | String | '取消' | 取消按钮文本 |
| retryText | String | '重试' | 重试按钮文本 |
| confirmText | String | '确定' | 确认按钮文本 |
| closeText | String | '知道了' | 关闭按钮文本 |
| autoClose | Boolean | false | 是否自动关闭 |
| countdown | Number | 5 | 自动关闭倒计时（秒） |
| isDevMode | Boolean | false | 是否开发模式（显示错误代码） |

## 组件事件

| 事件 | 说明 | 回调参数 |
|------|------|----------|
| bind:close | 关闭事件 | - |
| bind:cancel | 取消按钮点击 | - |
| bind:retry | 重试按钮点击 | - |
| bind:confirm | 确认按钮点击 | - |
| bind:change | 显示状态变化 | { visible: Boolean } |

## 错误类型说明

| 类型 | 图标 | 适用场景 |
|------|------|----------|
| network | 📡 | 网络连接失败、API 请求失败 |
| server | ⚠️ | 服务器错误、5xx 错误 |
| business | 💼 | 业务逻辑错误、资源不存在 |
| auth | 🔒 | 权限错误、未登录、未授权 |
| timeout | ⏱️ | 请求超时 |
| default | ❌ | 其他未知错误 |

## 工具函数

### errorHandler.js

```javascript
import { 
  handleApiError,      // 处理错误对象
  showError,           // 显示错误提示（原生）
  logError,            // 记录错误日志
  isRetryableError,    // 判断是否可重试
  getErrorDetail,      // 获取错误详情
  getFriendlyMessage   // 获取友好消息
} from '../../utils/errorHandler';
```

### uiHelper.js

```javascript
import { 
  showErrorToast,      // 显示错误提示
  showErrorModal,      // 显示错误模态框
  showSuccess,         // 显示成功提示
  showLoading,         // 显示加载中
  hideLoading,         // 隐藏加载中
  showNetworkError,    // 显示网络错误
  showTimeoutError,    // 显示超时错误
  showAuthError        // 显示权限错误
} from '../../utils/uiHelper';
```

## 使用示例

### 示例 1: API 请求错误处理

```javascript
async loadData() {
  try {
    const data = await api.getData();
    this.setData({ data });
  } catch (error) {
    const handled = handleApiError(error);
    this.setData({
      showErrorToast: true,
      errorType: handled.type,
      errorTitle: handled.title,
      errorMessage: handled.message,
      showRetry: handled.retryable
    });
  }
}
```

### 示例 2: 快捷错误提示

```javascript
// 使用工具函数快速显示
import { showErrorToast } from '../../utils/uiHelper';

onError(error) {
  showErrorToast(error, {
    duration: 3000,
    mask: true
  });
}
```

### 示例 3: 全局错误处理

```javascript
// app.js
App({
  globalData: {
    errorToast: null
  },
  
  setErrorToast(component) {
    this.globalData.errorToast = component;
  },
  
  showError(error, options) {
    const errorToast = this.globalData.errorToast;
    if (errorToast && typeof errorToast.showError === 'function') {
      errorToast.showError(error, options);
    }
  }
});

// 页面中使用
getApp().showError(error, { showRetry: true });
```

### 示例 4: 带详情的错误

```javascript
handleComplexError(error) {
  this.setData({
    showErrorToast: true,
    errorType: 'server',
    errorTitle: '服务器错误',
    errorMessage: error.message,
    errorDetail: JSON.stringify(error.detail, null, 2),
    showDetail: true,
    errorCode: error.code,
    isDevMode: true
  });
}
```

## 最佳实践

1. **统一错误处理**: 在所有 API 调用中使用 `handleApiError` 处理错误
2. **记录日志**: 使用 `logError` 记录错误便于问题排查
3. **友好提示**: 向用户显示友好的错误消息，而非技术细节
4. **提供重试**: 对于网络错误等可重试错误，提供重试按钮
5. **区分场景**: 根据错误类型显示不同的提示和操作
6. **开发模式**: 在开发环境显示错误代码便于调试

## 样式定制

在页面的 wxss 文件中可以覆盖组件默认样式：

```css
/* 自定义错误提示容器样式 */
.error-toast-container {
  border-radius: 20rpx;
}

/* 自定义错误标题颜色 */
.error-title {
  color: #f44336;
}
```

## 注意事项

1. 确保在页面卸载时关闭错误提示，避免内存泄漏
2. 自动关闭时间不宜过短，建议 3-5 秒
3. 重要错误不要使用自动关闭，确保用户看到
4. 错误消息应简洁明了，避免技术术语
