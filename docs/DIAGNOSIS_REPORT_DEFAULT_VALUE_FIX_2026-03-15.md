# 诊断报告页默认值展示优化报告

**日期**: 2026-03-15  
**版本**: v1.0  
**状态**: ✅ 已完成

---

## 📋 需求概述

用户希望详细诊断报告页在点击任何一个诊断记录时都能正常打开，对于报告里的数据若没有真实统计出来，则以默认值或 0 的形式展示。默认值的样式相对于真实值使用浅灰色或斜体等较弱的视觉效果，当有真实值时则展示真实值。

## 🎯 实现目标

1. ✅ **确保任何诊断记录都能正常打开** - 即使数据不完整也能正常展示
2. ✅ **默认值/兜底逻辑** - 无真实数据时显示 0 或默认值
3. ✅ **弱视觉效果** - 默认值使用浅灰色、斜体、降低透明度等样式
4. ✅ **真实数据优先** - 有真实值时正常显示，优先级高于默认值

---

## 🔧 实现步骤

### 步骤 1: 诊断记录点击跳转逻辑分析

**文件**: `pages/history/history.js` → `pages/history-detail/history-detail.js`

**现状**:
- 历史记录列表页通过 `onReportTap` 函数跳转到详情页
- 跳转时传递 `executionId` 和 `brandName` 参数
- 详情页从本地缓存或 API 加载数据

**确认**: 跳转逻辑正常，问题在于数据加载失败时的处理

---

### 步骤 2: 实现报告数据默认值/兜底逻辑

**文件**: `pages/history-detail/history-detail.js`

#### 2.1 核心信息加载层 (`_loadCoreInfo`)

```javascript
_loadCoreInfo: function(record, results) {
  // 【P21 增强】确保 results 是对象，避免 undefined 错误
  const resultsObj = results || {};
  const overallScore = resultsObj.overall_score || resultsObj.overallScore || 0;
  const overallGrade = this.calculateGrade(overallScore);

  this.setData({
    brandName: record.brandName || record.brand_name || this.data.brandName || '未知品牌',
    overallScore: overallScore,
    overallGrade: overallGrade,
    overallSummary: this.getGradeSummary(overallGrade),
    gradeClass: this.getGradeClass(overallGrade),
    // 【P21 增强】标记是否有真实数据
    hasRealData: !!(resultsObj && (resultsObj.overall_score || resultsObj.overallScore))
  });
}
```

**关键改进**:
- 添加 `hasRealData` 标志，用于区分真实数据和默认值
- 使用 `|| 0` 确保数值类型始终有效

#### 2.2 分析数据加载层 (`_loadAnalysisData`)

```javascript
_loadAnalysisData: function(record, results) {
  const resultsObj = results || {};
  
  // 优先使用后端预计算数据
  let dimensionScores = resultsObj.dimension_scores || resultsObj.dimensionScores || null;
  
  // 降级方案：前端计算
  if (!dimensionScores) {
    dimensionScores = this._calculateDimensionScoresFromResults(detailedResults.slice(0, 20));
  }

  // 【P21 增强】标记是否有真实数据
  const hasRealDimensionScores = !!(resultsObj.dimension_scores || resultsObj.dimensionScores);
  const hasRealMetrics = !!(resultsObj.exposure_analysis && brandData.sov_share);

  this.setData({
    overallAuthority: dimensionScores.authority || 0,
    overallVisibility: dimensionScores.visibility || 0,
    overallPurity: dimensionScores.purity || 0,
    overallConsistency: dimensionScores.consistency || 0,
    hasRealDimensionScores: hasRealDimensionScores,  // 标记真实数据
    
    sovShare: brandData.sov_share ? Math.round(brandData.sov_share * 100) : 0,
    sentimentScore: brandData.sentiment_score || 0,
    physicalRank: brandData.rank || 0,
    influenceScore: Math.round((/*...*/) / 4),
    hasRealMetrics: hasRealMetrics,  // 标记真实数据
    
    highRisks: riskLevels.high || [],
    mediumRisks: riskLevels.medium || [],
    suggestions: recommendationData.priority_recommendations || [],
    hasRealRecommendations: !!recommendationData,  // 标记真实数据
    
    sourceList: sourcePool.slice(0, 10),
    hasRealSources: sourcePool.length > 0  // 标记真实数据
  });
}
```

