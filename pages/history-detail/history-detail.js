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
    showShareMenu: false
  },

  onLoad: function(options) {
    // 【调试 P0】添加参数日志
    console.log('[报告详情页] onLoad 执行，options:', options);

    // 从参数获取记录 ID 或执行 ID
    const recordId = options.id || null;
    const executionId = options.executionId || null;
    const brandName = options.brandName ? decodeURIComponent(options.brandName) : '';

    // 【调试 P0】添加 ID 日志
    console.log('[报告详情页] executionId:', executionId, 'recordId:', recordId);

    if (!recordId && !executionId) {
      console.error('[报告详情页] ❌ 缺少记录 ID!');
      wx.showToast({
        title: '缺少记录 ID',
        icon: 'none'
      });
      return;
    }

    // 【P21 修复 - 添加超时保护】
    const loadTimeout = setTimeout(() => {
      console.error('[报告详情页] ⚠️ 加载超时（5 秒），强制解除 loading');
      this.setData({ loading: false });
      wx.showToast({ title: '加载超时', icon: 'none' });
    }, 5000);

    this.setData({
      recordId: recordId,
      executionId: executionId || recordId,
      brandName: brandName || '未知品牌',
      loading: true
    });

    // 【P0 修复 - 2026-03-11】优先使用本地缓存
    const localRecord = loadDiagnosisResult(executionId || recordId);

    if (localRecord) {
      console.log('[报告详情页] ✅ 本地缓存命中，直接加载');
      clearTimeout(loadTimeout);
      // 合并本地缓存数据和基础信息
      const mergedRecord = {
        ...localRecord,
        brandName: brandName || localRecord.brandName || '未知品牌',
        executionId: executionId || recordId
      };
      this.processHistoryDataOptimized(mergedRecord);
      return;
    }

    console.log('[报告详情页] ⚠️ 本地缓存未命中，从服务器加载');
    clearTimeout(loadTimeout);

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
    const serverUrl = getApp().globalData.serverUrl;

    // 【调试 P0】添加执行日志
    console.log('[报告详情页] loadFromServer 执行，executionId:', executionId);
    console.log('[报告详情页] token:', token ? '有' : '无');
    console.log('[报告详情页] serverUrl:', serverUrl);

    // 【P1-3 修复 - 2026-03-11】检查服务器 URL 配置
    if (!serverUrl) {
      console.error('[报告详情页] ❌ serverUrl 未配置，降级到本地缓存');
      this.loadHistoryRecordLocal(executionId);
      return;
    }

    // 【调试 P0】添加请求日志
    // 【P0 关键修复 - 2026-03-13】使用正确的 API 端点获取完整报告
    console.log('[第 2 层] 发起请求:', {
      url: `${serverUrl}/api/diagnosis/report/${executionId}`,
      executionId: executionId,
      hasToken: !!token
    });

    this.setData({ loading: true });

    // 【P1-3 修复 - 2026-03-11】添加超时保护，防止 loading 永久不解除
    const timeoutId = setTimeout(() => {
      console.warn('[报告详情页] ⚠️ 请求超时（10 秒），强制解除 loading 并降级到本地');
      this.setData({ loading: false });
      wx.showToast({ title: '网络请求超时', icon: 'none' });
      // 超时后降级到本地缓存
      this.loadHistoryRecordLocal(executionId);
    }, 10000); // 10 秒超时

    wx.request({
      url: `${serverUrl}/api/diagnosis/report/${executionId}`,
      header: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      timeout: 10000, // 【P1-3 修复】设置 10 秒超时
      method: 'GET',
      responseType: 'text',
      success: (res) => {
        // 【调试 P0】添加响应日志
        console.log('[第 2 层] 请求成功:', {
          statusCode: res.statusCode,
          hasData: !!res.data,
          dataKeys: Object.keys(res.data || {}),
          hasResults: !!(res.data?.data?.results || res.data?.results),
          hasBrandDistribution: !!(res.data?.data?.brandDistribution || res.data?.brandDistribution)
        });

        clearTimeout(timeoutId); // 【P1-3 修复】清除超时定时器

        if (res.statusCode === 200 && res.data) {
          // 【P21 修复 - 修复 API 返回格式不匹配问题】
          // API 返回格式：{success: true, data: {...}, hasPartialData: true, warnings: [...]}
          // 需要访问 res.data.data 获取实际报告数据
          const apiResponse = res.data;
          const report = apiResponse.data || apiResponse;  // 优先使用 apiResponse.data
          
          console.log('[报告详情页] 提取报告数据:', {
            hasData: !!report,
            hasResults: !!(report.results || report.result),
            resultsCount: (report.results || report.result || []).length
          });
          
          // 【P0 关键修复 - 2026-03-13】检查是否返回了完整数据
          if (report && (report.results || report.result || report.brandDistribution)) {
            console.log('[报告详情页] ✅ 服务器数据加载成功，有完整报告数据');
            // 【性能优化 P0】直接使用返回的数据，不再重复请求
            this.processHistoryDataFromApi(report);
            return;
          } else {
            console.warn('[报告详情页] ⚠️ 服务器返回数据不完整，降级到本地缓存');
          }
        } else if (res.statusCode === 401) {
          console.error('[报告详情页] ❌ 认证失败（401），降级到本地缓存');
          wx.showToast({ title: '认证失效，使用本地数据', icon: 'none' });
        } else if (res.statusCode === 404) {
          console.warn('[报告详情页] ⚠️ 数据未找到（404），降级到本地缓存');
        } else {
          console.error('[报告详情页] ❌ 服务器返回错误状态码:', res.statusCode);
        }

        // 降级到本地
        this.loadHistoryRecordLocal(executionId);
      },
      fail: (err) => {
        // 【调试 P0】添加错误日志
        console.error('[第 2 层] 请求失败:', err);
        clearTimeout(timeoutId); // 【P1-3 修复】清除超时定时器

        // 【P1-3 修复 - 2026-03-11】详细错误分析
        let errorMessage = '网络请求失败';
        if (err.errMsg) {
          if (err.errMsg.includes('timeout')) {
            errorMessage = '请求超时，使用本地数据';
            console.warn('[报告详情页] ⏰ 请求超时错误');
          } else if (err.errMsg.includes('fail')) {
            errorMessage = '网络连接失败，使用本地数据';
            console.error('[报告详情页] 🔌 网络连接失败');
          }
        }

        wx.showToast({ title: errorMessage, icon: 'none' });

        // 降级到本地
        this.loadHistoryRecordLocal(executionId);
      }
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

        // 【性能优化 P0】预先计算 scoreClass
        const simplifiedResults = results.slice(0, 5).map((r, index) => {
          const score = r.score || r.quality_score || 0;
          let scoreClass = 'poor';
          if (score >= 80) scoreClass = 'excellent';
          else if (score >= 60) scoreClass = 'good';

          return {
            id: r.id || `result_${index}`,
            brand: r.brand || r.extracted_brand || '未知品牌',
            model: r.model || '未知模型',
            score: score,
            scoreClass: scoreClass,
            question: (r.question || '').substring(0, 50),
            response: (r.response_content || r.response?.content || '').substring(0, 100),
            truncated: (r.response_content?.length || 0) > 100,
            fullResponse: r.response_content || r.response?.content || '',
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
   */
  processHistoryDataOptimized: function(record) {
    // 【紧急修复 - 2026-03-15】立即解除 loading，防止卡死
    this.setData({ loading: false });
    console.log('[紧急修复] processHistoryDataOptimized: loading=false');

    // 【P21 修复 - 数据验证】
    if (!record) {
      console.error('[报告详情页] ❌ record 为空');
      wx.showToast({ title: '数据为空', icon: 'none' });
      return;
    }

    // 【P0 修复 - 2026-03-15】避免循环引用：只提取必要的字段，不直接引用整个对象
    const results = record.results || record.result || null;

    // 【P21 修复 - 验证 results】
    if (!results) {
      console.error('[报告详情页] ❌ results 为空');
      // 降级处理：使用空数据继续加载
      this._loadCoreInfo(record, {});
      return;
    }

    console.log('[报告详情页] 开始处理数据，record keys:', Object.keys(record).length);

    // ==================== 第 1 层：核心信息（0ms，直接获取，无需计算）====================
    this._loadCoreInfo(record, results);

    // ==================== 第 2 层：分析数据（100ms，优先后端预计算，前端降级）====================
    setTimeout(() => {
      this._loadAnalysisData(record, results);
    }, 100);

    // ==================== 第 3 层：详细结果（200ms，异步简化）====================
    setTimeout(() => {
      this._loadDetailedResults(record, results);
    }, 200);

    // 最后：收藏状态（600ms，独立获取）
    setTimeout(() => {
      this._loadFavoriteStatus(record);
    }, 600);
  },

  /**
   * 【P0 修复 - 2026-03-15】加载核心信息
   */
  _loadCoreInfo: function(record, results) {
    const overallScore = results.overall_score || results.overallScore || 0;
    const overallGrade = this.calculateGrade(overallScore);

    console.log('[报告详情页] 第 1 层：overallScore=', overallScore, 'overallGrade=', overallGrade);

    this.setData({
      brandName: record.brandName || record.brand_name || this.data.brandName || '未知品牌',
      overallScore: overallScore,
      overallGrade: overallGrade,
      overallSummary: this.getGradeSummary(overallGrade),
      gradeClass: this.getGradeClass(overallGrade)
    });

    console.log('[报告详情页] 第 1 层加载完成');
  },

  /**
   * 【P0 修复 - 2026-03-15】加载分析数据
   */
  _loadAnalysisData: function(record, results) {
    try {
      // 【优先】使用后端预计算的评分维度
      let dimensionScores = results.dimension_scores || results.dimensionScores || null;

      // 【降级】如果后端未返回，从 detailed_results 计算
      if (!dimensionScores) {
        const detailedResults = results.detailed_results || results.detailedResults || [];
        // 【P0 修复】限制计算数量，防止大量数据
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
  },

  /**
   * 【P0 修复 - 2026-03-15】加载详细结果
   */
  _loadDetailedResults: function(record, results) {
    try {
      const detailedResults = results.detailed_results || results.detailedResults || [];

      // 【P0 修复 - 2026-03-15】确保 detailedResults 是数组，并且限制处理数量
      if (!Array.isArray(detailedResults)) {
        console.error('[第 3 层] detailedResults 不是数组，降级处理');
        this.setData({
          detailedResults: [],
          aiModels: [],
          competitors: [],
          questions: [],
          hasMoreResults: false,
          totalResults: 0
        });
        return;
      }

      // 异步简化数据（只处理前 5 条）
      // 【性能优化 P0】预先计算 scoreClass，避免 WXML 中三元表达式
      const simplifiedResults = detailedResults.slice(0, 5).map((r, index) => {
        // 预先计算 scoreClass
        let scoreClass = 'poor';
        if (r.score >= 80) scoreClass = 'excellent';
        else if (r.score >= 60) scoreClass = 'good';

        return {
          id: r.id || `result_${index}`,
          brand: r.brand || r.brandName,
          model: r.aiModel || r.ai_model || '未知模型',
          score: r.score,
          scoreClass: scoreClass,  // ✅ 预先计算，WXML 直接使用
          question: (r.question || '').substring(0, 50),
          response: (r.response || r.answer || '').substring(0, 100),
          truncated: (r.response?.length || r.answer?.length || 0) > 100,
          fullResponse: r.response || r.answer || '',
          expanded: false
        };
      });

      // 【性能优化 P0】只保存必要信息到全局变量
      const app = getApp();
      if (!app.globalData) app.globalData = {};
      app.globalData.currentReportData = {
        executionId: record.executionId || record.result_id || record.id,
        totalResults: detailedResults.length
        // 不保存 detailedResults 完整数据，避免内存占用
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
