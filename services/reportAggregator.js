/**
 * 报告聚合服务 - 重构简化版
 * 
 * 重构说明:
 * - 数据清洗 → services/dataSanitizer.js
 * - 评分计算 → services/scoringService.js
 * - 归因分析 → services/attributionService.js
 * 
 * 输入：NxM 执行结果数组
 * 输出：战略看板数据结构
 */

const { sanitizeResults, fillMissingData } = require('./dataSanitizer');
const { calculateSOV, calculateRiskScore, calculateBrandHealth, generateInsightText } = require('./scoringService');
const { attributeThreats, analyzeInterceptionPatterns, generateAttributionReport } = require('./attributionService');

/**
 * 聚合品牌诊断报告
 * @param {Array} rawResults - 原始结果数组
 * @param {string} brandName - 品牌名称
 * @param {Array} competitors - 竞品品牌列表
 * @param {Object} additionalData - 额外数据（语义偏移、推荐等）
 * @returns {Object} 聚合后的报告数据
 */
const aggregateReport = (rawResults, brandName, competitors, additionalData = {}) => {
  // 1. 数据清洗
  const results = sanitizeResults(rawResults);
  const filledResults = fillMissingData(results, brandName);

  // 2. 计算品牌分数
  const brandScores = calculateBrandScores(filledResults, brandName, competitors);

  // 3. 计算 SOV
  const sovData = calculateBrandSOV(filledResults, brandName, competitors);

  // 4. 计算风险评分
  const riskData = calculateBrandRisk(filledResults, brandName);

  // 5. 品牌健康度
  const healthData = calculateBrandHealth({
    authority: brandScores[brandName]?.overallAuthority || 50,
    visibility: brandScores[brandName]?.overallVisibility || 50,
    purity: brandScores[brandName]?.overallPurity || 50,
    consistency: brandScores[brandName]?.overallConsistency || 50
  });

  // 6. 生成洞察文本
  const insights = generateInsightText({
    authority: brandScores[brandName]?.overallAuthority || 50,
    visibility: brandScores[brandName]?.overallVisibility || 50,
    purity: brandScores[brandName]?.overallPurity || 50,
    consistency: brandScores[brandName]?.overallConsistency || 50
  }, brandName);

  // 7. 归因分析
  const threats = attributeThreats(additionalData.negative_sources || [], brandName);
  const patterns = analyzeInterceptionPatterns(additionalData.interception_data || {});
  const attribution = generateAttributionReport(threats, patterns);

  // 8. 整合报告
  return {
    brandName,
    competitors,
    brandScores,
    sov: sovData,
    risk: riskData,
    health: healthData,
    insights,
    attribution,
    semanticDriftData: additionalData.semantic_drift_data || null,
    recommendationData: additionalData.recommendation_data || null,
    overallScore: brandScores[brandName]?.overallScore || 50,
    timestamp: new Date().toISOString()
  };
};

/**
 * 计算品牌分数
 * @param {Array} results - 结果数组
 * @param {string} brandName - 品牌名称
 * @param {Array} competitors - 竞品列表
 * @returns {Object} 品牌分数
 */
const calculateBrandScores = (results, brandName, competitors) => {
  const allBrands = [brandName, ...competitors];
  const scores = {};

  allBrands.forEach(brand => {
    const brandResults = results.filter(r => r.brand === brand);

    if (brandResults.length === 0) {
      scores[brand] = {
        overallScore: 50,
        overallGrade: 'C',
        overallAuthority: 50,
        overallVisibility: 50,
        overallPurity: 50,
        overallConsistency: 50,
        overallSummary: '暂无数据'
      };
      return;
    }

    // 计算各项平均分
    const totalScore = brandResults.reduce((sum, r) => sum + (r.score || 50), 0);
    const avgScore = Math.round(totalScore / brandResults.length);

    // 计算等级
    let grade = 'D';
    if (avgScore >= 90) grade = 'A+';
    else if (avgScore >= 80) grade = 'A';
    else if (avgScore >= 70) grade = 'B';
    else if (avgScore >= 60) grade = 'C';

    scores[brand] = {
      overallScore: avgScore,
      overallGrade: grade,
      overallAuthority: Math.round(avgScore * 0.9), // 简化计算
      overallVisibility: Math.round(avgScore * 0.85),
      overallPurity: Math.round(avgScore * 0.9),
      overallConsistency: Math.round(avgScore * 0.8),
      overallSummary: getScoreSummary(avgScore)
    };
  });

  return scores;
};

/**
 * 计算品牌 SOV
 */
const calculateBrandSOV = (results, brandName, competitors) => {
  const brandMentions = results.filter(r => r.brand === brandName).length;
  const competitorMentions = results.filter(r => competitors.includes(r.brand)).length;

  return calculateSOV({ brandMentions, competitorMentions });
};

/**
 * 计算品牌风险
 */
const calculateBrandRisk = (results, brandName) => {
  const brandResults = results.filter(r => r.brand === brandName);
  const negativeCount = brandResults.filter(r => r.sentiment === 'negative').length;
  const totalCount = brandResults.length;

  return calculateRiskScore({
    positiveInterceptions: totalCount - negativeCount,
    negativeInterceptions: negativeCount,
    totalMentions: totalCount
  });
};

/**
 * 获取分数摘要
 */
const getScoreSummary = (score) => {
  if (score >= 90) return '表现卓越';
  if (score >= 80) return '表现良好';
  if (score >= 70) return '表现一般';
  if (score >= 60) return '有待提升';
  return '需要改进';
};

module.exports = {
  aggregateReport,
  calculateBrandScores,
  getScoreSummary
};
