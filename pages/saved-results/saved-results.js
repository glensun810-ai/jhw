Page({
  data: {
    savedResults: [],
    filteredResults: [],
    searchKeyword: '',
    timeRange: 'all',
    timeRangeText: '全部时间',
    categoryFilter: 'all',
    categoryFilterText: '全部分类',
    sortBy: 'date_desc',
    sortByText: '按时间倒序',
    showTimeFilterModal: false,
    showCategoryFilterModal: false,
    showSortByModal: false,
    allCategories: [],
    timeOptions: [
      { label: '全部时间', value: 'all' },
      { label: '今天', value: 'today' },
      { label: '本周', value: 'week' },
      { label: '本月', value: 'month' },
      { label: '三个月内', value: 'three_months' },
      { label: '半年内', value: 'half_year' }
    ],
    sortOptions: [
      { label: '按时间倒序', value: 'date_desc' },
      { label: '按时间正序', value: 'date_asc' },
      { label: '按品牌名称', value: 'brand_name' },
      { label: '按综合分数', value: 'overall_score' }
    ]
  },

  onLoad: function() {
    this.loadSavedResults();
  },

  onShow: function() {
    this.loadSavedResults();
  },

  loadSavedResults: function() {
    try {
      const savedResults = wx.getStorageSync('savedSearchResults') || [];
      this.setData({
        savedResults: savedResults,
        filteredResults: savedResults
      });
      
      // 提取所有分类
      const categories = [...new Set(savedResults.map(item => item.category).filter(cat => cat))];
      this.setData({
        allCategories: ['全部分类', ...categories]
      });
      
      this.applyFilters();
    } catch (e) {
      console.error('加载保存的搜索结果失败', e);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  onSearchInput: function(e) {
    this.setData({
      searchKeyword: e.detail.value
    });
  },

  onSearch: function() {
    this.applyFilters();
  },

  applyFilters: function() {
    let results = this.data.savedResults;

    // 搜索关键词过滤
    if (this.data.searchKeyword) {
      const keyword = this.data.searchKeyword.toLowerCase();
      results = results.filter(item => 
        item.brandName.toLowerCase().includes(keyword) ||
        item.tags.some(tag => tag.toLowerCase().includes(keyword)) ||
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
        case 'half_year':
          timeThreshold = now - 6 * 30 * 24 * 60 * 60 * 1000;
          break;
      }

      results = results.filter(item => item.timestamp >= timeThreshold);
    }

    // 分类过滤
    if (this.data.categoryFilter !== 'all') {
      results = results.filter(item => item.category === this.data.categoryFilter);
    }

    // 排序
    results.sort((a, b) => {
      switch (this.data.sortBy) {
        case 'date_desc':
          return b.timestamp - a.timestamp;
        case 'date_asc':
          return a.timestamp - b.timestamp;
        case 'brand_name':
          return a.brandName.localeCompare(b.brandName);
        case 'overall_score':
          return (b.results?.overallScore || 0) - (a.results?.overallScore || 0);
        default:
          return b.timestamp - a.timestamp;
      }
    });

    this.setData({
      filteredResults: results
    });
  },

  showTimeFilter: function() {
    this.setData({
      showTimeFilterModal: true
    });
  },

  hideTimeFilter: function() {
    this.setData({
      showTimeFilterModal: false
    });
  },

  selectTimeOption: function(e) {
    const value = e.currentTarget.dataset.value;
    const option = this.data.timeOptions.find(opt => opt.value === value);
    
    this.setData({
      timeRange: value,
      timeRangeText: option.label,
      showTimeFilterModal: false
    });
    
    this.applyFilters();
  },

  showCategoryFilter: function() {
    this.setData({
      showCategoryFilterModal: true
    });
  },

  hideCategoryFilter: function() {
    this.setData({
      showCategoryFilterModal: false
    });
  },

  selectCategory: function(e) {
    const category = e.currentTarget.dataset.category;
    
    this.setData({
      categoryFilter: category,
      categoryFilterText: category,
      showCategoryFilterModal: false
    });
    
    this.applyFilters();
  },

  sortByChange: function() {
    this.setData({
      showSortByModal: true
    });
  },

  hideSortByModal: function() {
    this.setData({
      showSortByModal: false
    });
  },

  selectSortOption: function(e) {
    const value = e.currentTarget.dataset.value;
    const option = this.data.sortOptions.find(opt => opt.value === value);
    
    this.setData({
      sortBy: value,
      sortByText: option.label,
      showSortByModal: false
    });
    
    this.applyFilters();
  },

  viewResult: function(e) {
    const id = e.currentTarget.dataset.id;
    const result = this.data.savedResults.find(item => item.id === id);
    
    if (result) {
      // 将结果传递到结果页面
      wx.navigateTo({
        url: `/pages/results/results?results=${encodeURIComponent(JSON.stringify(result.results))}&targetBrand=${encodeURIComponent(result.brandName)}&savedResultId=${id}`
      });
    }
  },

  editResult: function(e) {
    const id = e.currentTarget.dataset.id;
    const result = this.data.savedResults.find(item => item.id === id);
    
    if (result) {
      // 跳转到编辑页面
      wx.navigateTo({
        url: `/pages/edit-saved-result/edit-saved-result?id=${id}`
      });
    }
  },

  deleteResult: function(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条保存的搜索结果吗？',
      success: (res) => {
        if (res.confirm) {
          let savedResults = this.data.savedResults;
          savedResults = savedResults.filter(item => item.id !== id);
          
          try {
            wx.setStorageSync('savedSearchResults', savedResults);
            this.setData({
              savedResults: savedResults
            });
            this.applyFilters();
            
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            });
          } catch (e) {
            console.error('删除保存的搜索结果失败', e);
            wx.showToast({
              title: '删除失败',
              icon: 'none'
            });
          }
        }
      }
    });
  },

  formatDate: function(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
})