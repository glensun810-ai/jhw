/**
 * 错误处理中间件
 *
 * 提供全局错误拦截和处理能力
 */

const { handleApiError, showError, logError } = require('../utils/errorHandler');

// 默认配置
const config = {
  // 是否启用错误上报
  enableReporting: false,
  // 是否显示错误提示
  showToast: true,
  // 是否记录日志
  enableLogging: true,
  // 错误上报地址
  reportUrl: '',
  // 忽略的错误列表
  ignoreErrors: []
};

/**
 * 错误处理类
 */
class ErrorHandler {
  /**
   * 构造函数
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.config = { ...config, ...options };
  }

  /**
   * 处理错误
   * @param {Object} error - 错误对象
   * @param {Object} options - 选项
   * @returns {Object} 处理结果
   */
  handle(error, options = {}) {
    const {
      showToast = this.config.showToast,
      showLogging = this.config.enableLogging,
      context = {}
    } = options;

    // 处理错误
    const handled = handleApiError(error);

    // 记录日志
    if (showLogging) {
      logError(error, context);
    }

    // 显示提示
    if (showToast) {
      this._showErrorToast(handled);
    }

    // 上报错误
    if (this.config.enableReporting) {
      this._reportError(handled, context);
    }

    return handled;
  }

  /**
   * 显示错误提示
   * @private
   * @param {Object} handled - 处理后的错误
   */
  _showErrorToast(handled) {
    wx.showToast({
      title: handled.message,
      icon: 'none',
      duration: 3000,
      mask: true
    });
  }

  /**
   * 上报错误
   * @private
   * @param {Object} handled - 处理后的错误
   * @param {Object} context - 上下文
   */
  _reportError(handled, context) {
    const errorData = {
      ...handled,
      context,
      timestamp: new Date().toISOString()
    };

    // 发送到错误上报服务
    wx.request({
      url: this.config.reportUrl,
      method: 'POST',
      data: errorData
    }).catch(() => {
      // 上报失败，忽略
    });
  }

  /**
   * 全局错误处理（拦截未捕获的错误）
   */
  installGlobalHandler() {
    const self = this;

    // 微信小程序全局错误处理
    wx.onError = function(error) {
      self.handle(error, {
        context: { source: 'global' }
      });
    };

    // Promise 未捕获错误
    const originalPromise = Promise;
    Promise = function(executor) {
      return new originalPromise((resolve, reject) => {
        executor(resolve, (error) => {
          self.handle(error, {
            context: { source: 'promise' }
          });
          reject(error);
        });
      });
    };

    console.log('[ErrorHandler] Global error handler installed');
  }

  /**
   * 更新配置
   * @param {Object} newConfig - 新配置
   */
  updateConfig(newConfig) {
    Object.assign(this.config, newConfig);
  }

  /**
   * 获取当前配置
   * @returns {Object} 当前配置
   */
  getConfig() {
    return { ...this.config };
  }
}

// 导出单例（CommonJS 语法，兼容微信小程序）
const errorHandlerInstance = new ErrorHandler();
module.exports = {
  errorHandler: errorHandlerInstance,
  default: function handle(error, options) {
    return errorHandlerInstance.handle(error, options);
  }
};
