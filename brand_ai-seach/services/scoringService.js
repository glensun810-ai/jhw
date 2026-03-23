/**
 * 战略评分服务
 * 负责 SOV、风险评分、品牌健康度计算
 */

// SOV 标签阈值
const SOV_THRESHOLDS = {
  leading: 60,
  neutral: 40,
  lagging: 0
};

// 风险等级阈值
const RISK_THRESHOLDS = {
  high: 0.3,
  mid: 0.6
};

// 情感颜色映射
const SENTIMENT_COLOR_MAP = {
  positive: '#22c55e',
  neutral: '#6b7280',
  negative: '#ef4444'
};

/**
 * 计算 SOV (Share of Voice)
 * @param {Object} mentions - 提及数据
 * @returns {Object} SOV 结果
 */
const calculateSOV = (mentions) => {
  const { brandMentions, competitorMentions } = mentions;

  const totalMentions = brandMentions + competitorMentions;
  if (totalMentions === 0) {
    return {
      sov: 0,
      sovLabel: '无数据',
      sovColor: '#999999'
    };
  }

  const sov = (brandMentions / totalMentions) * 100;

  let sovLabel = '落后';
  if (sov >= SOV_THRESHOLDS.leading) sovLabel = '领先';
  else if (sov >= SOV_THRESHOLDS.neutral) sovLabel = '持平';

  return {
    sov: Math.round(sov),
    sovLabel,
    sovColor: sov >= 50 ? '#22c55e' : '#ef4444'
  };
};

/**
 * 计算风险评分
 * @param {Object} interceptionData - 拦截数据
 * @returns {Object} 风险评分结果
 */
const calculateRiskScore = (interceptionData) => {
  const { positiveInterceptions, negativeInterceptions, totalMentions } = interceptionData;

  if (totalMentions === 0) {
    return {
      riskScore: 0,
      riskLevel: 'safe',
      riskLabel: '无数据'
    };
  }

  const negativeRate = negativeInterceptions / totalMentions;

  let riskLevel = 'safe';
  if (negativeRate >= RISK_THRESHOLDS.high) riskLevel = 'high';
  else if (negativeRate >= RISK_THRESHOLDS.mid) riskLevel = 'mid';

  return {
    riskScore: Math.round(negativeRate * 100),
    riskLevel,
    riskLabel: riskLevel === 'high' ? '高风险' : riskLevel === 'mid' ? '中风险' : '低风险'
  };
};

/**
 * 计算品牌健康度
 * @param {Object} scores - 各项评分
 * @returns {Object} 健康度结果
 */
const calculateBrandHealth = (scores) => {
  const { authority, visibility, purity, consistency } = scores;

  const avgScore = (authority + visibility + purity + consistency) / 4;

  let healthLabel = 'poor';
  if (avgScore >= 90) healthLabel = 'excellent';
  else if (avgScore >= 80) healthLabel = 'good';
  else if (avgScore >= 70) healthLabel = 'fair';

  return {
    healthScore: Math.round(avgScore),
    healthLabel,
    healthColor: avgScore >= 80 ? '#22c55e' : avgScore >= 60 ? '#f59e0b' : '#ef4444'
  };
};

/**
 * 生成洞察文本
 * @param {Object} scores - 评分数据
 * @param {string} targetBrand - 目标品牌
 * @returns {Object} 洞察文本
 */
const generateInsightText = (scores, targetBrand) => {
  const { authority, visibility, purity, consistency } = scores;

  const advantages = [];
  const risks = [];
  const opportunities = [];

  // 优势
  if (authority >= 80) advantages.push('权威度表现突出');
  if (visibility >= 80) advantages.push('可见度良好');
  if (purity >= 80) advantages.push('品牌纯净度高');

  // 风险
  if (authority < 60) risks.push('权威度有待提升');
  if (visibility < 60) risks.push('可见度不足');
  if (purity < 60) risks.push('品牌纯净度需改善');

  // 机会
  if (consistency < 70) opportunities.push('一致性方面有较大提升空间');
  if (consistency >= 70 && consistency < 80) opportunities.push('可进一步优化一致性');

  return {
    advantageInsight: advantages.length > 0 ? advantages.join('，') : '表现均衡',
    riskInsight: risks.length > 0 ? risks.join('，') : '风险可控',
    opportunityInsight: opportunities.length > 0 ? opportunities.join('，') : '保持当前优势'
  };
};

/**
 * 获取分数摘要
 * @param {number} score - 分数
 * @returns {string} 摘要文本
 */
const getScoreSummary = (score) => {
  if (score >= 90) return '表现卓越';
  if (score >= 80) return '表现良好';
  if (score >= 70) return '表现一般';
  if (score >= 60) return '有待提升';
  return '需要改进';
};

module.exports = {
  calculateSOV,
  calculateRiskScore,
  calculateBrandHealth,
  generateInsightText,
  getScoreSummary,
  SOV_THRESHOLDS,
  RISK_THRESHOLDS,
  SENTIMENT_COLOR_MAP
};
