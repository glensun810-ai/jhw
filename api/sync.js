/**
 * 数据同步 API
 */

const { post, get } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 同步数据（增量同步）
 * @param {Object} syncData - 同步数据
 * @param {string} syncData.lastSyncTimestamp - 上次同步时间戳（可选）
 * @param {Array} syncData.localResults - 本地结果列表（可选）
 * @returns {Promise}
 */
const syncData = (syncData) => {
  return post(API_ENDPOINTS.SYNC.DATA, syncData);
};

/**
 * 下载数据（增量下载）
 * @param {Object} downloadData - 下载数据
 * @param {string} downloadData.lastSyncTimestamp - 上次同步时间戳（可选）
 * @returns {Promise}
 */
const downloadData = (downloadData) => {
  return post(API_ENDPOINTS.SYNC.DOWNLOAD, downloadData);
};

/**
 * 上传单个结果
 * @param {Object} uploadData - 上传数据
 * @param {Object} uploadData.result - 测试结果
 * @returns {Promise}
 */
const uploadResult = (uploadData) => {
  return post(API_ENDPOINTS.SYNC.UPLOAD_RESULT, uploadData);
};

/**
 * 删除结果
 * @param {Object} deleteData - 删除数据
 * @param {string} deleteData.result_id - 结果 ID
 * @returns {Promise}
 */
const deleteResult = (deleteData) => {
  return post(API_ENDPOINTS.SYNC.DELETE_RESULT, deleteData);
};

/**
 * 获取同步状态
 * @returns {Promise}
 */
const getSyncStatus = () => {
  return get(API_ENDPOINTS.SYNC.STATUS);
};

module.exports = {
  syncData,
  downloadData,
  uploadResult,
  deleteResult,
  getSyncStatus
};
