# 品牌诊断报告 - 完整数据字典

**文档版本**: 1.0  
**更新日期**: 2026-03-22  
**用途**: 前后端联调对照表

---

## 🎯 核心诊断结果数据分类

### 一、核心指标数据 (metrics)
**后端计算**: `backend_python/wechat_backend/services/metrics_calculator.py`  
**前端展示**: `report-v2.js` - 核心指标卡片

| 字段名 | 类型 | 说明 | 计算逻辑 | 前端展示 |
|--------|------|------|---------|---------|
| `sov` | float | 声量份额 (0-100) | (品牌提及数 / 总提及数) × 100 | SOV 百分比 |
| `sentiment` | float | 情感得分 (0-100) | (正面数 - 负面数) / 总提及数 × 50 + 50 | 情感得分 |
| `rank` | int | 物理排名 (1,2,3...) | 按品牌提及数排序 | 排名第# |
| `influence` | float | 影响力得分 (0-100) | SOV×0.4 + 情感×0.3 + (1/排名)×100×0.3 | 影响力得分 |

**后端 API 返回格式**:
```json
{
  "metrics": {
    "sov": 85.0,
    "sentiment": 70.0,
    "rank": 1,
    "influence": 78.5
  }
}
```

**前端期望格式** (camelCase):
```javascript
{
  metrics: {
    sov: 85.0,
    sentiment: 70.0,
    rank: 1,
    influence: 78.5
  }
}
```

---

### 二、评分维度数据 (dimensionScores)
**后端计算**: `backend_python/wechat_backend/services/dimension_scorer.py`  
**前端展示**: `report-v2.js` - 评分维度进度条

| 字段名 | 类型 | 说明 | 计算逻辑 | 前端展示 |
|--------|------|------|---------|---------|
| `authority` | int | 权威度 (0-100) | 基于 AI 平台权威性、信源质量 | 权威度进度条 |
| `visibility` | int | 可见度 (0-100) | 基于提及频率、排名位置 | 可见度进度条 |
| `purity` | int | 纯净度 (0-100) | 基于负面提及比例 | 纯净度进度条 |
| `consistency` | int | 一致性 (0-100) | 基于跨模型一致性 | 一致性进度条 |

**后端 API 返回格式**:
```json
{
  "dimensionScores": {
    "authority": 80,
    "visibility": 75,
    "purity": 85,
    "consistency": 70
  }
}
```

---

### 三、问题诊断墙数据 (diagnosticWall)
**后端生成**: `backend_python/wechat_backend/services/diagnostic_wall_generator.py`  
**前端展示**: `report-v2.js` - 问题诊断墙卡片

| 字段名 | 类型 | 说明 | 生成逻辑 | 前端展示 |
|--------|------|------|---------|---------|
| `risk_levels.high` | array | 高风险问题列表 | SOV<20%、情感<-30、排名>3 | 高风险卡片 |
| `risk_levels.medium` | array | 中风险问题列表 | SOV<40%、情感<0、排名>2 | 中风险卡片 |
| `priority_recommendations` | array | 优化建议列表 | 基于风险类型匹配建议 | 建议列表 |

**后端 API 返回格式**:
```json
{
  "diagnosticWall": {
    "risk_levels": {
      "high": [
        {
          "id": "RISK-001",
          "title": "排名严重落后",
          "description": "您的品牌在 AI 回答中排名第 4 位",
          "severity": "high"
        }
      ],
      "medium": [
        {
          "id": "RISK-101",
          "title": "声量份额偏低",
          "description": "声量份额仅 35%",
          "severity": "medium"
        }
      ]
    },
    "priority_recommendations": [
      {
        "priority": "high",
        "category": "rank_improvement",
        "title": "提升物理排名",
        "description": "加强在权威渠道的品牌曝光",
        "actions": ["与更多权威媒体合作", "增加用户生成内容"],
        "expected_impact": "提升 AI 回答中的排名",
        "timeline": "2-3 个月"
      }
    ]
  }
}
```

---

### 四、品牌分布数据 (brandDistribution)
**后端计算**: `backend_python/wechat_backend/diagnosis_report_service.py`  
**前端展示**: `report-v2.js` - 品牌分布图表

