/**
 * 历史记录页面 - 专业版
 * 
 * 功能特性：
 * 1. 历史报告列表展示（支持分页）
 * 2. 搜索和筛选（品牌、状态、时间）
 * 3. 多种排序方式（时间、分数）
 * 4. 单个删除和批量删除
 * 5. 本地缓存管理
 * 6. 空状态和加载状态
 * 7. 统计信息展示
 * 
 * 设计理念：
 * - 麦肯锡式专业分析风格
 * - 清晰的信息层级
 * - 高效的操作流程
 * 
 * 作者：前端工程师 & UI 设计大师
 * 日期：2026-03-04
 * 版本：2.0
 */

const { getTestHistory, deleteHistoryReport, batchDeleteHistoryReports } = require('../../api/history');
const { clearDiagnosisResult, batchClearDiagnosisResults } = require('../../utils/storage-manager');

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
    
    // 排序
    sortBy: 'time', // time, score
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
      averageScore: 0
    },
    
    // 空状态
    isEmpty: false,
    emptyType: 'no_data', // no_data, no_search_result, network_error
    
    // UI 状态
    showFilterPanel: false,
    showSortMenu: false,
    toast: {
      show: false,
      message: '',
      type: 'info' // info, success, error
    }
  },

  onLoad: function(options) {
    console.log('📋 历史记录页面加载');
    this.initPage();
  },

  onShow: function() {
    // 页面显示时检查是否需要刷新
    if (this.data.historyList.length === 0) {
      this.refreshHistory();
    }
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
   * 加载历史记录
   */
  async loadHistory() {
    if (this.data.loading) return;

    this.setData({ loading: true });

    try {
      const { currentPage, pageSize, filterBrand, filterStatus, sortBy, sortOrder } = this.data;

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
      const processedReports = reports.map(report => ({
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
        shortDate: this.formatShortDate(report.created_at || report.createdAt)
      }));

      // 更新数据
      const historyList = currentPage === 1
        ? processedReports
        : [...this.data.historyList, ...processedReports];

      this.setData({
        historyList,
        filteredList: historyList,
        totalCount: result.total || result.pagination?.total || historyList.length,
        hasMore: result.has_more !== false && processedReports.length === pageSize,
        isEmpty: historyList.length === 0,
        emptyType: historyList.length === 0 ? 'no_data' : 'no_search_result',
        loading: false
      });

      console.log(`✅ 加载历史记录成功：${historyList.length} 条`);

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
            averageScore: 0
          }
        });
        return;
      }

      const stats = {
        total: historyList.length,
        completed: historyList.filter(r => r.status === 'completed').length,
        failed: historyList.filter(r => r.status === 'failed').length,
        averageScore: Math.round(
          historyList.reduce((sum, r) => sum + (r.overallScore || 0), 0) / historyList.length
        )
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
    const { historyList, searchKeyword, filterBrand, filterStatus, filterScore, sortBy, sortOrder } = this.data;
    
    let filtered = [...historyList];
    
    // 关键词搜索
    if (searchKeyword) {
      filtered = filtered.filter(item => 
        item.brandName.toLowerCase().includes(searchKeyword.toLowerCase())
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
    
    // 排序
    filtered.sort((a, b) => {
      let compareValue = 0;
      
      if (sortBy === 'time') {
        const timeA = new Date(a.createdAt || 0).getTime();
        const timeB = new Date(b.createdAt || 0).getTime();
        compareValue = timeA - timeB;
      } else if (sortBy === 'score') {
        compareValue = (a.overallScore || 0) - (b.overallScore || 0);
      }
      
      return sortOrder === 'desc' ? -compareValue : compareValue;
    });
    
    this.setData({
      filteredList: filtered,
      isEmpty: filtered.length === 0,
      emptyType: filtered.length === 0 ? (historyList.length === 0 ? 'no_data' : 'no_search_result') : 'no_data'
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
   * 删除单个报告
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
            // 调用删除 API
            await deleteHistoryReport(executionId, reportId);
            
            // 清除本地缓存
            clearDiagnosisResult(executionId);
            
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
   * 批量删除
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
            // 调用批量删除 API
            await batchDeleteHistoryReports(selectedIds);
            
            // 清除本地缓存
            const executionIds = filteredList
              .filter(item => selectedIds.includes(item.id))
              .map(item => item.executionId);
            
            batchClearDiagnosisResults(executionIds);
            
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
    wx.navigateTo({
      url: '/pages/index/index'
    });
  }
});
