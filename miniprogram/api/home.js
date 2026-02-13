/**
 * 首页相关API接口
 * 从 pages/index/index.js 中提取的网络请求逻辑
 */

const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 检查服务器连接状态
 * @returns {Promise}
 */
const checkServerConnectionApi = () => {
  return get(API_ENDPOINTS.SYSTEM.TEST_CONNECTION);
};

/**
 * 启动品牌测试
 * @param {Object} data - 请求数据
 * @param {Array} data.brand_list - 品牌列表
 * @param {Array} data.selectedModels - 选中的AI模型列表
 * @param {Array} data.customQuestions - 自定义问题列表
 * @returns {Promise}
 */
const startBrandTestApi = (data) => {
  return post(API_ENDPOINTS.BRAND.TEST, data);
};

/**
 * 获取测试进度
 * @param {string} executionId - 执行ID
 * @returns {Promise}
 */
const getTestProgressApi = (executionId) => {
  return get(`${API_ENDPOINTS.BRAND.PROGRESS}?executionId=${executionId}`);
};

module.exports = {
  checkServerConnectionApi,
  startBrandTestApi,
  getTestProgressApi
};