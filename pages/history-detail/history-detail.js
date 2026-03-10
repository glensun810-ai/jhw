// pages/history-detail/history-detail.js
/**
 * 历史记录详情页 - 增强版（整合报告展示）
 *
 * 功能：
 * 1. 完整报告详情展示（整合原报告看板功能）
 * 2. 删除报告
 * 3. 导出/分享报告
 * 4. 重新诊断
 * 5. 收藏/取消收藏
 *
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v3.0 - 产品架构优化版
 */

const { getSavedResults } = require('../../utils/saved-results-sync');
const { exportPdfReport } = require('../../api/export');
const { deleteHistoryReport } = require('../../api/history');
const { clearDiagnosisResult } = require('../../utils/storage-manager');
const logger = require('../../utils/logger');
const navigationService = require('../../services/navigationService');

Page({
  data: {
    // 基础信息
    brandName: '',
    timestamp: 0,
    formattedTime: '',
    executionId: null,
    reportId: null,

    // 评分信息
    overallScore: 0,
    overallGrade: 'D',
    overallSummary: '暂无评价',
    overallAuthority: 0,
    overallVisibility: 0,
    overallPurity: 0,
    overallConsistency: 0,
    gradeClass: 'grade-pending',

    // 核心指标（产品架构优化新增）
    sovShare: 0,
    sentimentScore: 0,
    physicalRank: 0,
    influenceScore: 0,
    hasMetrics: false,

    // 详细数据
    detailedResults: [],
    aiModels: [],
    competitors: [],
    questions: [],

    // 问题诊断墙数据
    highRisks: [],
    mediumRisks: [],
    suggestions: [],

    // 信源列表数据
    sourceList: [],

    // UI 状态
    loading: true,
    showActions: false,
    recordId: null,

    // 【产品架构优化 - 2026-03-10】新增：收藏状态
    isFavorited: false,

    // 【产品架构优化 - 2026-03-10】新增：报告详情数据（整合看板功能）
    dashboardData: null,
    questionCards: [],
    toxicSources: [],
    scoreData: null,
    competitionData: null,
    showShareMenu: false
  },

  onLoad: function(options) {
    // 从参数获取记录 ID 或执行 ID
    const recordId = options.id || null;
    const executionId = options.executionId || null;
    const brandName = options.brandName ? decodeURIComponent(options.brandName) : '';

    if (!recordId && !executionId) {
      wx.showToast({
        title: '缺少记录 ID',
        icon: 'none'
      });
      return;
    }

    this.setData({
      recordId: recordId,
      executionId: executionId || recordId,
      brandName: brandName || '未知品牌',
      loading: true
    });

    // 加载历史记录
    if (executionId) {
      this.loadFromServer(executionId);
    } else {
      this.loadHistoryRecord(recordId);
    }
  },

  // 从服务器加载 - 性能优化版
  loadFromServer: function(executionId) {
    const token = wx.getStorageSync('token');
    
    // 【性能优化 P0】先显示加载状态
    this.setData({ loading: true });

    wx.request({
      url: `${getApp().globalData.serverUrl}/api/test-history`,
      header: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      data: {
        executionId: executionId
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          const record = res.data.records?.[0];
          if (record) {
            // 【性能优化 P0】直接使用返回的数据，不再重复请求
            this.processHistoryDataOptimized(record);
            return;
          }
        }
        // 降级到本地
        this.loadHistoryRecordLocal(executionId);
      },
      fail: (err) => {
        logger.error('加载失败', err);
        // 降级到本地
        this.loadHistoryRecordLocal(executionId);
      }
    });
  },

  // 加载历史记录 - 性能优化版
  loadHistoryRecord: function(recordId) {
    // 【性能优化 P0】使用本地缓存，避免遍历大数组
    this.loadHistoryRecordLocal(recordId);
  },

  // 从本地加载记录 - 优化版
  loadHistoryRecordLocal: function(recordId) {
    const that = this;
    
    // 【性能优化 P0】直接从专用 key 读取，避免遍历
    const key = 'diagnosis_result_' + recordId;
    const record = wx.getStorageSync(key);
    
    if (!record) {
      // 如果专用 key 没有，再尝试从 saved-results 查找
      getSavedResults()
        .then(searchResults => {
          const found = searchResults.find(item =>
            item.id === recordId ||
            item.executionId === recordId ||
            item.result_id === recordId
          );
          
          if (found) {
            that.processHistoryDataOptimized(found);
          } else {
            wx.showToast({ title: '未找到记录', icon: 'none' });
            that.setData({ loading: false });
          }
        })
        .catch(error => {
          console.error('加载历史记录失败', error);
          wx.showToast({ title: '加载失败', icon: 'none' });
          that.setData({ loading: false });
        });
      return;
    }
    
    that.processHistoryDataOptimized(record);
  },

  /**
   * 【架构重构 P0 - 2026-03-11】处理历史数据 - 完全分层加载版本
   * 核心原则：优先使用后端预计算数据；如果未返回，前端计算降级
   */
  processHistoryDataOptimized: function(record) {
    const results = record.results || record.result || record;
    
    // ==================== 第 1 层：核心信息（0ms，直接获取，无需计算）====================
    // 关键：立即显示，解除加载状态
    const overallScore = results.overall_score || results.overallScore || 0;
    const overallGrade = this.calculateGrade(overallScore);
    
    this.setData({
      brandName: record.brandName || record.brand_name || this.data.brandName || '未知品牌',
      overallScore: overallScore,
      overallGrade: overallGrade,
      overallSummary: this.getGradeSummary(overallGrade),
      gradeClass: this.getGradeClass(overallGrade),
      loading: false  // 关键：立即解除加载状态
    });
    
    // ==================== 第 2 层：分析数据（100ms，优先后端预计算，前端降级）====================
    setTimeout(() => {
      try {
        // 【优先】使用后端预计算的评分维度
        let dimensionScores = results.dimension_scores || results.dimensionScores || null;
        
        // 【降级】如果后端未返回，从 detailed_results 计算
        if (!dimensionScores) {
          const detailedResults = results.detailed_results || results.detailedResults || [];
          dimensionScores = this._calculateDimensionScoresFromResults(detailedResults.slice(0, 20));
          console.log('[第 2 层] 后端未返回 dimension_scores，使用前端计算降级');
        } else {
          console.log('[第 2 层] 使用后端预计算 dimension_scores');
        }
        
        // 【优先】使用后端预计算的核心指标
        const exposureAnalysis = results.exposure_analysis || {};
        const brandDetails = exposureAnalysis.brand_details || {};
        const mainBrand = Object.keys(brandDetails)[0] || '';
        const brandData = brandDetails[mainBrand] || {};
        
        // 【优先】使用后端预计算的问题诊断
        let recommendationData = results.recommendation_data || null;
        
        // 【降级】如果后端未返回，使用空数组
        if (!recommendationData) {
          recommendationData = {
            risk_levels: { high: [], medium: [] },
            priority_recommendations: []
          };
          console.log('[第 2 层] 后端未返回 recommendation_data，使用空数据降级');
        } else {
          console.log('[第 2 层] 使用后端预计算 recommendation_data');
        }
        
        const riskLevels = recommendationData.risk_levels || {};
        
        // 【优先】使用后端预计算的信源分析
        const sourceIntelligence = results.source_intelligence || {};
        const sourcePool = sourceIntelligence.source_pool || [];
        
        this.setData({
          // 评分维度（后端预计算或前端计算）
          overallAuthority: dimensionScores.authority || 0,
          overallVisibility: dimensionScores.visibility || 0,
          overallPurity: dimensionScores.purity || 0,
          overallConsistency: dimensionScores.consistency || 0,
          
          // 核心指标（后端预计算）
          sovShare: brandData.sov_share ? Math.round(brandData.sov_share * 100) : 0,
          sentimentScore: brandData.sentiment_score || 0,
          physicalRank: brandData.rank || 0,
          influenceScore: Math.round((
            (dimensionScores.authority || 0) + 
            (dimensionScores.visibility || 0) + 
            (dimensionScores.purity || 0) + 
            (dimensionScores.consistency || 0)
          ) / 4),
          hasMetrics: true,
          
          // 问题诊断（后端预计算或降级）
          highRisks: riskLevels.high || [],
          mediumRisks: riskLevels.medium || [],
          suggestions: recommendationData.priority_recommendations || [],
          
          // 信源分析（后端预计算）
          sourceList: sourcePool.slice(0, 10)
        });
      } catch (error) {
        console.error('[第 2 层] 加载分析数据失败:', error);
        // 容错：设置默认值，不影响其他层
        this.setData({
          overallAuthority: 0,
          overallVisibility: 0,
          overallPurity: 0,
          overallConsistency: 0,
          hasMetrics: false,
          highRisks: [],
          mediumRisks: [],
          suggestions: [],
          sourceList: []
        });
      }
    }, 100);
    
    // ==================== 第 3 层：详细结果（200ms，异步简化）====================
    setTimeout(() => {
      try {
        const detailedResults = results.detailed_results || results.detailedResults || [];
        
        // 异步简化数据（只处理前 5 条）
        const simplifiedResults = detailedResults.slice(0, 5).map((r, index) => ({
          id: r.id || `result_${index}`,
          brand: r.brand || r.brandName,
          model: r.aiModel || r.ai_model || '未知模型',
          score: r.score,
          question: (r.question || '').substring(0, 50),
          response: (r.response || r.answer || '').substring(0, 100),
          truncated: (r.response?.length || r.answer?.length || 0) > 100,
          fullResponse: r.response || r.answer || '',
          expanded: false
        }));
        
        // 保存完整数据到全局变量（用于加载更多）
        const app = getApp();
        if (!app.globalData) app.globalData = {};
        app.globalData.currentReportData = {
          detailedResults: detailedResults,
          executionId: record.executionId || record.result_id || record.id
        };
        
        this.setData({
          // 详细结果（简化，前 5 条）
          detailedResults: simplifiedResults,
          
          // 其他数据（直接获取）
          aiModels: results.ai_models || [],
          competitors: results.competitors || [],
          questions: results.questions || [],
          
          // 分页信息
          hasMoreResults: detailedResults.length > 5,
          totalResults: detailedResults.length
        });
      } catch (error) {
        console.error('[第 3 层] 加载详细结果失败:', error);
        // 容错：设置默认值，不影响其他层
        this.setData({
          detailedResults: [],
          aiModels: [],
          competitors: [],
          questions: [],
          hasMoreResults: false,
          totalResults: 0
        });
      }
    }, 200);
    
    // 最后：收藏状态（600ms，独立获取）
    setTimeout(() => {
      try {
        this.setData({
          isFavorited: this.checkFavoriteStatus(record.executionId || record.result_id || record.id)
        });
      } catch (error) {
        console.error('[收藏状态] 加载失败:', error);
        this.setData({ isFavorited: false });
      }
    }, 600);
  },

  /**
   * 【降级方案】从 detailed_results 计算评分维度
   * 当后端未返回 dimension_scores 时使用
   */
  _calculateDimensionScoresFromResults: function(detailedResults) {
    if (!detailedResults || detailedResults.length === 0) {
      return { authority: 0, visibility: 0, purity: 0, consistency: 0 };
    }

    const total = detailedResults.length;
    let authSum = 0, visSum = 0, purSum = 0, conSum = 0;
    
    for (let i = 0; i < total; i++) {
      const r = detailedResults[i];
      authSum += (r.authority_score || r.authority || 0);
      visSum += (r.visibility_score || r.visibility || 0);
      purSum += (r.purity_score || r.purity || 0);
      conSum += (r.consistency_score || r.consistency || 0);
    }

    return {
      authority: Math.round(authSum / total),
      visibility: Math.round(visSum / total),
      purity: Math.round(purSum / total),
      consistency: Math.round(conSum / total)
    };
  },

  /**
   * 【性能优化 P0】检查收藏状态
   */
  checkFavoriteStatus: function(executionId) {
    if (!executionId) return false;
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      return favorites.some(f => f.executionId === executionId);
    } catch (error) {
      console.error('检查收藏状态失败:', error);
      return false;
    }
  },

  /**
   * 【性能优化 P0 - 2026-03-11】加载更多结果
   */
  loadMoreResults: function() {
    if (!this.data.hasMoreResults) return;

    wx.showLoading({ title: '加载中...' });

    const currentLength = this.data.detailedResults.length;
    const pageSize = 5;
    
    // 从完整数据中获取下一批
    // 注意：这里需要从缓存或全局变量中获取完整数据
    // 简化处理：假设完整数据已经在某个地方
    const allResults = this._getFullDetailedResults();
    const nextResults = allResults.slice(currentLength, currentLength + pageSize);
    
    // 简化数据
    const simplifiedResults = nextResults.map((r, index) => ({
      id: r.id || `result_${currentLength + index}`,
      brand: r.brand || r.brandName,
      model: r.aiModel || r.ai_model || '未知模型',
      score: r.score,
      question: r.question?.substring(0, 50) || '',
      response: r.response?.substring(0, 100) || r.answer?.substring(0, 100) || '',
      truncated: (r.response?.length || 0) > 100 || (r.answer?.length || 0) > 100,
      fullResponse: r.response || r.answer || '',
      expanded: false
    }));

    setTimeout(() => {
      this.setData({
        detailedResults: [...this.data.detailedResults, ...simplifiedResults],
        hasMoreResults: (currentLength + simplifiedResults.length) < this.data.totalResults
      });
      wx.hideLoading();
    }, 300);
  },

  /**
   * 获取完整详细结果（用于分页加载）
   */
  _getFullDetailedResults: function() {
    // 从全局变量或缓存中获取
    const app = getApp();
    if (app.globalData && app.globalData.currentReportData) {
      return app.globalData.currentReportData.detailedResults || [];
    }
    // 如果没有缓存，返回当前数据（简化处理）
    return this.data.detailedResults;
  },

  /**
   * 【性能优化 P0 - 2026-03-11】展开/收起回复
   */
  toggleExpand: function(e) {
    const { id } = e.currentTarget.dataset;
    
    const results = this.data.detailedResults.map(item => {
      if (item.id === id) {
        return { ...item, expanded: !item.expanded };
      }
      return item;
    });
    
    this.setData({ detailedResults: results });
  },

  /**
   * 计算影响力评分
   */
  calculateInfluenceScore: function(dimensionScores) {
    const { authority, visibility, purity, consistency } = dimensionScores;
    return Math.round((authority + visibility + purity + consistency) / 4);
  },

  /**
   * 计算等级
   */
  calculateGrade: function(score) {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'E';
  },

  /**
   * 获取等级描述
   */
  getGradeSummary: function(grade) {
    const summaries = {
      'A': '表现优秀',
      'B': '表现良好',
      'C': '表现中等',
      'D': '有待改进',
      'E': '需要加强'
    };
    return summaries[grade] || '暂无评价';
  },

  /**
   * 获取等级样式类
   */
  getGradeClass: function(grade) {
    const classes = {
      'A': 'grade-excellent',
      'B': 'grade-good',
      'C': 'grade-fair',
      'D': 'grade-poor',
      'E': 'grade-pending'
    };
    return classes[grade] || 'grade-pending';
  },

  /**
   * 【产品架构优化 - 2026-03-10】切换收藏状态
   */
  toggleFavorite: function() {
    const { isFavorited, executionId, brandName, overallScore } = this.data;
    
    if (isFavorited) {
      this.removeFavorite();
    } else {
      this.addFavorite();
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】添加收藏
   */
  addFavorite: function() {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      
      // 检查是否已存在
      const exists = favorites.some(f => f.executionId === this.data.executionId);
      if (exists) {
        wx.showToast({ title: '已在收藏中', icon: 'none' });
        return;
      }
      
      favorites.unshift({
        executionId: this.data.executionId,
        brandName: this.data.brandName,
        favoritedAt: Date.now(),
        timestamp: Date.now(),
        overallScore: this.data.overallScore
      });
      
      wx.setStorageSync('favorites', favorites);
      this.setData({ isFavorited: true });
      
      wx.showToast({ title: '收藏成功', icon: 'success' });
    } catch (error) {
      console.error('添加收藏失败:', error);
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】移除收藏
   */
  removeFavorite: function() {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      const filtered = favorites.filter(f => f.executionId !== this.data.executionId);
      wx.setStorageSync('favorites', filtered);
      this.setData({ isFavorited: false });
      
      wx.showToast({ title: '已取消收藏', icon: 'success' });
    } catch (error) {
      console.error('取消收藏失败:', error);
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  // 切换操作菜单
  toggleActions: function() {
    this.setData({
      showActions: !this.data.showActions
    });
  },

  // 删除报告
  onDeleteReport: function() {
    const { executionId, reportId, brandName } = this.data;
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除"${brandName}"的诊断报告吗？此操作不可恢复。`,
      confirmText: '删除',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' });
          
          try {
            // 调用删除 API
            if (reportId) {
              await deleteHistoryReport(executionId, reportId);
            }
            
            // 清除本地缓存
            clearDiagnosisResult(executionId);
            
            wx.hideLoading();
            
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            });
            
            // 返回历史列表
            setTimeout(() => {
              wx.navigateBack();
            }, 1500);
            
          } catch (error) {
            console.error('删除失败:', error);
            wx.hideLoading();
            wx.showToast({
              title: '删除失败，请重试',
              icon: 'none'
            });
          }
        }
      }
    });
  },

  // 导出报告
  onExportReport: function() {
    if (!this.data.executionId) {
      wx.showToast({
        title: '无法生成报告',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '正在生成报告...',
      mask: true
    });

    exportPdfReport({
      executionId: this.data.executionId
    })
    .then(() => {
      wx.hideLoading();
      wx.showToast({
        title: '报告已保存',
        icon: 'success'
      });
    })
    .catch(error => {
      wx.hideLoading();
      wx.showToast({
        title: error.message || '生成失败',
        icon: 'none'
      });
    });
  },

  // 重新诊断
  onReDiagnose: function() {
    const { brandName, competitors } = this.data;
    
    // 跳转到诊断页面，带上品牌信息
    wx.navigateTo({
      url: `/pages/index/index?brandName=${encodeURIComponent(brandName)}&competitors=${encodeURIComponent(JSON.stringify(competitors))}`
    });
  },

  // 分享
  onShareAppMessage: function() {
    const { brandName, overallScore } = this.data;
    return {
      title: `${brandName} AI 诊断报告 - 得分${overallScore}`,
      path: `/pages/history-detail/history-detail?executionId=${this.data.executionId}`
    };
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({ url: '/pages/index/index' });
  },

  // 查看历史
  viewHistory: function() {
    wx.navigateBack();
  },

  /**
   * 【产品架构优化 - 2026-03-10】加载收藏状态
   */
  loadFavoriteStatus: function() {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      const isFavorited = favorites.some(f => f.executionId === this.data.executionId);
      this.setData({ isFavorited });
    } catch (error) {
      console.error('加载收藏状态失败:', error);
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】切换收藏
   */
  toggleFavorite: function() {
    const { isFavorited, executionId, brandName } = this.data;
    
    if (isFavorited) {
      this.removeFavorite();
    } else {
      this.addFavorite();
    }
  },

  /**
   * 【产品架构优化 - 2026-03-10】添加收藏
   */
  addFavorite: function() {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      
      favorites.unshift({
        executionId: this.data.executionId,
        brandName: this.data.brandName,
        favoritedAt: Date.now(),
        timestamp: Date.now(),
        overallScore: this.data.overallScore
      });
      
      wx.setStorageSync('favorites', favorites);
      this.setData({ isFavorited: true });
      
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
  removeFavorite: function() {
    try {
      const favorites = wx.getStorageSync('favorites') || [];
      const filtered = favorites.filter(f => f.executionId !== this.data.executionId);
      wx.setStorageSync('favorites', filtered);
      this.setData({ isFavorited: false });
      
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
  },

  /**
   * 【产品架构优化 - 2026-03-10】加载完整报告数据
   */
  loadFullReportData: function(executionId) {
    const token = wx.getStorageSync('token');
    
    wx.request({
      url: `${getApp().globalData.serverUrl}/api/test-history`,
      header: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      data: { executionId },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          const record = res.data.records?.[0];
          if (record) {
            this.processReportData(record);
          }
        }
      },
      fail: (err) => {
        logger.error('加载报告数据失败', err);
      }
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】处理报告数据
   */
  processReportData: function(record) {
    const results = record.results || record.result || record;
    
    this.setData({
      dashboardData: results.dashboard || {},
      questionCards: results.questions || [],
      toxicSources: results.sources || [],
      scoreData: results.scores || {},
      competitionData: results.competition || {},
      detailedResults: results.detailed_results || [],
      aiModels: results.ai_models || [],
      competitors: results.competitors || [],
      questions: results.questions || []
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】切换分享菜单
   */
  toggleShareMenu: function() {
    this.setData({
      showShareMenu: !this.data.showShareMenu
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】导出报告
   */
  onExportReport: function() {
    wx.showActionSheet({
      itemList: ['导出为 PDF', '导出为图片', '导出为 Excel'],
      success: (res) => {
        wx.showLoading({ title: '导出中...' });
        setTimeout(() => {
          wx.hideLoading();
          wx.showToast({
            title: '导出功能开发中',
            icon: 'none'
          });
        }, 1000);
      }
    });
  },

  /**
   * 【产品架构优化 - 2026-03-10】重新诊断
   */
  onReDiagnose: function() {
    const { brandName, competitors } = this.data;
    navigationService.navigateToHome();
  }
});
