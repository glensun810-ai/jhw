/**
 * 统一请求工具
 * 符合 REFACTOR_GUIDE.md 规范
 *
 * 增强功能：
 * - 自动 Token 刷新机制
 * - 401 错误自动重试
 * - P1-5 优化：智能重试机制（指数退避 + 错误分类）
 * - P2 优化：请求重试机制（指数退避）
 * - P2 优化：加载进度显示
 */

const { debugLog, debugLogAiIo, debugLogStatusFlow, debugLogResults, debugLogException, ENABLE_DEBUG_AI_CODE } = require('./debug');
const { API_ENDPOINTS } = require('./config');

// P1-5 优化：重试配置增强
const RETRY_CONFIG = {
  MAX_RETRIES: 3,           // 最大重试次数
  BASE_DELAY: 1000,         // 基础延迟 (ms)
  MAX_DELAY: 10000,         // 最大延迟 (ms)
  RETRYABLE_ERRORS: [       // 可重试的错误
    'request:fail',
    'timeout',
    'network',
    'ETIMEDOUT',
    'ENOTFOUND',
    'Connection refused'
  ],
  // P1-5 新增：HTTP 状态码重试策略
  RETRYABLE_STATUS_CODES: [408, 429, 500, 502, 503, 504],
  // P1-5 新增：不重试的状态码
  NON_RETRYABLE_STATUS_CODES: [400, 401, 403, 404, 422],
  // P1-5 新增：超时配置
  TIMEOUT: 30000            // 请求超时 (ms)
};

const ENV_CONFIG = {
  develop: { baseURL: 'http://127.0.0.1:5001', timeout: 30000 },  // 开发环境默认端口（使用 5001 避免与 macOS Control Center 冲突）
  trial: { baseURL: 'https://staging.api.yourdomain.com', timeout: 20000 },
  release: { baseURL: 'https://api.yourdomain.com', timeout: 15000 }
};

const getCurrentEnv = () => {
  try {
    const accountInfo = wx.getAccountInfoSync();
    const envVersion = accountInfo.miniProgram.envVersion || 'release';
    return ENV_CONFIG[envVersion] || ENV_CONFIG.release;
  } catch (e) {
    console.warn('获取环境信息失败', e);
    return ENV_CONFIG.release;
  }
};

const env = getCurrentEnv();

const getBaseUrl = () => {
  try {
    const customBaseURL = wx.getStorageSync('custom_base_url');
    if (customBaseURL && customBaseURL.startsWith('http')) return customBaseURL;
  } catch (e) {
    console.warn('无法获取自定义 API 地址:', e);
  }
  return env.baseURL;
};

// =============================================================================
// P1-5 优化：重试机制辅助函数增强
// =============================================================================

/**
 * 延迟函数
 * @param {number} ms - 延迟毫秒数
 * @returns {Promise}
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * P1-5 增强：判断错误是否可重试
 * @param {Error} error - 错误对象
 * @param {number} statusCode - HTTP 状态码
 * @returns {boolean}
 */
const isRetryableError = (error, statusCode) => {
  if (!error) return false;
  
  // P1-5 新增：根据 HTTP 状态码判断
  if (statusCode) {
    // 明确不重试的状态码
    if (RETRY_CONFIG.NON_RETRYABLE_STATUS_CODES.includes(statusCode)) {
      return false;
    }
    // 可重试的状态码
    if (RETRY_CONFIG.RETRYABLE_STATUS_CODES.includes(statusCode)) {
      return true;
    }
  }
  
  // 根据错误消息判断
  const errorMsg = String(error.errMsg || error.message || '');
  return RETRY_CONFIG.RETRYABLE_ERRORS.some(retryable =>
    errorMsg.toLowerCase().includes(retryable.toLowerCase())
  );
};

/**
 * P1-5 新增：错误分类
 * @param {Error} error - 错误对象
 * @param {number} statusCode - HTTP 状态码
 * @returns {string} 错误类型
 */
const classifyError = (error, statusCode) => {
  if (!error) return 'unknown';
  
  // HTTP 状态码分类
  if (statusCode) {
    if (statusCode >= 200 && statusCode < 300) return 'success';
    if (statusCode === 400) return 'bad_request';
    if (statusCode === 401) return 'unauthorized';
    if (statusCode === 403) return 'forbidden';
    if (statusCode === 404) return 'not_found';
    if (statusCode === 408) return 'timeout';
    if (statusCode === 429) return 'rate_limit';
    if (statusCode >= 500 && statusCode < 600) return 'server_error';
  }
  
  // 错误消息分类
  const errorMsg = String(error.errMsg || error.message || '').toLowerCase();
  if (errorMsg.includes('timeout')) return 'timeout';
  if (errorMsg.includes('network') || errorMsg.includes('fail')) return 'network';
  if (errorMsg.includes('auth')) return 'unauthorized';
  
  return 'unknown';
};

