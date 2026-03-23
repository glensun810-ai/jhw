/**
 * 历史记录相关 API 接口
 * 
 * 功能：
 * 1. 获取历史报告列表
 * 2. 删除单个报告
 * 3. 批量删除报告
 * 4. 获取报告统计信息
 */

const { get, post, del } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 获取测试历史记录
 * @param {Object} params - 请求参数
 * @param {number} params.page - 页码（默认 1）
 * @param {number} params.limit - 每页数量（默认 20）
 * @param {string} params.brand - 品牌筛选（可选）
 * @param {string} params.status - 状态筛选（可选）
 * @param {string} params.sortBy - 排序字段（created_at/overall_score）
 * @param {string} params.sortOrder - 排序方向（asc/desc）
 * @returns {Promise}
 */
const getTestHistory = (params = {}) => {
  const defaultParams = {
    page: 1,
    limit: 20,
    sortBy: 'created_at',
    sortOrder: 'desc'
  };
  
  const queryParams = { ...defaultParams, ...params };
  return get(API_ENDPOINTS.HISTORY.LIST, queryParams);
};

/**
 * 删除单个历史报告
 * @param {string} executionId - 执行 ID
 * @param {number} reportId - 报告 ID
 * @returns {Promise}
 */
const deleteHistoryReport = (executionId, reportId) => {
  // 后端 API: DELETE /api/test-history/<record_id>
  return del(`/api/test-history/${reportId}`, { executionId });
};

/**
 * 批量删除历史报告
 * @param {Array} reportIds - 报告 ID 列表
 * @returns {Promise}
 */
const batchDeleteHistoryReports = (reportIds) => {
  return post('/api/test-history/batch-delete', { 
    reportIds 
  });
};

/**
 * 获取历史报告统计信息
 * @returns {Promise}
 */
const getHistoryStats = () => {
  return get('/api/test-history/stats');
};

/**
 * 搜索历史报告
 * @param {string} keyword - 搜索关键词
 * @param {Object} params - 其他参数
 * @returns {Promise}
 */
const searchHistoryReports = (keyword, params = {}) => {
  return get(`${API_ENDPOINTS.HISTORY.LIST}/search`, {
    keyword,
    ...params
  });
};

module.exports = {
  getTestHistory,
  deleteHistoryReport,
  batchDeleteHistoryReports,
  getHistoryStats,
  searchHistoryReports
};
