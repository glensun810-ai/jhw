// pages/admin/analytics/analytics.js
/**
 * 使用分析页面
 */

const app = getApp();
const logger = require('../../../utils/logger');
const { getLineChartConfig, getPieChartConfig } = require('../../../utils/charts');

Page({

  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    days: 7,
    userMetrics: {
      dau: 0,
      mau: 0,
      dau_mau_ratio: 0
    },
    testMetrics: {
      tests_today: 0,
      tests_period: 0,
      avg_per_day: 0
    },
    platformMetrics: {
      top_platform: '',
      platform_count: 0
    },
    activeTrend: [],
    activeTrendChartOption: null,
    platformPieChartOption: null,
    errorTrendChartOption: null,
    platformStats: [],
    platformOverview: {
      total_calls: 0,
      avg_calls_per_day: 0
    },
    errorStats: [],
    errorTrend: [],
    errorOverview: {
      overall_error_rate: 0
    },
    featureStats: {
      brand_test: 0,
      ai_diagnosis: 0,
      unique_users: 0
    },
    charts: {}
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.loadAnalyticsData();
  },

  /**
   * 选择天数
   */
  selectDays(e) {
    const days = e.currentTarget.dataset.days;
    if (days !== this.data.days) {
      this.setData({ days });
      this.loadAnalyticsData();
    }
  },

  /**
   * 加载分析数据
   */
  loadAnalyticsData() {
    try {
      this.setData({ loading: true });
      const token = wx.getStorageSync('token');

      // 并行加载多个接口
      Promise.all([
        this.fetchDashboard(token),
        this.fetchActiveUsers(token),
        this.fetchPlatformStats(token),
        this.fetchErrorStats(token),
        this.fetchFeatureUsage(token)
      ]).then(() => {
        this.setData({ loading: false });
      }).catch(error => {
        logger.error('加载分析数据失败', error);
        this.setData({ loading: false });
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        });
      });
    } catch (error) {
      logger.error('加载分析数据异常', error);
      this.setData({ loading: false });
    }
  },

  /**
   * 图表准备就绪
   */
  onChartReady(e) {
    const chartId = e.currentTarget.id;
    const { chart } = e.detail;
    this.data.charts[chartId] = chart;
  },

  /**
   * 获取仪表盘数据
   */
  fetchDashboard(token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.serverUrl}/analytics/dashboard?days=${this.data.days}`,
        header: { 'Authorization': token ? `Bearer ${token}` : '' },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            const data = res.data.data;
            this.setData({
              userMetrics: data.user_metrics,
              testMetrics: data.test_metrics,
              platformMetrics: data.platform_metrics
            });
          }
          resolve();
        },
        fail: reject
      });
    });
  },

  /**
   * 获取活跃用户数据
   */
  fetchActiveUsers(token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.serverUrl}/analytics/users/active?days=${this.data.days}`,
        header: { 'Authorization': token ? `Bearer ${token}` : '' },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            const dailyStats = res.data.data.daily_stats || [];

            // 准备图表数据
            const categories = dailyStats.map(item => item.date.substring(5));
            const data = dailyStats.map(item => item.dau);

            // 生成折线图配置（带防御性检查）
            const chartOption = getLineChartConfig({
              data,
              categories,
              title: '',
              color: '#667eea'
            });

            const updateData = {
              activeTrend: dailyStats.map(item => ({
                date: item.date.substring(5),
                dau: item.dau
              }))
            };
            
            // 只有在图表配置有效时才更新
            if (chartOption) {
              updateData.activeTrendChartOption = chartOption;
            }

            this.setData(updateData);

            // 更新已渲染的图表
            if (chartOption && this.data.charts.activeTrendChart) {
              this.data.charts.activeTrendChart.setOption(chartOption);
            }
          }
          resolve();
        },
        fail: reject
      });
    });
  },

  /**
   * 获取平台统计数据
   */
  fetchPlatformStats(token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.serverUrl}/analytics/ai-platforms/stats?days=${this.data.days}`,
        header: { 'Authorization': token ? `Bearer ${token}` : '' },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            const data = res.data.data;

            // 计算百分比
            const maxCount = Math.max(...data.platforms.map(p => p.count), 1);
            const platformStats = data.platforms.map(p => ({
              ...p,
              percentage: (p.count / maxCount) * 100
            })).slice(0, 10);

            // 生成饼图数据
            const pieData = data.platforms.slice(0, 5).map(p => ({
              name: p.name,
              value: p.count
            }));

            // 生成饼图配置（带防御性检查）
            const pieChartOption = getPieChartConfig({
              data: pieData,
              title: ''
            });

            const updateData = {
              platformStats,
              platformOverview: data.overview
            };
            
            // 只有在图表配置有效时才更新
            if (pieChartOption) {
              updateData.platformPieChartOption = pieChartOption;
            }

            this.setData(updateData);

            // 更新已渲染的图表
            if (pieChartOption && this.data.charts.platformPieChart) {
              this.data.charts.platformPieChart.setOption(pieChartOption);
            }
          }
          resolve();
        },
        fail: reject
      });
    });
  },

  /**
   * 获取错误统计数据
   */
  fetchErrorStats(token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.serverUrl}/analytics/errors/stats?days=${this.data.days}`,
        header: { 'Authorization': token ? `Bearer ${token}` : '' },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            const data = res.data.data;
            
            // 生成错误趋势图数据
            const errorTrend = data.error_trend || [];
            const categories = errorTrend.map(item => item.date.substring(5));
            const errorRates = errorTrend.map(item => item.error_rate);
            
            // 生成折线图配置
            const errorChartOption = getLineChartConfig({
              data: errorRates,
              categories,
              title: '',
              color: '#f5576c'
            });
            
            this.setData({
              errorStats: data.stage_stats,
              errorTrend,
              errorOverview: data.overview,
              errorTrendChartOption: errorChartOption
            });
            
            // 更新已渲染的图表
            if (this.data.charts.errorTrendChart) {
              this.data.charts.errorTrendChart.setOption(errorChartOption);
            }
          }
          resolve();
        },
        fail: reject
      });
    });
  },

  /**
   * 获取功能使用数据
   */
  fetchFeatureUsage(token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.serverUrl}/analytics/features/usage?days=${this.data.days}`,
        header: { 'Authorization': token ? `Bearer ${token}` : '' },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            this.setData({
              featureStats: res.data.data.feature_stats
            });
          }
          resolve();
        },
        fail: reject
      });
    });
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    this.loadAnalyticsData();
    wx.stopPullDownRefresh();
  },

  /**
   * 页面卸载时销毁图表
   */
  onUnload() {
    Object.values(this.data.charts).forEach(chart => {
      if (chart) {
        chart.dispose();
      }
    });
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: '使用分析 - 品牌 AI 诊断系统',
      path: '/pages/admin/analytics/analytics'
    };
  }
});
