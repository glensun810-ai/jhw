/**
 * history-detail.js displayReport 方法修复补丁
 * 
 * 问题根因:
 * 1. detailedResults 包含 _raw: r 引用完整原始数据，导致循环引用和大数据量
 * 2. 一次性 setData 太多数据，导致页面渲染阻塞
 * 
 * 修复方案:
 * 1. 移除 _raw 引用，完整数据已保存在全局变量中
 * 2. 采用分层加载，将 setData 分成 3 层逐步执行
 */

// ============================================================================
// 替换位置：history-detail.js 第 218-328 行 (displayReport 方法)
// ============================================================================

  /**
   * 展示报告数据（第 31 次修复 - 性能优化版）
   * @param {Object} report - 报告数据
   */
  displayReport: function(report) {
    console.log('[报告详情页] displayReport 执行', report ? '有数据' : '无数据');

    // 【P0 性能修复 - 2026-03-22】立即解除 loading，防止卡死
    this.setData({ loading: false });

    // 处理详细结果数据
    const results = report.results || report.detailedResults || [];
    
    // 【关键修复】保存完整数据到全局变量（用于加载更多），不放入 setData
    const app = getApp();
    if (!app.globalData) app.globalData = {};
    app.globalData.currentReportData = {
      executionId: report.executionId || report.report?.execution_id,
      totalResults: results.length,
      fullResults: results,
      metrics: report.metrics || {},
      dimensionScores: report.dimension_scores || {},
      diagnosticWall: report.diagnosticWall || {}
    };

    // 【性能优化】只计算前 5 条用于展示，不包含_raw 引用
    const initialResults = results.slice(0, 5).map((r, index) => {
      const score = r.score || r.qualityScore || r.quality_score || 85;
      let scoreClass = 'poor';
      if (score >= 80) scoreClass = 'excellent';
      else if (score >= 60) scoreClass = 'good';

      return {
        id: r.id || `result_${index}`,
        brand: r.brand || r.extractedBrand || r.extracted_brand || '未知品牌',
        model: r.model || r.platform || '未知模型',
        platform: r.platform || r.model || '',
        score: score,
        scoreClass: scoreClass,
        question: (r.question || '').substring(0, 50),
        response: (r.responseContent || r.response_content || r.response?.content || '').substring(0, 100),
        truncated: (r.responseContent?.length || r.response_content?.length || 0) > 100,
        fullResponse: r.responseContent || r.response_content || r.response?.content || '',
        expanded: false
        // 【关键修复】移除 _raw 引用，防止循环引用和大数据量
      };
    });

    // 计算综合评分
    const metrics = report.metrics || {};
    const dimensionScores = report.dimension_scores || {};
    const qualityScore = metrics.influence || report.validation?.qualityScore || report.qualityHints?.qualityScore ||
                        report.overall_score || 75;
    const overallScore = qualityScore > 1 ? qualityScore : qualityScore * 100;

    // 【分层加载 P1】第 1 层：核心信息（立即加载）
    this.setData({
      // 核心信息
      brandName: report.brandName || report.report?.brand_name || this.data.brandName || '未知品牌',
      overallScore: overallScore,
      overallGrade: this.calculateGrade(overallScore),
      overallSummary: this.getGradeSummary(this.calculateGrade(overallScore)),
      gradeClass: this.getGradeClass(this.calculateGrade(overallScore)),

      // 详细结果（前 5 条）
      detailedResults: initialResults,
      hasMoreResults: results.length > 5,
      totalResults: results.length,

      // 诊断信息
      hasRealData: true,
      hasRealResults: results.length > 0
    });

    console.log('[报告详情页] ✅ 第 1 层：核心信息已加载');

    // 【分层加载 P2】第 2 层：分析数据（100ms 延迟）
    setTimeout(() => {
      try {
        this.setData({
          // 分析数据
          brandDistribution: report.brandDistribution || {},
          sentimentDistribution: report.sentimentDistribution || {},
          keywords: report.keywords || [],

          // 核心指标
          sovShare: metrics.sov || 0,
          sentimentScore: metrics.sentiment || 0,
          physicalRank: metrics.rank || 1,
          influenceScore: metrics.influence || 0,
          hasMetrics: true,

          // 评分维度
          overallAuthority: dimensionScores.authority || 50,
          overallVisibility: dimensionScores.visibility || 50,
          overallPurity: dimensionScores.purity || 50,
          overallConsistency: dimensionScores.consistency || 50,
          hasRealDimensionScores: true
        });
        console.log('[报告详情页] ✅ 第 2 层：分析数据已加载');
      } catch (error) {
        console.error('[报告详情页] ❌ 第 2 层加载失败:', error);
      }
    }, 100);

    // 【分层加载 P3】第 3 层：问题诊断墙（200ms 延迟）
    setTimeout(() => {
      try {
        this.setData({
          // 问题诊断墙
          highRisks: report.diagnosticWall?.risk_levels?.high || [],
          mediumRisks: report.diagnosticWall?.risk_levels?.medium || [],
          suggestions: report.diagnosticWall?.priority_recommendations || [],
          hasRealRecommendations: true
        });
        console.log('[报告详情页] ✅ 第 3 层：问题诊断墙已加载');
      } catch (error) {
        console.error('[报告详情页] ❌ 第 3 层加载失败:', error);
      }
    }, 200);

    console.log('[报告详情页] ✅ 数据展示完成', {
      brandName: this.data.brandName,
      detailedResults: initialResults.length,
      totalResults: results.length,
      hasMoreResults: results.length > 5
    });
  },

// ============================================================================
// 使用说明
// ============================================================================
/**
 * 1. 打开 history-detail.js 文件
 * 2. 找到第 218-328 行的 displayReport 方法
 * 3. 用上述代码替换整个方法
 * 4. 保存文件并重新编译小程序
 * 
 * 关键修复点:
 * 1. 立即解除 loading (this.setData({ loading: false }))
 * 2. 移除 _raw 引用，防止循环引用
 * 3. 分层加载数据，避免一次性 setData 太多数据
 * 4. 完整数据保存在全局变量，需要时从全局变量获取
 */
