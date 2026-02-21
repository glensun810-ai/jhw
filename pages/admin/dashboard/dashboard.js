// pages/admin/dashboard/dashboard.js
/**
 * 管理员仪表盘
 */

const app = getApp();
const logger = require('../../../utils/logger');

Page({

  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    overview: {
      total_users: 0,
      new_users_today: 0,
      total_tests: 0,
      tests_today: 0
    },
    pendingTasks: [],
    recentActivities: [],
    systemStatus: null
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.loadDashboardData();
  },

  /**
   * 加载仪表盘数据
   */
  loadDashboardData() {
    try {
      this.setData({ loading: true });

      const token = wx.getStorageSync('token');

      wx.request({
        url: `${app.globalData.serverUrl}/admin/dashboard`,
        header: {
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            const data = res.data.data;
            
            // 处理待处理任务
            const pendingTasks = Object.entries(data.pending_tasks || {}).map(([stage, count]) => ({
              stage_name: this.getStageName(stage),
              stage,
              count
            }));

            this.setData({
              loading: false,
              overview: data.overview,
              pendingTasks,
              recentActivities: data.recent_activities || [],
              systemStatus: data.system_status
            });
          } else {
            throw new Error(res.data.error || '加载失败');
          }
        },
        fail: (err) => {
          logger.error('加载仪表盘失败', err);
          this.setData({ 
            loading: false,
            error: '加载失败'
          });
          wx.showToast({
            title: '加载失败',
            icon: 'none'
          });
        }
      });
    } catch (error) {
      logger.error('加载仪表盘异常', error);
      this.setData({ loading: false, error: '加载异常' });
    }
  },

  /**
   * 获取阶段名称
   */
  getStageName(stage) {
    const stageNames = {
      'init': '初始化',
      'ai_fetching': 'AI 获取中',
      'ranking_analysis': '排名分析',
      'source_tracing': '信源追踪',
      'completed': '已完成'
    };
    return stageNames[stage] || stage;
  },

  /**
   * 格式化日期
   */
  formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${month}-${day} ${hours}:${minutes}`;
  },

  /**
   * 导航到指定页面
   */
  navigateTo(e) {
    const url = e.currentTarget.dataset.url;
    if (url) {
      wx.navigateTo({ url });
    }
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    this.loadDashboardData();
    wx.stopPullDownRefresh();
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: '管理后台 - 品牌 AI 诊断系统',
      path: '/pages/admin/dashboard/dashboard'
    };
  }
});