**关键改进**:
- 为每个数据类别添加 `hasReal*` 标志
- 区分后端预计算数据和前端降级计算数据
- 确保所有数值都有默认值（0 或空数组）

---

### 步骤 3: 为默认值添加弱视觉效果样式

**文件**: `pages/history-detail/history-detail.wxss`

#### 3.1 基础占位样式类

```css
/* ========== 默认值/占位数据弱视觉效果 ========== */
/* 【P21 新增 - 2026-03-15】无真实数据时显示默认值的弱视觉效果 */

/* 浅灰色文字 */
.placeholder-text {
  color: #5a5a5a !important;
  font-style: italic;
  font-weight: 400;
}

/* 浅灰色数字 */
.placeholder-value {
  color: #5a5a5a !important;
  font-style: italic;
  opacity: 0.6;
}
```

#### 3.2 组件特定占位样式

```css
/* 核心指标卡片中的占位值 */
.metrics-section .metric-item.placeholder .metric-value {
  color: #5a5a5a;
  font-style: italic;
  opacity: 0.6;
}

.metrics-section .metric-item.placeholder .metric-label {
  color: #6a6a6a;
}

/* 评分维度条的占位样式 */
.score-dimensions-section .dimension-item.placeholder .dimension-value {
  color: #5a5a5a;
  font-style: italic;
}

.score-dimensions-section .dimension-item.placeholder .bar-fill {
  background: linear-gradient(90deg, #3a3a3a 0%, #2a2a2a 100%);
  opacity: 0.4;
}

/* 综合评分仪表盘的占位样式 */
.score-gauge-section.placeholder .gauge-score {
  color: #5a5a5a;
  font-style: italic;
}

/* 数据不可用提示 */
.data-unavailable {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
  color: #5a5a5a;
  font-size: 26rpx;
  font-style: italic;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12rpx;
  border: 1rpx dashed #3a3a3a;
}

.data-unavailable::before {
  content: '📊';
  margin-right: 12rpx;
  opacity: 0.5;
}
```

**样式特点**:
- **浅灰色**: `#5a5a5a` (比正常文字 `#8c8c8c` 更浅)
- **斜体**: `font-style: italic`
- **降低透明度**: `opacity: 0.4-0.6`
- **虚线边框**: `border: 1rpx dashed #3a3a3a`

---

### 步骤 4: 确保真实数据正常显示

**文件**: `pages/history-detail/history-detail.wxml`

#### 4.1 综合评分仪表盘

```xml
<view class="score-gauge-section {{hasRealData ? '' : 'placeholder'}}">
  <text class="section-title">综合评分</text>
  <view class="gauge-wrapper">
    <text class="gauge-score {{hasRealData ? '' : 'placeholder-value'}}">{{overallScore}}</text>
    <text class="gauge-grade {{gradeClass}} {{hasRealData ? '' : 'placeholder-value'}}">{{overallGrade}}</text>
    <text class="gauge-summary {{hasRealData ? '' : 'placeholder-text'}}">{{overallSummary}}</text>
  </view>
</view>
```

#### 4.2 核心指标卡

```xml
<view class="metrics-section {{hasMetrics ? '' : 'placeholder'}}" wx:if="{{true}}">
  <view class="metrics-grid">
    <view class="metric-item {{hasRealMetrics ? '' : 'placeholder'}}">
      <text class="metric-label">声量份额</text>
      <text class="metric-value {{hasRealMetrics ? '' : 'placeholder-value'}}">
        {{hasRealMetrics ? sovShare + '%' : '0%'}}
      </text>
    </view>
    <!-- ... 其他指标 ... -->
  </view>
</view>
```

#### 4.3 评分维度

```xml
<view class="score-dimensions-section {{hasRealDimensionScores ? '' : 'placeholder'}}">
  <view class="dimension-item {{hasRealDimensionScores ? '' : 'placeholder'}}">
    <text class="dimension-label">权威度</text>
    <view class="dimension-bar">
      <view class="bar-fill authority" style="width: {{overallAuthority}}%;"></view>
    </view>
    <text class="dimension-value {{hasRealDimensionScores ? '' : 'placeholder-value'}}">
      {{overallAuthority}}分
    </text>
  </view>
  <!-- ... 其他维度 ... -->
</view>
```

#### 4.4 详细结果列表

