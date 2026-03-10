/**
 * dataProcessorService 测试
 * 
 * 测试覆盖：
 * - processReportData
 * - extractScoreData
 * - extractCompetitionData
 * - extractPredictionData
 */

const { describe, test, beforeAll, afterAll, beforeEach, afterEach, expect, mockWx } = require('./test-utils');
const {
  processReportData,
  extractScoreData,
  extractCompetitionData,
  extractPredictionData,
  extractSourceListData,
  generateTrendChartData,
  defensiveGet,
  getDefaultReportStructure
} = require('../services/dataProcessorService');

describe('dataProcessorService 测试', () => {
  
  // 测试数据
  const mockReportData = {
    scores: {
      accuracy: 85,
      completeness: 90,
      relevance: 75,
      security: 95,
      sentiment: 80,
      competitiveness: 70,
      authority: 88
    },
    competition: {
      brand_keywords: ['品牌 A', '知名品牌'],
      shared_keywords: ['行业领先', '创新'],
      competitors: ['品牌 B', '品牌 C']
    },
    prediction: {
      forecast_points: [85, 88, 90, 92, 95],
      confidence: 0.85,
      trend: 'positive'
    },
    results: [
      { brand: '品牌 A', score: 85, response: '正面评价' },
      { brand: '品牌 B', score: 75, response: '中性评价' }
    ],
    sources: [
      { title: '来源 1', url: 'http://example.com/1', score: 90 },
      { title: '来源 2', url: 'http://example.com/2', score: 85 }
    ]
  };

  beforeEach(() => {
    // 每个测试前清空 Mock
    Object.keys(mockWx).forEach(key => {
      if (mockWx[key] && mockWx[key].mockClear) {
        mockWx[key].mockClear();
      }
    });
  });

  describe('processReportData 测试', () => {
    test('应该正确处理完整数据', () => {
      const result = processReportData(mockReportData);
      
      expect(result.scores).toEqual(mockReportData.scores);
      expect(result.competition).toEqual(mockReportData.competition);
      expect(result.prediction).toEqual(mockReportData.prediction);
      expect(result.sources).toEqual(mockReportData.sources);
      expect(result.results).toEqual(mockReportData.results);
    });

    test('应该处理空数据', () => {
      const result = processReportData(null);
      const expected = getDefaultReportStructure();
      
      expect(result).toEqual(expected);
    });

    test('应该处理缺失字段的数据', () => {
      const incompleteData = {
        scores: { accuracy: 80 }
      };
      
      const result = processReportData(incompleteData);
      
      expect(result.scores.accuracy).toBe(80);
      expect(result.results).toEqual([]);
    });
  });

  describe('extractScoreData 测试', () => {
    test('应该正确提取评分数据', () => {
      const result = extractScoreData(mockReportData);
      
      expect(result.accuracy).toBe(85);
      expect(result.completeness).toBe(90);
      expect(result.relevance).toBe(75);
      expect(result.security).toBe(95);
      expect(result.sentiment).toBe(80);
      expect(result.competitiveness).toBe(70);
      expect(result.authority).toBe(88);
    });

    test('应该处理缺失的评分数据', () => {
      const result = extractScoreData({});
      
      expect(result.accuracy).toBe(0);
      expect(result.completeness).toBe(0);
      expect(result.relevance).toBe(0);
    });

    test('应该处理空数据', () => {
      const result = extractScoreData(null);
      
      expect(result.accuracy).toBe(0);
      expect(result.completeness).toBe(0);
    });

    test('应该从 results 中提取评分', () => {
      const data = {
        results: [{
          scores: {
            accuracy: 77,
            completeness: 88
          }
        }]
      };
      
      const result = extractScoreData(data);
      
      expect(result.accuracy).toBe(77);
      expect(result.completeness).toBe(88);
    });
  });

  describe('extractCompetitionData 测试', () => {
    test('应该正确提取竞争数据', () => {
      const result = extractCompetitionData(mockReportData);
      
      expect(result.brand_keywords).toContain('品牌 A');
      expect(result.brand_keywords).toContain('知名品牌');
      expect(result.shared_keywords).toContain('行业领先');
      expect(result.competitors).toContain('品牌 B');
    });

    test('应该处理缺失的竞争数据', () => {
      const result = extractCompetitionData({});
      
      expect(result.brand_keywords).toEqual([]);
      expect(result.shared_keywords).toEqual([]);
      expect(result.competitors).toEqual([]);
    });

    test('应该从 competitive_analysis 中提取', () => {
      const data = {
        competitive_analysis: {
          brand_keywords: ['分析品牌'],
          shared_keywords: ['共享词'],
          competitors: ['竞品']
        }
      };
      
      const result = extractCompetitionData(data);
      
      expect(result.brand_keywords).toContain('分析品牌');
      expect(result.shared_keywords).toContain('共享词');
    });
  });

  describe('extractPredictionData 测试', () => {
    test('应该正确提取预测数据', () => {
      const result = extractPredictionData(mockReportData);
      
      expect(result.forecast_points).toEqual([85, 88, 90, 92, 95]);
      expect(result.confidence).toBe(0.85);
      expect(result.trend).toBe('positive');
    });

    test('应该处理缺失的预测数据', () => {
      const result = extractPredictionData({});
      
      expect(result.forecast_points).toEqual([]);
      expect(result.confidence).toBe(0);
      expect(result.trend).toBe('neutral');
    });

    test('应该从 results 中提取预测', () => {
      const data = {
        results: [{
          prediction: {
            forecast_points: [70, 75, 80],
            confidence: 0.7,
            trend: 'negative'
          }
        }]
      };
      
      const result = extractPredictionData(data);
      
      expect(result.forecast_points).toEqual([70, 75, 80]);
      expect(result.confidence).toBe(0.7);
      expect(result.trend).toBe('negative');
    });
  });

  describe('extractSourceListData 测试', () => {
    test('应该正确提取信源列表', () => {
      const result = extractSourceListData(mockReportData);
      
      expect(result.length).toBe(2);
      expect(result[0].title).toBe('来源 1');
      expect(result[0].url).toBe('http://example.com/1');
      expect(result[0].score).toBe(90);
    });

    test('应该处理缺失的信源数据', () => {
      const result = extractSourceListData({});
      
      // 应该返回默认数据
      expect(result.length).toBeGreaterThan(0);
    });

    test('应该从 results 中提取信源', () => {
      const data = {
        results: [{
          sources: [
            { title: '结果来源', url: 'http://example.com', score: 88 }
          ]
        }]
      };
      
      const result = extractSourceListData(data);
      
      expect(result.length).toBe(1);
      expect(result[0].title).toBe('结果来源');
    });
  });

  describe('generateTrendChartData 测试', () => {
    test('应该正确生成趋势图数据', () => {
      const data = {
        timeSeries: [
          { period: '周一', value: 30 },
          { period: '周二', value: 45 },
          { period: '周三', value: 60 }
        ],
        prediction: {
          forecast_points: [88, 92, 95]
        }
      };
      
      const result = generateTrendChartData(data);
      
      expect(result.dates).toEqual(['周一', '周二', '周三']);
      expect(result.values).toEqual([30, 45, 60]);
      // 预测数据从 prediction.forecast_points 提取
      expect(result.predictions).toEqual([88, 92, 95]);
    });

    test('应该处理缺失的时间序列数据', () => {
      const result = generateTrendChartData({});
      
      // 应该返回默认数据
      expect(result.dates.length).toBe(7);
      expect(result.values.length).toBe(7);
    });

    test('应该处理空数据', () => {
      const result = generateTrendChartData(null);
      
      expect(result.dates).toEqual([]);
      expect(result.values).toEqual([]);
      expect(result.predictions).toEqual([]);
    });
  });

  describe('defensiveGet 测试', () => {
    test('应该正确获取嵌套属性', () => {
      const obj = {
        a: {
          b: {
            c: 'value'
          }
        }
      };
      
      const result = defensiveGet(obj, 'a.b.c', 'default');
      expect(result).toBe('value');
    });

    test('应该返回默认值当属性不存在', () => {
      const obj = { a: { b: 'value' } };
      
      const result = defensiveGet(obj, 'a.c.d', 'default');
      expect(result).toBe('default');
    });

    test('应该处理 null 对象', () => {
      const result = defensiveGet(null, 'a.b', 'default');
      expect(result).toBe('default');
    });

    test('应该处理 undefined 对象', () => {
      const result = defensiveGet(undefined, 'a.b', 'default');
      expect(result).toBe('default');
    });
  });

  describe('getDefaultReportStructure 测试', () => {
    test('应该返回默认报告结构', () => {
      const result = getDefaultReportStructure();
      
      expect(result.prediction).toBeDefined();
      expect(result.scores).toBeDefined();
      expect(result.competition).toBeDefined();
      expect(result.sources).toBeDefined();
      expect(result.results).toEqual([]);
    });

    test('默认预测数据应该正确', () => {
      const result = getDefaultReportStructure();
      
      expect(result.prediction.forecast_points).toEqual([]);
      expect(result.prediction.confidence).toBe(0);
      expect(result.prediction.trend).toBe('neutral');
    });

    test('默认评分数据应该正确', () => {
      const result = getDefaultReportStructure();
      
      expect(result.scores.accuracy).toBe(0);
      expect(result.scores.completeness).toBe(0);
      expect(result.scores.relevance).toBe(0);
    });
  });
});

// 运行测试
if (require.main === module) {
  const { runTests } = require('./test-utils');
  runTests();
}
