/**
 * Mock 数据服务
 * 用于在 backend API 未完成时提供测试数据
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

/**
 * 生成品牌对比 Mock 数据
 */
const getBrandCompareMock = () => {
  return {
    status: 'success',
    data: {
      brands: [
        { name: '华为', value: 88, trend: 'up' },
        { name: '小米', value: 82, trend: 'up' },
        { name: 'OPPO', value: 75, trend: 'down' },
        { name: 'vivo', value: 73, trend: 'stable' },
        { name: '荣耀', value: 70, trend: 'up' }
      ],
      timeRange: 'last30days',
      updatedAt: new Date().toISOString()
    }
  };
};

/**
 * 生成趋势分析 Mock 数据
 */
const getTrendAnalysisMock = () => {
  const today = new Date();
  const trend = [];
  
  for (let i = 9; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i * 3);
    trend.push({
      value: Math.floor(60 + Math.random() * 30),
      label: `${date.getMonth() + 1}/${date.getDate()}`,
      timestamp: date.getTime()
    });
  }
  
  return {
    status: 'success',
    data: {
      trend,
      metric: 'sov_share',
      timeRange: 'last30days'
    }
  };
};

/**
 * 生成 AI 平台对比 Mock 数据
 */
const getPlatformCompareMock = () => {
  return {
    status: 'success',
    data: {
      platforms: [
        { name: '声量', value: 85 },
        { name: '情感', value: 72 },
        { name: '权威', value: 68 },
        { name: '可见', value: 78 },
        { name: '纯净', value: 82 },
        { name: '一致', value: 75 }
      ]
    }
  };
};

/**
 * 生成问题聚合 Mock 数据
 */
const getQuestionAnalysisMock = () => {
  return {
    status: 'success',
    data: {
      questions: [
        { name: '品牌知名度如何', value: 156, sentiment: 'positive' },
        { name: '产品质量怎么样', value: 132, sentiment: 'neutral' },
        { name: '和竞品比哪个更好', value: 98, sentiment: 'neutral' },
        { name: '性价比如何', value: 85, sentiment: 'positive' },
        { name: '售后服务好吗', value: 72, sentiment: 'negative' },
        { name: '有什么优缺点', value: 65, sentiment: 'neutral' },
        { name: '值得购买吗', value: 58, sentiment: 'positive' },
        { name: '用户评价如何', value: 52, sentiment: 'positive' },
        { name: '最新款怎么样', value: 45, sentiment: 'neutral' },
        { name: '适合什么人用', value: 38, sentiment: 'neutral' }
      ],
      total: 10,
      timeRange: 'last30days'
    }
  };
};

/**
 * 生成行业基准 Mock 数据
 */
const getBenchmarkMock = (category = 'default') => {
  return {
    status: 'success',
    data: {
      industry: category,
      average: {
        sovShare: 65,
        sentimentScore: 70,
        overallScore: 68
      },
      top10Percent: {
        sovShare: 85,
        sentimentScore: 88,
        overallScore: 86
      },
      topPerformers: ['品牌 A', '品牌 B', '品牌 C']
    }
  };
};

module.exports = {
  getBrandCompareMock,
  getTrendAnalysisMock,
  getPlatformCompareMock,
  getQuestionAnalysisMock,
  getBenchmarkMock
};
