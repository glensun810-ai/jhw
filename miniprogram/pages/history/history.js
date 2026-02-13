const { getTestHistory } = require('../../api/history.js');

Page({
  data: {
    historyList: [],
    isLoading: true,
    openid: ''
  },

  onLoad: function (options) {
    const openid = wx.getStorageSync('openid');
    if (openid) {
      this.setData({ openid: openid });
      this.loadHistory();
    } else {
      // 如果没有 openid，可以提示用户先登录
      wx.showToast({
        title: '请先登录以查看历史记录',
        icon: 'none',
        duration: 2000,
        complete: () => {
          setTimeout(() => {
            wx.navigateBack();
          }, 2000);
        }
      });
    }
  },

  // 下拉刷新
  onPullDownRefresh: function () {
    this.loadHistory();
  },

  // 加载历史记录
  async loadHistory() {
    this.setData({ isLoading: true });
    try {
      const res = await getTestHistory({
        userOpenid: this.data.openid
      });

      if (res.statusCode === 200 && res.data.status === 'success') {
        // 格式化时间
        const formattedHistory = res.data.history.map(item => {
          item.created_at = new Date(item.created_at).toLocaleString();
          return item;
        });
        this.setData({
          historyList: formattedHistory,
          isLoading: false
        });
      } else {
        this.setData({ isLoading: false });
        wx.showToast({ title: '加载失败', icon: 'error' });
      }
    } catch (err) {
      this.setData({ isLoading: false });
      console.error('加载历史记录失败:', err);
      wx.showToast({ title: '网络请求失败', icon: 'error' });
    } finally {
      wx.stopPullDownRefresh();
    }
  },

  // 查看详情
  viewDetail: function (e) {
    const recordId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/history-detail/history-detail?id=${recordId}`
    });
  },

  // 查看最近一次的诊断结果
  viewLatestResult: function() {
    const cachedResults = wx.getStorageSync('latestTestResults');
    const cachedAnalysis = wx.getStorageSync('latestCompetitiveAnalysis');
    const cachedBrand = wx.getStorageSync('latestTargetBrand');

    if (cachedResults && cachedAnalysis && cachedBrand) {
      const params = {
        results: JSON.stringify(cachedResults),
        competitiveAnalysis: encodeURIComponent(JSON.stringify(cachedAnalysis)),
        targetBrand: cachedBrand
      };

      const queryString = Object.keys(params)
        .map(key => `${key}=${params[key]}`)
        .join('&');

      wx.navigateTo({ url: `/pages/results/results?${queryString}` });
    } else {
      wx.showToast({
        title: '暂无最近的诊断结果',
        icon: 'none'
      });
    }
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({
      url: '/pages/index/index'
    });
  },

  // 查看已保存的结果
  viewSavedResults: function() {
    wx.navigateTo({
      url: '/pages/saved-results/saved-results'
    });
  },

  // 查看公共历史记录
  viewPublicHistory: function() {
    wx.navigateTo({
      url: '/pages/public-history/public-history'
    });
  },

  // 查看个人历史记录
  viewPersonalHistory: function() {
    wx.navigateTo({
      url: '/pages/personal-history/personal-history'
    });
  }
})