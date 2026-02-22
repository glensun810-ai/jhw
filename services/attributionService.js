/**
 * 归因分析服务
 * 负责信源威胁归因、拦截模式分析
 */

/**
 * 分析信源威胁
 * @param {Array} sources - 信源列表
 * @param {string} targetBrand - 目标品牌
 * @returns {Object} 威胁分析结果
 */
const attributeThreats = (sources, targetBrand) => {
  if (!Array.isArray(sources) || sources.length === 0) {
    return {
      threats: [],
      threatCount: 0,
      threatLevel: 'low'
    };
  }

  const threats = sources
    .filter(source => {
      // 识别负面信源
      return source.sentiment === 'negative' || 
             source.interception === true ||
             (source.rank && source.rank > 5);
    })
    .map(source => ({
      sourceName: source.name || source.title || '未知信源',
      sourceUrl: source.url || '',
      threatType: source.sentiment === 'negative' ? '负面情感' : 
                  source.interception ? '品牌拦截' : '排名落后',
      severity: source.sentiment === 'negative' ? 'high' : 'medium',
      rank: source.rank || -1,
      sentiment: source.sentiment || 'neutral'
    }));

  const threatCount = threats.length;
  let threatLevel = 'low';
  if (threatCount >= 5) threatLevel = 'high';
  else if (threatCount >= 3) threatLevel = 'medium';

  return {
    threats,
    threatCount,
    threatLevel
  };
};

/**
 * 分析拦截模式
 * @param {Object} interceptionData - 拦截数据
 * @returns {Object} 拦截模式分析结果
 */
const analyzeInterceptionPatterns = (interceptionData) => {
  const { positiveInterceptions, negativeInterceptions, byPlatform } = interceptionData;

  const patterns = [];

  // 分析平台维度的拦截模式
  if (byPlatform) {
    Object.keys(byPlatform).forEach(platform => {
      const platformData = byPlatform[platform];
      const interceptionRate = platformData.interceptions / platformData.totalMentions;

      if (interceptionRate > 0.3) {
        patterns.push({
          platform,
          pattern: '高拦截率',
          interceptionRate: Math.round(interceptionRate * 100),
          recommendation: `建议加强在${platform}平台的 SEO 优化`
        });
      }
    });
  }

  // 总体分析
  const totalMentions = positiveInterceptions + negativeInterceptions;
  const overallInterceptionRate = totalMentions > 0 
    ? negativeInterceptions / totalMentions 
    : 0;

  return {
    patterns,
    overallInterceptionRate: Math.round(overallInterceptionRate * 100),
    recommendation: overallInterceptionRate > 0.3 
      ? '整体拦截率较高，建议全面优化品牌内容策略'
      : '拦截率在可控范围内，保持当前策略'
  };
};

/**
 * 生成归因报告
 * @param {Object} threats - 威胁数据
 * @param {Object} patterns - 模式数据
 * @returns {Object} 归因报告
 */
const generateAttributionReport = (threats, patterns) => {
  return {
    summary: {
      totalThreats: threats.threatCount,
      threatLevel: threats.threatLevel,
      interceptionRate: patterns.overallInterceptionRate
    },
    threats: threats.threats.slice(0, 10), // Top 10 威胁
    patterns: patterns.patterns,
    recommendations: [
      ...threats.threats.slice(0, 3).map(t => `处理${t.sourceName}的${t.threatType}问题`),
      ...patterns.patterns.map(p => p.recommendation)
    ].slice(0, 5)
  };
};

module.exports = {
  attributeThreats,
  analyzeInterceptionPatterns,
  generateAttributionReport
};
