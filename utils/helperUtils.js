/**
 * 辅助工具函数
 * 从 pages/index/index.js 提取的纯工具函数
 */

/**
 * 计算总分
 * @param {Object} scoreData - 评分数据
 * @returns {number} 平均分
 */
const calculateTotalScore = (scoreData) => {
  if (!scoreData) {
    return 0;
  }

  const scores = scoreData;
  const total = (scores.accuracy || 0) +
                (scores.completeness || 0) +
                (scores.relevance || 0) +
                (scores.security || 0) +
                (scores.sentiment || 0) +
                (scores.competitiveness || 0) +
                (scores.authority || 0);

  return Math.round(total / 7);
};

/**
 * 获取趋势指示器
 * @param {Object} scoreData - 评分数据
 * @returns {string} 趋势符号
 */
const getTrendIndicator = (scoreData) => {
  if (!scoreData) {
    return '→';
  }

  const currentScore = calculateTotalScore(scoreData);

  if (currentScore > 80) {
    return '↑';
  } else if (currentScore < 60) {
    return '↓';
  } else {
    return '→';
  }
};

/**
 * 获取完成时间文本
 * @returns {string} 格式化时间
 */
const getCompletedTimeText = () => {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  return `完成于 ${hours}:${minutes}`;
};

/**
 * 获取平台显示名称
 * @param {string} platform - 平台标识
 * @returns {string} 显示名称
 */
const getPlatformDisplayName = (platform) => {
  const platformNames = {
    'deepseek': 'DeepSeek',
    'qwen': '通义千问',
    'zhipu': '智谱 AI',
    'doubao': '豆包'
  };
  return platformNames[platform] || platform;
};

/**
 * 获取风险类型名称
 * @param {string} type - 风险类型
 * @returns {string} 风险名称
 */
const getRiskTypeName = (type) => {
  const riskTypes = {
    'visibility': '可见度拦截',
    'sentiment': '情感风险',
    'accuracy': '准确性风险',
    'purity': '纯净度风险'
  };
  return riskTypes[type] || type;
};

module.exports = {
  calculateTotalScore,
  getTrendIndicator,
  getCompletedTimeText,
  getPlatformDisplayName,
  getRiskTypeName
};
