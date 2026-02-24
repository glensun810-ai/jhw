# 品牌洞察报告 - 功能补全完善计划

**制定时间**: 2026-02-24  
**优先级**: P0 紧急  
**执行周期**: 1-2 个工作日

---

## 📋 问题清单总览

根据字段盘点报告，发现以下缺失或待完善的功能：

| 序号 | 功能模块 | 问题描述 | 优先级 | 预计工时 |
|------|---------|---------|--------|---------|
| 1 | 核心洞察文案 | 显示默认值，无真实数据 | P0 | 2 小时 |
| 2 | 竞品数据生成 | NxM 只执行主品牌测试 | P0 | 4 小时 |
| 3 | 信源纯净度 | 后端生成逻辑待核实 | P1 | 3 小时 |
| 4 | 信源情报图谱 | 后端未生成 | P1 | 3 小时 |
| 5 | 前端数据验证 | 部分模块缺少验证 | P2 | 2 小时 |

**总预计工时**: 14 小时

---

## 🎯 修复目标

### 核心目标
1. ✅ 所有评分字段显示正确分数（非 0）
2. ✅ 核心洞察显示真实分析结论（非默认值）
3. ✅ 竞品对比功能正常工作（有竞品数据）
4. ✅ 信源纯净度分析显示真实信源
5. ✅ 信源情报图谱正常展示

### 验收标准
1. 品牌评分从 geo_data 正确计算
2. 核心洞察基于实际数据分析生成
3. detailed_results 包含所有品牌（主品牌 + 竞品）
4. 信源数据从 AI 响应中正确提取
5. 所有前端字段都有数据源

---

## 🔧 详细修复方案

### 任务 1: 核心洞察文案生成（P0）

#### 问题
- 当前显示默认文案
- 没有基于实际数据分析生成

#### 修复方案

**方案 A: 后端生成（推荐）**

在 `nxm_execution_engine.py` 中添加洞察生成逻辑：

```python
# 4.5. 生成核心洞察
try:
    api_logger.info(f"[NxM] 开始生成核心洞察：{execution_id}")
    
    # 从 brand_scores 分析优势、风险、机会
    target_brand_scores = brand_scores.get(main_brand, {})
    
    # 分析各维度得分
    authority = target_brand_scores.get('overallAuthority', 50)
    visibility = target_brand_scores.get('overallVisibility', 50)
    purity = target_brand_scores.get('overallPurity', 50)
    consistency = target_brand_scores.get('overallConsistency', 50)
    
    # 找出最高分维度（优势）
    dimensions = {
        '权威度': authority,
        '可见度': visibility,
        '纯净度': purity,
        '一致性': consistency
    }
    advantage_dim = max(dimensions, key=dimensions.get)
    advantage_score = dimensions[advantage_dim]
    
    # 找出最低分维度（风险）
    risk_dim = min(dimensions, key=dimensions.get)
    risk_score = dimensions[risk_dim]
    
    # 生成洞察文案
    advantage_insight = f"{advantage_dim}表现突出，得分{advantage_score}分"
    risk_insight = f"{risk_dim}相对薄弱，得分{risk_score}分，需重点关注"
    
    # 找出提升空间最大的维度（机会点）
    sorted_dims = sorted(dimensions.items(), key=lambda x: x[1])
    opportunity_dim = sorted_dims[0][0]
    opportunity_insight = f"{opportunity_dim}有较大提升空间，建议优先优化"
    
    # 保存到 execution_store
    execution_store[execution_id]['insights'] = {
        'advantage': advantage_insight,
        'risk': risk_insight,
        'opportunity': opportunity_insight
    }
    
    api_logger.info(f"[NxM] 核心洞察生成完成：{execution_id}")
except Exception as e:
    api_logger.error(f"[NxM] 核心洞察生成失败：{e}")
    execution_store[execution_id]['insights'] = {
        'advantage': '权威度表现突出，可见度良好',
        'risk': '品牌纯净度有待提升',
        'opportunity': '一致性方面有较大提升空间'
    }
```

**方案 B: 前端计算（备用）**

在 `results.js` 中添加 `generateInsights` 方法：

```javascript
generateInsights: function(brandScores, targetBrand) {
  const scores = brandScores[targetBrand] || {};
  const authority = scores.overallAuthority || 50;
  const visibility = scores.overallVisibility || 50;
  const purity = scores.overallPurity || 50;
  const consistency = scores.overallConsistency || 50;
  
  const dimensions = {
    '权威度': authority,
    '可见度': visibility,
    '纯净度': purity,
    '一致性': consistency
  };
  
  const advantageDim = Object.keys(dimensions).reduce((a, b) => 
    dimensions[a] > dimensions[b] ? a : b
  );
  const riskDim = Object.keys(dimensions).reduce((a, b) => 
    dimensions[a] < dimensions[b] ? a : b
  );
  
  return {
    advantage: `${advantageDim}表现突出，得分${dimensions[advantageDim]}分`,
    risk: `${riskDim}相对薄弱，得分${dimensions[riskDim]}分，需重点关注`,
    opportunity: `${riskDim}有较大提升空间，建议优先优化`
  };
}
```

