/**
 * 首页相关 API 接口
 * 从 pages/index/index.js 中提取的网络请求逻辑
 */

const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

// 【P0 关键修复 - 2026-03-04】添加请求状态锁，防止重复请求
const pendingRequests = new Map();

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
 * @param {Array} data.selectedModels - 选中的 AI 模型列表
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
 * 获取任务详细状态（统一进度查询接口）
 * @param {string} executionId - 执行 ID
 * @returns {Promise}
 */
const getTaskStatusApi = (executionId) => {
  // 【P0 关键修复 - 2026-03-04】过滤重复请求
  const requestKey = `status_${executionId}`;

  if (pendingRequests.has(requestKey)) {
    console.warn(`[API] ⚠️ 重复请求被拦截：${requestKey}`);
    // 返回已存在的 Promise
    return pendingRequests.get(requestKey);
  }

  // 统一使用 /test/status/{id} 接口
  // 【P2 修复 - 2026-03-07】添加 fields=full 参数，确保返回详细结果数据
  const apiUrl = `${API_ENDPOINTS.BRAND.STATUS}/${executionId}?fields=full`;
  console.log(`Calling API: ${apiUrl} with executionId: ${executionId}`);

  const requestPromise = get(apiUrl)
    .then(result => {
      // 请求完成，清除锁
      pendingRequests.delete(requestKey);
      return result;
    })
    .catch(error => {
      // 请求失败，也清除锁
      pendingRequests.delete(requestKey);
      throw error;
    });

  // 保存 Promise 到 pendingRequests
  pendingRequests.set(requestKey, requestPromise);

  return requestPromise;
};

module.exports = {
  checkServerConnectionApi,
  startBrandTestApi,
  getTaskStatusApi
};
