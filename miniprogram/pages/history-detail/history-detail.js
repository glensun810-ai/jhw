Page({
  data: {
    brandName: '',
    timestamp: 0,
    overallScore: 0,
    overallGrade: 'D',
    overallSummary: '暂无评价',
    overallAuthority: 0,
    overallVisibility: 0,
    overallPurity: 0,
    overallConsistency: 0,
    detailedResults: []
  },

  onLoad: function(options) {
    // 从参数获取历史记录ID
    const recordId = options.id;
    
    if (!recordId) {
      wx.showToast({
        title: '缺少记录ID',
        icon: 'none'
      });
      return;
    }
    
    // 从本地存储获取历史记录
    this.loadHistoryRecord(recordId);
  },

  // 加载历史记录
  loadHistoryRecord: function(recordId) {
    try {
      // 从本地存储获取所有搜索结果
      const searchResults = wx.getStorageSync('savedSearchResults') || [];
      
      // 查找指定ID的记录
      const record = searchResults.find(item => item.id === recordId);
      
      if (!record) {
        wx.showToast({
          title: '未找到记录',
          icon: 'none'
        });
        return;
      }
      
      // 设置页面数据
      this.setData({
        brandName: record.brandName,
        timestamp: record.timestamp,
        overallScore: record.results.overallScore || 0,
        overallGrade: record.results.overallGrade || 'D',
        overallSummary: record.results.overallSummary || '暂无评价',
        overallAuthority: record.results.overallAuthority || 0,
        overallVisibility: record.results.overallVisibility || 0,
        overallPurity: record.results.overallPurity || 0,
        overallConsistency: record.results.overallConsistency || 0,
        detailedResults: record.results.detailed_results || []
      });
    } catch (e) {
      console.error('加载历史记录失败', e);
      wx.showToast({
        title: '加载失败',
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
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({ url: '/pages/index/index' });
  },

  // 查看历史
  viewHistory: function() {
    wx.navigateTo({ url: '/pages/history/history' });
  },

  // 生成报告
  generateReport: function() {
    wx.showLoading({
      title: '正在生成报告...',
      mask: true
    });

    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({
        title: '报告生成成功',
        icon: 'success'
      });
    }, 2000);
  }
})