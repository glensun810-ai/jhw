/**
 * 数据清洗器 - 将后端复杂的嵌套 JSON 扁平化为前端易用的结构
 * 遵循前端开发宪法 v2.0 - 数据防御法则
 */

/**
 * 解析报告数据，将其扁平化为前端易用的结构
 * @param {Object} rawData - 后端返回的原始数据
 * @returns {Object} 扁平化的报告数据结构
 */
const parseReportData = function(rawData) {
  // 数据防御：检查输入参数
  if (!rawData || typeof rawData !== 'object') {
    console.warn('原始数据无效，返回默认结构');
    return getDefaultReportStructure();
  }

  try {
    // 解析预测数据
    const predictionData = parsePredictionData(rawData);
    
    // 解析评分数据
    const scoreData = parseScoreData(rawData);
    
    // 解析竞争分析数据
    const competitionData = parseCompetitionData(rawData);
    
    // 解析信源数据
    const sourceData = parseSourceData(rawData);
    
    // 解析趋势数据
    const trendData = parseTrendData(rawData);

    // 返回扁平化的结构
    return {
      prediction: predictionData,
      scores: scoreData,
      competition: competitionData,
      sources: sourceData,
      trends: trendData,
      // 原始数据备份
      original: rawData
    };
  } catch (error) {
    console.error('解析报告数据失败:', error);
    // 数据防御：返回默认结构
    return getDefaultReportStructure();
  }
};

/**
 * 解析预测数据
 */
const parsePredictionData = function(rawData) {
  try {
    // 数据防御：检查数据结构
    if (!rawData || typeof rawData !== 'object') {
      return { forecast_points: [], confidence: 0, trend: 'neutral' };
    }

    // 支持多种字段命名约定
    const prediction = rawData.prediction || rawData.Prediction || rawData.prediction_data || rawData.predictionData || {};

    return {
      forecast_points: (prediction.forecast_points || prediction.forecastPoints) || [],
      confidence: typeof prediction.confidence === 'number' ? prediction.confidence : 0,
      trend: typeof prediction.trend === 'string' ? prediction.trend : 'neutral'
    };
  } catch (error) {
    console.error('解析预测数据失败:', error);
    return { forecast_points: [], confidence: 0, trend: 'neutral' };
  }
};

/**
 * 解析评分数据
 */
const parseScoreData = function(rawData) {
  try {
    // 数据防御：检查数据结构
    if (!rawData || typeof rawData !== 'object') {
      return {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        security: 0,
        sentiment: 0,
        competitiveness: 0
      };
    }

    // 查找评分数据，支持多种结构
    let scores = {};

    // 优先查找顶层的 scores
    if (rawData.scores) {
      scores = rawData.scores;
    } else if (rawData.Scores) {
      scores = rawData.Scores;
    } else if (rawData.results && Array.isArray(rawData.results) && rawData.results.length > 0) {
      // 从第一个结果中查找
      const firstResult = rawData.results[0];
      if (firstResult.scores) {
        scores = firstResult.scores;
      } else if (firstResult.Scores) {
        scores = firstResult.Scores;
      }
    }

    return {
      accuracy: (scores.accuracy || scores.Accuracy || scores.accuracy_score) || 0,
      completeness: (scores.completeness || scores.Completeness || scores.completeness_score) || 0,
      relevance: (scores.relevance || scores.Relevance || scores.relevance_score) || 0,
      security: (scores.security || scores.Security || scores.security_score) || 0,
      sentiment: (scores.sentiment || scores.Sentiment || scores.sentiment_score) || 0,
      competitiveness: (scores.competitiveness || scores.Competitiveness || scores.competitiveness_score) || 0
    };
  } catch (error) {
    console.error('解析评分数据失败:', error);
    return {
      accuracy: 0,
      completeness: 0,
      relevance: 0,
      security: 0,
      sentiment: 0,
      competitiveness: 0
    };
  }
};

/**
 * 解析竞争分析数据
 */
const parseCompetitionData = function(rawData) {
  try {
    // 数据防御：检查数据结构
    if (!rawData || typeof rawData !== 'object') {
      return {
        brand_keywords: [],
        shared_keywords: [],
        competitor_keywords: [],
        competitors: []
      };
    }

    // 查找竞争分析数据
    let competition = {};

    if (rawData.competition) {
      competition = rawData.competition;
    } else if (rawData.Competition) {
      competition = rawData.Competition;
    } else if (rawData.competitive_analysis) {
      competition = rawData.competitive_analysis;
    } else if (rawData.competitiveAnalysis) {
      competition = rawData.competitiveAnalysis;
    } else if (rawData.results && Array.isArray(rawData.results) && rawData.results.length > 0) {
      // 从第一个结果中查找
      const firstResult = rawData.results[0];
      if (firstResult.competition) {
        competition = firstResult.competition;
      } else if (firstResult.competitive_analysis) {
        competition = firstResult.competitive_analysis;
      }
    }

    return {
      brand_keywords: (competition.brand_keywords || competition.brandKeywords) || [],
      shared_keywords: (competition.shared_keywords || competition.sharedKeywords) || [],
      competitor_keywords: (competition.competitor_keywords || competition.competitorKeywords) || [],
      competitors: competition.competitors || []
    };
  } catch (error) {
    console.error('解析竞争分析数据失败:', error);
    return {
      brand_keywords: [],
      shared_keywords: [],
      competitor_keywords: [],
      competitors: []
    };
  }
};

