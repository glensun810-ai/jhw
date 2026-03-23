# 全局样式库使用指南

**版本**: 1.0.0  
**更新日期**: 2026-02-21

---

## 目录

1. [进度条特效样式库](#进度条特效样式库)
2. [高斯模糊背景样式库](#高斯模糊背景样式库)
3. [使用示例](#使用示例)

---

## 进度条特效样式库

**文件**: `styles/progress-effects.wxss`

### 快速开始

在页面 wxss 中导入：
```css
@import './styles/progress-effects.wxss';
```

### 基础用法

```xml
<!-- WXML -->
<view class="progress-base">
  <view class="progress-inner progress-tech" style="width: {{progress}}%"></view>
</view>
```

### 预设样式

| 类名 | 效果描述 | 适用场景 |
|------|----------|----------|
| `progress-tech` | 科技蓝光 + 流光 | 技术类应用 |
| `progress-premium` | 高端金光 + 脉冲 | VIP/付费功能 |
| `progress-energy` | 活力橙光 + 条纹 | 运动/健康类 |
| `progress-nature` | 自然绿光 + 流光 | 环保/健康类 |
| `progress-passion` | 热情红光 + 流光 | 紧急/重要任务 |
| `progress-dream` | 梦幻紫光 + 脉冲 | 创意/艺术类 |
| `progress-rainbow` | 彩虹渐变 + 流光 | 特殊活动 |

### 状态指示

| 类名 | 效果 | 说明 |
|------|------|------|
| `progress-processing` | 蓝色流光 | 处理中 |
| `progress-success` | 绿色脉冲 | 成功 |
| `progress-warning` | 橙色条纹 | 警告 |
| `progress-error` | 红色闪烁 | 错误 |

### 尺寸变体

| 类名 | 高度 | 用途 |
|------|------|------|
| `progress-sm` | 8rpx | 紧凑布局 |
| `progress-md` | 16rpx | 标准尺寸 |
| `progress-lg` | 24rpx | 突出显示 |
| `progress-xl` | 32rpx | 大幅展示 |

### 组合示例

```xml
<!-- 科技感进度条 -->
<view class="progress-glass-container">
  <view 
    class="progress-inner progress-tech progress-md progress-rounded-full" 
    style="width: {{progress}}%">
  </view>
</view>

<!-- 高端会员进度 -->
<view class="progress-base">
  <view 
    class="progress-inner progress-premium progress-lg progress-rounded" 
    style="width: {{progress}}%">
  </view>
</view>

<!-- 彩虹活动进度 -->
<view class="progress-base">
  <view 
    class="progress-inner progress-rainbow progress-md progress-striped" 
    style="width: {{progress}}%">
  </view>
</view>
```

---

## 高斯模糊背景样式库

**文件**: `styles/glassmorphism.wxss`

### 快速开始

在页面 wxss 中导入：
```css
@import './styles/glassmorphism.wxss';
```

### 基础用法

```xml
<!-- WXML -->
<view class="glass-card">
  <text>毛玻璃卡片内容</text>
</view>
```

### 预设样式

| 类名 | 效果描述 | 适用场景 |
|------|----------|----------|
| `glass-card` | 标准卡片 | 内容卡片 |
| `glass-modal` | 弹窗效果 | 模态框/对话框 |
| `glass-navbar` | 导航栏效果 | 顶部导航 |
| `glass-float-button` | 悬浮按钮 | FAB 按钮 |
| `glass-input` | 输入框效果 | 表单输入 |
| `glass-badge` | 徽章效果 | 标签/徽章 |

### 模糊强度

| 类名 | 模糊值 | 效果 |
|------|--------|------|
| `glass-blur-sm` | 4px | 轻度模糊 |
| `glass-blur` | 10px | 标准模糊 |
| `glass-blur-lg` | 20px | 强度模糊 |
| `glass-blur-xl` | 30px | 超强模糊 |

### 透明度

| 类名 | 透明度 | 效果 |
|------|--------|------|
| `glass-transparent` | 2% | 高透明 |
| `glass-base` | 5% | 标准透明 |
| `glass-translucent` | 10% | 半透明 |
| `glass-opaque` | 15% | 低透明 |

### 色调变体

| 类名 | 色调 | 适用场景 |
|------|------|----------|
| `glass-cool` | 冷色蓝灰 | 科技/商务 |
| `glass-warm` | 暖色米白 | 生活/社交 |
| `glass-dark` | 暗色调 | 夜间模式 |
| `glass-tint-red` | 红色调 | 警告/热情 |
| `glass-tint-blue` | 蓝色调 | 冷静/专业 |
| `glass-tint-green` | 绿色调 | 健康/环保 |
| `glass-tint-purple` | 紫色调 | 创意/奢华 |

### 动态光斑背景

```xml
<!-- WXML -->
<view class="glass-orb-background">
  <view class="glass-orb glass-orb-1"></view>
  <view class="glass-orb glass-orb-2"></view>
  <view class="glass-orb glass-orb-3"></view>
</view>

<!-- 内容区域 -->
<view class="glass-card">
  <text>内容</text>
</view>
```

### 组合示例

```xml
<!-- 标准卡片 -->
<view class="glass-card">
  <text>基础毛玻璃卡片</text>
</view>

<!-- 自定义组合 -->
<view class="glass-base glass-blur-lg glass-rounded-xl glass-shadow-lg glass-tint-blue">
  <text>自定义组合效果</text>
</view>

<!-- 弹窗 -->
<view class="glass-modal">
  <view class="glass-card">
    <text>弹窗内容</text>
  </view>
</view>

<!-- 导航栏 -->
<view class="glass-navbar glass-shadow-sm">
  <text>粘性导航栏</text>
</view>
```

---

## 最佳实践

### 1. 性能优化

```css
/* ✅ 推荐：适度使用模糊效果 */
.glass-element {
  backdrop-filter: blur(10px);
}

/* ❌ 避免：过度使用高强度模糊 */
.glass-element {
  backdrop-filter: blur(50px); /* 性能开销大 */
}
```

### 2. 兼容性处理

```css
.glass-element {
  /* 标准属性 */
  backdrop-filter: blur(10px);
  
  /* WebKit 前缀（微信小程序需要） */
  -webkit-backdrop-filter: blur(10px);
  
  /* 降级背景色 */
  background: rgba(255, 255, 255, 0.1);
}
```

### 3. 层次结构

```xml
<!-- ✅ 推荐：清晰的层次 -->
<view class="glass-orb-background"></view>  <!-- z-index: 0 -->
<view class="glass-card"></view>            <!-- z-index: 10 -->
<view class="glass-modal"></view>           <!-- z-index: 100 -->

<!-- ❌ 避免：层次混乱 -->
<view class="glass-card" style="z-index: 999"></view>
```

### 4. 响应式适配

```css
/* 根据屏幕尺寸调整模糊强度 */
@media (max-width: 768px) {
  .glass-card {
    backdrop-filter: blur(8px); /* 移动端降低模糊 */
  }
}
```

---

## 更新日志

### v1.0.0 (2026-02-21)

- ✅ 新增进度条特效样式库
- ✅ 新增高斯模糊背景样式库
- ✅ 新增动态光斑背景动画
- ✅ 新增 7 种进度条预设样式
- ✅ 新增 6 种毛玻璃预设样式

---

## 文件结构

```
styles/
├── progress-effects.wxss    # 进度条特效样式库
├── glassmorphism.wxss       # 高斯模糊背景样式库
└── README.md                # 使用指南（本文件）
```

---

## 技术支持

如有问题或建议，请联系开发团队。
