/**
 * 用户资料 API
 */

const { post, get, put } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 获取用户资料
 */
const getUserProfile = () => {
  return get(API_ENDPOINTS.USER.PROFILE);
};

/**
 * 更新用户资料
 * @param {Object} profileData - 用户资料数据
 * @param {string} profileData.nickname - 昵称
 * @param {string} profileData.avatar_url - 头像 URL
 */
const updateUserProfile = (profileData) => {
  return put(API_ENDPOINTS.USER.UPDATE, profileData);
};

module.exports = {
  getUserProfile,
  updateUserProfile
};