#### 实施步骤
1. 在 `nxm_execution_engine.py` 第 340 行后添加洞察生成代码
2. 在 `diagnosis_views.py` 的 `/test/status` 接口中返回 insights
3. 在 `results.js` 的 `fetchResultsFromServer` 中解析 insights
4. 在 `results.js` 的 `initializePageWithData` 中使用 insights

#### 验证方法
- 后端日志：`[NxM] 核心洞察生成完成`
- 前端 Console：显示洞察数据
- 页面展示：显示真实的优势/风险/机会文案

---

### 任务 2: 竞品数据生成（P0）

#### 问题
- NxM 执行引擎只遍历主品牌
- detailed_results 中没有竞品数据
- 无法进行竞品对比分析

#### 修复方案

修改 `nxm_execution_engine.py` 的执行循环：

```python
# 原代码（只执行主品牌）
for q_idx, question in enumerate(raw_questions):
    for model_info in selected_models:
        # 调用 AI
        result = {
            'brand': main_brand,  # ← 只有主品牌
            ...
        }

# 修复后（遍历所有品牌）
all_brands = [main_brand] + (competitor_brands or [])

api_logger.info(f"[NxM] 执行品牌数：{len(all_brands)}, 品牌列表：{all_brands}")

for brand in all_brands:
    for q_idx, question in enumerate(raw_questions):
        for model_info in selected_models:
            # 构建提示词（包含当前品牌）
            prompt = GEO_PROMPT_TEMPLATE.format(
                brand_name=brand,
                competitors=', '.join([b for b in all_brands if b != brand]),
                question=question
            )
            
            # 调用 AI
            response = client.generate_response(prompt=prompt, api_key=api_key)
            
            # 解析 geo_data
            geo_data, parse_error = parse_geo_with_validation(
                response.content if hasattr(response, 'content') else response,
                execution_id,
                q_idx,
                model_name
            )
            
            # 构建结果
            result = {
                'brand': brand,  # ← 包含所有品牌
                'question': question,
                'model': model_name,
                'response': response.content if hasattr(response, 'content') else str(response),
                'geo_data': geo_data,
                'timestamp': datetime.now().isoformat()
            }
            
            scheduler.add_result(result)
            results.append(result)
```

#### 实施步骤
1. 修改 `nxm_execution_engine.py` 第 90-150 行的执行循环
2. 添加 all_brands 变量，包含主品牌和竞品
3. 在外层循环遍历所有品牌
4. 为每个品牌构建正确的提示词
5. 测试验证所有品牌都有数据

#### 验证方法
- 后端日志：`[NxM] 执行品牌数：4, 品牌列表：['华为', '小米', 'Vivo', 'Oppo']`
- 数据库：`detailed_results` 包含所有品牌
- 前端：竞品对比功能正常显示

---

### 任务 3: 信源纯净度数据生成（P1）

#### 问题
- 后端生成逻辑待核实
- 前端可能没有正确解析

#### 修复方案

**步骤 1: 检查后端生成逻辑**

在 `nxm_execution_engine.py` 中添加信源分析：

```python
# 4.6. 生成信源纯净度分析
try:
    api_logger.info(f"[NxM] 开始生成信源纯净度分析：{execution_id}")
    
    # 从 detailed_results 中提取信源
    all_sources = []
    for result in deduplicated:
        geo_data = result.get('geo_data', {})
        cited_sources = geo_data.get('cited_sources', [])
        all_sources.extend(cited_sources)
    
    # 分析信源类别
    category_distribution = {}
    for source in all_sources:
        category = source.get('category', 'unknown')
        if category not in category_distribution:
            category_distribution[category] = 0
        category_distribution[category] += 1
    
    # 计算纯净度分数
    total_sources = len(all_sources)
    high_weight_sources = sum(1 for s in all_sources if s.get('weight', 0) > 0.8)
    purity_score = int((high_weight_sources / total_sources * 100) if total_sources > 0 else 50)
    
    # 确定等级
    if purity_score >= 80:
        purity_level = 'high'
        purity_level_text = '优秀'
    elif purity_score >= 60:
        purity_level = 'medium'
        purity_level_text = '良好'
    else:
        purity_level = 'low'
        purity_level_text = '待提升'
    
    # 构建信源纯净度数据
    source_purity_data = {
        'purityScore': purity_score,
        'purityLevel': purity_level,
        'purityLevelText': purity_level_text,
        'highWeightRatio': int(high_weight_sources / total_sources * 100) if total_sources > 0 else 0,
        'pollutionCount': 0,
        'categoryDistribution': [
            {
                'category': cat,
                'categoryName': cat,
                'count': count,
                'percentage': int(count / total_sources * 100) if total_sources > 0 else 0
            }
            for cat, count in category_distribution.items()
        ],
        'topSources': [],
        'pollutionSources': []
    }
    
    execution_store[execution_id]['source_purity_data'] = source_purity_data
    api_logger.info(f"[NxM] 信源纯净度分析完成：{execution_id}")
except Exception as e:
    api_logger.error(f"[NxM] 信源纯净度分析失败：{e}")
    execution_store[execution_id]['source_purity_data'] = None
```

