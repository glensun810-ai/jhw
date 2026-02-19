/**
 * 前端日志工具模块
 *
 * 功能:
 * 1. 日志级别控制 (DEBUG/INFO/WARN/ERROR)
 * 2. 生产环境自动禁用 DEBUG 日志
 * 3. 统一的日志格式
 * 4. 可选的错误上报
 *
 * 使用示例:
 * const logger = require('../../utils/logger');
 *
 * logger.debug('调试信息', data);  // 生产环境自动禁用
 * logger.info('普通信息', data);
 * logger.warn('警告信息', data);
 * logger.error('错误信息', error); // 始终记录
 */

// 日志级别
const LOG_LEVEL = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3
};

// 环境判断：小程序原生环境不支持 __DEV__，使用 wx.getAccountInfoSync() 判断
const isDev = (function() {
  try {
    const accountInfo = wx.getAccountInfoSync();
    return accountInfo.miniProgram.envVersion === 'develop';
  } catch (e) {
    // 如果获取失败，默认为开发环境
    return true;
  }
})();

// 当前日志级别 (根据环境自动设置)
// 生产环境：只记录 ERROR
// 开发环境：记录所有级别
const CURRENT_LOG_LEVEL = isDev ? LOG_LEVEL.DEBUG : LOG_LEVEL.ERROR;

/**
 * 格式化日志消息
 */
function formatMessage(level, message, data) {
  const timestamp = new Date().toISOString();
  const levelStr = ['DEBUG', 'INFO', 'WARN', 'ERROR'][level];

  let formatted = `[${timestamp}] [${levelStr}] ${message}`;

  if (data !== undefined) {
    if (typeof data === 'object') {
      try {
        formatted += ' ' + JSON.stringify(data);
      } catch (e) {
        formatted += ' [Object]';
      }
    } else {
      formatted += ' ' + data;
    }
  }

  return formatted;
}

/**
 * 日志工具类
 */
class Logger {
  /**
   * 设置日志级别
   * @param {number} level - 日志级别
   */
  static setLevel(level) {
    if (typeof level === 'number' && level >= LOG_LEVEL.DEBUG && level <= LOG_LEVEL.ERROR) {
      CURRENT_LOG_LEVEL = level;
    }
  }

  /**
   * 获取当前日志级别
   * @returns {number} 日志级别
   */
  static getLevel() {
    return CURRENT_LOG_LEVEL;
  }

  /**
   * 调试日志 (生产环境禁用)
   * @param {string} message - 日志消息
   * @param {any} data - 附加数据
   */
  static debug(message, data) {
    if (CURRENT_LOG_LEVEL <= LOG_LEVEL.DEBUG) {
      console.debug(formatMessage(LOG_LEVEL.DEBUG, message, data));
    }
  }

  /**
   * 信息日志
   * @param {string} message - 日志消息
   * @param {any} data - 附加数据
   */
  static info(message, data) {
    if (CURRENT_LOG_LEVEL <= LOG_LEVEL.INFO) {
      console.log(formatMessage(LOG_LEVEL.INFO, message, data));
    }
  }

  /**
   * 警告日志
   * @param {string} message - 日志消息
   * @param {any} data - 附加数据
   */
  static warn(message, data) {
    if (CURRENT_LOG_LEVEL <= LOG_LEVEL.WARN) {
      console.warn(formatMessage(LOG_LEVEL.WARN, message, data));
    }
  }

  /**
   * 错误日志 (始终记录)
   * @param {string} message - 日志消息
   * @param {Error|any} error - 错误对象或数据
   */
  static error(message, error) {
    if (CURRENT_LOG_LEVEL <= LOG_LEVEL.ERROR) {
      console.error(formatMessage(LOG_LEVEL.ERROR, message));
      if (error) {
        if (error instanceof Error) {
          console.error('Error:', error.message);
          console.error('Stack:', error.stack);
        } else {
          console.error('Data:', error);
        }
      }
    }
  }

  /**
   * 上报错误到服务器 (可选)
   * @param {Error} error - 错误对象
   * @param {Object} context - 上下文信息
   */
  static reportError(error, context = {}) {
    // 生产环境才上报
    if (!isDev) {
      const app = getApp();
      const apiBaseUrl = app.globalData.apiBaseUrl || '';

      if (apiBaseUrl) {
        wx.request({
          url: `${apiBaseUrl}/api/log/error`,
          method: 'POST',
          data: {
            error: error.message,
            stack: error.stack,
            context: context,
            timestamp: Date.now(),
            userAgent: wx.getSystemInfoSync().model
          },
          timeout: 5000,
          fail: (reportError) => {
            // 上报失败不重复上报，避免死循环
            console.error('Error report failed:', reportError);
          }
        });
      }
    }
  }
}

module.exports = Logger;