/**
 * 解析信源数据
 */
const parseSourceData = function(rawData) {
  try {
    // 数据防御：检查数据结构
    if (!rawData || typeof rawData !== 'object') {
      return [];
    }

    // 查找信源数据
    if (Array.isArray(rawData.sources)) {
      return rawData.sources;
    } else if (rawData.sources && Array.isArray(rawData.sources.items)) {
      return rawData.sources.items;
    } else if (rawData.results && Array.isArray(rawData.results)) {
      // 从结果中合并所有信源
      const allSources = [];
      rawData.results.forEach(result => {
        if (result.sources && Array.isArray(result.sources)) {
          allSources.push(...result.sources);
        }
      });
      return allSources;
    }

    return [];
  } catch (error) {
    console.error('解析信源数据失败:', error);
    return [];
  }
};

/**
 * 解析趋势数据
 */
const parseTrendData = function(rawData) {
  try {
    // 数据防御：检查数据结构
    if (!rawData || typeof rawData !== 'object') {
      return { historical: [], projected: [] };
    }

    // 查找趋势数据
    if (rawData.trends) {
      return {
        historical: (rawData.trends.historical) || [],
        projected: (rawData.trends.projected) || []
      };
    } else if (rawData.trend_data) {
      return {
        historical: (rawData.trend_data.historical) || [],
        projected: (rawData.trend_data.projected) || []
      };
    } else if (rawData.results && Array.isArray(rawData.results)) {
      // 从结果中查找趋势数据
      for (const result of rawData.results) {
        if (result.trends) {
          return {
            historical: (result.trends.historical) || [],
            projected: (result.trends.projected) || []
          };
        }
      }
    }

    return { historical: [], projected: [] };
  } catch (error) {
    console.error('解析趋势数据失败:', error);
    return { historical: [], projected: [] };
  }
};

/**
 * 获取默认报告结构
 */
const getDefaultReportStructure = function() {
  return {
    prediction: { forecast_points: [], confidence: 0, trend: 'neutral' },
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
    trends: { historical: [], projected: [] },
    original: {}
  };
};

/**
 * 将后端复杂嵌套JSON转换为ECharts可用的数据结构
 * @param {Object} rawData - 后端返回的原始数据
 * @returns {Object} ECharts所需的数据结构
 */
const transformForECharts = function(rawData) {
  // 数据防御：检查输入参数
  if (!rawData || typeof rawData !== 'object') {
    console.warn('原始数据无效，返回默认ECharts结构');
    return getDefaultEChartsStructure();
  }

  try {
    // 转换预测数据为ECharts系列数据
    const forecastPoints = (rawData.prediction && rawData.prediction.forecast_points) || [];

    // 构建ECharts配置
    const chartData = {
      // 预测数据转换为ECharts series格式
      series: forecastPoints.map((point, index) => ({
        name: point.name || `预测点${index + 1}`,
        type: point.type || 'line',
        data: Array.isArray(point.values) ? point.values : [point.value || 0]
      })),

      // X轴数据
      xAxis: forecastPoints.map((point, index) => point.label || `时间${index + 1}`),

      // 如果有评分数据，也转换为图表格式
      scoreRadar: rawData.scores ? {
        indicator: [
          { name: '准确性', max: 100 },
          { name: '完整性', max: 100 },
          { name: '相关性', max: 100 },
          { name: '安全性', max: 100 },
          { name: '情感倾向', max: 100 },
          { name: '竞争力', max: 100 }
        ],
        value: [
          rawData.scores.accuracy || 0,
          rawData.scores.completeness || 0,
          rawData.scores.relevance || 0,
          rawData.scores.security || 0,
          rawData.scores.sentiment || 0,
          rawData.scores.competitiveness || 0
        ]
      } : null,

      // 竞争分析数据转换
      competitionData: {
        brandKeywords: (rawData.competition && rawData.competition.brand_keywords) || [],
        sharedKeywords: (rawData.competition && rawData.competition.shared_keywords) || [],
        competitorKeywords: (rawData.competition && rawData.competition.competitor_keywords) || []
      }
    };

    return chartData;
  } catch (error) {
    console.error('转换ECharts数据失败:', error);
    return getDefaultEChartsStructure();
  }
};

/**
 * 获取默认ECharts结构
 */
const getDefaultEChartsStructure = function() {
  return {
    series: [],
    xAxis: [],
    scoreRadar: null,
    competitionData: {
      brandKeywords: [],
      sharedKeywords: [],
      competitorKeywords: []
    }
  };
};

module.exports = {
  parseReportData,
  parsePredictionData,
  parseScoreData,
  parseCompetitionData,
  parseSourceData,
  parseTrendData,
  transformForECharts
};