/**
 * 品牌测试增强API接口
 * 提供问题解析和分发功能的API接口
 */

const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 执行品牌测试（增强版）
 * @param {Object} data - 请求数据
 * @returns {Promise}
 */
const performEnhancedBrandTest = (data) => {
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
 * 获取测试状态
 * @param {string} executionId - 执行ID
 * @returns {Promise}
 */
const getTestStatus = (executionId) => {
  return get(`${API_ENDPOINTS.BRAND.STATUS}?executionId=${executionId}`);
};

module.exports = {
  performEnhancedBrandTest,
  getTestProgress,
  getTestStatus
};