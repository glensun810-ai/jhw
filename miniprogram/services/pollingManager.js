/**
 * 轮询管理器
 * 
 * 职责：
 * 1. 管理诊断任务的状态轮询
 * 2. 实现智能终止（基于 should_stop_polling）
 * 3. 指数退避重试策略
 * 4. 定时器清理防止内存泄漏
 * 
 * @author 系统架构组
 * @date 2026-02-27
 * @version 1.0.0
 */

import { RetryStrategy } from '../utils/retryStrategy';
import { isFeatureEnabled } from '../config/featureFlags';

class PollingManager {
  /**
   * 构造函数
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.baseInterval = options.baseInterval || 2000;        // 基础轮询间隔（2 秒）
    this.maxInterval = options.maxInterval || 30000;         // 最大轮询间隔（30 秒）
    this.maxRetries = options.maxRetries || 5;               // 最大重试次数
    this.timeout = options.timeout || 600000;                // 总超时时间（10 分钟）
    
    this.pollingTasks = new Map();                            // 正在轮询的任务
    this.retryCounts = new Map();                             // 重试次数记录
    this.startTimes = new Map();                               // 开始时间记录
    this.lastStatusMap = new Map();                            // 最后一次状态记录
    
    // 日志
    if (isFeatureEnabled('diagnosis.debug.enableLogging')) {
      console.log('[PollingManager] Initialized with config:', {
        baseInterval: this.baseInterval,
        maxInterval: this.maxInterval,
        maxRetries: this.maxRetries,
        timeout: this.timeout
      });
    }
  }

  /**
   * 开始轮询诊断任务
   * @param {string} executionId - 任务执行 ID
   * @param {Object} callbacks - 回调函数
   * @param {Function} callbacks.onStatus - 状态更新回调
   * @param {Function} callbacks.onComplete - 完成回调
   * @param {Function} callbacks.onError - 错误回调
   * @param {Function} callbacks.onTimeout - 超时回调
   * @returns {string} 任务 ID（用于取消）
   */
  startPolling(executionId, callbacks) {
    // 如果已存在相同任务，先取消旧的
    if (this.pollingTasks.has(executionId)) {
      console.warn(`[PollingManager] Task ${executionId} already polling, canceling old task`);
      this.stopPolling(executionId);
    }

    // 记录开始时间
    this.startTimes.set(executionId, Date.now());
    
    // 初始化重试次数
    this.retryCounts.set(executionId, 0);

    // 创建轮询任务
    const task = {
      executionId,
      callbacks,
      timerId: null,
      isActive: true,
      attempt: 0
    };

    // 立即执行第一次轮询
    this._poll(executionId);

    // 存储任务
    this.pollingTasks.set(executionId, task);

    console.log(`[PollingManager] Started polling for task: ${executionId}`);
    return executionId;
  }

  /**
   * 停止轮询任务
   * @param {string} executionId 
   */
  stopPolling(executionId) {
    const task = this.pollingTasks.get(executionId);
    if (task && task.timerId) {
      clearTimeout(task.timerId);
    }
    
    this.pollingTasks.delete(executionId);
    this.retryCounts.delete(executionId);
    this.startTimes.delete(executionId);
    this.lastStatusMap.delete(executionId);
    
    console.log(`[PollingManager] Stopped polling for task: ${executionId}`);
  }

  /**
   * 停止所有轮询任务
   */
  stopAllPolling() {
    const taskIds = Array.from(this.pollingTasks.keys());
    taskIds.forEach((executionId) => {
      this.stopPolling(executionId);
    });
    console.log(`[PollingManager] Stopped all ${taskIds.length} polling tasks`);
  }

  /**
   * 暂停轮询（保留任务状态）
   * @param {string} executionId 
   */
  pausePolling(executionId) {
    const task = this.pollingTasks.get(executionId);
    if (task && task.timerId) {
      clearTimeout(task.timerId);
      task.timerId = null;
      task.isPaused = true;
      console.log(`[PollingManager] Paused polling for task: ${executionId}`);
    }
  }

