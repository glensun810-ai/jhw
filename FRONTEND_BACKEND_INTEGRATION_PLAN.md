# 品牌诊断报告 - 前后端联调计划

**联调日期**: 2026-03-22  
**联调目标**: 确保每个诊断数据模块都能正确展示

---

## 📊 当前状态检查

### 后端返回数据检查 ✅
```
【1】核心指标 (metrics) ✅
  存在：True
  数据：{"sov": 0.0, "sentiment": 50.0, "rank": 2, "influence": 30.0}

【2】评分维度 (dimensionScores) ✅
  存在：True
  数据：{"authority": 0, "visibility": 0, "purity": 60, "consistency": 100}

【3】问题诊断墙 (diagnosticWall) ✅
  存在：True
  高风险数：0
  中风险数：0
  建议数：0

【4】品牌分布 (brandDistribution) ✅
  存在：True
  数据：{"data": {"特斯拉官方服务中心及授权钣喷中心": 1}, ...}

【5】情感分布 (sentimentDistribution) ✅
  存在：True
  数据：{"data": {"positive": 0, "neutral": 1, "negative": 0}, ...}

【6】关键词 (keywords) ⚠️
  存在：True
  数量：0
  数据：空

【7】原始结果 (results) ✅
  存在：True
  数量：1

【8】品牌分析 (brandAnalysis) ❌
  存在：False
  数据：空
```

### 前端数据处理检查
- ✅ `_processReportData` 方法存在
- ✅ 支持多种数据格式兼容
- ✅ 有降级计算逻辑

---

## 🔧 联调步骤

### 模块 1: 核心指标 (metrics)

**后端**: ✅ 已计算并返回
**前端**: 需要检查是否正确解析

**检查点**:
1. [ ] 前端 `reportService._processReportData` 是否处理 `metrics` 字段
2. [ ] 前端 `report-v2.js` 是否有 `data.metrics` 的 setData
3. [ ] WXML 是否有对应的 `{{metrics.sov}}` 等绑定

**修复步骤**:
```javascript
// reportService.js _processReportData 方法中添加
// 4. 处理核心指标数据
const metrics = report.metrics;
if (metrics && typeof metrics === 'object') {
  report.metrics = {
    sov: metrics.sov || 0,
    sentiment: metrics.sentiment || 0,
    rank: metrics.rank || 1,
    influence: metrics.influence || 0
  };
} else {
  report.metrics = { sov: 0, sentiment: 0, rank: 1, influence: 0 };
}
```

---

### 模块 2: 评分维度 (dimensionScores)

**后端**: ✅ 已计算并返回
**前端**: 需要检查是否正确解析

**检查点**:
1. [ ] 前端 `reportService._processReportData` 是否处理 `dimensionScores` 字段
2. [ ] 前端 `report-v2.js` 是否有 `data.dimensionScores` 的 setData
3. [ ] WXML 是否有对应的进度条绑定

**修复步骤**:
```javascript
// reportService.js _processReportData 方法中添加
// 5. 处理评分维度数据
const dimensionScores = report.dimensionScores;
if (dimensionScores && typeof dimensionScores === 'object') {
  report.dimensionScores = {
    authority: dimensionScores.authority || 0,
    visibility: dimensionScores.visibility || 0,
    purity: dimensionScores.purity || 0,
    consistency: dimensionScores.consistency || 0
  };
} else {
  report.dimensionScores = { authority: 50, visibility: 50, purity: 50, consistency: 50 };
}
```

---

### 模块 3: 问题诊断墙 (diagnosticWall)

**后端**: ✅ 已生成（但无风险和建议）
**前端**: 需要检查是否正确解析

**检查点**:
1. [ ] 前端 `reportService._processReportData` 是否处理 `diagnosticWall` 字段
2. [ ] 前端 `report-v2.js` 是否有 `data.diagnosticWall` 的 setData
3. [ ] WXML 是否有对应的风险列表和建议列表绑定

