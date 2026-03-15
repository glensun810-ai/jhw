// pages/report/history/history.js - P21 完整修复版
// 修复内容：
// 1. 从后端 API 加载历史记录（而不是本地存储）
// 2. 使用正确的 API 端点
// 3. 修复跳转逻辑

const app = getApp();

Page({
  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    error: null,
    reports: [],
    sortBy: 'time',
    showExecutionId: true
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function(options) {
    console.log('[History] 页面加载');
    this.loadHistory();
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow: function() {
    // 每次显示时重新加载最新数据
    if (!this.data.loading) {
      this.loadHistory();
    }
  },

  /**
   * 加载历史记录（P21 修复：从 API 加载）
   */
  loadHistory: function() {
    var that = this;
    
    console.log('[History] 开始加载历史记录');
    this.setData({ loading: true, error: null });
    
    // 从后端 API 加载
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

  /**
   * 从服务器获取历史记录（P21 修复：使用正确的 API 端点）
   */
  fetchHistoryFromServer: function() {
    var that = this;
    var API_BASE_URL = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';
    var userOpenid = app.globalData.userOpenid || 'anonymous';
    
    return new Promise(function(resolve, reject) {
      console.log('[History] 请求 API:', API_BASE_URL + '/api/diagnosis/history');
      
      wx.request({
        url: API_BASE_URL + '/api/diagnosis/history?user_id=' + userOpenid,
        method: 'GET',
        data: {
          user_id: userOpenid,
          page: 1,
          limit: 100
        },
        timeout: 30000,
        success: function(res) {
          console.log('[History] API 响应:', res.data);
          
          if (res.statusCode === 200 && res.data) {
            var data = res.data;
            var reports = data.reports || data.history || data.list || [];
            
            console.log('[History] 获取到 ' + reports.length + ' 条记录');
            
            // 排序
            var sortedReports = that.sortReports(reports);
            
            that.setData({
              loading: false,
              reports: sortedReports
            });
            
            // 同步到本地存储
            wx.setStorageSync('diagnosisHistory', sortedReports);
            
            resolve();
          } else {
            console.error('[History] 服务器响应异常:', res.statusCode);
            reject(new Error('服务器响应异常：' + res.statusCode));
          }
        },
        fail: function(error) {
          console.error('[History] 请求失败:', error);
          
          // 如果 API 请求失败，尝试从本地存储加载
          console.log('[History] 尝试从本地存储加载');
          that.loadFromLocalStorage();
          resolve(); // 不 reject，避免页面显示错误
        }
      });
    });
  },

  /**
   * 从本地存储加载（备用方案）
   */
  loadFromLocalStorage: function() {
    var history = wx.getStorageSync('diagnosisHistory') || [];
    console.log('[History] 本地存储加载:', history.length + ' 条');
    
    if (history.length > 0) {
      var sortedHistory = this.sortReports(history);
      this.setData({
        loading: false,
        reports: sortedHistory
      });
    } else {
      this.setData({
        loading: false,
        reports: [],
        error: '暂无历史记录'
      });
    }
  },

  /**
   * 排序报告列表
   */
  sortReports: function(reports) {
    var sortBy = this.data.sortBy;
    
    var sorted = [].concat(reports).sort(function(a, b) {
      if (sortBy === 'time') {
        var timeA = a.createdAt || a.created_at || a.diagnoseAt || 0;
        var timeB = b.createdAt || b.created_at || b.diagnoseAt || 0;
        return timeB - timeA;
      } else if (sortBy === 'score') {
        var scoreA = a.healthScore || a.health_score || a.score || 0;
        var scoreB = b.healthScore || b.health_score || b.score || 0;
        return scoreB - scoreA;
      } else if (sortBy === 'brand') {
        var brandA = (a.brandName || a.brand_name || a.brand || '').toLowerCase();
        var brandB = (b.brandName || b.brand_name || b.brand || '').toLowerCase();
        return brandA.localeCompare(brandB);
      }
      return 0;
    });
    
    return sorted;
  },

  /**
   * 改变排序方式
   */
  changeSort: function(e) {
    var sort = e.currentTarget.dataset.sort;
    console.log('[History] 改变排序方式:', sort);
    
    if (this.data.sortBy !== sort) {
      this.setData({ sortBy: sort });
      var sortedReports = this.sortReports(this.data.reports);
      this.setData({ reports: sortedReports });
      
      wx.showToast({
        title: '按' + (sort === 'time' ? '时间' : sort === 'score' ? '评分' : '品牌') + '排序',
        icon: 'none',
        duration: 1500
      });
    }
  },

  /**
   * 查看报告详情（P21 修复：跳转到详情页）
   */
  viewDetail: function(e) {
    var item = e.currentTarget.dataset.item;
    console.log('[History] 查看报告详情:', item);
    
    if (item && item.executionId) {
      // 跳转到诊断详情页
      wx.navigateTo({
        url: '/pages/report/detail/index?executionId=' + item.executionId,
        success: function() {
          console.log('[History] 跳转成功');
        },
        fail: function(err) {
          console.error('[History] 跳转失败:', err);
          wx.showToast({
            title: '跳转失败',
            icon: 'none'
          });
        }
      });
    } else {
      console.error('[History] 报告数据不完整:', item);
      wx.showToast({
        title: '报告数据不完整',
        icon: 'none'
      });
    }
  },

  /**
   * 返回首页
   */
  goHome: function() {
    wx.switchTab({
      url: '/pages/index/index',
      fail: function() {
        wx.navigateTo({
          url: '/pages/index/index'
        });
      }
    });
  },

  /**
   * 重试加载
   */
  retry: function() {
    this.loadHistory();
  }
});