```xml
<view class="detailed-results-section {{detailedResults.length > 0 ? '' : 'placeholder'}}">
  <!-- ... -->
  <view class="result-item {{detailedResults.length > 0 ? '' : 'placeholder'}}" 
        wx:for="{{detailedResults}}" wx:key="id">
    <view class="result-header">
      <view class="result-brand {{detailedResults.length > 0 ? '' : 'placeholder-text'}}">
        {{item.brand}}
      </view>
      <!-- ... -->
    </view>
  </view>
  
  <!-- 无数据提示 -->
  <view wx:if="{{detailedResults.length === 0 && totalResults === 0}}" 
        class="data-unavailable">
    <text>暂无详细测试数据</text>
  </view>
</view>
```

**关键实现**:
- 使用 `{{hasRealData ? '' : 'placeholder'}}` 条件类名
- 使用 `{{hasRealData ? '' : 'placeholder-value'}}` 条件值样式
- 使用 `{{hasRealMetrics ? realValue : '0'}}` 条件显示真实值或默认值

---

## 📊 视觉效果对比

| 状态 | 颜色 | 字体 | 透明度 | 边框 |
|------|------|------|--------|------|
| **真实数据** | `#FFFFFF` / `#e8e8e8` | 正常 | 100% | 实线 |
| **默认值** | `#5a5a5a` | 斜体 | 40-60% | 虚线 |

---

## 🧪 测试验证清单

### 功能测试
- [ ] 点击任意诊断记录能正常打开详情页
- [ ] 数据完整时显示真实值（正常样式）
- [ ] 数据缺失时显示默认值（弱视觉效果）
- [ ] 混合状态：部分真实数据 + 部分默认值正确显示

### 视觉测试
- [ ] 默认值使用浅灰色 (`#5a5a5a`)
- [ ] 默认值使用斜体 (`font-style: italic`)
- [ ] 默认值降低透明度 (`opacity: 0.4-0.6`)
- [ ] 真实数据保持正常样式

### 边界测试
- [ ] 完全无数据时显示"暂无详细测试数据"
- [ ] 数据为 0 时正确显示 0（带弱视觉效果）
- [ ] 数据加载中显示骨架屏
- [ ] 数据加载失败显示错误提示

---

## 📝 修改文件清单

| 文件路径 | 修改类型 | 说明 |
|----------|----------|------|
| `pages/history-detail/history-detail.js` | 修改 | 添加 `hasRealData` 等标志，实现默认值逻辑 |
| `pages/history-detail/history-detail.wxss` | 新增 | 添加 `.placeholder-*` 系列样式类 |
| `pages/history-detail/history-detail.wxml` | 修改 | 添加条件样式类，区分真实/默认值 |

---

## 🚀 部署建议

### 开发环境测试
```bash
# 1. 启动微信开发者工具
# 2. 编译项目
# 3. 访问诊断记录页面
# 4. 点击不同状态的诊断记录验证
```

### 测试场景
1. **场景 A**: 完整数据的诊断记录 → 显示真实值（正常样式）
2. **场景 B**: 无数据的诊断记录 → 显示默认值（弱视觉效果）
3. **场景 C**: 部分数据的诊断记录 → 混合显示

---

## 📈 后续优化建议

### 短期优化 (P1)
1. **report-v2 页面同步优化**: 为 `report-v2` 页面添加相同的默认值处理逻辑
2. **组件化占位符**: 将占位样式封装为可复用组件
3. **动画过渡**: 添加数据加载完成时的淡入动画

### 中期优化 (P2)
1. **智能数据预加载**: 在历史记录列表页预加载详情数据
2. **离线模式**: 支持完全离线查看已缓存的诊断报告
3. **数据重建**: 从原始结果数据自动重建汇总统计

### 长期优化 (P3)
1. **实时协作**: 支持多人同时查看和标注报告
2. **报告对比**: 支持多个历史报告的并排对比
3. **趋势分析**: 基于历史数据生成品牌发展趋势图

---

## 📞 技术支持

如有问题，请查阅以下文档：
- `DIAGNOSIS_DATA_AUTHENTICITY_REPORT.md` - 诊断数据真实性报告
- `FRONTEND_DIAGNOSIS_API_FIX.md` - 前端诊断 API 修复报告
- `HISTORY_REPORT_DETAIL_FIX_2026-03-13.md` - 历史报告详情页修复报告

---

**报告生成时间**: 2026-03-15  
**最后更新**: 2026-03-15  
**版本**: v1.0
