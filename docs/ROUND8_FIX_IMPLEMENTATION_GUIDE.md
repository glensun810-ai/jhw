# 第 8 次诊断修复 - 实施指南

**日期**: 2026-03-12
**问题**: AI API 限流导致 50% 失败率，前端显示"未找到数据"

---

## 一、根因总结

**真正根因**: AI API 限流（429 Too Many Requests）导致 50% 任务失败
- Doubao API: 429 限流
- Zhipu API: 429 限流
- 结果：4 个任务失败 2 个，只有 2 个成功结果
- 影响：品牌分布只有 1 个品牌数据，前端认为数据不足

---

## 二、修复清单

### P0 修复（必须）

1. **后端：结果验证增强** - 区分"无数据"和"数据不足"
2. **后端：品牌分布计算增强** - 支持少样本场景
3. **前端：数据不足友好提示** - 显示部分数据 + 警告

### P1 修复（重要）

4. **后端：AI 调用降级策略** - 429 时切换备用模型
5. **后端：部分成功处理** - 生成降级报告

---

## 三、修复步骤

### 步骤 1: 修改诊断编排器（结果验证增强）

**文件**: `backend_python/wechat_backend/services/diagnosis_orchestrator.py`

**位置**: `_phase_results_validating` 方法（约 973-1070 行）

**修改内容**:
```python
# 在验证逻辑中添加品牌多样性检查
unique_brands = set(r.get('brand') for r in results if r.get('brand'))
expected_brand_count = len(brand_list) if brand_list else 1

if len(unique_brands) < expected_brand_count:
    missing = set(brand_list) - unique_brands if brand_list else set()
    quality_warnings.append({
        'type': 'missing_brands',
        'severity': 'warning',
        'message': f'缺失 {len(missing)} 个品牌的数据：{missing}',
        'suggestion': '报告将基于已有数据生成，但可能不完整'
    })

# 即使有警告也继续执行（降级执行）
return PhaseResult(
    success=True,  # 改为 True，允许降级执行
    data={
        'passed': len(quality_warnings) == 0,
        'partial_success': len(quality_warnings) > 0,
        'warnings': quality_warnings,
        ...
    }
)
```

### 步骤 2: 修改报告服务（品牌分布计算增强）

**文件**: `backend_python/wechat_backend/diagnosis_report_service.py`

**位置**: `_calculate_brand_distribution` 方法（约 917-946 行）

**修改内容**:
```python
def _calculate_brand_distribution(self, results: List[Dict[str, Any]], 
                                   expected_brands: Optional[List[str]] = None) -> Dict[str, Any]:
    """计算品牌分布（增强版 - 支持少样本场景）"""
    distribution = {}
    for result in results:
        if not result:
            continue
        brand = result.get('brand')
        if not brand or not str(brand).strip():
            brand = 'Unknown'
        distribution[brand] = distribution.get(brand, 0) + 1
    
    total_count = sum(distribution.values())
    
    # 检测数据不足
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

### 步骤 3: 修改前端报告页（数据不足友好提示）

**文件**: `miniprogram/pages/report-v2/report-v2.js`

**位置**: `loadReportData` 方法（约 814-878 行）

**修改内容**:
```javascript
// 修改验证逻辑
if (!report) {
  // 真的没有数据
  this.setData({
    hasError: true,
    errorMessage: '未找到诊断数据，建议重新诊断'
  });
} else if (!hasBrandDistribution) {
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
    // 数据不足（少于 4 个样本）- 显示部分数据
    this.setData({
      hasError: false,
      showPartialData: true,
      partialMessage: `当前只有 ${resultCount} 个有效样本（建议至少 4 个），报告可能不完整`,
      brandDistribution: report.brandDistribution || {},
      sentimentDistribution: report.sentimentDistribution || {},
      keywords: report.keywords || []
    });
  }
}
```

### 步骤 4: 修改前端报告服务（处理部分成功响应）

**文件**: `miniprogram/services/reportService.js`

**位置**: `getFullReport` 方法

**修改内容**:
```javascript
async getFullReport(executionId, options = {}) {
  const res = await wx.cloud.callFunction({
    name: 'getDiagnosisReport',
    data: { executionId },
    timeout: 30000
  });

  const report = res.result?.data || res.result;

  // 【P0 关键修复 - 2026-03-12 第 8 次】处理部分成功响应
  if (report?.qualityHints?.partial_success) {
    console.warn('[ReportService] 部分成功，包含质量警告:', report.qualityHints.warnings);
    // 仍然返回报告，但标记为部分成功
    report.partialSuccess = true;
    report.qualityWarnings = report.qualityHints.warnings || [];
  }

  return report;
}
```

---

## 四、验证步骤

### 后端验证

```bash
# 1. 重启后端服务
cd backend_python && python app.py

# 2. 执行诊断（使用可能限流的 AI 模型）
curl -X POST http://localhost:5001/api/perform-brand-test \
  -H "Content-Type: application/json" \
  -d '{
    "brand_list": ["宝马", "奔驰"],
    "selectedModels": ["doubao", "zhipu"],
    "custom_question": "介绍一下{brandName}"
  }'

# 3. 获取执行 ID 并检查响应
# 期望：返回 execution_id，status=202

# 4. 轮询状态
curl http://localhost:5001/api/test/status/<execution_id>

# 期望：包含 quality_warning 字段
```

### 前端验证

1. **清除缓存**: 删除小程序 Storage
2. **执行诊断**: 输入 2 个品牌，选择 2 个 AI 模型
3. **观察日志**: 
   - 后端：搜索 `quality_warning`
   - 前端：搜索 `[ReportPageV2]`
4. **验证显示**:
   - 场景 A (AI 全部失败): 显示"AI 调用失败"提示
   - 场景 B (AI 部分失败): 显示部分数据 + 警告
   - 场景 C (AI 全部成功): 显示完整报告

---

## 五、回滚方案

如果修复后问题更严重：

```bash
# 1. Git 回滚
git checkout HEAD~1 -- backend_python/wechat_backend/services/diagnosis_orchestrator.py
git checkout HEAD~1 -- backend_python/wechat_backend/diagnosis_report_service.py
git checkout HEAD~1 -- miniprogram/pages/report-v2/report-v2.js

# 2. 重启后端
pkill -f "python app.py"
cd backend_python && python app.py &

# 3. 清除前端缓存
# 微信开发者工具 → 清除缓存 → 清除全部
```

---

## 六、预期效果

| 指标 | 修复前 | 修复后 |
|------|-------|-------|
| AI 限流时页面 | 空白 | 显示部分数据 + 警告 |
| 用户体验 | "未找到数据" | "数据不完整，建议..." |
| 数据可用率 | 0% (全部失败) | 50-100% (部分成功) |
| 用户困惑度 | 高 | 低（有清晰提示） |

---

*实施时间：2026-03-12*
*实施人：首席全栈工程师*
