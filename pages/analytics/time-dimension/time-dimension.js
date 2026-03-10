/**
 * 时间维度分析页面
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

Page({
  data: {
    // 品牌选择
    brandOptions: [{ label: '全部品牌', value: 'all' }],
    brandIndex: 0,
    selectedBrand: 'all',
    
    // 时间范围
    timeRange: 'last90days',
    timeRangeOptions: [
      { label: '近 7 天', value: 'last7days' },
      { label: '近 30 天', value: 'last30days' },
      { label: '近 90 天', value: 'last90days' }
    ],
    
    // 图表数据
    scoreTrendData: [],
    volumeData: [],
    sentimentTrendData: [],
    rankingTrendData: [],
    
    // UI 状态
    showTooltip: false,
    loading: false
  },

  onLoad: function(options) {
    this.loadBrandOptions();
  },

  onShow: function() {
    this.loadData();
  },

  onPullDownRefresh: function() {
    this.loadData().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载品牌选项
   */
  loadBrandOptions: function() {
    try {
      const history = wx.getStorageSync('diagnosis_history_list') || [];
      
      const brandSet = new Set();
      history.forEach(record => {
        if (record.brandName) {
          brandSet.add(record.brandName);
        }
      });
      
      const brandOptions = [
        { label: '全部品牌', value: 'all' },
        ...Array.from(brandSet).map(brand => ({ label: brand, value: brand }))
      ];
      
      this.setData({ brandOptions });
    } catch (error) {
      console.error('加载品牌选项失败:', error);
    }
  },

  /**
   * 加载数据
   */
  async loadData() {
    this.setData({ loading: true });
    
    try {
      const history = this.getFilteredHistory();
      
      this.loadScoreTrend(history);
      this.loadVolumeData(history);
      this.loadSentimentTrend(history);
      this.loadRankingTrend(history);
      
      this.setData({ loading: false });
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
    
    // 品牌筛选
    if (this.data.selectedBrand !== 'all') {
      history = history.filter(record => record.brandName === this.data.selectedBrand);
    }
    
    // 时间筛选
    const now = Date.now();
    let timeThreshold = 0;
    
    switch (this.data.timeRange) {
      case 'last7days':
        timeThreshold = now - 7 * 24 * 60 * 60 * 1000;
        break;
      case 'last30days':
        timeThreshold = now - 30 * 24 * 60 * 60 * 1000;
        break;
      case 'last90days':
        timeThreshold = now - 90 * 24 * 60 * 60 * 1000;
        break;
    }
    
    if (timeThreshold > 0) {
      history = history.filter(record => {
        const recordTime = new Date(record.createdAt || 0).getTime();
        return recordTime >= timeThreshold;
      });
    }
    
    return history;
  },

  /**
   * 加载评分趋势
   */
  loadScoreTrend: function(history) {
    const sortedHistory = history.sort((a, b) => {
      const timeA = new Date(a.createdAt || 0).getTime();
      const timeB = new Date(b.createdAt || 0).getTime();
      return timeA - timeB;
    });
    
    const scoreTrendData = sortedHistory.map(record => {
      const date = new Date(record.createdAt || 0);
      return {
        value: record.overallScore || 0,
        label: `${date.getMonth() + 1}/${date.getDate()}`
      };
    });
    
    this.setData({ scoreTrendData });
  },

  /**
   * 加载声量数据
   */
  loadVolumeData: function(history) {
    // 按日期分组
    const dateMap = {};
    
    history.forEach(record => {
      const date = new Date(record.createdAt || 0);
      const dateKey = `${date.getMonth() + 1}/${date.getDate()}`;
      
      if (!dateMap[dateKey]) {
        dateMap[dateKey] = 0;
      }
      dateMap[dateKey] += 1;
    });
    
    const maxValue = Math.max(...Object.values(dateMap), 1);
    
    const volumeData = Object.entries(dateMap).map(([date, count]) => ({
      date,
      value: count,
      label: date,
      height: (count / maxValue) * 80 + 20 // 20%-100% 高度
    }));
    
    this.setData({ volumeData });
  },

  /**
   * 加载情感趋势
   */
  loadSentimentTrend: function(history) {
    const sortedHistory = history.sort((a, b) => {
      const timeA = new Date(a.createdAt || 0).getTime();
      const timeB = new Date(b.createdAt || 0).getTime();
      return timeA - timeB;
    });
    
    const sentimentTrendData = sortedHistory.map((record, index) => {
      const score = record.overallScore || 0;
      let level = 'poor';
      
      if (score >= 80) level = 'excellent';
      else if (score >= 60) level = 'good';
      
      return {
        date: new Date(record.createdAt || 0).toLocaleDateString(),
        score,
        level,
        x: (index / (sortedHistory.length - 1 || 1)) * 100,
        y: (score / 100) * 80 + 10
      };
    });
    
    this.setData({ sentimentTrendData });
  },

  /**
   * 加载排名趋势
   */
  loadRankingTrend: function(history) {
    const sortedHistory = history.sort((a, b) => {
      const timeA = new Date(a.createdAt || 0).getTime();
      const timeB = new Date(b.createdAt || 0).getTime();
      return timeA - timeB;
    });
    
    const rankingTrendData = sortedHistory.map((record, index) => {
      // 模拟排名数据
      const rank = Math.floor(Math.random() * 5) + 1;
      
      return {
        date: new Date(record.createdAt || 0).toLocaleDateString(),
        rank,
        x: (index / (sortedHistory.length - 1 || 1)) * 100,
        y: ((6 - rank) / 5) * 80 + 10
      };
    });
    
    this.setData({ rankingTrendData });
  },

  /**
   * 品牌切换
   */
  onBrandChange: function(e) {
    const index = e.detail.value;
    const brand = this.data.brandOptions[index];
    
    this.setData({
      brandIndex: index,
      selectedBrand: brand.value
    });
    
    this.loadData();
  },

  /**
   * 时间范围切换
   */
  onTimeRangeChange: function(e) {
    const { value } = e.currentTarget.dataset;
    
    this.setData({ timeRange: value });
    this.loadData();
  }
});