| 字段名 | 类型 | 说明 | 计算逻辑 | 前端展示 |
|--------|------|------|---------|---------|
| `data` | object | 品牌提及次数 {品牌名：次数} | 从 AI 回答中提取品牌并统计 | 柱状图/饼图 |
| `totalCount` | int | 总提及次数 | 所有品牌提及数之和 | 总数显示 |
| `successRate` | float | 提取成功率 (0-1) | 成功提取数 / 总结果数 | 成功率标签 |

**后端 API 返回格式**:
```json
{
  "brandDistribution": {
    "data": {
      "趣车良品": 3,
      "车尚艺": 2,
      "车蚂蚁": 1
    },
    "totalCount": 6,
    "successRate": 1.0
  }
}
```

---

### 五、情感分布数据 (sentimentDistribution)
**后端计算**: `backend_python/wechat_backend/diagnosis_report_service.py`  
**前端展示**: `report-v2.js` - 情感分布图表

| 字段名 | 类型 | 说明 | 计算逻辑 | 前端展示 |
|--------|------|------|---------|---------|
| `data.positive` | int | 正面情感数量 | 统计正面情感的回答数 | 情感饼图 |
| `data.neutral` | int | 中性情感数量 | 统计中性情感的回答数 | 情感饼图 |
| `data.negative` | int | 负面情感数量 | 统计负面情感的回答数 | 情感饼图 |
| `totalCount` | int | 总情感分析数 | positive+neutral+negative | 总数显示 |

**后端 API 返回格式**:
```json
{
  "sentimentDistribution": {
    "data": {
      "positive": 3,
      "neutral": 2,
      "negative": 1
    },
    "totalCount": 6
  }
}
```

---

### 六、关键词数据 (keywords)
**后端提取**: `backend_python/wechat_backend/diagnosis_report_service.py`  
**前端展示**: `report-v2.js` - 关键词云/列表

| 字段名 | 类型 | 说明 | 提取逻辑 | 前端展示 |
|--------|------|------|---------|---------|
| `keywords` | array | 关键词列表 | 从 AI 回答中提取高频词 | 关键词云/标签 |

**后端 API 返回格式**:
```json
{
  "keywords": ["新能源汽车", "智能驾驶", "续航里程", "安全性", "性价比"]
}
```

---

### 七、原始诊断结果 (results)
**数据来源**: `backend_python/wechat_backend/database_repositories.py`  
**前端展示**: `report-v2.js` - 详细结果列表

| 字段名 | 类型 | 说明 | 来源 | 前端展示 |
|--------|------|------|------|---------|
| `id` | string | 结果 ID | diagnosis_results.id | 列表项 |
| `brand` | string | 品牌名称 | diagnosis_results.brand | 品牌名 |
| `model` | string | AI 模型 | diagnosis_results.model | 模型名 |
| `question` | string | 问题 | diagnosis_results.question | 问题文本 |
| `response` | string | AI 回答 | diagnosis_results.response | 回答内容 |
| `qualityScore` | int | 质量评分 (0-100) | diagnosis_results.quality_score | 质量标签 |
| `sentiment` | string | 情感 (positive/neutral/negative) | diagnosis_results.sentiment | 情感标签 |

**后端 API 返回格式**:
```json
{
  "results": [
    {
      "id": "result_1",
      "brand": "趣车良品",
      "model": "deepseek",
      "question": "这个品牌怎么样？",
      "response": "趣车良品是一个...",
      "qualityScore": 85,
      "qualityLevel": "excellent",
      "sentiment": "positive"
    }
  ]
}
```

---

### 八、品牌分析数据 (brandAnalysis)
**后端计算**: `backend_python/wechat_backend/services/brand_analysis_service.py`  
**前端展示**: `report-v2.js` - 品牌分析卡片

| 字段名 | 类型 | 说明 | 计算逻辑 | 前端展示 |
|--------|------|------|---------|---------|
| `userBrandAnalysis` | object | 用户品牌分析 | 提及率、平均排名、情感等 | 品牌分析卡片 |
| `competitorAnalysis` | array | 竞品分析列表 | 各竞品的提及率、排名等 | 竞品对比卡片 |
| `comparison` | object | 对比分析 | 用户品牌 vs 竞品 | 对比图表 |
| `top3Brands` | array | TOP3 品牌 | 从回答中提取的 TOP3 | TOP3 列表 |

