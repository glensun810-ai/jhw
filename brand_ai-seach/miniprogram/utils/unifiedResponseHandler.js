/**
 * 统一响应处理器 - P0 架构级修复
 * 
 * 所有 API 响应必须经过此层处理，确保：
 * 1. 统一的解包逻辑
 * 2. 空数据自动重试
 * 3. 友好的错误提示
 * 4. 完整的审计日志
 * 
 * 架构设计：
 * ┌────────────────────────────────────────────┐
 * │  Layer 5: 统一响应处理器                    │
 * │  - 解包 {success, data} 格式                │
 * │  - 空数据拦截                              │
 * │  - 自动重试                                │
 * └────────────────────────────────────────────┘
 * 
 * 使用示例:
 * const { UnifiedResponseHandler } = require('../utils/unifiedResponseHandler');
 * 
 * // 基本用法
 * const report = await UnifiedResponseHandler.handleResponse(res, 'getReport');
 * 
 * // 带重试
 * const report = await UnifiedResponseHandler.handleWithRetry(
 *   () => wx.request({...}),
 *   'getReport'
 * );
 * 
 * @author: 系统架构组
 * @date: 2026-03-18
 * @version: 1.0.0
 */

// 配置
const CONFIG = {
  // 最大重试次数
  MAX_RETRY: 2,
  // 重试间隔（毫秒）
  RETRY_DELAY: 500,
  // 是否启用详细日志
  ENABLE_VERBOSE_LOG: true
};

// 可重试的错误类型
const RETRYABLE_ERROR_PATTERNS = [
  '网络',
  'timeout',
  '超时',
  '为空',
  'fail',
  'NETWORK_ERROR',
  'TIMEOUT',
  'EMPTY_RESPONSE'
];

/**
 * 统一响应处理器类
 */
class UnifiedResponseHandler {
  /**
   * 处理 API 响应
   * @param {Object} res - wx.request 响应
   * @param {string} context - 调用上下文（用于日志）
   * @returns {Promise<any>} 解包后的数据
   * @throws {Error} 当响应无效或数据为空时抛出
   */
  static async handleResponse(res, context = 'API') {
    this._log(context, '收到响应', {
      hasRes: !!res,
      statusCode: res?.statusCode,
      hasData: !!res?.data,
      dataType: typeof res?.data,
      errMsg: res?.errMsg
    });

    // 【防御 1】检查 res 是否存在
    if (!res) {
      this._error(context, 'res 为空');
      throw this._createError('NETWORK_ERROR', '网络请求返回为空');
    }

    // 【防御 2】检查网络错误
    const errMsg = res.errMsg || '';
    if (errMsg.includes('fail') || errMsg.includes('timeout')) {
      this._error(context, `网络错误：${errMsg}`);
      throw this._createError('NETWORK_ERROR', '网络请求失败：' + errMsg);
    }

    // 【防御 3】检查 HTTP 状态码
    const statusCode = res.statusCode;
    if (statusCode !== undefined && statusCode !== 200 && statusCode !== 207) {
      this._error(context, `HTTP 错误：${statusCode}`);
      const errorData = res.data;
      
      // 尝试从错误响应中提取消息
      let errorMsg = `HTTP 错误：${statusCode}`;
      if (errorData) {
        errorMsg = errorData?.error?.message || 
                   errorData?.error_message || 
                   errorData?.message || 
                   errorMsg;
      }
      
      throw this._createError('HTTP_ERROR', errorMsg, { statusCode });
    }

    // 【防御 4】检查响应体
    const responseData = res.data;
    if (!responseData) {
      this._error(context, '响应体为空');
      throw this._createError('EMPTY_RESPONSE', '服务器返回数据为空');
    }

    // 【防御 5】处理统一响应格式 {success, data}
    if (responseData.success !== undefined) {
      return this._handleStandardizedResponse(responseData, context);
    }

    // 【兼容】旧格式：直接返回数据
    this._log(context, '使用旧格式响应');
    return responseData;
  }

