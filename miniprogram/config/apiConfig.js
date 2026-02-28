/**
 * API 配置
 *
 * 配置后端 API 地址和环境切换
 *
 * @author 系统架构组
 * @date 2026-02-28
 * @version 1.0.0
 */

// 开发环境配置
const DEV_CONFIG = {
  API_BASE_URL: 'http://localhost:5000',
  API_TIMEOUT: 30000,
  API_RETRY_COUNT: 3
};

// 生产环境配置（微信小程序云函数模式）
const PROD_CONFIG = {
  API_BASE_URL: 'https://your-domain.com',
  API_TIMEOUT: 30000,
  API_RETRY_COUNT: 3
};

// 当前环境
const IS_DEV = process.env && process.env.NODE_ENV === 'development';

// 当前配置
const CURRENT_CONFIG = IS_DEV ? DEV_CONFIG : PROD_CONFIG;

/**
 * API 配置对象
 */
export const APIConfig = {
  // API 基础地址
  API_BASE_URL: CURRENT_CONFIG.API_BASE_URL,

  // 请求超时时间（毫秒）
  API_TIMEOUT: CURRENT_CONFIG.API_TIMEOUT,

  // 重试次数
  API_RETRY_COUNT: CURRENT_CONFIG.API_RETRY_COUNT,

  // 是否启用 HTTP 直连模式（微信小程序建议使用云函数）
  // 注意：小程序环境需要使用云函数代理，避免 CORS 问题
  USE_HTTP_DIRECT: false
};

/**
 * 获取 API 基础地址
 * @returns {string} API 基础地址
 */
export function getApiBaseUrl() {
  return APIConfig.API_BASE_URL;
}

/**
 * 获取请求超时时间
 * @returns {number} 超时时间（毫秒）
 */
export function getApiTimeout() {
  return APIConfig.API_TIMEOUT;
}

/**
 * 检查是否启用 HTTP 直连模式
 * @returns {boolean} 是否直连
 */
export function isHttpDirect() {
  return APIConfig.USE_HTTP_DIRECT;
}

export default APIConfig;
