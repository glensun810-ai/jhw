/**
 * 诊断服务
 * 
 * 封装诊断相关的 API 调用和轮询管理
 * 
 * @author 系统架构组
 * @date 2026-02-27
 * @version 1.0.0
 */

import pollingManager from './pollingManager';
import { handleApiError, logError } from '../utils/errorHandler';
import { isFeatureEnabled } from '../config/featureFlags';

// 本地存储键名
const STORAGE_KEY = 'pendingDiagnosis';

/**
 * 诊断服务类
 */
class DiagnosisService {
  /**
   * 构造函数
   */
  constructor() {
    this.currentTask = null;
    this.pendingTask = null;
  }

  /**
   * 发起诊断任务
   * @param {Object} config - 诊断配置
   * @returns {Promise<Object>} 任务信息
   */
  async startDiagnosis(config) {
    try {
      console.log('[DiagnosisService] Starting diagnosis with config:', config);

      const res = await wx.cloud.callFunction({
        name: 'startDiagnosis',
        data: config
      });

      const taskInfo = res.result;
      
      // 记录当前任务
      this.currentTask = {
        executionId: taskInfo.execution_id,
        reportId: taskInfo.report_id,
        startTime: Date.now(),
        config: config
      };

      // 保存到本地存储（用于恢复）
      this._saveToStorage(this.currentTask);

      console.log('[DiagnosisService] Diagnosis started:', this.currentTask);
      return taskInfo;
    } catch (error) {
      const handledError = handleApiError(error);
      logError(error, {
        context: 'startDiagnosis',
        config: config
      });
      throw handledError;
    }
  }

  /**
   * 开始轮询诊断状态
   * @param {Object} callbacks - 回调函数
   * @param {string} executionId - 可选的执行 ID，如果提供则直接使用
   * @returns {string} 执行 ID
   */
  startPolling(callbacks, executionId) {
    // P0 修复：支持直接传入 executionId 参数
    let task;
    
    if (executionId) {
      // 如果提供了 executionId，直接使用
      task = { executionId };
      console.log('[DiagnosisService] Starting polling with provided executionId:', executionId);
    } else if (this.currentTask || this.pendingTask) {
      // 使用 pendingTask 或 currentTask
      task = this.pendingTask || this.currentTask;
      executionId = task.executionId;
      console.log('[DiagnosisService] Starting polling for task:', executionId);
    } else {
      const error = new Error('No active diagnosis task');
      error.code = 'TASK_NOT_FOUND';
      throw error;
    }

    // P0 修复：直接传递 executionId 给 pollingManager
    pollingManager.startPolling(executionId, {
      onStatus: (status) => {
        // 更新页面状态
        if (callbacks.onStatus) {
          callbacks.onStatus({
            ...status,
            elapsedTime: this._getElapsedTime()
          });
        }
      },
      onComplete: (result) => {
        // 任务完成
        console.log('[DiagnosisService] Task completed:', result);
        if (callbacks.onComplete) {
          callbacks.onComplete(result);
        }
        this._clearCurrentTask();
      },
      onError: (error) => {
        // 轮询错误
        console.error('[DiagnosisService] Polling error:', error);
        if (callbacks.onError) {
          callbacks.onError(error);
        }
        // 不立即清理任务，让用户决定是否重试
      },
      onTimeout: (timeoutInfo) => {
        // 超时
        console.warn('[DiagnosisService] Task timeout:', timeoutInfo);
        if (callbacks.onTimeout) {
          callbacks.onTimeout(timeoutInfo);
        }
        this._clearCurrentTask();
      }
    });

    return executionId;
  }

  /**
   * 停止轮询
   */
  stopPolling() {
    if (this.currentTask) {
      pollingManager.stopPolling(this.currentTask.executionId);
    }
    if (this.pendingTask) {
      pollingManager.stopPolling(this.pendingTask.executionId);
    }
  }

  /**
   * 暂停轮询
   */
  pausePolling() {
    if (this.currentTask) {
      pollingManager.pausePolling(this.currentTask.executionId);
    }
  }