  /**
   * 处理标准化响应格式
   * @private
   */
  static _handleStandardizedResponse(responseData, context) {
    this._log(context, '检测到标准化响应格式');

    // 明确的成功/失败标志
    if (responseData.success === false) {
      const error = responseData.error || {};
      const errorMsg = error.message || 
                       error.error_message || 
                       error.message || 
                       '操作失败';
      
      this._error(context, `业务错误：${errorMsg}`, {
        errorCode: error.code,
        errorDetail: error.detail
      });

      throw this._createError(
        error.code || 'BUSINESS_ERROR',
        errorMsg,
        { detail: error.detail }
      );
    }

    // success=true，检查 data
    if (responseData.data) {
      this._log(context, '✅ 解包成功');
      
      // 部分成功标志
      if (responseData.partial === true) {
        this._warn(context, '部分成功响应', {
          warnings: responseData.warnings
        });
      }
      
      return responseData.data;
    }

    // success=true 但 data 为空
    this._warn(context, 'success=true 但 data 为空');
    throw this._createError('EMPTY_DATA', '服务器返回数据为空');
  }

  /**
   * 带重试的响应处理
   * @param {Function} requestFn - 请求函数（返回 Promise）
   * @param {string} context - 调用上下文
   * @param {number} retryCount - 当前重试次数（内部使用）
   * @returns {Promise<any>} 解包后的数据
   */
  static async handleWithRetry(requestFn, context = 'API', retryCount = 0) {
    try {
      const res = await requestFn();
      return await this.handleResponse(res, context);
      
    } catch (error) {
      // 判断是否可重试
      const isRetryable = this._isRetryableError(error);
      
      if (isRetryable && retryCount < CONFIG.MAX_RETRY) {
        const delay = CONFIG.RETRY_DELAY * Math.pow(2, retryCount);
        this._warn(context, `第${retryCount + 1}次重试，${delay}ms 后...`, {
          error: error.message
        });
        
        await this._sleep(delay);
        return await this.handleWithRetry(requestFn, context, retryCount + 1);
      }
      
      // 不可重试或已达到最大重试次数
      this._error(context, `请求最终失败（重试${retryCount}次）`, {
        error: error.message,
        isRetryable
      });
      
      throw error;
    }
  }

  /**
   * 判断错误是否可重试
   * @private
   */
  static _isRetryableError(error) {
    if (!error || !error.message) {
      return false;
    }
    
    const message = error.message.toUpperCase();
    return RETRYABLE_ERROR_PATTERNS.some(pattern => 
      message.includes(pattern.toUpperCase())
    );
  }

  /**
   * 创建统一的错误对象
   * @private
   */
  static _createError(code, message, extra = {}) {
    const error = new Error(message);
    error.code = code;
    error.timestamp = new Date().toISOString();
    
    if (Object.keys(extra).length > 0) {
      error.extra = extra;
    }
    
    return error;
  }

  /**
   * 延迟函数
   * @private
   */
  static _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 日志输出
   * @private
   */
  static _log(context, message, data = null) {
    if (!CONFIG.ENABLE_VERBOSE_LOG) return;
    
    console.log(`[UnifiedResponse] ${context}: ${message}`, data || '');
  }

  /**
   * 警告日志
   * @private
   */
  static _warn(context, message, data = null) {
    console.warn(`[UnifiedResponse] ${context}: ${message}`, data || '');
  }

  /**
   * 错误日志
   * @private
   */
  static _error(context, message, data = null) {
    console.error(`[UnifiedResponse] ${context}: ${message}`, data || '');
  }
}

/**
 * 简化的响应处理函数（便于快速集成）
 * @param {Object} res - wx.request 响应
 * @param {string} context - 上下文
 * @returns {Promise<any>} 解包后的数据
 */
const handleResponse = (res, context) => {
  return UnifiedResponseHandler.handleResponse(res, context);
};

/**
 * 带重试的响应处理函数
 * @param {Function} requestFn - 请求函数
 * @param {string} context - 上下文
 * @returns {Promise<any>}
 */
const handleWithRetry = (requestFn, context) => {
  return UnifiedResponseHandler.handleWithRetry(requestFn, context);
};

module.exports = {
  UnifiedResponseHandler,
  handleResponse,
  handleWithRetry,
  CONFIG
};
