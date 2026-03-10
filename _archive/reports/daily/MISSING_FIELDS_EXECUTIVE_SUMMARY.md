# 品牌诊断系统 - 字段缺失问题执行摘要

**创建时间**: 2026-02-24  
**紧急程度**: 🔴 P0 高优先级  
**影响范围**: 用户无法获取完整诊断报告

---

## 📊 问题概述

**当前状态**: 用户只能看到基础诊断结果，**缺失 3 个核心高级分析模块**

```
✅ 可正常展示:
- 品牌基础分析（品牌是否被提及）
- 基础评分（权威度、可见度、纯净度、一致性）
- AI 响应内容展示

❌ 缺失内容:
- 语义偏移分析（semantic_drift_data）
- 优化建议（recommendation_data）
- 负面信源分析（negative_sources）
- 信源 URL（cited_sources[].url）99% 丢失
```

---

## 🔴 核心缺失字段清单

### P0 级缺失（影响核心功能）

| # | 字段 | 当前状态 | 影响 | 缺失原因 |
|---|------|----------|------|----------|
| 1 | `semantic_drift_data` | ❌ null | 语义偏移分析完全无法展示 | 后端服务未调用 |
| 2 | `recommendation_data` | ❌ null | 优化建议完全无法展示 | 后端服务未调用 |
| 3 | `negative_sources` | ❌ null | 负面信源分析完全无法展示 | 后端服务未调用 |
| 4 | `cited_sources[].url` | ❌ 99% 丢失 | 信源追溯功能失效 | AI 不提供真实 URL |
| 5 | `cited_sources[].site_name` | ❌ 99% 丢失 | 信源追溯功能失效 | AI 不提供真实 URL |

### ⚠️ P1 级缺失（影响用户体验）

| # | 字段 | 当前状态 | 影响 | 缺失原因 |
|---|------|----------|------|----------|
| 1 | `geo_analysis.rank` | ⚠️ 多为 -1 | 品牌排名信息缺失 | AI 未输出排名 |
| 2 | `geo_analysis.sentiment` | ⚠️ 多为 0.0 | 情感分析缺失 | AI 倾向中性回答 |
| 3 | `firstMentionByPlatform` | ❌ 未计算 | 首次提及率缺失 | 前端未计算 |
| 4 | `interceptionRisks` | ❌ 未计算 | 拦截风险缺失 | 前端未计算 |

---

## 📈 字段完整率统计

| 字段类别 | 完整率 | 状态 |
|---------|--------|------|
| 基础字段（execution_id 等） | 100% | ✅ 正常 |
| GEO 分析字段 | 37.5% | ❌ 严重不足 |
| 信源字段 | 0% | ❌ 完全缺失 |
| 高级分析字段 | 0% | ❌ 完全缺失 |
| 计算字段（评分等） | 80% | ✅ 基本正常 |
| **总体完整率** | **63%** | ❌ 不及格 |

---

## 🔧 修复方案（按优先级）

### P0 修复（立即执行，共 6 小时）

#### 1. 集成语义偏移分析服务
```python
# 文件：backend_python/wechat_backend/views/diagnosis_views.py
# 位置：在 execute_nxm_test 完成后添加

from wechat_backend.semantic_analyzer import SemanticAnalyzer

analyzer = SemanticAnalyzer()
semantic_drift_data = analyzer.analyze_semantic_drift(
    execution_id=execution_id,
    results=results
)

# 存储到 execution_store
execution_store[execution_id]['semantic_drift_data'] = semantic_drift_data
```
**工作量**: 2 小时  
**影响**: 修复 semantic_drift_data 缺失

---

#### 2. 集成推荐建议生成服务
```python
from wechat_backend.recommendation_generator import RecommendationGenerator

generator = RecommendationGenerator()
recommendation_data = generator.generate_recommendations(
    execution_id=execution_id,
    results=results,
    negative_sources=negative_sources
)

# 存储到 execution_store
execution_store[execution_id]['recommendation_data'] = recommendation_data
```
**工作量**: 2 小时  
**影响**: 修复 recommendation_data 缺失

---

#### 3. 集成负面信源分析服务
```python
from wechat_backend.analytics.source_intelligence_processor import SourceIntelligenceProcessor

processor = SourceIntelligenceProcessor()
negative_sources = processor.analyze_negative_sources(
    execution_id=execution_id,
    results=results
)

# 存储到 execution_store
execution_store[execution_id]['negative_sources'] = negative_sources
```
**工作量**: 2 小时  
**影响**: 修复 negative_sources 缺失

---

### P1 修复（本周内执行，共 2 小时）

#### 4. 优化 AI Prompt 模板
修改 `GEO_PROMPT_TEMPLATE`，强制要求 AI 输出：
- 至少 2 个真实信源 URL
- 明确的品牌排名（1-10）
- 情感倾向（positive/negative/neutral）

**工作量**: 1 小时  
**影响**: 改善 GEO 分析字段质量

---

#### 5. 添加首次提及率计算
在前端 `reportAggregator.js` 中添加：
```javascript
const calculateFirstMentionByPlatform = (results) => {
  // 计算每个平台的首次提及率
  // ...
};
```

**工作量**: 1 小时  
**影响**: 修复 firstMentionByPlatform 缺失

---

## 📊 修复前后对比

| 指标 | 修复前 | 修复后 | 改善 |
|------|--------|--------|------|
| 总体完整率 | 63% | 92% | +29% |
| 高级分析字段 | 0% | 95% | +95% |
| GEO 分析字段 | 37.5% | 90% | +52.5% |
| 信源字段 | 0% | 80% | +80% |
| 用户可见模块 | 4 个 | 7 个 | +3 个 |

---

## 🎯 修复后用户可见内容

### 修复前（当前状态）
```
品牌诊断报告
├─ ✅ 品牌综合评分
├─ ✅ 四维分析（权威度/可见度/纯净度/一致性）
├─ ❌ 语义偏移分析（缺失）
├─ ❌ 优化建议（缺失）
├─ ❌ 负面信源分析（缺失）
└─ ✅ AI 响应内容展示
```

### 修复后（预期）
```
品牌诊断报告
├─ ✅ 品牌综合评分
├─ ✅ 四维分析
├─ ✅ 语义偏移分析（新增）
├─ ✅ 优化建议（新增）
├─ ✅ 负面信源分析（新增）
├─ ✅ 首次提及率（新增）
├─ ✅ 拦截风险（新增）
└─ ✅ AI 响应内容展示（含信源 URL）
```

---

## 📝 详细分析文档

完整分析请查看：
- `FIELD_MAPPING_AND_MISSING_ANALYSIS.md` - 完整字段映射与缺失分析
- `COMPREHENSIVE_VISUAL_ANALYSIS.md` - 全链路可视化分析
- `LOG_BASED_FAILURE_ANALYSIS.md` - 基于日志的时间线分析

---

## ✅ 行动建议

### 立即执行（今天）
1. [ ] 集成语义偏移分析服务（2 小时）
2. [ ] 集成推荐建议生成服务（2 小时）
3. [ ] 集成负面信源分析服务（2 小时）

### 本周内执行
4. [ ] 优化 AI Prompt 模板（1 小时）
5. [ ] 添加首次提及率计算（1 小时）

### 验证测试
6. [ ] 执行完整诊断流程测试
7. [ ] 验证所有字段是否正确展示
8. [ ] 用户验收测试

---

**预计总工作量**: 8 小时  
**预计完成时间**: 1-2 个工作日  
**预期效果**: 用户可获取完整诊断报告，所有核心功能正常

---

**报告结束**
