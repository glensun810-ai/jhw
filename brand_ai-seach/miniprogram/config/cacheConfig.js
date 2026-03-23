/**
 * 缓存配置模块
 * 
 * 提供缓存版本管理、缓存策略配置等功能
 */

const CACHE_CONFIG = {
  // 缓存版本（每次更新缓存策略时递增）
  version: 'v1.0.0',
  
  // 缓存名称前缀
  prefix: 'wechat-app',
  
  // 缓存类型
  caches: {
    // 静态资源缓存（页面、组件、样式）
    static: 'static',
    // API 响应缓存
    api: 'api',
    // 用户数据缓存
    user: 'user',
    // 临时缓存
    temp: 'temp'
  },
  
  // 缓存大小限制
  maxSize: {
    // API 缓存最多保存 50 个响应
    api: 50,
    // 用户数据缓存最多保存 20 个
    user: 20,
    // 临时缓存最多保存 10 个
    temp: 10
  },
  
  // 缓存过期时间（毫秒）
  expiration: {
    // API 缓存 5 分钟过期
    api: 5 * 60 * 1000,
    // 用户数据缓存 30 分钟过期
    user: 30 * 60 * 1000,
    // 临时缓存 1 分钟过期
    temp: 1 * 60 * 1000,
    // 静态资源缓存 24 小时过期
    static: 24 * 60 * 60 * 1000
  },
  
  // API 缓存白名单（只缓存这些路径的 GET 请求）
  apiWhitelist: [
    '/api/home',
    '/api/history',
    '/api/user',
    '/api/brand',
    '/api/competitive-analysis',
    '/api/data-sync',
    '/api/export'
  ],
  
  // API 缓存黑名单（不缓存这些路径）
  apiBlacklist: [
    '/api/auth',
    '/api/login',
    '/api/logout',
    '/api/diagnosis/start',
    '/api/diagnosis/submit',
    '/api/diagnosis/status'
  ],
  
  // 静态资源缓存列表
  staticAssets: [
    // 核心页面
    '/pages/index/index',
    '/pages/history/history',
    '/pages/saved-results/saved-results',
    '/pages/user-profile/user-profile',
    
    // 报告相关页面
    '/pages/report/dashboard/index',
    '/pages/report-v2/report-v2',
    
    // 常用组件
    '/components/error-toast/error-toast',
    '/components/skeleton/skeleton',
    '/components/virtual-list/virtualList',
    '/components/keyword-cloud/keyword-cloud',
    '/components/sentiment-chart/sentiment-chart',
    '/components/brand-distribution/brand-distribution',
    
    // 核心服务
    '/services/reportService',
    '/services/diagnosisService',
    '/services/webSocketClient',
    '/services/pollingManager',
    
    // 工具类
    '/utils/errorHandler',
    '/utils/retryStrategy',
    '/utils/uiHelper',
    
    // 配置
    '/config/featureFlags'
  ],
  
  // 网络策略
  network: {
    // 超时时间（毫秒）
    timeout: 30000,
    // 重试次数
    retryCount: 3,
    // 重试延迟（毫秒）
    retryDelay: 1000
  },
  
  // 离线模式配置
  offline: {
    // 是否启用离线模式
    enabled: true,
    // 离线提示消息
    message: '当前处于离线模式，部分功能可能受限',
    // 自动检测网络状态
    autoDetect: true
  }
};

/**
 * 获取完整的缓存名称
 * @param {string} type - 缓存类型
 * @returns {string} 完整的缓存名称
 */
function getCacheName(type) {
  const cacheType = CACHE_CONFIG.caches[type] || type;
  return `${CACHE_CONFIG.prefix}-${cacheType}-${CACHE_CONFIG.version}`;
}

/**
 * 检查 API 路径是否应该被缓存
 * @param {string} path - API 路径
 * @param {string} method - HTTP 方法
 * @returns {boolean} 是否应该缓存
 */
function shouldCacheApi(path, method = 'GET') {
  // 只缓存 GET 请求
  if (method !== 'GET') {
    return false;
  }
  
  // 检查是否在黑名单中
  const isInBlacklist = CACHE_CONFIG.apiBlacklist.some(blacklistPath => 
    path.startsWith(blacklistPath)
  );
  
  if (isInBlacklist) {
    return false;
  }
  
  // 检查是否在白名单中
  const isInWhitelist = CACHE_CONFIG.apiWhitelist.some(whitelistPath => 
    path.startsWith(whitelistPath)
  );
  
  return isInWhitelist;
}

/**
 * 检查是否为静态资源
 * @param {string} path - 资源路径
 * @returns {boolean} 是否为静态资源
 */
function isStaticAsset(path) {
  const patterns = [
    /^\/pages\//,
    /^\/components\//,
    /^\/services\//,
    /^\/utils\//,
    /^\/config\//
  ];
  
  return patterns.some(pattern => pattern.test(path));
}

/**
 * 获取缓存过期时间
 * @param {string} type - 缓存类型
 * @returns {number} 过期时间（毫秒）
 */
function getCacheExpiration(type) {
  return CACHE_CONFIG.expiration[type] || CACHE_CONFIG.expiration.temp;
}

/**
 * 获取缓存大小限制
 * @param {string} type - 缓存类型
 * @returns {number} 最大缓存数量
 */
function getMaxCacheSize(type) {
  return CACHE_CONFIG.maxSize[type] || CACHE_CONFIG.maxSize.temp;
}

/**
 * 检查是否检查是否启用离线模式
 * @returns {boolean} 是否启用离线模式
 */
function isOfflineEnabled() {
  return CACHE_CONFIG.offline.enabled;
}

/**
 * 获取离线提示消息
 * @returns {string} 离线提示消息
 */
function getOfflineMessage() {
  return CACHE_CONFIG.offline.message;
}

module.exports = {
  CACHE_CONFIG,
  getCacheName,
  shouldCacheApi,
  isStaticAsset,
  getCacheExpiration,
  getMaxCacheSize,
  isOfflineEnabled,
  getOfflineMessage
};
