/**
 * 重试策略工具
 * 
 * 提供各种重试算法：
 * 1. 固定间隔
 * 2. 线性递增
 * 3. 指数退避
 * 4. 带抖动的指数退避
 */

export const RetryStrategy = {
  /**
   * 固定间隔
   * @param {number} attempt - 当前重试次数
   * @param {number} baseDelay - 基础延迟（毫秒）
   * @returns {number} 延迟时间（毫秒）
   */
  fixed: (attempt, baseDelay = 2000) => {
    return baseDelay;
  },

  /**
   * 线性递增
   * @param {number} attempt - 当前重试次数
   * @param {number} baseDelay - 基础延迟（毫秒）
   * @param {number} increment - 每次递增的延迟（毫秒）
   * @returns {number} 延迟时间（毫秒）
   */
  linear: (attempt, baseDelay = 2000, increment = 1000) => {
    return baseDelay + (attempt * increment);
  },

  /**
   * 指数退避
   * @param {number} attempt - 当前重试次数
   * @param {number} baseDelay - 基础延迟（毫秒）
   * @param {number} maxDelay - 最大延迟（毫秒）
   * @returns {number} 延迟时间（毫秒）
   */
  exponential: (attempt, baseDelay = 2000, maxDelay = 30000) => {
    const delay = baseDelay * Math.pow(2, attempt);
    return Math.min(delay, maxDelay);
  },

  /**
   * 带抖动的指数退避（推荐）
   * @param {number} attempt - 当前重试次数
   * @param {number} baseDelay - 基础延迟（毫秒）
   * @param {number} maxDelay - 最大延迟（毫秒）
   * @returns {number} 延迟时间（毫秒）
   */
  exponentialWithJitter: (attempt, baseDelay = 2000, maxDelay = 30000) => {
    const exponentialDelay = baseDelay * Math.pow(2, attempt);
    const cappedDelay = Math.min(exponentialDelay, maxDelay);
    
    // 添加 ±10% 的随机抖动
    const jitter = cappedDelay * 0.1 * (Math.random() * 2 - 1);
    return Math.max(0, Math.round(cappedDelay + jitter));
  },

  /**
   * 根据状态动态调整
   * @param {number} attempt - 当前重试次数
   * @param {number} baseDelay - 基础延迟（毫秒）
   * @param {number} maxDelay - 最大延迟（毫秒）
   * @param {number} progress - 当前进度百分比
   * @returns {number} 延迟时间（毫秒）
   */
  adaptive: (attempt, baseDelay = 2000, maxDelay = 30000, progress) => {
    // 根据进度调整基础延迟
    let adjustedBase = baseDelay;
    if (progress < 30) {
      adjustedBase = baseDelay * 1.5;  // 进度慢，放慢轮询
    } else if (progress > 80) {
      adjustedBase = baseDelay * 0.8;  // 快完成了，加快轮询
    }

    const delay = adjustedBase * Math.pow(1.5, attempt);
    return Math.min(delay, maxDelay);
  },

  /**
   * 计算下一次轮询时间
   * @param {number} attempt - 当前重试次数
   * @param {Object} lastStatus - 最后一次状态
   * @param {Object} config - 配置
   * @returns {number} 延迟时间（毫秒）
   */
  calculateNextPoll: (attempt, lastStatus, config = {}) => {
    const {
      strategy = 'exponentialWithJitter',
      baseDelay = 2000,
      maxDelay = 30000
    } = config;

    const strategyFn = RetryStrategy[strategy] || RetryStrategy.exponentialWithJitter;
    
    if (strategy === 'adaptive') {
      return strategyFn(attempt, baseDelay, maxDelay, lastStatus?.progress);
    }

    return strategyFn(attempt, baseDelay, maxDelay);
  },

  /**
   * 判断是否应该重试
   * @param {number} attempt - 当前重试次数
   * @param {number} maxRetries - 最大重试次数
   * @param {Object} error - 错误对象
   * @returns {boolean} 是否应该重试
   */
  shouldRetry: (attempt, maxRetries, error) => {
    if (attempt >= maxRetries) return false;

    // 某些错误不应该重试
    const nonRetryableErrors = [
      'TaskNotFound',
      'InvalidExecutionId',
      'Unauthorized'
    ];

    if (error?.code && nonRetryableErrors.includes(error.code)) {
      return false;
    }

    return true;
  }
};
