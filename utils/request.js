/**
 * 统一请求工具
 * 符合 REFACTOR_GUIDE.md 规范
 * 
 * 增强功能：
 * - 自动 Token 刷新机制
 * - 401 错误自动重试
 */

const { debugLog, debugLogAiIo, debugLogStatusFlow, debugLogResults, debugLogException, ENABLE_DEBUG_AI_CODE } = require('./debug');
const { API_ENDPOINTS } = require('./config');

const ENV_CONFIG = {
  develop: { baseURL: 'http://127.0.0.1:5001', timeout: 30000 },  // 修改为 5001 端口，避免与 macOS AirTunes 冲突
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

const request = (options = {}) => {
  return new Promise((resolve, reject) => {
    const {
      url, method = 'GET', data = {}, header = {},
      loading = true, timeout = env.timeout, showError = true
    } = options;

    const executionId = data.execution_id || data.task_id || 'unknown';

    // 获取设备 ID 和 OpenID
    const app = getApp();
    const deviceId = app ? (app.globalData.deviceId || wx.getStorageSync('device_id')) : null;
    const openid = app ? (app.globalData.openid || wx.getStorageSync('openid')) : null;

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
      header: { 'Content-Type': 'application/json', ...header },
      timeout: timeout || env.timeout,
      success: (response) => {
        if (loading) wx.hideLoading();
        if (ENABLE_DEBUG_AI_CODE) {
          debugLog('RESPONSE', executionId, `Status: ${response.statusCode}`);
          debugLog('RESPONSE_DATA', executionId, `Data: ${JSON.stringify(response.data).substring(0, 200)}...`);
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

const get = (url, params = {}, options = {}) => request({ url, method: 'GET', data: params, ...options });
const post = (url, data = {}, options = {}) => request({ url, method: 'POST', data, ...options });
const put = (url, data = {}, options = {}) => request({ url, method: 'PUT', data, ...options });
const del = (url, data = {}, options = {}) => request({ url, method: 'DELETE', data, ...options });

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

module.exports = { request, get, post, put, delete: del, ENV_CONFIG, clearStorage, clearStorageRecursive };
