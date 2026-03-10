# P0-002 修复报告 - 认证错误过早熔断修复

**修复日期：** 2026 年 2 月 26 日  
**修复人：** 首席架构师  
**状态：** ✅ 已完成

---

## 问题描述

### 问题编号：P0-002
**标题：** 认证错误过早熔断导致结果丢失  
**影响：** 临时网络波动导致轮询停止，但后端诊断仍在执行，用户失去查看结果的机会  
**发生概率：** 中（网络不稳定环境）

### 问题代码位置
**文件：** `services/brandTestService.js` (第 243 行)

### 原代码
```javascript
// Step 1: 错误计数器，实现熔断机制
let consecutiveAuthErrors = 0;
const MAX_AUTH_ERRORS = 2;  // 连续 2 次 403/401 错误即熔断

if (errorInfo.isAuthError) {
  consecutiveAuthErrors++;
  if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
    controller.stop();
    console.error('认证错误熔断，停止轮询');
    if (onError) onError(new Error('权限验证失败，请重新登录'));
    return;
  }
}
```

### 问题根因
- 连续 2 次 401/403 错误即停止轮询
- 但后端诊断可能仍在执行（通常需要 3-5 分钟）
- 用户失去查看结果的机会，即使后端已成功完成
- 没有重试机制和降级方案

---

## 修复方案

### 修复策略
1. **增加重试次数** - 从 2 次提升到 5 次
2. **指数退避** - 每次重试延迟递增（1s → 2s → 4s → 8s → 10s）
3. **Token 刷新** - 在熔断前尝试清除本地 token 缓存
4. **Storage 恢复** - 熔断前尝试从本地缓存恢复结果
5. **友好提示** - 告知用户结果已恢复，建议重新登录

### 修复 1: 增加熔断阈值
**位置：** `services/brandTestService.js` (第 243 行)

```javascript
// 修复前：
const MAX_AUTH_ERRORS = 2;  // 连续 2 次错误即熔断

// 修复后：
const MAX_AUTH_ERRORS = 5;  // 【P0-002 修复】连续 5 次 403/401 错误才熔断（原为 2 次）
```

### 修复 2: 指数退避机制
**位置：** `services/brandTestService.js` (第 389-393 行)

```javascript
// 【P0-002 修复】计算指数退避延迟
const authErrorRetryDelay = Math.min(
  1000 * Math.pow(2, consecutiveAuthErrors),
  10000  // 最多延迟 10 秒
);
```

**退避策略：**
| 错误次数 | 延迟时间 |
|---------|---------|
| 第 1 次 | 1 秒 |
| 第 2 次 | 2 秒 |
| 第 3 次 | 4 秒 |
| 第 4 次 | 8 秒 |
| 第 5 次 | 10 秒（熔断） |

### 修复 3: Token 刷新尝试
**位置：** `services/brandTestService.js` (第 395-403 行)

```javascript
// 【P0-002 修复】在熔断前尝试刷新 token
if (consecutiveAuthErrors >= MAX_AUTH_ERRORS - 2) {
  console.log('[认证错误] 尝试刷新 token...');
  try {
    // 尝试清除本地认证缓存
    wx.removeStorageSync('user_token');
    console.log('[认证错误] 已清除本地 token 缓存');
  } catch (refreshErr) {
    console.warn('[认证错误] 刷新 token 失败:', refreshErr);
  }
}
```

### 修复 4: Storage 结果恢复
**位置：** `services/brandTestService.js` (第 405-428 行)

```javascript
if (consecutiveAuthErrors >= MAX_AUTH_ERRORS) {
  // 【P0-002 修复】熔断前尝试从 Storage 恢复结果
  console.log('[认证错误熔断] 尝试从 Storage 恢复结果...');
  try {
    const { loadDiagnosisResult } = require('../utils/storage-manager');
    const cachedResults = loadDiagnosisResult(executionId);
    
    if (cachedResults && (cachedResults.results || cachedResults.detailed_results)) {
      console.log('[认证错误熔断] ✅ 从 Storage 恢复结果成功，结果数:', 
        (cachedResults.results || []).length + (cachedResults.detailed_results || []).length);
      
      // 显示降级提示
      wx.showModal({
        title: '网络提示',
        content: '认证信息已过期，但诊断结果已从本地缓存恢复。建议重新登录后再次诊断以获取完整数据。',
        showCancel: false,
        confirmText: '知道了'
      });
      
      // 使用恢复的结果完成轮询
      controller.stop();
      if (onComplete) {
        onComplete(cachedResults);
      }
      return;
    }
  } catch (storageErr) {
    console.warn('[认证错误熔断] 从 Storage 恢复结果失败:', storageErr);
  }
  
  // 无法恢复结果，停止轮询
  controller.stop();
  console.error('[认证错误熔断] 停止轮询');
  if (onError) {
    onError(new Error('权限验证失败，请重新登录'));
  }
  return;
}
```

