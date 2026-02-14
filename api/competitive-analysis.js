/**
 * 竞争分析相关API接口
 */

const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 执行品牌测试
 * @param {Object} data - 请求数据
 * @returns {Promise}
 */
const performBrandTest = (data) => {
  return post(API_ENDPOINTS.BRAND.TEST, data);
};

/**
 * 获取测试进度
 * @param {Object} params - 查询参数
 * @param {string} params.executionId - 执行ID
 * @returns {Promise}
 */
const getTestProgress = (params) => {
  return get(API_ENDPOINTS.BRAND.PROGRESS, params);
};

/**
 * 执行竞争分析
 * @param {Object} data - 请求数据
 * @returns {Promise}
 */
const performCompetitiveAnalysis = (data) => {
  return post(API_ENDPOINTS.COMPETITIVE.ANALYSIS, data);
};

module.exports = {
  performBrandTest,
  getTestProgress,
  performCompetitiveAnalysis
};