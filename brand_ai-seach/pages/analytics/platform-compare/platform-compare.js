/**
 * AI 平台对比子页面
 */
Page({
  data: {
    platformList: []
  },

  onLoad: function(options) {
    this.loadData();
  },

  async loadData() {
    const history = wx.getStorageSync('diagnosis_history') || [];
    // 数据处理逻辑...
  }
});
