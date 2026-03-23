# API 请求结果检查报告

**创建日期**: 2026-03-13  
**执行 ID**: `3f12b620-7ffa-4f5e-a0d7-c9839ce9beb9`  
**品牌**: 趣车良品

---

## 📊 数据库保存结果

### 1. 诊断报告主表 (diagnosis_reports)

| 字段 | 值 |
|------|-----|
| execution_id | `3f12b620-7ffa-4f5e-a0d7-c9839ce9beb9` |
| brand_name | `趣车良品` |
| competitor_brands | `["车尚艺"]` |
| status | `completed` |
| progress | `100` |
| stage | `completed` |
| is_completed | `1` |
| created_at | `2026-03-13T14:30:03.583846` |

### 2. 诊断结果明细表 (diagnosis_results)

**结果数量**: 1 条

| 字段 | 值 |
|------|-----|
| id | `52` |
| brand | `EV Power` |
| extracted_brand | `EV Power` |
| question | `深圳新能源汽车改装门店推荐？` |
| model | `qwen` |
| platform | `qwen` |
| quality_score | `0.0` |
| tokens_used | `0` |
| finish_reason | `stop` |
| status | `success` |
| response_content | `好的，基于我的了解，以下是我为您推荐的深圳新能源汽车改装门店：...` |

**新增字段检查**:
- ✅ `extracted_brand` - 有值
- ✅ `tokens_used` - 有值 (0)
- ✅ `finish_reason` - 有值 (`stop`)
- ✅ `platform` - 有值 (`qwen`)
- ⚠️ `request_id` - NULL
- ⚠️ `reasoning_content` - NULL
- ⚠️ `response_metadata` - 空对象 `{}`
- ⚠️ `geo_data` - NULL

### 3. 诊断分析表 (diagnosis_analysis)

**分析类型数量**: 2 种

| analysis_type | id |
|---------------|----|
| brand_analysis | 71 |
| competitive_analysis | 72 |

### 4. 诊断快照表 (diagnosis_snapshots)

**快照数量**: 1 条

| id | snapshot_reason | created_at |
|----|-----------------|------------|
| 44 | completed | 2026-03-13T14:31:53.172162 |

---

## 📡 API 返回数据格式

### 1. 服务端处理日志

```
[HistoryReport] 开始获取历史报告：3f12b620-7ffa-4f5e-a0d7-c9839ce9beb9
[get_by_execution_id] ✅ 获取结果：execution_id=..., count=1, brands=1
[品牌分布] 数据不完整：expected=['趣车良品', '车尚艺'], actual=['EV Power']
[HistoryReport] ✅ 历史报告获取成功：results=1, brands=1
```

### 2. API 返回字段检查

**前端必需字段**:

| 字段 | 状态 | 值 |
|------|------|-----|
| `brandDistribution` | ✅ | `{"data": {"EV Power": 1}, "totalCount": 1}` |
| `sentimentDistribution` | ✅ | `{"data": {"positive": 0, "neutral": 1, "negative": 0}}` |
| `keywords` | ⚠️ | `[]` (空数组) |
| `results` | ✅ | 1 条记录 |
| `detailedResults` | ✅ | 1 条记录 |
| `brandScores` | ❌ | 缺失 |

### 3. 字段命名风格转换

**snake_case → camelCase**:

```python
execution_id → executionId
report_id → reportId
brand_name → brandName
competitor_brands → competitorBrands
selected_models → selectedModels
is_completed → isCompleted
created_at → createdAt
completed_at → completedAt
brandDistribution → brandDistribution (保持不变)
sentimentDistribution → sentimentDistribution (保持不变)
detailed_results → detailedResults
```

---

## 🔍 发现的问题

### 1. 品牌字段不一致

**问题**: 
- 主品牌：`趣车良品`
- 竞品：`车尚艺`
- 结果中的品牌：`EV Power` (从 AI 响应中提取)

**原因**: AI 响应中提取的品牌与实际配置的品牌不匹配

**影响**: 
- `brandDistribution` 中缺少主品牌和竞品
- 品牌分布统计不准确

**日志**:
```
[品牌分布] 数据不完整：expected=['趣车良品', '车尚艺'], actual=['EV Power'], 
missing={'车尚艺', '趣车良品'}
```

### 2. keywords 为空

**问题**: `keywords` 字段返回空数组

**原因**: 结果明细中的 `geo_data` 为 NULL，无法从中提取关键词

**影响**: 前端关键词展示为空

