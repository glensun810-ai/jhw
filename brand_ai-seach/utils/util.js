/**
 * 前端调试日志工具
 * 统一管理前端调试信息输出
 */

// 全局调试模式开关
const GEO_DEBUG_MODE = true;

/**
 * 统一的调试日志函数
 * @param {string} tag - 日志标签
 * @param {string} message - 日志消息
 */
function debugLog(tag, message) {
  // 检查是否为开发环境
  const isDevEnvironment = checkEnvironment();
  
  if (GEO_DEBUG_MODE && isDevEnvironment) {
    const timestamp = new Date().toISOString();
    const formattedMessage = `[GEO-DEBUG][${tag}] ${message}`;
    
    // 使用 console.group 来组织日志
    console.group(`[${timestamp}] ${formattedMessage}`);
    console.trace(); // 输出调用栈以便追踪
    console.groupEnd();
  }
}

/**
 * 检查当前运行环境
 * @returns {boolean} 是否为开发环境
 */
function checkEnvironment() {
  // 小程序环境中可以通过 wx.getAccountInfoSync() 来判断环境
  if (typeof wx !== 'undefined' && wx.getAccountInfoSync) {
    try {
      const accountInfo = wx.getAccountInfoSync();
      // develop: 开发版, trial: 体验版, formal: 正式版
      const envVersion = accountInfo.miniProgram.envVersion;
      return envVersion !== 'formal'; // 非正式版都视为开发环境
    } catch (e) {
      // 如果无法获取环境信息，默认认为是开发环境
      return true;
    }
  }
  
  // 如果不是小程序环境，可以根据其他方式判断
  return process.env.NODE_ENV !== 'production';
}

/**
 * AI I/O 相关日志
 * @param {string} message - 日志消息
 */
function aiIoLog(message) {
  debugLog('AI_IO', message);
}

/**
 * 状态流转相关日志
 * @param {string} message - 日志消息
 */
function statusFlowLog(message) {
  debugLog('STATUS_FLOW', message);
}

/**
 * 异常相关日志
 * @param {string} message - 日志消息
 */
function exceptionLog(message) {
  debugLog('EXCEPTION', message);
}

module.exports = {
  debugLog,
  aiIoLog,
  statusFlowLog,
  exceptionLog,
  GEO_DEBUG_MODE
};