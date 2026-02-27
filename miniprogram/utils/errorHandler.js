/**
 * 错误处理工具
 *
 * 提供统一的错误处理、日志记录和用户友好的错误提示
 */

/**
 * 错误代码枚举
 */
export const ErrorCodes = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  TASK_NOT_FOUND: 'TASK_NOT_FOUND',
  UNAUTHORIZED: 'UNAUTHORIZED',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  INVALID_EXECUTION_ID: 'INVALID_EXECUTION_ID',
  SERVER_ERROR: 'SERVER_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  FORBIDDEN: 'FORBIDDEN',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  RATE_LIMIT: 'RATE_LIMIT'
};

/**
 * 错误类型映射
 */
export const ErrorTypes = {
  [ErrorCodes.NETWORK_ERROR]: 'network',
  [ErrorCodes.TIMEOUT]: 'timeout',
  [ErrorCodes.TASK_NOT_FOUND]: 'business',
  [ErrorCodes.UNAUTHORIZED]: 'auth',
  [ErrorCodes.INTERNAL_ERROR]: 'server',
  [ErrorCodes.INVALID_EXECUTION_ID]: 'business',
  [ErrorCodes.SERVER_ERROR]: 'server',
  [ErrorCodes.NOT_FOUND]: 'business',
  [ErrorCodes.FORBIDDEN]: 'auth',
  [ErrorCodes.VALIDATION_ERROR]: 'business',
  [ErrorCodes.RATE_LIMIT]: 'network'
};

/**
 * 错误消息映射（用户友好的默认消息）
 */
export const ErrorMessages = {
  [ErrorCodes.NETWORK_ERROR]: '网络连接失败，请检查网络设置',
  [ErrorCodes.TIMEOUT]: '请求超时，请稍后重试',
  [ErrorCodes.TASK_NOT_FOUND]: '诊断任务不存在',
  [ErrorCodes.UNAUTHORIZED]: '请先登录',
  [ErrorCodes.INTERNAL_ERROR]: '系统错误，请稍后重试',
  [ErrorCodes.INVALID_EXECUTION_ID]: '无效的任务 ID',
  [ErrorCodes.SERVER_ERROR]: '服务器错误，请稍后重试',
  [ErrorCodes.NOT_FOUND]: '请求的资源不存在',
  [ErrorCodes.FORBIDDEN]: '无权访问此资源',
  [ErrorCodes.VALIDATION_ERROR]: '输入数据无效',
  [ErrorCodes.RATE_LIMIT]: '请求过于频繁，请稍后重试'
};

/**
 * 错误标题映射
 */
export const ErrorTitles = {
  [ErrorCodes.NETWORK_ERROR]: '网络连接失败',
  [ErrorCodes.TIMEOUT]: '请求超时',
  [ErrorCodes.TASK_NOT_FOUND]: '任务不存在',
  [ErrorCodes.UNAUTHORIZED]: '需要登录',
  [ErrorCodes.INTERNAL_ERROR]: '系统错误',
  [ErrorCodes.INVALID_EXECUTION_ID]: '无效任务',
  [ErrorCodes.SERVER_ERROR]: '服务器错误',
  [ErrorCodes.NOT_FOUND]: '资源不存在',
  [ErrorCodes.FORBIDDEN]: '禁止访问',
  [ErrorCodes.VALIDATION_ERROR]: '数据错误',
  [ErrorCodes.RATE_LIMIT]: '请求频繁'
};

/**
 * 处理 API 错误
 * @param {Object} error - 错误对象
 * @returns {Object} 处理后的错误信息
 */
export function handleApiError(error) {
  console.error('API Error:', error);

  // 提取错误信息
  const errorCode = error?.code || error?.errorCode;
  const errorMessage = error?.message || error?.errMsg;
  const statusCode = error?.statusCode;

  // 根据错误类型返回用户友好的信息
  if (errorCode && ErrorCodes[errorCode]) {
    return {
      code: errorCode,
      type: ErrorTypes[errorCode] || 'default',
      title: ErrorTitles[errorCode] || '发生错误',
      message: ErrorMessages[errorCode] || errorMessage,
      raw: error,
      retryable: isRetryableError({ code: errorCode })
    };
  }

  // 根据 HTTP 状态码判断
  if (statusCode) {
    if (statusCode >= 500) {
      return {
        code: ErrorCodes.SERVER_ERROR,
        type: 'server',
        title: '服务器错误',
        message: ErrorMessages[ErrorCodes.SERVER_ERROR],
        raw: error,
        retryable: true
      };
    }
    if (statusCode === 401) {
      return {
        code: ErrorCodes.UNAUTHORIZED,
        type: 'auth',
        title: '需要登录',
        message: ErrorMessages[ErrorCodes.UNAUTHORIZED],
        raw: error,
        retryable: false
      };
    }
    if (statusCode === 403) {
      return {
        code: ErrorCodes.FORBIDDEN,
        type: 'auth',
        title: '禁止访问',
        message: ErrorMessages[ErrorCodes.FORBIDDEN],
        raw: error,
        retryable: false
      };
    }
    if (statusCode === 404) {
      return {
        code: ErrorCodes.NOT_FOUND,
        type: 'business',
        title: '资源不存在',
        message: ErrorMessages[ErrorCodes.NOT_FOUND],
        raw: error,
        retryable: false
      };
    }
    if (statusCode === 429) {
      return {
        code: ErrorCodes.RATE_LIMIT,
        type: 'network',
        title: '请求频繁',
        message: ErrorMessages[ErrorCodes.RATE_LIMIT],
        raw: error,
        retryable: true
      };
    }
  }

  // 网络错误
  if (errorMessage) {
    if (errorMessage.includes('timeout')) {
      return {
        code: ErrorCodes.TIMEOUT,
        type: 'timeout',
        title: '请求超时',
        message: ErrorMessages[ErrorCodes.TIMEOUT],
        raw: error,
        retryable: true
      };
    }
    if (errorMessage.includes('fail') || errorMessage.includes('网络')) {
      return {
        code: ErrorCodes.NETWORK_ERROR,
        type: 'network',
        title: '网络连接失败',
        message: ErrorMessages[ErrorCodes.NETWORK_ERROR],
        raw: error,
        retryable: true
      };
    }
  }

  // 默认错误
  return {
    code: ErrorCodes.INTERNAL_ERROR,
    type: 'default',
    title: '发生错误',
    message: errorMessage || ErrorMessages[ErrorCodes.INTERNAL_ERROR],
    raw: error,
    retryable: true
  };
}

