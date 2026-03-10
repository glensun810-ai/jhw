/**
 * 我的收藏 - 子页面
 * 功能：查看和管理收藏的诊断报告
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

const navigationService = require('../../../../services/navigationService');

Page({
  data: {
    favorites: [],
    filteredFavorites: [],
    loading: false,
    isEmpty: false,
    searchKeyword: '',
    sortBy: 'time_desc', // time_desc, time_asc, score_desc
    showSortMenu: false
  },

  onLoad: function(options) {
    console.log('📑 我的收藏页面加载');
    this.loadFavorites();
  },

  onShow: function() {
    // 每次显示时重新加载
    this.loadFavorites();
  },

  onPullDownRefresh: function() {
    this.loadFavorites().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载收藏列表
   */
  async loadFavorites() {
    this.setData({ loading: true });
    
    try {
      // 从本地存储获取收藏
      const favorites = wx.getStorageSync('favorites') || [];
      
      // 处理收藏数据
      const processedFavorites = favorites.map(fav => ({
        ...fav,
        formattedTime: this.formatTime(fav.favoritedAt || fav.timestamp || Date.now()),
        scoreLevel: this.calculateScoreLevel(fav.overallScore || 0)
      }));
      
      this.setData({
        favorites: processedFavorites,
        filteredFavorites: processedFavorites,
        isEmpty: processedFavorites.length === 0,
        loading: false
      });
      
      console.log('✅ 加载收藏列表成功:', processedFavorites.length, '条');
    } catch (error) {
      console.error('❌ 加载收藏列表失败:', error);
      this.setData({ loading: false });
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  /**
   * 计算得分等级
   */
  calculateScoreLevel(score) {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    return 'poor';
  },

  /**
   * 格式化时间
   */
  formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;

    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
  },

  /**
   * 搜索关键词变化
   */
  onSearchChange: function(e) {
    const value = e.detail.value.trim();
    this.setData({ searchKeyword: value });
    this.applyFilters();
  },

  /**
   * 排序方式变化
   */
  onSortChange: function(e) {
    const value = e.currentTarget.dataset.value;
    this.setData({ 
      sortBy: value,
      showSortMenu: false
    });
    this.applyFilters();
  },

  /**
   * 切换排序菜单
   */
  toggleSortMenu: function() {
    this.setData({
      showSortMenu: !this.data.showSortMenu
    });
  },

  /**
   * 应用筛选和排序
   */
  applyFilters() {
    const { favorites, searchKeyword, sortBy } = this.data;
    
    let filtered = [...favorites];
    
    // 关键词搜索
    if (searchKeyword) {
      filtered = filtered.filter(item =>
        item.brandName.toLowerCase().includes(searchKeyword.toLowerCase())
      );
    }
    
    // 排序
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'time_desc':
          return (b.favoritedAt || b.timestamp || 0) - (a.favoritedAt || a.timestamp || 0);
        case 'time_asc':
          return (a.favoritedAt || a.timestamp || 0) - (b.favoritedAt || b.timestamp || 0);
        case 'score_desc':
          return (b.overallScore || 0) - (a.overallScore || 0);
        default:
          return 0;
      }
    });
    
    this.setData({
      filteredFavorites: filtered,
      isEmpty: filtered.length === 0
    });
  },

  /**
   * 查看收藏详情
   */
  onViewDetail: function(e) {
    const { executionId, brandName } = e.currentTarget.dataset;
    
    navigationService.navigateToReportDetail(executionId, brandName);
  },

  /**
   * 取消收藏
   */
  onRemoveFavorite: function(e) {
    const { executionId, index } = e.currentTarget.dataset;
    
    wx.showModal({
      title: '确认取消',
      content: '确定要取消收藏这条报告吗？',
      success: (res) => {
        if (res.confirm) {
          this.removeFavorite(executionId, index);
        }
      }
    });
  },

  /**
   * 移除收藏
   */
  removeFavorite: function(executionId, index) {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      const filtered = favorites.filter(f => f.executionId !== executionId);
      wx.setStorageSync('favorites', filtered);
      
      // 更新页面数据
      const { favorites: currentFavorites } = this.data;
      currentFavorites.splice(index, 1);
      
      this.setData({ favorites: currentFavorites });
      this.applyFilters();
      
      wx.showToast({
        title: '已取消收藏',
        icon: 'success'
      });
    } catch (error) {
      console.error('❌ 取消收藏失败:', error);
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      });
    }
  },

  /**
   * 返回首页
   */
  goHome: function() {
    navigationService.navigateToHome();
  },

  /**
   * 去诊断
   */
  goToDiagnosis: function() {
    navigationService.navigateToHome();
  }
});
