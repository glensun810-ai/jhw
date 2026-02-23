# 诊断进度系统测试执行指南

**版本**: v12.0  
**日期**: 2026-02-20  
**测试负责人**: AI Assistant (资深测试专家)

---

## 📋 测试前准备

### 1. 环境检查清单

- [ ] 微信开发者工具已启动
- [ ] 后端服务运行正常 (http://127.0.0.1:5000)
- [ ] 测试账号已登录
- [ ] Console 面板已打开

### 2. 清除旧数据

在 Console 执行:
```javascript
wx.clearStorageSync();
console.log('✅ 存储已清除');
```

### 3. 加载测试工具

在 Console 执行:
```javascript
const { testHelper } = require('./utils/testHelper.js');
console.log('✅ 测试工具已加载');
```

---

## 🧪 阶段 1 测试执行

### 模块 1.1: 时间预估算法测试

#### 测试 TE-01: 首次预估 (无历史)

**执行步骤**:

1. **清除历史**
```javascript
wx.clearStorageSync();
```

2. **开始测试**
```javascript
testHelper.startTest('TE-01', '首次预估测试');
```

3. **启动诊断**
- 品牌：华为
- 模型：通义千问、豆包、DeepSeek (3 个)
- 问题：3 个

4. **记录预估时间**
```javascript
// 在 detail 页面 Console 执行
const estimate = this.timeEstimator.estimate(1, 3, 3);
testHelper.record({
  type: 'estimate',
  estimatedMin: estimate.min,
  estimatedMax: estimate.max,
  estimatedExpected: estimate.expected,
  confidence: estimate.confidence
});
console.log('预估时间:', estimate);
```

5. **等待完成，记录实际时间**
```javascript
// 诊断完成后执行
const actualDuration = (Date.now() - this.startTime) / 1000;
testHelper.record({
  type: 'actual',
  actualTime: actualDuration
});

const report = testHelper.endTest();
console.log('测试报告:', report);
```

6. **记录结果**
```
预估时间：___秒 (范围：___-___秒)
实际时间：___秒
偏差：___%
置信度：___
```

---

#### 测试 TE-02: 有历史数据预估

**执行步骤**:

1. **连续执行 3 次诊断**
```javascript
testHelper.startTest('TE-02', '历史数据预估测试');

// 每次诊断完成后记录
testHelper.record({
  estimated: estimate.expected,
  actual: actualDuration,
  deviation: Math.abs(estimate.expected - actualDuration) / actualDuration * 100
});
```

2. **分析结果**
```javascript
const report = testHelper.endTest();
console.log('平均偏差:', report.analysis.timeEstimation.deviation);
console.log('是否通过:', report.analysis.timeEstimation.passed);
```

---

### 模块 1.2: 轮询间隔测试

#### 测试 PI-01~03: 轮询间隔验证

**执行步骤**:

1. **启动诊断**
```javascript
testHelper.startTest('PI-01', '轮询间隔测试');
```

2. **监控轮询日志**
```javascript
// 在 detail/index.js 的 performPoll 中添加
console.log(`轮询：进度${progress}%, 间隔${this.currentPollInterval}ms`);
testHelper.record({
  progress: progress,
  pollInterval: this.currentPollInterval
});
```

3. **记录各阶段间隔**
```
0-20%:  ___ms (预期 3000ms)
20-80%: ___ms (预期 2000ms)
80-100%: ___ms (预期 1000ms)
```

4. **验证结果**
```javascript
const report = testHelper.endTest();
console.log('轮询间隔:', report.analysis.pollingInterval);
```

---

### 模块 1.3: 剩余时间平滑测试

#### 测试 RT-01: 初期显示范围

**执行步骤**:

1. **启动诊断**
```javascript
testHelper.startTest('RT-01', '初期显示范围测试');
```

2. **记录<5% 时的显示**
```javascript
// 在 updateProgressDetails 中添加
if (parsedStatus.progress < 5) {
  console.log('初期显示:', this.data.smoothedRemainingTime);
  testHelper.record({
    progress: parsedStatus.progress,
    display: this.data.smoothedRemainingTime
  });
}
```

3. **验证**
```
预期："2-5 分钟" 或 "计算中..."
实际："___"
```

---

#### 测试 RT-02: 中期平滑度

**执行步骤**:

1. **每 5 秒记录一次**
```javascript
setInterval(() => {
  testHelper.record({
    progress: this.data.progress,
    remainingTime: this.data.remainingTime,
    smoothedRemaining: this.data.smoothedRemainingTime
  });
}, 5000);
```

2. **计算最大跳动**
```javascript
const report = testHelper.endTest();
console.log('最大跳动:', report.analysis.smoothness.maxJump, '秒');
console.log('是否通过:', report.analysis.smoothness.passed);
```

---

## 📊 测试结果记录表

### 模块 1.1 结果

| 次数 | 配置 | 预估 | 实际 | 偏差 | 通过 |
|------|------|------|------|------|------|
| 1 | 1×3 | | | | ⏳ |
| 2 | 1×3 | | | | ⏳ |
| 3 | 1×5 | | | | ⏳ |

### 模块 1.2 结果

| 阶段 | 预期间隔 | 实测间隔 | 通过 |
|------|----------|----------|------|
| 0-20% | 3000ms | | ⏳ |
| 20-80% | 2000ms | | ⏳ |
| 80-100% | 1000ms | | ⏳ |

### 模块 1.3 结果

| 测试项 | 预期 | 实测 | 通过 |
|--------|------|------|------|
| 初期显示 | 2-5 分钟 | | ⏳ |
| 最大跳动 | <30 秒 | | ⏳ |

---

## 🐛 问题记录表

| ID | 问题描述 | 严重性 | 模块 | 状态 |
|----|----------|--------|------|------|
| - | 暂无 | - | - | - |

---

## ✅ 阶段 1 通过标准

- [ ] TE-01: 首次预估偏差<50% (无历史数据)
- [ ] TE-02: 有历史数据偏差<20%
- [ ] PI-01~03: 轮询间隔符合设计
- [ ] RT-01: 初期显示范围正确
- [ ] RT-02: 最大跳动<30 秒

**全部通过**方可进入阶段 2 测试

---

**指南版本**: v1.0  
**更新时间**: 2026-02-20
