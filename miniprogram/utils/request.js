/**
 * 统一请求工具
 * 符合 REFACTOR_GUIDE.md 规范
 */

// 环境配置
const ENV_CONFIG = {
  develop: {
    baseURL: 'http://127.0.0.1:5001', // 开发环境 API 地址
    timeout: 30000 // 30秒超时
  },
  trial: {
    baseURL: 'https://staging.api.yourdomain.com', // 体验版 API 地址
    timeout: 20000 // 20秒超时
  },
  release: {
    baseURL: 'https://api.yourdomain.com', // 正式环境 API 地址
    timeout: 15000 // 15秒超时
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

const env = getCurrentEnv();

/**
 * 统一请求方法
 * @param {Object} options - 请求参数
 * @param {string} options.url - 请求地址
 * @param {string} options.method - 请求方法
 * @param {Object} options.data - 请求数据
 * @param {Object} options.header - 请求头
 * @param {boolean} options.loading - 是否显示loading
 * @param {number} options.timeout - 超时时间
 * @param {boolean} options.showError - 是否显示错误提示
 * @returns {Promise}
 */
const request = (options = {}) => {
  return new Promise((resolve, reject) => {
    const {
      url,
      method = 'GET',
      data = {},
      header = {},
      loading = true,
      timeout = env.timeout,
      showError = true
    } = options;

    // 显示加载动画
    if (loading) {
      wx.showLoading({
        title: '加载中...',
        mask: true
      });
    }

    // 构建请求参数
    const requestParams = {
      url: url.startsWith('http') ? url : env.baseURL + url, // 支持绝对路径和相对路径
      method: method.toUpperCase(),
      data: data,
      header: {
        'Content-Type': 'application/json',
        ...header
      },
      timeout: timeout || env.timeout,
      success: (response) => {
        // 隐藏加载动画
        if (loading) {
          wx.hideLoading();
        }

        // 检查响应状态
        if (response.statusCode === 200) {
          // 成功响应
          resolve(response.data);
        } else if (response.statusCode === 401) {
          // 未授权，需要重新登录
          handleUnauthorized();
          const errorMsg = '未授权，请重新登录';
          if (showError) {
            wx.showToast({
              title: errorMsg,
              icon: 'none'
            });
          }
          reject(new Error(errorMsg));
        } else {
          // 其他错误状态码
          // 错误捕获增强：如果状态码为 400，尝试打印出后端返回的 res.data.error 或 res.data.details
          let errorMsg = `请求失败，状态码: ${response.statusCode}`;
          if (response.statusCode === 400 && response.data) {
            if (response.data.error) {
              errorMsg += ` - ${response.data.error}`;
            }
            if (response.data.details) {
              errorMsg += ` (${response.data.details})`;
            }
          }

          if (showError) {
            wx.showToast({
              title: '请求失败',
              icon: 'none'
            });
          }
          reject(new Error(errorMsg));
        }
      },
      fail: (error) => {
        // 隐藏加载动画
        if (loading) {
          wx.hideLoading();
        }

        // 请求失败
        const errorMsg = error.errMsg || '网络请求失败';
        if (showError) {
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          });
        }
        reject(new Error(errorMsg));
      }
    };

    // 请求拦截器：自动添加token
    const token = wx.getStorageSync('userToken');
    if (token) {
      requestParams.header.Authorization = `Bearer ${token}`;
    }

    // 发起请求
    wx.request(requestParams);
  });
};

/**
 * 处理401未授权状态
 */
const handleUnauthorized = () => {
  // 清空本地缓存的用户信息
  wx.removeStorageSync('userInfo');
  wx.removeStorageSync('userToken');
  wx.removeStorageSync('isLoggedIn');
  wx.removeStorageSync('userPermissions');

  // 跳转到登录页面
  wx.redirectTo({
    url: '/pages/login/login'
  });
};

/**
 * GET 请求封装
 * @param {string} url - 请求地址
 * @param {Object} params - 查询参数
 * @param {Object} options - 其他选项
 * @returns {Promise}
 */
const get = (url, params = {}, options = {}) => {
  return request({
    url,
    method: 'GET',
    data: params,
    ...options
  });
};

/**
 * POST 请求封装
 * @param {string} url - 请求地址
 * @param {Object} data - 请求数据
 * @param {Object} options - 其他选项
 * @returns {Promise}
 */
const post = (url, data = {}, options = {}) => {
  return request({
    url,
    method: 'POST',
    data,
    ...options
  });
};

/**
 * PUT 请求封装
 * @param {string} url - 请求地址
 * @param {Object} data - 请求数据
 * @param {Object} options - 其他选项
 * @returns {Promise}
 */
const put = (url, data = {}, options = {}) => {
  return request({
    url,
    method: 'PUT',
    data,
    ...options
  });
};

/**
 * DELETE 请求封装
 * @param {string} url - 请求地址
 * @param {Object} data - 请求数据
 * @param {Object} options - 其他选项
 * @returns {Promise}
 */
const del = (url, data = {}, options = {}) => {
  return request({
    url,
    method: 'DELETE',
    data,
    ...options
  });
};

module.exports = {
  request,
  get,
  post,
  put,
  delete: del, // 避免与 JavaScript 关键字冲突
  ENV_CONFIG
};