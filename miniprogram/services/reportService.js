/**
 * 报告数据服务
 *
 * 封装报告相关的 API 调用和数据处理
 * 适配后端统计算法返回的数据格式
 *
 * @author 系统架构组
 * @date 2026-02-27
 * @version 1.0.0
 */

import { handleApiError, logError } from '../utils/errorHandler';
import { isFeatureEnabled } from '../config/featureFlags';

/**
 * P1-4 修复：统一错误类型定义
 */
const ErrorTypes = {
  // 网络错误
  NETWORK_ERROR: 'NETWORK_ERROR',
  NETWORK_TIMEOUT: 'NETWORK_TIMEOUT',
  
  // 数据错误
  DATA_NOT_FOUND: 'DATA_NOT_FOUND',
  DATA_INVALID: 'DATA_INVALID',
  DATA_INCOMPLETE: 'DATA_INCOMPLETE',
  
  // 业务错误
  BUSINESS_FAILED: 'BUSINESS_FAILED',
  BUSINESS_TIMEOUT: 'BUSINESS_TIMEOUT',
  BUSINESS_NO_RESULTS: 'BUSINESS_NO_RESULTS',
  
  // 系统错误
  SYSTEM_ERROR: 'SYSTEM_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'
};

/**
 * P1-4 修复：错误建议映射
 */
const ErrorSuggestions = {
  [ErrorTypes.NETWORK_ERROR]: '请检查网络连接后重试',
  [ErrorTypes.NETWORK_TIMEOUT]: '网络请求超时，请检查网络后重试',
  [ErrorTypes.DATA_NOT_FOUND]: '报告不存在或已被删除',
  [ErrorTypes.DATA_INVALID]: '报告数据格式错误',
  [ErrorTypes.DATA_INCOMPLETE]: '报告数据不完整，可能尚未生成完成',
  [ErrorTypes.BUSINESS_FAILED]: '诊断执行失败，请查看错误详情',
  [ErrorTypes.BUSINESS_TIMEOUT]: '诊断处理超时，建议减少品牌数量后重试',
  [ErrorTypes.BUSINESS_NO_RESULTS]: '诊断未生成有效结果',
  [ErrorTypes.SYSTEM_ERROR]: '系统内部错误，请联系技术支持',
  [ErrorTypes.UNKNOWN_ERROR]: '未知错误，请稍后重试'
};

/**
 * 报告数据服务类
 */
class ReportService {
  /**
   * 构造函数
   */
  constructor() {
    this.cache = new Map(); // 数据缓存
    this.cacheTimeout = 300000; // 缓存超时时间（5 分钟）
    this.maxRetryCount = 3; // P1-4 新增：最大重试次数
    this.retryDelay = 1000; // P1-4 新增：重试延迟（毫秒）
    
    // P1-5 新增：缓存监控指标
    this.cacheStats = {
      hits: 0,
      misses: 0,
      invalidations: 0,
      expirations: 0
    };
  }

