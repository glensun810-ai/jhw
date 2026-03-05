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
 * 报告数据服务类
 */
class ReportService {
  /**
   * 构造函数
   */
  constructor() {
    this.cache = new Map(); // 数据缓存
    this.cacheTimeout = 300000; // 缓存超时时间（5 分钟）
  }

  /**
   * 获取完整诊断报告
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 报告数据
   */
  async getFullReport(executionId) {
    try {
      console.log('[ReportService] Getting full report:', executionId);

      // 检查缓存
      const cached = this._getFromCache(executionId);
      if (cached) {
        console.log('[ReportService] Cache hit for:', executionId);
        return cached;
      }

      const res = await wx.cloud.callFunction({
        name: 'getDiagnosisReport',
        data: { executionId }
      });

      const report = res.result;

      // P1-5 修复：处理空状态和错误状态
      if (!report) {
        console.warn('[ReportService] Report is empty');
        return this._createEmptyReportWithSuggestion('报告不存在', 'not_found');
      }

      // 处理报告数据
      const processedReport = this._processReportData(report);

      // P1-5 修复：检查验证信息
      const validation = processedReport.validation;
      if (validation && !validation.is_valid && validation.errors?.length > 0) {
        console.warn('[ReportService] Report validation failed:', validation.errors);
      }

      // P1-5 修复：检查质量评分
      const qualityScore = validation?.quality_score;
      if (qualityScore !== undefined && qualityScore < 60) {
        console.warn('[ReportService] Low quality report:', qualityScore);
        processedReport.lowQualityWarning = true;
      }

      // 缓存报告
      this._setCache(executionId, processedReport);

      console.log('[ReportService] Report fetched successfully:', executionId);
      return processedReport;
    } catch (error) {
      const handledError = handleApiError(error);
      logError(error, {
        context: 'getFullReport',
        executionId: executionId
      });
      
      // P1-5 修复：错误时返回空报告
      return this._createEmptyReportWithSuggestion(
        '获取报告失败：' + (error.message || '未知错误'),
        'error'
      );
    }
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
        suggestion: suggestions[type] || '请稍后重试'
      },
      validation: {
        is_valid: false,
        errors: [message],
        warnings: [],
        quality_score: 0
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
  async getBrandDistribution(executionId) {
    try {
      console.log('[ReportService] Getting brand distribution:', executionId);

      const report = await this.getFullReport(executionId);
      return report.brandDistribution || {
        data: {},
        total_count: 0,
        warning: '暂无品牌分布数据'
      };
    } catch (error) {
      console.error('[ReportService] Get brand distribution failed:', error);
      throw error;
    }
  }

  /**
   * 获取情感分布数据
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 情感分布数据
   */
  async getSentimentDistribution(executionId) {
    try {
      console.log('[ReportService] Getting sentiment distribution:', executionId);

      const report = await this.getFullReport(executionId);
      return report.sentimentDistribution || {
        data: {
          positive: 0,
          neutral: 0,
          negative: 0
        },
        total_count: 0,
        warning: '暂无情感分布数据'
      };
    } catch (error) {
      console.error('[ReportService] Get sentiment distribution failed:', error);
      throw error;
    }
  }

  /**
   * 获取关键词数据
   * @param {string} executionId - 执行 ID
   * @param {number} topN - 返回前 N 个关键词
   * @returns {Promise<Array>} 关键词列表
   */
  async getKeywords(executionId, topN = 50) {
    try {
      console.log('[ReportService] Getting keywords:', executionId);

      const report = await this.getFullReport(executionId);
      const keywords = report.keywords || [];

      // 返回前 N 个关键词
      return keywords.slice(0, topN);
    } catch (error) {
      console.error('[ReportService] Get keywords failed:', error);
      throw error;
    }
  }

  /**
   * 获取趋势对比数据
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 趋势对比数据
   */
  async getTrendAnalysis(executionId) {
    try {
      console.log('[ReportService] Getting trend analysis:', executionId);

      const report = await this.getFullReport(executionId);
      return report.trendAnalysis || {
        current: {},
        historical: {},
        trend: {},
        warning: '暂无趋势对比数据'
      };
    } catch (error) {
      console.error('[ReportService] Get trend analysis failed:', error);
      throw error;
    }
  }

  /**
   * 获取竞品对比数据
   * @param {string} executionId - 执行 ID
   * @param {string} mainBrand - 主品牌名称
   * @returns {Promise<Object>} 竞品对比数据
   */
  async getCompetitorAnalysis(executionId, mainBrand) {
    try {
      console.log('[ReportService] Getting competitor analysis:', executionId);

      const report = await this.getFullReport(executionId);
      return report.competitorAnalysis || {
        main_brand: mainBrand,
        main_brand_share: 0,
        competitor_shares: {},
        rank: 0,
        total_competitors: 0
      };
    } catch (error) {
      console.error('[ReportService] Get competitor analysis failed:', error);
      throw error;
    }
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
   * 从缓存获取数据
   * @private
   * @param {string} key - 缓存键
   * @returns {Object|null} 缓存的数据
   */
  _getFromCache(key) {
    const cached = this.cache.get(key);
    if (!cached) {
      return null;
    }

    // 检查是否过期
    if (Date.now() - cached.timestamp > this.cacheTimeout) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  /**
   * 设置缓存
   * @private
   * @param {string} key - 缓存键
   * @param {Object} data - 缓存数据
   */
  _setCache(key, data) {
    this.cache.set(key, {
      data: data,
      timestamp: Date.now()
    });

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

// 导出单例
export default new ReportService();
