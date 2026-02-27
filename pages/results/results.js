const { debug, info, warn, error } = require('../../utils/logger');
const { PageTransition } = require('../../utils/page-transition');

const { saveResult } = require('../../utils/saved-results-sync');
const { loadDiagnosisResult, loadLastDiagnosis } = require('../../utils/storage-manager');
const { generateFullReport } = require('../../utils/pdf-export');

// P1-008 新增：统一数据加载服务
const { loadDiagnosisData } = require('../../services/dataLoaderService');

// P1-011 新增：结果数据服务
const { fetchResultsFromServer: fetchResultsService } = require('../../services/resultDataService');

// 【存储架构优化】新增诊断报告 API
const { getFullReport, validateReport } = require('../../services/diagnosisApi');

// P3-1 优化：导入流式报告聚合器
const { createStreamingAggregator } = require('../../services/streamingReportAggregator');

Page({
  data: {
    // 页面过渡动画
    pageTransitionClass: '',
    pageLoaded: false,

    targetBrand: '',
    competitiveAnalysis: null,
    latestTestResults: null,
    pkDataByPlatform: {},
    platforms: [],
    platformDisplayNames: {}, // 存储显示名称
    currentSwiperIndex: 0,
    currentPlatform: '', // 当前选中的平台
    isPremium: false, // 模拟用户会员状态
    advantageInsight: '权威度表现突出，可见度良好',
    riskInsight: '品牌纯净度有待提升',
    opportunityInsight: '一致性方面有较大提升空间',
    currentViewMode: 'brand', // 当前视图模式：brand, dimension, detailed
    groupedResultsByBrand: [], // 按品牌分组的结果
    dimensionComparisonData: [], // 维度对比数据
    expandedBrands: {}, // 展开的品牌详情

    // 【容错机制】新增字段
    hasPartialResults: false, // 是否有部分结果
    platformErrors: [], // 平台错误列表
    quotaWarnings: [], // 配额警告
    executionWarnings: [], // 执行警告
    
    // P0-3 竞争分析相关数据
    brandRankingList: [], // 品牌排名列表
    firstMentionByPlatform: [], // 首次提及率
    interceptionRisks: [], // 拦截风险
    competitorComparisonData: [], // 竞品对比详情

    // P1-1 语义偏移相关数据
    semanticDriftData: null, // 语义偏移分析结果
    semanticContrastData: null, // 语义对比数据（官方关键词 vs AI 关键词）

    // P1-2 信源纯净度相关数据
    sourcePurityData: null, // 信源纯净度分析结果
    sourceIntelligenceMap: null, // 信源情报图谱

    // P1-3 优化建议相关数据
    recommendationData: null, // 优化建议数据

    // P2-2 雷达图相关数据
    radarChartData: [],      // 雷达图数据
    canvasWidth: 300,        // Canvas 宽度
    canvasHeight: 300,       // Canvas 高度
    radarChartRendered: false, // 是否已渲染

    // P2-3 关键词云相关数据
    keywordCloudData: [],      // 词云数据
    topKeywords: [],           // 高频词列表
    keywordStats: {            // 关键词统计
      positiveCount: 0,
      neutralCount: 0,
      negativeCount: 0
    },
    wordCloudCanvasWidth: 350, // Canvas 宽度
    wordCloudCanvasHeight: 350, // Canvas 高度
    wordCloudRendered: false,   // 是否已渲染

    // 保存结果相关数据
    showSaveResultModal: false,
    saveBrandName: '',
    saveTags: [],
    saveCategories: ['未分类', '日常监测', '竞品分析', '季度报告', '年度总结'],
    saveCategoryIndex: 0,
    selectedSaveCategory: '未分类',
    saveNotes: '',
    saveAsFavorite: false,
    newSaveTag: '',

    // 高优先级修复 2&3: 缓存和刷新相关
    isCached: false, // 是否使用缓存数据
    cacheTime: null, // 缓存时间戳
    refreshing: false, // 是否正在刷新
    
    // P3-1 优化：流式渲染相关
    useStreamingRender: true,  // 是否启用流式渲染
    isStreaming: false,  // 是否正在流式渲染
    streamStage: 'loading',  // 当前渲染阶段
    streamProgress: 0,  // 渲染进度 (0-100)
    streamStageText: '准备渲染...',  // 阶段提示文本
    streamingData: {},  // 流式渲染的中间数据

    // P2-022 新增：错误详情相关
    showErrorDetailsModal: false,  // 是否显示错误详情模态框
    errorLogList: [],  // 错误日志列表
    quotaExhaustedCount: 0,  // 配额用尽错误数
    otherErrorCount: 0,  // 其他错误数

    // P2-023 新增：自动刷新相关
    isAutoRefreshing: false,  // 是否正在自动刷新
    autoRefreshTimer: null,  // 自动刷新定时器
    useFallbackData: false,  // 是否使用降级数据

    // 【完整性修复】新增遗漏字段展示
    // 诊断配置信息
    selectedModels: [],  // 使用的 AI 模型列表
    customQuestions: [],  // 诊断问题列表
    completedAt: '',  // 完成时间
    stage: '',  // 当前阶段
    isCompleted: false,  // 是否完成
    errorMessage: '',  // 错误信息

    // AI 模型性能统计
    modelPerformanceStats: [],  // 模型性能统计 {model, avgLatency, resultCount}

    // 质量详情统计
    qualityDetailsStats: {
      avgAccuracy: 0,
      avgCompleteness: 0,
      avgRelevance: 0,
      avgCoherence: 0
    },

    // 响应时间统计
    responseTimeStats: {
      minLatency: 0,
      maxLatency: 0,
      avgLatency: 0
    },

    // 展示控制
    showConfigSection: true,  // 是否展示配置回顾区域
    showModelPerformance: true,  // 是否展示模型性能
    showQualityDetails: true,  // 是否展示质量详情
    showResponseTime: true  // 是否展示响应时间
  },

  /**
   * P0-005 修复：前端数据加载竞态条件
   *
   * 修复策略：
   * 1. 并行加载所有数据源（Cache, Storage, API）
   * 2. 使用 Promise.allSettled 确保所有数据源都尝试加载
   * 3. 选择最优结果（优先级：API > Storage > Cache）
   * 4. 避免竞态条件导致空结果展示
   */
  onLoad: async function(options) {
    console.log('[结果页 P0-005] 页面加载，开始并行加载数据...');

    // 应用页面进入动画
    this.applyPageEnterAnimation();

    const executionId = decodeURIComponent(options.executionId || '');
    const brandName = decodeURIComponent(options.brandName || '');

    if (!executionId) {
      console.error('[结果页] 缺少 executionId');
      this.showNoDataModal();
      return;
    }

    // 显示加载中状态
    this.setData({
      isLoading: true,
      showLoadingSpinner: true,
      showErrorBanner: false
    });

    // 并行加载所有数据源
    const [cachedResult, storageResult, apiResult] = await Promise.allSettled([
      this.loadFromCache(),
      this.loadFromStorage(executionId),
      this.loadFromApi(executionId)
    ]);

    // 选择最优结果（优先级：API > Storage > Cache）
    let bestResult = null;
    let loadError = null;

    if (apiResult.status === 'fulfilled' && apiResult.value && apiResult.value.results) {
      bestResult = apiResult.value;
      console.log('✅ 从 API 加载成功');
    } else if (storageResult.status === 'fulfilled' && storageResult.value) {
      bestResult = storageResult.value;
      console.log('✅ 从 Storage 加载成功');
      loadError = apiResult.reason?.message || 'API 加载失败';
    } else if (cachedResult.status === 'fulfilled' && cachedResult.value) {
      bestResult = cachedResult.value;
      console.log('✅ 从缓存加载成功');
      loadError = '使用缓存数据';
    }

    // 停止加载动画
    this.setData({
      isLoading: false,
      showLoadingSpinner: false
    });

    // 如果有结果，展示数据
    if (bestResult) {
      this.processAndDisplayResults(bestResult, brandName);

      // 如果有降级提示，显示
      if (loadError) {
        this.setData({
          showFallbackBanner: true,
          fallbackMessage: loadError,
          useFallbackData: true
        });
        
        // P2-023 新增：启动后台自动刷新
        this.startAutoRefresh(executionId, brandName);
      }
    } else {
      // 所有数据源都失败
      this.setData({
        showErrorBanner: true,
        errorMessage: '加载诊断结果失败，请重试'
      });
      wx.showModal({
        title: '加载失败',
        content: '所有数据源均加载失败，请重试',
        showCancel: false,
        confirmText: '重试',
        success: (res) => {
          if (res.confirm) {
            this.onLoad(options);
          }
        }
      });
    }
  },

  /**
   * P0-005 新增：从缓存加载
   */
  loadFromCache: function() {
    return new Promise((resolve) => {
      try {
        const cached = wx.getStorageSync('last_diagnostic_results');
        if (cached && cached.results && cached.results.length > 0) {
          resolve(cached);
        } else {
          resolve(null);
        }
      } catch (e) {
        console.warn('[loadFromCache] 缓存加载失败:', e);
        resolve(null);
      }
    });
  },

  /**
   * P0-005 新增：从 Storage 加载
   */
  loadFromStorage: function(executionId) {
    return new Promise((resolve) => {
      try {
        const result = loadDiagnosisResult(executionId);
        if (result && result.data && result.data.results && result.data.results.length > 0) {
          resolve(result.data);
        } else {
          resolve(null);
        }
      } catch (e) {
        console.warn('[loadFromStorage] Storage 加载失败:', e);
        resolve(null);
      }
    });
  },

  /**
   * P0-005 新增：从 API 加载
   */
  loadFromApi: function(executionId) {
    return new Promise((resolve, reject) => {
      try {
        const { getFullReport } = require('../../services/diagnosisApi');
        getFullReport(executionId)
          .then(res => {
            if (res && res.results && res.results.length > 0) {
              resolve(res);
            } else {
              reject(new Error('API 返回空结果'));
            }
          })
          .catch(err => reject(err));
      } catch (e) {
        console.warn('[loadFromApi] API 加载失败:', e);
        reject(e);
      }
    });
  },

  /**
   * P0-005 新增：处理并展示结果
   */
  processAndDisplayResults: function(resultData, brandName) {
    console.log('[processAndDisplayResults] 处理结果数据:', resultData);

    const results = resultData.results || [];
    const competitiveAnalysis = resultData.competitive_analysis || resultData.competitiveAnalysis || {};

    // 初始化页面
    this.initializePageWithData(
      results,
      brandName,
      [],
      competitiveAnalysis,
      resultData.negative_sources || [],
      resultData.semantic_drift_data || null,
      resultData.recommendation_data || null
    );

    // 保存额外数据到 data（P0-007/P0-009 增强：添加配额警告和完成率）
    const completionRate = resultData.completion_rate !== undefined
      ? resultData.completion_rate
      : (resultData.total_tasks > 0 ? Math.round((resultData.completed_tasks || results.length) * 100 / resultData.total_tasks) : 100);

    // 【完整性修复】处理遗漏字段
    const selectedModels = resultData.selected_models || resultData.selectedModels || [];
    const customQuestions = resultData.custom_questions || resultData.customQuestions || [];
    const completedAt = resultData.completed_at || resultData.completedAt || '';
    const stage = resultData.stage || '';
    const isCompleted = resultData.is_completed !== undefined ? resultData.is_completed : false;
    const reportErrorMessage = resultData.error_message || '';

    // 计算 AI 模型性能统计
    const modelStats = {};
    const latencies = [];
    results.forEach(r => {
      const model = r.model || 'unknown';
      const latency = r.response?.latency || r.response_latency || 0;
      if (!modelStats[model]) {
        modelStats[model] = { model, totalLatency: 0, count: 0 };
      }
      modelStats[model].totalLatency += latency;
      modelStats[model].count++;
      if (latency > 0) latencies.push(latency);
    });
    const modelPerformanceStats = Object.values(modelStats).map(stat => ({
      model: stat.model,
      avgLatency: stat.count > 0 ? (stat.totalLatency / stat.count).toFixed(2) : 0,
      resultCount: stat.count
    }));

    // 计算质量详情统计
    let totalAccuracy = 0, totalCompleteness = 0, totalRelevance = 0, totalCoherence = 0;
    let qualityCount = 0;
    results.forEach(r => {
      const details = r.quality_details || {};
      if (details.accuracy) { totalAccuracy += details.accuracy; qualityCount++; }
      if (details.completeness) { totalCompleteness += details.completeness; qualityCount++; }
      if (details.relevance) { totalRelevance += details.relevance; qualityCount++; }
      if (details.coherence) { totalCoherence += details.coherence; qualityCount++; }
    });
    const qualityDetailsStats = {
      avgAccuracy: qualityCount > 0 ? (totalAccuracy / qualityCount).toFixed(2) : 0,
      avgCompleteness: qualityCount > 0 ? (totalCompleteness / qualityCount).toFixed(2) : 0,
      avgRelevance: qualityCount > 0 ? (totalRelevance / qualityCount).toFixed(2) : 0,
      avgCoherence: qualityCount > 0 ? (totalCoherence / qualityCount).toFixed(2) : 0
    };

    // 计算响应时间统计
    const responseTimeStats = {
      minLatency: latencies.length > 0 ? Math.min(...latencies).toFixed(2) : 0,
      maxLatency: latencies.length > 0 ? Math.max(...latencies).toFixed(2) : 0,
      avgLatency: latencies.length > 0 ? (latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(2) : 0
    };

    this.setData({
      sourcePurityData: resultData.source_purity_data,
      sourceIntelligenceMap: resultData.source_intelligence_map,
      warning: resultData.warning,
      missingCount: resultData.missing_count,
      qualityScore: resultData.quality_score,
      qualityLevel: resultData.quality_level,
      qualityLevelText: this.getQualityLevelText(resultData.quality_level),
      // P0-007/P0-009 新增：配额警告和完成率（总是设置，即使用户未提供）
      quotaWarnings: resultData.quota_warnings || [],
      quotaExhaustedModels: resultData.quota_exhausted_models || [],
      completionRate: completionRate,
      completedTasks: resultData.completed_tasks || results.length,
      totalTasks: resultData.total_tasks || results.length,
      hasPartialResults: resultData.has_partial_results || (completionRate < 100),
      partialWarning: resultData.partial_warning || (completionRate < 100 ? `诊断部分完成：${results.length}/${resultData.total_tasks || results.length} (${completionRate}%)` : null),
      // P1-016 新增：配额恢复建议
      quotaRecoverySuggestions: resultData.quota_recovery_suggestions || [],
      // P2-022 新增：错误日志列表（只计算一次）
      errorLogList: [],
      quotaExhaustedCount: 0,
      otherErrorCount: 0,
      // 【完整性修复】新增遗漏字段
      selectedModels: selectedModels,
      customQuestions: customQuestions,
      completedAt: completedAt ? this.formatDateTime(completedAt) : '',
      stage: stage,
      isCompleted: isCompleted,
      reportErrorMessage: reportErrorMessage,
      modelPerformanceStats: modelPerformanceStats,
      qualityDetailsStats: qualityDetailsStats,
      responseTimeStats: responseTimeStats
    });

    // P2-022 新增：计算错误日志和统计（只计算一次，避免重复）
    const errorLogList = this.buildErrorLogList(results);
    const quotaExhaustedCount = errorLogList.filter(e => 
      e.errorType === 'quota_exhausted' || e.errorType === 'insufficient_quota'
    ).length;
    const otherErrorCount = errorLogList.filter(e => 
      e.errorType !== 'quota_exhausted' && e.errorType !== 'insufficient_quota'
    ).length;
    this.setData({
      errorLogList: errorLogList,
      quotaExhaustedCount: quotaExhaustedCount,
      otherErrorCount: otherErrorCount
    });

    // P0-007 新增：如果有配额警告，更新提示条
    if (resultData.quota_warnings && resultData.quota_warnings.length > 0) {
      this.setData({
        showFallbackBanner: true,
        fallbackMessage: resultData.quota_warnings.join('; ') + '。请查看下方恢复建议'
      });
    }

    // 合并所有警告
    const warnings = [];
    if (resultData.warning) {
      const resultsCount = results.length;
      const totalCount = resultsCount + (resultData.missing_count || 0);
      warnings.push(`诊断部分完成：${resultData.warning}\n\n已获取 ${resultsCount}/${totalCount} 条有效结果`);
    }
    if (resultData.quality_warning) {
      const suggestion = resultData.quality_suggestion === 'retry'
        ? '建议：重新运行诊断以获得更准确的结果'
        : '建议：结果仅供参考，建议结合其他数据源综合判断';
      warnings.push(`${resultData.quality_warning}\n\n${suggestion}`);
    }
    // P0-007 新增：配额警告
    if (resultData.quota_warnings && resultData.quota_warnings.length > 0) {
      warnings.push(`⚠️ 配额警告：${resultData.quota_warnings.join('; ')}`);
    }
    if (warnings.length > 0) {
      wx.showModal({
        title: '诊断提示',
        content: warnings.join('\n\n---\n\n'),
        showCancel: false,
        confirmText: '知道了'
      });
    }
  },

  /**
   * 从 results 计算品牌评分（备用方案）
   */
  calculateBrandScoresFromResults: function(results, targetBrand) {
    const brandScores = {};
    const allBrands = new Set();
    
    // 收集所有品牌
    results.forEach(r => {
      const brand = r.brand || targetBrand;
      allBrands.add(brand);
    });
    
    // 为每个品牌计算评分
    allBrands.forEach(brand => {
      const brandResults = results.filter(r => r.brand === brand);
      
      let totalScore = 0;
      let count = 0;
      
      brandResults.forEach(r => {
        const geoData = r.geo_data || {};
        const rank = geoData.rank || -1;
        const sentiment = geoData.sentiment || 0.0;
        
        // 从 rank 和 sentiment 计算分数
        let score = 0;
        if (rank > 0) {
          if (rank <= 3) {
            score = 90 + (3 - rank) * 3 + sentiment * 10;
          } else if (rank <= 6) {
            score = 70 + (6 - rank) * 3 + sentiment * 10;
          } else {
            score = 50 + (10 - rank) * 2 + sentiment * 10;
          }
        } else {
          score = 30 + sentiment * 10;
        }
        
        score = Math.min(100, Math.max(0, score));
        totalScore += score;
        count++;
      });
      
      if (count > 0) {
        const avgScore = totalScore / count;
        let grade = 'D';
        if (avgScore >= 90) grade = 'A+';
        else if (avgScore >= 80) grade = 'A';
        else if (avgScore >= 70) grade = 'B';
        else if (avgScore >= 60) grade = 'C';
        
        brandScores[brand] = {
          overallScore: Math.round(avgScore),
          overallGrade: grade,
          overallAuthority: Math.round(50 + (avgScore - 50) * 0.9),
          overallVisibility: Math.round(50 + (avgScore - 50) * 0.85),
          overallPurity: Math.round(50 + (avgScore - 50) * 0.9),
          overallConsistency: Math.round(50 + (avgScore - 50) * 0.8),
          overallSummary: `GEO 综合评分为 ${Math.round(avgScore)} 分，等级为 ${grade}`
        };
      }
    });
    
    console.log('🎯 从 results 计算的品牌评分:', brandScores);
    return brandScores;
  },

  /**
   * P1-011 修复：从服务器获取结果数据
   * @param {string} executionId - 执行 ID
   * @param {string} brandName - 品牌名称
   * @returns {Promise}
   */
  fetchResultsFromServer: function(executionId, brandName) {
    const that = this;
    return new Promise((resolve, reject) => {
      fetchResultsService(
        executionId,
        brandName,
        // onSuccess
        (responseData) => {
          console.log('[fetchResultsFromServer] 获取成功，结果数量:', responseData.results.length);
          that.setData({
            latestTestResults: responseData.results,
            latestCompetitiveAnalysis: responseData.competitiveAnalysis,
            targetBrand: responseData.targetBrand || brandName,
            isCached: false
          });
          resolve(responseData);
        },
        // onError
        (error) => {
          console.error('[fetchResultsFromServer] 获取失败:', error);
          reject(error);
        }
      );
    });
  },

  // P1-011 已删除：fetchResultsFromServer 函数（已迁移到 dataLoaderService）

    /**
   * 【新增】显示认证失败提示
   */
  showAuthFailedModal: function() {
    wx.showModal({
      title: '认证失败',
      content: '登录已过期，请重新登录',
      confirmText: '去登录',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          wx.reLaunch({ url: '/pages/login/login' });
        }
      }
    });
  },

  /**
   * 【新增】显示无数据提示
   */
  showNoDataModal: function() {
    wx.showModal({
      title: '暂无数据',
      content: '未找到诊断结果数据，请重新运行诊断或返回首页。',
      confirmText: '返回首页',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          wx.reLaunch({ url: '/pages/index/index' });
        }
      }
    });
  },

  /**
   * 【容错机制】显示部分结果警告（P1-017 优化：避免过度弹窗）
   * 
   * 优化策略：
   * 1. 不再自动弹窗，通过 UI 提示条展示
   * 2. 用户点击"详情"按钮时才显示弹窗
   * 3. 简化文案，突出关键信息
   */
  showPartialResultsWarning: function() {
    const { hasPartialResults, platformErrors, quotaWarnings, completionRate, completedTasks, totalTasks } = this.data;

    if (!hasPartialResults && !quotaWarnings.length) {
      return;
    }

    // P1-017 优化：简化文案，突出关键信息
    let content = '';
    
    // 完成率信息（最重要）
    if (completionRate !== undefined && completionRate < 100) {
      content += `📊 诊断完成率：${completedTasks || 0}/${totalTasks || 0} (${completionRate}%)\n\n`;
    }
    
    // 配额警告（如果有）
    if (quotaWarnings.length > 0) {
      content += `⚠️ 配额用尽：${quotaWarnings.join(', ')}\n\n`;
    }
    
    // 平台错误（如果有）
    if (platformErrors.length > 0) {
      content += `❌ 平台错误：${platformErrors.length} 个\n\n`;
    }
    
    // 建议（精简版）
    content += `💡 建议：\n`;
    content += `• 配额用尽：查看下方"配额恢复建议"卡片\n`;
    content += `• 切换平台：点击错误平台的"切换其他平台"按钮\n`;
    content += `• 重新诊断：返回首页重新运行诊断`;

    wx.showModal({
      title: '⚠️ 诊断部分完成',
      content: content,
      confirmText: '查看结果',
      cancelText: '重试',
      success: (res) => {
        if (res.cancel) {
          // 用户选择重试
          this.refreshData();
        }
      }
    });
  },

  /**
   * P0-006 新增：重试加载
   */
  retryLoad: function() {
    const executionId = this.data.executionId || '';
    if (executionId) {
      this.onLoad({ executionId });
    } else {
      wx.reLaunch({ url: '/pages/index/index' });
    }
  },

  /**
   * P0-006 新增：显示部分结果详情
   */
  showPartialDetails: function() {
    this.showPartialResultsWarning();
  },

  /**
   * P1-016 新增：切换其他平台重试
   */
  retryWithOtherPlatform: function(e) {
    const failedModel = e.currentTarget.dataset.model;
    wx.showModal({
      title: '切换平台',
      content: `检测到 ${failedModel} 配额已用尽。您可以：\n\n1. 返回诊断页面切换其他 AI 平台\n2. 充值后重新诊断\n\n是否返回诊断页面？`,
      confirmText: '去切换',
      cancelText: '再看看',
      success: (res) => {
        if (res.confirm) {
          // 返回诊断页面，带上当前结果
          if (this.data.latestTestResults && this.data.targetBrand) {
            wx.setStorageSync('latestTestResults', this.data.latestTestResults);
            wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
          }
          wx.navigateBack();
        }
      }
    });
  },

  /**
   * P2-022 新增：构建错误日志列表
   */
  buildErrorLogList: function(results) {
    const errorLogList = [];
    const now = new Date();
    
    if (results && Array.isArray(results)) {
      results.forEach((result, index) => {
        if (result.error || result.error_type) {
          const errorType = result.error_type || 'unknown';
          let errorTypeName = '未知错误';
          
          // 错误类型映射
          switch (errorType) {
            case 'quota_exhausted':
            case 'insufficient_quota':
              errorTypeName = '配额用尽';
              break;
            case 'timeout':
              errorTypeName = '超时';
              break;
            case 'network_error':
              errorTypeName = '网络错误';
              break;
            case 'invalid_api_key':
              errorTypeName = 'API Key 无效';
              break;
            case 'rate_limit_exceeded':
              errorTypeName = '频率限制';
              break;
            default:
              errorTypeName = '其他错误';
          }
          
          errorLogList.push({
            index: index,
            model: result.model || '未知平台',
            errorType: errorType,
            errorTypeName: errorTypeName,
            message: result.error || '未知错误',
            time: now.toLocaleTimeString('zh-CN')
          });
        }
      });
    }
    
    return errorLogList;
  },

  /**
   * P2-022 新增：显示错误日志详情
   */
  showErrorLogDetails: function() {
    this.setData({
      showErrorDetailsModal: true
    });
  },

  /**
   * P2-022 新增：关闭错误详情
   */
  closeErrorDetails: function() {
    this.setData({
      showErrorDetailsModal: false
    });
  },

  /**
   * P2-023 新增：启动自动刷新
   */
  startAutoRefresh: function(executionId, brandName) {
    // 清除之前的定时器
    if (this.data.autoRefreshTimer) {
      clearInterval(this.data.autoRefreshTimer);
    }
    
    this.setData({
      isAutoRefreshing: false
    });
    
    console.log('[P2-023 自动刷新] 启动后台刷新，executionId:', executionId);
    
    // 每 30 秒尝试刷新一次
    const refreshInterval = 30000;
    const maxRefreshAttempts = 10;  // 最多尝试 10 次
    let refreshAttempts = 0;
    
    const timer = setInterval(() => {
      refreshAttempts++;
      console.log(`[P2-023 自动刷新] 第 ${refreshAttempts}/${maxRefreshAttempts} 次刷新尝试`);
      
      if (refreshAttempts >= maxRefreshAttempts) {
        clearInterval(timer);
        this.setData({
          autoRefreshTimer: null,
          isAutoRefreshing: false
        });
        console.log('[P2-023 自动刷新] 达到最大尝试次数，停止刷新');
        return;
      }
      
      // 后台静默刷新
      this.silentRefreshFromApi(executionId, brandName)
        .then((success) => {
          if (success) {
            console.log('[P2-023 自动刷新] 刷新成功，停止定时器');
            clearInterval(timer);
            this.setData({
              autoRefreshTimer: null,
              isAutoRefreshing: false,
              useFallbackData: false
            });
            
            // 显示刷新成功提示
            wx.showToast({
              title: '已获取最新结果',
              icon: 'success'
            });
          }
        })
        .catch((err) => {
          console.warn('[P2-023 自动刷新] 刷新失败:', err);
        });
      
    }, refreshInterval);
    
    this.setData({
      autoRefreshTimer: timer
    });
  },

  /**
   * P2-023 新增：后台静默刷新
   */
  silentRefreshFromApi: function(executionId, brandName) {
    return new Promise((resolve, reject) => {
      try {
        const { getFullReport } = require('../../services/diagnosisApi');
        
        getFullReport(executionId)
          .then((res) => {
            if (res && res.results && res.results.length > 0) {
              // 检查新结果是否比当前结果更好（更多结果或更高完成率）
              const currentResults = this.data.latestTestResults || [];
              const newResults = res.results || [];
              
              if (newResults.length > currentResults.length) {
                console.log('[P2-023 自动刷新] 发现更新的结果，数量:', newResults.length);
                
                // 更新页面数据
                this.processAndDisplayResults(res, brandName);
                resolve(true);
              } else {
                console.log('[P2-023 自动刷新] 结果数量无变化，继续等待');
                resolve(false);
              }
            } else {
              reject(new Error('API 返回空结果'));
            }
          })
          .catch((err) => {
            reject(err);
          });
      } catch (e) {
        reject(e);
      }
    });
  },

  /**
   * 从 URL 参数加载数据
   */
  loadFromUrlParams: function(options) {
    try {
      // 解析 results 参数（它可能是一个 JSON 字符串）
      let results;
      if (typeof options.results === 'string') {
        try {
          results = JSON.parse(decodeURIComponent(options.results));
        } catch (parseErr) {
          console.error('Failed to parse results:', parseErr);
          results = options.results;
        }
      } else {
        results = options.results;
      }

      const targetBrand = options.targetBrand || '';

      // 如果 competitiveAnalysis 参数存在，解析它
      let competitiveAnalysis;
      if (options.competitiveAnalysis) {
        try {
          competitiveAnalysis = JSON.parse(decodeURIComponent(options.competitiveAnalysis));
        } catch (parseErr) {
          competitiveAnalysis = results.competitiveAnalysis || null;
        }
      } else {
        competitiveAnalysis = results.competitiveAnalysis || null;
      }

      // 如果 competitiveAnalysis 不存在，尝试从 results 中构建
      if (!competitiveAnalysis && results && typeof results === 'object') {
        if (results.competitiveAnalysis) {
          competitiveAnalysis = results.competitiveAnalysis;
        } else if (results.brandScores) {
          competitiveAnalysis = {
            brandScores: results.brandScores,
            firstMentionByPlatform: results.firstMentionByPlatform || {},
            interceptionRisks: results.interceptionRisks || {}
          };
        } else {
          competitiveAnalysis = {
            brandScores: results,
            firstMentionByPlatform: {},
            interceptionRisks: {}
          };
        }
      } else if (!competitiveAnalysis) {
        competitiveAnalysis = {
          brandScores: {},
          firstMentionByPlatform: {},
          interceptionRisks: {}
        };
      }

      console.log('Parsed data:', { targetBrand, competitiveAnalysis, results });

      // 生成平台对比数据
      const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(competitiveAnalysis, targetBrand, results);

      // 确定最终的测试结果数据
      let finalTestResults = [];
      if (results && typeof results === 'object') {
        if (results.detailed_results) {
          finalTestResults = results.detailed_results;
        } else if (results.results) {
          finalTestResults = results.results;
        } else if (Array.isArray(results)) {
          finalTestResults = results;
        }
      }

      const currentPlatform = platforms.length > 0 ? platforms[0] : '';
      const insights = this.generateInsights(competitiveAnalysis, targetBrand);
      const groupedResults = this.groupResultsByBrand(finalTestResults, targetBrand);
      const dimensionComparison = this.generateDimensionComparison(finalTestResults, targetBrand);
      const sourceIntelligenceMap = results.sourceIntelligenceMap || {};

      this.setData({
        targetBrand,
        competitiveAnalysis: competitiveAnalysis || {},
        latestTestResults: finalTestResults,
        pkDataByPlatform,
        platforms,
        platformDisplayNames,
        currentPlatform,
        advantageInsight: insights.advantage,
        riskInsight: insights.risk,
        opportunityInsight: insights.opportunity,
        groupedResultsByBrand: groupedResults,
        dimensionComparisonData: dimensionComparison,
        sourceIntelligenceMap: sourceIntelligenceMap,
        showSourceIntelligence: !!sourceIntelligenceMap.nodes && sourceIntelligenceMap.nodes.length > 0
      });

      console.log('Set page data:', this.data);

    } catch (e) {
      console.error('解析结果数据失败', e);
      this.loadFromCache();
    }
  },

  /**
   * P0-1 修复：使用加载的数据初始化页面
   * P3-1 优化：支持流式渲染（分阶段展示）
   */
  initializePageWithData: function(results, targetBrand, competitorBrands, competitiveAnalysis, negativeSources, semanticDriftData, recommendationData, insightsData) {
    try {
      console.log('📊 初始化页面数据，结果数量:', results.length);

      // P3-1 优化：检查是否使用流式渲染
      const useStreaming = this.data.useStreamingRender !== false;  // 默认启用
      
      if (useStreaming && results && results.length > 10) {
        // 大数据量时使用流式渲染
        console.log('🚀 使用流式渲染');
        this.initializePageWithStreaming(results, targetBrand, competitorBrands, competitiveAnalysis, negativeSources, semanticDriftData, recommendationData, insightsData);
        return;
      }

      // 传统全量渲染
      console.log('📊 使用传统全量渲染');
      this._initializePageWithDataInternal(results, targetBrand, competitorBrands, competitiveAnalysis, negativeSources, semanticDriftData, recommendationData, insightsData);
      
    } catch (error) {
      console.error('❌ 初始化页面数据失败:', error);
      wx.hideLoading();
      wx.showModal({
        title: '初始化失败',
        content: '页面初始化失败，请稍后重试',
        showCancel: false
      });
    }
  },

  /**
   * P3-1 新增：流式渲染初始化
   */
  initializePageWithStreaming: function(results, targetBrand, competitorBrands, competitiveAnalysis, negativeSources, semanticDriftData, recommendationData, insightsData) {
    // 显示加载进度
    this.setData({
      isStreaming: true,
      streamStage: 'loading',
      streamProgress: 0
    });

    // 创建流式聚合器
    const streamer = createStreamingAggregator(results, targetBrand, competitorBrands, {
      negative_sources: negativeSources,
      semantic_drift_data: semanticDriftData,
      recommendation_data: recommendationData
    });

    // 设置进度回调
    streamer.onProgress((progress) => {
      console.log('[流式渲染] 进度:', progress);
      this.setData({
        streamProgress: progress.progress,
        streamStage: progress.stage
      });
    });

    // 设置阶段回调
    streamer.onStage((stageName, data) => {
      console.log('[流式渲染] 阶段:', stageName);
      
      switch (stageName) {
        case 'cleaned':
          // 阶段 1: 数据清洗完成
          this.setData({
            streamProgress: 12,
            streamStageText: '数据清洗完成'
          });
          break;
          
        case 'filled':
          // 阶段 2: 数据填充完成
          this.setData({
            streamProgress: 25,
            streamStageText: '数据填充完成'
          });
          break;
          
        case 'scores':
          // 阶段 3: 品牌分数计算完成（可先展示）
          console.log('[流式渲染] 渲染分数卡片');
          this._renderScoreCards(data, targetBrand);
          this.setData({
            streamProgress: 37,
            streamStageText: '品牌分数已生成'
          });
          break;
          
        case 'sov':
          // 阶段 4: SOV 计算完成
          console.log('[流式渲染] 渲染 SOV 图表');
          this._renderSOVChart(data);
          this.setData({
            streamProgress: 50,
            streamStageText: '市场份额已计算'
          });
          break;
          
        case 'risk':
          // 阶段 5: 风险评分完成
          console.log('[流式渲染] 渲染风险评分');
          this._renderRiskScore(data);
          this.setData({
            streamProgress: 62,
            streamStageText: '风险评分已生成'
          });
          break;
          
        case 'health':
          // 阶段 6: 品牌健康度完成
          console.log('[流式渲染] 渲染品牌健康度');
          this._renderBrandHealth(data);
          this.setData({
            streamProgress: 75,
            streamStageText: '品牌健康度已评估'
          });
          break;
          
        case 'insights':
          // 阶段 7: 洞察生成完成
          console.log('[流式渲染] 生成洞察');
          this._renderInsights(data);
          this.setData({
            streamProgress: 87,
            streamStageText: '核心洞察已生成'
          });
          break;
          
        case 'complete':
          // 阶段 8: 完整报告完成
          console.log('[流式渲染] 完整报告完成');
          this._finalizeStreaming(data);
          this.setData({
            isStreaming: false,
            streamProgress: 100,
            streamStageText: '渲染完成'
          });
          break;
      }
    });

    // 开始流式执行
    streamer.stream().then(() => {
      console.log('[流式渲染] 完成');
      wx.hideLoading();
    }).catch((err) => {
      console.error('[流式渲染] 失败:', err);
      wx.hideLoading();
      wx.showModal({
        title: '渲染失败',
        content: '流式渲染失败，请稍后重试',
        showCancel: false
      });
    });
  },

  /**
   * 内部方法：传统全量渲染
   */
  _initializePageWithDataInternal: function(results, targetBrand, competitorBrands, competitiveAnalysis, negativeSources, semanticDriftData, recommendationData, insightsData) {
    try {
      // 如果没有传入 competitiveAnalysis，则构建它
      if (!competitiveAnalysis) {
        competitiveAnalysis = this.buildCompetitiveAnalysis(results, targetBrand, competitorBrands);
      }

      // 生成平台对比数据
      const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(competitiveAnalysis, targetBrand, results);

      const currentPlatform = platforms.length > 0 ? platforms[0] : '';

      // 【P0 修复】使用后端返回的 insights，如果没有则前端生成
      const insights = insightsData || this.generateInsights(competitiveAnalysis, targetBrand);
      if (insightsData) {
        console.log('✅ 使用后端返回的核心洞察:', insightsData);
      }

      const groupedResults = this.groupResultsByBrand(results, targetBrand);
      const dimensionComparison = this.generateDimensionComparison(results, targetBrand);

      // P0-3 修复：处理竞争分析数据
      const competitiveAnalysisData = this.processCompetitiveAnalysisData(competitiveAnalysis, results, targetBrand, competitorBrands);

      // P1-1 修复：处理语义偏移数据 - 使用后端数据
      const semanticDriftAnalysisData = this.processSemanticDriftData(competitiveAnalysis, results, targetBrand, semanticDriftData);

      // P1-2 修复：处理信源纯净度数据 - 使用负面信源数据
      const sourcePurityAnalysisData = this.processSourcePurityData(competitiveAnalysis, results, negativeSources);

      // P1-3 修复：处理优化建议数据 - 使用后端数据
      const recommendationAnalysisData = this.processRecommendationData(competitiveAnalysis, results, negativeSources, recommendationData);

      // P2-2 修复：准备雷达图数据
      const radarData = this.prepareRadarChartData(competitiveAnalysis, targetBrand, competitorBrands);

      // P2-3 修复：准备关键词云数据
      const keywordCloudResult = this.prepareKeywordCloudData(semanticDriftAnalysisData.semanticDriftData, results, targetBrand);

      this.setData({
        targetBrand: targetBrand,
        competitiveAnalysis: competitiveAnalysis,
        latestTestResults: results,
        
        // 【容错机制】设置错误和警告
        hasPartialResults: hasErrors || (results && results.some(r => r.status === 'failed' || r.status === 'error')),
        platformErrors: errorMessages,
        
        pkDataByPlatform,
        platforms,
        platformDisplayNames,
        currentPlatform,
        advantageInsight: insights.advantage,
        riskInsight: insights.risk,
        opportunityInsight: insights.opportunity,
        groupedResultsByBrand: groupedResults,
        dimensionComparisonData: dimensionComparison,
        // P0-3 修复：设置竞争分析数据
        ...competitiveAnalysisData,
        // P1-1 修复：设置语义偏移数据
        ...semanticDriftAnalysisData,
        // P1-2 修复：设置信源纯净度数据
        ...sourcePurityAnalysisData,
        // P1-3 修复：设置优化建议数据
        ...recommendationAnalysisData,
        // P2-2 修复：设置雷达图数据
        radarChartData: radarData,
        // P2-3 修复：设置关键词云数据
        keywordCloudData: keywordCloudResult.keywordCloudData,
        topKeywords: keywordCloudResult.topKeywords,
        keywordStats: keywordCloudResult.keywordStats
      }, () => {
        // 数据设置完成后渲染雷达图
        // 【关键修复】使用 wx.nextTick 确保 DOM 完全渲染后再初始化 ECharts
        if (radarData.length > 0) {
          wx.nextTick(() => {
            setTimeout(() => {
              this.renderRadarChart();
            }, 300);
          });
        }

        // 渲染词云
        if (keywordCloudResult.keywordCloudData.length > 0) {
          wx.nextTick(() => {
            setTimeout(() => {
              this.renderWordCloud();
            }, 500);
          });
        }
      });

      console.log('✅ 页面数据初始化完成');

      // P1-017 优化：移除自动弹窗，通过 UI 提示条展示错误信息
      // 用户点击"详情"按钮时才显示弹窗
      // this.showPartialResultsWarning();  // 已移除

      wx.showToast({
        title: '数据加载成功',
        icon: 'success'
      });

    } catch (e) {
      console.error('初始化页面数据失败', e);
      wx.showToast({
        title: '数据加载失败',
        icon: 'none'
      });
    }
  },

  /**
   * P0-1 修复：构建竞争分析数据结构
   */
  buildCompetitiveAnalysis: function(results, targetBrand, competitorBrands) {
    const brandScores = {};
    const firstMentionByPlatform = {};

    // 按品牌分组计算分数
    const brandResults = {};
    results.forEach(result => {
      // 兼容不同数据格式
      const brand = result.brand || result.main_brand || targetBrand;
      if (!brandResults[brand]) {
        brandResults[brand] = [];
      }
      brandResults[brand].push(result);
    });

    // 计算每个品牌的分数
    Object.keys(brandResults).forEach(brand => {
      const scores = brandResults[brand];
      
      // 从 geo_data 中提取分数（兼容后端数据格式）
      let totalScore = 0;
      let totalAuthority = 0;
      let totalVisibility = 0;
      let totalPurity = 0;
      let totalConsistency = 0;
      let count = 0;
      
      scores.forEach(s => {
        // 尝试多种字段名
        let score = s.score;
        let authority = s.authority_score;
        let visibility = s.visibility_score;
        let purity = s.purity_score;
        let consistency = s.consistency_score;
        
        // 如果没有直接字段，从 geo_data 中提取
        if (s.geo_data) {
          const geo = s.geo_data;
          if (score === undefined || score === null) {
            // 从 rank 和 sentiment 计算分数
            const rank = geo.rank || -1;
            const sentiment = geo.sentiment || 0;
            // 排名 1-3 得 90-100 分，4-6 得 70-89 分，7-10 得 50-69 分，未入榜得 30 分
            if (rank > 0) {
              if (rank <= 3) score = 90 + (3 - rank) * 3 + sentiment * 10;
              else if (rank <= 6) score = 70 + (6 - rank) * 3 + sentiment * 10;
              else score = 50 + (10 - rank) * 2 + sentiment * 10;
            } else {
              score = 30 + sentiment * 10;
            }
            score = Math.min(100, Math.max(0, score));
          }
          if (authority === undefined || authority === null) {
            // 从 sentiment 推断权威度
            authority = 50 + sentiment * 25;
          }
          if (visibility === undefined || visibility === null) {
            // 从 rank 推断可见度
            const rank = geo.rank || -1;
            if (rank <= 3) visibility = 90 + sentiment * 10;
            else if (rank <= 6) visibility = 70 + sentiment * 10;
            else if (rank > 0) visibility = 50 + sentiment * 10;
            else visibility = 30 + sentiment * 10;
          }
          if (purity === undefined || purity === null) {
            purity = 70 + sentiment * 15;
          }
          if (consistency === undefined || consistency === null) {
            consistency = 75 + sentiment * 10;
          }
        }
        
        // 如果还是 undefined，使用默认值
        if (score === undefined || score === null) score = 50;
        if (authority === undefined || authority === null) authority = 50;
        if (visibility === undefined || visibility === null) visibility = 50;
        if (purity === undefined || purity === null) purity = 50;
        if (consistency === undefined || consistency === null) consistency = 50;
        
        totalScore += score;
        totalAuthority += authority;
        totalVisibility += visibility;
        totalPurity += purity;
        totalConsistency += consistency;
        count++;
      });
      
      if (count > 0) {
        const avgScore = totalScore / count;
        const avgAuthority = totalAuthority / count;
        const avgVisibility = totalVisibility / count;
        const avgPurity = totalPurity / count;
        const avgConsistency = totalConsistency / count;
        
        // 计算等级
        let grade = 'D';
        if (avgScore >= 90) grade = 'A+';
        else if (avgScore >= 80) grade = 'A';
        else if (avgScore >= 70) grade = 'B';
        else if (avgScore >= 60) grade = 'C';
        
        brandScores[brand] = {
          overallScore: Math.round(avgScore),
          overallGrade: grade,
          overallAuthority: Math.round(avgAuthority),
          overallVisibility: Math.round(avgVisibility),
          overallPurity: Math.round(avgPurity),
          overallConsistency: Math.round(avgConsistency),
          overallSummary: this.getScoreSummary(avgScore)
        };
      }
    });

    return {
      brandScores,
      firstMentionByPlatform,
      interceptionRisks: {}
    };
  },

  /**
   * P0-3 修复：处理竞争分析数据
   */
  processCompetitiveAnalysisData: function(competitiveAnalysis, results, targetBrand, competitorBrands) {
    try {
      // 1. 品牌排名列表（按综合得分排序）
      const brandRankingList = Object.keys(competitiveAnalysis.brandScores || {})
        .sort((a, b) => {
          const scoreA = (competitiveAnalysis.brandScores[a] || {}).overallScore || 0;
          const scoreB = (competitiveAnalysis.brandScores[b] || {}).overallScore || 0;
          return scoreB - scoreA;
        });

      // 2. 首次提及率（从 competitiveAnalysis 中提取）
      const firstMentionByPlatform = [];
      const firstMentionData = competitiveAnalysis.firstMentionByPlatform || {};
      Object.keys(firstMentionData).forEach(platform => {
        const rate = firstMentionData[platform] || 0;
        firstMentionByPlatform.push({
          platform: this.getPlatformDisplayName(platform),
          rate: Math.round(rate * 100)
        });
      });

      // 3. 拦截风险（从 competitiveAnalysis 中提取）
      const interceptionRisks = [];
      const interceptionRiskData = competitiveAnalysis.interceptionRisks || {};
      Object.keys(interceptionRiskData).forEach(type => {
        const risk = interceptionRiskData[type];
        interceptionRisks.push({
          type: this.getRiskTypeName(type),
          level: risk.level || 'medium',
          description: risk.description || '暂无描述'
        });
      });

      // 4. 竞品对比详情（从结果中提取）
      const competitorComparisonData = [];
      const allBrands = [...competitorBrands];
      allBrands.forEach(competitor => {
        // 查找该竞品的对比数据
        const competitorResults = results.filter(r => r.brand === competitor);
        const targetResults = results.filter(r => r.brand === targetBrand);
        
        if (competitorResults.length > 0 && targetResults.length > 0) {
          // 计算差异化评分（基于维度分数差异）
          const competitorAvgScore = competitorResults.reduce((sum, r) => sum + (r.score || 0), 0) / competitorResults.length;
          const targetAvgScore = targetResults.reduce((sum, r) => sum + (r.score || 0), 0) / targetResults.length;
          const differentiationScore = Math.round(100 - Math.abs(competitorAvgScore - targetAvgScore));

          // 提取共同关键词（从响应中提取高频词）
          const commonKeywords = this.extractCommonKeywords(targetResults, competitorResults);
          
          // 提取独特关键词
          const uniqueToBrand = this.extractUniqueKeywords(targetResults, competitorResults);
          const uniqueToCompetitor = this.extractUniqueKeywords(competitorResults, targetResults);

          competitorComparisonData.push({
            competitor: competitor,
            differentiationScore: differentiationScore,
            commonKeywords: commonKeywords.slice(0, 5), // 限制显示数量
            uniqueToBrand: uniqueToBrand.slice(0, 5),
            uniqueToCompetitor: uniqueToCompetitor.slice(0, 5),
            differentiationGap: this.generateDifferentiationGap(targetBrand, competitor, differentiationScore)
          });
        }
      });

      return {
        brandRankingList,
        firstMentionByPlatform,
        interceptionRisks,
        competitorComparisonData
      };
    } catch (e) {
      console.error('处理竞争分析数据失败:', e);
      return {
        brandRankingList: [],
        firstMentionByPlatform: [],
        interceptionRisks: [],
        competitorComparisonData: []
      };
    }
  },

  /**
   * 获取平台显示名称
   */
  getPlatformDisplayName: function(platform) {
    const platformNames = {
      'deepseek': 'DeepSeek',
      'qwen': '通义千问',
      'zhipu': '智谱 AI',
      'doubao': '豆包'
    };
    return platformNames[platform] || platform;
  },

  /**
   * 获取风险类型名称
   */
  getRiskTypeName: function(type) {
    const riskTypes = {
      'visibility': '可见度拦截',
      'sentiment': '情感风险',
      'accuracy': '准确性风险',
      'purity': '纯净度风险'
    };
    return riskTypes[type] || type;
  },

  /**
   * 提取共同关键词
   */
  extractCommonKeywords: function(results1, results2) {
    const keywords1 = this.extractKeywordsFromResults(results1);
    const keywords2 = this.extractKeywordsFromResults(results2);
    return keywords1.filter(k => keywords2.includes(k));
  },

  /**
   * 提取独特关键词
   */
  extractUniqueKeywords: function(results1, results2) {
    const keywords1 = this.extractKeywordsFromResults(results1);
    const keywords2 = this.extractKeywordsFromResults(results2);
    return keywords1.filter(k => !keywords2.includes(k));
  },

  /**
   * 从结果中提取关键词
   */
  extractKeywordsFromResults: function(results) {
    const text = results.map(r => r.response || '').join(' ');
    // 简单的中文分词（实际应用中应该使用更好的分词库）
    const words = text.split(/[\s,，.。！？!？]+/);
    // 过滤停用词和短词
    const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等', '等', '一个', '这个', '这些'];
    return words
      .filter(w => w.length > 1 && !stopWords.includes(w))
      .slice(0, 20); // 限制数量
  },

  /**
   * 生成差异化建议
   */
  generateDifferentiationGap: function(brand1, brand2, score) {
    if (score >= 80) {
      return `${brand1}与${brand2}差异化明显，保持当前优势`;
    } else if (score >= 60) {
      return `${brand1}与${brand2}有一定差异化，建议强化独特卖点`;
    } else {
      return `${brand1}与${brand2}差异化不足，急需建立独特品牌形象`;
    }
  },

  /**
   * P1-1 修复：处理语义偏移数据
   */
  processSemanticDriftData: function(competitiveAnalysis, results, targetBrand, backendSemanticDriftData) {
    try {
      // 【优先使用后端数据】如果传入了后端语义偏移数据，直接使用
      if (backendSemanticDriftData && backendSemanticDriftData.driftScore !== undefined) {
        console.log('✅ 使用后端语义偏移数据');
        return {
          semanticDriftData: backendSemanticDriftData,
          semanticContrastData: competitiveAnalysis.semanticContrastData || null
        };
      }
      
      // 从 backend 获取语义对比数据
      const semanticContrastData = competitiveAnalysis.semanticContrastData || null;

      // 计算语义偏移分数
      let driftScore = 0;
      let driftSeverity = 'low';
      let driftSeverityText = '偏移轻微';
      let similarityScore = 0;

      // 如果有语义对比数据，计算偏移分数
      if (semanticContrastData) {
        const officialWords = semanticContrastData.official_words || [];
        const aiWords = semanticContrastData.ai_generated_words || [];

        // 计算偏移分数（基于 AI 生成词中的风险词比例）
        const riskyWords = aiWords.filter(w => w.category === 'AI_Generated_Risky');
        const totalWords = officialWords.length + aiWords.length;

        if (totalWords > 0) {
          driftScore = Math.round((riskyWords.length / totalWords) * 100);
        }

        // 计算相似度分数
        const commonKeywords = this.extractCommonKeywordsFromWords(officialWords, aiWords);
        const allKeywords = [...new Set([...officialWords.map(w => w.name), ...aiWords.map(w => w.name)])];

        if (allKeywords.length > 0) {
          similarityScore = Math.round((commonKeywords.length / allKeywords.length) * 100);
        }

        // 判断偏移严重程度
        if (driftScore >= 60) {
          driftSeverity = 'high';
          driftSeverityText = '严重偏移';
        } else if (driftScore >= 30) {
          driftSeverity = 'medium';
          driftSeverityText = '中度偏移';
        } else {
          driftSeverity = 'low';
          driftSeverityText = '偏移轻微';
        }
      }

      // 提取缺失和意外的关键词
      let missingKeywords = [];
      let unexpectedKeywords = [];
      let negativeTerms = [];
      let positiveTerms = [];

      if (semanticContrastData) {
        const officialWords = semanticContrastData.official_words || [];
        const aiWords = semanticContrastData.ai_generated_words || [];

        // 官方有但 AI 没有的词
        const officialNames = officialWords.map(w => w.name);
        const aiNames = aiWords.map(w => w.name);

        missingKeywords = officialNames.filter(name => !aiNames.includes(name));
        unexpectedKeywords = aiNames.filter(name => !officialNames.includes(name));

        // 提取负面和正面术语
        negativeTerms = aiWords
          .filter(w => w.sentiment_valence < 0 || w.category === 'AI_Generated_Risky')
          .map(w => w.name);

        positiveTerms = aiWords
          .filter(w => w.sentiment_valence > 0 && w.category !== 'AI_Generated_Risky')
          .map(w => w.name);
      }

      // 如果没有语义对比数据，尝试从结果中提取
      if (!semanticContrastData) {
        const targetResults = results.filter(r => r.brand === targetBrand);
        const allResponses = targetResults.map(r => r.response || '').join(' ');
        
        // 简单的关键词提取
        const words = allResponses.split(/[\s,，.。！？!？]+/);
        const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等'];
        const filteredWords = words
          .filter(w => w.length > 1 && !stopWords.includes(w))
          .slice(0, 20);
        
        unexpectedKeywords = filteredWords.slice(0, 10);
        positiveTerms = filteredWords.slice(10, 15);
        negativeTerms = [];
        
        driftScore = 20; // 默认低偏移
        similarityScore = 80;
        driftSeverity = 'low';
        driftSeverityText = '偏移轻微';
      }
      
      return {
        semanticDriftData: {
          driftScore: driftScore,
          driftSeverity: driftSeverity,
          driftSeverityText: driftSeverityText,
          similarityScore: similarityScore,
          missingKeywords: missingKeywords,
          unexpectedKeywords: unexpectedKeywords,
          negativeTerms: negativeTerms,
          positiveTerms: positiveTerms
        },
        semanticContrastData: semanticContrastData
      };
    } catch (e) {
      console.error('处理语义偏移数据失败:', e);
      return {
        semanticDriftData: null,
        semanticContrastData: null
      };
    }
  },

  /**
   * 从词对象数组中提取共同关键词
   */
  extractCommonKeywordsFromWords: function(words1, words2) {
    const names1 = words1.map(w => w.name);
    const names2 = words2.map(w => w.name);
    return names1.filter(name => names2.includes(name));
  },

  /**
   * P2-3 修复：准备关键词云数据
   */
  prepareKeywordCloudData: function(semanticDriftData, results, targetBrand) {
    try {
      let allKeywords = [];
      
      // 从语义偏移数据中提取关键词
      if (semanticDriftData) {
        // 添加正面术语
        if (semanticDriftData.positiveTerms) {
          semanticDriftData.positiveTerms.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'positive' });
          });
        }
        
        // 添加负面术语
        if (semanticDriftData.negativeTerms) {
          semanticDriftData.negativeTerms.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'negative' });
          });
        }
        
        // 添加意外关键词（中性）
        if (semanticDriftData.unexpectedKeywords) {
          semanticDriftData.unexpectedKeywords.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'neutral' });
          });
        }
      }
      
      // 从 AI 响应中提取更多关键词
      const targetResults = results.filter(r => r.brand === targetBrand);
      const allResponses = targetResults.map(r => r.response || '').join(' ');
      
      // 简单分词和统计
      const words = allResponses.split(/[\s,.。！？!？]+/);
      const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等', '一个', '这个', '这些'];
      
      const wordCount = {};
      words.forEach(word => {
        if (word.length > 1 && !stopWords.includes(word)) {
          wordCount[word] = (wordCount[word] || 0) + 1;
        }
      });
      
      // 合并词频数据
      const keywordMap = {};
      allKeywords.forEach(item => {
        keywordMap[item.word] = {
          word: item.word,
          count: wordCount[item.word] || 1,
          sentiment: item.sentiment
        };
      });
      
      // 转换为数组并排序
      const keywordData = Object.values(keywordMap)
        .sort((a, b) => b.count - a.count)
        .slice(0, 50);  // 限制最多 50 个词
      
      // 计算权重（用于字体大小）
      const maxCount = keywordData.length > 0 ? keywordData[0].count : 1;
      keywordData.forEach(item => {
        item.weight = item.count / maxCount;
      });
      
      // 统计情感分布
      const stats = {
        positiveCount: keywordData.filter(k => k.sentiment === 'positive').length,
        neutralCount: keywordData.filter(k => k.sentiment === 'neutral').length,
        negativeCount: keywordData.filter(k => k.sentiment === 'negative').length
      };
      
      // 高频词（Top 10）
      const topKeywords = keywordData.slice(0, 10);
      
      return {
        keywordCloudData: keywordData,
        topKeywords: topKeywords,
        keywordStats: stats
      };
    } catch (e) {
      console.error('准备关键词云数据失败:', e);
      return {
        keywordCloudData: [],
        topKeywords: [],
        keywordStats: {
          positiveCount: 0,
          neutralCount: 0,
          negativeCount: 0
        }
      };
    }
  },

  /**
   * P2-3 修复：渲染关键词云
   * 【关键修复】添加重试机制和更好的错误处理
   */
  renderWordCloud: function(retryCount) {
    try {
      const query = wx.createSelectorQuery();
      query.select('#wordCloudCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0] || !res[0].node) {
            console.error('❌ 词云 Canvas not found');
            // 【关键修复】重试机制，最多重试 3 次
            const currentRetry = retryCount || 0;
            if (currentRetry < 3) {
              console.log(`🔄 词云 Canvas 未找到，${currentRetry + 1}/3 重试...`);
              setTimeout(() => {
                this.renderWordCloud(currentRetry + 1);
              }, 500);
            }
            return;
          }

          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;

          // 设置 Canvas 尺寸
          const width = this.data.wordCloudCanvasWidth;
          const height = this.data.wordCloudCanvasHeight;
          canvas.width = width * dpr;
          canvas.height = height * dpr;
          ctx.scale(dpr, dpr);

          const data = this.data.keywordCloudData;
          const centerX = width / 2;
          const centerY = height / 2;

          // 清空画布
          ctx.clearRect(0, 0, width, height);

          // 绘制词云
          this.drawWordCloud(ctx, centerX, centerY, data);

          this.setData({ wordCloudRendered: true });
          console.log('✅ 词云渲染成功');
        });
    } catch (e) {
      console.error('渲染词云失败:', e);
    }
  },

  /**
   * 绘制关键词云
   */
  drawWordCloud: function(ctx, centerX, centerY, data) {
    const placedWords = [];
    const maxRadius = Math.min(centerX, centerY) - 40;
    
    // 情感颜色映射
    const sentimentColors = {
      'positive': '#00F5A0',  // 绿色
      'neutral': '#00A9FF',   // 蓝色
      'negative': '#F44336'   // 红色
    };
    
    data.forEach((item, index) => {
      // 计算字体大小（12-28px）
      const fontSize = Math.round(12 + item.weight * 16);
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = sentimentColors[item.sentiment] || '#FFFFFF';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // 计算位置（螺旋布局）
      const angle = index * 0.5;  // 黄金角度
      const radius = (index / data.length) * maxRadius;
      let x = centerX + Math.cos(angle) * radius;
      let y = centerY + Math.sin(angle) * radius;
      
      // 简单的碰撞检测
      let overlap = false;
      const wordWidth = ctx.measureText(item.word).width;
      const wordHeight = fontSize;
      
      for (let placed of placedWords) {
        const dx = x - placed.x;
        const dy = y - placed.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < (wordWidth + placed.width) / 2) {
          overlap = true;
          break;
        }
      }
      
      // 如果不重叠，绘制并记录
      if (!overlap || index < 5) {  // 前 5 个词强制显示
        ctx.fillText(item.word, x, y);
        placedWords.push({
          x: x,
          y: y,
          width: wordWidth,
          height: wordHeight
        });
      }
    });
  },

  /**
   * P2-2 修复：准备雷达图数据
   */
  prepareRadarChartData: function(competitiveAnalysis, targetBrand, competitorBrands) {
    try {
      if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
        return [];
      }
      
      const brandScores = competitiveAnalysis.brandScores;
      const targetScores = brandScores[targetBrand] || {};
      
      // 计算竞品平均分
      let competitorScores = {};
      let competitorCount = 0;
      
      competitorBrands.forEach(brand => {
        if (brandScores[brand]) {
          competitorCount++;
          const scores = brandScores[brand];
          Object.keys(scores).forEach(key => {
            if (key.startsWith('overall') && key !== 'overallScore' && key !== 'overallGrade' && key !== 'overallSummary') {
              competitorScores[key] = (competitorScores[key] || 0) + (scores[key] || 0);
            }
          });
        }
      });
      
      // 计算平均值
      if (competitorCount > 0) {
        Object.keys(competitorScores).forEach(key => {
          competitorScores[key] = Math.round(competitorScores[key] / competitorCount);
        });
      }
      
      // 构建雷达图数据（5 个维度）
      const dimensionMap = {
        'overallAuthority': '权威度',
        'overallVisibility': '可见度',
        'overallSentiment': '好感度',
        'overallPurity': '纯净度',
        'overallConsistency': '一致性'
      };
      
      const radarData = [];
      Object.keys(dimensionMap).forEach(key => {
        radarData.push({
          dimension: dimensionMap[key],
          myBrand: targetScores[key] || 0,
          competitor: competitorScores[key] || 0
        });
      });
      
      return radarData;
    } catch (e) {
      console.error('准备雷达图数据失败:', e);
      return [];
    }
  },

  /**
   * P2-2 修复：渲染雷达图
   * 【关键修复】添加重试机制和更好的错误处理
   */
  renderRadarChart: function(retryCount) {
    try {
      const query = wx.createSelectorQuery();
      query.select('#radarChartCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0] || !res[0].node) {
            console.error('❌ 雷达图 Canvas not found');
            // 【关键修复】重试机制，最多重试 3 次
            const currentRetry = retryCount || 0;
            if (currentRetry < 3) {
              console.log(`🔄 雷达图 Canvas 未找到，${currentRetry + 1}/3 重试...`);
              setTimeout(() => {
                this.renderRadarChart(currentRetry + 1);
              }, 500);
            }
            return;
          }

          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;

          // 设置 Canvas 尺寸
          const width = this.data.canvasWidth;
          const height = this.data.canvasHeight;
          canvas.width = width * dpr;
          canvas.height = height * dpr;
          ctx.scale(dpr, dpr);

          const centerX = width / 2;
          const centerY = height / 2;
          const radius = Math.min(width, height) / 2 - 40;
          const data = this.data.radarChartData;

          // 清空画布
          ctx.clearRect(0, 0, width, height);

          // 绘制背景网格（5 边形）
          this.drawRadarGrid(ctx, centerX, centerY, radius);

          // 绘制数据区域
          this.drawRadarData(ctx, centerX, centerY, radius, data);

          this.setData({ radarChartRendered: true });
          console.log('✅ 雷达图渲染成功');
        });
    } catch (e) {
      console.error('渲染雷达图失败:', e);
    }
  },

  /**
   * 绘制雷达图网格
   */
  drawRadarGrid: function(ctx, centerX, centerY, radius) {
    const levels = 5;
    const angleStep = (Math.PI * 2) / 5;
    
    for (let level = 1; level <= levels; level++) {
      const levelRadius = (radius / levels) * level;
      ctx.beginPath();
      
      for (let i = 0; i <= 5; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const x = centerX + Math.cos(angle) * levelRadius;
        const y = centerY + Math.sin(angle) * levelRadius;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      ctx.closePath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    
    // 绘制维度轴线
    for (let i = 0; i < 5; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
      
      // 绘制维度标签
      const labelAngle = i * angleStep - Math.PI / 2;
      const labelRadius = radius + 20;
      const labelX = centerX + Math.cos(labelAngle) * labelRadius;
      const labelY = centerY + Math.sin(labelAngle) * labelRadius;
      
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(this.data.radarChartData[i].dimension, labelX, labelY);
    }
  },

  /**
   * 绘制雷达图数据
   */
  drawRadarData: function(ctx, centerX, centerY, radius, data) {
    const angleStep = (Math.PI * 2) / 5;
    
    // 绘制目标品牌区域（绿色）
    ctx.beginPath();
    for (let i = 0; i <= 5; i++) {
      const dataIndex = i % 5;
      const angle = i * angleStep - Math.PI / 2;
      const value = data[dataIndex].myBrand;
      const pointRadius = (value / 100) * radius;
      const x = centerX + Math.cos(angle) * pointRadius;
      const y = centerY + Math.sin(angle) * pointRadius;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 245, 160, 0.3)';
    ctx.fill();
    ctx.strokeStyle = '#00F5A0';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 绘制竞品平均区域（蓝色）
    ctx.beginPath();
    for (let i = 0; i <= 5; i++) {
      const dataIndex = i % 5;
      const angle = i * angleStep - Math.PI / 2;
      const value = data[dataIndex].competitor;
      const pointRadius = (value / 100) * radius;
      const x = centerX + Math.cos(angle) * pointRadius;
      const y = centerY + Math.sin(angle) * pointRadius;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 169, 255, 0.3)';
    ctx.fill();
    ctx.strokeStyle = '#00A9FF';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 绘制数据点
    for (let i = 0; i < 5; i++) {
      const angle = i * angleStep - Math.PI / 2;
      
      // 目标品牌数据点
      const myBrandRadius = (data[i].myBrand / 100) * radius;
      const myBrandX = centerX + Math.cos(angle) * myBrandRadius;
      const myBrandY = centerY + Math.sin(angle) * myBrandRadius;
      
      ctx.beginPath();
      ctx.arc(myBrandX, myBrandY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00F5A0';
      ctx.fill();
      
      // 竞品平均数据点
      const competitorRadius = (data[i].competitor / 100) * radius;
      const competitorX = centerX + Math.cos(angle) * competitorRadius;
      const competitorY = centerY + Math.sin(angle) * competitorRadius;
      
      ctx.beginPath();
      ctx.arc(competitorX, competitorY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00A9FF';
      ctx.fill();
    }
  },

  /**
   * P1-3 修复：处理优化建议数据
   */
  processRecommendationData: function(competitiveAnalysis, results, negativeSources, backendRecommendationData) {
    try {
      // 【优先使用后端数据】如果传入了后端优化建议数据，直接使用
      if (backendRecommendationData && backendRecommendationData.recommendations) {
        console.log('✅ 使用后端优化建议数据');
        return { recommendationData: backendRecommendationData };
      }
      
      // 从 backend 获取建议数据
      const recommendations = competitiveAnalysis.recommendations || [];

      if (!recommendations || recommendations.length === 0) {
        return { recommendationData: null };
      }
      
      // 统计各优先级数量
      let highPriorityCount = 0;
      let mediumPriorityCount = 0;
      let lowPriorityCount = 0;
      
      // 处理每条建议
      const processedRecommendations = recommendations.map(rec => {
        // 统计优先级
        if (rec.priority === 'high') highPriorityCount++;
        else if (rec.priority === 'medium') mediumPriorityCount++;
        else if (rec.priority === 'low') lowPriorityCount++;
        
        // 转换优先级文本
        const priorityTextMap = {
          'high': '高优先级',
          'medium': '中优先级',
          'low': '低优先级'
        };
        
        // 转换类型文本
        const typeTextMap = {
          'content_correction': '内容纠偏',
          'brand_strengthening': '品牌强化',
          'source_attack': '信源攻坚',
          'risk_mitigation': '风险缓解'
        };
        
        // 转换预估影响文本
        const impactTextMap = {
          'high': '高影响',
          'medium': '中影响',
          'low': '低影响'
        };
        
        return {
          priority: rec.priority || 'medium',
          priorityText: priorityTextMap[rec.priority] || '中优先级',
          type: rec.type || 'content_correction',
          typeText: typeTextMap[rec.type] || '内容纠偏',
          title: rec.title || '优化建议',
          description: rec.description || '',
          target: rec.target || '',
          estimatedImpact: rec.estimated_impact || 'medium',
          estimatedImpactText: impactTextMap[rec.estimated_impact] || '中影响',
          actionSteps: rec.action_steps || [],
          urgency: rec.urgency || 5
        };
      });
      
      return {
        recommendationData: {
          totalCount: recommendations.length,
          highPriorityCount: highPriorityCount,
          mediumPriorityCount: mediumPriorityCount,
          lowPriorityCount: lowPriorityCount,
          recommendations: processedRecommendations
        }
      };
    } catch (e) {
      console.error('处理优化建议数据失败:', e);
      return {
        recommendationData: null
      };
    }
  },

  /**
   * P1-2 修复：处理信源纯净度数据
   */
  processSourcePurityData: function(competitiveAnalysis, results) {
    try {
      // 从 backend 获取信源情报图谱
      const sourceIntelligenceMap = competitiveAnalysis.sourceIntelligenceMap || null;
      
      let purityScore = 0;
      let purityLevel = 'high';
      let purityLevelText = '优秀';
      let highWeightRatio = 0;
      let pollutionCount = 0;
      let categoryDistribution = [];
      let topSources = [];
      let pollutionSources = [];
      
      if (sourceIntelligenceMap && sourceIntelligenceMap.nodes) {
        const nodes = sourceIntelligenceMap.nodes;
        
        // 过滤掉品牌节点
        const sourceNodes = nodes.filter(n => n.level > 0);
        
        // 计算纯净度分数
        const highWeightSources = sourceNodes.filter(n => n.value >= 7);
        const mediumWeightSources = sourceNodes.filter(n => n.value >= 4 && n.value < 7);
        const lowWeightSources = sourceNodes.filter(n => n.value < 4);
        const riskSources = sourceNodes.filter(n => n.category === 'risk' || n.sentiment === 'negative');
        
        const totalSources = sourceNodes.length;
        
        if (totalSources > 0) {
          // 纯净度 = (高权重源数量 * 100 + 中权重源数量 * 70 + 低权重源数量 * 30) / 总源数量
          purityScore = Math.round(
            (highWeightSources.length * 100 + mediumWeightSources.length * 70 + lowWeightSources.length * 30) / totalSources
          );
          
          // 高权重信源占比
          highWeightRatio = Math.round((highWeightSources.length / totalSources) * 100);
          
          // 污染源数量
          pollutionCount = riskSources.length;
          
          // 判断纯净度等级
          if (purityScore >= 80) {
            purityLevel = 'high';
            purityLevelText = '优秀';
          } else if (purityScore >= 60) {
            purityLevel = 'medium';
            purityLevelText = '良好';
          } else if (purityScore >= 40) {
            purityLevel = 'low';
            purityLevelText = '一般';
          } else {
            purityLevel = 'critical';
            purityLevelText = '较差';
          }
        }
        
        // 信源类别分布
        const categoryCount = {};
        sourceNodes.forEach(node => {
          const cat = node.category || 'other';
          if (!categoryCount[cat]) {
            categoryCount[cat] = 0;
          }
          categoryCount[cat]++;
        });
        
        const categoryNames = {
          'social': '社交媒体',
          'wiki': '百科',
          'tech': '科技媒体',
          'news': '新闻媒体',
          'official': '官方',
          'finance': '财经',
          'risk': '风险源',
          'other': '其他'
        };
        
        Object.keys(categoryCount).forEach(cat => {
          const count = categoryCount[cat];
          categoryDistribution.push({
            category: cat,
            categoryName: categoryNames[cat] || cat,
            count: count,
            percentage: totalSources > 0 ? Math.round((count / totalSources) * 100) : 0
          });
        });
        
        // 信源权重排名（Top 10）
        topSources = sourceNodes
          .sort((a, b) => (b.value || 0) - (a.value || 0))
          .slice(0, 10)
          .map(node => ({
            name: node.name,
            weight: node.value || 0,
            isHighWeight: node.value >= 7
          }));
        
        // 污染源
        pollutionSources = riskSources.map(node => ({
          name: node.name,
          reason: node.sentiment === 'negative' ? '负面情感' : '风险源'
        }));
      }
      
      // 如果没有信源情报数据，使用默认值
      if (!sourceIntelligenceMap || !sourceIntelligenceMap.nodes) {
        purityScore = 70;
        purityLevel = 'medium';
        purityLevelText = '良好';
        highWeightRatio = 50;
        pollutionCount = 0;
        categoryDistribution = [
          { category: 'social', categoryName: '社交媒体', count: 3, percentage: 50 },
          { category: 'news', categoryName: '新闻媒体', count: 2, percentage: 33 },
          { category: 'official', categoryName: '官方', count: 1, percentage: 17 }
        ];
        topSources = [
          { name: '知乎', weight: 7, isHighWeight: true },
          { name: '36Kr', weight: 6, isHighWeight: false },
          { name: '官网', weight: 9, isHighWeight: true }
        ];
        pollutionSources = [];
      }
      
      return {
        sourcePurityData: {
          purityScore: purityScore,
          purityLevel: purityLevel,
          purityLevelText: purityLevelText,
          highWeightRatio: highWeightRatio,
          pollutionCount: pollutionCount,
          categoryDistribution: categoryDistribution,
          topSources: topSources,
          pollutionSources: pollutionSources
        },
        sourceIntelligenceMap: sourceIntelligenceMap
      };
    } catch (e) {
      console.error('处理信源纯净度数据失败:', e);
      return {
        sourcePurityData: null,
        sourceIntelligenceMap: null
      };
    }
  },

  /**
   * 获取分数对应的总结描述
   */
  getScoreSummary: function(score) {
    if (score >= 90) return '表现卓越，行业标杆';
    if (score >= 80) return '表现优秀，保持领先';
    if (score >= 70) return '表现良好，稳中有进';
    if (score >= 60) return '表现一般，有待提升';
    return '表现较弱，急需改进';
  },

  // 生成洞察摘要
  generateInsights: function(competitiveAnalysis, targetBrand) {
    if (!competitiveAnalysis || !competitiveAnalysis.brandScores || !targetBrand) {
      return {
        advantage: '数据不足，无法生成洞察',
        risk: '数据不足，无法生成洞察',
        opportunity: '数据不足，无法生成洞察'
      };
    }

    const brandData = competitiveAnalysis.brandScores[targetBrand];
    if (!brandData) {
      return {
        advantage: '品牌数据缺失',
        risk: '品牌数据缺失',
        opportunity: '品牌数据缺失'
      };
    }

    const authority = brandData.overallAuthority || 0;
    const visibility = brandData.overallVisibility || 0;
    const purity = brandData.overallPurity || 0;
    const consistency = brandData.overallConsistency || 0;

    // 生成优势洞察
    let advantage = '表现良好的领域：';
    if (authority >= 80) advantage += '权威度优秀，';
    if (visibility >= 80) advantage += '可见度优秀，';
    if (purity >= 80) advantage += '纯净度优秀，';
    if (consistency >= 80) advantage += '一致性优秀，';
    if (advantage === '表现良好的领域：') advantage = '暂无特别突出的优势';

    // 生成风险洞察
    let risk = '需要关注的领域：';
    if (authority < 60) risk += '权威度较低，';
    if (visibility < 60) risk += '可见度较低，';
    if (purity < 60) risk += '纯净度较低，';
    if (consistency < 60) risk += '一致性较低，';
    if (risk === '需要关注的领域：') risk = '暂无明显风险';

    // 生成机会洞察
    let opportunity = '可提升的领域：';
    if (authority < 80 && authority >= 60) opportunity += '权威度有提升空间，';
    if (visibility < 80 && visibility >= 60) opportunity += '可见度有提升空间，';
    if (purity < 80 && purity >= 60) opportunity += '纯净度有提升空间，';
    if (consistency < 80 && consistency >= 60) opportunity += '一致性有提升空间，';
    if (opportunity === '可提升的领域：') opportunity = '各维度均有提升空间';

    return {
      advantage: advantage.replace(/,$/, ''),
      risk: risk.replace(/,$/, ''),
      opportunity: opportunity.replace(/,$/, '')
    };
  },

  // 获取维度状态描述
  getDimensionStatus: function(score, dimension) {
    if (score >= 85) return '优秀';
    if (score >= 70) return '良好';
    if (score >= 50) return '一般';
    return '待优化';
  },

  // P0-012 新增：获取质量等级文本
  getQualityLevelText: function(level) {
    const levelMap = {
      'excellent': '优秀',
      'good': '良好',
      'fair': '一般',
      'poor': '较差'
    };
    return levelMap[level] || '未知';
  },

  // 【完整性修复】格式化日期时间
  formatDateTime: function(dateTimeStr) {
    if (!dateTimeStr) return '';
    try {
      const date = new Date(dateTimeStr);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    } catch (e) {
      return dateTimeStr;
    }
  },

  // 切换平台
  switchPlatform: function(e) {
    const platform = e.currentTarget.dataset.platform;
    this.setData({
      currentPlatform: platform
    });
  },

  // 切换视图模式
  switchViewMode: function(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({
      currentViewMode: mode
    });
  },

  // 按品牌分组结果
  groupResultsByBrand: function(results, mainBrand) {
    if (!results || !Array.isArray(results)) {
      return [];
    }

    const grouped = {};
    results.forEach(item => {
      const brand = item.brand;
      if (!grouped[brand]) {
        grouped[brand] = {
          brand: brand,
          isMainBrand: brand === mainBrand,
          scores: {
            authority_score: 0,
            visibility_score: 0,
            purity_score: 0,
            consistency_score: 0
          },
          overallScore: 0,
          questions: []
        };
      }

      grouped[brand].scores.authority_score += item.authority_score || 0;
      grouped[brand].scores.visibility_score += item.visibility_score || 0;
      grouped[brand].scores.purity_score += item.purity_score || 0;
      grouped[brand].scores.consistency_score += item.consistency_score || 0;

      grouped[brand].questions.push({
        question: item.question,
        response: item.response
      });
    });

    Object.keys(grouped).forEach(brand => {
      const brandData = grouped[brand];
      const count = brandData.questions.length;
      brandData.scores.authority_score = Math.round(brandData.scores.authority_score / count) || 0;
      brandData.scores.visibility_score = Math.round(brandData.scores.visibility_score / count) || 0;
      brandData.scores.purity_score = Math.round(brandData.scores.purity_score / count) || 0;
      brandData.scores.consistency_score = Math.round(brandData.scores.consistency_score / count) || 0;
      brandData.overallScore = Math.round((brandData.scores.authority_score +
                                         brandData.scores.visibility_score +
                                         brandData.scores.purity_score +
                                         brandData.scores.consistency_score) / 4) || 0;
    });

    return Object.values(grouped).sort((a, b) => {
      if (a.isMainBrand && !b.isMainBrand) return -1;
      if (!a.isMainBrand && b.isMainBrand) return 1;
      return b.overallScore - a.overallScore;
    });
  },

  // 生成维度对比数据
  generateDimensionComparison: function(results, mainBrand) {
    if (!results || !Array.isArray(results)) {
      return [];
    }

    const dimensions = ['authority_score', 'visibility_score', 'purity_score', 'consistency_score'];
    const dimensionIcons = {
      'authority_score': '🏆',
      'visibility_score': '👁️',
      'purity_score': '✨',
      'consistency_score': '🔗'
    };
    const dimensionNames = {
      'authority_score': '权威度',
      'visibility_score': '可见度',
      'purity_score': '纯净度',
      'consistency_score': '一致性'
    };

    const comparisonData = [];

    dimensions.forEach(dim => {
      const brandScores = {};
      results.forEach(item => {
        const brand = item.brand;
        if (!brandScores[brand]) {
          brandScores[brand] = {
            brand: brand,
            isMainBrand: brand === mainBrand,
            score: 0,
            count: 0
          };
        }
        brandScores[brand].score += item[dim] || 0;
        brandScores[brand].count++;
      });

      Object.keys(brandScores).forEach(brand => {
        brandScores[brand].score = Math.round(brandScores[brand].score / brandScores[brand].count) || 0;
      });

      const allScores = Object.values(brandScores).map(b => b.score);
      const averageScore = allScores.length > 0 ? Math.round(allScores.reduce((a, b) => a + b, 0) / allScores.length) : 0;

      const brands = Object.values(brandScores).sort((a, b) => b.score - a.score);

      comparisonData.push({
        name: dimensionNames[dim],
        icon: dimensionIcons[dim],
        dimension: dim,
        averageScore: averageScore,
        brands: brands
      });
    });

    return comparisonData;
  },

  // 切换品牌问题详情
  toggleBrandQuestions: function(e) {
    const brand = e.currentTarget.dataset.brand;
    const expandedBrands = this.data.expandedBrands;
    expandedBrands[brand] = !expandedBrands[brand];

    this.setData({
      expandedBrands: {...expandedBrands}
    });
  },

  // 从本地存储加载数据
  loadFromCache: function() {
    // 【P0 修复】优先尝试带 executionId 的 key，然后尝试不带 executionId 的 key
    const executionId = this.data.executionId || '';
    
    // 尝试多种 key 组合
    let cachedResults = wx.getStorageSync('latestTestResults_' + executionId);
    if (!cachedResults || !cachedResults.length) {
      cachedResults = wx.getStorageSync('latestTestResults');
    }
    
    let cachedAnalysis = wx.getStorageSync('latestCompetitiveAnalysis_' + executionId);
    if (!cachedAnalysis || !cachedAnalysis.brandScores) {
      cachedAnalysis = wx.getStorageSync('latestCompetitiveAnalysis');
    }
    
    const cachedBrand = wx.getStorageSync('latestTargetBrand');
    const cachedCompetitors = wx.getStorageSync('latestCompetitorBrands');
    
    // 新增：加载语义偏移和优化建议数据
    const cachedSemanticDrift = wx.getStorageSync('latestSemanticDrift_' + executionId) || wx.getStorageSync('latestSemanticDrift');
    const cachedRecommendations = wx.getStorageSync('latestRecommendations_' + executionId) || wx.getStorageSync('latestRecommendations');
    const cachedNegativeSources = wx.getStorageSync('latestNegativeSources_' + executionId) || wx.getStorageSync('latestNegativeSources');

    if (cachedResults && cachedAnalysis && cachedBrand) {
      try {
        const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(cachedAnalysis, cachedBrand, cachedResults);

        const currentPlatform = platforms.length > 0 ? platforms[0] : '';
        const insights = this.generateInsights(cachedAnalysis, cachedBrand);
        const groupedResults = this.groupResultsByBrand(cachedResults, cachedBrand);
        const dimensionComparison = this.generateDimensionComparison(cachedResults, cachedBrand);

        this.setData({
          targetBrand: cachedBrand,
          competitiveAnalysis: cachedAnalysis,
          latestTestResults: cachedResults,
          pkDataByPlatform,
          platforms,
          platformDisplayNames,
          currentPlatform,
          advantageInsight: insights.advantage,
          riskInsight: insights.risk,
          opportunityInsight: insights.opportunity,
          groupedResultsByBrand: groupedResults,
          dimensionComparisonData: dimensionComparison
        });

        wx.showToast({
          title: '已从缓存加载上次结果',
          icon: 'none'
        });
      } catch (e) {
        console.error('从缓存加载数据失败', e);
        wx.showToast({
          title: '无可用结果数据',
          icon: 'none'
        });
      }
    } else {
      wx.showToast({
        title: '无可用结果数据',
        icon: 'none'
      });
    }
  },

  generatePKDataByPlatform: function(competitiveAnalysis, targetBrand, results) {
    const pkDataByPlatform = {};
    const platforms = new Set();
    const platformDisplayNames = {};

    if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
      console.warn('Invalid competitive analysis data');
      return { pkDataByPlatform: {}, platforms: [], platformDisplayNames: {} };
    }

    const allBrands = Object.keys(competitiveAnalysis.brandScores);
    const competitors = allBrands.filter(b => b !== targetBrand);

    // P0-008 新增：收集错误平台信息
    const errorPlatforms = {};
    const quotaExhaustedPlatforms = {};
    if (results && Array.isArray(results)) {
      results.forEach(item => {
        if (item.aiModel && item.error) {
          // 标记有错误的平台
          errorPlatforms[item.aiModel] = true;
          // 标记配额用尽的平台
          if (item.error_type === 'quota_exhausted' || item.error_type === 'insufficient_quota') {
            quotaExhaustedPlatforms[item.aiModel] = true;
          }
        }
      });
    }

    if (results && Array.isArray(results)) {
      results.forEach(item => {
        if (item.aiModel) {
          platforms.add(item.aiModel);
          platformDisplayNames[item.aiModel] = item.aiModel;
        }
      });
    } else if (competitiveAnalysis.firstMentionByPlatform) {
      Object.keys(competitiveAnalysis.firstMentionByPlatform).forEach(platform => {
        platforms.add(platform);
        platformDisplayNames[platform] = platform;
      });
    }

    Array.from(platforms).forEach(platform => {
      pkDataByPlatform[platform] = [];

      competitors.forEach(comp => {
        const myBrandData = competitiveAnalysis.brandScores[targetBrand] || { overallScore: 0, overallGrade: 'D' };
        const competitorData = competitiveAnalysis.brandScores[comp] || { overallScore: 0, overallGrade: 'D' };

        // P0-008 新增：添加错误标记
        const myBrandDataWithBrand = {
          ...myBrandData,
          brand: targetBrand,
          hasError: !!errorPlatforms[platform],
          isQuotaExhausted: !!quotaExhaustedPlatforms[platform],
          errorMessage: errorPlatforms[platform] ? 'AI 调用失败' : null
        };
        const competitorDataWithBrand = { ...competitorData, brand: comp };

        pkDataByPlatform[platform].push({
          myBrandData: myBrandDataWithBrand,
          competitorData: competitorDataWithBrand
        });
      });
    });

    return {
      pkDataByPlatform,
      platforms: Array.from(platforms),
      platformDisplayNames
    };
  },

  onSwiperChange: function(e) {
    this.setData({
      currentSwiperIndex: e.detail.current
    });
  },

  goHome: function() {
    if (this.data.latestTestResults && this.data.competitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.competitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    wx.reLaunch({ url: '/pages/index/index' });
  },

  generateReport: function() {
    // 使用 PDF 导出工具生成完整报告
    generateFullReport(this);
  },

  viewHistory: function() {
    if (this.data.latestTestResults && this.data.competitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.competitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    // 跳转到个人历史记录页面（查看本地保存的结果，无需登录）
    wx.navigateTo({
      url: '/pages/personal-history/personal-history'
    });
  },

  // 保存结果功能
  saveResult: function() {
    this.setData({
      showSaveResultModal: true,
      saveBrandName: this.data.targetBrand,
      saveTags: [],
      saveNotes: '',
      saveAsFavorite: false,
      newSaveTag: '',
      saveCategoryIndex: 0,
      selectedSaveCategory: '未分类'
    });
  },

  hideSaveResultModal: function() {
    this.setData({
      showSaveResultModal: false
    });
  },

  onSaveBrandNameInput: function(e) {
    this.setData({
      saveBrandName: e.detail.value
    });
  },

  onNewSaveTagInput: function(e) {
    this.setData({
      newSaveTag: e.detail.value
    });
  },

  addSaveTag: function() {
    if (this.data.newSaveTag.trim() && !this.data.saveTags.includes(this.data.newSaveTag.trim())) {
      const tags = [...this.data.saveTags, this.data.newSaveTag.trim()];
      this.setData({
        saveTags: tags,
        newSaveTag: ''
      });
    }
  },

  removeSaveTag: function(e) {
    const index = e.currentTarget.dataset.index;
    const tags = [...this.data.saveTags];
    tags.splice(index, 1);
    this.setData({
      saveTags: tags
    });
  },

  onSaveCategoryChange: function(e) {
    const index = e.detail.value;
    const categories = ['未分类', '日常监测', '竞品分析', '季度报告', '年度总结'];
    const category = categories[index];
    this.setData({
      saveCategoryIndex: index,
      selectedSaveCategory: category
    });
  },

  onSaveNotesInput: function(e) {
    this.setData({
      saveNotes: e.detail.value
    });
  },

  onSaveFavoriteChange: function(e) {
    this.setData({
      saveAsFavorite: e.detail.value
    });
  },

  confirmSaveResult: function() {
    if (!this.data.saveBrandName.trim()) {
      wx.showToast({
        title: '请输入品牌名称',
        icon: 'none'
      });
      return;
    }

    const that = this;

    try {
      const saveData = {
        id: Date.now().toString(),
        timestamp: Date.now(),
        brandName: this.data.saveBrandName.trim(),
        results: {
          ...this.data.competitiveAnalysis,
          overallScore: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallScore || 0,
          overallAuthority: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallAuthority || 0,
          overallVisibility: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallVisibility || 0,
          overallPurity: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallPurity || 0,
          overallConsistency: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallConsistency || 0
        },
        tags: this.data.saveTags,
        category: this.data.selectedSaveCategory,
        notes: this.data.saveNotes,
        isFavorite: this.data.saveAsFavorite
      };

      // 使用云端同步工具保存结果
      saveResult(saveData)
        .then(() => {
          that.setData({
            showSaveResultModal: false
          });

          wx.showToast({
            title: '保存成功',
            icon: 'success'
          });
        })
        .catch(error => {
          console.error('保存搜索结果失败', error);
          wx.showToast({
            title: '保存失败',
            icon: 'none'
          });
        });
    } catch (e) {
      console.error('保存搜索结果失败', e);
      wx.showToast({
        title: '保存失败',
        icon: 'none'
      });
    }
  },

  // 查看信源详情
  viewSourceDetails: function(e) {
    const sourceId = e.currentTarget.dataset.id;
    const source = this.data.sourceIntelligenceMap.nodes.find(node => node.id === sourceId);

    if (source) {
      wx.showModal({
        title: source.name,
        content: `类型：${source.category}\n权重：${source.value || 'N/A'}\n情感：${source.sentiment || 'N/A'}`,
        showCancel: false,
        confirmText: '确定'
      });
    }
  },

  /**
   * P1-1: 计算各平台的首次提及率
   */
  calculateFirstMentionByPlatform: function(results) {
    try {
      const platformMentions = {};
      
      results.forEach(result => {
        const platform = result.model || result.aiModel || 'unknown';
        if (!platformMentions[platform]) {
          platformMentions[platform] = { total: 0, firstMention: 0 };
        }
        platformMentions[platform].total++;
        if (result.geo_data?.brand_mentioned) {
          platformMentions[platform].firstMention++;
        }
      });

      const result = Object.entries(platformMentions).map(([platform, data]) => ({
        platform: this.getPlatformDisplayName(platform),
        rate: Math.round(data.firstMention / data.total * 100) || 0
      }));

      console.log('✅ 首次提及率计算完成:', result);
      return result;
    } catch (e) {
      console.error('计算首次提及率失败:', e);
      return [];
    }
  },

  /**
   * 获取平台显示名称
   */
  getPlatformDisplayName: function(platform) {
    const map = {
      'deepseek': 'DeepSeek',
      'deepseekr1': 'DeepSeek R1',
      'qwen': '通义千问',
      'doubao': '豆包',
      'chatgpt': 'ChatGPT',
      'gemini': 'Gemini',
      'zhipu': '智谱 AI',
      'wenxin': '文心一言'
    };
    return map[platform] || platform;
  },

  /**
   * P1-2: 分析竞品流量拦截风险
   */
  calculateInterceptionRisks: function(results, targetBrand) {
    try {
      const competitorMentions = {};
      
      results.forEach(result => {
        if (result.brand && result.brand !== targetBrand && result.geo_data?.brand_mentioned) {
          const competitor = result.brand;
          if (!competitorMentions[competitor]) {
            competitorMentions[competitor] = 0;
          }
          competitorMentions[competitor]++;
        }
      });

      const risks = Object.entries(competitorMentions).map(([competitor, count]) => {
        const level = count > 5 ? 'high' : count > 3 ? 'medium' : 'low';
        return {
          type: 'competitor_interception',
          level: level,
          description: `${competitor} 被提及${count}次，存在${level === 'high' ? '严重' : level === 'medium' ? '中等' : '轻微'}的流量拦截风险`
        };
      });

      console.log('✅ 拦截风险分析完成:', risks);
      return risks;
    } catch (e) {
      console.error('分析拦截风险失败:', e);
      return [];
    }
  },

  /**
   * P1-3: 完整数据验证报告
   */
  validateDataIntegrity: function(results, brandScores, insights, semanticDriftData, recommendationData, sourcePurityData, sourceIntelligenceMap, targetBrand) {
    const validation = {
      hasResults: results && results.length > 0,
      resultsCount: results ? results.length : 0,
      hasBrandScores: brandScores && Object.keys(brandScores).length > 0,
      targetBrandScore: brandScores ? (brandScores[targetBrand]?.overallScore || null) : null,
      hasInsights: !!insights,
      hasSemanticDrift: !!semanticDriftData,
      driftScore: semanticDriftData ? (semanticDriftData.driftScore || null) : null,
      hasRecommendation: !!recommendationData,
      recommendationCount: recommendationData ? (recommendationData.totalCount || 0) : 0,
      hasSourcePurity: !!sourcePurityData,
      purityScore: sourcePurityData ? (sourcePurityData.purityScore || null) : null,
      hasSourceIntelligence: !!sourceIntelligenceMap,
      sourceCount: sourceIntelligenceMap ? (sourceIntelligenceMap.nodes?.length || 0) : 0
    };

    console.log('📊 完整数据验证报告:', validation);

    // 缺失数据提示
    const missingData = [];
    if (!validation.hasResults) missingData.push('基础结果数据');
    if (!validation.hasBrandScores) missingData.push('品牌评分');
    if (!validation.hasInsights) missingData.push('核心洞察');
    if (!validation.hasSemanticDrift) missingData.push('语义偏移');
    if (!validation.hasRecommendation) missingData.push('优化建议');
    if (!validation.hasSourcePurity) missingData.push('信源纯净度');
    if (!validation.hasSourceIntelligence) missingData.push('信源情报');

    if (missingData.length > 0) {
      console.warn('⚠️ 以下数据缺失:', missingData);
    } else {
      console.log('✅ 所有核心数据完整');
    }

    return {
      ...validation,
      missingData: missingData,
      isComplete: missingData.length === 0
    };
  },

  /**
   * 高优先级修复 1: AI 调用失败重试建议
   * 获取单个结果的展示状态和重试建议
   */
  getResultDisplayStatus: function(result) {
    if (result._failed) {
      const errorType = result.geo_data?._error || result.response || '';
      if (errorType.includes('API') || errorType.includes('调用') || errorType.includes('网络')) {
        return { status: 'failed', message: 'AI 接口调用失败，建议稍后重试', canRetry: true, errorType: 'api_error' };
      } else if (errorType.includes('解析') || errorType.includes('JSON')) {
        return { status: 'failed', message: 'AI 响应解析失败，建议重试', canRetry: true, errorType: 'parse_error' };
      } else if (errorType.includes('超时') || errorType.includes('timeout')) {
        return { status: 'failed', message: 'AI 响应超时，建议重试', canRetry: true, errorType: 'timeout' };
      } else {
        return { status: 'failed', message: '数据获取失败', canRetry: false, errorType: 'unknown' };
      }
    } else if (!result.geo_data || !result.geo_data.brand_mentioned) {
      return { status: 'not_mentioned', message: 'AI 未提及该品牌', canRetry: false, errorType: 'not_mentioned' };
    } else {
      return { status: 'success', message: '', canRetry: false, errorType: 'success' };
    }
  },

  /**
   * 【存储架构优化】从新 API 初始化页面数据
   * @param {Object} report - 完整报告数据
   */
  initializePageDataFromNewAPI: function(report) {
    try {
      console.log('📊 从新 API 初始化页面数据');
      
      const reportData = report.report;
      const results = report.results || [];
      const analysis = report.analysis || {};
      
      // 构建页面数据
      const pageData = {
        targetBrand: reportData.brand_name,
        latestTestResults: results,
        latestCompetitiveAnalysis: analysis.competitive_analysis || {},
        
        // 高级分析数据
        semanticDriftData: analysis.semantic_drift_data || null,
        recommendationData: analysis.recommendation_data || null,
        sourcePurityData: analysis.source_purity_data || null,
        
        // 元数据
        dataLoadedFrom: 'database',
        dataLoadedAt: new Date().toISOString(),
        checksumVerified: report.checksum_verified || false
      };
      
      this.setData(pageData);
      
      // 渲染图表
      this.renderCharts(results);
      
      console.log('✅ 页面数据初始化完成');
      
    } catch (error) {
      console.error('❌ 页面数据初始化失败:', error);
      
      // 降级到本地加载
      this.loadFromLocalStorage();
    }
  },

  /**
   * 【存储架构优化】从本地 Storage 加载（降级方案）
   */
  loadFromLocalStorage: function() {
    console.log('📦 降级到本地 Storage 加载');
    // 原有的本地加载逻辑
    this.onLoad(this.options || {});
  },

  /**
   * 高优先级修复 3: 数据刷新功能
   * 允许用户主动刷新数据
   */
  refreshData: function() {
    const that = this;

    // 防止重复刷新
    if (this.data.refreshing) {
      console.log('[刷新] 正在刷新中，请等待...');
      return;
    }

    this.setData({ refreshing: true });
    wx.showLoading({ title: '刷新中...', mask: true });

    console.log('[刷新] 开始刷新数据 executionId:', this.data.executionId);

    this.fetchResultsFromServer(this.data.executionId, this.data.targetBrand)
      .then(() => {
        console.log('[刷新] 刷新成功');
        // 清除缓存标记
        that.setData({
          isCached: false,
          cacheTime: null,
          refreshing: false
        });
        wx.showToast({ title: '刷新成功', icon: 'success', duration: 2000 });
      })
      .catch(error => {
        console.error('[刷新] 刷新失败:', error);
        wx.showModal({
          title: '刷新失败',
          content: '无法获取最新数据，继续使用当前数据',
          showCancel: false,
          confirmText: '知道了'
        });
        that.setData({ refreshing: false });
      })
      .finally(() => {
        wx.hideLoading();
      });
  },

  // ==================== P3-1 流式渲染辅助方法 ====================

  /**
   * P3-1 新增：渲染品牌分数卡片
   */
  _renderScoreCards: function(data, targetBrand) {
    const brandScores = data.brandScores || {};
    const mainBrandScore = brandScores[targetBrand] || {};
    
    this.setData({
      brandScores: brandScores,
      targetBrandScore: mainBrandScore,
      // 更新洞察文本
      advantageInsight: mainBrandScore.overallSummary || '品牌表现良好',
      streamStageText: '品牌分数已生成'
    });
    
    console.log('[流式渲染] 品牌分数卡片已渲染');
  },

  /**
   * P3-1 新增：渲染 SOV 图表
   */
  _renderSOVChart: function(data) {
    const sovData = data.sov || {};
    
    // 生成平台对比数据
    const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform({
      brandScores: sovData
    }, this.data.targetBrand, []);
    
    this.setData({
      sovData: sovData,
      pkDataByPlatform: pkDataByPlatform,
      platforms: platforms,
      platformDisplayNames: platformDisplayNames,
      streamStageText: '市场份额已计算'
    });
    
    console.log('[流式渲染] SOV 图表已渲染');
  },

  /**
   * P3-1 新增：渲染风险评分
   */
  _renderRiskScore: function(data) {
    const riskData = data.risk || {};
    
    this.setData({
      riskData: riskData,
      riskInsight: riskData.summary || '品牌风险较低',
      streamStageText: '风险评分已生成'
    });
    
    console.log('[流式渲染] 风险评分已渲染');
  },

  /**
   * P3-1 新增：渲染品牌健康度
   */
  _renderBrandHealth: function(data) {
    const healthData = data.health || {};
    
    this.setData({
      healthData: healthData,
      streamStageText: '品牌健康度已评估'
    });
    
    console.log('[流式渲染] 品牌健康度已渲染');
  },

  /**
   * P3-1 新增：渲染洞察
   */
  _renderInsights: function(data) {
    const insights = data.insights || {};
    
    this.setData({
      insightsData: insights,
      advantageInsight: insights.advantage || this.data.advantageInsight,
      riskInsight: insights.risk || this.data.riskInsight,
      opportunityInsight: insights.opportunity || this.data.opportunityInsight,
      streamStageText: '核心洞察已生成'
    });
    
    console.log('[流式渲染] 洞察已渲染');
  },

  /**
   * P3-1 新增：完成流式渲染
   */
  _finalizeStreaming: function(data) {
    // 设置完整报告数据
    this.setData({
      competitiveAnalysis: data,
      isStreaming: false,
      streamProgress: 100,
      streamStageText: '渲染完成'
    });
    
    console.log('[流式渲染] 完成');
    
    // 隐藏加载提示
    wx.hideLoading();

    // 显示完成提示
    wx.showToast({
      title: '渲染完成',
      icon: 'success',
      duration: 1500
    });
  },

  /**
   * P2-023 新增：页面卸载时清理定时器
   */
  onUnload: function() {
    if (this.data.autoRefreshTimer) {
      clearInterval(this.data.autoRefreshTimer);
      this.setData({
        autoRefreshTimer: null,
        isAutoRefreshing: false
      });
      console.log('[P2-023 自动刷新] 页面卸载，清理定时器');
    }
  },

  /**
   * 应用页面进入动画
   */
  applyPageEnterAnimation: function() {
    setTimeout(() => {
      this.setData({
        pageTransitionClass: 'fade-enter-active',
        pageLoaded: true
      });
    }, 50);
  },

  /**
   * P1-001 修复：页面隐藏时清理定时器（防止内存泄漏）
   */
  onHide: function() {
    if (this.data.autoRefreshTimer) {
      clearInterval(this.data.autoRefreshTimer);
      this.setData({
        autoRefreshTimer: null,
        isAutoRefreshing: false
      });
      console.log('[P1-001 自动刷新] 页面隐藏，清理定时器');
    }
  }
});