/**
 * 计算重试延迟（指数退避 + 随机抖动）
 * @param {number} retryCount - 当前重试次数
 * @returns {number} 延迟毫秒数
 */
const getRetryDelay = (retryCount) => {
  const delay = RETRY_CONFIG.BASE_DELAY * Math.pow(2, retryCount);
  // P1-5 新增：添加随机抖动，避免多个请求同时重试
  const jitter = Math.random() * 0.3 * delay; // 0-30% jitter
  return Math.min(delay + jitter, RETRY_CONFIG.MAX_DELAY);
};

/**
 * P1-5 新增：生成错误提示文本
 * @param {string} errorType - 错误类型
 * @param {number} retryCount - 重试次数
 * @returns {string} 用户友好的错误提示
 */
const getErrorUserMessage = (errorType, retryCount = 0) => {
  const messages = {
    timeout: '请求超时，服务器响应缓慢',
    network: '网络连接失败，请检查网络设置',
    unauthorized: '登录已过期，请重新登录',
    forbidden: '无权访问此资源',
    not_found: '请求的资源不存在',
    rate_limit: '请求过于频繁，请稍后重试',
    server_error: '服务器暂时不可用，请稍后重试',
    bad_request: '请求格式错误',
    unknown: '网络开小差了，请稍后重试'
  };
  
  const baseMessage = messages[errorType] || messages.unknown;
  
  if (retryCount > 0) {
    return `${baseMessage}（已重试${retryCount}次）`;
  }
  
  return baseMessage;
};

// =============================================================================
// P2 优化：加载进度显示辅助函数
// =============================================================================

/**
 * 显示加载进度
 * @param {string} text - 进度文本
 * @param {number} progress - 进度值 (0-100)
 */
const showLoadingProgress = (text, progress) => {
  try {
    // 微信小程序原生 loading 不支持进度条，使用 toast 替代
    if (progress >= 100) {
      wx.hideLoading();
    } else {
      wx.showLoading({
        title: `${text} (${progress}%)`,
        mask: true
      });
    }
  } catch (e) {
    console.warn('显示加载进度失败:', e);
  }
};

/**
 * 更新加载进度
 * @param {string} stage - 当前阶段
 * @param {number} current - 当前进度
 * @param {number} total - 总进度
 */
const updateLoadingProgress = (stage, current, total) => {
  const progress = Math.round((current / total) * 100);
  const stageTexts = {
    'init': '正在初始化',
    'ai_fetching': '正在连接 AI 平台',
    'intelligence_analyzing': '正在分析数据',
    'competition_analyzing': '正在比对竞品',
    'completed': '诊断完成'
  };
  const text = stageTexts[stage] || stage || '加载中';
  showLoadingProgress(text, progress);
};

// =============================================================================
// Token 刷新相关
// =============================================================================

// Token 刷新锁，防止并发刷新
let isRefreshing = false;
let refreshQueue = [];

/**
 * 执行刷新队列中的请求
 */
const executeRefreshQueue = (newToken) => {
  refreshQueue.forEach(({ resolve, options }) => {
    // 使用新 token 重试请求
    const newHeader = { ...options.header, Authorization: `Bearer ${newToken}` };
    request({ ...options, header: newHeader, loading: false })
      .then(resolve)
      .catch(() => {}); // 忽略二次错误
  });
  refreshQueue = [];
};

/**
 * 拒绝刷新队列中的请求
 */
const rejectRefreshQueue = (error) => {
  refreshQueue.forEach(({ reject }) => reject(error));
  refreshQueue = [];
};

/**
 * 刷新 Token
 */
const refreshToken = () => {
  return new Promise((resolve, reject) => {
    const refresh_token = wx.getStorageSync('refreshToken');
    
    if (!refresh_token) {
      console.error('No refresh token available');
      reject(new Error('No refresh token'));
      return;
    }
    
    wx.request({
      url: getBaseUrl() + API_ENDPOINTS.AUTH.REFRESH_TOKEN,
      method: 'POST',
      data: { refresh_token },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          // 保存新 token
          wx.setStorageSync('userToken', res.data.token);
          wx.setStorageSync('refreshToken', res.data.refresh_token);
          console.log('Token refreshed successfully');
          resolve(res.data.token);
        } else {
          console.error('Token refresh failed:', res.data);
          reject(new Error('Token refresh failed'));
        }
      },
      fail: (err) => {
        console.error('Token refresh request failed:', err);
        reject(err);
      }
    });
  });
};

