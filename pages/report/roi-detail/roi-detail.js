// pages/report/roi-detail/roi-detail.js
/**
 * ROI 详情分析页
 * 
 * 功能:
 * - 展示 ROI 核心指标详情
 * - 品牌影响力评分多维度分析
 * - 行业基准对比分析
 * 
 * 数据来源:
 * - 从 wx.getStorageSync('roi_detail_data') 获取传递的数据
 * - 或从服务器 API 获取最新数据
 */

const app = getApp();
const logger = require('../../../utils/logger');

// 默认行业基准
const DEFAULT_BENCHMARKS = {
  exposure_roi_industry_avg: 2.5,
  sentiment_roi_industry_avg: 0.6,
  ranking_roi_industry_avg: 50
};

Page({

  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    error: null,
    
    // ROI 数据
    roiData: null,
    
    // 影响力评分
    impactScores: null,
    
    // 行业基准
    benchmarks: DEFAULT_BENCHMARKS,
    
    // 执行 ID
    executionId: null,
    
    // 页面标题
    pageTitle: 'ROI 详情分析',
    
    // 影响力等级（用于 WXM 显示）
    impactLevelClass: '',
    impactLevelText: ''
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    logger.info('ROI 详情页加载', { options });
    
    // 获取执行 ID（如果有）
    if (options && options.executionId) {
      this.setData({ executionId: options.executionId });
    }
    
    // 加载 ROI 数据
    this.loadROIData();
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {
    logger.debug('ROI 详情页初次渲染完成');
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 每次显示时检查数据是否有效
    this.validateData();
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
    logger.debug('ROI 详情页隐藏');
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    logger.debug('ROI 详情页卸载');
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    logger.debug('用户下拉刷新');
    this.loadROIData()
      .then(() => {
        wx.stopPullDownRefresh();
        wx.showToast({
          title: '刷新成功',
          icon: 'success'
        });
      })
      .catch(() => {
        wx.stopPullDownRefresh();
        wx.showToast({
          title: '刷新失败',
          icon: 'none'
        });
      });
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    // 暂无更多数据
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: 'ROI 详情分析 - GEO 品牌诊断',
      path: '/pages/report/roi-detail/roi-detail'
    };
  },

  /**
   * 加载 ROI 数据
   * 优先从本地存储获取，如果没有则从服务器获取
   */
  loadROIData() {
    return new Promise((resolve, reject) => {
      try {
        this.setData({ loading: true, error: null });

        // 1. 尝试从本地存储获取数据
        const cachedData = wx.getStorageSync('roi_detail_data');
        logger.debug('本地存储数据', { cachedData });

        if (cachedData && cachedData.roiData && cachedData.impactScores) {
          // 检查数据是否过期（超过 30 分钟）
          const isExpired = Date.now() - cachedData.timestamp > 30 * 60 * 1000;
          
          if (!isExpired) {
            logger.info('使用缓存的 ROI 数据');
            const impactLevel = this.getImpactLevel(cachedData.impactScores.overall_impact);
            
            // P2 修复：预处理数据，避免 WXML 中调用方法
            const displayData = this.preprocessROIData(
              cachedData.roiData,
              cachedData.impactScores,
              cachedData.benchmarks || DEFAULT_BENCHMARKS
            );
            
            this.setData({
              loading: false,
              roiData: cachedData.roiData,
              impactScores: cachedData.impactScores,
              benchmarks: cachedData.benchmarks || DEFAULT_BENCHMARKS,
              executionId: cachedData.executionId,
              impactLevelClass: impactLevel,
              impactLevelText: this.getImpactLevelText(cachedData.impactScores.overall_impact),
              // P2 新增：显示数据
              ...displayData
            });
            resolve();
            return;
          } else {
            logger.info('缓存数据已过期，尝试从服务器获取最新数据');
          }
        }

        // 2. 如果有 executionId，尝试从服务器获取最新数据
        if (this.data.executionId) {
          this.fetchROIDataFromServer(this.data.executionId)
            .then(resolve)
            .catch(() => {
              // 服务器获取失败，使用缓存数据（如果有）
              if (cachedData && cachedData.roiData) {
                logger.warn('服务器获取失败，使用缓存数据');
                this.setData({
                  loading: false,
                  roiData: cachedData.roiData,
                  impactScores: cachedData.impactScores,
                  benchmarks: cachedData.benchmarks || DEFAULT_BENCHMARKS
                });
                resolve();
              } else {
                // 使用默认数据
                this.loadDefaultData();
                resolve();
              }
            });
        } else {
          // 3. 没有 executionId，使用默认数据
          logger.info('无 executionId，使用默认数据');
          this.loadDefaultData();
          resolve();
        }
      } catch (error) {
        logger.error('加载 ROI 数据失败', error);
        this.setData({
          loading: false,
          error: '加载失败：' + (error.message || '未知错误')
        });
        reject(error);
      }
    });
  },

  /**
   * 从服务器获取 ROI 数据
   */
  fetchROIDataFromServer(executionId) {
    return new Promise((resolve, reject) => {
      const apiUrl = app.globalData.apiBaseUrl || 'https://api.example.com';

      wx.request({
        url: `${apiUrl}/api/roi-metrics/${executionId}`,
        method: 'GET',
        timeout: 30000,
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            const data = res.data;
            const impactScores = data.impact_scores || data.impactScores || {};
            const overallImpact = impactScores.overall_impact || 75;
            const impactLevel = this.getImpactLevel(overallImpact);
            const impactChartConfig = this.generateImpactChartConfig(impactScores);
            
            // P2 修复：预处理数据，避免 WXML 中调用方法
            const displayData = this.preprocessROIData(
              data.roi_metrics || data.roiData,
              impactScores,
              data.benchmarks || DEFAULT_BENCHMARKS
            );

            this.setData({
              loading: false,
              roiData: data.roi_metrics || data.roiData,
              impactScores: impactScores,
              benchmarks: data.benchmarks || DEFAULT_BENCHMARKS,
              impactLevelClass: impactLevel,
              impactLevelText: this.getImpactLevelText(overallImpact),
              impactChartConfig: impactChartConfig,
              // P2 新增：显示数据
              ...displayData
            });

            // 更新缓存
            wx.setStorageSync('roi_detail_data', {
              roiData: data.roi_metrics || data.roiData,
              impactScores: impactScores,
              benchmarks: data.benchmarks || DEFAULT_BENCHMARKS,
              executionId: executionId,
              timestamp: Date.now()
            });

            resolve();
          } else {
            reject(new Error('服务器响应异常'));
          }
        },
        fail: (error) => {
          logger.error('请求 ROI 数据失败', error);
          reject(error);
        }
      });
    });
  },

  /**
   * 加载默认数据
   */
  loadDefaultData() {
    // 使用默认数据展示
    const defaultImpactScores = {
      authority_impact: 72,
      visibility_impact: 85,
      sentiment_impact: 68,
      overall_impact: 75
    };
    const defaultRoiData = {
      exposure_roi: 3.5,
      sentiment_roi: 2.1,
      ranking_roi: 75,
      estimated_value: 50000
    };
    
    const impactLevel = this.getImpactLevel(defaultImpactScores.overall_impact);
    const impactChartConfig = this.generateImpactChartConfig(defaultImpactScores);
    
    // P2 修复：预处理数据，避免 WXML 中调用方法
    const displayData = this.preprocessROIData(
      defaultRoiData,
      defaultImpactScores,
      DEFAULT_BENCHMARKS
    );

    this.setData({
      loading: false,
      roiData: defaultRoiData,
      impactScores: defaultImpactScores,
      benchmarks: DEFAULT_BENCHMARKS,
      impactLevelClass: impactLevel,
      impactLevelText: this.getImpactLevelText(defaultImpactScores.overall_impact),
      impactChartConfig: impactChartConfig,
      // P2 新增：显示数据
      ...displayData
    });
  },

  /**
   * P2 新增：生成影响力饼图配置
   */
  generateImpactChartConfig(impactScores) {
    return {
      series: [
        { name: '权威性', value: impactScores.authority_impact || 0 },
        { name: '可见度', value: impactScores.visibility_impact || 0 },
        { name: '情感', value: impactScores.sentiment_impact || 0 }
      ],
      colors: ['#667eea', '#f093fb', '#4facfe'],
      legend: ['权威性', '可见度', '情感']
    };
  },

  /**
   * P2 修复：预处理 ROI 数据，避免 WXML 中调用方法
   * @param {Object} roiData - ROI 原始数据
   * @param {Object} impactScores - 影响力评分数据
   * @param {Object} benchmarks - 行业基准数据
   * @returns {Object} 预处理后的数据
   */
  preprocessROIData(roiData, impactScores, benchmarks) {
    // 安全获取数值，避免 null/undefined
    const exposureRoi = (roiData && roiData.exposure_roi) || 0;
    const sentimentRoi = (roiData && roiData.sentiment_roi) || 0;
    const rankingRoi = (roiData && roiData.ranking_roi) || 0;
    const estimatedValue = (roiData && roiData.estimated_value) || 0;

    const exposureAvg = (benchmarks && benchmarks.exposure_roi_industry_avg) || 2.5;
    const sentimentAvg = (benchmarks && benchmarks.sentiment_roi_industry_avg) || 0.6;
    const rankingAvg = (benchmarks && benchmarks.ranking_roi_industry_avg) || 50;

    return {
      // ROI 显示值（保留一位小数）
      exposure_roi_display: exposureRoi.toFixed(1),
      sentiment_roi_display: sentimentRoi.toFixed(1),
      ranking_roi_display: rankingRoi.toFixed(0),
      estimated_value_display: this.formatValue(estimatedValue),

      // 影响力显示值（保留整数）
      authority_impact_display: ((impactScores && impactScores.authority_impact) || 0).toFixed(0),
      visibility_impact_display: ((impactScores && impactScores.visibility_impact) || 0).toFixed(0),
      sentiment_impact_display: ((impactScores && impactScores.sentiment_impact) || 0).toFixed(0),
      overall_impact_display: ((impactScores && impactScores.overall_impact) || 0).toFixed(0),

      // 百分比差值（保留一位小数）
      exposure_delta_percent: ((exposureRoi - exposureAvg) / exposureAvg * 100).toFixed(1),
      sentiment_delta_percent: ((sentimentRoi - sentimentAvg) / sentimentAvg * 100).toFixed(1),
      ranking_delta_percent: ((rankingRoi - rankingAvg) / rankingAvg * 100).toFixed(1),

      // 比较结果（用于样式类）
      exposure_is_positive: exposureRoi >= exposureAvg,
      sentiment_is_positive: sentimentRoi >= sentimentAvg,
      ranking_is_positive: rankingRoi >= rankingAvg
    };
  },

  /**
   * 验证数据有效性
   */
  validateData() {
    const { roiData, impactScores } = this.data;
    
    if (!roiData || !impactScores) {
      logger.warn('数据无效，重新加载');
      this.loadROIData();
    }
  },

  /**
   * 格式化价值数字
   */
  formatValue(value) {
    if (value >= 10000) {
      return (value / 10000).toFixed(1) + '万';
    } else if (value >= 1000) {
      return (value / 1000).toFixed(1) + '千';
    }
    return value.toFixed(0);
  },

  /**
   * 获取影响力等级
   */
  getImpactLevel(score) {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'average';
    return 'poor';
  },

  /**
   * 获取影响力等级文本
   */
  getImpactLevelText(score) {
    if (score >= 80) return '优秀';
    if (score >= 60) return '良好';
    if (score >= 40) return '一般';
    return '待提升';
  },

  /**
   * 重试加载
   */
  retry() {
    this.loadROIData();
  }
});
