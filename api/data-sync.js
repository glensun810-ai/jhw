/**
 * 数据同步相关API接口
 * 从 utils/data-sync.js 中提取的网络请求逻辑
 */

const { post, get } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 同步数据到云端
 * @param {Object} data - 同步数据
 * @param {string} data.openid - 用户openid
 * @param {Array} data.localResults - 本地结果数据
 * @returns {Promise}
 */
const syncDataApi = (data) => {
  return post(API_ENDPOINTS.SYNC.DATA, data);
};

/**
 * 从云端下载数据
 * @param {Object} data - 请求数据
 * @param {string} data.openid - 用户openid
 * @returns {Promise}
 */
const downloadDataApi = (data) => {
  return post(API_ENDPOINTS.SYNC.DOWNLOAD, data);
};

/**
 * 上传单个结果
 * @param {Object} data - 上传数据
 * @param {string} data.openid - 用户openid
 * @param {Object} data.result - 结果数据
 * @returns {Promise}
 */
const uploadResultApi = (data) => {
  return post(API_ENDPOINTS.SYNC.UPLOAD_RESULT, data);
};

/**
 * 删除云端结果
 * @param {Object} data - 删除数据
 * @param {string} data.openid - 用户openid
 * @param {string} data.id - 结果ID
 * @returns {Promise}
 */
const deleteResultApi = (data) => {
  return post(API_ENDPOINTS.SYNC.DELETE_RESULT, data);
};

module.exports = {
  syncDataApi,
  downloadDataApi,
  uploadResultApi,
  deleteResultApi
};