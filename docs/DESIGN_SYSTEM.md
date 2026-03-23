# 品牌诊断系统设计规范

**版本**: 2.0.0  
**更新日期**: 2026-03-11  
**适用范围**: 小程序全页面

---

## 一、设计理念

### 1.1 设计愿景
打造**科技感、专业化、沉浸式**的品牌诊断体验，让用户感受到 AI 智能分析的权威性和数据的可信度。

### 1.2 设计原则
- **一致性**: 所有页面使用统一的设计语言和组件规范
- **科技感**: 深色主题 + 渐变效果 + 玻璃拟态
- **可读性**: 高对比度配色，确保信息清晰传达
- **流畅性**: 精致的动画过渡，提升交互体验

---

## 二、色彩系统

### 2.1 主色调

| 名称 | 色值 | 用途 | 示例 |
|------|------|------|------|
| **深空黑** | `#121826` | 页面背景 | 首页、报告页背景 |
| **星空蓝** | `#1A202C` | 卡片背景 | 输入框、设置面板 |
| **科技青** | `#00E5FF` | 主强调色 | 标题渐变、按钮、进度条 |
| **极光绿** | `#00F5A0` | 次强调色 | 渐变搭配、成功状态 |
| **深空蓝** | `#1A237E` | 辅助色 | 渐变起始色 |

### 2.2 渐变色规范

```css
/* 主渐变 - 用于按钮、标题 */
background: linear-gradient(135deg, #00A9FF 0%, #00F5A0 100%);

/* 卡片渐变 - 用于玻璃拟态 */
background: linear-gradient(135deg, rgba(26, 32, 44, 0.6) 0%, rgba(15, 52, 96, 0.6) 100%);

/* 进度条渐变 */
background: linear-gradient(90deg, #00A9FF, #00F5A0);

/* 标题文字渐变 */
background: linear-gradient(135deg, #00E5FF 0%, #00F5A0 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
```

### 2.3 功能色

| 状态 | 色值 | 用途 |
|------|------|------|
| 成功 | `#27ae60` | 完成状态、成功提示 |
| 警告 | `#f39c12` | 注意提示、配置警告 |
| 错误 | `#e74c3c` | 错误提示、删除操作 |
| 信息 | `#3498db` | 信息提示、帮助说明 |

### 2.4 文本色

| 层级 | 色值 | 用途 |
|------|------|------|
| 主文本 | `#e8e8e8` | 主要内容、标题 |
| 次文本 | `#8c8c8c` | 副标题、说明文字 |
| 提示文本 | `#666666` | 辅助信息、占位符 |
| 禁用文本 | `#4a4a4a` | 禁用状态 |

---

## 三、排版系统

### 3.1 字体规范

```css
/* 字体栈 */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
             Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
```

### 3.2 字号规范

| 用途 | 字号 | 字重 | 行高 |
|------|------|------|------|
| 大标题 | 48rpx | 700 | 1.2 |
| 页面标题 | 36rpx | 700 | 1.3 |
| 卡片标题 | 32rpx | 600 | 1.4 |
| 正文 | 28rpx | 400/500 | 1.6 |
| 辅助文字 | 24rpx | 400 | 1.5 |
| 小字 | 22rpx | 400 | 1.4 |

### 3.3 字重规范

| 字重 | 用途 |
|------|------|
| 700 (Bold) | 大标题、重要数字 |
| 600 (SemiBold) | 卡片标题、按钮文字 |
| 500 (Medium) | 强调文字、选中状态 |
| 400 (Regular) | 正文、辅助文字 |

---

## 四、布局系统

### 4.1 间距规范

基于 **8rpx** 的倍数：

| 间距 | 用途 |
|------|------|
| 8rpx | 小组件内部间距 |
| 16rpx | 卡片内边距、元素间距 |
| 24rpx | 标准内边距 |
| 32rpx | 大卡片内边距 |
| 48rpx | 区块间距 |
| 64rpx | 大区块间距 |

### 4.2 圆角规范

| 圆角 | 用途 |
|------|------|
| 8rpx | 小按钮、输入框 |
| 12rpx | 卡片、芯片 |
| 16rpx | 大卡片、弹窗 |
| 20rpx | 大卡片、报告卡片 |
| 48rpx | 主按钮、胶囊 |

### 4.3 阴影规范

```css
/* 小阴影 - 用于小组件 */
box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.1);

/* 中阴影 - 用于卡片 */
box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.15);

/* 大阴影 - 用于弹窗、悬浮元素 */
box-shadow: 0 16rpx 48rpx rgba(0, 0, 0, 0.2);

/* 发光阴影 - 用于强调元素 */
box-shadow: 0 0 20rpx rgba(0, 229, 255, 0.3),
            0 0 40rpx rgba(0, 229, 255, 0.2);
```

---

## 五、组件规范

### 5.1 按钮组件

#### 主按钮
```css
.btn-primary {
  height: 88rpx;
  background: linear-gradient(135deg, #00A9FF 0%, #00F5A0 100%);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: 44rpx;
  border: none;
  box-shadow: 0 8rpx 24rpx rgba(0, 169, 255, 0.3);
  transition: all 0.3s ease;
}

.btn-primary:active {
  transform: scale(0.96);
  opacity: 0.9;
}
```

#### 次按钮
```css
.btn-secondary {
  height: 72rpx;
  background: rgba(255, 255, 255, 0.05);
  color: #e8e8e8;
  font-size: 28rpx;
  font-weight: 500;
  border-radius: 36rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}
```

