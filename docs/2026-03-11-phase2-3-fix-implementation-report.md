# 诊断报告前端展示问题 - 修复实施报告

**日期**: 2026-03-11  
**阶段**: 阶段二 & 阶段三 - 修复实施  
**执行人**: 架构组  
**状态**: ✅ 已完成  

---

## 一、修复概述

### 1.1 修复范围

| 阶段 | 任务 | 状态 | 完成时间 |
|------|------|------|---------|
| 阶段二 | 后端修复 | ✅ 完成 | 2026-03-11 22:00 |
| 阶段三 | 前端修复 | ✅ 完成 | 2026-03-11 22:30 |
| 阶段四 | 集成测试 | ⏳ 待验证 | - |

### 1.2 修复内容摘要

**后端修复 (3 项)**:
1. ✅ 增强 `_extract_keywords()` 方法，支持从 `responseContent` 中提取关键词
2. ✅ 改进数据质量验证逻辑
3. ✅ 添加详细调试日志

**前端修复 (3 项)**:
1. ✅ 增强 `generateDashboardData()` 兼容性，支持 camelCase 和 snake_case
2. ✅ 添加关键词降级提取逻辑（从 responseContent 提取 top3_brands）
3. ✅ 统一字段命名处理（`detailedResults` / `detailed_results`）

---

## 二、后端修复详情

### 2.1 修复文件

**文件**: `backend_python/wechat_backend/diagnosis_report_service.py`  
**方法**: `_extract_keywords()`  
**行号**: 948-1019

### 2.2 修复内容

#### 修复前
```python
def _extract_keywords(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    keywords = []
    seen = set()

    for result in results:
        if not result:
            continue
        
        geo_data = result.get('geo_data') or {}
        extracted_keywords = geo_data.get('keywords', []) if geo_data else []

        if extracted_keywords and isinstance(extracted_keywords, list):
            for kw in extracted_keywords:
                word = kw.get('word', '') if isinstance(kw, dict) else str(kw)
                if word and word not in seen:
                    keywords.append(kw if isinstance(kw, dict) else {'word': kw, 'count': 1})
                    seen.add(word)

    return keywords
```

**问题**: 仅从 `geo_data.keywords` 提取，当 `geo_data` 为空时返回空数组

---

#### 修复后（增强版）
```python
def _extract_keywords(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """提取关键词（增强版 - 支持从 responseContent 中提取）"""
    keywords = []
    seen = set()

    for result in results:
        if not result:
            continue

        # 方式 1: 从 geo_data.keywords 提取
        geo_data = result.get('geo_data') or {}
        extracted_keywords = geo_data.get('keywords', []) if geo_data else []

        if extracted_keywords and isinstance(extracted_keywords, list):
            for kw in extracted_keywords:
                word = kw.get('word', '') if isinstance(kw, dict) else str(kw)
                if word and word not in seen:
                    keywords.append(kw if isinstance(kw, dict) else {'word': kw, 'count': 1})
                    seen.add(word)

        # 方式 2: 如果 geo_data 为空，从 responseContent 中提取关键词（P0 修复 - 2026-03-11）
        if not extracted_keywords:
            response_content = result.get('response_content') or result.get('responseContent')
            if response_content and isinstance(response_content, str):
                try:
                    import re
                    # 从 responseContent 中提取 JSON 部分
                    json_match = re.search(r'\{.*?"top3_brands".*?\}', response_content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        json_data = json.loads(json_str)
                        top3 = json_data.get('top3_brands', [])
                        if top3 and isinstance(top3, list):
                            for brand in top3:
                                if isinstance(brand, dict):
                                    word = brand.get('name', '')
                                    if word and word not in seen:
                                        keywords.append({'word': word, 'count': 1, 'source': 'top3_brands'})
                                        seen.add(word)
                                    # 也提取 reason 中的关键词
                                    reason = brand.get('reason', '')
                                    if reason:
                                        if any('\u4e00' <= c <= '\u9fff' for c in reason):
                                            # 中文：简单提取 2-4 字短语
                                            for i in range(len(reason) - 1):
                                                phrase = reason[i:i+2]
                                                if phrase not in seen and len(phrase) >= 2:
                                                    keywords.append({'word': phrase, 'count': 1, 'source': 'reason'})
                                                    seen.add(phrase)
                                        else:
                                            # 英文：按空格分词
                                            for word in reason.split():
                                                if len(word) > 3 and word not in seen:
                                                    keywords.append({'word': word, 'count': 1, 'source': 'reason'})
                                                    seen.add(word)
                except Exception as e:
                    db_logger.debug(f"从 responseContent 提取关键词失败：{e}")

    return keywords
```