  /**
   * 恢复轮询
   * @param {string} executionId 
   */
  resumePolling(executionId) {
    const task = this.pollingTasks.get(executionId);
    if (task && task.isPaused) {
      task.isPaused = false;
      this._poll(executionId);
      console.log(`[PollingManager] Resumed polling for task: ${executionId}`);
    }
  }

  /**
   * 执行一次轮询
   * @private
   * @param {string} executionId 
   */
  async _poll(executionId) {
    const task = this.pollingTasks.get(executionId);
    if (!task || !task.isActive || task.isPaused) {
      return;
    }

    // 检查是否超时
    if (this._isTimeout(executionId)) {
      this._handleTimeout(executionId);
      return;
    }

    try {
      // 调用状态接口
      const response = await wx.cloud.callFunction({
        name: 'getDiagnosisStatus',
        data: { executionId }
      });

      const statusData = response.result;

      // 保存最后一次状态
      this.lastStatusMap.set(executionId, statusData);

      // 重置重试计数（成功）
      this.retryCounts.set(executionId, 0);
      task.attempt = 0;

      // 调用状态更新回调
      if (task.callbacks.onStatus) {
        task.callbacks.onStatus(statusData);
      }

      // 判断是否需要停止轮询（关键逻辑）
      if (statusData.should_stop_polling === true) {
        console.log(`[PollingManager] Polling stopped by server flag: ${executionId}`);
        
        if (statusData.status === 'completed' || 
            statusData.status === 'partial_success') {
          // 成功完成
          if (task.callbacks.onComplete) {
            task.callbacks.onComplete(statusData);
          }
        } else {
          // 失败或超时
          if (task.callbacks.onError) {
            task.callbacks.onError({
              message: statusData.error_message || '诊断任务失败',
              status: statusData.status,
              data: statusData
            });
          }
        }
        
        this.stopPolling(executionId);
        return;
      }

      // 继续下一次轮询
      this._scheduleNextPoll(executionId);

    } catch (error) {
      console.error(`[PollingManager] Polling error for ${executionId}:`, error);
      
      // 处理轮询错误（使用指数退避）
      this._handlePollingError(executionId, error);
    }
  }

  /**
   * 安排下一次轮询
   * @private
   * @param {string} executionId 
   */
  _scheduleNextPoll(executionId) {
    const task = this.pollingTasks.get(executionId);
    if (!task || !task.isActive) return;

    // 计算下一次轮询间隔（可根据进度动态调整）
    let interval = this.baseInterval;
    
    // 如果进度较慢，适当增加间隔
    const status = this.lastStatusMap.get(executionId);
    if (status && status.progress < 30) {
      interval = Math.min(interval * 1.5, this.maxInterval);
    }

    // 使用重试策略计算间隔
    if (isFeatureEnabled('diagnosis.enableRetryStrategy')) {
      interval = RetryStrategy.calculateNextPoll(
        task.attempt || 0,
        status,
        {
          strategy: 'exponentialWithJitter',
          baseDelay: this.baseInterval,
          maxDelay: this.maxInterval
        }
      );
    }

    task.timerId = setTimeout(() => {
      this._poll(executionId);
    }, interval);

    if (isFeatureEnabled('diagnosis.debug.enableLogging')) {
      console.log(`[PollingManager] Next poll for ${executionId} in ${interval}ms`);
    }
  }

