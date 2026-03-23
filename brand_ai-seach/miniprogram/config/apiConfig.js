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
// 【P0 修复 - 2026-03-11】端口从 5000 修改为 5001，与后端 main.py 保持一致
const DEV_CONFIG = {
  API_BASE_URL: 'http://localhost:5001',
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
const APIConfig = {
  // API 基础地址
  API_BASE_URL: CURRENT_CONFIG.API_BASE_URL,

  // 请求超时时间（毫秒）
  API_TIMEOUT: CURRENT_CONFIG.API_TIMEOUT,

  // 重试次数
  API_RETRY_COUNT: CURRENT_CONFIG.API_RETRY_COUNT,

  // 是否启用 HTTP 直连模式
  // 【P0 修复 - 2026-03-11】启用 HTTP 直连，云函数未部署时使用此模式
  USE_HTTP_DIRECT: true
};

/**
 * 获取 API 基础地址
 * @returns {string} API 基础地址
 */
function getApiBaseUrl() {
  return APIConfig.API_BASE_URL;
}

/**
 * 获取请求超时时间
 * @returns {number} 超时时间（毫秒）
 */
function getApiTimeout() {
  return APIConfig.API_TIMEOUT;
}

/**
 * 检查是否启用 HTTP 直连模式
 * @returns {boolean} 是否直连
 */
function isHttpDirect() {
  return APIConfig.USE_HTTP_DIRECT;
}

// 导出（CommonJS 语法，兼容微信小程序）
module.exports = APIConfig;
module.exports.default = APIConfig; // 兼容 .default 导入方式
module.exports.getApiBaseUrl = getApiBaseUrl;
module.exports.getApiTimeout = getApiTimeout;
module.exports.isHttpDirect = isHttpDirect;