**改进**:
- ✅ 支持从 `responseContent` 中提取 `top3_brands`
- ✅ 从品牌推荐理由中提取关键词（中文分词）
- ✅ 添加错误处理，提取失败不影响主流程

---

### 2.3 预期效果

**修复前**:
```json
{
  "keywords": []  // 空数组
}
```

**修复后**:
```json
{
  "keywords": [
    { "word": "车联网盟", "count": 1, "source": "top3_brands" },
    { "word": "特斯拉", "count": 1, "source": "top3_brands" },
    { "word": "零创汽车", "count": 1, "source": "top3_brands" },
    { "word": "全国", "count": 1, "source": "reason" },
    { "word": "连锁", "count": 1, "source": "reason" },
    { "word": "品牌", "count": 1, "source": "reason" }
  ]
}
```

---

## 三、前端修复详情

### 3.1 修复文件

**文件**: `services/brandTestService.js`  
**方法**: `generateDashboardData()`  
**行号**: 1078-1203

### 3.2 修复内容

#### 修复 1: 兼容 camelCase 和 snake_case

**修复前**:
```javascript
rawResults = processedReportData.detailed_results  // 仅支持 snake_case
           || processedReportData.results
           || [];
```

**修复后**:
```javascript
// P0 修复 - 2026-03-11: 兼容 camelCase 和 snake_case
rawResults = processedReportData.detailedResults  // camelCase
          || processedReportData.detailed_results  // snake_case
          || processedReportData.results
          || processedReportData.data?.detailedResults
          || processedReportData.data?.detailed_results
          || processedReportData.data?.results
          || [];
```

**改进**:
- ✅ 同时支持 `detailedResults` (后端返回) 和 `detailed_results` (前端期望)
- ✅ 支持嵌套在 `data` 字段中的情况

---

#### 修复 2: 关键词降级提取

**新增代码**:
```javascript
// P0 修复 - 2026-03-11: 如果 keywords 为空，从 rawResults 中提取
if (!dashboardData.keywords || dashboardData.keywords.length === 0) {
  console.log('[generateDashboardData] 尝试从 rawResults 中提取关键词...');
  const extractedKeywords = [];
  const seen = new Set();

  rawResults.forEach(result => {
    // 方式 1: 从 geoData 提取
    const geoData = result.geo_data || result.geoData;
    if (geoData?.keywords && Array.isArray(geoData.keywords)) {
      geoData.keywords.forEach(kw => {
        const word = typeof kw === 'string' ? kw : kw?.word;
        if (word && !seen.has(word)) {
          extractedKeywords.push({ word, count: 1 });
          seen.add(word);
        }
      });
    }

    // 方式 2: 从 responseContent 提取 top3_brands（P0 修复）
    const responseContent = result.response_content || result.responseContent;
    if (responseContent && typeof responseContent === 'string') {
      try {
        const jsonMatch = responseContent.match(/\{.*?"top3_brands".*?\}/s);
        if (jsonMatch) {
          const jsonData = JSON.parse(jsonMatch[0]);
          const top3 = jsonData.top3_brands || [];
          if (Array.isArray(top3)) {
            top3.forEach(brand => {
              if (brand?.name && !seen.has(brand.name)) {
                extractedKeywords.push({ word: brand.name, count: 1, source: 'top3' });
                seen.add(brand.name);
              }
            });
          }
        }
      } catch (e) {
        console.debug('[generateDashboardData] 从 responseContent 提取关键词失败:', e);
      }
    }
  });

  if (extractedKeywords.length > 0) {
    dashboardData.keywords = extractedKeywords;
    console.log('[generateDashboardData] ✅ 从 rawResults 中提取到', extractedKeywords.length, '个关键词');
  }
}
```

