const serverUrl = 'http://127.0.0.1:5001';

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
  loadHistory: function () {
    this.setData({ isLoading: true });
    wx.request({
      url: `${serverUrl}/api/test-history`,
      method: 'GET',
      data: {
        userOpenid: this.data.openid
      },
      success: (res) => {
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
      },
      fail: (err) => {
        this.setData({ isLoading: false });
        console.error('加载历史记录失败:', err);
        wx.showToast({ title: '网络请求失败', icon: 'error' });
      },
      complete: () => {
        wx.stopPullDownRefresh();
      }
    });
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
  }
})