/**
 * 统一配置文件
 * 将散落的硬编码URL和其他配置项收拢至此
 */

// API端点配置
const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/login',
    VALIDATE_TOKEN: '/api/validate-token',  // Needs backend implementation
    REFRESH_TOKEN: '/api/refresh-token',   // Needs backend implementation
    SEND_VERIFICATION_CODE: '/api/send-verification-code',  // Needs backend implementation
    REGISTER: '/api/register'               // Needs backend implementation
  },
  USER: {
    PROFILE: '/api/user/profile',          // Needs backend implementation
    UPDATE: '/api/user/update'             // Needs backend implementation
  },
  SYNC: {
    DATA: '/api/sync-data',                // Needs backend implementation
    DOWNLOAD: '/api/download-data',        // Needs backend implementation
    UPLOAD_RESULT: '/api/upload-result',   // Needs backend implementation
    DELETE_RESULT: '/api/delete-result'    // Needs backend implementation
  },
  HISTORY: {
    LIST: '/api/test-history'
  },
  BRAND: {
    TEST: '/api/perform-brand-test',
    PROGRESS: '/api/test-progress'
  },
  COMPETITIVE: {
    ANALYSIS: '/action/recommendations'   // Matches existing backend endpoint
  },
  SYSTEM: {
    TEST_CONNECTION: '/api/test'
  }
};

// 环境配置
const ENV_CONFIG = {
  develop: {
    // 使用 127.0.0.1 作为默认开发地址，支持模拟器调试
    // 真机调试时，在微信开发者工具中设置"不校验合法域名"即可使用本地服务
    baseURL: 'http://127.0.0.1:5001', // 开发环境 API 地址
    timeout: 30000, // 30秒超时
    env: 'dev'
  },
  trial: {
    baseURL: 'https://staging.api.yourdomain.com', // 体验版 API 地址
    timeout: 20000, // 20秒超时
    env: 'trial'
  },
  release: {
    baseURL: 'https://api.yourdomain.com', // 正式环境 API 地址
    timeout: 15000, // 15秒超时
    env: 'release'
  }
};

// 获取当前环境配置
const getCurrentEnv = () => {
  try {
    const accountInfo = wx.getAccountInfoSync();
    const envVersion = accountInfo.miniProgram.envVersion || 'release'; // 默认为正式版
    return ENV_CONFIG[envVersion] || ENV_CONFIG.release;
  } catch (e) {
    console.warn('获取环境信息失败，默认使用生产环境配置', e);
    return ENV_CONFIG.release;
  }
};

// 当前环境配置
const CURRENT_ENV = getCurrentEnv();

// 完整的基础URL
const BASE_URL = CURRENT_ENV.baseURL;

module.exports = {
  API_ENDPOINTS,
  ENV_CONFIG,
  CURRENT_ENV,
  BASE_URL
};