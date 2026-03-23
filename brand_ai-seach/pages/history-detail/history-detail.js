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
const { clearDiagnosisResult, loadDiagnosisResult, StorageKey } = require('../../utils/storage-manager');
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
    showShareMenu: false,

    // 【P21 关键修复 - 2026-03-15】新增：真实数据标志（用于弱视觉效果）
    hasRealData: false,
    hasRealDimensionScores: false,
    hasRealMetrics: false,
    hasRealRecommendations: false,
    hasRealSources: false,
    hasRealResults: false
  },

  onLoad: function(options) {
    // 【调试 P0】添加参数日志
    console.log('[报告详情页] onLoad 执行，options:', options);

    // 从参数获取执行 ID
    const executionId = options.executionId;
    const brandName = options.brandName ? decodeURIComponent(options.brandName) : '';

    // 【调试 P0】添加 ID 日志
    console.log('[报告详情页] executionId:', executionId, 'brandName:', brandName);

    if (!executionId) {
      console.error('[报告详情页] ❌ 缺少 executionId!');
      wx.showToast({
        title: '缺少执行 ID',
        icon: 'none'
      });
      return;
    }

    // 【第 30 次修复 - 2026-03-17】直接从 API 加载，不使用缓存
    // 原因：缓存数据结构不匹配，导致"命中但无数据展示"
    console.log('[报告详情页] 开始从 API 加载数据，loading=true');

    this.setData({
      executionId: executionId,
      brandName: brandName || '未知品牌',
      loading: true
    });

    // 从服务器加载数据
    this.loadFromServer(executionId);
  },

  /**
   * 【首席工程师修复 - 2026-03-15】立即展示页面
   * 核心原则：无论是否有数据，先展示页面框架，再异步加载数据
   * @param {Object|null} record - 诊断记录数据
   */
  _immediateShowPage: function(record) {
    // 立即解除 loading
    this.setData({ loading: false });
    console.log('[首席工程师修复] _immediateShowPage: loading=false，页面立即展示');
    
    // 处理数据
    this.processHistoryDataOptimized(record);
  },

  /**
   * 从服务器加载数据（第 30 次修复 - 简化版）
   * @param {string} executionId - 执行 ID
   */
  loadFromServer: function(executionId) {
    const token = wx.getStorageSync('token');
    const serverUrl = getApp().globalData.serverUrl;

    console.log('[报告详情页] loadFromServer 执行，executionId:', executionId);

    if (!serverUrl) {
      console.error('[报告详情页] ❌ serverUrl 未配置');
      this.setData({ loading: false });
      wx.showModal({
        title: '配置错误',
        content: '服务器地址未配置，请联系管理员',
        showCancel: false
      });
      return;
    }

    wx.request({
      url: `${serverUrl}/api/diagnosis/report/${executionId}`,
      header: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      timeout: 10000,
      method: 'GET',
      responseType: 'text',
      success: (res) => {
        console.log('[报告详情页] API 响应:', {
          statusCode: res.statusCode,
          hasData: !!res.data,
          dataKeys: res.data ? Object.keys(res.data) : []
        });

        if (res.statusCode === 200 && res.data?.data) {
          // API 返回格式：{success: true, data: {...}}
          const report = res.data.data;
          console.log('[报告详情页] ✅ 数据加载成功');
          this.displayReport(report);
        } else if (res.statusCode === 404) {
          console.error('[报告详情页] ❌ 报告不存在:', executionId);
          this.setData({ loading: false });
          wx.showModal({
            title: '报告不存在',
            content: '该诊断报告可能已被删除或从未生成',
            showCancel: false,
            success: () => wx.navigateBack()
          });
        } else if (res.statusCode === 401) {
          console.error('[报告详情页] ❌ 认证失败');
          this.setData({ loading: false });
          wx.showModal({
            title: '认证失败',
            content: '登录已过期，请重新登录',
            success: () => wx.navigateBack()
          });
        } else {
          console.error('[报告详情页] ❌ 服务器错误:', res.statusCode);
          this.setData({ loading: false });
          wx.showModal({
            title: '加载失败',
            content: `服务器错误 (${res.statusCode})`,
            showCancel: false
          });
        }
      },
      fail: (err) => {
        console.error('[报告详情页] ❌ 网络错误:', err);
        this.setData({ loading: false });
        wx.showModal({
          title: '网络错误',
          content: '无法连接服务器，请检查网络连接',
          showCancel: false
        });
      }
    });
  },

  /**
   * 展示报告数据（第 32 次修复 - 彻底修复版）
   * @param {Object} report - 报告数据
   */
  displayReport: function(report) {
    console.log('[报告详情页] displayReport 执行', report ? '有数据' : '无数据');

    // 【P0 性能修复 - 2026-03-22】立即解除 loading，防止卡死
    this.setData({ loading: false });

    // 处理详细结果数据
    const results = report.results || report.detailedResults || [];
    
    // 【关键修复】保存完整数据到全局变量（用于加载更多），不放入 setData
    const app = getApp();
    if (!app.globalData) app.globalData = {};
    app.globalData.currentReportData = {
      executionId: report.executionId || report.report?.execution_id,
      totalResults: results.length,
      fullResults: results,
      metrics: report.metrics || {},
      dimensionScores: report.dimension_scores || {},
      diagnosticWall: report.diagnosticWall || {}
    };

    // 【性能优化】只计算前 5 条用于展示，不包含_raw 引用
    const initialResults = results.slice(0, 5).map((r, index) => {
      const score = r.score || r.qualityScore || r.quality_score || 85;
      let scoreClass = 'poor';
      if (score >= 80) scoreClass = 'excellent';
      else if (score >= 60) scoreClass = 'good';

      // 【关键修复】安全提取 response 文本，处理对象和字符串两种情况
      let responseText = '';
      if (r.responseContent) {
        responseText = typeof r.responseContent === 'string' ? r.responseContent : (r.responseContent.content || JSON.stringify(r.responseContent));
      } else if (r.response_content) {
        responseText = typeof r.response_content === 'string' ? r.response_content : (r.response_content.content || JSON.stringify(r.response_content));
      } else if (r.response) {
        responseText = typeof r.response === 'string' ? r.response : (r.response.content || JSON.stringify(r.response));
      }

      // 【关键修复】安全提取 question 文本
      let questionText = r.question || '';
      if (typeof questionText !== 'string') {
        questionText = JSON.stringify(questionText);
      }

      return {
        id: r.id || `result_${index}`,
        brand: r.brand || r.extractedBrand || r.extracted_brand || '未知品牌',
        model: r.model || r.platform || '未知模型',
        platform: r.platform || r.model || '',
        score: score,
        scoreClass: scoreClass,
        question: questionText.substring(0, 50),
        response: responseText.substring(0, 100),
        truncated: responseText.length > 100,
        fullResponse: responseText,
        expanded: false
      };
    });

    // 计算综合评分
    const metrics = report.metrics || {};
    const dimensionScores = report.dimension_scores || {};
    const qualityScore = metrics.influence || report.validation?.qualityScore || report.qualityHints?.qualityScore ||
                        report.overall_score || 75;
    const overallScore = qualityScore > 1 ? qualityScore : qualityScore * 100;

    // 【分层加载 P1】第 1 层：核心信息（立即加载）
    this.setData({
      // 核心信息
      brandName: report.brandName || report.report?.brand_name || this.data.brandName || '未知品牌',
      overallScore: overallScore,
      overallGrade: this.calculateGrade(overallScore),
      overallSummary: this.getGradeSummary(this.calculateGrade(overallScore)),
      gradeClass: this.getGradeClass(this.calculateGrade(overallScore)),

      // 详细结果（前 5 条）
      detailedResults: initialResults,
      hasMoreResults: results.length > 5,
      totalResults: results.length,

      // 诊断信息
      hasRealData: true,
      hasRealResults: results.length > 0
    });

    console.log('[报告详情页] ✅ 第 1 层：核心信息已加载');

    // 【分层加载 P2】第 2 层：分析数据（100ms 延迟）
    setTimeout(() => {
      try {
        this.setData({
          // 分析数据
          brandDistribution: report.brandDistribution || {},
          sentimentDistribution: report.sentimentDistribution || {},
          keywords: report.keywords || [],

          // 核心指标
          sovShare: metrics.sov || 0,
          sentimentScore: metrics.sentiment || 0,
          physicalRank: metrics.rank || 1,
          influenceScore: metrics.influence || 0,
          hasMetrics: true,

          // 评分维度
          overallAuthority: dimensionScores.authority || 50,
          overallVisibility: dimensionScores.visibility || 50,
          overallPurity: dimensionScores.purity || 50,
          overallConsistency: dimensionScores.consistency || 50,
          hasRealDimensionScores: true
        });
        console.log('[报告详情页] ✅ 第 2 层：分析数据已加载');
      } catch (error) {
        console.error('[报告详情页] ❌ 第 2 层加载失败:', error);
      }
    }, 100);

    // 【分层加载 P3】第 3 层：问题诊断墙（200ms 延迟）
    setTimeout(() => {
      try {
        this.setData({
          // 问题诊断墙
          highRisks: report.diagnosticWall?.risk_levels?.high || [],
          mediumRisks: report.diagnosticWall?.risk_levels?.medium || [],
          suggestions: report.diagnosticWall?.priority_recommendations || [],
          hasRealRecommendations: true
        });
        console.log('[报告详情页] ✅ 第 3 层：问题诊断墙已加载');
      } catch (error) {
        console.error('[报告详情页] ❌ 第 3 层加载失败:', error);
      }
    }, 200);

    console.log('[报告详情页] ✅ 数据展示完成', {
      brandName: this.data.brandName,
      detailedResults: initialResults.length,
      totalResults: results.length,
      hasMoreResults: results.length > 5
    });
  },

  /**
   * 【P0 关键修复 - 2026-03-13】从 API 处理历史数据
   * 用于处理从 /api/diagnosis/report/{executionId} 返回的完整报告数据
   */
  processHistoryDataFromApi: function(report) {
    // 【紧急修复 - 2026-03-15】立即解除 loading，防止卡死
    this.setData({ loading: false });
    console.log('[紧急修复] processHistoryDataFromApi: loading=false');

    // 【P0 修复 - 2026-03-15】提取数据，避免循环引用
    const results = report.results || report.detailedResults || [];
    const brandDistribution = report.brandDistribution || {};
    const sentimentDistribution = report.sentimentDistribution || {};
    const analysis = report.analysis || {};
    const validation = report.validation || {};

    // ==================== 第 1 层：核心信息====================
    const overallScore = report.overallScore || validation.quality_score || 0;
    const overallGrade = this.calculateGrade(overallScore);

    this.setData({
      brandName: report.brandName || report.report?.brand_name || this.data.brandName || '未知品牌',
      overallScore: overallScore,
      overallGrade: overallGrade,
      overallSummary: this.getGradeSummary(overallGrade),
      gradeClass: this.getGradeClass(overallGrade)
    });

    // ==================== 第 2 层：分析数据====================
    setTimeout(() => {
      try {
        // 从 API 返回的数据中获取评分维度
        const dimensionScores = analysis.dimension_scores || validation.dimension_scores || {};

        // 获取品牌分布
        const brandDistData = brandDistribution.data || {};
        const brandList = Object.keys(brandDistData);
        const mainBrand = brandList[0] || '';

        // 获取情感分布
        const sentimentData = sentimentDistribution.data || {};

        this.setData({
          // 评分维度
          overallAuthority: dimensionScores.authority || 0,
          overallVisibility: dimensionScores.visibility || 0,
          overallPurity: dimensionScores.purity || 0,
          overallConsistency: dimensionScores.consistency || 0,

          // 核心指标
          sovShare: brandDistribution.total_count || 0,
          sentimentScore: sentimentData.positive || 0,
          hasMetrics: true,

          // 问题诊断（从 recommendation_data 获取）
          highRisks: report.recommendationData?.risk_levels?.high || [],
          mediumRisks: report.recommendationData?.risk_levels?.medium || [],
          suggestions: report.recommendationData?.priority_recommendations || [],

          // 信源分析
          sourceList: report.sourceIntelligence?.source_pool?.slice(0, 10) || []
        });
      } catch (error) {
        console.error('[第 2 层] 加载分析数据失败:', error);
        this.setData({
          overallAuthority: 0,
          overallVisibility: 0,
          overallPurity: 0,
          overallConsistency: 0,
          hasMetrics: false
        });
      }
    }, 100);

    // ==================== 第 3 层：详细结果====================
    setTimeout(() => {
      try {
        // 【P0 修复 - 2026-03-15】确保 results 是数组
        if (!Array.isArray(results)) {
          console.error('[第 3 层] results 不是数组，降级处理');
          this.setData({
            detailedResults: [],
            aiModels: report.aiModels || [],
            competitors: report.competitors || [],
            questions: report.questions || [],
            hasMoreResults: false,
            totalResults: 0
          });
          return;
        }

        // 【性能优化 P0 - 2026-03-11】预先计算 scoreClass
        // 【修复 - 2026-03-20】保存完整数据到全局变量，支持"加载更多"功能
        const app = getApp();
        if (!app.globalData) app.globalData = {};

        // 保存完整结果到全局变量（用于加载更多）
        app.globalData.currentReportData = {
          executionId: report.executionId || report.id,
          totalResults: results.length,
          fullResults: results  // 【修复关键】保存完整数据
        };

        // 初始只显示前 5 条（性能优化）
        const initialCount = Math.min(5, results.length);
        const simplifiedResults = results.slice(0, initialCount).map((r, index) => {
          const score = r.score || r.quality_score || 0;
          let scoreClass = 'poor';
          if (score >= 80) scoreClass = 'excellent';
          else if (score >= 60) scoreClass = 'good';

          // 【P0 关键修复 - 2026-03-22】安全提取 response 和 question 文本
          let responseText = '';
          if (r.response_content) {
            responseText = typeof r.response_content === 'string' ? r.response_content : (r.response_content.content || JSON.stringify(r.response_content));
          } else if (r.response) {
            responseText = typeof r.response === 'string' ? r.response : (r.response.content || JSON.stringify(r.response));
          }
          
          let questionText = r.question || '';
          if (typeof questionText !== 'string') {
            questionText = JSON.stringify(questionText);
          }

          return {
            id: r.id || `result_${index}`,
            brand: r.brand || r.extracted_brand || '未知品牌',
            model: r.model || '未知模型',
            score: score,
            scoreClass: scoreClass,
            question: questionText.substring(0, 50),
            response: responseText.substring(0, 100),
            truncated: responseText.length > 100,
            fullResponse: responseText,
            expanded: false
          };
        });

        this.setData({
          detailedResults: simplifiedResults,
          aiModels: report.aiModels || [],
          competitors: report.competitors || [],
          questions: report.questions || [],
          hasMoreResults: results.length > 5,
          totalResults: results.length
        });
      } catch (error) {
        console.error('[第 3 层] 加载详细结果失败:', error);
        this.setData({
          detailedResults: [],
          hasMoreResults: false,
          totalResults: 0
        });
      }
    }, 200);

    // 最后：收藏状态
    setTimeout(() => {
      this.setData({
        isFavorited: this.checkFavoriteStatus(report.executionId || report.id)
      });
    }, 600);
  },

  // 加载历史记录 - 性能优化版
  loadHistoryRecord: function(recordId) {
    // 【性能优化 P0】使用本地缓存，避免遍历大数组
    this.loadHistoryRecordLocal(recordId);
  },

  // 从本地加载记录 - 优化版
  loadHistoryRecordLocal: function(recordId) {
    const that = this;

    // 【调试 P0】添加加载日志
    console.log('[第 2 层] 从本地加载:', recordId);

    // 【性能优化 P0】使用 storage-manager 统一方法加载
    const record = loadDiagnosisResult(recordId);

    // 【调试 P0】添加缓存检查日志
    console.log('[第 2 层] 本地缓存:', record ? '有' : '无');

    if (!record) {
      // 【P0 修复 - 2026-03-15】直接从 saved-results 查找，不使用 Promise
      console.log('[第 2 层] 尝试从 saved-results 查找');

      try {
        // 同步获取 saved-results
        const searchResults = wx.getStorageSync('savedSearchResults') || [];
        const found = searchResults.find(item =>
          item.id === recordId ||
          item.executionId === recordId ||
          item.result_id === recordId
        );

        if (found) {
          console.log('[第 2 层] 找到记录，开始处理');
          that.processHistoryDataOptimized(found);
        } else {
          console.warn('[第 2 层] 未找到记录');
          wx.showToast({ title: '未找到记录', icon: 'none' });
          that.setData({ loading: false });
        }
      } catch (error) {
        console.error('[第 2 层] 加载历史记录失败', error);
        wx.showToast({ title: '加载失败', icon: 'none' });
        that.setData({ loading: false });
      }
      return;
    }

    console.log('[第 2 层] 从专用 key 加载成功');
    that.processHistoryDataOptimized(record);
  },

  /**
   * 【架构重构 P0 - 2026-03-11】处理历史数据 - 完全分层加载版本
   * 核心原则：优先使用后端预计算数据；如果未返回，前端计算降级
   * 【首席工程师修复 - 2026-03-15】无论是否有数据，都立即展示页面
   */
  processHistoryDataOptimized: function(record) {
    console.log('[processHistoryDataOptimized] 开始处理数据，record:', record ? '有数据' : '无数据');

    // 【首席工程师修复 - 2026-03-15】即使 record 为空，也要展示页面（使用默认值）
    if (!record) {
      console.warn('[报告详情页] ⚠️ record 为空，使用默认值展示页面');
      this._loadCoreInfo({}, {});
      this._loadAnalysisData({}, {});
      this._loadDetailedResults({}, {});
      this._loadFavoriteStatus({});
      return;
    }

    // 提取 results 数据
    const results = record.results || record.result || null;

    // 【首席工程师修复 - 2026-03-15】即使 results 为空，也要继续加载（使用默认值）
    if (!results) {
      console.warn('[报告详情页] ⚠️ results 为空，使用默认值继续加载');
      this._loadCoreInfo(record, {});
      this._loadAnalysisData(record, {});
      this._loadDetailedResults(record, {});
      this._loadFavoriteStatus(record);
      return;
    }

    console.log('[报告详情页] 开始分层加载数据');

    // ==================== 第 1 层：核心信息（0ms，直接获取）====================
    this._loadCoreInfo(record, results);

    // ==================== 第 2 层：分析数据（100ms 延迟）====================
    setTimeout(() => {
      this._loadAnalysisData(record, results);
    }, 100);

    // ==================== 第 3 层：详细结果（200ms 延迟）====================
    setTimeout(() => {
      this._loadDetailedResults(record, results);
    }, 200);

    // ==================== 第 4 层：收藏状态（300ms 延迟）====================
    setTimeout(() => {
      this._loadFavoriteStatus(record);
    }, 300);
  },

  /**
   * 【P0 修复 - 2026-03-15】加载核心信息
   * 【首席工程师修复 - 2026-03-15】确保任何诊断记录都能正常打开，无数据时显示默认值
   */
  _loadCoreInfo: function(record, results) {
    // 【首席工程师修复】确保 results 是对象，避免 undefined 错误
    const resultsObj = results || {};
    const overallScore = resultsObj.overall_score || resultsObj.overallScore || 0;
    const overallGrade = this.calculateGrade(overallScore);

    // 【P21 关键修复】格式化时间
    const now = new Date();
    const formattedTime = now.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });

    console.log('[报告详情页] 第 1 层：overallScore=', overallScore, 'overallGrade=', overallGrade);

    this.setData({
      brandName: record.brandName || record.brand_name || this.data.brandName || '未知品牌',
      overallScore: overallScore,
      overallGrade: overallGrade,
      overallSummary: this.getGradeSummary(overallGrade),
      gradeClass: this.getGradeClass(overallGrade),
      formattedTime: formattedTime,  // 【P21 关键修复】设置格式化时间
      // 【P21 关键修复】标记是否有真实数据
      hasRealData: !!(resultsObj && (resultsObj.overall_score || resultsObj.overallScore))
    });

    console.log('[报告详情页] 第 1 层加载完成');
  },

  /**
   * 【P0 修复 - 2026-03-15】加载分析数据
   * 【P21 关键修复 - 2026-03-15】无真实数据时显示默认值，并标记为弱视觉效果
   */
  _loadAnalysisData: function(record, results) {
    try {
      // 【P21 关键修复】确保 results 和 record 是对象，避免 undefined 错误
      const resultsObj = results || {};
      const recordObj = record || {};

      // 【优先】使用后端预计算的评分维度
      let dimensionScores = resultsObj.dimension_scores || resultsObj.dimensionScores || null;

      // 【降级】如果后端未返回，从 detailed_results 计算
      if (!dimensionScores) {
        const detailedResults = resultsObj.detailed_results || resultsObj.detailedResults || [];
        // 【P0 修复】限制计算数量，防止大量数据
        dimensionScores = this._calculateDimensionScoresFromResults(detailedResults.slice(0, 20));
        console.log('[第 2 层] 后端未返回 dimension_scores，使用前端计算降级');
      } else {
        console.log('[第 2 层] 使用后端预计算 dimension_scores');
      }

      // 【优先】使用后端预计算的核心指标
      const exposureAnalysis = resultsObj.exposure_analysis || {};
      const brandDetails = exposureAnalysis.brand_details || {};
      const mainBrand = Object.keys(brandDetails)[0] || '';
      const brandData = brandDetails[mainBrand] || {};

      // 【优先】使用后端预计算的问题诊断
      let recommendationData = resultsObj.recommendation_data || null;

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
      const sourceIntelligence = resultsObj.source_intelligence || {};
      const sourcePool = sourceIntelligence.source_pool || [];

      // 【P21 关键修复】标记是否有真实数据（用于弱视觉效果）
      const hasRealDimensionScores = !!(resultsObj.dimension_scores || resultsObj.dimensionScores);
      const hasRealMetrics = !!(resultsObj.exposure_analysis && brandData.sov_share);
      const hasRealRecommendations = !!recommendationData && (riskLevels.high?.length > 0 || riskLevels.medium?.length > 0);
      const hasRealSources = sourcePool.length > 0;

      this.setData({
        // 评分维度（后端预计算或前端计算或默认值）
        overallAuthority: dimensionScores.authority || 0,
        overallVisibility: dimensionScores.visibility || 0,
        overallPurity: dimensionScores.purity || 0,
        overallConsistency: dimensionScores.consistency || 0,
        // 【P21 关键修复】标记哪些是真实数据（用于弱视觉效果）
        hasRealDimensionScores: hasRealDimensionScores,

        // 核心指标（后端预计算或默认值）
        sovShare: brandData.sov_share ? Math.round(brandData.sov_share * 100) : 0,
        sentimentScore: brandData.sentiment_score || 0,
        physicalRank: brandData.rank || 0,
        influenceScore: Math.round((
          (dimensionScores.authority || 0) +
          (dimensionScores.visibility || 0) +
          (dimensionScores.purity || 0) +
          (dimensionScores.consistency || 0)
        ) / 4),
        // 【P21 关键修复】标记哪些是真实数据（用于弱视觉效果）
        hasRealMetrics: hasRealMetrics,

        // 问题诊断（后端预计算或降级）
        highRisks: riskLevels.high || [],
        mediumRisks: riskLevels.medium || [],
        suggestions: recommendationData.priority_recommendations || [],
        hasRealRecommendations: hasRealRecommendations,

        // 信源分析（后端预计算或默认值）
        sourceList: sourcePool.slice(0, 10),
        hasRealSources: hasRealSources
      });

      console.log('[第 2 层] 加载完成:', {
        hasRealDimensionScores,
        hasRealMetrics,
        hasRealRecommendations,
        hasRealSources
      });
    } catch (error) {
      console.error('[第 2 层] 加载分析数据失败:', error);
      // 容错：设置默认值，不影响其他层
      this.setData({
        overallAuthority: 0,
        overallVisibility: 0,
        overallPurity: 0,
        overallConsistency: 0,
        hasRealDimensionScores: false,
        hasMetrics: false,
        highRisks: [],
        mediumRisks: [],
        suggestions: [],
        sourceList: [],
        hasRealRecommendations: false,
        hasRealSources: false
      });
    }
  },

  /**
   * 【P0 修复 - 2026-03-15】加载详细结果
   * 【P21 关键修复 - 2026-03-15】无数据时显示默认值，标记为弱视觉效果
   */
  _loadDetailedResults: function(record, results) {
    try {
      // 【P21 关键修复】确保 results 是对象
      const resultsObj = results || {};
      const detailedResults = resultsObj.detailed_results || resultsObj.detailedResults || [];

      // 【P21 关键修复】标记是否有真实数据
      const hasRealResults = Array.isArray(detailedResults) && detailedResults.length > 0;

      // 【P0 修复 - 2026-03-15】确保 detailedResults 是数组，并且限制处理数量
      if (!Array.isArray(detailedResults) || detailedResults.length === 0) {
        console.log('[第 3 层] 无详细结果数据，使用默认值');
        this.setData({
          detailedResults: [],
          aiModels: [],
          competitors: [],
          questions: [],
          hasMoreResults: false,
          totalResults: 0,
          hasRealResults: false  // 【P21 关键修复】标记无真实数据
        });
        return;
      }

      // 【性能优化 P0 - 2026-03-11】预先计算 scoreClass，避免 WXML 中三元表达式
      // 【修复 - 2026-03-20】保存完整数据到全局变量，支持"加载更多"功能
      const app = getApp();
      if (!app.globalData) app.globalData = {};
      
      // 保存完整结果到全局变量（用于加载更多）
      app.globalData.currentReportData = {
        executionId: record.executionId || record.result_id || record.id,
        totalResults: detailedResults.length,
        fullResults: detailedResults  // 【修复关键】保存完整数据
      };

      // 初始只显示前 5 条（性能优化）
      const initialCount = Math.min(5, detailedResults.length);
      const simplifiedResults = detailedResults.slice(0, initialCount).map((r, index) => {
        // 预先计算 scoreClass
        let scoreClass = 'poor';
        if (r.score >= 80) scoreClass = 'excellent';
        else if (r.score >= 60) scoreClass = 'good';

        // 【P0 关键修复 - 2026-03-22】安全提取 response 和 question 文本
        let responseText = '';
        if (r.response) {
          responseText = typeof r.response === 'string' ? r.response : (r.response.content || JSON.stringify(r.response));
        } else if (r.answer) {
          responseText = typeof r.answer === 'string' ? r.answer : (r.answer.content || JSON.stringify(r.answer));
        }
        
        let questionText = r.question || '未知问题';
        if (typeof questionText !== 'string') {
          questionText = JSON.stringify(questionText);
        }

        return {
          id: r.id || `result_${index}`,
          brand: r.brand || r.brandName,
          model: r.aiModel || r.ai_model || '未知模型',
          score: r.score || 0,  // 【P21 关键修复】确保 score 有默认值
          scoreClass: scoreClass,  // ✅ 预先计算，WXML 直接使用
          question: questionText.substring(0, 50),
          response: responseText.substring(0, 100),
          truncated: responseText.length > 100,
          fullResponse: responseText,
          expanded: false
        };
      });

      this.setData({
        // 详细结果（简化，前 5 条）
        detailedResults: simplifiedResults,

        // 其他数据（直接获取）
        aiModels: resultsObj.ai_models || [],
        competitors: resultsObj.competitors || [],
        questions: resultsObj.questions || [],

        // 分页信息
        hasMoreResults: detailedResults.length > 5,
        totalResults: detailedResults.length,
        // 【P21 关键修复】标记是否有真实数据
        hasRealResults: hasRealResults
      });

      console.log('[第 3 层] 加载完成:', {
        count: simplifiedResults.length,
        hasRealResults: hasRealResults
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
        totalResults: 0,
        hasRealResults: false  // 【P21 关键修复】标记无真实数据
      });
    }
  },

  /**
   * 【P0 修复 - 2026-03-15】加载收藏状态
   */
  _loadFavoriteStatus: function(record) {
    try {
      this.setData({
        isFavorited: this.checkFavoriteStatus(record.executionId || record.result_id || record.id)
      });
    } catch (error) {
      console.error('[收藏状态] 加载失败:', error);
      this.setData({ isFavorited: false });
    }
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
   * 【修复 - 2026-03-20】修复加载更多功能，确保可以加载所有结果
   */
  loadMoreResults: function() {
    if (!this.data.hasMoreResults) return;

    wx.showLoading({ title: '加载中...' });

    const currentLength = this.data.detailedResults.length;
    const pageSize = 5;

    // 【修复关键】从全局变量获取完整数据
    const allResults = this._getFullDetailedResults();
    const nextResults = allResults.slice(currentLength, currentLength + pageSize);

    // 简化数据
    const simplifiedResults = nextResults.map((r, index) => {
      // 预先计算 scoreClass
      let scoreClass = 'poor';
      const score = r.score || 0;
      if (score >= 80) scoreClass = 'excellent';
      else if (score >= 60) scoreClass = 'good';

      // 【P0 关键修复 - 2026-03-22】安全提取 response 和 question 文本
      let responseText = '';
      if (r.response) {
        responseText = typeof r.response === 'string' ? r.response : (r.response.content || JSON.stringify(r.response));
      } else if (r.answer) {
        responseText = typeof r.answer === 'string' ? r.answer : (r.answer.content || JSON.stringify(r.answer));
      } else if (r.response_content) {
        responseText = typeof r.response_content === 'string' ? r.response_content : (r.response_content.content || JSON.stringify(r.response_content));
      }
      
      let questionText = r.question || '未知问题';
      if (typeof questionText !== 'string') {
        questionText = JSON.stringify(questionText);
      }

      return {
        id: r.id || `result_${currentLength + index}`,
        brand: r.brand || r.brandName || '未知品牌',
        model: r.aiModel || r.ai_model || r.model || '未知模型',
        score: score,
        scoreClass: scoreClass,
        question: questionText.substring(0, 50),
        response: responseText.substring(0, 100),
        truncated: responseText.length > 100,
        fullResponse: responseText,
        expanded: false
      };
    });

    setTimeout(() => {
      this.setData({
        detailedResults: [...this.data.detailedResults, ...simplifiedResults],
        hasMoreResults: (currentLength + simplifiedResults.length) < this.data.totalResults
      });
      wx.hideLoading();
      
      // 加载完成提示
      if (!this.data.hasMoreResults) {
        wx.showToast({ title: '已加载全部', icon: 'success' });
      }
    }, 300);
  },

  /**
   * 获取完整详细结果（用于分页加载）
   * 【修复 - 2026-03-20】从全局变量中获取完整数据
   */
  _getFullDetailedResults: function() {
    const app = getApp();
    if (app.globalData && app.globalData.currentReportData) {
      // 【修复关键】返回完整的结果数据
      const fullResults = app.globalData.currentReportData.fullResults || [];
      if (fullResults.length > 0) {
        return fullResults;
      }
    }
    // 降级处理：返回当前已加载的数据
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