/**
 * 带重试的请求函数（P1-5 优化）
 * @param {Object} options - 请求选项
 * @param {number} retryCount - 当前重试次数
 * @returns {Promise}
 */
const requestWithRetry = async (options, retryCount = 0) => {
  const startTime = Date.now();
  
  try {
    const result = await executeRequest(options);
    
    // 记录成功请求的耗时
    const duration = Date.now() - startTime;
    if (duration > 1000) {
      console.log(`⚠️ 慢请求警告：${options.url} 耗时 ${duration}ms`);
    }
    
    return result;
  } catch (error) {
    const errorType = classifyError(error, error.statusCode);
    const duration = Date.now() - startTime;
    
    // Step 1: 403 错误不重试，立即返回
    if (error.statusCode === 403 || error.isAuthError) {
      console.error(`请求失败 (${error.statusCode})，不重试：${options.url}`);
      throw error;
    }

    // P1-5 增强：判断是否可重试
    if (retryCount < RETRY_CONFIG.MAX_RETRIES && isRetryableError(error, error.statusCode)) {
      const delay = getRetryDelay(retryCount);
      console.log(`请求失败 (${errorType})，${Math.round(delay)}ms 后重试 (${retryCount + 1}/${RETRY_CONFIG.MAX_RETRIES}): ${options.url}`);

      // 显示重试提示
      if (options.loading) {
        const retryMessage = getErrorUserMessage(errorType, retryCount + 1);
        wx.showLoading({ title: retryMessage, mask: true });
      }

      await sleep(delay);
      return requestWithRetry(options, retryCount + 1);
    }

    // 不可重试或已达最大重试次数，记录错误日志
    console.error(`请求最终失败 (${errorType}): ${options.url}, 耗时 ${duration}ms`);
    
    // P1-5 新增：添加用户友好的错误消息
    if (!error.userMessage) {
      error.userMessage = getErrorUserMessage(errorType, retryCount);
    }
    
    throw error;
  }
};

/**
 * 执行实际请求
 */