  /**
   * 获取完整诊断报告
   * @param {string} executionId - 执行 ID
   * @param {Object} options - 可选配置
   * @param {number} options.retryCount - 重试次数
   * @returns {Promise<Object>} 报告数据
   */
  getFullReport(executionId, options) {
    var that = this;
    options = options || {};
    var retryCount = options.retryCount || 0;
    var maxRetryCount = 3;

    console.log('[ReportService] Getting full report:', executionId, 'retry: ' + retryCount + '/' + maxRetryCount);

    // 检查缓存（首次请求才使用缓存）
    if (retryCount === 0) {
      var cached = that._getFromCache(executionId);
      if (cached) {
        console.log('[ReportService] Cache hit for:', executionId);
        return Promise.resolve(cached);
      }
    }

    // 开发环境：HTTP 直连后端
    var envVersion = that._getEnvVersion();
    if (envVersion === 'develop' || envVersion === 'trial') {
      return that._getFullReportViaHttp(executionId);
    }

    // 生产环境：使用云函数
    var callFunctionPromise = wx.cloud.callFunction({
      name: 'getDiagnosisReport',
      data: { executionId: executionId },
      timeout: 15000
    }).then(function(res) {
      if (!res || !res.result) {
        console.error('[ReportService] 云函数返回为空:', res);
        throw new Error('云函数返回为空');
      }
      return res;
    });

    var timeoutPromise = new Promise(function(_, reject) {
      setTimeout(function() {
        reject(new Error('请求超时'));
      }, 15000);
    });

    return Promise.race([callFunctionPromise, timeoutPromise])
      .then(function(res) {
        var result = res.result;
        if (!result) {
          throw new Error('云函数返回 result 为空');
        }

        var report = result.data || result;
        var hasPartialData = result.hasPartialData || false;
        var warnings = result.warnings || [];

        console.log('[ReportService] 云函数返回:', {
          success: result.success,
          hasPartialData: hasPartialData,
          warnings: warnings,
          hasReport: !!report
        });

        // 检查报告是否为空
        if (!report) {
          return that._createEmptyReportWithSuggestion('报告不存在', 'not_found');
        }

        // 处理失败状态
        if (report.status === 'failed' || report.success === false) {
          return that._createFailedReportWithMetadata(report);
        }

        // 有部分成功标志，继续处理
        if (hasPartialData) {
          console.warn('[ReportService] 数据不完整，但继续处理:', warnings);
          report.partialSuccess = true;
          report.qualityWarnings = warnings;
        }

        // 处理报告数据
        var processedReport = that._processReportData(report);

        // 验证失败也返回数据
        if (processedReport.validation && !processedReport.validation.is_valid) {
          console.warn('[ReportService] 验证失败，但保留数据');
          processedReport.hasValidationWarnings = true;
        }

        // 缓存报告
        if (retryCount === 0) {
          that._setCache(executionId, processedReport);
        }

        console.log('[ReportService] Report fetched:', executionId);
        return processedReport;
      })
      .catch(function(error) {
        console.error('[ReportService] 获取报告失败:', error);

        var errorType = that._classifyError(error);
        var canRetry = retryCount < maxRetryCount &&
                       errorType !== 'DATA_NOT_FOUND' &&
                       errorType !== 'DATA_INVALID';

        if (canRetry) {
          var retryDelay = 1000 * (retryCount + 1);
          console.log('[ReportService] ' + retryDelay + 'ms 后重试');
          
          return new Promise(function(resolve) {
            setTimeout(function() {
              resolve(that.getFullReport(executionId, { retryCount: retryCount + 1 }));
            }, retryDelay);
          });
        }

        // 达到最大重试次数或不可重试错误
        var errorMessage = that._getErrorMessage(error, errorType);
        console.error('[ReportService] 最终失败:', errorMessage);

        return that._createEmptyReportWithSuggestion(errorMessage, that._getErrorTypeString(errorType));
      });
  },

  /**
   * P1-4 新增：分类错误类型
   * @param {Error|string} error - 错误对象或消息
   * @returns {string} 错误类型
   */
  _classifyError(error) {
    const message = error.message || String(error);
    
    if (message.includes('不存在') || message.includes('not found')) {
      return ErrorTypes.DATA_NOT_FOUND;
    }
    if (message.includes('超时') || message.includes('timeout')) {
      return ErrorTypes.NETWORK_TIMEOUT;
    }
    if (message.includes('网络') || message.includes('network')) {
      return ErrorTypes.NETWORK_ERROR;
    }
    if (message.includes('格式') || message.includes('invalid')) {
      return ErrorTypes.DATA_INVALID;
    }
    if (message.includes('失败') || message.includes('failed')) {
      return ErrorTypes.BUSINESS_FAILED;
    }
    if (message.includes('不完整') || message.includes('incomplete')) {
      return ErrorTypes.DATA_INCOMPLETE;
    }
    
    return ErrorTypes.UNKNOWN_ERROR;
  }

  /**
   * P1-4 新增：获取错误消息
   * @param {Error} error - 错误对象
   * @param {string} errorType - 错误类型
   * @returns {string} 友好的错误消息
   */
  _getErrorMessage(error, errorType) {
    const baseMessage = error.message || '未知错误';
    const suggestion = ErrorSuggestions[errorType] || '';
    
    if (suggestion) {
      return `${baseMessage}。${suggestion}`;
    }
    return baseMessage;
  }

