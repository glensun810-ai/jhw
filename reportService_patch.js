/**
 * reportService.js 修复补丁
 * 
 * 修复内容：在 _processReportData 方法中添加 metrics、dimensionScores、diagnosticWall、brandAnalysis 的处理
 * 
 * 应用方法：
 * 1. 打开 brand_ai-seach/miniprogram/services/reportService.js
 * 2. 找到第 618 行的 _processReportData 方法
 * 3. 在关键词处理之后（约第 660 行），竞品分析处理之前，插入以下代码
 */

// ============================================================================
// 插入位置：关键词处理之后，竞品分析处理之前
// ============================================================================

    // 4. 【P0 关键修复 - 2026-03-22】处理核心指标数据
    const metrics = report.metrics;
    if (metrics && typeof metrics === 'object') {
      report.metrics = {
        sov: metrics.sov || 0,
        sentiment: metrics.sentiment || 0,
        rank: metrics.rank || 1,
        influence: metrics.influence || 0
      };
      console.log('[ReportService] ✅ 核心指标已处理:', report.metrics);
    } else {
      report.metrics = { sov: 0, sentiment: 0, rank: 1, influence: 0 };
      console.warn('[ReportService] ⚠️ 核心指标缺失，使用默认值');
    }

    // 5. 【P0 关键修复 - 2026-03-22】处理评分维度数据
    const dimensionScores = report.dimensionScores || report.dimension_scores;
    if (dimensionScores && typeof dimensionScores === 'object') {
      report.dimensionScores = {
        authority: dimensionScores.authority || 0,
        visibility: dimensionScores.visibility || 0,
        purity: dimensionScores.purity || 0,
        consistency: dimensionScores.consistency || 0
      };
      console.log('[ReportService] ✅ 评分维度已处理:', report.dimensionScores);
    } else {
      report.dimensionScores = { authority: 50, visibility: 50, purity: 50, consistency: 50 };
      console.warn('[ReportService] ⚠️ 评分维度缺失，使用默认值');
    }

    // 6. 【P0 关键修复 - 2026-03-22】处理问题诊断墙数据
    const diagnosticWall = report.diagnosticWall || report.diagnostic_wall;
    if (diagnosticWall && typeof diagnosticWall === 'object') {
      report.diagnosticWall = {
        risk_levels: diagnosticWall.risk_levels || { high: [], medium: [] },
        priority_recommendations: diagnosticWall.priority_recommendations || []
      };
      console.log('[ReportService] ✅ 问题诊断墙已处理:', {
        highRisks: report.diagnosticWall.risk_levels.high.length,
        mediumRisks: report.diagnosticWall.risk_levels.medium.length,
        recommendations: report.diagnosticWall.priority_recommendations.length
      });
    } else {
      report.diagnosticWall = { risk_levels: { high: [], medium: [] }, priority_recommendations: [] };
      console.warn('[ReportService] ⚠️ 问题诊断墙缺失，使用默认值');
    }

// ============================================================================
// 插入位置：优化建议数据处理之后，元数据处理之前
// ============================================================================

    // 12. 【P0 关键修复 - 2026-03-22】处理品牌分析数据
    const brandAnalysis = report.analysis?.brand_analysis;
    if (brandAnalysis && typeof brandAnalysis === 'object') {
      report.brandAnalysis = {
        userBrandAnalysis: brandAnalysis.user_brand_analysis || {},
        competitorAnalysis: brandAnalysis.competitor_analysis || [],
        comparison: brandAnalysis.comparison || {},
        top3Brands: brandAnalysis.top3_brands || []
      };
      console.log('[ReportService] ✅ 品牌分析已处理');
    } else {
      report.brandAnalysis = {};
      console.warn('[ReportService] ⚠️ 品牌分析缺失');
    }

// ============================================================================
// 插入位置：验证信息处理之后，return report 之前
// ============================================================================

    console.log('[ReportService] ✅ 报告数据处理完成');

// ============================================================================
// 使用说明
// ============================================================================
/**
 * 1. 打开 reportService.js 文件
 * 2. 找到第 618 行的 _processReportData 方法
 * 3. 按照上述插入位置，将代码插入到正确的位置
 * 4. 确保原有代码的序号需要调整（原 4-10 改为 7-13）
 * 5. 保存文件并重新编译小程序
 */
