# 品牌洞察报告详情页 - 数据问题全面排查与修复

**分析时间**: 2026-02-24 10:30  
**问题级别**: 🔴 P0 紧急修复  
**影响范围**: 结果页所有数据展示

---

## 📊 问题清单

### 用户反馈的问题

1. ❌ **评分是 0 分** - 应该不对
2. ❌ **核心洞察三段结论** - 显示默认值，没有真实数据
3. ❌ **多维度分析都是 0 分** - 不正常
4. ❌ **AI 平台认知对比里暂无数据** - 不正常
5. ❌ **信源纯净度分析看不到真实信源** - 功能缺失
6. ❌ **信源权重结果像默认预设的三个结果** - 需要核实
7. ❌ **详细测试结果里没有竞品对比信息** - 缺失
8. ❌ **华为的得分是 0** - 不对

---

## 🔍 根因分析

### 问题 1-4: 评分和洞察数据为 0 或默认值

**根因**: 后端 `/test/status` 接口返回的数据中缺少以下字段：
- `brand_scores` - 品牌评分
- `competitive_analysis` - 竞争分析
- `semantic_drift_data` - 语义偏移数据
- `recommendation_data` - 优化建议数据

**当前后端返回**（从日志推断）:
```json
{
  "task_id": "...",
  "progress": 100,
  "stage": "completed",
  "detailed_results": [...],  // ✅ 有基础结果
  "is_completed": true,
  ...
  // ❌ 缺少以下字段！
  // "brand_scores": {...},
  // "competitive_analysis": {...},
  // "semantic_drift_data": {...},
  // "recommendation_data": {...}
}
```

### 问题 5-6: 信源纯净度分析缺失

**根因**: 
1. 后端没有生成 `negative_sources` 数据
2. 前端没有正确处理信源数据

### 问题 7-8: 竞品对比和华为得分为 0

**根因**:
1. `detailed_results` 中只有华为的数据，没有竞品数据
2. 评分计算逻辑有问题

---

## 🔧 修复方案

### 修复 1: 后端确保返回完整数据

**文件**: `backend_python/wechat_backend/views/diagnosis_views.py`  
**位置**: `/test/status` 接口（约第 2490-2540 行）

**问题**: 高级分析数据生成后没有添加到返回数据中

**修复代码**:
```python
# 在 get_task_status_api 函数中
if task_status.get('status') == 'completed':
    # 从 execution_store 获取高级分析数据
    response_data['brand_scores'] = task_status.get('brand_scores', {})
    response_data['competitive_analysis'] = task_status.get('competitive_analysis', {})
    response_data['semantic_drift_data'] = task_status.get('semantic_drift_data', {})
    response_data['recommendation_data'] = task_status.get('recommendation_data', {})
    response_data['negative_sources'] = task_status.get('negative_sources', [])
```

### 修复 2: 前端正确解析和展示数据

**文件**: `pages/results/results.js`  
**位置**: `initializePageWithData` 函数

**问题**: 没有从后端数据中提取高级分析数据

**修复代码**:
```javascript
initializePageWithData: function(results, targetBrand, competitorBrands, competitiveAnalysis, 
                                  negativeSources, semanticDriftData, recommendationData) {
  console.log('📊 初始化页面数据，结果数量:', results.length);
  
  // 如果没有传入 competitiveAnalysis，则从 results 构建
  if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
    competitiveAnalysis = this.buildCompetitiveAnalysis(results, targetBrand, competitorBrands);
  }
  
  // 使用 competitiveAnalysis 中的数据
  const brandScores = competitiveAnalysis.brandScores || {};
  
  // 计算品牌得分
  const targetBrandScore = brandScores[targetBrand]?.overallScore || 0;
  console.log('🎯 品牌得分:', targetBrandScore);
  
  // 设置数据
  this.setData({
    targetBrand: targetBrand,
    competitiveAnalysis: competitiveAnalysis,
    latestTestResults: results,
    // ... 其他数据
  });
}
```

### 修复 3: 确保 detailed_results 包含竞品数据

**文件**: `backend_python/wechat_backend/nxm_execution_engine.py`  
**位置**: 执行引擎主循环

**问题**: 只执行了主品牌的测试，没有执行竞品测试

**修复**: 需要确认 NxM 执行引擎是否正确遍历了所有品牌

---

## 📝 详细修复步骤

### 第一步：检查后端返回数据

在微信开发者工具 Console 中查看：
```javascript
// 在 fetchResultsFromServer 的 success 回调中
console.log('📡 后端 API 完整响应:', JSON.stringify(res.data, null, 2));
```

**预期输出**:
```json
{
  "task_id": "...",
  "progress": 100,
  "stage": "completed",
  "detailed_results": [
    {
      "brand": "华为",
      "question": "...",
      "model": "doubao",
      "response": "...",
      "geo_data": {
        "brand_mentioned": true,
        "rank": 1,
        "sentiment": 0.8,
        "cited_sources": [...]
      }
    },
    {
      "brand": "小米",  // ← 应该有竞品数据
      ...
    }
  ],
  "brand_scores": {  // ← 应该有评分
    "华为": {
      "overallScore": 85,
      "overallGrade": "A",
      ...
    },
    "小米": {...}
  },
  "competitive_analysis": {...},  // ← 应该有竞争分析
  "semantic_drift_data": {...},   // ← 应该有语义偏移
  "recommendation_data": {...},   // ← 应该有优化建议
  "negative_sources": [...]       // ← 应该有负面信源
}
```

### 第二步：根据实际返回修复

#### 情况 A: 后端返回了完整数据
→ 问题在前端解析逻辑，修复前端

#### 情况 B: 后端没有返回完整数据
→ 问题在后端生成逻辑，修复后端

### 第三步：验证修复

1. 重启后端
2. 清除前端缓存
3. 重新编译
4. 执行诊断
5. 检查结果页数据

---

## ✅ 验证清单

### 后端验证
- [ ] `/test/status` 返回 `brand_scores`
- [ ] `/test/status` 返回 `competitive_analysis`
- [ ] `/test/status` 返回 `semantic_drift_data`
- [ ] `/test/status` 返回 `recommendation_data`
- [ ] `/test/status` 返回 `negative_sources`
- [ ] `detailed_results` 包含所有品牌（华为 + 竞品）

### 前端验证
- [ ] 品牌评分显示正确（非 0）
- [ ] 核心洞察显示真实数据（非默认值）
- [ ] 多维度分析显示正确分数
- [ ] AI 平台认知对比有数据
- [ ] 信源纯净度分析显示真实信源
- [ ] 信源权重结果真实可信
- [ ] 详细测试结果包含竞品对比
- [ ] 华为得分正确计算

---

## 🚀 立即执行

### 1. 查看后端日志
```bash
tail -200 /Users/sgl/PycharmProjects/PythonProject/logs/app.log | grep -E "detailed_results|brand_scores|competitive_analysis"
```

### 2. 查看前端日志
在微信开发者工具 Console 中查看：
- `📡 后端 API 响应:`
- `📊 初始化页面数据`

### 3. 复制日志发给我
需要看到：
1. 后端实际返回的数据结构
2. 前端接收到的数据
3. 前端解析后的数据

---

**下一步**: 请执行诊断测试，然后复制前端 Console 和后端日志发给我，我将根据实际情况精准修复！