**后端 API 返回格式**:
```json
{
  "brandAnalysis": {
    "userBrandAnalysis": {
      "brand": "趣车良品",
      "mentionedCount": 3,
      "totalResponses": 4,
      "mentionRate": 0.75,
      "averageRank": 1.5,
      "averageSentiment": 0.6,
      "isTop3": true
    },
    "competitorAnalysis": [
      {
        "brand": "车尚艺",
        "mentionedCount": 2,
        "mentionRate": 0.5,
        "averageRank": 2.0
      }
    ],
    "comparison": {
      "userBrandAdvantage": "提及率更高",
      "competitorAdvantage": "情感得分略高"
    },
    "top3Brands": [
      {"name": "趣车良品", "rank": 1},
      {"name": "车尚艺", "rank": 2},
      {"name": "车蚂蚁", "rank": 3}
    ]
  }
}
```

---

## 🔍 前后端数据流对照

### 后端数据流转
```
1. AI 调用结果 (results)
   ↓
2. 品牌分布计算 (_calculate_brand_distribution)
   ↓
3. 情感分布计算 (_calculate_sentiment_distribution)
   ↓
4. 关键词提取 (_extract_keywords)
   ↓
5. 核心指标计算 (calculate_diagnosis_metrics)
   ↓
6. 维度评分计算 (calculate_dimension_scores)
   ↓
7. 诊断墙生成 (generate_diagnostic_wall)
   ↓
8. 品牌分析 (BrandAnalysisService.analyze_brand_mentions)
   ↓
9. 聚合报告 (ReportAggregator.aggregate)
   ↓
10. API 返回 (diagnosis_api.get_full_report)
```

### 前端数据流转
```
1. wx.request 调用 API
   ↓
2. unifiedResponseHandler 处理响应
   ↓
3. diagnosisService.getFullReport 解包
   ↓
4. report-v2.js _loadFromAPI 加载
   ↓
5. report-v2.js _updateReportData 更新
   ↓
6. setData 渲染页面
```

---

## ✅ 联调检查清单

### 核心指标 (metrics)
- [ ] 后端计算 `sov`、`sentiment`、`rank`、`influence`
- [ ] API 返回包含 `metrics` 字段
- [ ] 前端正确解析 `metrics` 对象
- [ ] 前端展示 4 个指标卡片

### 评分维度 (dimensionScores)
- [ ] 后端计算 `authority`、`visibility`、`purity`、`consistency`
- [ ] API 返回包含 `dimensionScores` 字段
- [ ] 前端正确解析 `dimensionScores` 对象
- [ ] 前端展示 4 个进度条

### 问题诊断墙 (diagnosticWall)
- [ ] 后端生成 `risk_levels.high/medium`
- [ ] 后端生成 `priority_recommendations`
- [ ] API 返回包含 `diagnosticWall` 字段
- [ ] 前端正确解析并展示风险和建议

### 品牌分布 (brandDistribution)
- [ ] 后端统计各品牌提及次数
- [ ] API 返回包含 `brandDistribution.data`
- [ ] 前端正确解析并展示图表

### 情感分布 (sentimentDistribution)
- [ ] 后端统计 positive/neutral/negative 数量
- [ ] API 返回包含 `sentimentDistribution.data`
- [ ] 前端正确解析并展示图表

### 关键词 (keywords)
- [ ] 后端提取关键词列表
- [ ] API 返回包含 `keywords` 数组
- [ ] 前端正确解析并展示

### 原始结果 (results)
- [ ] 后端返回 diagnosis_results 列表
- [ ] API 返回包含 `results` 数组
- [ ] 前端正确解析并展示列表

### 品牌分析 (brandAnalysis)
- [ ] 后端计算用户品牌分析
- [ ] 后端计算竞品分析
- [ ] API 返回包含 `brandAnalysis` 对象
- [ ] 前端正确解析并展示

---

**下一步**: 逐一联调每个数据模块，确保前后端数据格式一致、展示正常
