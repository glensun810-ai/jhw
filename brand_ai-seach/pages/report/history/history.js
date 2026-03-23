// pages/report/history/history.js
// P21 修复版 - 从 API 加载历史记录

const app = getApp();

Page({
  data: {
    loading: true,
    error: null,
    reports: [],
    sortBy: 'time',
    showExecutionId: true
  },

  onLoad: function(options) {
    console.log('[History] 页面加载');
    this.loadHistory();
  },

  onShow: function() {
    if (!this.data.loading) {
      this.loadHistory();
    }
  },

  loadHistory: function() {
    var that = this;
    console.log('[History] 开始加载历史记录');
    this.setData({ loading: true, error: null });
    
    this.fetchHistoryFromServer()
      .then(function() {
        console.log('[History] 加载成功');
      })
      .catch(function(error) {
        console.error('[History] 加载失败:', error);
        that.setData({
          loading: false,
          error: '加载失败：' + (error.message || '未知错误')
        });
      });
  },

  fetchHistoryFromServer: function() {
    var that = this;
    var API_BASE_URL = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';
    var userOpenid = app.globalData.userOpenid || 'anonymous';
    
    return new Promise(function(resolve, reject) {
      console.log('[History] 请求 API:', API_BASE_URL + '/api/diagnosis/history');
      
      wx.request({
        url: API_BASE_URL + '/api/diagnosis/history?user_id=' + userOpenid,
        method: 'GET',
        data: { user_id: userOpenid, page: 1, limit: 100 },
        timeout: 30000,
        success: function(res) {
          console.log('[History] API 响应:', res.data);
          
          if (res.statusCode === 200 && res.data) {
            var data = res.data;
            var reports = data.reports || data.history || data.list || [];
            console.log('[History] 获取到 ' + reports.length + ' 条记录');
            
            var sortedReports = that.sortReports(reports);
            that.setData({ loading: false, reports: sortedReports });
            wx.setStorageSync('diagnosisHistory', sortedReports);
            resolve();
          } else {
            reject(new Error('服务器响应异常'));
          }
        },
        fail: function(error) {
          console.error('[History] 请求失败:', error);
          that.loadFromLocalStorage();
          resolve();
        }
      });
    });
  },

  loadFromLocalStorage: function() {
    var history = wx.getStorageSync('diagnosisHistory') || [];
    console.log('[History] 本地存储加载:', history.length + ' 条');
    
    if (history.length > 0) {
      this.setData({ loading: false, reports: this.sortReports(history) });
    } else {
      this.setData({ loading: false, reports: [], error: '暂无历史记录' });
    }
  },

  sortReports: function(reports) {
    var sortBy = this.data.sortBy;
    return [].concat(reports).sort(function(a, b) {
      if (sortBy === 'time') {
        // 适配 snake_case: created_at
        return (b.created_at || b.createdAt || 0) - (a.created_at || a.createdAt || 0);
      } else if (sortBy === 'score') {
        // 适配 snake_case: health_score
        return (b.health_score || b.healthScore || b.score || 0) - (a.health_score || a.healthScore || a.score || 0);
      } else if (sortBy === 'brand') {
        // 适配 snake_case: brand_name
        return (a.brand_name || a.brandName || a.brand || '').toLowerCase().localeCompare(b.brand_name || b.brandName || b.brand || '');
      }
      return 0;
    });
  },

  changeSort: function(e) {
    var sort = e.currentTarget.dataset.sort;
    if (this.data.sortBy !== sort) {
      this.setData({ sortBy: sort });
      this.setData({ reports: this.sortReports(this.data.reports) });
      wx.showToast({
        title: '按' + (sort === 'time' ? '时间' : sort === 'score' ? '评分' : '品牌') + '排序',
        icon: 'none',
        duration: 1500
      });
    }
  },

  viewDetail: function(e) {
    var item = e.currentTarget.dataset.item;
    console.log('[History] 查看报告详情:', item);
    
    if (item && item.executionId) {
      wx.navigateTo({
        url: '/pages/report/detail/index?executionId=' + item.executionId,
        success: function() { console.log('[History] 跳转成功'); },
        fail: function(err) {
          console.error('[History] 跳转失败:', err);
          wx.showToast({ title: '跳转失败', icon: 'none' });
        }
      });
    } else {
      wx.showToast({ title: '报告数据不完整', icon: 'none' });
    }
  },

  goHome: function() {
    wx.switchTab({
      url: '/pages/index/index',
      fail: function() { wx.navigateTo({ url: '/pages/index/index' }); }
    });
  },

  retry: function() {
    this.loadHistory();
  }
});
