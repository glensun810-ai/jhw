/**
 * 品牌维度分析页面
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

Page({
  data: {
    // 分析指标
    metricOptions: [
      { label: '综合评分', value: 'overall' },
      { label: '声量份额', value: 'sov' },
      { label: '情感得分', value: 'sentiment' },
      { label: '物理排名', value: 'ranking' }
    ],
    metricIndex: 0,
    
    // 图表数据
    scoreCompareData: [],
    sovData: [],
    sentimentData: [],
    rankingData: [],
    
    // 加载状态
    loading: false,
    loaded: false
  },

  onLoad: function(options) {
    this.loadData();
  },

  onPullDownRefresh: function() {
    this.loadData().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载数据
   */
  async loadData() {
    this.setData({ loading: true });
    
    try {
      const history = this.getFilteredHistory();
      
      // 加载各项数据
      this.loadScoreCompare(history);
      this.loadSOVData(history);
      this.loadSentimentData(history);
      this.loadRankingData(history);
      
      this.setData({
        loading: false,
        loaded: true
      });
    } catch (error) {
      console.error('加载数据失败:', error);
      this.setData({ loading: false });
    }
  },

  /**
   * 获取筛选后的数据
   */
  getFilteredHistory: function() {
    let history = wx.getStorageSync('diagnosis_history_list') || [];
    
    // 时间范围筛选
    const timeRange = 'last30days'; // 默认近 30 天
    const now = Date.now();
    let timeThreshold = now - 30 * 24 * 60 * 60 * 1000;
    
    history = history.filter(record => {
      const recordTime = new Date(record.createdAt || 0).getTime();
      return recordTime >= timeThreshold;
    });
    
    return history;
  },

  /**
   * 加载综合评分对比
   */
  loadScoreCompare: function(history) {
    const brandMap = {};
    
    history.forEach(record => {
      const brand = record.brandName || '未知';
      const score = record.overallScore || 0;
      
      if (!brandMap[brand]) {
        brandMap[brand] = { scores: [] };
      }
      brandMap[brand].scores.push(score);
    });
    
    const scoreCompareData = Object.entries(brandMap).map(([brand, data]) => ({
      name: brand,
      value: Math.round(data.scores.reduce((a, b) => a + b, 0) / data.scores.length)
    })).sort((a, b) => b.value - a.value);
    
    this.setData({ scoreCompareData });
  },

  /**
   * 加载声量份额数据
   */
  loadSOVData: function(history) {
    const brandMap = {};
    let totalWordCount = 0;
    
    history.forEach(record => {
      const brand = record.brandName || '未知';
      // 假设每个诊断的字数相近，用诊断次数代替
      if (!brandMap[brand]) {
        brandMap[brand] = { count: 0 };
      }
      brandMap[brand].count += 1;
      totalWordCount += 1;
    });
    
    const colors = ['#4A7BFF', '#00F5A0', '#f39c12', '#e74c3c', '#9b59b6', '#3498db'];
    
    const sovData = Object.entries(brandMap)
      .map(([brand, data], index) => {
        const percentage = Math.round((data.count / totalWordCount) * 100);
        return {
          brand,
          percentage,
          color: colors[index % colors.length]
        };
      })
      .sort((a, b) => b.percentage - a.percentage);
    
    this.setData({ sovData });
  },

  /**
   * 加载情感得分数据
   */
  loadSentimentData: function(history) {
    const brandMap = {};
    
    history.forEach(record => {
      const brand = record.brandName || '未知';
      // 使用 overallScore 作为情感得分的代理
      const sentiment = record.overallScore || 0;
      
      if (!brandMap[brand]) {
        brandMap[brand] = { scores: [] };
      }
      brandMap[brand].scores.push(sentiment);
    });
    
    const colors = ['#e74c3c', '#f39c12', '#00F5A0'];
    
    const sentimentData = Object.entries(brandMap)
      .map(([brand, data]) => {
        const avgScore = Math.round(data.scores.reduce((a, b) => a + b, 0) / data.scores.length);
        let level = 'poor';
        let color = colors[0];
        
        if (avgScore >= 80) {
          level = 'excellent';
          color = colors[2];
        } else if (avgScore >= 60) {
          level = 'good';
          color = colors[1];
        }
        
        return {
          brand,
          score: avgScore,
          level,
          color
        };
      })
      .sort((a, b) => b.score - a.score);
    
    this.setData({ sentimentData });
  },

  /**
   * 加载物理排名数据
   */
  loadRankingData: function(history) {
    const brandMap = {};
    
    history.forEach(record => {
      const brand = record.brandName || '未知';
      // 假设排名，实际应该从后端数据获取
      const rank = Math.floor(Math.random() * 5) + 1;
      
      if (!brandMap[brand]) {
        brandMap[brand] = { ranks: [] };
      }
      brandMap[brand].ranks.push(rank);
    });
    
    const trends = ['up', 'stable', 'down'];
    const trendIcons = ['↑', '→', '↓'];
    
    const rankingData = Object.entries(brandMap)
      .map(([brand, data], index) => {
        const avgRank = (data.ranks.reduce((a, b) => a + b, 0) / data.ranks.length).toFixed(1);
        const trendIndex = Math.floor(Math.random() * 3);
        
        return {
          rank: index + 1,
          brand,
          avgRank,
          trend: trends[trendIndex],
          trendIcon: trendIcons[trendIndex]
        };
      })
      .sort((a, b) => parseFloat(a.avgRank) - parseFloat(b.avgRank));
    
    this.setData({ rankingData });
  },

  /**
   * 指标切换
   */
  onMetricChange: function(e) {
    const index = e.detail.value;
    this.setData({ metricIndex: index });
  }
});
