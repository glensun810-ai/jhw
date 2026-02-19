/**
 * 统一请求工具
 * 符合 REFACTOR_GUIDE.md 规范
 */

// 引入 DEBUG_AI_CODE 日志工具
const { debugLog, debugLogAiIo, debugLogStatusFlow, debugLogResults, debugLogException, ENABLE_DEBUG_AI_CODE } = require('./debug');

// 环境配置
const ENV_CONFIG = {
  develop: {
    baseURL: 'http://127.0.0.1:5000', // 开发环境 API 地址 - 与后端实际运行端口保持一致
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

// 获取基础URL覆盖
const getBaseUrl = () => {
  // 优先使用本地存储的自定义URL
  try {
    const customBaseURL = wx.getStorageSync('custom_base_url');
    if (customBaseURL && typeof customBaseURL === 'string' && customBaseURL.startsWith('http')) {
      return customBaseURL;
    }
  } catch (e) {
    console.warn('无法获取自定义API地址:', e);
  }

  // 否则使用环境配置
  return env.baseURL;
};

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

    // Extract execution_id from data if present for cross-end association
    const executionId = data.execution_id || data.task_id || 'unknown';

    // Log request initiation with DEBUG_AI_CODE
    if (ENABLE_DEBUG_AI_CODE) {
      debugLog('REQUEST', executionId, `Sending ${method} request to ${url}`); // #DEBUG_CLEAN
      debugLog('REQUEST_DATA', executionId, `Request data: ${JSON.stringify(data).substring(0, 200)}...`); // #DEBUG_CLEAN
    }

    // 显示加载动画
    if (loading) {
      wx.showLoading({
        title: '加载中...',
        mask: true
      });
    }

    // 构建请求参数
    const baseUrl = getBaseUrl();
    const fullUrl = url.startsWith('http') ? url : baseUrl + url; // 支持绝对路径和相对路径，优先使用自定义URL
    
    // 确保URL格式正确，避免双重斜杠等问题
    const normalizedUrl = fullUrl.replace(/([^:])\/\//g, '$1/'); // 替换多余的双斜杠，但保留协议部分的双斜杠
    
    const requestParams = {
      url: normalizedUrl,
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

        // Log response with DEBUG_AI_CODE
        if (ENABLE_DEBUG_AI_CODE) {
          debugLog('RESPONSE', executionId, `Received response with status: ${response.statusCode}`); // #DEBUG_CLEAN
          debugLog('RESPONSE_DATA', executionId, `Response data preview: ${JSON.stringify(response.data).substring(0, 200)}...`); // #DEBUG_CLEAN
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

        // Log failure with DEBUG_AI_CODE
        if (ENABLE_DEBUG_AI_CODE) {
          debugLogException(executionId, `Request failed: ${JSON.stringify(error)}`); // #DEBUG_CLEAN
        }

        // 检查是否是存储空间超出限制的错误
        if (error.errMsg && error.errMsg.includes('the maximum size limit exceeded')) {
          console.warn('存储空间超出限制，正在清理缓存...');

          // 调用存储清理函数，专门处理AI诊断大数据包
          clearStorageRecursive();

          // 静默忽略此错误，不显示错误提示
          console.log('存储清理完成，忽略存储限制错误');
          resolve(null); // 返回空结果而不是拒绝
          return;
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

// 清理存储空间的函数
const clearStorage = () => {
  // 清理临时文件
  wx.getSavedFileList({
    success: (res) => {
      const fileList = res.fileList;
      if (fileList && fileList.length > 0) {
        console.log(`发现 ${fileList.length} 个保存的文件，开始清理...`);

        fileList.forEach((file) => {
          wx.removeSavedFile({
            filePath: file.filePath,
            success: () => {
              console.log(`成功删除文件: ${file.filePath}`);
            },
            fail: (err) => {
              console.error(`删除文件失败: ${file.filePath}`, err);
            }
          });
        });
      }

      // 清理本地存储
      wx.clearStorage({
        success: () => {
          console.log('本地存储清理完成');
        },
        fail: (err) => {
          console.error('本地存储清理失败', err);
        }
      });
    },
    fail: (err) => {
      console.error('获取保存文件列表失败', err);
    }
  });
};

// 递归清理存储空间的函数，专门用于AI诊断大数据包
const clearStorageRecursive = () => {
  // 递归清理保存的文件
  const cleanFilesRecursively = (index = 0) => {
    wx.getSavedFileList({
      success: (res) => {
        const fileList = res.fileList;
        if (fileList && fileList.length > index) {
          // 删除当前索引的文件
          wx.removeSavedFile({
            filePath: fileList[index].filePath,
            success: () => {
              console.log(`成功删除文件: ${fileList[index].filePath}`);
              // 递归处理下一个文件
              cleanFilesRecursively(index + 1);
            },
            fail: (err) => {
              console.error(`删除文件失败: ${fileList[index].filePath}`, err);
              // 即使失败也继续处理下一个文件
              cleanFilesRecursively(index + 1);
            }
          });
        } else {
          // 所有文件都已处理完毕，清理本地存储
          wx.clearStorage({
            success: () => {
              console.log('本地存储清理完成');
            },
            fail: (err) => {
              console.error('本地存储清理失败', err);
            }
          });
        }
      },
      fail: (err) => {
        console.error('获取保存文件列表失败', err);
      }
    });
  };

  // 开始递归清理
  cleanFilesRecursively();
};

module.exports = {
  request,
  get,
  post,
  put,
  delete: del, // 避免与 JavaScript 关键字冲突
  ENV_CONFIG,
  clearStorage,
  clearStorageRecursive
};