/**
 * 历史记录相关API接口
 */

const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 获取测试历史记录
 * @param {Object} data - 请求数据
 * @param {string} data.userOpenid - 用户openid
 * @returns {Promise}
 */
const getTestHistory = (data) => {
  return get(API_ENDPOINTS.HISTORY.LIST, data);
};

module.exports = {
  getTestHistory
};