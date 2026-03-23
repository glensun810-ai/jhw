/**
 * 品牌对比子页面
 */
Page({
  data: {
    brandList: []
  },

  onLoad: function(options) {
    this.loadData();
  },

  async loadData() {
    // 从主页面获取数据或重新加载
    const history = wx.getStorageSync('diagnosis_history') || [];
    // 数据处理逻辑...
  }
});
