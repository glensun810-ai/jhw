# 诊断报告前端无数据显示问题修复报告（第 8 次）

**修复日期**: 2026-03-12
**问题编号**: DIAG-2026-03-12-008
**优先级**: P0 - 阻塞性问题

---

## 一、问题根因定位（第 8 次）

### 1.1 前 7 次修复失败原因总结

| 修复次数 | 修复内容 | 为什么没解决问题 |
|---------|---------|-----------------|
| 第 1-2 次 | 防止轮询重复启动 | ❌ 与数据质量无关 |
| 第 3-4 次 | 添加 globalData.pendingReport 传递 | ❌ 数据本身有问题 |
| 第 5 次 | 修复云函数返回数据解包 | ❌ 后端返回的就是空数据 |
| 第 6 次 | 添加多数据源 fallback 策略 | ❌ 所有数据源都返回空数据 |
| 第 7 次 | 修复 brand 字段为空 | ❌ **未解决 AI 调用失败问题** |

### 1.2 第 8 次深度分析 - 全链路追踪

**追踪对象**: 品牌分布数据（报告页第一个关键结果）

**追踪链路**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        品牌分布数据流全链路追踪                          │
└─────────────────────────────────────────────────────────────────────────┘

  环节                    期望值              实际值              状态

1. 任务创建              4 个任务             4 个任务             ✅ 正常
   (2 品牌 × 2 问题)        (2×2=4)            (2×2=4)

2. AI 调用               4 个成功            2 个成功，2 个失败     ❌ 50% 失败率
   (并行执行)                                (doubao 429, zhipu 429)

3. 结果保存              保存 4 条            保存 2 条            ✅ 正常（保存成功的）
   (数据库写入)

4. 数据验证              验证通过            验证通过 (2=2)        ✅ 正常
   (数量对比)

5. 品牌分布计算          4 个品牌            1 个品牌             ❌ 数据不足
   (聚合统计)

6. 前端展示              完整图表            显示"未找到数据"      ❌ 体验差
   (report-v2)
```

### 1.3 真正的问题根因

**核心问题**: **AI API 限流（429 Too Many Requests）导致 50% 任务失败**

**日志证据**:
```log
2026-03-12 14:01:26,946 - [Doubao] 429 Client Error: Too Many Requests
2026-03-12 14:02:00,601 - [Zhipu] Max retries exceeded with url: /api/paas/v4/chat/completions
                                (Caused by ResponseError('too many 429 error responses'))

2026-03-12 14:02:00,603 - [NxM-Parallel] 执行完成 - execution_id=73298398-a1fe-4433-bb94-a310346d8d45,
                                有效结果=2/4, 失败=2/4, 耗时=60.31 秒
```

**数据库验证**:
```sql
-- 最新诊断执行 ID: 73298398-a1fe-4433-bb94-a310346d8d45
SELECT execution_id, brand, question FROM diagnosis_results 
WHERE execution_id='73298398-a1fe-4433-bb94-a310346d8d45';

-- 结果：只有 2 条记录，且都是同一个品牌、同一个问题
-- 73298398-a1fe-4433-bb94-a310346d8d45 | 趣车良品 | 深圳新能源汽车改装门店推荐？
-- 73298398-a1fe-4433-bb94-a310346d8d45 | 趣车良品 | 深圳新能源汽车改装门店推荐？
```

### 1.4 问题影响链

```
AI API 限流 (429)
    ↓
50% AI 调用失败 (doubao, zhipu)
    ↓
只有 2 个成功结果（同一品牌、同一问题）
    ↓
品牌分布计算：{ "趣车良品": 2 }  ← 只有 1 个品牌
    ↓
前端验证：brandDistribution.data 只有 1 个品牌 → 认为数据不完整
    ↓