  /**
   * 处理轮询错误（指数退避）
   * @private
   * @param {string} executionId 
   * @param {Object} error 
   */
  _handlePollingError(executionId, error) {
    const task = this.pollingTasks.get(executionId);
    if (!task || !task.isActive) return;

    const retryCount = this.retryCounts.get(executionId) || 0;
    
    if (retryCount >= this.maxRetries) {
      // 超过最大重试次数
      console.error(`[PollingManager] Max retries exceeded for ${executionId}`);
      
      if (task.callbacks.onError) {
        task.callbacks.onError({
          message: '无法获取诊断状态，请检查网络后重试',
          error: error,
          retryCount: retryCount
        });
      }
      
      this.stopPolling(executionId);
      return;
    }

    // 计算退避时间（指数退避 + 随机抖动）
    const delay = RetryStrategy.exponentialWithJitter(
      retryCount,
      this.baseInterval,
      this.maxInterval
    );

    console.log(`[PollingManager] Retry ${retryCount + 1} for ${executionId} after ${delay}ms`);

    // 更新重试计数
    this.retryCounts.set(executionId, retryCount + 1);
    task.attempt = retryCount + 1;

    // 延迟后重试
    task.timerId = setTimeout(() => {
      this._poll(executionId);
    }, delay);
  }

  /**
   * 处理超时
   * @private
   * @param {string} executionId 
   */
  _handleTimeout(executionId) {
    const task = this.pollingTasks.get(executionId);
    if (!task) return;

    console.warn(`[PollingManager] Polling timeout for ${executionId}`);

    if (task.callbacks.onTimeout) {
      task.callbacks.onTimeout({
        message: '诊断任务执行时间过长，请稍后查看历史记录',
        executionId: executionId
      });
    }

    this.stopPolling(executionId);
  }

  /**
   * 检查是否超时
   * @private
   * @param {string} executionId 
   * @returns {boolean}
   */
  _isTimeout(executionId) {
    const startTime = this.startTimes.get(executionId);
    if (!startTime) return false;
    
    return (Date.now() - startTime) > this.timeout;
  }

  /**
   * 获取剩余时间（秒）
   * @param {string} executionId 
   * @returns {number}
   */
  getRemainingTime(executionId) {
    const startTime = this.startTimes.get(executionId);
    if (!startTime) return 0;
    
    const elapsed = Date.now() - startTime;
    return Math.max(0, Math.floor((this.timeout - elapsed) / 1000));
  }

  /**
   * 获取已用时间（秒）
   * @param {string} executionId 
   * @returns {number}
   */
  getElapsedTime(executionId) {
    const startTime = this.startTimes.get(executionId);
    if (!startTime) return 0;
    
    return Math.floor((Date.now() - startTime) / 1000);
  }

  /**
   * 获取活跃任务数量
   * @returns {number}
   */
  getActiveTaskCount() {
    return this.pollingTasks.size;
  }

  /**
   * 检查任务是否在轮询中
   * @param {string} executionId 
   * @returns {boolean}
   */
  isPolling(executionId) {
    return this.pollingTasks.has(executionId);
  }

  /**
   * 获取任务状态
   * @param {string} executionId 
   * @returns {Object|null}
   */
  getTaskStatus(executionId) {
    const task = this.pollingTasks.get(executionId);
    if (!task) return null;

    return {
      executionId,
      isActive: task.isActive,
      isPaused: task.isPaused,
      attempt: task.attempt,
      retryCount: this.retryCounts.get(executionId) || 0,
      elapsedTime: this.getElapsedTime(executionId),
      remainingTime: this.getRemainingTime(executionId),
      lastStatus: this.lastStatusMap.get(executionId)
    };
  }

  /**
   * 清理过期任务
   * @param {number} maxAge - 最大年龄（毫秒）
   */
  cleanupExpiredTasks(maxAge = 3600000) {
    const now = Date.now();
    const expiredTasks = [];

    this.startTimes.forEach((startTime, executionId) => {
      if (now - startTime > maxAge) {
        expiredTasks.push(executionId);
      }
    });

    expiredTasks.forEach((executionId) => {
      this.stopPolling(executionId);
    });

    if (expiredTasks.length > 0) {
      console.log(`[PollingManager] Cleaned up ${expiredTasks.length} expired tasks`);
    }
  }
}

// 导出单例
export default new PollingManager();