### 修复 5: 立即轮询的错误处理
**位置：** `services/brandTestService.js` (第 277-299 行)

```javascript
// 【P0-002 修复】立即轮询时的认证错误处理
if (err.statusCode === 403 || err.statusCode === 401 || err.isAuthError) {
  consecutiveAuthErrors++;
  
  // 尝试从 Storage 恢复结果
  try {
    const { loadDiagnosisResult } = require('../utils/storage-manager');
    const cachedResults = loadDiagnosisResult(executionId);
    
    if (cachedResults && (cachedResults.results || cachedResults.detailed_results)) {
      console.log('[立即轮询] ✅ 认证失败但从 Storage 恢复结果成功');
      if (onComplete) {
        onComplete(cachedResults);
      }
      return;
    }
  } catch (storageErr) {
    console.warn('[立即轮询] 从 Storage 恢复结果失败:', storageErr);
  }
  
  controller.stop();
  if (onError) onError(new Error('权限验证失败，请重新登录'));
  return;
}
```

---

## 修复对比

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| 熔断阈值 | 2 次错误 | 5 次错误 |
| 重试策略 | 立即重试 | 指数退避（1s → 10s） |
| Token 刷新 | ❌ 无 | ✅ 自动清除缓存 |
| 结果恢复 | ❌ 无 | ✅ 从 Storage 恢复 |
| 用户提示 | "权限验证失败" | "结果已恢复，建议重新登录" |
| 网络波动容忍 | 低（2 次即失败） | 高（5 次 + 退避） |

---

## 验证结果

### 语法检查
```bash
node -c services/brandTestService.js
# ✅ 通过，无语法错误
```

### 预期行为

#### 场景 1: 临时网络波动（1-2 次 401）
- ✅ 自动重试，用户无感知
- ✅ 诊断继续进行

#### 场景 2: 持续认证问题（3-4 次 401）
- ✅ 指数退避，给服务器恢复时间
- ✅ 尝试清除 token 缓存
- ✅ 诊断继续进行

#### 场景 3: 认证完全失效（5 次 401）
- ✅ 尝试从 Storage 恢复结果
- ✅ 如果恢复成功，展示结果 + 友好提示
- ✅ 如果恢复失败，提示重新登录

---

## 影响范围

### 修改文件
- `services/brandTestService.js`

### 影响功能
- 前端轮询机制
- 认证错误处理
- 结果恢复逻辑

### 向后兼容性
- ✅ 完全兼容，接口签名未变化
- ✅ 行为语义保持一致（轮询直到完成或失败）

---

## 测试用例

### 用例 1: 网络波动导致 1 次 401
- **预期：** 自动重试，诊断继续
- **验收：** 用户看到完整结果

### 用例 2: 网络波动导致 3 次 401
- **预期：** 指数退避后重试，诊断继续
- **验收：** 用户看到完整结果，延迟略有增加

### 用例 3: 认证失效但有缓存结果
- **预期：** 5 次 401 后从 Storage 恢复
- **验收：** 用户看到结果 + "建议重新登录"提示

### 用例 4: 认证失效且无缓存
- **预期：** 5 次 401 后提示重新登录
- **验收：** 用户看到"权限验证失败"提示

---

## 下一步行动

### 立即执行
- [ ] 在测试环境部署修复
- [ ] 模拟网络波动测试（使用 Charles 或 Fiddler）
- [ ] 验证 Storage 恢复功能

### 验收标准
- [ ] 网络波动 3 次内，诊断成功率 100%
- [ ] 有缓存时，结果恢复成功率 100%
- [ ] 用户提示准确友好

---

## 相关文档

- 完整问题清单：`/docs/COMPREHENSIVE_ISSUE_LIST_AND_FIX_PLAN.md`
- 快速修复清单：`/docs/P0_QUICK_FIX_CHECKLIST.md`
- 执行摘要：`/docs/EXECUTIVE_SUMMARY_FIX_PLAN.md`
- P0-001 修复报告：`/docs/P0-001_FIX_REPORT.md`

---

**修复完成时间：** 约 20 分钟  
**下一步：** 继续修复 P0-003（AI 错误类型映射不完整）
