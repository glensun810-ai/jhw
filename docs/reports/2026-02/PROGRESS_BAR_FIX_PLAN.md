# 进度条优化实施方案

**版本**: v14.0  
**日期**: 2026-02-20  
**状态**: 🟡 规划中

---

## 📊 问题总结

### 当前问题

| 问题 | 现象 | 根因 | 优先级 |
|------|------|------|--------|
| 进度条卡在 80% | 长时间不动 | 动画与轮询脱节 | P0 |
| 进度条跳动 | 忽快忽慢 | 轮询间隔不合理 | P1 |
| 文案更新慢 | 长时间不变 | 依赖后端返回 | P1 |
| 进度不准确 | 与实际任务不符 | 计算方式问题 | P0 |

---

## 🎯 修复目标

### 核心指标

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 进度准确度 | 60% | 95% | +58% |
| 流畅度 | 2/5 | 5/5 | +150% |
| 文案及时性 | 3/5 | 5/5 | +67% |
| 用户满意度 | 3/5 | 5/5 | +67% |

---

## 🏗️ 技术方案

### 1. 进度管理器

**文件**: `utils/progressManager.js`

**功能**:
- ✅ 基于任务数的进度计算
- ✅ 平滑过渡动画
- ✅ 智能文案更新
- ✅ 详细进度显示

**使用**:
```javascript
const ProgressManager = require('../../utils/progressManager');

// 初始化
this.progressManager = new ProgressManager(this);
this.progressManager.init(3, 3); // 3 问题×3 模型

// 更新进度
this.progressManager.updateProgress(4); // 完成 4 个任务

// 完成任务时调用
this.progressManager.incrementProgress();
```

---

### 2. 轮询优化

**修改**: `pages/detail/index.js`

**优化前**:
```javascript
// 轮询间隔递增 (3s → 6s)
if (progress < 20) interval = 3000;
else if (progress < 50) interval = 4000;
else if (progress < 80) interval = 5000;
else interval = 6000; // ❌ 问题
```

**优化后**:
```javascript
// 固定轮询间隔 (2s)
this.currentPollInterval = 2000;

// 每次轮询更新进度
const statusData = await this.fetchTaskStatus();
this.progressManager.updateProgress(statusData.completedTasks);
```

---

### 3. UI 优化

**修改**: `pages/detail/index.wxml`

**新增显示**:
```xml
<view class="progress-detail">
  <text class="progress-percentage">{{progress}}%</text>
  <text class="progress-tasks">{{progressDetail}}</text>
</view>
```

**样式**:
```css
.progress-detail {
  display: flex;
  justify-content: space-between;
  margin-top: 8rpx;
}

.progress-percentage {
  font-size: 28rpx;
  font-weight: bold;
  color: #00F2FF;
}

.progress-tasks {
  font-size: 24rpx;
  color: #8c8c8d;
}
```

---

## 📋 实施步骤

### 步骤 1: 集成进度管理器 (2 小时)

- [ ] 在 `detail/index.js` 中引入
- [ ] 在 `onLoad` 中初始化
- [ ] 替换原有的 `startProgressAnimation`

### 步骤 2: 优化轮询逻辑 (2 小时)

- [ ] 固定轮询间隔为 2 秒
- [ ] 每次轮询调用 `progressManager.updateProgress()`
- [ ] 添加平滑过渡

### 步骤 3: UI 优化 (1 小时)

- [ ] 添加进度百分比显示
- [ ] 添加任务进度显示
- [ ] 优化文案

### 步骤 4: 测试验证 (1 小时)

- [ ] 模拟测试 (1×3 配置)
- [ ] 真实测试 (1×3 配置)
- [ ] 压力测试 (2×5 配置)

---

## 🧪 测试用例

### 用例 1: 标准配置 (3 问题×3 模型)

**步骤**:
1. 输入：华为，小米，3 问题，3 模型
2. 启动诊断
3. 观察进度条

**预期**:
- ✅ 进度从 0% 平滑增长
- ✅ 每完成一个任务增长 11% (1/9)
- ✅ 显示"1/9 任务完成"、"2/9 任务完成"...
- ✅ 文案根据进度变化
- ✅ 不会卡在 80%

---

### 用例 2: 大型配置 (5 问题×5 模型)

**步骤**:
1. 输入：华为，5 竞品，5 问题，5 模型
2. 启动诊断
3. 观察进度条

**预期**:
- ✅ 总任务数：25 个
- ✅ 每任务增长 4% (1/25)
- ✅ 进度条流畅
- ✅ 文案更新及时

---

### 用例 3: 错误处理

**步骤**:
1. 启动诊断
2. 模拟网络错误
3. 观察进度条

**预期**:
- ✅ 显示错误提示
- ✅ 进度条停止
- ✅ 提供重试按钮

---

## 📊 预期效果

### 进度条展示

```
┌─────────────────────────────────────────┐
│ AI 正在连接全网大模型...                 │
├─────────────────────────────────────────┤
│                                         │
│ ████████░░░░░░░░░  45%                 │
│                                         │
│ 4/9 任务完成                            │
└─────────────────────────────────────────┘
```

### 文案变化

| 进度 | 文案 |
|------|------|
| 0-10% | 准备诊断环境... |
| 11-20% | 正在连接 AI 模型... |
| 21-40% | 正在分析问题... |
| 41-60% | 正在收集 AI 回答... |
| 61-80% | 正在聚合分析结果... |
| 81-90% | 正在生成诊断报告... |
| 91-99% | 正在做最后校验... |
| 100% | 诊断完成！✅ |

---

## 🔗 依赖关系

### 前置条件

- [ ] 后端支持返回 `completedTasks` 字段
- [ ] 后端支持返回 `totalTasks` 字段
- [ ] 后端进度计算基于任务数

### 后端接口

**期望返回格式**:
```json
{
  "progress": 45,
  "status": "running",
  "completedTasks": 4,
  "totalTasks": 9,
  "stage": "analyzing"
}
```

---

## 📝 备注

### 兼容性考虑

- ✅ 向后兼容：如果后端不支持新字段，使用旧逻辑
- ✅ 平滑过渡：新旧逻辑无缝切换

### 性能考虑

- ✅ 轮询间隔：2 秒 (平衡实时性和性能)
- ✅ 动画帧率：≥50fps
- ✅ 内存占用：<10MB

---

**下一步**: 开始实施步骤 1
