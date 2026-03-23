/**
 * 图表数据服务
 * 负责为 ECharts 准备各种图表的数据
 */

/**
 * 准备雷达图数据
 * @param {Object} competitiveAnalysis - 竞争分析数据
 * @param {string} targetBrand - 目标品牌
 * @param {Array} competitorBrands - 竞品品牌列表
 * @returns {Array} 雷达图数据
 */
const prepareRadarChartData = (competitiveAnalysis, targetBrand, competitorBrands) => {
  if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
    return [];
  }

  const brandScores = competitiveAnalysis.brandScores;
  const targetScore = brandScores[targetBrand];

  if (!targetScore) {
    return [];
  }

  const radarData = [
    {
      name: '权威度',
      value: targetScore.overallAuthority || 0,
      max: 100
    },
    {
      name: '可见度',
      value: targetScore.overallVisibility || 0,
      max: 100
    },
    {
      name: '纯净度',
      value: targetScore.overallPurity || 0,
      max: 100
    },
    {
      name: '一致性',
      value: targetScore.overallConsistency || 0,
      max: 100
    },
    {
      name: '综合得分',
      value: targetScore.overallScore || 0,
      max: 100
    }
  ];

  // 添加竞品数据（如果有）
  if (competitorBrands && competitorBrands.length > 0) {
    competitorBrands.forEach(brand => {
      const competitorScore = brandScores[brand];
      if (competitorScore) {
        radarData.push({
          name: brand,
          value: competitorScore.overallScore || 0,
          max: 100
        });
      }
    });
  }

  return radarData;
};

/**
 * 准备关键词云数据
 * @param {Object} semanticDriftData - 语义偏移数据
 * @param {Array} results - 结果数组
 * @param {string} targetBrand - 目标品牌
 * @returns {Object} 词云数据 { keywordCloudData, topKeywords, keywordStats }
 */
const prepareKeywordCloudData = (semanticDriftData, results, targetBrand) => {
  let allKeywords = [];

  // 从语义偏移数据中提取关键词
  if (semanticDriftData) {
    if (semanticDriftData.positiveTerms) {
      semanticDriftData.positiveTerms.forEach(word => {
        allKeywords.push({ word: word, sentiment: 'positive' });
      });
    }

    if (semanticDriftData.negativeTerms) {
      semanticDriftData.negativeTerms.forEach(word => {
        allKeywords.push({ word: word, sentiment: 'negative' });
      });
    }

    if (semanticDriftData.unexpectedKeywords) {
      semanticDriftData.unexpectedKeywords.forEach(word => {
        allKeywords.push({ word: word, sentiment: 'neutral' });
      });
    }
  }

  // 从 AI 响应中提取更多关键词
  const targetResults = results.filter(r => r.brand === targetBrand);
  const allResponses = targetResults.map(r => r.response || '').join(' ');

  // 简单分词和统计
  const words = allResponses.split(/[\s,.。！？!？]+/);
  const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等', '一个', '这个', '这些'];

  const wordCount = {};
  words.forEach(word => {
    if (word.length > 1 && !stopWords.includes(word)) {
      wordCount[word] = (wordCount[word] || 0) + 1;
    }
  });

  // 合并词频数据
  const keywordMap = {};
  allKeywords.forEach(item => {
    keywordMap[item.word] = {
      word: item.word,
      count: wordCount[item.word] || 1,
      sentiment: item.sentiment
    };
  });

  // 转换为数组并排序
  const keywordData = Object.values(keywordMap)
    .sort((a, b) => b.count - a.count)
    .slice(0, 50);

  // 计算权重
  const maxCount = keywordData.length > 0 ? keywordData[0].count : 1;
  keywordData.forEach(item => {
    item.weight = item.count / maxCount;
  });

  // 统计情感分布
  const stats = {
    positiveCount: keywordData.filter(k => k.sentiment === 'positive').length,
    neutralCount: keywordData.filter(k => k.sentiment === 'neutral').length,
    negativeCount: keywordData.filter(k => k.sentiment === 'negative').length
  };

  // 高频词（Top 10）
  const topKeywords = keywordData.slice(0, 10);

  return {
    keywordCloudData: keywordData,
    topKeywords: topKeywords,
    keywordStats: stats
  };
};

/**
 * 准备趋势图表数据
 * @param {Object} reportData - 报告数据
 * @returns {Object} 趋势图数据 { dates, values, predictions }
 */
const prepareTrendChartData = (reportData) => {
  if (!reportData || typeof reportData !== 'object') {
    return { dates: [], values: [], predictions: [] };
  }

  try {
    if (reportData.timeSeries && Array.isArray(reportData.timeSeries)) {
      const timeSeries = reportData.timeSeries;
      const dates = timeSeries.map(item => item.period || item.date || '未知时间');
      const values = timeSeries.map(item => item.value || 0);

      const predictions = reportData.prediction && Array.isArray(reportData.prediction.forecast_points)
        ? reportData.prediction.forecast_points.map(point => point.value || 0)
        : [];

      return { dates, values, predictions };
    }

    // 返回默认数据
    return {
      dates: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      values: [30, 45, 60, 75, 80, 85, 90],
      predictions: [88, 92, 95, 97, 98, 99, 100]
    };
  } catch (error) {
    console.error('准备趋势图数据失败:', error);
    return { dates: [], values: [], predictions: [] };
  }
};

/**
 * 准备品牌对比数据
 * @param {Object} competitiveAnalysis - 竞争分析数据
 * @param {string} targetBrand - 目标品牌
 * @returns {Object} 对比数据
 */
const prepareBrandComparisonData = (competitiveAnalysis, targetBrand) => {
  if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
    return { brands: [], scores: [] };
  }

  const brandScores = competitiveAnalysis.brandScores;
  const brands = Object.keys(brandScores);
  const scores = brands.map(brand => brandScores[brand].overallScore || 0);

  // 按分数排序
  const sortedData = brands
    .map((brand, index) => ({ brand, score: scores[index] }))
    .sort((a, b) => b.score - a.score);

  return {
    brands: sortedData.map(d => d.brand),
    scores: sortedData.map(d => d.score)
  };
};

module.exports = {
  prepareRadarChartData,
  prepareKeywordCloudData,
  prepareTrendChartData,
  prepareBrandComparisonData
};