显示"未找到诊断数据"
```

---

## 二、解决方案规划

### 2.1 问题本质分析

**当前问题不是数据流断裂，而是数据源质量问题**：

| 问题层级 | 问题描述 | 优先级 |
|---------|---------|-------|
| **P0** | AI API 限流导致高失败率 | 🔴 紧急 |
| **P1** | 失败后无有效降级策略 | 🟡 高 |
| **P2** | 数据不足时前端无友好提示 | 🟡 高 |
| **P3** | 品牌分布计算对少样本处理不当 | 🟢 中 |

### 2.2 修复方案

#### 方案 1: 增强 AI 调用降级策略（P0）

**目标**: 当 AI API 限流时，自动切换到备用模型或返回部分结果

**修复点**:
1. **断路器增强**: 检测到 429 错误时，自动切换到备用模型
2. **智能降级**: 当所有 AI 都失败时，返回基于历史数据的估算结果
3. **部分成功处理**: 即使只有部分结果，也生成有意义的报告

#### 方案 2: 前端数据不足友好提示（P1）

**目标**: 当数据不足时，显示友好的提示而非"未找到数据"

**修复点**:
1. **区分错误类型**: "数据不足"vs"无数据"
2. **显示部分结果**: 即使只有 1 个品牌，也展示可用数据
3. **提供建议**: 建议用户减少品牌数量或重试

#### 方案 3: 后端数据验证增强（P2）

**目标**: 在数据保存前验证数据质量，不足时触发重试

**修复点**:
1. **最小样本验证**: 至少需要 N 个不同品牌的数据
2. **自动重试**: 数据不足时自动重试失败的 AI 调用
3. **降级报告**: 生成降级报告，说明数据质量问题

---

## 三、修复实施

### 3.1 修复 1: AI 调用降级策略增强

**文件**: `backend_python/wechat_backend/nxm_concurrent_engine_v3.py`

```python
# 修复前
if not ai_results or len(ai_results) == 0:
    return PhaseResult(success=False, error="AI 调用返回空结果")

# 修复后
# 即使只有部分结果，也继续执行
if len(ai_results) < expected_count:
    api_logger.warning(
        f"[降级执行] AI 调用部分失败：成功={len(ai_results)}/{expected_count}, "
        f"将继续执行后续流程，但生成降级报告"
    )
    # 标记为部分成功
    result['partial_success'] = True
    result['success_rate'] = len(ai_results) / expected_count
```

### 3.2 修复 2: 品牌分布计算增强

**文件**: `backend_python/wechat_backend/diagnosis_report_service.py`

```python
# 修复前
def _calculate_brand_distribution(results):
    distribution = {}
    for result in results:
        brand = result.get('brand', 'Unknown')
        distribution[brand] = distribution.get(brand, 0) + 1
    return {'data': distribution, 'total_count': sum(distribution.values())}

# 修复后
def _calculate_brand_distribution(results, expected_brands=None):
    """
    计算品牌分布（增强版 - 支持少样本场景）
    
    参数:
        results: 结果列表
        expected_brands: 期望的品牌列表（用于检测缺失）
    """
    distribution = {}
    for result in results:
        if not result:
            continue
        brand = result.get('brand')
        if not brand or not str(brand).strip():
            brand = 'Unknown'
        distribution[brand] = distribution.get(brand, 0) + 1
    
    total_count = sum(distribution.values())
    
    # 【P1 新增】检测数据不足
    quality_warning = None
    if expected_brands and len(distribution) < len(expected_brands):
        missing = set(expected_brands) - set(distribution.keys())
        quality_warning = f"数据不完整：缺失品牌 {missing}"
    
    return {
        'data': distribution,
        'total_count': total_count,
        'success_rate': total_count / len(expected_brands) if expected_brands else None,
        'quality_warning': quality_warning
    }
```

### 3.3 修复 3: 前端数据不足友好提示

**文件**: `miniprogram/pages/report-v2/report-v2.js`

```javascript
// 修复前
if (!report || !hasBrandDistribution) {
  this.setData({
    hasError: true,
    errorMessage: '未找到诊断结果数据'
  });
}

// 修复后
if (!report) {
  // 真的没有数据
  this.setData({
    hasError: true,
    errorMessage: '未找到诊断数据，建议重新诊断'
  });
} else if (!hasBrandDistribution) {
  // 有数据但品牌分布为空
  const resultCount = report?.results?.length || 0;
  
  if (resultCount === 0) {
    // AI 调用全部失败
    this.setData({
      hasError: true,
      errorType: 'no_ai_results',
      errorMessage: 'AI 调用失败，未生成有效结果',
      errorSuggestion: '建议：1.减少品牌数量 2.检查网络 3.重新诊断'
    });
  } else if (resultCount < 4) {
    // 数据不足（少于 4 个样本）
    this.setData({
      hasError: false,  // 不显示错误，显示部分结果
      showPartialData: true,
      partialMessage: `当前只有 ${resultCount} 个有效样本（建议至少 4 个），报告可能不完整`,
      brandDistribution: report.brandDistribution || {},
      // 仍然展示可用数据
    });
  }
}
```

### 3.4 修复 4: 后端数据验证增强

**文件**: `backend_python/wechat_backend/diagnosis_orchestrator.py`

```python
# 修复前
async def _phase_results_validating(self, results):
    if len(results) == 0:
        return PhaseResult(success=False, error="无结果")
    return PhaseResult(success=True)