  /**
   * 恢复轮询
   */
  resumePolling() {
    if (this.currentTask) {
      pollingManager.resumePolling(this.currentTask.executionId);
    }
  }

  /**
   * 获取诊断结果
   * @param {string} executionId 
   * @returns {Promise<Object>}
   */
  async getReport(executionId) {
    try {
      const res = await wx.cloud.callFunction({
        name: 'getDiagnosisReport',
        data: { executionId }
      });

      return res.result;
    } catch (error) {
      const handledError = handleApiError(error);
      logError(error, {
        context: 'getReport',
        executionId: executionId
      });
      throw handledError;
    }
  }

  /**
   * 获取任务状态
   * @param {string} executionId 
   * @returns {Promise<Object>}
   */
  async getStatus(executionId) {
    try {
      const res = await wx.cloud.callFunction({
        name: 'getDiagnosisStatus',
        data: { executionId }
      });

      return res.result;
    } catch (error) {
      const handledError = handleApiError(error);
      logError(error, {
        context: 'getStatus',
        executionId: executionId
      });
      throw handledError;
    }
  }

  /**
   * 恢复未完成的任务
   * @returns {Promise<Object|null>}
   */
  async restorePendingTask() {
    try {
      const saved = wx.getStorageSync(STORAGE_KEY);
      if (!saved) {
        console.log('[DiagnosisService] No pending task found');
        return null;
      }

      // 检查是否过期（超过 1 小时）
      const oneHour = 3600000;
      if (Date.now() - saved.startTime > oneHour) {
        console.log('[DiagnosisService] Pending task expired, removing');
        wx.removeStorageSync(STORAGE_KEY);
        return null;
      }

      // 检查任务是否还在进行中
      try {
        const status = await this.getStatus(saved.executionId);
        
        if (!status.should_stop_polling) {
          // 任务还在进行中
          console.log('[DiagnosisService] Restoring pending task:', saved.executionId);
          this.pendingTask = saved;
          return saved;
        } else {
          console.log('[DiagnosisService] Task already completed, removing pending flag');
          // 任务已完成，清理存储
          wx.removeStorageSync(STORAGE_KEY);
          return null;
        }
      } catch (error) {
        console.error('[DiagnosisService] Failed to restore task:', error);
        // 无法获取状态，保留任务让用户决定
        this.pendingTask = saved;
        return saved;
      }
    } catch (error) {
      console.error('[DiagnosisService] Error restoring pending task:', error);
      return null;
    }
  }

  /**
   * 获取当前任务信息
   * @returns {Object|null}
   */
  getCurrentTask() {
    return this.currentTask || this.pendingTask;
  }

  /**
   * 获取活跃任务数量
   * @returns {number}
   */
  getActiveTaskCount() {
    return pollingManager.getActiveTaskCount();
  }

  /**
   * 获取已耗时
   * @private
   * @returns {number}
   */
  _getElapsedTime() {
    const task = this.currentTask || this.pendingTask;
    if (!task) return 0;
    return Math.floor((Date.now() - task.startTime) / 1000);
  }

  /**
   * 保存任务到本地存储
   * @private
   * @param {Object} task 
   */
  _saveToStorage(task) {
    try {
      wx.setStorageSync(STORAGE_KEY, {
        ...task,
        saveTime: Date.now()
      });
      console.log('[DiagnosisService] Task saved to storage');
    } catch (error) {
      console.error('[DiagnosisService] Failed to save task to storage:', error);
    }
  }

  /**
   * 清理当前任务
   * @private
   */
  _clearCurrentTask() {
    this.currentTask = null;
    this.pendingTask = null;
    try {
      wx.removeStorageSync(STORAGE_KEY);
      console.log('[DiagnosisService] Current task cleared');
    } catch (error) {
      console.error('[DiagnosisService] Failed to clear storage:', error);
    }
  }

  /**
   * 清理所有资源
   */
  dispose() {
    this.stopPolling();
    this._clearCurrentTask();
    console.log('[DiagnosisService] Disposed');
  }
}

// 导出单例
export default new DiagnosisService();
