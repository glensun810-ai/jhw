// pages/admin/audit-logs/audit-logs.js
/**
 * 审计日志页面
 */

const app = getApp();
const logger = require('../../../utils/logger');

Page({

  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    logs: [],
    statistics: null,
    suspiciousActivities: [],
    filters: {
      admin_id: '',
      action: '',
      actionIndex: 0,
      resource: '',
      start_date: '',
      end_date: '',
    },
    pagination: {
      page: 1,
      page_size: 20,
      total: 0,
      total_pages: 0
    },
    actionOptions: ['全部', 'grant_admin', 'revoke_admin', 'batch_delete', 'batch_notification', 'export_data']
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.loadAuditLogs();
    this.loadStatistics();
    this.loadSuspiciousActivities();
  },

  /**
   * 加载审计日志
   */
  loadAuditLogs() {
    try {
      this.setData({ loading: true });
      const token = wx.getStorageSync('token');
      const { page, page_size } = this.data.pagination;
      const { filters } = this.data;

      // 构建查询参数
      const queryParams = [];
      queryParams.push(`page=${page}`);
      queryParams.push(`page_size=${page_size}`);
      
      if (filters.admin_id) queryParams.push(`admin_id=${filters.admin_id}`);
      if (filters.action && filters.action !== '全部') queryParams.push(`action=${filters.action}`);
      if (filters.resource) queryParams.push(`resource=${filters.resource}`);
      if (filters.start_date) queryParams.push(`start_date=${filters.start_date}`);
      if (filters.end_date) queryParams.push(`end_date=${filters.end_date}`);

      const queryString = queryParams.join('&');

      wx.request({
        url: `${app.globalData.serverUrl}/audit/logs?${queryString}`,
        header: { 'Authorization': token ? `Bearer ${token}` : '' },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            const data = res.data.data;
            this.setData({
              loading: false,
              logs: data.logs,
              pagination: data.pagination
            });
          } else {
            throw new Error(res.data.error || '加载失败');
          }
        },
        fail: (err) => {
          logger.error('加载审计日志失败', err);
          this.setData({ loading: false });
          wx.showToast({
            title: '加载失败',
            icon: 'none'
          });
        }
      });
    } catch (error) {
      logger.error('加载审计日志异常', error);
      this.setData({ loading: false });
    }
  },

  /**
   * 加载统计数据
   */
  loadStatistics() {
    const token = wx.getStorageSync('token');
    
    wx.request({
      url: `${app.globalData.serverUrl}/audit/statistics?days=7`,
      header: { 'Authorization': token ? `Bearer ${token}` : '' },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          this.setData({
            statistics: res.data.data
          });
        }
      },
      fail: (err) => {
        logger.error('加载统计数据失败', err);
      }
    });
  },

  /**
   * 加载可疑活动
   */
  loadSuspiciousActivities() {
    const token = wx.getStorageSync('token');
    
    wx.request({
      url: `${app.globalData.serverUrl}/audit/suspicious?threshold=10&minutes=5`,
      header: { 'Authorization': token ? `Bearer ${token}` : '' },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          this.setData({
            suspiciousActivities: res.data.data.suspicious_activities
          });
        }
      },
      fail: (err) => {
        logger.error('加载可疑活动失败', err);
      }
    });
  },

  /**
   * 筛选条件输入
   */
  onAdminIdInput(e) {
    this.setData({
      'filters.admin_id': e.detail.value
    });
  },

  /**
   * 操作类型选择
   */
  onActionChange(e) {
    const index = parseInt(e.detail.value);
    const action = index > 0 ? this.data.actionOptions[index] : '';
    
    this.setData({
      'filters.actionIndex': index,
      'filters.action': action
    });
  },

  /**
   * 日期选择
   */
  onDateChange(e) {
    this.setData({
      'filters.end_date': e.detail.value
    });
  },

  /**
   * 应用筛选
   */
  applyFilters() {
    this.setData({
      pagination: { ...this.data.pagination, page: 1 }
    });
    this.loadAuditLogs();
  },

  /**
   * 重置筛选
   */
  resetFilters() {
    this.setData({
      filters: {
        admin_id: '',
        action: '',
        actionIndex: 0,
        resource: '',
        start_date: '',
        end_date: '',
      }
    });
    this.loadAuditLogs();
  },

  /**
   * 导出日志
   */
  exportLogs() {
    wx.showLoading({ title: '生成文件中...', mask: true });

    const token = wx.getStorageSync('token');
    const { filters } = this.data;
    
    // 构建查询参数
    const queryParams = ['format=csv'];
    if (filters.admin_id) queryParams.push(`admin_id=${filters.admin_id}`);
    if (filters.start_date) queryParams.push(`start_date=${filters.start_date}`);
    if (filters.end_date) queryParams.push(`end_date=${filters.end_date}`);
    
    const queryString = queryParams.join('&');
    const timestamp = new Date().getTime();

    wx.downloadFile({
      url: `${app.globalData.serverUrl}/audit/export?${queryString}`,
      header: { 'Authorization': token ? `Bearer ${token}` : '' },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200) {
          wx.openDocument({
            filePath: res.tempFilePath,
            showMenu: true,
            success: () => {
              wx.showToast({
                title: '导出成功',
                icon: 'success'
              });
            }
          });
        } else {
          wx.showToast({
            title: '导出失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        logger.error('导出失败', err);
        wx.showToast({
          title: '导出失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 分页
   */
  prevPage() {
    if (this.data.pagination.page > 1) {
      this.setData({
        pagination: { ...this.data.pagination, page: this.data.pagination.page - 1 }
      });
      this.loadAuditLogs();
    }
  },

  nextPage() {
    if (this.data.pagination.page < this.data.pagination.total_pages) {
      this.setData({
        pagination: { ...this.data.pagination, page: this.data.pagination.page + 1 }
      });
      this.loadAuditLogs();
    }
  },

  /**
   * 格式化日期时间
   */
  formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${month}-${day} ${hours}:${minutes}`;
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    this.loadAuditLogs();
    this.loadStatistics();
    this.loadSuspiciousActivities();
    wx.stopPullDownRefresh();
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: '审计日志 - 品牌 AI 诊断系统',
      path: '/pages/admin/audit-logs/audit-logs'
    };
  }
});
