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
  SERVER_ERROR: 'SERVER_ERROR'
};

/**
 * 错误消息映射
 */
export const ErrorMessages = {
  [ErrorCodes.NETWORK_ERROR]: '网络连接失败，请检查网络设置',
  [ErrorCodes.TIMEOUT]: '请求超时，请稍后重试',
  [ErrorCodes.TASK_NOT_FOUND]: '诊断任务不存在',
  [ErrorCodes.UNAUTHORIZED]: '请重新登录',
  [ErrorCodes.INTERNAL_ERROR]: '系统错误，请稍后重试',
  [ErrorCodes.INVALID_EXECUTION_ID]: '无效的任务 ID',
  [ErrorCodes.SERVER_ERROR]: '服务器错误，请稍后重试'
};

/**
 * 处理 API 错误
 * @param {Object} error - 错误对象
 * @returns {Object} 处理后的错误信息
 */
export function handleApiError(error) {
  console.error('API Error:', error);

  // 提取错误信息
  const errorCode = error.code || error.errorCode;
  const errorMessage = error.message || error.errMsg;

  // 根据错误类型返回用户友好的信息
  if (errorCode) {
    return {
      code: errorCode,
      message: ErrorMessages[errorCode] || errorMessage,
      raw: error
    };
  }

  // 网络错误
  if (error.errMsg && error.errMsg.includes('timeout')) {
    return {
      code: ErrorCodes.TIMEOUT,
      message: ErrorMessages[ErrorCodes.TIMEOUT],
      raw: error
    };
  }

  if (error.errMsg && error.errMsg.includes('fail')) {
    return {
      code: ErrorCodes.NETWORK_ERROR,
      message: ErrorMessages[ErrorCodes.NETWORK_ERROR],
      raw: error
    };
  }

  // 默认错误
  return {
    code: ErrorCodes.INTERNAL_ERROR,
    message: errorMessage || ErrorMessages[ErrorCodes.INTERNAL_ERROR],
    raw: error
  };
}

/**
 * 显示错误提示
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
    message: error.message,
    stack: error.stack,
    context: context
  };

  // 上报到日志服务
  wx.cloud.callFunction({
    name: 'logError',
    data: errorInfo
  }).catch(logError => {
    // 日志上报失败也要记录到控制台
    console.error('Failed to log error:', logError);
  });

  console.error('Error logged:', errorInfo);
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
    ErrorCodes.INVALID_EXECUTION_ID
  ];

  if (error.code && nonRetryableCodes.includes(error.code)) {
    return false;
  }

  // 网络错误和超时通常可重试
  if (error.code === ErrorCodes.NETWORK_ERROR || error.code === ErrorCodes.TIMEOUT) {
    return true;
  }

  // 默认可以重试
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
