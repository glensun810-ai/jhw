/**
 * 问题聚合子页面
 */
Page({
  data: {
    questionList: []
  },

  onLoad: function(options) {
    this.loadData();
  },

  async loadData() {
    const history = wx.getStorageSync('diagnosis_history') || [];
    // 数据处理逻辑...
  }
});