**修复步骤**:
```javascript
// reportService.js _processReportData 方法中添加
// 6. 处理问题诊断墙数据
const diagnosticWall = report.diagnosticWall;
if (diagnosticWall && typeof diagnosticWall === 'object') {
  report.diagnosticWall = {
    risk_levels: diagnosticWall.risk_levels || { high: [], medium: [] },
    priority_recommendations: diagnosticWall.priority_recommendations || []
  };
} else {
  report.diagnosticWall = { risk_levels: { high: [], medium: [] }, priority_recommendations: [] };
}
```

---

### 模块 4: 品牌分布 (brandDistribution)

**后端**: ✅ 已计算并返回
**前端**: 需要检查是否正确解析和展示

**检查点**:
1. [ ] 前端 `reportService._processReportData` 是否正确处理
2. [ ] 前端 `report-v2.js` 是否有 `data.brandDistribution` 的 setData
3. [ ] WXML 是否有对应的图表绑定

**状态**: ✅ 前端已有处理逻辑

---

### 模块 5: 情感分布 (sentimentDistribution)

**后端**: ✅ 已计算并返回
**前端**: 需要检查是否正确解析和展示

**检查点**:
1. [ ] 前端 `reportService._processReportData` 是否正确处理
2. [ ] 前端 `report-v2.js` 是否有 `data.sentimentDistribution` 的 setData
3. [ ] WXML 是否有对应的图表绑定

**状态**: ✅ 前端已有处理逻辑

---

### 模块 6: 关键词 (keywords)

**后端**: ⚠️ 返回空数组（需要数据量足够才能提取）
**前端**: 需要检查是否正确处理空数据

**检查点**:
1. [ ] 前端 `reportService._processReportData` 是否正确处理
2. [ ] 前端 `report-v2.js` 是否有 `data.keywords` 的 setData
3. [ ] WXML 是否有对应的关键词云绑定
4. [ ] 空数据时是否有友好提示

**修复建议**:
- 后端：需要至少 5 条有效结果才能提取关键词
- 前端：空数据时显示"数据不足，无法提取关键词"

---

### 模块 7: 原始结果 (results)

**后端**: ✅ 已返回
**前端**: 需要检查是否正确解析和展示

**检查点**:
1. [ ] 前端 `reportService._processReportData` 是否正确处理
2. [ ] 前端 `report-v2.js` 是否有 `data.results` 的 setData
3. [ ] WXML 是否有对应的列表绑定

**状态**: ✅ 前端已有处理逻辑

---

### 模块 8: 品牌分析 (brandAnalysis)

**后端**: ❌ 未返回（在 `analysis.brand_analysis` 中）
**前端**: 需要检查是否正确解析

**检查点**:
1. [ ] 后端是否在 `analysis` 对象中包含 `brand_analysis`
2. [ ] 前端 `reportService._processReportData` 是否正确处理
3. [ ] 前端 `report-v2.js` 是否有 `data.brandAnalysis` 的 setData
4. [ ] WXML 是否有对应的品牌分析卡片绑定

**修复步骤**:
```javascript
// reportService.js _processReportData 方法中添加
// 9. 处理品牌分析数据
const brandAnalysis = report.analysis?.brand_analysis;
if (brandAnalysis && typeof brandAnalysis === 'object') {
  report.brandAnalysis = {
    userBrandAnalysis: brandAnalysis.user_brand_analysis || {},
    competitorAnalysis: brandAnalysis.competitor_analysis || [],
    comparison: brandAnalysis.comparison || {},
    top3Brands: brandAnalysis.top3_brands || []
  };
} else {
  report.brandAnalysis = {};
}
```

---

## ✅ 联调验收标准

每个模块需要满足：
1. [ ] 后端正确计算并返回数据
2. [ ] 前端正确解析数据
3. [ ] 前端页面正确展示数据
4. [ ] 空数据时有友好提示

---

## 📝 下一步行动

1. **修复前端数据处理**: 在 `reportService.js` 中添加 `metrics`、`dimensionScores`、`diagnosticWall` 的处理逻辑
2. **检查前端页面绑定**: 确保 WXML 中有对应的数据绑定
3. **测试完整流程**: 执行新的诊断，验证所有模块正常展示
4. **优化空数据处理**: 对于数据量不足导致的空数据，添加友好提示

---

**联调负责人**: ___________  
**开始时间**: ___________  
**完成时间**: ___________
