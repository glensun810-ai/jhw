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

  // 8. 计算首次提及率【P1 修复】
  const firstMentionByPlatform = calculateFirstMentionByPlatform(filledResults);

  // 9. 计算拦截风险【P1 修复】
  const interceptionRisks = calculateInterceptionRisks(filledResults, brandName);

  // 10. 整合报告
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
    negativeSources: additionalData.negative_sources || null,
    competitiveAnalysis: additionalData.competitive_analysis || null,
    firstMentionByPlatform,  // 【P1 修复】添加首次提及率
    interceptionRisks,  // 【P1 修复】添加拦截风险
    overallScore: brandScores[brandName]?.overallScore || 50,
    timestamp: new Date().toISOString()
  };
};

/**
 * 计算品牌分数 - 增强版
 * @param {Array} results - 结果数组
 * @param {string} brandName - 品牌名称
 * @param {Array} competitors - 竞品列表
 * @returns {Object} 品牌分数（包含详细分析）
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
        overallSummary: '暂无数据',
        detailedScores: {
          authorityScores: [],
          visibilityScores: [],
          purityScores: [],
          consistencyScores: []
        },
        scoreDistribution: {
          excellent: 0,  // >= 90
          good: 0,       // >= 80
          fair: 0,       // >= 70
          poor: 0        // < 70
        },
        dataQuality: {
          totalResponses: 0,
          validResponses: 0,
          responseRate: 0
        }
      };
      return;
    }

    // 计算各项平均分
    const totalScore = brandResults.reduce((sum, r) => sum + (r.score || 50), 0);
    const avgScore = Math.round(totalScore / brandResults.length);

    // 计算详细分数
    const authorityScores = brandResults.map(r => r.authority_score || 50);
    const visibilityScores = brandResults.map(r => r.visibility_score || 50);
    const purityScores = brandResults.map(r => r.purity_score || 50);
    const consistencyScores = brandResults.map(r => r.consistency_score || 50);

    const avgAuthority = Math.round(authorityScores.reduce((a, b) => a + b, 0) / authorityScores.length);
    const avgVisibility = Math.round(visibilityScores.reduce((a, b) => a + b, 0) / visibilityScores.length);
    const avgPurity = Math.round(purityScores.reduce((a, b) => a + b, 0) / purityScores.length);
    const avgConsistency = Math.round(consistencyScores.reduce((a, b) => a + b, 0) / consistencyScores.length);

    // 计算等级
    let grade = 'D';
    if (avgScore >= 90) grade = 'A+';
    else if (avgScore >= 80) grade = 'A';
    else if (avgScore >= 70) grade = 'B';
    else if (avgScore >= 60) grade = 'C';

    // 计算分数分布
    const scoreDistribution = {
      excellent: brandResults.filter(r => (r.score || 0) >= 90).length,
      good: brandResults.filter(r => (r.score || 0) >= 80 && (r.score || 0) < 90).length,
      fair: brandResults.filter(r => (r.score || 0) >= 70 && (r.score || 0) < 80).length,
      poor: brandResults.filter(r => (r.score || 0) < 70).length
    };

    // 计算数据质量
    const validResponses = brandResults.filter(r => r.response && r.response.content).length;
    const dataQuality = {
      totalResponses: brandResults.length,
      validResponses: validResponses,
      responseRate: Math.round((validResponses / brandResults.length) * 100)
    };

    scores[brand] = {
      overallScore: avgScore,
      overallGrade: grade,
      overallAuthority: avgAuthority,
      overallVisibility: avgVisibility,
      overallPurity: avgPurity,
      overallConsistency: avgConsistency,
      overallSummary: getScoreSummary(avgScore),
      detailedScores: {
        authorityScores,
        visibilityScores,
        purityScores,
        consistencyScores
      },
      scoreDistribution,
      dataQuality,
      trends: {
        authorityTrend: calculateTrend(authorityScores),
        visibilityTrend: calculateTrend(visibilityScores),
        purityTrend: calculateTrend(purityScores),
        consistencyTrend: calculateTrend(consistencyScores)
      }
    };
  });

  return scores;
};

/**
 * 计算趋势（简单线性回归斜率）
 * @param {Array} scores - 分数数组
 * @returns {string} 趋势描述
 */
const calculateTrend = (scores) => {
  if (scores.length < 2) return 'stable';
  
  const n = scores.length;
  const sumX = n * (n - 1) / 2;
  const sumY = scores.reduce((a, b) => a + b, 0);
  const sumXY = scores.reduce((sum, score, i) => sum + i * score, 0);
  const sumX2 = n * (n - 1) * (2 * n - 1) / 6;
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  
  if (slope > 2) return 'improving';
  if (slope < -2) return 'declining';
  return 'stable';
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
 * 【P1 修复】计算首次提及率
 * @param {Array} results - 结果数组
 * @returns {Array} 各平台的首次提及率
 */
const calculateFirstMentionByPlatform = (results) => {
  const platformStats = {};

  results.forEach(result => {
    const platform = result.model || 'unknown';
    if (!platformStats[platform]) {
      platformStats[platform] = {
        platform,
        total: 0,
        firstMention: 0
      };
    }
    platformStats[platform].total++;
    if (result.geo_data?.brand_mentioned) {
      platformStats[platform].firstMention++;
    }
  });

  return Object.values(platformStats).map(stats => ({
    platform: stats.platform,
    rate: stats.total > 0 ? Math.round((stats.firstMention / stats.total) * 100) : 0,
    firstMention: stats.firstMention,
    total: stats.total
  }));
};

/**
 * 【P1 修复】计算拦截风险
 * @param {Array} results - 结果数组
 * @param {string} brandName - 主品牌名称
 * @returns {Array} 拦截风险列表
 */
const calculateInterceptionRisks = (results, brandName) => {
  const interceptionCounts = {};
  let totalIntercepted = 0;

  results.forEach(result => {
    const interception = result.geo_data?.interception || '';
    if (interception && interception.trim() !== '') {
      totalIntercepted++;
      // 分割竞品名称（可能包含多个）
      const competitors = interception.split(/[,,]/).map(c => c.trim()).filter(c => c);
      competitors.forEach(competitor => {
        if (!interceptionCounts[competitor]) {
          interceptionCounts[competitor] = 0;
        }
        interceptionCounts[competitor]++;
      });
    }
  });

  const totalResults = results.length;
  const interceptionRate = totalResults > 0 ? (totalIntercepted / totalResults) * 100 : 0;

  // 确定风险等级
  let riskLevel = 'low';
  if (interceptionRate > 50) riskLevel = 'high';
  else if (interceptionRate > 30) riskLevel = 'medium';

  // 构建拦截风险列表
  const risks = Object.entries(interceptionCounts).map(([competitor, count]) => ({
    type: 'brand_interception',
    competitor,
    count,
    rate: Math.round((count / totalResults) * 100),
    level: riskLevel,
    description: `${competitor} 在 ${count}/${totalResults} 次诊断中拦截了您的品牌`
  }));

  // 按拦截次数排序
  risks.sort((a, b) => b.count - a.count);

  return risks;
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
