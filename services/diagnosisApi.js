/**
 * 诊断报告 API 服务 - 存储架构优化版本
 * 
 * 新增 API:
 * 1. getDiagnosisHistory - 获取用户历史报告
 * 2. getFullReport - 获取完整报告
 * 3. validateReport - 验证报告完整性
 * 
 * 优化 API:
 * 1. getTaskStatus - 支持增量轮询
 * 
 * 作者：前端工程师
 * 日期：2026-03-01
 * 版本：1.0
 */

const { get } = require('../utils/request');

// API 端点配置
const API_BASE = '/api/diagnosis';

/**
 * 获取用户历史报告
 * @param {Object} options - 选项
 * @param {number} options.page - 页码（默认 1）
 * @param {number} options.limit - 每页数量（默认 20）
 * @returns {Promise}
 */
const getDiagnosisHistory = (options = {}) => {
  const { page = 1, limit = 20 } = options;
  
  return get(`${API_BASE}/history`, {
    page,
    limit
  });
};

/**
 * 获取完整诊断报告
 * @param {string} executionId - 执行 ID
 * @returns {Promise}
 */
const getFullReport = (executionId) => {
  return get(`${API_BASE}/report/${executionId}`);
};

/**
 * 验证报告完整性
 * @param {string} executionId - 执行 ID
 * @returns {Promise}
 */
const validateReport = (executionId) => {
  return get(`${API_BASE}/report/${executionId}/validate`);
};

/**
 * 获取任务状态（支持增量轮询）
 * @param {string} executionId - 执行 ID
 * @param {string} since - 上次更新时间（可选，用于增量轮询）
 * @returns {Promise}
 */
const getTaskStatus = (executionId, since = null) => {
  const params = since ? { since } : {};
  return get(`/test/status/${executionId}`, params);
};

module.exports = {
  getDiagnosisHistory,
  getFullReport,
  validateReport,
  getTaskStatus
};
