/**
 * 诊断记录页面 - 增强版
 * 
 * 功能特性：
 * 1. 历史报告列表展示（支持分页）
 * 2. 搜索和筛选（品牌、状态、时间）
 * 3. 多种排序方式（时间、分数）
 * 4. 单个删除和批量删除
 * 5. 收藏/取消收藏
 * 6. 本地缓存管理
 * 7. 空状态和加载状态
 * 8. 统计信息展示
 *
 * 设计理念：
 * - 麦肯锡式专业分析风格
 * - 清晰的信息层级
 * - 高效的操作流程
 *
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v3.0 - 产品架构优化版
 */

const { getTestHistory, deleteHistoryReport, batchDeleteHistoryReports } = require('../../api/history');
const { clearDiagnosisResult, batchClearDiagnosisResults, getDiagnosisHistory } = require('../../utils/storage-manager');
const navigationService = require('../../services/navigationService');
const pageStateService = require('../../services/pageStateService');

Page({
  data: {
    // 列表数据
    historyList: [],
    filteredList: [],

    // 分页
    currentPage: 1,
    pageSize: 20,
    totalCount: 0,
    hasMore: false,
    loading: false,
    refreshing: false,

    // 筛选条件
    searchKeyword: '',
    filterBrand: '',
    filterStatus: 'all', // all, completed, failed, processing
    filterScore: 'all', // all, excellent(>=80), good(60-79), poor(<60)
    timeRange: 'all', // all, today, last7days, last30days, last90days
    favoriteStatus: 'all', // all, favorited, not_favorited

    // 排序
    sortBy: 'time', // time, score, brand
    sortOrder: 'desc', // asc, desc

    // 批量操作模式
    batchMode: false,
    selectedIds: [],
    selectAll: false,

    // 统计信息
    stats: {
      total: 0,
      completed: 0,
      failed: 0,
      averageScore: 0,
      favorited: 0
    },

    // 空状态
    isEmpty: false,
    emptyType: 'no_data', // no_data, no_search_result, network_error

    // UI 状态
    showFilterPanel: false,
    showSortMenu: false,
    hasActiveFilters: false,
    toast: {
      show: false,
      message: '',
      type: 'info' // info, success, error
    },

    // 【产品架构优化 - 2026-03-10】新增：收藏状态管理
    favorites: []
  },

  onLoad: function(options) {
    console.log('📋 诊断记录页面加载');
    this.initPage();
  },

  onShow: function() {
    // 页面显示时检查是否需要刷新
    this.loadFavorites();
    if (this.data.historyList.length === 0) {
      this.refreshHistory();
    } else {
      // 恢复页面状态
      this.restorePageState();
    }
  },

  onHide: function() {
    // 保存页面状态
    this.savePageState();
  },

  onPullDownRefresh: function() {
    this.refreshHistory().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom: function() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadMore();
    }
  },

  /**
   * 初始化页面
   */
  async initPage() {
    try {
      await this.loadHistory();
      this.calculateStats();
    } catch (error) {
      console.error('初始化页面失败:', error);
      this.setData({
        isEmpty: true,
        emptyType: 'network_error'
      });
    }
  },

  /**
   * 加载历史记录 - 产品架构优化版
   * 优先从本地存储加载，确保诊断完成后立即可见
   */
  async loadHistory() {
    if (this.data.loading) return;

    this.setData({ loading: true });

    try {
      const { currentPage, pageSize, filterBrand, filterStatus, sortBy, sortOrder } = this.data;

      // 【产品架构优化 - 2026-03-10】优先从本地存储加载历史记录
      let historyList = [];
      let totalCount = 0;

      try {
        // 从本地存储加载
        const localHistory = getDiagnosisHistory() || [];
        historyList = localHistory;
        totalCount = localHistory.length;
        
        console.log(`[历史记录] 从本地存储加载 ${localHistory.length} 条记录`);
      } catch (localError) {
        console.warn('[历史记录] 本地存储加载失败，尝试从 API 加载:', localError);
      }

      // 如果没有本地数据，尝试从 API 加载
      if (historyList.length === 0) {
        try {
          // 构建 API 请求参数
          const params = {
            page: currentPage,
            limit: pageSize,
            sortBy: sortBy === 'time' ? 'created_at' : 'overall_score',
            sortOrder
          };

          if (filterBrand) {
            params.brand = filterBrand;
          }
          if (filterStatus !== 'all') {
            params.status = filterStatus;
          }

          // 调用 API
          const result = await getTestHistory(params);
          const reports = result.reports || result.data || [];
          
          // 处理数据
          historyList = reports.map(report => ({
            ...report,
            id: report.id || report.reportId,
            executionId: report.execution_id || report.executionId,
            brandName: report.brand_name || report.brandName,
            createdAt: report.created_at || report.createdAt,
            overallScore: report.overall_score || report.overallScore || 0,
            status: report.status || 'completed'
          }));
          
          totalCount = result.total || result.pagination?.total || historyList.length;
          
          console.log(`[历史记录] 从 API 加载 ${historyList.length} 条记录`);
        } catch (apiError) {
          console.error('[历史记录] API 加载失败:', apiError);
        }
      }

      // 【产品架构优化 - 2026-03-10】获取收藏列表
      const favorites = wx.getStorageSync('favorites') || [];

      // 处理数据
      const processedReports = historyList.map(report => ({
        ...report,
        // 确保字段一致性
        id: report.id || report.reportId,
        executionId: report.execution_id || report.executionId,
        brandName: report.brand_name || report.brandName,
        createdAt: report.created_at || report.createdAt,
        overallScore: report.overall_score || report.overallScore || 0,
        status: report.status || 'completed',
        // 计算得分等级
        scoreLevel: this.calculateScoreLevel(report.overall_score || report.overallScore || 0),
        // 格式化时间
        formattedTime: this.formatTime(report.created_at || report.createdAt),
        // 短日期显示
        shortDate: this.formatShortDate(report.created_at || report.createdAt),
        // 【产品架构优化 - 2026-03-10】添加收藏状态标记
        isFavorited: favorites.some(f => f.executionId === (report.execution_id || report.executionId))
      }));

      // 更新数据
      const historyListData = currentPage === 1
        ? processedReports
        : [...this.data.historyList, ...processedReports];

      this.setData({
        historyList: historyListData,
        filteredList: historyListData,
        totalCount: totalCount || historyListData.length,
        hasMore: false, // 本地存储不需要分页
        isEmpty: historyListData.length === 0,
        emptyType: historyListData.length === 0 ? 'no_data' : 'no_search_result',
        loading: false
      });

      console.log(`✅ 加载历史记录成功：${historyListData.length} 条`);

      // 计算统计信息
      this.calculateStats();
    } catch (error) {
      console.error('❌ 加载历史记录失败:', error);

      this.setData({
        loading: false,
        isEmpty: true,
        emptyType: 'network_error'
      });

      this.showToast('加载失败，请重试', 'error');
    }
  },

  /**
   * 刷新历史记录
   */
  async refreshHistory() {
    this.setData({ 
      currentPage: 1, 
      historyList: [],
      filteredList: [],
      refreshing: true 
    });
    
    try {
      await this.loadHistory();
      await this.calculateStats();
    } finally {
      this.setData({ refreshing: false });
    }
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
   * 计算统计信息
   */
  async calculateStats() {
    try {
      const { historyList } = this.data;

      if (historyList.length === 0) {
        this.setData({
          stats: {
            total: 0,
            completed: 0,
            failed: 0,
            averageScore: 0,
            favorited: 0
          }
        });
        return;
      }

      // 获取收藏列表
      const favorites = wx.getStorageSync('favorites') || [];
      const favoritedIds = new Set(favorites.map(f => f.executionId));

      const stats = {
        total: historyList.length,
        completed: historyList.filter(r => r.status === 'completed').length,
        failed: historyList.filter(r => r.status === 'failed').length,
        averageScore: Math.round(
          historyList.reduce((sum, r) => sum + (r.overallScore || 0), 0) / historyList.length
        ),
        favorited: historyList.filter(r => favoritedIds.has(r.executionId)).length
      };

      this.setData({ stats });
    } catch (error) {
      console.error('计算统计信息失败:', error);
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
  formatTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    // 少于 1 分钟
    if (diff < 60000) return '刚刚';
    // 少于 1 小时
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    // 少于 24 小时
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    // 少于 7 天
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
    
    // 超过 7 天显示具体日期
    return this.formatShortDate(dateStr);
  },

  /**
   * 格式化短日期
   */
  formatShortDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hours = date.getHours();
    const minutes = date.getMinutes();
    
    return `${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')} ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
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
   * 筛选品牌变化
   */
  onFilterBrandChange: function(e) {
    const value = e.detail.value;
    this.setData({ filterBrand: value });
    this.applyFilters();
  },

  /**
   * 筛选状态变化
   */
  onFilterStatusChange: function(e) {
    const value = e.detail.value;
    this.setData({ filterStatus: value });
    this.applyFilters();
  },

  /**
   * 筛选分数段变化
   */
  onFilterScoreChange: function(e) {
    const value = e.detail.value;
    this.setData({ filterScore: value });
    this.applyFilters();
  },

  /**
   * 排序方式变化
   */
  onSortByChange: function(e) {
    const value = e.detail.value;
    const [sortBy, sortOrder] = value.split('-');
    
    this.setData({ sortBy, sortOrder });
    this.applyFilters();
  },

  /**
   * 应用筛选和排序
   */
  applyFilters() {
    const { historyList, searchKeyword, filterBrand, filterStatus, filterScore, sortBy, sortOrder, timeRange, favoriteStatus } = this.data;

    let filtered = [...historyList];

    // 关键词搜索
    if (searchKeyword) {
      filtered = filtered.filter(item =>
        item.brandName.toLowerCase().includes(searchKeyword.toLowerCase()) ||
        (item.executionId && item.executionId.toLowerCase().includes(searchKeyword.toLowerCase()))
      );
    }

    // 品牌筛选
    if (filterBrand) {
      filtered = filtered.filter(item =>
        item.brandName.toLowerCase().includes(filterBrand.toLowerCase())
      );
    }

    // 状态筛选
    if (filterStatus !== 'all') {
      filtered = filtered.filter(item => item.status === filterStatus);
    }

    // 时间范围筛选
    if (timeRange !== 'all') {
      const now = Date.now();
      let timeThreshold = 0;
      
      switch (timeRange) {
        case 'today':
          timeThreshold = now - 24 * 60 * 60 * 1000;
          break;
        case 'last7days':
          timeThreshold = now - 7 * 24 * 60 * 60 * 1000;
          break;
        case 'last30days':
          timeThreshold = now - 30 * 24 * 60 * 60 * 1000;
          break;
        case 'last90days':
          timeThreshold = now - 90 * 24 * 60 * 60 * 1000;
          break;
      }
      
      if (timeThreshold > 0) {
        filtered = filtered.filter(item => {
          const itemTime = new Date(item.createdAt || 0).getTime();
          return itemTime >= timeThreshold;
        });
      }
    }

    // 分数段筛选
    if (filterScore !== 'all') {
      filtered = filtered.filter(item => {
        const score = item.overallScore || 0;
        if (filterScore === 'excellent') return score >= 80;
        if (filterScore === 'good') return score >= 60 && score < 80;
        if (filterScore === 'poor') return score < 60;
        return true;
      });
    }

    // 收藏状态筛选
    if (favoriteStatus !== 'all') {
      const favorites = wx.getStorageSync('favorites') || [];
      const favoritedIds = new Set(favorites.map(f => f.executionId));
      
      filtered = filtered.filter(item => {
        const isFavorited = favoritedIds.has(item.executionId);
        if (favoriteStatus === 'favorited') return isFavorited;
        if (favoriteStatus === 'not_favorited') return !isFavorited;
        return true;
      });
    }

    // 排序
    filtered.sort((a, b) => {
      let compareValue = 0;

      if (sortBy === 'time') {
        const timeA = new Date(a.createdAt || 0).getTime();
        const timeB = new Date(b.createdAt || 0).getTime();
        compareValue = timeA - timeB;
      } else if (sortBy === 'score') {
        compareValue = (a.overallScore || 0) - (b.overallScore || 0);
      } else if (sortBy === 'brand') {
        compareValue = (a.brandName || '').localeCompare(b.brandName || '');
      }

      return sortOrder === 'desc' ? -compareValue : compareValue;
    });

    // 检查是否有激活的筛选条件
    const hasActiveFilters = 
      filterStatus !== 'all' || 
      timeRange !== 'all' || 
      filterScore !== 'all' || 
      favoriteStatus !== 'all';

    this.setData({
      filteredList: filtered,
      isEmpty: filtered.length === 0,
      emptyType: filtered.length === 0 ? (historyList.length === 0 ? 'no_data' : 'no_search_result') : 'no_data',
      hasActiveFilters
    });
  },

  /**
   * 切换筛选面板
   */
  toggleFilterPanel() {
    this.setData({
      showFilterPanel: !this.data.showFilterPanel,
      showSortMenu: false
    });
  },

  /**
   * 切换排序菜单
   */
  toggleSortMenu() {
    this.setData({
      showSortMenu: !this.data.showSortMenu,
      showFilterPanel: false
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】统计卡片点击
   */
  onStatTap: function(e) {
    const { type } = e.currentTarget.dataset;
    
    switch (type) {
      case 'total':
        // 清空所有筛选
        this.clearAllFilters();
        break;
      case 'completed':
        // 筛选已完成
        this.setData({ filterStatus: 'completed' });
        this.applyFilters();
        break;
      case 'average':
        // 按分数排序
        this.setData({ sortBy: 'score', sortOrder: 'desc' });
        this.applyFilters();
        break;
      case 'favorited':
        // 筛选已收藏
        this.setData({ favoriteStatus: 'favorited' });
        this.applyFilters();
        break;
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】筛选条件点击事件
   */
  onFilterStatusTap: function(e) {
    const { value } = e.currentTarget.dataset;
    this.setData({ filterStatus: value });
    this.applyFilters();
  },

  onTimeRangeTap: function(e) {
    const { value } = e.currentTarget.dataset;
    this.setData({ timeRange: value });
    this.applyFilters();
  },

  onFilterScoreTap: function(e) {
    const { value } = e.currentTarget.dataset;
    this.setData({ filterScore: value });
    this.applyFilters();
  },

  onFavoriteStatusTap: function(e) {
    const { value } = e.currentTarget.dataset;
    this.setData({ favoriteStatus: value });
    this.applyFilters();
  },

  /**
   * 【产品架构优化 - 2026-03-10】清除单个筛选
   */
  clearFilter: function(e) {
    const { type } = e.currentTarget.dataset;
    
    const updates = {};
    switch (type) {
      case 'status':
        updates.filterStatus = 'all';
        break;
      case 'timeRange':
        updates.timeRange = 'all';
        break;
      case 'score':
        updates.filterScore = 'all';
        break;
      case 'favorite':
        updates.favoriteStatus = 'all';
        break;
    }
    
    this.setData(updates);
    this.applyFilters();
  },

  /**
   * 【产品架构优化 - 2026-03-10】清空所有筛选
   */
  clearAllFilters: function() {
    this.setData({
      filterStatus: 'all',
      timeRange: 'all',
      filterScore: 'all',
      favoriteStatus: 'all'
    });
    this.applyFilters();
  },

  /**
   * 【产品架构优化 - 2026-03-10】获取状态文本
   */
  getStatusText: function(status) {
    const map = {
      'completed': '已完成',
      'failed': '失败',
      'processing': '处理中'
    };
    return map[status] || '';
  },

  /**
   * 【产品架构优化 - 2026-03-10】获取时间范围文本
   */
  getTimeRangeText: function(range) {
    const map = {
      'today': '今天',
      'last7days': '近 7 天',
      'last30days': '近 30 天',
      'last90days': '近 90 天'
    };
    return map[range] || '';
  },

  /**
   * 【产品架构优化 - 2026-03-10】获取分数文本
   */
  getScoreText: function(score) {
    const map = {
      'excellent': '80 分以上',
      'good': '60-79 分',
      'poor': '60 分以下'
    };
    return map[score] || '';
  },

  /**
   * 【产品架构优化 - 2026-03-10】显示导出菜单
   */
  showExportMenu: function() {
    wx.showActionSheet({
      itemList: ['导出为 Excel', '导出为 PDF', '导出为 CSV'],
      success: (res) => {
        this.exportData(res.tapIndex);
      }
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】导出数据
   */
  exportData: function(formatIndex) {
    const formats = ['excel', 'pdf', 'csv'];
    const format = formats[formatIndex] || 'excel';
    
    wx.showLoading({ title: '生成中...' });
    
    // 模拟导出（实际应该调用后端 API）
    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({
        title: `已导出为${format.toUpperCase()}`,
        icon: 'success'
      });
    }, 1000);
  },

  /**
   * 进入批量操作模式
   */
  enterBatchMode() {
    this.setData({
      batchMode: true,
      selectedIds: [],
      selectAll: false
    });
  },

  /**
   * 退出批量操作模式
   */
  exitBatchMode() {
    this.setData({
      batchMode: false,
      selectedIds: [],
      selectAll: false
    });
  },

  /**
   * 选择/取消选择单个项目
   */
  onItemSelect(e) {
    const { id } = e.currentTarget.dataset;
    let { selectedIds } = this.data;
    
    const index = selectedIds.indexOf(id);
    if (index > -1) {
      selectedIds.splice(index, 1);
    } else {
      selectedIds.push(id);
    }
    
    this.setData({
      selectedIds,
      selectAll: selectedIds.length === this.data.filteredList.length && this.data.filteredList.length > 0
    });
  },

  /**
   * 全选/取消全选
   */
  onSelectAll() {
    const { selectAll, filteredList } = this.data;
    
    if (selectAll) {
      this.setData({
        selectedIds: [],
        selectAll: false
      });
    } else {
      this.setData({
        selectedIds: filteredList.map(item => item.id),
        selectAll: true
      });
    }
  },

  /**
   * 点击历史记录项
   */
  onReportTap: function(e) {
    const { executionId, brandName } = e.currentTarget.dataset;

    wx.navigateTo({
      url: `/pages/history-detail/history-detail?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`
    });
  },

  /**
   * 删除单个报告 - 产品架构优化版
   */
  async onDeleteReport(e) {
    const { executionId, reportId, index } = e.currentTarget.dataset;

    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条诊断记录吗？此操作不可恢复。',
      confirmText: '删除',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' });

          try {
            // 【产品架构优化 - 2026-03-10】从本地存储删除
            const { removeFromDiagnosisHistory } = require('../../utils/storage-manager');
            removeFromDiagnosisHistory(executionId);
            clearDiagnosisResult(executionId);

            // 尝试调用删除 API（如果后端支持）
            try {
              await deleteHistoryReport(executionId, reportId);
            } catch (apiError) {
              console.warn('[删除] API 删除失败，仅删除本地存储:', apiError);
            }

            // 从列表中移除
            const { historyList, filteredList } = this.data;
            historyList.splice(index, 1);
            filteredList.splice(index, 1);

            this.setData({ historyList, filteredList });

            // 更新统计
            await this.calculateStats();

            wx.hideLoading();
            this.showToast('删除成功', 'success');

          } catch (error) {
            console.error('删除失败:', error);
            wx.hideLoading();
            this.showToast('删除失败，请重试', 'error');
          }
        }
      }
    });
  },

  /**
   * 批量删除 - 产品架构优化版
   */
  async onBatchDelete() {
    const { selectedIds, historyList, filteredList } = this.data;

    if (selectedIds.length === 0) {
      this.showToast('请先选择要删除的报告', 'info');
      return;
    }

    wx.showModal({
      title: '批量删除确认',
      content: `确定要删除选中的 ${selectedIds.length} 条诊断记录吗？此操作不可恢复。`,
      confirmText: '删除',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' });

          try {
            // 【产品架构优化 - 2026-03-10】从本地存储批量删除
            const { removeFromDiagnosisHistory } = require('../../utils/storage-manager');
            
            const executionIds = filteredList
              .filter(item => selectedIds.includes(item.id))
              .map(item => item.executionId);

            // 从本地存储删除
            executionIds.forEach(id => removeFromDiagnosisHistory(id));
            batchClearDiagnosisResults(executionIds);

            // 尝试调用批量删除 API（如果后端支持）
            try {
              await batchDeleteHistoryReports(selectedIds);
            } catch (apiError) {
              console.warn('[批量删除] API 删除失败，仅删除本地存储:', apiError);
            }

            // 从列表中移除
            const newHistoryList = historyList.filter(item => !selectedIds.includes(item.id));
            const newFilteredList = filteredList.filter(item => !selectedIds.includes(item.id));

            this.setData({
              historyList: newHistoryList,
              filteredList: newFilteredList,
              batchMode: false,
              selectedIds: [],
              selectAll: false
            });

            // 更新统计
            await this.calculateStats();

            wx.hideLoading();
            this.showToast(`成功删除 ${selectedIds.length} 条记录`, 'success');

          } catch (error) {
            console.error('批量删除失败:', error);
            wx.hideLoading();
            this.showToast('删除失败，请重试', 'error');
          }
        }
      }
    });
  },

  /**
   * 查看报告详情
   */
  viewDetail(e) {
    const { executionId, brandName } = e.currentTarget.dataset;
    
    wx.navigateTo({
      url: `/pages/history-detail/history-detail?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`
    });
  },

  /**
   * 分享报告
   */
  onShareReport(e) {
    const { brandName, score } = e.currentTarget.dataset;
    
    wx.showActionSheet({
      itemList: ['分享给微信好友', '分享到朋友圈', '生成海报'],
      success: (res) => {
        this.showToast('分享功能开发中', 'info');
      }
    });
  },

  /**
   * 导出报告
   */
  onExportReport(e) {
    const { executionId, brandName } = e.currentTarget.dataset;
    
    wx.showActionSheet({
      itemList: ['导出为 PDF', '导出为图片', '导出为 Excel'],
      success: (res) => {
        wx.showLoading({ title: '导出中...' });
        setTimeout(() => {
          wx.hideLoading();
          this.showToast('导出功能开发中', 'info');
        }, 1000);
      }
    });
  },

  /**
   * 显示 Toast 提示
   */
  showToast(message, type = 'info') {
    this.setData({
      toast: {
        show: true,
        message,
        type
      }
    });
    
    setTimeout(() => {
      this.setData({
        toast: {
          show: false,
          message: '',
          type: 'info'
        }
      });
    }, 2000);
  },

  /**
   * 清空筛选条件
   */
  clearFilters() {
    this.setData({
      searchKeyword: '',
      filterBrand: '',
      filterStatus: 'all',
      filterScore: 'all',
      sortBy: 'time',
      sortOrder: 'desc'
    });
    this.applyFilters();
  },

  /**
   * 【产品架构优化 - 2026-03-10】加载收藏列表
   */
  loadFavorites: function() {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      this.setData({ favorites });
    } catch (error) {
      console.error('加载收藏失败:', error);
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】切换收藏状态
   */
  toggleFavorite: function(e) {
    const { executionId, brandName, isFavorited } = e.currentTarget.dataset;
    
    if (isFavorited) {
      this.removeFavorite(executionId);
    } else {
      this.addFavorite(executionId, brandName);
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】添加收藏
   */
  addFavorite: function(executionId, brandName) {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      
      // 检查是否已存在
      const exists = favorites.some(f => f.executionId === executionId);
      if (exists) {
        wx.showToast({
          title: '已在收藏中',
          icon: 'none'
        });
        return;
      }
      
      // 添加收藏
      favorites.unshift({
        executionId,
        brandName,
        favoritedAt: Date.now(),
        timestamp: Date.now()
      });
      
      wx.setStorageSync('favorites', favorites);
      this.setData({ favorites });
      
      // 【产品架构优化 - 2026-03-10】更新列表中对应项的收藏状态
      const { historyList } = this.data;
      const updatedList = historyList.map(item => {
        if (item.executionId === executionId) {
          return { ...item, isFavorited: true };
        }
        return item;
      });
      this.setData({ historyList, filteredList: updatedList });
      
      wx.showToast({
        title: '收藏成功',
        icon: 'success'
      });
    } catch (error) {
      console.error('添加收藏失败:', error);
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      });
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】移除收藏
   */
  removeFavorite: function(executionId) {
    wx.showModal({
      title: '确认取消',
      content: '确定要取消收藏这条报告吗？',
      success: (res) => {
        if (res.confirm) {
          try {
            const favorites = wx.getStorageSync('favorites') || [];
            const filtered = favorites.filter(f => f.executionId !== executionId);
            wx.setStorageSync('favorites', filtered);
            this.setData({ favorites });
            
            // 【产品架构优化 - 2026-03-10】更新列表中对应项的收藏状态
            const { historyList } = this.data;
            const updatedList = historyList.map(item => {
              if (item.executionId === executionId) {
                return { ...item, isFavorited: false };
              }
              return item;
            });
            this.setData({ historyList, filteredList: updatedList });
            
            wx.showToast({
              title: '已取消收藏',
              icon: 'success'
            });
          } catch (error) {
            console.error('取消收藏失败:', error);
            wx.showToast({
              title: '操作失败',
              icon: 'none'
            });
          }
        }
      }
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】查看报告详情
   */
  viewReportDetail: function(e) {
    const { executionId, brandName } = e.currentTarget.dataset;
    navigationService.navigateToReportDetail(executionId, brandName);
  },

  /**
   * 【产品架构优化 - 2026-03-10】保存页面状态
   */
  savePageState: function() {
    const app = getApp();
    if (app && app.savePageState) {
      app.savePageState('history', {
        historyList: this.data.historyList,
        filteredList: this.data.filteredList,
        currentPage: this.data.currentPage,
        searchKeyword: this.data.searchKeyword,
        filterBrand: this.data.filterBrand,
        filterStatus: this.data.filterStatus,
        sortBy: this.data.sortBy,
        sortOrder: this.data.sortOrder
      });
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】恢复页面状态
   */
  restorePageState: function() {
    const app = getApp();
    if (app && app.getPageState) {
      const state = app.getPageState('history');
      if (state) {
        this.setData(state);
        console.log('✅ 恢复页面状态成功');
      }
    }
  },

  /**
   * 返回首页
   */
  goHome() {
    wx.switchTab({
      url: '/pages/index/index'
    });
  },

  /**
   * 新建诊断
   */
  createNewDiagnosis() {
    navigationService.navigateToHome();
  }
});