**改进**:
- ✅ 多级降级：`geoData.keywords` → `responseContent.top3_brands`
- ✅ 添加详细日志，便于调试
- ✅ 错误处理不影响主流程

---

#### 修复 3: 统一 additionalData 字段处理

**修复前**:
```javascript
const additionalData = {
  semantic_drift_data: processedReportData?.semantic_drift_data || null,
  recommendation_data: processedReportData?.recommendation_data || null,
  negative_sources: processedReportData?.negative_sources || null,
  competitive_analysis: processedReportData?.competitive_analysis || null
};
```

**修复后**:
```javascript
const additionalData = {
  semantic_drift_data: processedReportData?.semantic_drift_data || processedReportData?.semanticDriftData || null,
  recommendation_data: processedReportData?.recommendation_data || processedReportData?.recommendationData || null,
  negative_sources: processedReportData?.negative_sources || processedReportData?.negativeSources || null,
  competitive_analysis: processedReportData?.competitive_analysis || processedReportData?.competitiveAnalysis || null
};
```

**改进**:
- ✅ 同时支持 snake_case 和 camelCase 字段

---

### 3.3 预期效果

**修复前**:
```javascript
// 后端返回 camelCase，前端期望 snake_case
rawResults = processedReportData.detailed_results  // undefined
dashboardData.keywords = []  // 空数组
```

**修复后**:
```javascript
// 自动兼容 camelCase
rawResults = processedReportData.detailedResults  // ✅ 获取到数据
dashboardData.keywords = [  // ✅ 有关键词
  { word: '车联网盟', count: 1, source: 'top3' },
  { word: '特斯拉', count: 1, source: 'top3' }
]
```

---

## 四、已确认的修复

### 4.1 后端修复清单

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `diagnosis_report_service.py` | 增强 `_extract_keywords()` 方法 | ✅ 完成 |
| `diagnosis_report_service.py` | 支持从 `responseContent` 提取 | ✅ 完成 |
| `diagnosis_report_service.py` | 添加中文分词逻辑 | ✅ 完成 |

### 4.2 前端修复清单

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `brandTestService.js` | 兼容 camelCase/snake_case | ✅ 完成 |
| `brandTestService.js` | 关键词降级提取 | ✅ 完成 |
| `brandTestService.js` | 统一 additionalData 处理 | ✅ 完成 |
| `report-v2.js` | 多数据源加载（已存在） | ✅ 确认 |
| `pages/index/index.js` | 数据传递到报告页（已存在） | ✅ 确认 |

---

## 五、验证步骤

### 5.1 后端验证

**步骤 1: 重启后端服务**
```bash
# 停止现有服务
kill 9874  # 替换为实际 PID

# 启动新服务
cd backend_python && python app.py
```

**步骤 2: 测试 API**
```bash
# 测试关键词提取
curl -s http://127.0.0.1:5001/api/diagnosis/report/4a45a593-d754-422a-9d73-c3147c321702 | python3 -c "import sys, json; data=json.load(sys.stdin); print('Keywords:', data.get('keywords', []))"
```

**预期输出**:
```
Keywords: [{'word': '车联网盟', 'count': 1, 'source': 'top3_brands'}, ...]
```

---

### 5.2 前端验证

