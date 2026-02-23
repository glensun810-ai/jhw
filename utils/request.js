/**
 * 统一请求工具
 * 符合 REFACTOR_GUIDE.md 规范
 *
 * 增强功能：
 * - 自动 Token 刷新机制
 * - 401 错误自动重试
 * - P2 优化：请求重试机制（指数退避）
 * - P2 优化：加载进度显示
 */

const { debugLog, debugLogAiIo, debugLogStatusFlow, debugLogResults, debugLogException, ENABLE_DEBUG_AI_CODE } = require('./debug');
const { API_ENDPOINTS } = require('./config');

// P2 优化：重试配置
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
  ]
};

const ENV_CONFIG = {
  develop: { baseURL: 'http://127.0.0.1:5000', timeout: 30000 },  // 开发环境默认端口
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
// P2 优化：重试机制辅助函数
// =============================================================================

/**
 * 延迟函数
 * @param {number} ms - 延迟毫秒数
 * @returns {Promise}
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * 判断错误是否可重试
 * @param {Error} error - 错误对象
 * @returns {boolean}
 */
const isRetryableError = (error) => {
  if (!error) return false;
  const errorMsg = String(error.errMsg || error.message || '');
  return RETRY_CONFIG.RETRYABLE_ERRORS.some(retryable => 
    errorMsg.toLowerCase().includes(retryable.toLowerCase())
  );
};

/**
 * 计算重试延迟（指数退避）
 * @param {number} retryCount - 当前重试次数
 * @returns {number} 延迟毫秒数
 */
const getRetryDelay = (retryCount) => {
  const delay = RETRY_CONFIG.BASE_DELAY * Math.pow(2, retryCount);
  return Math.min(delay, RETRY_CONFIG.MAX_DELAY);
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
 * 带重试的请求函数（P2 优化）
 * @param {Object} options - 请求选项
 * @param {number} retryCount - 当前重试次数
 * @returns {Promise}
 */
const requestWithRetry = async (options, retryCount = 0) => {
  try {
    return await executeRequest(options);
  } catch (error) {
    // Step 1: 403 错误不重试，立即返回
    if (error.statusCode === 403 || error.isAuthError) {
      console.error(`请求失败 (${error.statusCode})，不重试：${options.url}`);
      throw error;
    }
    
    // 判断是否可重试
    if (retryCount < RETRY_CONFIG.MAX_RETRIES && isRetryableError(error)) {
      const delay = getRetryDelay(retryCount);
      console.log(`请求失败，${delay}ms 后重试 (${retryCount + 1}/${RETRY_CONFIG.MAX_RETRIES}): ${options.url}`);

      // 显示重试提示
      if (options.loading) {
        showLoadingProgress('网络不稳定，重试中', (retryCount + 1) * 20);
      }

      await sleep(delay);
      return requestWithRetry(options, retryCount + 1);
    }

    // 不可重试或已达最大重试次数，抛出错误
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
  updateLoadingProgress
};
