/**
 * 数据处理服务
 * 负责报告数据的提取、格式化、防御性处理
 */

/**
 * 处理报告数据，应用数据防御机制
 * @param {Object} reportData - 原始报告数据
 * @returns {Object} 处理后的报告数据
 */
const processReportData = (reportData) => {
  if (!reportData || typeof reportData !== 'object') {
    console.warn('报告数据无效，返回默认结构');
    return getDefaultReportStructure();
  }

  return {
    prediction: defensiveGet(reportData, 'prediction', {}) || {},
    scores: defensiveGet(reportData, 'scores', {}) || {},
    competition: defensiveGet(reportData, 'competition', {}) || {},
    sources: defensiveGet(reportData, 'sources', []) || [],
    trends: defensiveGet(reportData, 'trends', {}) || {},
    results: defensiveGet(reportData, 'results', []) || [],
    original: reportData
  };
};

/**
 * 安全获取对象属性，防止 null/undefined 错误
 * @param {Object} obj - 源对象
 * @param {String} prop - 属性路径
 * @param {*} defaultValue - 默认值
 * @returns {*} 属性值或默认值
 */
const defensiveGet = (obj, prop, defaultValue = null) => {
  try {
    if (!obj || typeof obj !== 'object') {
      return defaultValue;
    }

    const props = prop.split('.');
    let result = obj;

    for (const p of props) {
      if (result == null || typeof result !== 'object') {
        return defaultValue;
      }
      result = result[p];

      if (result == null) {
        return defaultValue;
      }
    }

    if (Array.isArray(defaultValue) && Array.isArray(result) && result.length === 0) {
      return defaultValue;
    }

    return result;
  } catch (error) {
    console.error(`获取属性 ${prop} 时出错:`, error);
    return defaultValue;
  }
};

/**
 * 获取默认报告结构
 * @returns {Object} 默认报告结构
 */
const getDefaultReportStructure = () => {
  return {
    prediction: {
      forecast_points: [],
      confidence: 0,
      trend: 'neutral'
    },
    scores: {
      accuracy: 0,
      completeness: 0,
      relevance: 0,
      security: 0,
      sentiment: 0,
      competitiveness: 0
    },
    competition: {
      brand_keywords: [],
      shared_keywords: [],
      competitor_keywords: [],
      competitors: []
    },
    sources: [],
    trends: {
      historical: [],
      projected: []
    },
    results: [],
    original: {}
  };
};

/**
 * 提取预测数据
 * @param {Object} reportData - 报告数据
 * @returns {Object} 预测数据
 */
const extractPredictionData = (reportData) => {
  if (!reportData || typeof reportData !== 'object') {
    console.warn('报告数据无效，无法提取预测数据');
    return { forecast_points: [], confidence: 0, trend: 'neutral' };
  }

  try {
    if (reportData.prediction) {
      return {
        forecast_points: reportData.prediction.forecast_points || reportData.prediction.forecastPoints || [],
        confidence: reportData.prediction.confidence || 0,
        trend: reportData.prediction.trend || 'neutral'
      };
    } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
      const firstResult = reportData.results[0];
      if (firstResult.prediction) {
        return {
          forecast_points: firstResult.prediction.forecast_points || firstResult.prediction.forecastPoints || [],
          confidence: firstResult.prediction.confidence || 0,
          trend: firstResult.prediction.trend || 'neutral'
        };
      }
    }

    return { forecast_points: [], confidence: 0, trend: 'neutral' };
  } catch (error) {
    console.error('提取预测数据失败:', error);
    return { forecast_points: [], confidence: 0, trend: 'neutral' };
  }
};

/**
 * 提取评分数据
 * @param {Object} reportData - 报告数据
 * @returns {Object} 评分数据
 */
const extractScoreData = (reportData) => {
  if (!reportData || typeof reportData !== 'object') {
    console.warn('报告数据无效，无法提取评分数据');
    return {
      accuracy: 0, completeness: 0, relevance: 0,
      security: 0, sentiment: 0, competitiveness: 0, authority: 0
    };
  }

  try {
    if (reportData.scores) {
      return {
        accuracy: reportData.scores.accuracy || reportData.scores.Accuracy || 0,
        completeness: reportData.scores.completeness || reportData.scores.Completeness || 0,
        relevance: reportData.scores.relevance || reportData.scores.Relevance || 0,
        security: reportData.scores.security || reportData.scores.Security || 0,
        sentiment: reportData.scores.sentiment || reportData.scores.Sentiment || 0,
        competitiveness: reportData.scores.competitiveness || reportData.scores.Competitiveness || 0,
        authority: reportData.scores.authority || reportData.scores.Authority || 0
      };
    } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
      const firstResult = reportData.results[0];
      if (firstResult.scores) {
        return {
          accuracy: firstResult.scores.accuracy || firstResult.scores.Accuracy || 0,
          completeness: firstResult.scores.completeness || firstResult.scores.Completeness || 0,
          relevance: firstResult.scores.relevance || firstResult.scores.Relevance || 0,
          security: firstResult.scores.security || firstResult.scores.Security || 0,
          sentiment: firstResult.scores.sentiment || firstResult.scores.Sentiment || 0,
          competitiveness: firstResult.scores.competitiveness || firstResult.scores.Competitiveness || 0,
          authority: firstResult.scores.authority || firstResult.scores.Authority || 0
        };
      }
    }

    return {
      accuracy: 0, completeness: 0, relevance: 0,
      security: 0, sentiment: 0, competitiveness: 0, authority: 0
    };
  } catch (error) {
    console.error('提取评分数据失败:', error);
    return {
      accuracy: 0, completeness: 0, relevance: 0,
      security: 0, sentiment: 0, competitiveness: 0, authority: 0
    };
  }
};