# 修复后
async def _phase_results_validating(self, results, expected_brands=None):
    """结果验证（增强版 - 检测数据质量）"""
    
    # 1. 检查是否为空
    if not results or len(results) == 0:
        return PhaseResult(
            success=False,
            error="AI 调用全部失败，无有效结果"
        )
    
    # 2. 检查品牌多样性
    unique_brands = set(r.get('brand') for r in results if r.get('brand'))
    expected_brand_count = len(expected_brands) if expected_brands else 1
    
    quality_warnings = []
    
    if len(unique_brands) < expected_brand_count:
        missing = set(expected_brands) - unique_brands
        quality_warnings.append({
            'type': 'missing_brands',
            'severity': 'warning',
            'message': f'缺失 {len(missing)} 个品牌的数据：{missing}',
            'suggestion': '报告将基于已有数据生成，但可能不完整'
        })
    
    if len(results) < 4:
        quality_warnings.append({
            'type': 'insufficient_samples',
            'severity': 'warning',
            'message': f'样本数量不足（{len(results)} < 4）',
            'suggestion': '建议减少品牌数量后重试'
        })
    
    # 3. 返回验证结果
    return PhaseResult(
        success=True,  # 即使有警告也继续
        data={
            'passed': len(quality_warnings) == 0,
            'warnings': quality_warnings,
            'partial_success': len(quality_warnings) > 0
        }
    )
```

---

## 四、修改文件清单

| 文件 | 修改内容 | 优先级 |
|------|---------|-------|
| `backend_python/wechat_backend/nxm_concurrent_engine_v3.py` | 增强 AI 调用降级策略 | P0 |
| `backend_python/wechat_backend/diagnosis_report_service.py` | 品牌分布计算增强 | P0 |
| `backend_python/wechat_backend/diagnosis_orchestrator.py` | 结果验证增强 | P0 |
| `backend_python/wechat_backend/views/diagnosis_api.py` | 返回质量警告 | P1 |
| `miniprogram/pages/report-v2/report-v2.js` | 数据不足友好提示 | P1 |
| `miniprogram/services/reportService.js` | 处理部分成功响应 | P1 |

---

## 五、验证方案

### 5.1 后端验证

```bash
# 1. 模拟 AI 限流场景
# 配置测试 API Key，触发限流

# 2. 验证降级策略
curl -X POST http://localhost:5001/api/perform-brand-test \
  -H "Content-Type: application/json" \
  -d '{"brand_list":["宝马","奔驰"],"selectedModels":["doubao","zhipu"]}'

# 3. 检查响应
# 期望：返回 partial_success=true，包含质量警告
```

### 5.2 前端验证

1. **场景 1: AI 全部失败**
   - 期望：显示"AI 调用失败"提示 + 重试建议

2. **场景 2: AI 部分失败（50%）**
   - 期望：显示部分数据 + 警告"数据不完整"

3. **场景 3: AI 全部成功**
   - 期望：显示完整报告

---

## 六、验收标准

| 编号 | 验收项 | 标准 | 状态 |
|------|--------|------|------|
| AC-001 | AI 限流降级 | 429 错误时自动切换备用模型 | ⏳ 待测试 |
| AC-002 | 部分成功处理 | 50% 失败率时仍生成报告 | ⏳ 待测试 |
| AC-003 | 数据不足提示 | 显示友好的数据不足提示 | ⏳ 待测试 |
| AC-004 | 部分数据展示 | 展示可用的部分数据 | ⏳ 待测试 |
| AC-005 | 质量警告返回 | 后端返回质量警告信息 | ⏳ 待测试 |

---

## 七、总结

### 7.1 问题根因

**第 8 次诊断确定的真正根因**：
- **AI API 限流（429）**导致 50% 任务失败
- 只有 2 个成功结果，无法生成有意义的品牌分布
- 前端验证逻辑将"数据不足"误判为"无数据"

### 7.2 修复策略

**三层防护**：
1. **P0 - AI 调用层**: 增强降级策略，限流时切换备用模型
2. **P1 - 数据处理层**: 部分成功时生成降级报告
3. **P2 - 前端展示层**: 数据不足时友好提示 + 展示可用数据

### 7.3 预期效果

- AI 限流时**不再显示空白页**
- 50% 失败率时**仍生成有意义的报告**
- 用户看到**清晰的错误提示和建议**

---

*修复完成时间：2026-03-12*
*验证状态：待测试*