### 5.2 卡片组件

#### 玻璃拟态卡片
```css
.glass-card {
  background: linear-gradient(135deg, rgba(26, 32, 44, 0.6) 0%, rgba(15, 52, 96, 0.6) 100%);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 20rpx;
  padding: 32rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.3);
}
```

### 5.3 输入框组件

```css
.input-wrapper {
  display: flex;
  align-items: center;
  height: 88rpx;
  border-radius: 8rpx;
  background-color: #262626;
  border: 1rpx solid #3a3a3a;
}

.input {
  flex: 1;
  height: 100%;
  padding: 0 30rpx;
  font-size: 28rpx;
  color: #fff;
}
```

### 5.4 进度条组件

```css
.progress-bar-container {
  width: 100%;
  height: 16rpx;
  background-color: #262626;
  border-radius: 8rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.3);
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #00A9FF, #00F5A0);
  position: relative;
  overflow: hidden;
}

/* 流光效果 */
.progress-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.4) 50%,
    transparent 100%
  );
  animation: progress-shine 2s ease-in-out infinite;
}
```

---

## 六、动画规范

### 6.1 过渡时间

| 动画类型 | 时间 | 缓动函数 |
|---------|------|---------|
| 快速过渡 | 150ms | ease |
| 标准过渡 | 300ms | cubic-bezier(0.4, 0, 0.2, 1) |
| 慢速过渡 | 500ms | cubic-bezier(0.25, 0.46, 0.45, 0.94) |

### 6.2 页面进入动画

```css
@keyframes pageEnter {
  from {
    opacity: 0;
    transform: translateY(30rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-enter {
  animation: pageEnter 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
```

### 6.3 卡片进入动画

```css
@keyframes cardEnter {
  from {
    opacity: 0;
    transform: translateY(20rpx) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.card-enter {
  animation: cardEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
```

### 6.4 按钮点击效果

```css
.tap-effect {
  transition: transform 0.1s ease, opacity 0.1s ease;
}

.tap-effect:active {
  transform: scale(0.95);
  opacity: 0.8;
}
```

---

## 七、页面规范

### 7.1 首页规范

- **背景**: `#121826` 深空黑
- **主按钮**: 渐变绿 (#00F5A0 → #00D18C)
- **卡片**: 玻璃拟态 + 深色背景
- **输入框**: 深灰 (#262626) + 边框 (#3a3a3a)

### 7.2 报告页规范

- **背景**: `#121826` 深空黑（与首页一致）
- **头部**: 玻璃拟态 + 深色半透明
- **标签页**: 深色背景 + 科技青强调
- **卡片**: 玻璃拟态 + 渐变边框
- **按钮**: 渐变蓝绿 (#00A9FF → #00F5A0)

### 7.3 组件页规范

- 遵循统一卡片样式
- 使用相同的间距和圆角
- 保持色彩一致性

---

## 八、响应式设计

### 8.1 断点规范

| 设备 | 宽度范围 | 适配策略 |
|------|---------|---------|
| 小屏 | ≤ 375px | 缩小字号、减少间距 |
| 中屏 | 376px - 414px | 标准布局 |
| 大屏 | ≥ 415px | 增加内容宽度 |

### 8.2 小屏适配

```css
@media (max-width: 375px) {
  .header-title {
    font-size: 32rpx; /* 从 36rpx 降低 */
  }
  
  .tab-item {
    font-size: 26rpx; /* 从 28rpx 降低 */
  }
  
  .stat-value {
    font-size: 40rpx; /* 从 44rpx 降低 */
  }
}
```

---

## 九、暗黑模式

### 9.1 暗黑模式规范

小程序默认使用深色主题，暗黑模式增强：

```css
@media (prefers-color-scheme: dark) {
  .report-page {
    background-color: #121826;
  }
  
  .header {
    background: rgba(26, 32, 44, 0.98);
    border-bottom-color: rgba(255, 255, 255, 0.08);
  }
}
```

---

## 十、设计审查清单

### 10.1 视觉一致性检查

- [ ] 所有页面背景色一致 (#121826)
- [ ] 按钮使用统一的渐变色
- [ ] 卡片使用玻璃拟态效果
- [ ] 圆角规范一致 (8/12/16/20/48rpx)
- [ ] 间距规范一致 (8rpx 倍数)

### 10.2 交互一致性检查

- [ ] 按钮点击效果一致 (scale 0.95-0.96)
- [ ] 过渡时间一致 (150/300/500ms)
- [ ] 加载动画一致
- [ ] 错误提示样式一致

### 10.3 可访问性检查

- [ ] 对比度符合 WCAG AA 标准
- [ ] 触摸区域 ≥ 44x44rpx
- [ ] 文字大小适中 (≥ 22rpx)
- [ ] 动画适度（无过度闪烁）

---

## 十一、版本历史

| 版本 | 日期 | 更新内容 | 作者 |
|------|------|---------|------|
| 1.0.0 | 2026-02-27 | 初始版本 | 架构组 |
| 2.0.0 | 2026-03-11 | 统一设计系统，深色主题 | 架构组 |

---

## 十二、资源下载

- [Figma 设计稿](#) (待上传)
- [Sketch 设计稿](#) (待上传)
- [图标资源](../../images/)

---

**维护团队**: 系统架构组  
**联系方式**: architecture@example.com