### 3. brandScores 缺失

**问题**: API 返回数据中缺少 `brandScores` 字段

**原因**: `get_history_report()` 方法未从 `analysis` 中提取品牌评分

**影响**: 前端品牌评分模块无法显示数据

### 4. 部分新增字段为 NULL

**问题**: 以下字段在数据库中为 NULL 或空：
- `request_id`
- `reasoning_content`
- `response_metadata`
- `geo_data`

**原因**: 这些字段在 AI 调用时未保存或 AI 未返回

---

## ✅ 正常工作的部分

1. **数据库保存**:
   - ✅ 报告主数据正确保存
   - ✅ 结果明细正确保存
   - ✅ 分析数据正确保存
   - ✅ 快照正确创建

2. **API 检索**:
   - ✅ 能从数据库读取报告
   - ✅ 字段转换 (snake_case → camelCase) 正常工作
   - ✅ `brandDistribution` 有数据
   - ✅ `sentimentDistribution` 有数据
   - ✅ `results` / `detailedResults` 有数据

3. **新增字段支持**:
   - ✅ `extracted_brand` 已保存
   - ✅ `tokens_used` 已保存
   - ✅ `finish_reason` 已保存
   - ✅ `platform` 已保存

---

## 🔧 修复建议

### 1. 添加 brandScores 字段

**文件**: `diagnosis_report_service.py`

```python
def get_history_report(self, execution_id: str):
    # ... 现有代码 ...
    
    # 从 analysis 中提取 brandScores
    if 'brand_scores' in analysis:
        full_report['brandScores'] = analysis['brand_scores']
    elif 'brandScores' in analysis:
        full_report['brandScores'] = analysis['brandScores']
```

### 2. 生成默认关键词

**文件**: `diagnosis_report_service.py`

```python
def _extract_keywords(self, results: List) -> List:
    # 如果 geo_data 为空，从 response_content 提取
    if not keywords:
        keywords = self._extract_keywords_from_content(results)
    
    return keywords
```

### 3. 品牌字段映射优化

**文件**: `diagnosis_report_service.py`

```python
def _calculate_brand_distribution(self, results, expected_brands):
    # 使用 extracted_brand 而不是 brand
    # 添加品牌名称映射逻辑
    brand_mapping = {
        'EV Power': '趣车良品',  # 示例映射
        # ... 更多映射
    }
```

---

## 📋 完整 API 返回示例

```json
{
  "executionId": "3f12b620-7ffa-4f5e-a0d7-c9839ce9beb9",
  "brandName": "趣车良品",
  "competitorBrands": ["车尚艺"],
  "status": "completed",
  "progress": 100,
  "isCompleted": true,
  
  "brandDistribution": {
    "data": {"EV Power": 1},
    "totalCount": 1,
    "successRate": 0.5,
    "qualityWarning": "数据不完整：缺失品牌 {'车尚艺', '趣车良品'}"
  },
  
  "sentimentDistribution": {
    "data": {"positive": 0, "neutral": 1, "negative": 0},
    "totalCount": 1
  },
  
  "keywords": [],
  
  "results": [{
    "id": 52,
    "brand": "EV Power",
    "extractedBrand": "EV Power",
    "question": "深圳新能源汽车改装门店推荐？",
    "model": "qwen",
    "responseContent": "好的，基于我的了解...",
    "qualityScore": 0.0,
    "tokensUsed": 0,
    "finishReason": "stop",
    "platform": "qwen",
    "status": "success"
  }],
  
  "detailedResults": [/* 同上 */]
}
```

---

## 📊 测试结论

### 数据库检索功能

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 报告主数据读取 | ✅ | 正常 |
| 结果明细读取 | ✅ | 正常 |
| 分析数据读取 | ✅ | 正常 |
| 快照数据读取 | ✅ | 正常 |
| 字段转换 | ✅ | snake_case → camelCase |
| 聚合数据计算 | ✅ | brandDistribution, sentimentDistribution |

### 前端兼容性

| 字段 | 状态 | 建议 |
|------|------|------|
| brandDistribution | ✅ | 可用 |
| sentimentDistribution | ✅ | 可用 |
| keywords | ⚠️ | 需要生成逻辑 |
| results | ✅ | 可用 |
| detailedResults | ✅ | 可用 |
| brandScores | ❌ | 需要添加 |

---

**报告版本**: 1.0  
**最后更新**: 2026-03-13  
**维护者**: 首席全栈工程师
