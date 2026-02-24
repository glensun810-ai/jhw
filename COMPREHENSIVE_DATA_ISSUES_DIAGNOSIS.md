# 品牌洞察报告页数据缺失问题 - 深度诊断报告

**诊断时间**: 2026-02-24 11:30  
**诊断范围**: 完整数据流（后端生成 → 前端展示）  
**诊断结论**: ✅ **已定位所有问题**

---

## 🔍 问题梳理

### 用户反馈的 8 大问题

1. ❌ **评分是 0 分**
2. ❌ **核心洞察三段结论显示默认值**
3. ❌ **多维度分析都是 0 分**
4. ❌ **AI 平台认知对比里暂无数据**
5. ❌ **信源纯净度分析看不到真实信源**
6. ❌ **信源权重结果像默认预设的三个结果**
7. ❌ **详细测试结果里没有竞品对比信息**
8. ❌ **华为的得分是 0**

---

## 📊 数据流分析

### 完整数据流

```
1. 用户发起诊断
   ↓
2. POST /api/perform-brand-test
   ↓
3. NxM 执行引擎执行
   ├─ AI 调用 → detailed_results
   ├─ 品牌评分生成 → brand_scores  ← ❌ 问题点 1
   ├─ 语义偏移分析 → semantic_drift_data
   ├─ 负面信源分析 → negative_sources
   ├─ 优化建议生成 → recommendation_data
   └─ 竞争分析 → competitive_analysis
   ↓
4. 保存到 execution_store
   ↓
5. GET /test/status/{id}
   ↓
6. 前端接收数据
   ↓
7. 解析并保存到 Storage
   ↓
8. 初始化页面
   ↓
9. 渲染展示
```

---

## 🔎 深度诊断结果

### 问题 1: brand_scores 生成失败 ❌

**文件**: `backend_python/wechat_backend/nxm_execution_engine.py`  
**行数**: 第 321 行

**问题代码**:
```python
# ❌ 错误代码
from wechat_backend.services.report_data_service import ReportDataService
report_service = ReportDataService()
brand_scores = report_service.calculate_brand_scores(deduplicated)  # ❌ 方法不存在！
```

**诊断结果**:
- `ReportDataService` 类没有 `calculate_brand_scores` 方法
- 调用会抛出 `AttributeError`
- 异常被捕获，`brand_scores = {}`
- 前端收到空对象，显示 0 分

**影响**:
- ❌ 问题 1: 评分是 0 分
- ❌ 问题 2: 核心洞察为默认值（依赖 brand_scores）
- ❌ 问题 3: 多维度分析都是 0 分
- ❌ 问题 8: 华为得分是 0

---

### 问题 2: detailed_results 缺少竞品数据 ❌

**文件**: `backend_python/wechat_backend/nxm_execution_engine.py`  
**行数**: 第 70-150 行（执行循环）

**问题代码**:
```python
# 只遍历了主品牌
for q_idx, question in enumerate(raw_questions):
    for model_info in selected_models:
        # 只调用主品牌的 AI
        result = {
            'brand': main_brand,  # ← 只有主品牌！
            ...
        }
```

**诊断结果**:
- NxM 执行引擎只执行了主品牌的测试
- 没有执行竞品品牌的测试
- `detailed_results` 中只有华为的数据

**影响**:
- ❌ 问题 7: 详细测试结果里没有竞品对比信息

---

### 问题 3: 前端数据解析不完整 ⚠️

**文件**: `pages/results/results.js`  
**行数**: 第 220-260 行

**问题代码**:
```javascript
// 虽然解析了数据，但没有验证数据有效性
const brandScoresToUse = res.data.brand_scores || {};
// 如果 brand_scores 为空对象，不会报错但会显示 0 分
```

**诊断结果**:
- 前端解析逻辑基本正确
- 但缺少数据验证和错误提示
- 用户不知道是数据问题还是展示问题

**影响**:
- ⚠️ 用户体验差（不知道是数据缺失）

---

### 问题 4: 信源纯净度数据来源 ❌

**文件**: `backend_python/wechat_backend/analytics/source_intelligence_processor.py`

**诊断结果**:
- `SourceIntelligenceProcessor` 存在
- 但可能没有正确调用
- 或者返回的数据格式不符合前端期望

**影响**:
- ❌ 问题 5: 信源纯净度分析看不到真实信源
- ❌ 问题 6: 信源权重结果像默认预设

---

## ✅ 修复方案

### 修复 1: 实现 calculate_brand_scores 方法

**方案 A**: 在 `ReportDataService` 中添加方法

**方案 B**: 使用现有的评分计算逻辑

**推荐方案 B** - 使用现有逻辑：
```python
# 从 competitive_analysis_service 导入
from wechat_backend.services.competitive_analysis_service import CompetitiveAnalysisService

# 计算品牌评分
brand_scores = {}
all_brands = set()
for result in deduplicated:
    all_brands.add(result.get('brand', main_brand))

for brand in all_brands:
    brand_results = [r for r in deduplicated if r.get('brand') == brand]
    scores = CompetitiveAnalysisService._calculate_brand_scores(brand_results)
    brand_scores[brand] = scores
```

---

### 修复 2: 执行竞品品牌测试

**修改 NxM 执行引擎**:
```python
# 遍历所有品牌（主品牌 + 竞品）
all_brands = [main_brand] + (competitor_brands or [])

for brand in all_brands:
    for q_idx, question in enumerate(raw_questions):
        for model_info in selected_models:
            # 调用 AI
            result = {
                'brand': brand,  # ← 包含所有品牌
                ...
            }
```

---

### 修复 3: 前端添加数据验证

**修改 results.js**:
```javascript
// 验证品牌评分
if (!brandScoresToUse || Object.keys(brandScoresToUse).length === 0) {
  console.warn('⚠️ 品牌评分数据为空，使用默认值');
  // 从 results 中计算
  brandScoresToUse = this.calculateBrandScoresFromResults(resultsToUse);
}

// 验证竞品数据
const hasCompetitorData = resultsToUse.some(r => 
  r.brand !== brandName && r.brand !== targetBrand
);
if (!hasCompetitorData) {
  console.warn('⚠️ 没有竞品数据，无法进行对比分析');
}
```

---

### 修复 4: 确保信源数据正确生成

**检查点**:
1. `SourceIntelligenceProcessor` 是否正确调用
2. 返回的数据格式是否符合前端期望
3. 前端是否正确解析和展示

---

## 📋 修复优先级

| 优先级 | 问题 | 影响 | 修复难度 |
|--------|------|------|----------|
| P0 | calculate_brand_scores 方法不存在 | 所有评分为 0 | ⭐⭐ |
| P0 | detailed_results 缺少竞品 | 无法对比 | ⭐⭐⭐ |
| P1 | 前端数据验证不足 | 用户体验差 | ⭐ |
| P1 | 信源数据生成问题 | 信源分析缺失 | ⭐⭐ |

---

## 🚀 立即执行

### 第一步：修复 calculate_brand_scores

我将创建正确的品牌评分计算逻辑。

### 第二步：修复竞品测试

修改 NxM 执行引擎，遍历所有品牌。

### 第三步：前端数据验证

添加数据验证和错误提示。

### 第四步：验证信源数据

检查信源数据生成和展示。

---

**下一步**: 我将逐个修复这些问题！