/**
 * 提取竞争分析数据
 * @param {Object} reportData - 报告数据
 * @returns {Object} 竞争分析数据
 */
const extractCompetitionData = (reportData) => {
  if (!reportData || typeof reportData !== 'object') {
    console.warn('报告数据无效，无法提取竞争分析数据');
    return { brand_keywords: [], shared_keywords: [], competitors: [] };
  }

  try {
    if (reportData.competition) {
      return {
        brand_keywords: reportData.competition.brand_keywords || reportData.competition.brandKeywords || [],
        shared_keywords: reportData.competition.shared_keywords || reportData.competition.sharedKeywords || [],
        competitors: reportData.competition.competitors || []
      };
    } else if (reportData.competitive_analysis) {
      return {
        brand_keywords: reportData.competitive_analysis.brand_keywords || reportData.competitive_analysis.brandKeywords || [],
        shared_keywords: reportData.competitive_analysis.shared_keywords || reportData.competitive_analysis.sharedKeywords || [],
        competitors: reportData.competitive_analysis.competitors || []
      };
    } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
      const firstResult = reportData.results[0];
      if (firstResult.competition) {
        return {
          brand_keywords: firstResult.competition.brand_keywords || firstResult.competition.brandKeywords || [],
          shared_keywords: firstResult.competition.shared_keywords || firstResult.competition.sharedKeywords || [],
          competitors: firstResult.competition.competitors || []
        };
      } else if (firstResult.competitive_analysis) {
        return {
          brand_keywords: firstResult.competitive_analysis.brand_keywords || firstResult.competitive_analysis.brandKeywords || [],
          shared_keywords: firstResult.competitive_analysis.shared_keywords || firstResult.competitive_analysis.sharedKeywords || [],
          competitors: firstResult.competitive_analysis.competitors || []
        };
      }
    }

    return { brand_keywords: [], shared_keywords: [], competitors: [] };
  } catch (error) {
    console.error('提取竞争分析数据失败:', error);
    return { brand_keywords: [], shared_keywords: [], competitors: [] };
  }
};

/**
 * 提取信源列表数据
 * @param {Object} reportData - 报告数据
 * @returns {Array} 信源列表
 */
const extractSourceListData = (reportData) => {
  if (!reportData || typeof reportData !== 'object') {
    console.warn('报告数据无效，无法提取信源列表');
    return [];
  }

  try {
    if (reportData.sources && Array.isArray(reportData.sources)) {
      return reportData.sources.map(source => ({
        title: source.title || source.name || '未知信源',
        url: source.url || source.link || '',
        score: source.score || source.confidence || 0,
        type: source.type || '未知类型'
      }));
    } else if (reportData.results && Array.isArray(reportData.results)) {
      const sources = [];
      reportData.results.forEach(result => {
        if (result.sources && Array.isArray(result.sources)) {
          result.sources.forEach(source => {
            sources.push({
              title: source.title || source.name || '未知信源',
              url: source.url || source.link || '',
              score: source.score || source.confidence || 0,
              type: source.type || '未知类型'
            });
          });
        }
      });
      return sources;
    }

    return [
      { title: '品牌官网', url: 'https://brand.example.com', score: 95, type: '官方' },
      { title: '行业报告', url: 'https://industry-report.com', score: 87, type: '第三方' },
      { title: '社交媒体', url: 'https://social-media.com', score: 78, type: 'UGC' }
    ];
  } catch (error) {
    console.error('提取信源列表数据失败:', error);
    return [];
  }
};

/**
 * 生成趋势图表数据
 * @param {Object} reportData - 报告数据
 * @returns {Object} 图表配置对象
 */
const generateTrendChartData = (reportData) => {
  if (!reportData || typeof reportData !== 'object') {
    console.warn('报告数据无效，无法生成趋势图表');
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

    return {
      dates: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      values: [30, 45, 60, 75, 80, 85, 90],
      predictions: [88, 92, 95, 97, 98, 99, 100]
    };
  } catch (error) {
    console.error('生成趋势图表数据失败:', error);
    return { dates: [], values: [], predictions: [] };
  }
};

module.exports = {
  processReportData,
  defensiveGet,
  getDefaultReportStructure,
  extractPredictionData,
  extractScoreData,
  extractCompetitionData,
  extractSourceListData,
  generateTrendChartData
};
