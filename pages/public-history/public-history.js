const { getPublicHistory } = require('../../utils/local-storage.js');

Page({
  data: {
    searchKeyword: '',
    filteredHistory: [],
    isLoading: false,
    
    // 筛选相关
    timeRange: 'all',
    timeRangeText: '全部时间',
    scoreRange: [0, 100],
    scoreRangeText: '全部分数',
    showTimeFilterModal: false,
    showScoreFilterModal: false,
    
    // 筛选选项
    timeOptions: [
      { label: '全部时间', value: 'all' },
      { label: '今天', value: 'today' },
      { label: '本周', value: 'week' },
      { label: '本月', value: 'month' },
      { label: '三个月内', value: 'three_months' }
    ]
  },

  onLoad: function(options) {
    this.loadPublicHistory();
  },

  onShow: function() {
    this.loadPublicHistory();
  },

  // 加载公共历史记录
  loadPublicHistory: function() {
    try {
      const publicHistory = getPublicHistory();
      this.setData({
        filteredHistory: publicHistory
      });
    } catch (e) {
      console.error('加载公共历史记录失败', e);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  // 搜索输入
  onSearchInput: function(e) {
    this.setData({
      searchKeyword: e.detail.value
    });
  },

  // 搜索
  onSearch: function() {
    this.applyFilters();
  },

  // 应用筛选
  applyFilters: function() {
    let history = getPublicHistory();
    
    // 搜索关键词过滤
    if (this.data.searchKeyword) {
      const keyword = this.data.searchKeyword.toLowerCase();
      history = history.filter(item => 
        item.brandName.toLowerCase().includes(keyword)
      );
    }
    
    // 时间范围过滤
    if (this.data.timeRange !== 'all') {
      const now = Date.now();
      let timeThreshold = 0;

      switch (this.data.timeRange) {
        case 'today':
          timeThreshold = now - 24 * 60 * 60 * 1000;
          break;
        case 'week':
          timeThreshold = now - 7 * 24 * 60 * 60 * 1000;
          break;
        case 'month':
          timeThreshold = now - 30 * 24 * 60 * 60 * 1000;
          break;
        case 'three_months':
          timeThreshold = now - 3 * 30 * 24 * 60 * 60 * 1000;
          break;
      }

      history = history.filter(item => item.timestamp >= timeThreshold);
    }
    
    // 分数范围过滤
    history = history.filter(item => 
      item.overallScore >= this.data.scoreRange[0] && 
      item.overallScore <= this.data.scoreRange[1]
    );
    
    this.setData({
      filteredHistory: history
    });
  },

  // 显示时间筛选弹窗
  showTimeFilter: function() {
    this.setData({
      showTimeFilterModal: true
    });
  },

  // 隐藏时间筛选弹窗
  hideTimeFilter: function() {
    this.setData({
      showTimeFilterModal: false
    });
  },

  // 选择时间选项
  selectTimeOption: function(e) {
    const value = e.currentTarget.dataset.value;
    const option = this.data.timeOptions.find(opt => opt.value === value);
    
    this.setData({
      timeRange: value,
      timeRangeText: option.label,
      showTimeFilterModal: false
    });
    
    this.applyFilters();
  },

  // 显示分数筛选弹窗
  showScoreFilter: function() {
    this.setData({
      showScoreFilterModal: true
    });
  },

  // 隐藏分数筛选弹窗
  hideScoreFilter: function() {
    this.setData({
      showScoreFilterModal: false
    });
  },

  // 最低分改变
  onMinScoreChange: function(e) {
    const minScore = e.detail.value;
    const maxScore = this.data.scoreRange[1];
    
    if (minScore > maxScore) {
      // 如果最小值大于最大值，调整最大值
      this.setData({
        scoreRange: [minScore, minScore]
      });
    } else {
      this.setData({
        scoreRange: [minScore, maxScore]
      });
    }
  },

  // 最高分改变
  onMaxScoreChange: function(e) {
    const maxScore = e.detail.value;
    const minScore = this.data.scoreRange[0];
    
    if (maxScore < minScore) {
      // 如果最大值小于最小值，调整最小值
      this.setData({
        scoreRange: [maxScore, maxScore]
      });
    } else {
      this.setData({
        scoreRange: [minScore, maxScore]
      });
    }
  },

  // 应用分数筛选
  applyScoreFilter: function() {
    const [min, max] = this.data.scoreRange;
    this.setData({
      scoreRangeText: `${min}-${max}分`,
      showScoreFilterModal: false
    });
    
    this.applyFilters();
  },

  // 查看详情
  viewDetail: function(e) {
    const id = e.currentTarget.dataset.id;
    logger.info('查看公共历史详情', { id });

    // 查找对应的报告数据
    const report = this.data.reports.find(r => r.executionId === id || r.id === id);
    
    if (report && report.executionId) {
      // 保存到全局存储
      app.globalData.lastReport = {
        executionId: report.executionId,
        dashboard: report,
        raw: report.rawResults || [],
        competitors: report.competitors || []
      };

      // 跳转到 Dashboard 页面
      wx.navigateTo({
        url: `/pages/report/dashboard/index?executionId=${report.executionId}`,
        success: () => {
          logger.debug('成功跳转到报告详情页');
        },
        fail: (err) => {
          logger.error('跳转到报告详情页失败', err);
          wx.showToast({
            title: '跳转失败',
            icon: 'none'
          });
        }
      });
    } else {
      wx.showToast({
        title: '报告数据不完整',
        icon: 'none'
      });
    }
  },

  // 格式化日期
  formatDate: function(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
})