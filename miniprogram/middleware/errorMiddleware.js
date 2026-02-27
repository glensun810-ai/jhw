/**
 * 全局错误处理中间件
 * 
 * 提供统一的 API 请求错误处理
 */

import { handleApiError, logError, isRetryableError } from '../utils/errorHandler';
import { showErrorToast, showErrorModal } from '../utils/uiHelper';

/**
 * 错误处理配置
 */
const config = {
  // 是否自动显示错误提示
  autoShowError: true,
  // 是否自动记录错误日志
  autoLogError: true,
  // 是否启用错误上报
  enableReport: false,
  // 重试次数限制
  maxRetries: 3,
  // 重试延迟（毫秒）
  retryDelay: 1000
};

/**
 * 错误处理器
 */
class ErrorHandler {
  constructor() {
    this.errorQueue = [];
    this.isProcessing = false;
    this.listeners = [];
  }

  /**
   * 处理错误
   * @param {Object} error - 错误对象
   * @param {Object} options - 选项
   * @returns {Object} 处理后的错误信息
   */
  handle(error, options = {}) {
    const handled = handleApiError(error);
    
    // 记录错误日志
    if (config.autoLogError && options.log !== false) {
      logError(error, options.context || {});
    }
    
    // 显示错误提示
    if (config.autoShowError && options.showToast !== false) {
      if (options.modal) {
        showErrorModal(error, options);
      } else {
        showErrorToast(error, options);
      }
    }
    
    // 通知监听器
    this.notifyListeners(handled);
    
    return handled;
  }

  /**
   * 异步处理错误（支持重试）
   * @param {Function} fn - 可能出错的函数
   * @param {Object} options - 选项
   * @returns {Promise<any>}
   */
  async handleAsync(fn, options = {}) {
    let lastError;
    let retries = 0;
    const maxRetries = options.retries || config.maxRetries;
    
    while (retries <= maxRetries) {
      try {
        const result = await fn();
        return result;
      } catch (error) {
        lastError = error;
        const handled = handleApiError(error);
        
        // 记录错误
        if (config.autoLogError) {
          logError(error, options.context || {});
        }
        
        // 判断是否可重试
        if (!isRetryableError(handled) || retries >= maxRetries) {
          // 不可重试或达到最大重试次数
          if (config.autoShowError && options.showToast !== false) {
            if (options.modal) {
              const shouldRetry = await showErrorModal(error, {
                showRetry: handled.retryable
              });
              if (shouldRetry && handled.retryable) {
                retries = 0;
                continue;
              }
            } else {
              showErrorToast(error, options);
            }
          }
          break;
        }
        
        // 等待后重试
        retries++;
        const delay = options.retryDelay || config.retryDelay;
        await new Promise(resolve => setTimeout(resolve, delay * retries));
      }
    }
    
    // 所有重试失败
    throw lastError;
  }

  /**
   * 添加错误监听器
   * @param {Function} listener - 监听函数
   */
  addListener(listener) {
    if (typeof listener === 'function' && !this.listeners.includes(listener)) {
      this.listeners.push(listener);
    }
  }

  /**
   * 移除错误监听器
   * @param {Function} listener - 监听函数
   */
  removeListener(listener) {
    const index = this.listeners.indexOf(listener);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  /**
   * 通知所有监听器
   * @param {Object} error - 错误信息
   */
  notifyListeners(error) {
    this.listeners.forEach(listener => {
      try {
        listener(error);
      } catch (e) {
        console.error('Error listener failed:', e);
      }
    });
  }

  /**
   * 清除所有监听器
   */
  clearListeners() {
    this.listeners = [];
  }

  /**
   * 更新配置
   * @param {Object} newConfig - 新配置
   */
  updateConfig(newConfig) {
    Object.assign(config, newConfig);
  }

  /**
   * 获取当前配置
   * @returns {Object} 当前配置
   */
  getConfig() {
    return { ...config };
  }
}

// 导出单例
export const errorHandler = new ErrorHandler();

/**
 * 默认导出处理函数
 */
export default function handle(error, options) {
  return errorHandler.handle(error, options);
}
