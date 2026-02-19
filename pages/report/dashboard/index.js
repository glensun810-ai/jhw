/**
 * GEO 品牌战略诊断看板 - 页面逻辑
 *
 * 麦肯锡三段式布局：
 * 1. 概览评分（健康度、声量占比、情感均值）
 * 2. 核心问题诊断分析（问题墙）
 * 3. 高风险负面信源（归因列表）
 */

const app = getApp();
const logger = require('../../../utils/logger');
const storage = require('../../../utils/storage');

// API 基础 URL (根据实际部署环境配置)
const API_BASE_URL = app.globalData.apiBaseUrl || 'https://api.example.com'; // 请替换为实际的 API 地址

Page({
  data: {
    // 看板数据
    dashboardData: null,
    questionCards: [],
    toxicSources: [],

    // 原始数据
    rawResults: [],
    competitors: [],

    // 状态
    loading: true,
    loadError: null,
    executionId: null
  },

  /**
   * 页面加载
   */
  onLoad: function(options) {
    // 保存 executionId
    if (options && options.executionId) {
      this.setData({ executionId: options.executionId });
    }
    this.loadDashboardData();
  },

  /**
   * 页面显示
   */
  onShow: function() {
    // 每次显示时重新加载数据（确保数据最新）
    if (!this.data.dashboardData && !this.data.loading) {
      this.loadDashboardData();
    }
  },

  /**
   * 加载看板数据
   */
  loadDashboardData: function() {
    try {
      this.setData({ loading: true, loadError: null });

      // 优先从服务器获取真实数据
      const executionId = this.data.executionId || (app.globalData.lastReport && app.globalData.lastReport.executionId);
      
      if (executionId) {
        // 从服务器获取数据
        this.fetchDataFromServer(executionId);
        return;
      }

      // 如果没有 executionId，尝试从全局存储获取缓存数据
      const lastReport = app.globalData.lastReport;
      if (lastReport && lastReport.dashboard) {
        logger.debug('使用缓存的 Dashboard 数据');
        const dashboardData = lastReport.dashboard;
        this.setData({
          loading: false,
          dashboardData: dashboardData.summary || dashboardData,
          questionCards: dashboardData.questionCards || [],
          toxicSources: dashboardData.toxicSources || [],
          rawResults: lastReport.raw || [],
          competitors: lastReport.competitors || []
        });
        return;
      }

      // 既没有 executionId 也没有缓存数据
      logger.warn('未找到 Dashboard 数据');
      this.setData({
        loading: false,
        loadError: '未找到报告数据，请重新执行测试'
      });

    } catch (error) {
      logger.error('加载看板数据失败', error);
      this.setData({
        loading: false,
        loadError: '加载失败：' + (error.message || '未知错误')
      });
    }
  },

  /**
   * 从服务器获取数据
   */
  fetchDataFromServer: function(executionId) {
    logger.debug('开始获取 Dashboard 数据', { executionId });
    
    wx.request({
      url: `${API_BASE_URL}/api/dashboard/aggregate`,
      method: 'GET',
      data: {
        executionId: executionId,
        userOpenid: app.globalData.userOpenid || 'anonymous'
      },
      timeout: 30000, // 30 秒超时
      success: (res) => {
        logger.debug('Dashboard API 响应成功', { 
          success: res.data?.success,
          hasData: !!res.data?.dashboard 
        });
        
        if (res.data && res.data.success) {
          this.processServerData(res.data.dashboard);
        } else {
          // API 返回错误
          const errorMsg = res.data?.error || '数据格式错误';
          const errorCode = res.data?.code;
          
          logger.warn('Dashboard API 返回错误', { error: errorMsg, code: errorCode });
          
          if (errorCode === 'NO_DATA') {
            // 没有数据，提示用户重新测试
            this.setData({
              loading: false,
              loadError: '未找到测试数据，请先执行品牌测试'
            });
          } else {
            this.setData({
              loading: false,
              loadError: errorMsg
            });
          }
        }
      },
      fail: (error) => {
        logger.error('获取 Dashboard 数据失败', error);
        let errorMsg = '网络请求失败';
        
        if (error.errMsg) {
          if (error.errMsg.includes('timeout')) {
            errorMsg = '请求超时，请检查网络连接';
          } else if (error.errMsg.includes('fail')) {
            errorMsg = '无法连接服务器，请检查网络';
          }
        }
        
        this.setData({
          loading: false,
          loadError: errorMsg
        });
      }
    });
  },

  /**
   * 处理服务器返回的数据
   */
  processServerData: function(dashboard) {
    try {
      logger.debug('处理 Dashboard 数据', { 
        hasSummary: !!dashboard.summary,
        questionCount: dashboard.questionCards?.length,
        toxicSourceCount: dashboard.toxicSources?.length
      });
      
      // 提取数据
      const summary = dashboard.summary || {};
      const questionCards = dashboard.questionCards || [];
      const toxicSources = dashboard.toxicSources || [];

      // 更新页面数据
      this.setData({
        loading: false,
        dashboardData: summary,
        questionCards: questionCards,
        toxicSources: toxicSources
      });

      // 保存到全局存储 (缓存)
      app.globalData.lastReport = {
        executionId: this.data.executionId,
        dashboard: dashboard,
        raw: [],
        competitors: []
      };

      // 保存到本地历史记录
      this._saveToHistory(dashboard);

      logger.info('Dashboard 数据加载成功', { 
        healthScore: summary.healthScore,
        questionCount: questionCards.length 
      });

    } catch (error) {
      logger.error('处理 Dashboard 数据失败', error);
      this.setData({
        loading: false,
        loadError: '数据处理失败：' + (error.message || '未知错误')
      });
    }
  },

  /**
   * 保存到本地历史记录
   * @private
   * @param {Object} dashboard - Dashboard 数据
   */
  _saveToHistory: async function(dashboard) {
    try {
      const record = {
        executionId: this.data.executionId,
        summary: dashboard.summary || {},
        questionCards: dashboard.questionCards || [],
        toxicSources: dashboard.toxicSources || [],
        createdAt: Date.now()
      };

      const success = await storage.saveDiagnosisRecord(record);
      
      if (success) {
        logger.debug('历史记录保存成功');
        
        // 检查存储空间
        const usage = await storage.checkStorageUsage();
        if (usage.isWarning) {
          logger.warn('存储空间不足', { percent: usage.percent });
          
          // 提醒用户清理
          wx.showModal({
            title: '存储空间提醒',
            content: `本地存储空间已达${usage.percent}%，建议清理历史记录。`,
            confirmText: '去清理',
            cancelText: '稍后',
            success: (res) => {
              if (res.confirm) {
                wx.navigateTo({
                  url: '/pages/report/history/index'
                });
              }
            }
          });
        }
      }
    } catch (error) {
      logger.error('保存历史记录失败', error);
    }
  },

  /**
   * 跳转到问题详情页
   */
  goToQuestionDetail: function(e) {
    const index = e.currentTarget.dataset.index;
    const questionCard = this.data.questionCards[index];

    if (!questionCard) return;

    // 保存选中的问题数据到全局
    app.globalData.selectedQuestion = {
      index: index,
      data: questionCard,
      fullResults: this.data.rawResults.filter(r => r.question_id === index)
    };

    // 跳转到问题详情页（第四阶段：深度诊断）
    wx.navigateTo({
      url: `/pages/report/detail/index?index=${index}`,
      fail: (err) => {
        console.error('跳转到问题详情失败:', err);
        wx.showToast({
          title: '跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 查看历史记录
   */
  viewHistory: function() {
    wx.navigateTo({
      url: '/pages/report/history/index'
    });
  },

  /**
   * 查看原始数据
   */
  viewRawData: function() {
    // 保存到全局存储
    app.globalData.rawResults = this.data.rawResults;

    // TODO: 跳转到原始数据页面
    // wx.navigateTo({
    //   url: '/pages/report/raw-data/index'
    // });

    wx.showToast({
      title: '原始数据功能开发中',
      icon: 'none'
    });
  },

  /**
   * 导出报告
   */
  exportReport: function() {
    wx.showActionSheet({
      itemList: ['导出 PDF', '导出 Excel', '分享报告'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.exportToPDF();
        } else if (res.tapIndex === 1) {
          this.exportToExcel();
        } else if (res.tapIndex === 2) {
          this.shareReport();
        }
      }
    });
  },

  /**
   * 导出为 PDF
   */
  exportToPDF: function() {
    wx.showToast({
      title: 'PDF 导出功能开发中',
      icon: 'none'
    });
  },

  /**
   * 导出为 Excel
   */
  exportToExcel: function() {
    wx.showToast({
      title: 'Excel 导出功能开发中',
      icon: 'none'
    });
  },

  /**
   * 分享报告
   */
  shareReport: function() {
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    });
  },

  /**
   * 重试加载
   */
  retry: function() {
    this.loadDashboardData();
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function() {
    this.loadDashboardData()
      .then(() => {
        wx.stopPullDownRefresh();
      })
      .catch(() => {
        wx.stopPullDownRefresh();
      });
  },

  /**
   * 页面分享
   */
  onShareAppMessage: function() {
    const brandName = this.data.dashboardData?.summary?.brandName || '品牌';
    const healthScore = this.data.dashboardData?.summary?.healthScore || 0;
    
    return {
      title: `${brandName} GEO 品牌诊断报告 - 健康度得分${healthScore}`,
      path: '/pages/report/dashboard/index'
    };
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline: function() {
    const brandName = this.data.dashboardData?.summary?.brandName || '品牌';
    const healthScore = this.data.dashboardData?.summary?.healthScore || 0;
    
    return {
      title: `${brandName} GEO 品牌诊断报告 - 健康度得分${healthScore}`,
      query: '',
      imageUrl: ''
    };
  }
});