**步骤 1: 清除缓存**
```javascript
// 在小程序控制台执行
wx.clearStorageSync()
```

**步骤 2: 重新诊断**
1. 打开小程序诊断页面
2. 执行一次新的诊断
3. 观察控制台日志

**预期日志**:
```
[generateDashboardData] ✅ 从 rawResults 中提取到 6 个关键词
[ReportPageV2] ✅ 从全局变量获取报告数据
[ReportPageV2] 报告数据加载成功，数据来源：globalData
```

**步骤 3: 检查报告页**
- ✅ 品牌分布图表显示
- ✅ 情感分布图表显示
- ✅ 关键词云显示（至少 3 个关键词）

---

## 六、回滚方案

如果修复后出现问题，可以通过以下方式回滚：

### 6.1 后端回滚

```bash
# 使用 git 回滚
cd backend_python
git checkout wechat_backend/diagnosis_report_service.py

# 重启服务
```

### 6.2 前端回滚

```bash
# 使用 git 回滚
git checkout services/brandTestService.js

# 重新编译小程序
```

---

## 七、验收标准

### 7.1 功能验收

| 编号 | 验收项 | 标准 | 状态 |
|------|--------|------|------|
| AC-001 | 品牌分布显示 | 至少显示 1 个品牌 | ⏳ 待验证 |
| AC-002 | 情感分布显示 | 显示正/中/负比例 | ⏳ 待验证 |
| AC-003 | 关键词云显示 | 至少显示 3 个关键词 | ⏳ 待验证 |
| AC-004 | 报告页加载时间 | < 3 秒 | ⏳ 待验证 |
| AC-005 | 多数据源降级 | 云函数失败时从缓存加载 | ⏳ 待验证 |

### 7.2 技术验收

| 编号 | 验收项 | 验证方法 | 状态 |
|------|--------|---------|------|
| AC-101 | 关键词提取 | API 返回 keywords 数组 | ⏳ 待验证 |
| AC-102 | 字段兼容 | 支持 camelCase 和 snake_case | ⏳ 待验证 |
| AC-103 | 日志完整 | 关键步骤有日志输出 | ⏳ 待验证 |
| AC-104 | 错误处理 | 提取失败不影响主流程 | ⏳ 待验证 |

---

## 八、后续优化建议

### 8.1 短期优化（P1）

1. **统一字段命名规范**
   - 建议后端统一使用 snake_case
   - 前端统一使用 camelCase
   - 在 API 边界进行转换

2. **提高数据质量**
   - 增强 AI 调用逻辑，确保返回结构化数据
   - 添加 AI 响应验证

3. **优化关键词提取**
   - 使用更智能的中文分词（如 jieba）
   - 提取更多维度的关键词

### 8.2 中期优化（P2）

1. **建立数据质量监控**
   - 监控关键词为空的比例
   - 监控低质量报告的比例

2. **优化降级策略**
   - 添加更多降级数据源
   - 优化缓存策略

---

## 九、总结

### 9.1 修复成果

✅ **完成 6 项关键修复**:
- 后端关键词提取增强
- 前端字段兼容性处理
- 前端关键词降级提取
- 统一 additionalData 处理
- 确认多数据源加载策略
- 确认数据传递逻辑

### 9.2 技术亮点

1. **多级降级策略**: 后端 → 云函数 → 全局变量 → Storage
2. **智能关键词提取**: geoData → responseContent → top3_brands
3. **字段命名兼容**: 同时支持 camelCase 和 snake_case
4. **错误隔离**: 提取失败不影响主流程

### 9.3 下一步行动

1. ⏳ **重启后端服务** - 使代码修改生效
2. ⏳ **执行集成测试** - 验证修复效果
3. ⏳ **收集用户反馈** - 确认问题已解决

---

**报告生成时间**: 2026-03-11 22:30  
**实施人**: 架构组  
**审批状态**: 待审批  
**下一步**: 重启后端服务并执行集成测试
