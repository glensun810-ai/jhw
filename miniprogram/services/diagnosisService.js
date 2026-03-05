/**
 * 诊断服务（WebSocket）
 *
 * 功能：
 * 1. WebSocket 实时推送（优先）
 * 2. HTTP 轮询降级（兼容）
 *
 * @author: 系统架构组
 * @date: 2026-03-02
 * @version: 2.0.0
 */

import webSocketClient from './webSocketClient';
import pollingManager from './pollingManager';
import { handleApiError, logError } from '../utils/errorHandler';

// 本地存储键名
const STORAGE_KEY = 'pendingDiagnosis';

// 配置
const CONFIG = {
  // 是否启用 WebSocket
  ENABLE_WEBSOCKET: true,
  // WebSocket 连接超时时间（毫秒）
  WS_CONNECTION_TIMEOUT: 5000,
  // 降级检测：WebSocket 连接失败后多久切换到轮询
  FALLBACK_DELAY: 1000
};

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
    this.isUsingWebSocket = false;
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

      console.log('[DiagnosisService] Task info from cloud:', taskInfo);

      // 记录当前任务
      this.currentTask = {
        executionId: taskInfo.executionId || taskInfo.execution_id,
        reportId: taskInfo.reportId || taskInfo.report_id || null,
        startTime: Date.now(),
        config: config
      };

      console.log('[DiagnosisService] Current task:', this.currentTask);

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
   * 开始监听诊断进度（优先 WebSocket，失败降级轮询）
   * @param {Object} callbacks - 回调函数
   * @param {string} executionId - 可选的执行 ID
   * @returns {string} 执行 ID
   */
  startPolling(callbacks, executionId) {
    // 确定执行 ID
    if (executionId) {
      // 直接使用传入的 executionId
      this._ensureCurrentTask(executionId);
    } else if (this.currentTask || this.pendingTask) {
      // 使用已保存的任务
      executionId = (this.pendingTask || this.currentTask).executionId;
    } else {
      const error = new Error('No active diagnosis task');
      error.code = 'TASK_NOT_FOUND';
      throw error;
    }

    console.log('[DiagnosisService] Starting progress monitoring for:', executionId);

    // 优先使用 WebSocket
    if (CONFIG.ENABLE_WEBSOCKET) {
      this._connectWebSocket(executionId, callbacks);
    } else {
      this._startPolling(executionId, callbacks);
    }

    return executionId;
  }

  /**
   * 确保 currentTask 存在
   * @private
   */
  _ensureCurrentTask(executionId) {
    if (!this.currentTask) {
      this.currentTask = {
        executionId: executionId,
        startTime: Date.now(),
        config: {}
      };
    } else {
      this.currentTask.executionId = executionId;
    }
  }

  /**
   * 连接 WebSocket，失败时降级到轮询
   * @private
   */
  _connectWebSocket(executionId, callbacks) {
    console.log('[DiagnosisService] Attempting WebSocket connection...');

    const connected = webSocketClient.connect(executionId, {
      onConnected: () => {
        console.log('[DiagnosisService] ✅ WebSocket connected');
        this.isUsingWebSocket = true;

        if (callbacks.onConnected) {
          callbacks.onConnected({ mode: 'websocket' });
        }
      },

      onProgress: (data) => {
        console.log('[DiagnosisService] 📊 WebSocket progress:', data);

        if (callbacks.onStatus) {
          callbacks.onStatus({
            ...data,
            elapsedTime: this._getElapsedTime(),
            mode: 'websocket'
          });
        }
      },

      onComplete: (data) => {
        console.log('[DiagnosisService] ✅ WebSocket complete:', data);
        this.isUsingWebSocket = false;

        if (callbacks.onComplete) {
          callbacks.onComplete({
            ...data,
            mode: 'websocket'
          });
        }
        this._clearCurrentTask();
      },

      onError: (error) => {
        console.error('[DiagnosisService] ❌ WebSocket error:', error);

        if (callbacks.onError) {
          callbacks.onError(error);
        }
      },

      onFallback: () => {
        console.warn('[DiagnosisService] ⚠️ WebSocket fallback to polling');
        this.isUsingWebSocket = false;
        this._startPolling(executionId, callbacks);
      }
    });

    // 连接超时处理
    if (!connected) {
      console.warn('[DiagnosisService] WebSocket connection timeout, falling back to polling');
      setTimeout(() => {
        if (!webSocketClient.isConnected()) {
          this.isUsingWebSocket = false;
          this._startPolling(executionId, callbacks);
        }
      }, CONFIG.FALLBACK_DELAY);
    }
  }

  /**
   * 启动 HTTP 轮询
   * @private
   */
  _startPolling(executionId, callbacks) {
    console.log('[DiagnosisService] Starting HTTP polling');
    this.isUsingWebSocket = false;

    // 停止所有现有轮询，防止多个实例并存
    try {
      pollingManager.stopAllPolling();
      console.log('[DiagnosisService] ✅ Stopped all existing polling tasks');
    } catch (stopErr) {
      console.warn('[DiagnosisService] ⚠️ Failed to stop polling:', stopErr);
    }

    pollingManager.startPolling(executionId, {
      onStatus: (status) => {
        if (callbacks.onStatus) {
          callbacks.onStatus({
            ...status,
            elapsedTime: this._getElapsedTime(),
            mode: 'polling'
          });
        }
      },
      onComplete: (result) => {
        console.log('[DiagnosisService] Task completed via polling:', result);
        if (callbacks.onComplete) {
          callbacks.onComplete({
            ...result,
            mode: 'polling'
          });
        }
        this._clearCurrentTask();
      },
      onError: (error) => {
        console.error('[DiagnosisService] Polling error:', error);
        if (callbacks.onError) {
          callbacks.onError(error);
        }
      },
      onTimeout: (timeoutInfo) => {
        console.warn('[DiagnosisService] Task timeout:', timeoutInfo);
        if (callbacks.onTimeout) {
          callbacks.onTimeout(timeoutInfo);
        }
        this._clearCurrentTask();
      },
      onFallback: () => {
        console.log('[DiagnosisService] Already using polling');
      }
    });
  }

  /**
   * 停止监听
   */
  stopPolling() {
    // 停止 WebSocket
    if (webSocketClient.isConnected()) {
      webSocketClient.disconnect();
    }

    // 停止轮询
    if (this.currentTask) {
      pollingManager.stopPolling(this.currentTask.executionId);
    }
    if (this.pendingTask) {
      pollingManager.stopPolling(this.pendingTask.executionId);
    }

    this.isUsingWebSocket = false;
    console.log('[DiagnosisService] Progress monitoring stopped');
  }

  /**
   * 获取当前模式
   * @returns {string} 'websocket' 或 'polling'
   */
  getCurrentMode() {
    if (this.isUsingWebSocket && webSocketClient.isConnected()) {
      return 'websocket';
    }
    return 'polling';
  }

  /**
   * 获取连接统计
   * @returns {Object} 统计信息
   */
  getConnectionStats() {
    if (this.isUsingWebSocket) {
      return {
        mode: 'websocket',
        ...webSocketClient.getStatistics()
      };
    }
    return {
      mode: 'polling',
      ...pollingManager.getStats()
    };
  }

  /**
   * 计算已用时间
   * @private
   */
  _getElapsedTime() {
    if (this.currentTask && this.currentTask.startTime) {
      return Date.now() - this.currentTask.startTime;
    }
    return 0;
  }

  /**
   * 保存到本地存储
   * @private
   */
  _saveToStorage(task) {
    try {
      wx.setStorageSync(STORAGE_KEY, {
        executionId: task.executionId,
        startTime: task.startTime,
        config: task.config
      });
    } catch (error) {
      console.warn('[DiagnosisService] Failed to save to storage:', error);
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
    } catch (error) {
      console.warn('[DiagnosisService] Failed to clear storage:', error);
    }
  }

  /**
   * 从存储恢复任务
   * @returns {Object|null} 恢复的任务或 null
   */
  restoreFromStorage() {
    try {
      const stored = wx.getStorageSync(STORAGE_KEY);
      if (stored && stored.executionId) {
        this.pendingTask = stored;
        return stored;
      }
    } catch (error) {
      console.warn('[DiagnosisService] Failed to restore from storage:', error);
    }
    return null;
  }

  /**
   * 检查是否有待恢复的任务
   * @returns {boolean} 是否有待恢复的任务
   */
  hasPendingTask() {
    return this.pendingTask !== null || this.restoreFromStorage() !== null;
  }
}

// 导出单例
export default new DiagnosisService();
