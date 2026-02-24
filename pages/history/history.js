/**
 * 历史记录页面 - 存储架构优化版本
 * 
 * 优化：
 * 1. 使用新 API 获取历史报告
 * 2. 支持分页加载
 * 3. 支持按品牌筛选
 * 4. 支持按时间排序
 * 
 * 作者：前端工程师
 * 日期：2026-03-01
 * 版本：1.0
 */

const { getDiagnosisHistory } = require('../../services/diagnosisApi');

Page({
  data: {
    // 列表数据
    historyList: [],
    
    // 分页
    currentPage: 1,
    totalPages: 1,
    hasMore: false,
    loading: false,
    
    // 筛选
    filterBrand: '',
    filterStatus: 'all', // all, completed, processing, failed
    
    // 排序
    sortBy: 'created_at', // created_at, brand_name
    
    // 空状态
    isEmpty: false
  },

  onLoad: function(options) {
    console.log('📋 历史记录页面加载');
    
    // 初始化
    this.loadHistory();
  },

  onShow: function() {
    // 页面显示时刷新数据
    this.refreshHistory();
  },

  onPullDownRefresh: function() {
    // 下拉刷新
    this.refreshHistory().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom: function() {
    // 上拉加载更多
    if (this.data.hasMore && !this.data.loading) {
      this.loadMore();
    }
  },

  /**
   * 加载历史记录
   */
  async loadHistory() {
    if (this.data.loading) return;

    this.setData({ loading: true });

    try {
      const { currentPage, filterBrand, filterStatus, sortBy } = this.data;
      
      // 调用新 API
      const result = await getDiagnosisHistory({
        page: currentPage,
        limit: 20
      });

      const reports = result.reports || [];
      
      // 筛选
      let filteredReports = reports;
      if (filterBrand) {
        filteredReports = reports.filter(r => 
          r.brand_name.includes(filterBrand)
        );
      }
      if (filterStatus !== 'all') {
        filteredReports = reports.filter(r => 
          r.status === filterStatus
        );
      }

      // 排序
      filteredReports.sort((a, b) => {
        if (sortBy === 'created_at') {
          return new Date(b.created_at) - new Date(a.created_at);
        } else if (sortBy === 'brand_name') {
          return a.brand_name.localeCompare(b.brand_name);
        }
        return 0;
      });

      // 更新数据
      const historyList = currentPage === 1 
        ? filteredReports 
        : [...this.data.historyList, ...filteredReports];

      this.setData({
        historyList,
        totalPages: result.pagination?.total || 0,
        hasMore: result.pagination?.has_more || false,
        isEmpty: historyList.length === 0,
        loading: false
      });

      console.log(`✅ 加载历史记录成功：${historyList.length} 条`);

    } catch (error) {
      console.error('❌ 加载历史记录失败:', error);
      
      this.setData({
        loading: false,
        isEmpty: true
      });

      wx.showToast({
        title: '加载失败，请重试',
        icon: 'none'
      });
    }
  },

  /**
   * 刷新历史记录
   */
  async refreshHistory() {
    this.setData({ currentPage: 1, historyList: [] });
    return this.loadHistory();
  },

  /**
   * 加载更多
   */
  async loadMore() {
    this.setData({ 
      currentPage: this.data.currentPage + 1 
    });
    return this.loadHistory();
  },

  /**
   * 搜索品牌
   */
  onSearchBrand: function(e) {
    const value = e.detail.value.trim();
    this.setData({
      filterBrand: value,
      currentPage: 1,
      historyList: []
    });
    this.loadHistory();
  },

  /**
   * 筛选状态
   */
  onFilterStatus: function(e) {
    const status = e.detail.value;
    this.setData({
      filterStatus: status,
      currentPage: 1,
      historyList: []
    });
    this.loadHistory();
  },

  /**
   * 点击历史记录项
   */
  onReportTap: function(e) {
    const { executionId, brandName } = e.currentTarget.dataset;
    
    wx.navigateTo({
      url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`
    });
  },

  /**
   * 删除历史记录
   */
  onDeleteReport: function(e) {
    const { executionId, index } = e.currentTarget.dataset;
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条诊断记录吗？',
      success: (res) => {
        if (res.confirm) {
          // TODO: 调用删除 API
          const historyList = this.data.historyList;
          historyList.splice(index, 1);
          this.setData({ historyList });
          
          wx.showToast({
            title: '删除成功',
            icon: 'success'
          });
        }
      }
    });
  }
});