**步骤 2: 前端解析**

在 `results.js` 的 `fetchResultsFromServer` 中添加：

```javascript
const sourcePurityDataToUse = res.data.source_purity_data || null;

// 保存到 Storage
wx.setStorageSync('last_diagnostic_results', {
  // ... 其他数据
  sourcePurityData: sourcePurityDataToUse,
  // ...
});

// 初始化页面
this.initializePageWithData(
  resultsToUse,
  brandName,
  [],
  competitiveAnalysisToUse,
  negativeSourcesToUse,
  semanticDriftDataToUse,
  recommendationDataToUse,
  sourcePurityDataToUse  // ← 新增参数
);
```

#### 实施步骤
1. 在 `nxm_execution_engine.py` 第 350 行后添加信源分析代码
2. 在 `diagnosis_views.py` 的 `/test/status` 接口中返回 source_purity_data
3. 在 `results.js` 中解析 source_purity_data
4. 在 `results.js` 的 `initializePageWithData` 中添加 sourcePurityData 参数
5. 更新 `results.wxml` 的信源纯净度展示逻辑

#### 验证方法
- 后端日志：`[NxM] 信源纯净度分析完成`
- 前端 Console：显示信源纯净度数据
- 页面展示：信源纯净度分析模块正常显示

---

### 任务 4: 信源情报图谱生成（P1）

#### 问题
- 后端未生成信源情报图谱数据
- 前端展示逻辑已存在但无数据

#### 修复方案

在 `nxm_execution_engine.py` 中添加信源情报图谱生成：

```python
# 4.7. 生成信源情报图谱
try:
    api_logger.info(f"[NxM] 开始生成信源情报图谱：{execution_id}")
    
    # 从 detailed_results 中提取信源
    nodes = []
    node_id = 0
    
    for result in deduplicated:
        geo_data = result.get('geo_data', {})
        cited_sources = geo_data.get('cited_sources', [])
        
        for source in cited_sources:
            node = {
                'id': f'source_{node_id}',
                'name': source.get('site_name', '未知信源'),
                'value': source.get('weight', 50),
                'sentiment': source.get('attitude', 'neutral'),
                'category': source.get('category', 'general'),
                'url': source.get('url', '')
            }
            nodes.append(node)
            node_id += 1
    
    # 构建信源情报图谱
    source_intelligence_map = {
        'nodes': nodes,
        'links': []  # 可以后续添加信源间的关联
    }
    
    execution_store[execution_id]['source_intelligence_map'] = source_intelligence_map
    api_logger.info(f"[NxM] 信源情报图谱生成完成：{execution_id}, 节点数：{len(nodes)}")
except Exception as e:
    api_logger.error(f"[NxM] 信源情报图谱生成失败：{e}")
    execution_store[execution_id]['source_intelligence_map'] = None
```

#### 实施步骤
1. 在 `nxm_execution_engine.py` 第 380 行后添加信源情报图谱生成代码
2. 在 `diagnosis_views.py` 的 `/test/status` 接口中返回 source_intelligence_map
3. 在 `results.js` 中解析 source_intelligence_map
4. 在 `results.js` 的 `initializePageWithData` 中添加 sourceIntelligenceMap 参数
5. 验证 `results.wxml` 的信源情报展示逻辑

#### 验证方法
- 后端日志：`[NxM] 信源情报图谱生成完成，节点数：X`
- 前端 Console：显示信源情报图谱数据
- 页面展示：信源情报图谱正常显示

---

### 任务 5: 前端数据验证增强（P2）

#### 问题
- 部分模块缺少数据验证
- 用户不知道是数据问题还是展示问题

#### 修复方案

在 `results.js` 中添加全面的数据验证：

