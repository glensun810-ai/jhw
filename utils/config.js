/**
 * 统一配置文件
 * 将散落的硬编码 URL 和其他配置项收拢至此
 */

// API 端点配置
const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/login',
    VALIDATE_TOKEN: '/api/validate-token',
    REFRESH_TOKEN: '/api/refresh-token',
    SEND_VERIFICATION_CODE: '/api/send-verification-code',
    REGISTER: '/api/register'
  },
  USER: {
    PROFILE: '/api/user/profile',
    UPDATE: '/api/user/update'
  },
  SYNC: {
    DATA: '/api/sync/data',
    DOWNLOAD: '/api/sync/download',
    UPLOAD_RESULT: '/api/sync/upload-result',
    DELETE_RESULT: '/api/sync/delete-result',
    STATUS: '/api/sync/status'
  },
  ANALYTICS: {
    TRACK: '/api/analytics/track',
    USER_JOURNEY: '/api/analytics/user-journey',
    STATISTICS: '/api/analytics/statistics',
    HEATMAP: '/api/analytics/heatmap',
    FUNNEL: '/api/analytics/funnel'
  },
  AUDIT: {
    LOG: '/api/audit/log',
    LOGS: '/api/audit/logs',
    REPORT: '/api/audit/report',
    COMPLIANCE: '/api/audit/compliance',
    USER_ACTIVITY: '/api/audit/user-activity'
  },
  HISTORY: {
    LIST: '/api/test-history'
  },
  BRAND: {
    TEST: '/api/perform-brand-test',
    PROGRESS: '/api/test-progress',
    STATUS: '/test/status'
  },
  COMPETITIVE: {
    ANALYSIS: '/action/recommendations'
  },
  INTELLIGENCE: {
    PIPELINE: '/api/intelligence/pipeline',
    STREAM: '/api/intelligence/stream',
    ADD: '/api/intelligence/add',
    UPDATE: '/api/intelligence/update',
    CLEAR: '/api/intelligence/clear'
  },
  CACHE: {
    STATS: '/api/cache/stats',
    CLEAR: '/api/cache/clear',
    INVALIDATE: '/api/cache/invalidate'
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
    // 注意：确保后端服务运行在相同端口（默认 5001），与 backend_python/run.py 中的端口保持一致
    baseURL: 'http://127.0.0.1:5001', // 开发环境 API 地址
    timeout: 30000, // 30 秒超时
    env: 'dev'
  },
  trial: {
    baseURL: 'https://staging.api.yourdomain.com', // 体验版 API 地址
    timeout: 20000, // 20 秒超时
    env: 'trial'
  },
  release: {
    baseURL: 'https://api.yourdomain.com', // 正式环境 API 地址
    timeout: 15000, // 15 秒超时
    env: 'release'
  }
};

// 允许从环境变量或本地存储覆盖基础 URL
const getBaseUrlOverride = () => {
  try {
    // 检查本地存储中是否有自定义的 API 地址
    const customBaseURL = wx.getStorageSync('custom_base_url');
    if (customBaseURL && typeof customBaseURL === 'string' && customBaseURL.startsWith('http')) {
      return customBaseURL;
    }
  } catch (e) {
    console.warn('无法获取自定义 API 地址:', e);
  }
  return null;
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

// 完整的基础 URL
const BASE_URL = CURRENT_ENV.baseURL;

module.exports = {
  API_ENDPOINTS,
  ENV_CONFIG,
  CURRENT_ENV,
  BASE_URL
};
