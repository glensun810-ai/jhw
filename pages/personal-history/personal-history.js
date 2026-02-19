// pages/personal-history/personal-history.js
const { getSavedResults, deleteResult } = require('../../utils/saved-results-sync');

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
    this.loadPersonalHistory();
  },

  onShow: function() {
    this.loadPersonalHistory();
  },

  // 加载个人历史记录
  loadPersonalHistory: function() {
    const that = this;
    that.setData({ isLoading: true });

    // 使用云端同步工具获取保存的结果（支持登录用户云端同步）
    getSavedResults()
      .then(searchResults => {
        that.setData({
          filteredHistory: searchResults,
          isLoading: false
        });
      })
      .catch(error => {
        console.error('加载个人历史记录失败', error);
        that.setData({ isLoading: false });
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        });
      });
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
    const that = this;
    const history = this.data.filteredHistory;

    // 搜索关键词过滤
    let filtered = history;
    if (this.data.searchKeyword) {
      const keyword = this.data.searchKeyword.toLowerCase();
      filtered = filtered.filter(item =>
        (item.brandName && item.brandName.toLowerCase().includes(keyword)) ||
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

      filtered = filtered.filter(item => item.timestamp >= timeThreshold);
    }

    // 分数范围过滤
    filtered = filtered.filter(item => {
      const score = item.results?.overallScore || 0;
      return score >= this.data.scoreRange[0] && score <= this.data.scoreRange[1];
    });

    // 分类过滤
    if (this.data.selectedCategory !== 'all') {
      filtered = filtered.filter(item => item.category === this.data.selectedCategory);
    }

    this.setData({
      filteredHistory: filtered
    });
  },

  // 显示时间筛选弹窗
  showTimeFilter: function() {
    const that = this;
    wx.showActionSheet({
      itemList: this.data.timeOptions.map(opt => opt.label),
      success: (res) => {
        const option = that.data.timeOptions[res.tapIndex];
        that.setData({
          timeRange: option.value,
          timeRangeText: option.label
        });
        that.applyFilters();
      }
    });
  },

  // 显示分数筛选弹窗
  showScoreFilter: function() {
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    });
  },

  // 显示分类筛选弹窗
  showCategoryFilter: function() {
    const that = this;
    wx.showActionSheet({
      itemList: that.data.categories,
      success: (res) => {
        const category = that.data.categories[res.tapIndex];
        that.setData({
          selectedCategory: category,
          categoryText: category === 'all' ? '全部分类' : category
        });
        that.applyFilters();
      }
    });
  },

  // 查看详情
  viewDetail: function(e) {
    const id = e.currentTarget.dataset.id;
    // 跳转到历史记录详情页面
    wx.navigateTo({
      url: `/pages/history-detail/history-detail?id=${id}`
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
    const that = this;

    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条历史记录吗？',
      success: (res) => {
        if (res.confirm) {
          that.setData({ isLoading: true });
          
          deleteResult(id)
            .then(success => {
              if (success) {
                that.loadPersonalHistory();
                wx.showToast({
                  title: '删除成功',
                  icon: 'success'
                });
              } else {
                that.setData({ isLoading: false });
                wx.showToast({
                  title: '删除失败',
                  icon: 'none'
                });
              }
            })
            .catch(error => {
              console.error('删除历史记录失败', error);
              that.setData({ isLoading: false });
              wx.showToast({
                title: '删除失败',
                icon: 'none'
              });
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