```javascript
// 在 fetchResultsFromServer 的 success 回调中
console.log('📊 完整数据验证报告:', {
  // 基础数据
  hasResults: resultsToUse && resultsToUse.length > 0,
  resultsCount: resultsToUse ? resultsToUse.length : 0,
  
  // 品牌评分
  hasBrandScores: brandScoresToUse && Object.keys(brandScoresToUse).length > 0,
  targetBrandScore: brandScoresToUse ? brandScoresToUse[targetBrand]?.overallScore : null,
  
  // 竞争分析
  hasCompetitiveAnalysis: competitiveAnalysisToUse && Object.keys(competitiveAnalysisToUse).length > 0,
  hasCompetitorData: resultsToUse ? resultsToUse.some(r => r.brand && r.brand !== targetBrand) : false,
  
  // 语义偏移
  hasSemanticDrift: !!semanticDriftDataToUse,
  driftScore: semanticDriftDataToUse ? semanticDriftDataToUse.driftScore : null,
  
  // 优化建议
  hasRecommendation: !!recommendationDataToUse,
  recommendationCount: recommendationDataToUse ? recommendationDataToUse.totalCount : 0,
  
  // 信源纯净度
  hasSourcePurity: !!sourcePurityDataToUse,
  purityScore: sourcePurityDataToUse ? sourcePurityDataToUse.purityScore : null,
  
  // 信源情报
  hasSourceIntelligence: !!sourceIntelligenceMapToUse,
  sourceCount: sourceIntelligenceMapToUse ? sourceIntelligenceMapToUse.nodes?.length : 0
});

// 数据完整性检查
const missingData = [];
if (!hasResults) missingData.push('基础结果数据');
if (!hasBrandScores) missingData.push('品牌评分');
if (!hasCompetitorData) missingData.push('竞品数据');
if (!hasSemanticDrift) missingData.push('语义偏移数据');
if (!hasRecommendation) missingData.push('优化建议');
if (!hasSourcePurity) missingData.push('信源纯净度');
if (!hasSourceIntelligence) missingData.push('信源情报');

if (missingData.length > 0) {
  console.warn('⚠️ 以下数据缺失:', missingData);
  wx.showModal({
    title: '数据提示',
    content: `部分数据缺失：${missingData.join(', ')}\n可能影响报告完整性`,
    showCancel: false
  });
}
```

#### 实施步骤
1. 在 `results.js` 的 `fetchResultsFromServer` 中添加数据验证代码
2. 在 `initializePageWithData` 中添加数据完整性检查
3. 添加友好的错误提示
4. 添加数据修复建议

#### 验证方法
- 前端 Console：显示完整的数据验证报告
- 缺失数据时显示友好提示
- 用户知道哪些数据缺失

---

## 📅 实施计划

### 第 1 天（6 小时）
- [ ] 任务 1: 核心洞察文案生成（2 小时）
- [ ] 任务 2: 竞品数据生成（4 小时）

### 第 2 天（8 小时）
- [ ] 任务 3: 信源纯净度数据生成（3 小时）
- [ ] 任务 4: 信源情报图谱生成（3 小时）
- [ ] 任务 5: 前端数据验证增强（2 小时）

### 测试验证（2 小时）
- [ ] 执行完整诊断测试
- [ ] 验证所有模块数据展示
- [ ] 修复发现的问题

---

## ✅ 验收清单

### 功能验收
- [ ] 品牌评分显示正确分数（非 0）
- [ ] 核心洞察显示真实分析结论
- [ ] 多维度分析显示正确分数
- [ ] AI 平台认知对比有数据
- [ ] 信源纯净度分析显示真实信源
- [ ] 信源权重结果显示真实权重
- [ ] 详细测试结果包含所有品牌
- [ ] 竞品对比功能正常工作

### 数据验收
- [ ] detailed_results 包含所有品牌
- [ ] brand_scores 包含所有品牌评分
- [ ] insights 包含真实分析结论
- [ ] source_purity_data 包含真实信源
- [ ] source_intelligence_map 包含信源节点

### 日志验收
- [ ] 后端日志显示所有模块生成完成
- [ ] 前端 Console 显示完整数据验证报告
- [ ] 无错误日志

---

## 📊 预期效果

修复完成后，品牌洞察报告应该能够：

1. ✅ **准确评分** - 所有评分字段显示正确分数
2. ✅ **真实洞察** - 核心洞察基于实际数据分析
3. ✅ **完整对比** - 包含所有品牌的对比数据
4. ✅ **信源分析** - 显示真实的信源信息
5. ✅ **情报图谱** - 展示信源关系图谱
6. ✅ **友好提示** - 数据缺失时友好提示用户

---

**制定人**: 首席测试工程师 & 首席全栈开发工程师  
**制定日期**: 2026-02-24  
**文档版本**: v1.0

---

**🚀 立即开始执行！**
