/**
 * 认证相关API接口
 * 从 utils/auth.js 中提取的网络请求逻辑
 */

const { request, post, get } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 用户登录
 * @param {Object} loginData 登录数据
 * @returns {Promise}
 */
const userLogin = (loginData) => {
  return post(API_ENDPOINTS.AUTH.LOGIN, loginData);
};

/**
 * 验证令牌
 * @returns {Promise}
 */
const validateToken = () => {
  return post(API_ENDPOINTS.AUTH.VALIDATE_TOKEN);
};

/**
 * 刷新令牌
 * @param {string} refreshToken 刷新令牌
 * @returns {Promise}
 */
const refreshToken = (refreshToken) => {
  return post(API_ENDPOINTS.AUTH.REFRESH_TOKEN, { refresh_token: refreshToken });
};

/**
 * 发送验证码
 * @param {Object} data - 请求数据
 * @param {string} data.phone - 手机号
 * @returns {Promise}
 */
const sendVerificationCode = (data) => {
  return post(API_ENDPOINTS.AUTH.SEND_VERIFICATION_CODE, data);
};

/**
 * 用户注册
 * @param {Object} data - 注册数据
 * @param {string} data.phone - 手机号
 * @param {string} data.verificationCode - 验证码
 * @param {string} data.password - 密码
 * @returns {Promise}
 */
const registerUser = (data) => {
  return post(API_ENDPOINTS.AUTH.REGISTER, data);
};

module.exports = {
  userLogin,
  validateToken,
  refreshToken,
  sendVerificationCode,
  registerUser
};