/**
 * 显示错误提示（使用原生 wx.showToast）
 * @param {Object} error - 错误对象
 * @param {Object} options - 选项
 * @returns {Object} 处理后的错误信息
 */
export function showError(error, options = {}) {
  const handled = handleApiError(error);

  wx.showToast({
    title: handled.message,
    icon: 'none',
    duration: options.duration || 3000,
    mask: options.mask || true,
    ...options
  });

  return handled;
}

/**
 * 记录错误日志
 * @param {Object} error - 错误对象
 * @param {Object} context - 上下文信息
 */
export function logError(error, context = {}) {
  const errorInfo = {
    timestamp: new Date().toISOString(),
    message: error?.message || 'Unknown error',
    stack: error?.stack,
    code: error?.code || error?.errorCode,
    context: {
      page: context.page || getCurrentPageName(),
      action: context.action || 'unknown',
      userId: context.userId || getApp()?.globalData?.openid,
      deviceId: context.deviceId || getApp()?.globalData?.deviceId,
      ...context
    }
  };

  // 上报到日志服务（如果有）
  try {
    wx.cloud.callFunction({
      name: 'logError',
      data: errorInfo
    }).catch(logError => {
      console.error('Failed to log error:', logError);
    });
  } catch (e) {
    // 云函数不可用时，只记录到控制台
  }

  console.error('Error logged:', errorInfo);
  
  // 保存错误到本地（用于问题排查）
  saveErrorToLocal(errorInfo);
}

/**
 * 保存错误到本地存储
 * @param {Object} errorInfo - 错误信息
 */
export function saveErrorToLocal(errorInfo) {
  try {
    const key = 'recent_errors';
    const errors = wx.getStorageSync(key) || [];
    errors.unshift(errorInfo);
    
    // 只保留最近 50 条错误
    if (errors.length > 50) {
      errors.splice(50);
    }
    
    wx.setStorageSync(key, errors);
  } catch (e) {
    console.error('Failed to save error to local:', e);
  }
}

/**
 * 获取当前页面名称
 * @returns {string} 页面名称
 */
export function getCurrentPageName() {
  const pages = getCurrentPages();
  if (pages.length > 0) {
    const currentPage = pages[pages.length - 1];
    return currentPage.route || currentPage.__route__ || 'unknown';
  }
  return 'unknown';
}

/**
 * 判断错误是否可重试
 * @param {Object} error - 错误对象
 * @returns {boolean} 是否可重试
 */
export function isRetryableError(error) {
  if (!error) return false;

  const nonRetryableCodes = [
    ErrorCodes.TASK_NOT_FOUND,
    ErrorCodes.UNAUTHORIZED,
    ErrorCodes.INVALID_EXECUTION_ID,
    ErrorCodes.FORBIDDEN,
    ErrorCodes.NOT_FOUND,
    ErrorCodes.VALIDATION_ERROR
  ];

  if (error.code && nonRetryableCodes.includes(error.code)) {
    return false;
  }

  return true;
}

/**
 * 从错误中提取有用信息
 * @param {Object} error - 错误对象
 * @returns {string} 错误描述
 */
export function getErrorDetail(error) {
  if (!error) return '未知错误';

  if (error.message) {
    return error.message;
  }

  if (error.errMsg) {
    return error.errMsg;
  }

  if (error.code) {
    return ErrorMessages[error.code] || `错误代码：${error.code}`;
  }

  return '发生未知错误，请稍后重试';
}

/**
 * 获取友好的错误提示消息
 * @param {Object} error - 错误对象
 * @param {boolean} includeDetail - 是否包含详情
 * @returns {string} 友好的错误消息
 */
export function getFriendlyMessage(error, includeDetail = false) {
  const handled = handleApiError(error);
  let message = handled.message;
  
  if (includeDetail && handled.raw?.detail) {
    message += ' (' + handled.raw.detail + ')';
  }
  
  return message;
}

/**
 * 批量处理错误（用于 Promise.all 等）
 * @param {Array} errors - 错误数组
 * @returns {Array} 处理后的错误数组
 */
export function handleBatchErrors(errors) {
  return errors.map(error => handleApiError(error));
}

/**
 * 创建错误对象
 * @param {string} code - 错误代码
 * @param {string} message - 错误消息
 * @param {Object} detail - 详细信息
 * @returns {Object} 错误对象
 */
export function createError(code, message, detail = {}) {
  return {
    code,
    message,
    detail,
    timestamp: new Date().toISOString()
  };
}
