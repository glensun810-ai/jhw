/**
 * 统计分析 API 服务
 * 负责与后端统计分析接口通信
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

const { get } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 获取品牌对比数据
 * @param {object} options - 选项
 * @param {string} options.timeRange - 时间范围 (all, last7days, last30days, last90days)
 * @returns {Promise}
 */
const getBrandCompareApi = (options = {}) => {
  return get(API_ENDPOINTS.ANALYTICS.BRAND_COMPARE, {
    timeRange: options.timeRange || 'all'
  });
};

/**
 * 获取趋势分析数据
 * @param {object} options - 选项
 * @param {string} options.timeRange - 时间范围
 * @param {string} options.brandName - 品牌名称（可选）
 * @returns {Promise}
 */
const getTrendAnalysisApi = (options = {}) => {
  return get(API_ENDPOINTS.ANALYTICS.TREND, {
    timeRange: options.timeRange || 'all',
    brandName: options.brandName || ''
  });
};

/**
 * 获取 AI 平台对比数据
 * @param {object} options - 选项
 * @param {string} options.timeRange - 时间范围
 * @returns {Promise}
 */
const getPlatformCompareApi = (options = {}) => {
  return get(API_ENDPOINTS.ANALYTICS.PLATFORM_COMPARE, {
    timeRange: options.timeRange || 'all'
  });
};

/**
 * 获取问题聚合数据
 * @param {object} options - 选项
 * @param {string} options.timeRange - 时间范围
 * @param {number} options.limit - 限制数量
 * @returns {Promise}
 */
const getQuestionAnalysisApi = (options = {}) => {
  return get(API_ENDPOINTS.ANALYTICS.QUESTION_ANALYSIS, {
    timeRange: options.timeRange || 'all',
    limit: options.limit || 10
  });
};

/**
 * 获取行业基准数据
 * @param {string} category - 行业类别
 * @returns {Promise}
 */
const getBenchmarkApi = (category) => {
  return get(API_ENDPOINTS.ANALYTICS.BENCHMARK, {
    category: category || 'default'
  });
};

module.exports = {
  getBrandCompareApi,
  getTrendAnalysisApi,
  getPlatformCompareApi,
  getQuestionAnalysisApi,
  getBenchmarkApi
};
