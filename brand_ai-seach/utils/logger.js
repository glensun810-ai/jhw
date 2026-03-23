/**
 * 日志级别配置
 * 
 * BUG-009 修复：添加日志级别控制，生产环境可关闭 DEBUG 日志
 */

// 日志级别枚举
const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

// 当前日志级别（可通过环境变量或配置修改）
// 生产环境建议设置为 WARN 或 ERROR
let currentLogLevel = LogLevel.INFO;

/**
 * 设置日志级别
 * @param {number} level - 日志级别
 */
function setLogLevel(level) {
  currentLogLevel = level;
  console.log(`[日志配置] 日志级别已设置为：${level}`);
}

/**
 * 获取当前日志级别
 * @returns {number} 日志级别
 */
function getLogLevel() {
  return currentLogLevel;
}

/**
 * DEBUG 级别日志
 * 只在 DEBUG 级别下输出
 */
function debug(...args) {
  if (currentLogLevel <= LogLevel.DEBUG) {
    console.log('[DEBUG]', ...args);
  }
}

/**
 * INFO 级别日志
 * 在 INFO 及以上级别输出
 */
function info(...args) {
  if (currentLogLevel <= LogLevel.INFO) {
    console.log('[INFO]', ...args);
  }
}

/**
 * WARN 级别日志
 * 在 WARN 及以上级别输出
 */
function warn(...args) {
  if (currentLogLevel <= LogLevel.WARN) {
    console.warn('[WARN]', ...args);
  }
}

/**
 * ERROR 级别日志
 * 在 ERROR 及以上级别输出
 */
function error(...args) {
  if (currentLogLevel <= LogLevel.ERROR) {
    console.error('[ERROR]', ...args);
  }
}

/**
 * 生产环境配置（关闭 DEBUG 日志）
 */
function setProductionMode() {
  setLogLevel(LogLevel.WARN);
  console.log('[日志配置] 已切换到生产环境模式');
}

/**
 * 开发环境配置（开启所有日志）
 */
function setDevelopmentMode() {
  setLogLevel(LogLevel.DEBUG);
  console.log('[日志配置] 已切换到开发环境模式');
}

// 自动检测环境（延迟初始化，确保 wx 对象已就绪）
function initLogLevel() {
  try {
    // 检查 wx 对象是否存在
    if (typeof wx === 'undefined' || !wx.getAccountInfoSync) {
      // 在非微信环境或 wx 未初始化时，默认开发环境
      setDevelopmentMode();
      return;
    }

    // 检查是否在微信开发者工具中
    const accountInfo = wx.getAccountInfoSync();
    const envVersion = accountInfo?.miniProgram?.envVersion || 'develop';

    if (envVersion === 'release') {
      // 正式版：只输出 WARN 和 ERROR
      setProductionMode();
    } else if (envVersion === 'trial') {
      // 体验版：输出 INFO 及以上
      setLogLevel(LogLevel.INFO);
    } else {
      // 开发版：输出所有日志
      setDevelopmentMode();
    }
  } catch (e) {
    // 默认开发环境
    setDevelopmentMode();
  }
}

// 延迟初始化：在下一个事件循环中执行，确保 wx 对象已就绪
setTimeout(function() {
  initLogLevel();
}, 0);

module.exports = {
  LogLevel,
  debug,
  info,
  warn,
  error,
  setLogLevel,
  getLogLevel,
  setProductionMode,
  setDevelopmentMode
};
