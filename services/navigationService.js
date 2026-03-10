/**
 * 导航服务
 * 统一管理所有页面跳转逻辑
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

const navigationService = {
  /**
   * 跳转到诊断记录列表
   * @param {object} options - 选项
   */
  navigateToHistory: function(options = {}) {
    const { animation = true } = options;
    wx.switchTab({
      url: '/pages/history/history',
      fail: (err) => {
        console.error('❌ 跳转到诊断记录失败:', err);
      }
    });
  },

  /**
   * 跳转到诊断记录详情（报告页）
   * @param {string} executionId - 执行 ID
   * @param {string} brandName - 品牌名称
   * @param {object} options - 选项
   */
  navigateToReportDetail: function(executionId, brandName, options = {}) {
    const { events = {} } = options;

    wx.navigateTo({
      url: `/pages/history-detail/history-detail?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`,
      events: events,
      fail: (err) => {
        console.error('❌ 跳转到报告详情失败:', err);
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】跳转到报告页面（兼容旧版）
   * @param {string} executionId - 执行 ID
   * @param {object} options - 选项
   */
  navigateToReportPage: function(executionId, options = {}) {
    const { hasResults = true, showExecutionLog = false, showConfigReview = false } = options;
    
    // 获取品牌名称（从 options 或 storage）
    const brandName = options.brandName || wx.getStorageSync('latestBrandName') || '品牌诊断';
    
    wx.navigateTo({
      url: `/pages/history-detail/history-detail?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`,
      fail: (err) => {
        console.error('❌ 跳转到报告页面失败:', err);
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 跳转到统计分析
   * @param {object} options - 选项
   */
  navigateToAnalytics: function(options = {}) {
    const { tabId = '' } = options;
    
    if (tabId) {
      wx.switchTab({
        url: `/pages/analytics/analytics?tabId=${tabId}`,
        fail: (err) => {
          console.error('❌ 跳转到统计分析失败:', err);
        }
      });
    } else {
      wx.switchTab({
        url: '/pages/analytics/analytics',
        fail: (err) => {
          console.error('❌ 跳转到统计分析失败:', err);
        }
      });
    }
  },

  /**
   * 跳转到个人中心
   */
  navigateToProfile: function() {
    wx.switchTab({
      url: '/pages/user-profile/user-profile',
      fail: (err) => {
        console.error('❌ 跳转到个人中心失败:', err);
      }
    });
  },

  /**
   * 跳转到收藏列表
   */
  navigateToFavorites: function() {
    wx.navigateTo({
      url: '/pages/user-profile/subpages/favorites/favorites',
      fail: (err) => {
        console.error('❌ 跳转到收藏列表失败:', err);
      }
    });
  },

  /**
   * 跳转到配置管理
   */
  navigateToConfig: function() {
    wx.navigateTo({
      url: '/pages/config-manager/config-manager',
      fail: (err) => {
        console.error('❌ 跳转到配置管理失败:', err);
      }
    });
  },

  /**
   * 跳转到使用指南
   */
  navigateToGuide: function() {
    wx.navigateTo({
      url: '/pages/user-guide/user-guide',
      fail: (err) => {
        console.error('❌ 跳转到使用指南失败:', err);
      }
    });
  },

  /**
   * 跳转到 AI 搜索首页
   */
  navigateToHome: function() {
    wx.switchTab({
      url: '/pages/index/index',
      fail: (err) => {
        console.error('❌ 跳转回首页失败:', err);
      }
    });
  },

  /**
   * 返回上一页
   * @param {number} delta - 返回的页面数
   */
  navigateBack: function(delta = 1) {
    wx.navigateBack({
      delta: delta,
      fail: (err) => {
        console.error('❌ 返回失败:', err);
      }
    });
  },

  /**
   * 重定向到页面（关闭当前页）
   * @param {string} url - 目标 URL
   */
  redirectTo: function(url) {
    wx.redirectTo({
      url: url,
      fail: (err) => {
        console.error('❌ 重定向失败:', err);
      }
    });
  },

  /**
   * 关闭所有页面，打开到某个页面
   * @param {string} url - 目标 URL
   */
  reLaunch: function(url) {
    wx.reLaunch({
      url: url,
      fail: (err) => {
        console.error('❌ reLaunch 失败:', err);
      }
    });
  },

  /**
   * 跳转到历史记录详情
   * @param {string} executionId - 执行 ID
   */
  navigateToHistoryDetail: function(executionId) {
    wx.navigateTo({
      url: `/pages/history-detail/history-detail?executionId=${executionId}`,
      fail: (err) => {
        console.error('❌ 跳转到历史详情失败:', err);
      }
    });
  },

  /**
   * 跳转到保存的结果页（兼容旧版）
   */
  navigateToSavedResults: function() {
    wx.navigateTo({
      url: '/pages/saved-results/saved-results',
      fail: (err) => {
        console.error('❌ 跳转到保存结果失败:', err);
      }
    });
  }
};

module.exports = navigationService;