const executeRequest = (options = {}) => {
  return new Promise((resolve, reject) => {
    const {
      url, method = 'GET', data = {}, header = {},
      loading = true, timeout = env.timeout, showError = true,
      skipAuth = false  // Step 1: 新增跳过认证的选项
    } = options;

    const executionId = data.execution_id || data.task_id || 'unknown';

    // 获取设备 ID 和 OpenID
    const app = getApp();
    const deviceId = app ? (app.globalData.deviceId || wx.getStorageSync('device_id')) : null;
    const openid = app ? (app.globalData.openid || wx.getStorageSync('openid')) : null;

    // Step 1: 构建请求头，默认携带 Token
    const defaultHeader = { 'Content-Type': 'application/json' };
    
    // 如果不是跳过认证的请求，尝试添加 Token
    if (!skipAuth) {
      const token = wx.getStorageSync('userToken');
      if (token) {
        defaultHeader['Authorization'] = `Bearer ${token}`;
      }
    }

    const finalHeader = { ...defaultHeader, ...header };

    if (ENABLE_DEBUG_AI_CODE) {
      debugLog('REQUEST', executionId, `Sending ${method} request to ${url}`);
      debugLog('REQUEST_DATA', executionId, `Request data: ${JSON.stringify(data).substring(0, 200)}...`);
    }

    if (loading) wx.showLoading({ title: '加载中...', mask: true });

    const baseUrl = getBaseUrl();
    const fullUrl = url.startsWith('http') ? url : baseUrl + url;
    const normalizedUrl = fullUrl.replace(/([^:])\/\//g, '$1/');

    const requestParams = {
      url: normalizedUrl,
      method: method.toUpperCase(),
      data,
      header: finalHeader,
      timeout: timeout || env.timeout,
      success: (response) => {
        if (loading) wx.hideLoading();
        if (ENABLE_DEBUG_AI_CODE) {
          debugLog('RESPONSE', executionId, `Status: ${response.statusCode}`);
          debugLog('RESPONSE_DATA', executionId, `Data: ${JSON.stringify(response.data).substring(0, 200)}...`);
        }

        // Step 1: 处理 403 错误 - 立即返回错误，不重试
        if (response.statusCode === 403) {
          const error = new Error('权限验证失败 (403)');
          error.statusCode = 403;
          error.isAuthError = true;  // 标记为认证错误，触发熔断
          reject(error);
          return;
        }

        // 处理 401 错误 - 尝试刷新 token
        if (response.statusCode === 401) {
          // 如果不是刷新 token 的请求本身失败
          if (!options.url.includes('/api/refresh-token')) {
            if (isRefreshing) {
              // 已经在刷新，加入队列等待
              refreshQueue.push({ resolve, reject, options });
              return;
            }
            
            isRefreshing = true;
            
            // 尝试刷新 token
            refreshToken()
              .then((newToken) => {
                isRefreshing = false;
                // 执行队列中的请求
                executeRefreshQueue(newToken);
                // 重试原请求
                const newHeader = { ...header, Authorization: `Bearer ${newToken}` };
                return request({ ...options, header: newHeader, loading: false });
              })
              .then(resolve)
              .catch((err) => {
                isRefreshing = false;
                rejectRefreshQueue(err);
                handleUnauthorized();
                reject(new Error('认证失效，请重新登录'));
              });
            return;
          } else {
            // refresh token 请求本身失败
            handleUnauthorized();
            reject(new Error('未授权'));
            return;
          }
        }
        
        if (response.statusCode === 200) {
          resolve(response.data);
        } else {
          reject(new Error(`请求失败，状态码：${response.statusCode}`));
        }
      },
      fail: (error) => {
        if (loading) wx.hideLoading();
        if (ENABLE_DEBUG_AI_CODE) {
          debugLogException(executionId, `Request failed: ${JSON.stringify(error)}`);
        }
        if (error.errMsg && error.errMsg.includes('the maximum size limit exceeded')) {
          clearStorageRecursive();
          resolve(null);
          return;
        }
        reject(new Error(error.errMsg || '网络请求失败'));
      }
    };

    // 请求拦截器：自动添加 token 和设备信息
    const token = wx.getStorageSync('userToken');
    if (token) requestParams.header.Authorization = `Bearer ${token}`;
    if (deviceId) requestParams.header['X-Device-ID'] = deviceId;
    if (openid) requestParams.header['X-User-OpenID'] = openid;

    wx.request(requestParams);
  });
};

const handleUnauthorized = () => {
  wx.removeStorageSync('userInfo');
  wx.removeStorageSync('userToken');
  wx.removeStorageSync('isLoggedIn');
  wx.removeStorageSync('userPermissions');
  wx.redirectTo({ url: '/pages/login/login' });
};

// P2 优化：使用带重试的请求函数
const get = (url, params = {}, options = {}) => requestWithRetry({ url, method: 'GET', data: params, ...options });
const post = (url, data = {}, options = {}) => requestWithRetry({ url, method: 'POST', data, ...options });
const put = (url, data = {}, options = {}) => requestWithRetry({ url, method: 'PUT', data, ...options });
const del = (url, data = {}, options = {}) => requestWithRetry({ url, method: 'DELETE', data, ...options });

const clearStorage = () => {
  wx.getSavedFileList({
    success: (res) => {
      if (res.fileList && res.fileList.length > 0) {
        res.fileList.forEach(file => {
          wx.removeSavedFile({
            filePath: file.filePath,
            success: () => console.log(`成功删除文件：${file.filePath}`),
            fail: (err) => console.error(`删除文件失败：${file.filePath}`, err)
          });
        });
      }
      wx.clearStorage();
    }
  });
};

const clearStorageRecursive = () => {
  const clean = (index = 0) => {
    wx.getSavedFileList({
      success: (res) => {
        if (res.fileList && res.fileList.length > index) {
          wx.removeSavedFile({
            filePath: res.fileList[index].filePath,
            success: () => clean(index + 1),
            fail: () => clean(index + 1)
          });
        } else {
          wx.clearStorage();
        }
      }
    });
  };
  clean();
};

module.exports = {
  request: requestWithRetry,  // 默认导出带重试的版本
  requestWithRetry,
  executeRequest,
  get,
  post,
  put,
  delete: del,
  ENV_CONFIG,
  clearStorage,
  clearStorageRecursive,
  // P2 优化：导出进度显示函数
  showLoadingProgress,
  updateLoadingProgress,
  // P1-5 新增：导出错误处理函数
  classifyError,
  isRetryableError,
  getRetryDelay,
  getErrorUserMessage,
  RETRY_CONFIG
};