  /**
   * P1-4 新增：获取错误类型字符串
   * @param {string} errorType - 错误类型常量
   * @returns {string} 错误类型字符串
   */
  _getErrorTypeString(errorType) {
    const mapping = {
      [ErrorTypes.NETWORK_ERROR]: 'error',
      [ErrorTypes.NETWORK_TIMEOUT]: 'timeout',
      [ErrorTypes.DATA_NOT_FOUND]: 'not_found',
      [ErrorTypes.DATA_INVALID]: 'error',
      [ErrorTypes.DATA_INCOMPLETE]: 'no_results',
      [ErrorTypes.BUSINESS_FAILED]: 'failed',
      [ErrorTypes.BUSINESS_TIMEOUT]: 'timeout',
      [ErrorTypes.BUSINESS_NO_RESULTS]: 'no_results',
      [ErrorTypes.SYSTEM_ERROR]: 'error',
      [ErrorTypes.UNKNOWN_ERROR]: 'error'
    };
    return mapping[errorType] || 'error';
  }

  /**
   * 【P0 关键修复 - 2026-03-07】创建失败报告（带元数据）
   * @param {Object} report - 原始报告数据
   * @returns {Object} 失败报告
   */
  _createFailedReportWithMetadata(report) {
    const executionMetadata = report.execution_metadata || {};
    const errorDetails = report.error_details || report.error || {};

    return {
      status: 'failed',
      success: false,
      executionId: report.execution_id || report.executionId || '',
      error: typeof errorDetails === 'string'

  /**
   * 【死循环修复 - 2026-03-14】HTTP 直连后端获取报告（开发环境）
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 报告数据
   * @private
   */
  _getFullReportViaHttp(executionId) {
    var API_BASE_URL = 'http://localhost:5001';

    return new Promise(function(resolve, reject) {
      console.log('[ReportService] HTTP 直连后端:', executionId);

      wx.request({
        url: API_BASE_URL + '/api/diagnosis/report/' + executionId,
        method: 'GET',
        header: {
          'Content-Type': 'application/json'
        },
        timeout: 15000,
        success: function(res) {
          var result = res.data;
          console.log('[ReportService] HTTP 响应:', result);

          if (!result) {
            reject(new Error('HTTP 返回为空'));
            return;
          }

          if (result.error_code || result.error) {
            var error = new Error(result.error_message || result.error || '获取报告失败');
            error.code = result.error_code || 'REPORT_ERROR';
            reject(error);
            return;
          }

          var report = result.data || result;
          resolve(report);
        },
        fail: function(error) {
          console.error('[ReportService] HTTP 获取报告失败:', error);
          reject(error);
        }
      });
    });
  }

  /**
   * 【P0 关键修复 - 2026-03-07】创建失败报告（带元数据）
   * @param {Object} report - 原始报告数据
   * @returns {Object} 失败报告
   */
  _createFailedReportWithMetadata(report) {
    const executionMetadata = report.execution_metadata || {};
    const errorDetails = report.error_details || report.error || {};

    return {
      status: 'failed',
      success: false,
      executionId: report.execution_id || report.executionId || '',
      error: typeof errorDetails === 'string' 
        ? { message: errorDetails, suggestion: '请检查诊断配置' }
        : {
            type: errorDetails.type || 'unknown',
            message: errorDetails.message || '诊断失败',
            suggestion: errorDetails.suggestion || '请查看诊断详情'
          },
      // 元数据（让用户看到配置和日志）
      execution_metadata: {
        selected_models: executionMetadata.selected_models || report.selected_models || [],
        custom_questions: executionMetadata.custom_questions || report.custom_questions || [],
        main_brand: executionMetadata.main_brand || report.brand_name || '',
        competitor_brands: executionMetadata.competitor_brands || [],
        execution_log: executionMetadata.execution_log || [],
        failure_reason: executionMetadata.failure_reason || 'unknown',
        timestamp: executionMetadata.timestamp || new Date().toISOString()
      },
      // 执行统计
      total_tasks: report.total_tasks || 0,
      completed_tasks: report.completed_tasks || 0,
      completion_rate: report.completion_rate || 0,
      // 兼容性字段
      results: [],
      brandDistribution: { data: {}, total_count: 0 },
      sentimentDistribution: { data: { positive: 0, neutral: 0, negative: 0 }, total_count: 0 },
      keywords: [],
      // 验证信息
      validation: {
        is_valid: false,
        errors: [typeof errorDetails === 'string' ? errorDetails : (errorDetails.message || '诊断失败')],
        warnings: [],
        quality_score: 0
      },
      meta: {
        generated_at: new Date().toISOString(),
        execution_id: report.execution_id || report.executionId || '',
        version: '2.0.0'
      }
    };
  }

  /**
   * P1-5 新增：创建带建议的空报告
   * @param {string} message - 错误信息
   * @param {string} type - 错误类型
   * @returns {Object} 空报告
   */
  _createEmptyReportWithSuggestion(message, type) {
    const suggestions = {
      'not_found': '请检查执行 ID 是否正确，或重新进行诊断',
      'error': '请稍后重试或联系技术支持',
      'timeout': '诊断处理时间过长，建议减少品牌数量后重试',
      'no_results': '诊断未生成有效结果，建议检查 AI 平台配置'
    };

    // P1-1 增强：添加详细的降级场景信息
    const fallbackInfo = {
      'not_found': {
        title: '报告不存在',
        description: '未找到对应的诊断报告',
        icon: 'search',
        actions: [
          { text: '重新诊断', type: 'navigate', url: '/pages/diagnosis/diagnosis' },
          { text: '查看历史', type: 'navigate', url: '/pages/history/history' }
        ]
      },
      'error': {
        title: '发生错误',
        description: '系统遇到意外错误',
        icon: 'error',
        actions: [
          { text: '重试', type: 'retry' },
          { text: '返回首页', type: 'navigate', url: '/pages/index/index' }
        ]
      },
      'timeout': {
        title: '诊断超时',
        description: '诊断处理时间过长',
        icon: 'time',
        actions: [
          { text: '继续等待', type: 'wait' },
          { text: '查看历史', type: 'navigate', url: '/pages/history/history' }
        ]
      },
      'no_results': {
        title: '无有效结果',
        description: '诊断未生成有效结果',
        icon: 'warning',
        actions: [
          { text: '优化配置', type: 'navigate', url: '/pages/diagnosis/diagnosis' },
          { text: '联系支持', type: 'contact' }
        ]
      }
    };

    return {
      report: {},
      results: [],
      analysis: {},
      brandDistribution: { data: {}, total_count: 0 },
      sentimentDistribution: { data: { positive: 0, neutral: 0, negative: 0 }, total_count: 0 },
      keywords: [],
      error: {
        status: type,
        message: message,
        suggestion: suggestions[type] || '请稍后重试',
        fallbackInfo: fallbackInfo[type] || fallbackInfo.error
      },
      validation: {
        is_valid: false,
        errors: [message],
        warnings: [],
        quality_score: 0,
        fallbackScenarios: [type]
      },
      meta: {
        generated_at: new Date().toISOString(),
        execution_id: '',
        version: '2.0.0'
      }
    };
  }

  /**
   * 获取品牌分布数据
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 品牌分布数据
   */
  getBrandDistribution(executionId) {
    var that = this;
    return new Promise(function(resolve, reject) {
      console.log('[ReportService] Getting brand distribution:', executionId);

      that.getFullReport(executionId).then(function(report) {
        resolve(report.brandDistribution || {
          data: {},
          total_count: 0,
          warning: '暂无品牌分布数据'
        });
      }).catch(function(error) {
        console.error('[ReportService] Get brand distribution failed:', error);
        reject(error);
      });
    });
  },

  /**
   * 获取情感分布数据
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 情感分布数据
   */
  getSentimentDistribution(executionId) {
    var that = this;
    return new Promise(function(resolve, reject) {
      console.log('[ReportService] Getting sentiment distribution:', executionId);

      that.getFullReport(executionId).then(function(report) {
        resolve(report.sentimentDistribution || {
          data: {
            positive: 0,
            neutral: 0,
            negative: 0
          },
          total_count: 0,
          warning: '暂无情感分布数据'
        });
      }).catch(function(error) {
        console.error('[ReportService] Get sentiment distribution failed:', error);
        reject(error);
      });
    });
  },

  /**
   * 获取关键词数据
   * @param {string} executionId - 执行 ID
   * @param {number} topN - 返回前 N 个关键词
   * @returns {Promise<Array>} 关键词列表
   */
  getKeywords(executionId, topN) {
    var that = this;
    topN = topN || 50;
    return new Promise(function(resolve, reject) {
      console.log('[ReportService] Getting keywords:', executionId);

      that.getFullReport(executionId).then(function(report) {
        var keywords = report.keywords || [];
        resolve(keywords.slice(0, topN));
      }).catch(function(error) {
        console.error('[ReportService] Get keywords failed:', error);
        reject(error);
      });
    });
  },

  /**
   * 获取趋势对比数据
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 趋势对比数据
   */
  getTrendAnalysis(executionId) {
    var that = this;
    return new Promise(function(resolve, reject) {
      console.log('[ReportService] Getting trend analysis:', executionId);

      that.getFullReport(executionId).then(function(report) {
        resolve(report.trendAnalysis || {
          current: {},
          historical: {},
          trend: {},
          warning: '暂无趋势对比数据'
        });
      }).catch(function(error) {
        console.error('[ReportService] Get trend analysis failed:', error);
        reject(error);
      });
    });
  },

  /**
   * 获取竞品对比数据
   * @param {string} executionId - 执行 ID
   * @param {string} mainBrand - 主品牌名称
   * @returns {Promise<Object>} 竞品对比数据
   */
  getCompetitorAnalysis(executionId, mainBrand) {
    var that = this;
    return new Promise(function(resolve, reject) {
      console.log('[ReportService] Getting competitor analysis:', executionId);

      that.getFullReport(executionId).then(function(report) {
        resolve(report.competitorAnalysis || {
          main_brand: mainBrand,
          main_brand_share: 0,
          competitor_shares: {},
          rank: 0,
          total_competitors: 0
        });
      }).catch(function(error) {
        console.error('[ReportService] Get competitor analysis failed:', error);
        reject(error);
      });
    });
  }

  /**
   * 处理原始报告数据
   * @private
   * @param {Object} report - 原始报告数据
   * @returns {Object} 处理后的报告数据
   */
  _processReportData(report) {
    if (!report) {
      return this._createEmptyReport();
    }

    // P0-4 修复：统一数据格式处理
    
    // 1. 处理品牌分布数据（支持多种格式）
    const brandDistribution = report.brandDistribution || report.brand_distribution;
    if (brandDistribution && typeof brandDistribution === 'object') {
      report.brandDistribution = {
        data: brandDistribution.data || brandDistribution,
        total_count: brandDistribution.total_count || 0,
        warning: brandDistribution.warning || null
      };
    } else {
      // 如果后端未提供，从 results 计算
      report.brandDistribution = this._calculateBrandDistributionFromResults(report.results);
    }

    // 2. 处理情感分布数据（支持多种格式）
    const sentimentDistribution = report.sentimentDistribution || report.sentiment_distribution;
    if (sentimentDistribution && typeof sentimentDistribution === 'object') {
      report.sentimentDistribution = {
        data: sentimentDistribution.data || sentimentDistribution,
        total_count: sentimentDistribution.total_count || 0,
        warning: sentimentDistribution.warning || null
      };
    } else {
      // 如果后端未提供，从 results 计算
      report.sentimentDistribution = this._calculateSentimentDistributionFromResults(report.results);
    }

    // 3. 处理关键词数据（支持多种格式）
    const keywords = report.keywords || report.keyword_list;
    if (keywords && Array.isArray(keywords)) {
      report.keywords = keywords.map(kw => ({
        word: kw.word || kw.text || '',
        count: kw.count || kw.frequency || 0,
        sentiment: kw.sentiment || 0,
        sentiment_label: kw.sentiment_label || kw.sentimentLabel || 'neutral'
      }));
    } else {
      report.keywords = [];
    }

    // 4. 处理竞品分析数据（支持多种路径）
    const competitorAnalysis = report.competitorAnalysis || 
                               report.competitor_analysis || 
                               report.analysis?.competitive_analysis;
    if (competitorAnalysis && typeof competitorAnalysis === 'object') {
      report.competitorAnalysis = competitorAnalysis;
    } else {
      report.competitorAnalysis = {};
    }

    // 5. 处理品牌评分数据（支持多种路径）
    const brandScores = report.brandScores || 
                        report.brand_scores || 
                        report.analysis?.brand_scores;
    if (brandScores && typeof brandScores === 'object') {
      report.brandScores = brandScores;
    } else {
      report.brandScores = {};
    }

    // 6. 处理语义偏移数据
    const semanticDrift = report.semanticDrift || 
                          report.semantic_drift || 
                          report.analysis?.semantic_drift;
    report.semanticDrift = semanticDrift || {};

    // 7. 处理信源纯净度数据
    const sourcePurity = report.sourcePurity || 
                         report.source_purity || 
                         report.analysis?.source_purity;
    report.sourcePurity = sourcePurity || {};

    // 8. 处理优化建议数据
    const recommendations = report.recommendations || 
                            report.analysis?.recommendations;
    report.recommendations = recommendations || {};

    // 9. 添加/确保报告元数据
    report.meta = report.meta || {
      generated_at: report.generated_at || new Date().toISOString(),
      execution_id: report.execution_id || report.report?.execution_id || '',
      version: '2.0.0'
    };

    // 10. 添加验证信息（如果后端返回）
    if (report.validation) {
      report.validation = {
        is_valid: report.validation.is_valid || false,
        errors: report.validation.errors || [],
        warnings: report.validation.warnings || []
      };
    }

    return report;
  }

  /**
   * 从结果数组计算品牌分布
   * @private
   * @param {Array} results - 结果数组
   * @returns {Object} 品牌分布数据
   */
  _calculateBrandDistributionFromResults(results) {
    const distribution = {};
    let totalCount = 0;

    if (results && Array.isArray(results)) {
      for (const result of results) {
        const brand = result.brand || 'Unknown';
        distribution[brand] = (distribution[brand] || 0) + 1;
        totalCount++;
      }
    }

    return {
      data: distribution,
      total_count: totalCount
    };
  }

  /**
   * 从结果数组计算情感分布
   * @private
   * @param {Array} results - 结果数组
   * @returns {Object} 情感分布数据
   */
  _calculateSentimentDistributionFromResults(results) {
    const sentimentCounts = {
      positive: 0,
      neutral: 0,
      negative: 0
    };

    if (results && Array.isArray(results)) {
      for (const result of results) {
        const geoData = result.geo_data || {};
        const sentiment = geoData.sentiment || 0;

        if (sentiment > 0.3) {
          sentimentCounts.positive++;
        } else if (sentiment < -0.3) {
          sentimentCounts.negative++;
        } else {
          sentimentCounts.neutral++;
        }
      }
    }

    return {
      data: sentimentCounts,
      total_count: results ? results.length : 0
    };
  }

  /**
   * 创建空报告数据结构
   * @private
   * @returns {Object} 空报告
   */
  _createEmptyReport() {
    return {
      brandDistribution: {
        data: {},
        total_count: 0,
        warning: '暂无数据'
      },
      sentimentDistribution: {
        data: {
          positive: 0,
          neutral: 0,
          negative: 0
        },
        total_count: 0,
        warning: '暂无数据'
      },
      keywords: [],
      trendAnalysis: {
        current: {},
        historical: {},
        trend: {},
        warning: '暂无数据'
      },
      competitorAnalysis: {
        main_brand: '',
        main_brand_share: 0,
        competitor_shares: {},
        rank: 0,
        total_competitors: 0
      },
      meta: {
        generated_at: new Date().toISOString(),
        execution_id: '',
        version: '2.0.0'
      }
    };
  }

  /**
   * P1-5 修复：从缓存获取数据（增强版 - 支持动态超时）
   * @private
   * @param {string} key - 缓存键
   * @param {Object} reportData - 报告数据（用于判断状态）
   * @returns {Object|null} 缓存的数据
   */
  _getFromCache(key, reportData = null) {
    const cached = this.cache.get(key);
    if (!cached) {
      this.cacheStats.misses++;
      return null;
    }

    // P1-5 增强：根据报告状态动态计算超时时间
    const cacheTimeout = this._getDynamicCacheTimeout(cached.data);
    
    // 检查是否过期
    if (Date.now() - cached.timestamp > cacheTimeout) {
      console.log('[ReportService] 缓存已过期:', key);
      this.cache.delete(key);
      this.cacheStats.expirations++;
      return null;
    }

    // P1-5 增强：检查报告状态是否需要刷新缓存
    if (this._shouldInvalidateCache(cached.data, reportData)) {
      console.log('[ReportService] 缓存需要刷新:', key);
      this.cache.delete(key);
      this.cacheStats.invalidations++;
      return null;
    }

    this.cacheStats.hits++;
    console.log('[ReportService] 缓存命中:', key, `剩余时间：${Math.round((cacheTimeout - (Date.now() - cached.timestamp)) / 1000)}s`);
    return cached.data;
  }

  /**
   * P1-5 新增：根据报告状态获取动态缓存超时时间
   * @private
   * @param {Object} reportData - 报告数据
   * @returns {number} 缓存超时时间（毫秒）
   */
  _getDynamicCacheTimeout(reportData) {
    const status = reportData?.report?.status;
    const stage = reportData?.report?.stage;
    
    // 处理中：短缓存（30 秒），需要频繁刷新
    if (status === 'processing' || (stage && stage !== 'completed')) {
      return 30000; // 30 秒
    }
    
    // 已完成：长缓存（5 分钟）
    if (status === 'completed') {
      return this.cacheTimeout; // 5 分钟
    }
    
    // 失败状态：中等缓存（1 分钟）
    if (status === 'failed') {
      return 60000; // 1 分钟
    }
    
    // 默认：中等缓存（2 分钟）
    return 120000; // 2 分钟
  }

  /**
   * P1-5 新增：判断是否需要刷新缓存
   * @private
   * @param {Object} cachedData - 缓存的数据
   * @param {Object} freshData - 新获取的数据
   * @returns {boolean} 是否需要刷新
   */
  _shouldInvalidateCache(cachedData, freshData) {
    if (!freshData) {
      return false;
    }
    
    // 检查状态变化
    const cachedStatus = cachedData?.report?.status;
    const freshStatus = freshData?.report?.status;
    
    if (cachedStatus !== freshStatus) {
      return true;
    }
    
    // 检查进度变化
    const cachedProgress = cachedData?.report?.progress;
    const freshProgress = freshData?.report?.progress;
    
    if (cachedProgress !== freshProgress && freshProgress > cachedProgress) {
      return true;
    }
    
    // 检查验证状态变化
    const cachedValid = cachedData?.validation?.is_valid;
    const freshValid = freshData?.validation?.is_valid;
    
    if (cachedValid !== freshValid) {
      return true;
    }
    
    return false;
  }

  /**
   * P1-5 修复：设置缓存（增强版 - 支持动态超时标记）
   * @private
   * @param {string} key - 缓存键
   * @param {Object} data - 缓存数据
   */
  _setCache(key, data) {
    // P1-5 增强：记录缓存的超时时间
    const cacheTimeout = this._getDynamicCacheTimeout(data);
    
    this.cache.set(key, {
      data: data,
      timestamp: Date.now(),
      timeout: cacheTimeout // 记录超时时间
    });

    console.log('[ReportService] 设置缓存:', key, `超时时间：${cacheTimeout / 1000}s`);
    
    // 清理过期缓存
    this._cleanupCache();
  }

  /**
   * 清理过期缓存
   * @private
   */
  _cleanupCache() {
    const now = Date.now();
    for (const [key, value] of this.cache.entries()) {
      if (now - value.timestamp > this.cacheTimeout) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * 清除缓存
   * @param {string} key - 缓存键，不传则清除所有
   */
  clearCache(key) {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
    console.log('[ReportService] Cache cleared');
  }

  /**
   * P1-5 新增：获取缓存统计信息
   * @returns {Object} 缓存统计信息
   */
  getCacheStats() {
    const total = this.cacheStats.hits + this.cacheStats.misses;
    const hitRate = total > 0 ? ((this.cacheStats.hits / total) * 100).toFixed(2) : 0;
    
    return {
      hits: this.cacheStats.hits,
      misses: this.cacheStats.misses,
      invalidations: this.cacheStats.invalidations,
      expirations: this.cacheStats.expirations,
      hitRate: parseFloat(hitRate),
      cacheSize: this.cache.size
    };
  }

  /**
   * P1-5 新增：重置缓存统计
   */
  resetCacheStats() {
    this.cacheStats = {
      hits: 0,
      misses: 0,
      invalidations: 0,
      expirations: 0
    };
    console.log('[ReportService] 缓存统计已重置');
  }

  /**
   * 格式化品牌分布数据为图表格式
   * @param {Object} distribution - 品牌分布数据
   * @returns {Array} 图表数据
   */
  formatBrandDistributionForChart(distribution) {
    if (!distribution || !distribution.data) {
      return [];
    }

    return Object.entries(distribution.data).map(([name, value]) => ({
      name: name,
      value: parseFloat(value) || 0
    })).sort((a, b) => b.value - a.value);
  }

  /**
   * 格式化情感分布数据为图表格式
   * @param {Object} distribution - 情感分布数据
   * @returns {Array} 图表数据
   */
  formatSentimentForChart(distribution) {
    if (!distribution || !distribution.data) {
      return [];
    }

    const sentimentMap = {
      positive: '正面',
      neutral: '中性',
      negative: '负面'
    };

    const colorMap = {
      positive: '#28a745',
      neutral: '#6c757d',
      negative: '#dc3545'
    };

    return Object.entries(distribution.data).map(([key, value]) => ({
      name: sentimentMap[key] || key,
      value: parseFloat(value) || 0,
      color: colorMap[key] || '#6c757d'
    }));
  }

  /**
   * 格式化关键词数据为词云格式
   * @param {Array} keywords - 关键词列表
   * @returns {Array} 词云数据
   */
  formatKeywordsForWordCloud(keywords) {
    if (!keywords || !Array.isArray(keywords)) {
      return [];
    }

    // 计算最大最小值用于归一化
    const counts = keywords.map(kw => kw.count);
    const maxCount = Math.max(...counts, 1);
    const minCount = Math.min(...counts, 1);

    return keywords.map(kw => {
      // 归一化大小（12-48 像素）
      const normalized = maxCount === minCount ? 0.5 : (kw.count - minCount) / (maxCount - minCount);
      const size = Math.round(12 + normalized * 36);

      // 根据情感设置颜色
      const color = this._getSentimentColor(kw.sentiment);

      return {
        word: kw.word,
        size: size,
        color: color,
        count: kw.count,
        sentiment: kw.sentiment
      };
    });
  }

  /**
   * 根据情感得分获取颜色
   * @private
   * @param {number} sentiment - 情感得分
   * @returns {string} 颜色值
   */
  _getSentimentColor(sentiment) {
    if (sentiment > 0.3) {
      return '#28a745'; // 绿色（正面）
    } else if (sentiment < -0.3) {
      return '#dc3545'; // 红色（负面）
    } else {
      return '#6c757d'; // 灰色（中性）
    }
  }
}

// 导出单例（CommonJS 语法，兼容微信小程序）
const reportServiceInstance = new ReportService();
module.exports = reportServiceInstance;
module.exports.default = reportServiceInstance; // 兼容 .default 导入方式
