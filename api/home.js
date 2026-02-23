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
  // Step 1: 健康检查接口不需要认证，跳过 Token 携带
  return get(API_ENDPOINTS.SYSTEM.TEST_CONNECTION, {}, { skipAuth: true });
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
  // 确保参数格式正确 - 后端期望 custom_question 为字符串，而不是数组
  const payload = {
    ...data,
    // 将 customQuestions 数组转换为字符串格式，以匹配后端期望
    custom_question: Array.isArray(data.customQuestions) 
      ? data.customQuestions.join(' ') 
      : (data.custom_question || ''),
    // 确保 selectedModels 格式正确
    selectedModels: Array.isArray(data.selectedModels) ? data.selectedModels : []
  };
  
  return post(API_ENDPOINTS.BRAND.TEST, payload);
};

/**
 * 获取测试进度
 * @param {string} executionId - 执行ID
 * @returns {Promise}
 */
const getTestProgressApi = (executionId) => {
  return get(`${API_ENDPOINTS.BRAND.PROGRESS}?executionId=${executionId}`);
};

/**
 * 获取任务详细状态
 * @param {string} executionId - 执行ID
 * @returns {Promise}
 */
const getTaskStatusApi = (executionId) => {
  // 根据API契约，确保路径格式正确对应后端路由 /test/status/<task_id>
  // 构造完整的API路径，确保与后端路由 /test/status/<task_id> 匹配
  const apiUrl = `${API_ENDPOINTS.BRAND.STATUS}/${executionId}`;
  console.log(`Calling API: ${apiUrl} with executionId: ${executionId}`);

  return get(apiUrl);
};

module.exports = {
  checkServerConnectionApi,
  startBrandTestApi,
  getTestProgressApi,
  getTaskStatusApi
};