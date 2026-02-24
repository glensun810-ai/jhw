const { debug, info, warn, error } = require('../../utils/logger');

/**
 * 结果页 - 重构版本
 * 
 * 重构说明:
 * - 数据加载逻辑 → services/resultDataService.js
 * - 图表数据准备 → services/chartDataService.js
 * - 图表渲染逻辑 → utils/chartRenderer.js
 */

const { saveResult } = require('../../utils/saved-results-sync');
const { generateFullReport } = require('../../utils/pdf-export');
const { loadResultFromStorage, fetchResultsFromServer, buildCompetitiveAnalysis, saveResultToStorage } = require('../../services/resultDataService');
const { prepareRadarChartData, prepareKeywordCloudData, prepareTrendChartData } = require('../../services/chartDataService');
const { renderAllCharts, disposeCharts } = require('../../utils/chartRenderer');

Page({
  data: {
    targetBrand: '',
    competitiveAnalysis: null,
    latestTestResults: null,
    radarChartData: [],
    keywordCloudData: [],
    topKeywords: [],
    keywordStats: { positiveCount: 0, neutralCount: 0, negativeCount: 0 },
    chartsReady: false,
    loadingState: 'loading', // loading | success | error | empty
    errorMessage: '',
    canRetry: true
  },

  /**
   * 页面加载
   */
  onLoad: function(options) {
    console.log('📥 结果页加载 options:', options);

    const executionId = decodeURIComponent(options.executionId || '');
    const brandName = decodeURIComponent(options.brandName || '');

    this.setData({ loadingState: 'loading' });

    // 从 Storage 加载数据
    const { results, competitiveAnalysis, targetBrand, useStorageData } = loadResultFromStorage(executionId, brandName);

    if (useStorageData && results && results.length > 0) {
      console.log('✅ 从 Storage 加载数据成功');
      this.initializePageWithData(results, targetBrand, competitiveAnalysis);
    } else if (executionId) {
      console.log('🔄 Storage 无数据，从后端 API 拉取');
      this.fetchResultsFromServer(executionId, brandName);
    } else {
      this.setData({
        loadingState: 'empty',
        errorMessage: '缺少执行 ID'
      });
    }
  },

  /**
   * 从后端 API 拉取结果
   */
  fetchResultsFromServer: function(executionId, brandName) {
    fetchResultsFromServer(
      executionId,
      brandName,
      // 成功回调
      (data) => {
        this.initializePageWithData(data.results, data.targetBrand, data.competitiveAnalysis);
        this.setData({ loadingState: 'success' });
        wx.showToast({ title: '数据加载成功', icon: 'success' });
      },
      // 错误回调
      (error) => {
        console.error('加载失败:', error);
        this.setData({
          loadingState: 'error',
          errorMessage: error.message || '加载失败',
          canRetry: error.type !== 'auth'
        });

        if (error.type === 'auth') {
          setTimeout(() => {
            wx.reLaunch({ url: '/pages/login/login' });
          }, 2000);
        }
      }
    );
  },

  /**
   * 初始化页面数据
   */
  initializePageWithData: function(results, targetBrand, competitiveAnalysis) {
    try {
      // 准备图表数据
      const radarData = prepareRadarChartData(competitiveAnalysis, targetBrand, []);
      const keywordCloudResult = prepareKeywordCloudData(
        competitiveAnalysis.semanticDriftData || null,
        results,
        targetBrand
      );

      this.setData({
        targetBrand: targetBrand,
        competitiveAnalysis: competitiveAnalysis,
        latestTestResults: results,
        radarChartData: radarData,
        keywordCloudData: keywordCloudResult.keywordCloudData,
        topKeywords: keywordCloudResult.topKeywords,
        keywordStats: keywordCloudResult.keywordStats
      }, () => {
        // 数据设置完成后渲染图表
        wx.nextTick(() => {
          setTimeout(() => {
            renderAllCharts(this)
              .then(() => {
                this.setData({ chartsReady: true });
              })
              .catch(error => {
                console.error('图表渲染失败:', error);
              });
          }, 300);
        });
      });

      console.log('✅ 页面数据初始化完成');
    } catch (e) {
      console.error('初始化页面数据失败', e);
      this.setData({
        loadingState: 'error',
        errorMessage: '数据加载失败'
      });
    }
  },

  /**
   * 重试按钮点击
   */
  onRetryTap: function() {
    if (!this.data.canRetry) return;

    const executionId = wx.getStorageSync('last_diagnostic_results')?.executionId;
    const brandName = this.data.targetBrand;

    if (executionId && brandName) {
      this.setData({ loadingState: 'loading' });
      this.fetchResultsFromServer(executionId, brandName);
    }
  },

  /**
   * 返回首页
   */
  onGoHomeTap: function() {
    wx.reLaunch({ url: '/pages/index/index' });
  },

  /**
   * 平台切换
   */
  switchPlatform: function(e) {
    const index = e.currentTarget.dataset.index;
    this.setData({ currentSwiperIndex: index });
  },

  /**
   * 视图模式切换
   */
  switchViewMode: function(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({ currentViewMode: mode });
  },

  /**
   * 保存结果
   */
  saveResult: function() {
    const executionId = wx.getStorageSync('last_diagnostic_results')?.executionId;
    if (executionId) {
      saveResult({
        executionId: executionId,
        brandName: this.data.targetBrand,
        results: this.data.latestTestResults,
        competitiveAnalysis: this.data.competitiveAnalysis
      });
      wx.showToast({ title: '保存成功', icon: 'success' });
    }
  },

  /**
   * 生成报告
   */
  generateReport: function() {
    generateFullReport({
      brandName: this.data.targetBrand,
      results: this.data.latestTestResults,
      competitiveAnalysis: this.data.competitiveAnalysis
    });
  },

  /**
   * 查看历史
   */
  viewHistory: function() {
    wx.navigateTo({ url: '/pages/personal-history/personal-history' });
  },

  /**
   * 返回首页
   */
  goHome: function() {
    wx.reLaunch({ url: '/pages/index/index' });
  },

  /**
   * 页面卸载时清理图表
   */
  onUnload: function() {
    disposeCharts(this);
  }
});
