/**
 * GEO 品牌战略诊断看板 - 页面逻辑 (P0 增强版)
 *
 * 麦肯锡三段式布局：
 * 1. 概览评分（健康度、声量占比、情感均值）
 * 2. 核心问题诊断分析（问题墙）
 * 3. 高风险负面信源（归因列表）
 *
 * P0 增强:
 * - ROI 指标展示
 * - 影响力评分仪表盘
 * - 工作流分析发现
 */

const app = getApp();
const logger = require('../../../utils/logger');
const storage = require('../../../utils/storage');
const { exportToPDF, exportToExcel } = require('../../../utils/pdf-export');

// API 基础 URL (根据实际部署环境配置)
const API_BASE_URL = app.globalData.apiBaseUrl || 'https://api.example.com'; // 请替换为实际的 API 地址

// P0 新增：默认行业基准
const DEFAULT_BENCHMARKS = {
  exposure_roi_industry_avg: 2.5,
  sentiment_roi_industry_avg: 0.6,
  ranking_roi_industry_avg: 50
};

Page({
  data: {
    // 看板数据
    dashboardData: null,
    questionCards: [],
    toxicSources: [],

    // 原始数据
    rawResults: [],
    competitors: [],

    // P0 新增：ROI 和影响力数据
    defaultBenchmarks: DEFAULT_BENCHMARKS,

    // 状态
    loading: true,
    loadError: null,
    executionId: null,

    // 【新增】详情抽屉状态
    showDrawer: false,
    currentQuestionData: null,
    brandName: '',
    competitors: [],

    // P1 新增：工作流分析展开状态
    expandedWorkflowStage: ''
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
      const executionId = this.data.executionId || wx.getStorageSync('lastReport')?.executionId;

      if (executionId) {
        // 从服务器获取数据
        this.fetchDataFromServer(executionId);
        return;
      }

      // 如果没有 executionId，尝试从本地存储获取缓存数据
      const lastReport = wx.getStorageSync('lastReport');
      if (lastReport && (lastReport.dashboard || lastReport.summary)) {
        logger.debug('使用本地存储的 Dashboard 数据');
        const dashboardData = lastReport.dashboard || lastReport;
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

      // 【P0 修复】数据处理和字段兼容
      const summary = this.processSummaryData(dashboard.summary || {});
      const questionCards = this.processQuestionCards(dashboard.questionCards || []);
      const toxicSources = this.processToxicSources(dashboard.toxicSources || []);
      const interceptedTopics = dashboard.interceptedTopics || [];
      const workflowResults = dashboard.workflow_results || null;

      // 检查是否已收藏
      const favorites = wx.getStorageSync('favorites') || [];
      const isFavorite = favorites.some(f => f.executionId === this.data.executionId);

      // 更新页面数据
      this.setData({
        loading: false,
        dashboardData: summary,
        questionCards: questionCards,
        toxicSources: toxicSources,
        interceptedTopics: interceptedTopics,
        workflowResults: workflowResults,
        rawResults: dashboard.rawResults || [],
        competitors: dashboard.competitors || [],
        isFavorite: isFavorite
      });

      // 保存到全局存储 (缓存)
      app.globalData.lastReport = {
        executionId: this.data.executionId,
        dashboard: dashboard,
        raw: dashboard.rawResults || [],
        competitors: dashboard.competitors || []
      };

      // 保存到本地历史记录
      this._saveToHistory(dashboard);

      logger.info('Dashboard 数据加载成功', {
        healthScore: summary.healthScore,
        questionCount: questionCards.length,
        sovValue: summary.sov || summary.sov_value,
        isFavorite: isFavorite
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
   * 【P0 新增】处理 Summary 数据，确保字段兼容
   */
  processSummaryData: function(summary) {
    // 字段兼容处理
    return {
      brandName: summary.brandName || '未知品牌',
      healthScore: summary.healthScore || 0,
      sov: summary.sov || summary.sov_value || 0,
      sov_value: summary.sov_value || summary.sov || 0,
      avgSentiment: summary.avgSentiment || summary.sentiment_value || 0,
      sentiment_value: summary.sentiment_value || summary.avgSentiment || 0,
      totalMentions: summary.totalMentions || 0,
      totalTests: summary.totalTests || 0,
      sovLabel: summary.sovLabel || this._calculateSovLabel(summary.sov || summary.sov_value || 0),
      sovLabelClass: summary.sovLabelClass || this._calculateSovLabelClass(summary.sov || summary.sov_value || 0),
      sentimentStatus: summary.sentimentStatus || this._calculateSentimentStatus(summary.avgSentiment || summary.sentiment_value || 0),
      sentimentLabel: summary.sentimentLabel || this._calculateSentimentLabel(summary.avgSentiment || summary.sentiment_value || 0),
      riskLevel: summary.riskLevel || this._calculateRiskLevel(summary.healthScore || 0, summary.avgSentiment || summary.sentiment_value || 0),
      riskLevelText: summary.riskLevelText || this._calculateRiskLevelText(summary.riskLevel),
      healthBreakdown: summary.healthBreakdown || null,
      mention_rate: summary.mention_rate || 0
    };
  },

  /**
   * 【P0 新增】处理问题卡片数据
   */
  processQuestionCards: function(questionCards) {
    return questionCards.map(card => ({
      question_id: card.question_id,
      question_text: card.question_text,
      text: card.text || card.question_text,
      avg_rank: card.avg_rank,
      avgRank: card.avgRank || card.avg_rank,
      risk_level: card.risk_level,
      riskLevel: card.riskLevel || card.risk_level,
      riskLevelText: card.riskLevelText || this._calculateRiskLevelText(card.riskLevel || card.risk_level),
      key_competitor: card.key_competitor,
      mention_rate: card.mention_rate,
      mentionRate: card.mentionRate || card.mention_rate,
      mentionCount: card.mentionCount || 0,
      totalModels: card.totalModels || 0,
      avg_sentiment: card.avg_sentiment,
      avgSentiment: card.avgSentiment || card.avg_sentiment,
      intercepted_by: card.intercepted_by || [],
      interceptCount: card.interceptCount || 0
    }));
  },

  /**
   * 【P0 新增】处理毒源数据
   */
  processToxicSources: function(toxicSources) {
    return (toxicSources || []).map(source => ({
      url: source.url,
      site: source.site,
      site_name: source.site_name || source.site,
      threat_score: source.threat_score,
      threatScore: source.threatScore || source.threat_score,
      threatLevel: source.threatLevel || this._calculateThreatLevel(source.threat_score || source.threatScore || 0),
      totalMentions: source.total_mentions || source.totalMentions || 0,
      models: source.models || [],
      impactQuestions: source.impact_questions || source.impactQuestions || []
    }));
  },

  /**
   * 【P0 新增】计算 SOV 标签
   */
  _calculateSovLabel: function(sov) {
    if (sov >= 60) return '领先';
    if (sov >= 40) return '持平';
    return '落后';
  },

  /**
   * 【P0 新增】计算 SOV 标签类
   */
  _calculateSovLabelClass: function(sov) {
    if (sov >= 60) return 'leading';
    if (sov >= 40) return 'neutral';
    return 'lagging';
  },

  /**
   * 【P0 新增】计算情感状态
   */
  _calculateSentimentStatus: function(sentiment) {
    if (sentiment > 0.2) return 'positive';
    if (sentiment < -0.2) return 'negative';
    return 'neutral';
  },

  /**
   * 【P0 新增】计算情感标签
   */
  _calculateSentimentLabel: function(sentiment) {
    if (sentiment > 0.2) return '正面';
    if (sentiment < -0.2) return '负面';
    return '中性';
  },

  /**
   * 【P0 新增】计算风险等级
   */
  _calculateRiskLevel: function(healthScore, sentiment) {
    if (healthScore < 40 || sentiment < -0.3) return 'critical';
    if (healthScore < 60 || sentiment < 0) return 'warning';
    return 'safe';
  },

  /**
   * 【P0 新增】计算风险等级文本
   */
  _calculateRiskLevelText: function(riskLevel) {
    if (riskLevel === 'critical') return '高风险';
    if (riskLevel === 'warning') return '中风险';
    return '低风险';
  },

  /**
   * 【P0 新增】计算威胁等级
   */
  _calculateThreatLevel: function(threatScore) {
    if (threatScore >= 5) return 'critical';
    if (threatScore >= 3) return 'warning';
    return 'safe';
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
   * 打开详情抽屉（替代页面跳转）
   */
  goToQuestionDetail: function(e) {
    const index = e.currentTarget.dataset.index;
    const questionCard = this.data.questionCards[index];

    if (!questionCard) return;

    // 触发触感反馈
    wx.vibrateShort({ type: 'light' });

    // 获取该问题的完整模型数据
    const fullResults = this.data.rawResults.filter(r => r.question_id === index);
    
    // 构建抽屉组件需要的数据结构
    const questionData = {
      question_id: index,
      question_text: questionCard.text,
      models: fullResults,
      avg_rank: questionCard.avgRank,
      avg_sentiment: questionCard.avgSentiment,
      mention_count: questionCard.mentionCount,
      total_models: questionCard.totalModels
    };

    // 打开抽屉
    this.setData({
      showDrawer: true,
      currentQuestionData: questionData,
      brandName: this.data.dashboardData?.summary?.brandName || '',
      competitors: this.data.competitors
    });

    logger.info(`打开详情抽屉：问题 ${index + 1}`);
  },

  /**
   * 关闭抽屉回调
   */
  onDrawerClose: function() {
    this.setData({
      showDrawer: false,
      currentQuestionData: null
    });
    logger.info('详情抽屉已关闭');
  },

  /**
   * 【P0 新增】信源卡片点击 - 复制链接
   */
  onSourceTap: function(e) {
    const source = e.currentTarget.dataset.source;

    if (!source || !source.url) return;

    // 触发触感反馈
    wx.vibrateShort({ type: 'light' });

    // 弹出确认对话框
    wx.showModal({
      title: '查看信源',
      content: `是否复制链接去浏览器查看？\n\n${source.site_name || source.site}`,
      confirmText: '复制链接',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.copySourceLink(source.url);
        }
      }
    });
  },

  /**
   * 【P0 新增】复制信源链接
   */
  copySourceLink: function(url) {
    wx.setClipboardData({
      data: url,
      message: '链接已复制',
      success: () => {
        // 复制成功后触感反馈
        wx.vibrateShort({ type: 'light' });

        // 显式 Toast 提示
        wx.showToast({
          title: '证据链接已复制，请在浏览器打开',
          icon: 'success',
          duration: 2500
        });
      },
      fail: (err) => {
        console.error('复制链接失败', err);
        wx.showToast({
          title: '复制失败，请手动输入',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 保存抽屉数据回调
   */
  onDrawerSave: function(e) {
    const { questionData, modelId } = e.detail;
    
    // 保存到历史记录
    const savedData = {
      question: questionData,
      model: modelId,
      savedAt: new Date().toISOString()
    };
    
    // 保存到本地存储
    const history = wx.getStorageSync('savedQuestions') || [];
    history.unshift(savedData);
    wx.setStorageSync('savedQuestions', history);
    
    logger.info('详情数据已保存');
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

    // P0 修复：跳转到原始数据页面
    wx.navigateTo({
      url: `/pages/report/raw-data/raw-data?executionId=${this.data.executionId}`
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
   * 导出为 PDF - P1 修复
   */
  exportToPDF: function() {
    if (!this.data.executionId) {
      wx.showToast({
        title: '未找到执行 ID',
        icon: 'none'
      });
      return;
    }
    
    exportToPDF({
      executionId: this.data.executionId,
      includeROI: true,
      includeSources: true
    }).catch(error => {
      wx.showToast({
        title: error.message || '导出失败',
        icon: 'none'
      });
    });
  },

  /**
   * 导出为 Excel - P1 修复
   */
  exportToExcel: function() {
    if (!this.data.executionId) {
      wx.showToast({
        title: '未找到执行 ID',
        icon: 'none'
      });
      return;
    }
    
    exportToExcel({
      executionId: this.data.executionId
    }).catch(error => {
      wx.showToast({
        title: error.message || '导出失败',
        icon: 'none'
      });
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
   * P1 修复：收藏/取消收藏
   */
  toggleFavorite: function() {
    const isFavorite = !this.data.isFavorite;
    const dashboardData = this.data.dashboardData;
    
    logger.info('切换收藏状态', { isFavorite, dashboardData });

    if (isFavorite) {
      // 添加到收藏
      this.addToFavorites(dashboardData);
    } else {
      // 取消收藏
      this.removeFromFavorites(dashboardData);
    }

    this.setData({ isFavorite });
  },

  /**
   * 添加到收藏
   */
  addToFavorites: function(dashboardData) {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      
      // 构建收藏数据对象
      const favoriteItem = {
        executionId: this.data.executionId,
        brandName: dashboardData?.summary?.brandName || '品牌诊断',
        healthScore: dashboardData?.summary?.healthScore || 0,
        sov: dashboardData?.summary?.sov || 0,
        avgSentiment: dashboardData?.summary?.avgSentiment || 0,
        questionCount: dashboardData?.questionCards?.length || 0,
        questions: dashboardData?.questionCards || [],
        createdAt: Date.now(),
        favoritedAt: Date.now(),
        diagnoseTime: this.formatDiagnoseTime(Date.now())
      };

      // 检查是否已存在
      const exists = favorites.some(f => f.executionId === this.data.executionId);
      if (!exists) {
        favorites.push(favoriteItem);
        wx.setStorageSync('favorites', favorites);
        logger.info('添加收藏成功', { executionId: this.data.executionId });
      }

      wx.showToast({
        title: '已加入收藏',
        icon: 'success'
      });
    } catch (error) {
      logger.error('添加收藏失败', error);
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      });
    }
  },

  /**
   * 从收藏中移除
   */
  removeFromFavorites: function(dashboardData) {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      const newFavorites = favorites.filter(
        f => f.executionId !== this.data.executionId
      );
      wx.setStorageSync('favorites', newFavorites);
      logger.info('取消收藏成功', { executionId: this.data.executionId });

      wx.showToast({
        title: '已取消收藏',
        icon: 'success'
      });
    } catch (error) {
      logger.error('取消收藏失败', error);
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      });
    }
  },

  /**
   * 格式化诊断时间
   */
  formatDiagnoseTime: function(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // 今天
    if (diff < 24 * 60 * 60 * 1000) {
      return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
    
    // 昨天
    if (diff < 48 * 60 * 60 * 1000) {
      return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
    
    // 更早
    return `${date.getMonth() + 1}月${date.getDate()}日`;
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
  },

  /**
   * P0 修复：ROI 卡片点击事件 - 跳转到 ROI 详情页
   */
  onROICardTap: function(event) {
    const { roiData, impactScores } = event.detail;
    logger.info('ROI Card tapped', { roiData, impactScores });

    // 保存 ROI 数据到全局存储，供详情页使用
    if (roiData && impactScores) {
      wx.setStorageSync('roi_detail_data', {
        roiData: roiData,
        impactScores: impactScores,
        benchmarks: this.data.defaultBenchmarks,
        executionId: this.data.executionId,
        timestamp: Date.now()
      });
    }

    // 跳转到 ROI 详情页
    wx.navigateTo({
      url: '/pages/report/roi-detail/roi-detail',
      success: () => {
        logger.debug('成功跳转到 ROI 详情页');
      },
      fail: (err) => {
        logger.error('跳转到 ROI 详情页失败', err);
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * P1 修复：工作流阶段切换
   */
  onWorkflowStageToggle: function(event) {
    const { stage } = event.detail;
    logger.debug('工作流阶段切换', { stage });
    this.setData({ expandedWorkflowStage: stage });
  },

  /**
   * 情报流水线加载完成
   */
  onPipelineLoaded: function(event) {
    const { items, stats, metadata } = event.detail;
    logger.info('[Dashboard] 情报流水线加载完成', {
      itemCount: items.length,
      stats,
      metadata
    });
  },

  /**
   * 情报流水线更新
   */
  onPipelineUpdate: function(event) {
    const { items, addedCount } = event.detail;
    logger.info('[Dashboard] 情报流水线更新', {
      totalCount: items.length,
      added: addedCount
    });

    // 更新 dashboard 数据
    this.setData({
      pipelineItems: items,
      pipelineStats: {
        ...this.data.pipelineStats,
        addedCount: addedCount
      }
    });
  },

  /**
   * 情报流水线错误
   */
  onPipelineError: function(event) {
    const { type, error } = event.detail;
    logger.error('[Dashboard] 情报流水线错误', { type, error });

    wx.showToast({
      title: error || '情报加载失败',
      icon: 'none',
      duration: 3000
    });
  },

  /**
   * 情报项点击
   */
  onPipelineItemTap: function(event) {
    const { item } = event.detail;
    logger.info('[Dashboard] 情报项点击', item);

    // 显示详情或执行其他操作
    wx.showToast({
      title: `查看：${item.model}`,
      icon: 'none'
    });
  }
});
