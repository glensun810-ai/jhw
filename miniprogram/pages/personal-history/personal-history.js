const { checkLoginStatus, hasPermission } = require('../../utils/auth.js');
const { getSearchResults, removeSearchResult, updateSearchResult } = require('../../utils/local-storage.js');

Page({
  data: {
    searchKeyword: '',
    filteredHistory: [],
    isLoading: false,
    
    // 筛选相关
    timeRange: 'all',
    timeRangeText: '全部时间',
    scoreRange: [0, 100],
    scoreRangeText: '全部分数',
    selectedCategory: 'all',
    categoryText: '全部分类',
    
    // 筛选选项
    timeOptions: [
      { label: '全部时间', value: 'all' },
      { label: '今天', value: 'today' },
      { label: '本周', value: 'week' },
      { label: '本月', value: 'month' },
      { label: '三个月内', value: 'three_months' }
    ],
    categories: ['all', '日常监测', '竞品分析', '季度报告', '年度总结']
  },

  onLoad: function(options) {
    if (!checkLoginStatus()) {
      wx.showModal({
        title: '需要登录',
        content: '此功能需要登录后才能使用',
        confirmText: '去登录',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.redirectTo({
              url: '/pages/login/login'
            });
          } else {
            wx.navigateBack();
          }
        }
      });
      return;
    }
    
    if (!hasPermission('history')) {
      wx.showModal({
        title: '权限不足',
        content: '您没有访问此功能的权限',
        showCancel: false,
        confirmText: '确定',
        success: () => {
          wx.navigateBack();
        }
      });
      return;
    }
    
    this.loadPersonalHistory();
  },

  onShow: function() {
    this.loadPersonalHistory();
  },

  // 加载个人历史记录
  loadPersonalHistory: function() {
    try {
      const searchResults = getSearchResults();
      this.setData({
        filteredHistory: searchResults
      });
    } catch (e) {
      console.error('加载个人历史记录失败', e);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  // 搜索输入
  onSearchInput: function(e) {
    this.setData({
      searchKeyword: e.detail.value
    });
  },

  // 搜索
  onSearch: function() {
    this.applyFilters();
  },

  // 应用筛选
  applyFilters: function() {
    let history = getSearchResults();
    
    // 搜索关键词过滤
    if (this.data.searchKeyword) {
      const keyword = this.data.searchKeyword.toLowerCase();
      history = history.filter(item => 
        item.brandName.toLowerCase().includes(keyword) ||
        (item.tags && item.tags.some(tag => tag.toLowerCase().includes(keyword))) ||
        (item.notes && item.notes.toLowerCase().includes(keyword))
      );
    }
    
    // 时间范围过滤
    if (this.data.timeRange !== 'all') {
      const now = Date.now();
      let timeThreshold = 0;

      switch (this.data.timeRange) {
        case 'today':
          timeThreshold = now - 24 * 60 * 60 * 1000;
          break;
        case 'week':
          timeThreshold = now - 7 * 24 * 60 * 60 * 1000;
          break;
        case 'month':
          timeThreshold = now - 30 * 24 * 60 * 60 * 1000;
          break;
        case 'three_months':
          timeThreshold = now - 3 * 30 * 24 * 60 * 60 * 1000;
          break;
      }

      history = history.filter(item => item.timestamp >= timeThreshold);
    }
    
    // 分数范围过滤
    history = history.filter(item => 
      item.results.overallScore >= this.data.scoreRange[0] && 
      item.results.overallScore <= this.data.scoreRange[1]
    );
    
    // 分类过滤
    if (this.data.selectedCategory !== 'all') {
      history = history.filter(item => item.category === this.data.selectedCategory);
    }
    
    this.setData({
      filteredHistory: history
    });
  },

  // 显示时间筛选弹窗
  showTimeFilter: function() {
    // 这期实现时间筛选弹窗
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    });
  },

  // 显示分数筛选弹窗
  showScoreFilter: function() {
    // 这期实现分数筛选弹窗
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    });
  },

  // 显示分类筛选弹窗
  showCategoryFilter: function() {
    // 这期实现分类筛选弹窗
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    });
  },

  // 查看详情
  viewDetail: function(e) {
    const id = e.currentTarget.dataset.id;
    // 这期实现查看详情功能
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    });
  },

  // 编辑结果
  editResult: function(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/edit-saved-result/edit-saved-result?id=${id}`
    });
  },

  // 删除结果
  deleteResult: function(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条历史记录吗？',
      success: (res) => {
        if (res.confirm) {
          removeSearchResult(id);
          this.loadPersonalHistory(); // 重新加载数据
          
          wx.showToast({
            title: '删除成功',
            icon: 'success'
          });
        }
      }
    });
  },

  // 格式化日期
  formatDate: function(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
})