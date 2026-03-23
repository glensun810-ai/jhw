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

// 获取全局配置
const app = getApp();

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
   * 【P0 架构级修复 - 2026-03-18】使用统一响应处理器
   */
  _handleResponse(res, context) {
    const { UnifiedResponseHandler } = require('../utils/unifiedResponseHandler');
    return UnifiedResponseHandler.handleResponse(res, context);
  }

  /**
   * 【P0 架构级修复 - 2026-03-18】使用统一响应处理器（带重试）
   */
  _handleWithRetry(requestFn, context) {
    const { UnifiedResponseHandler } = require('../utils/unifiedResponseHandler');
    return UnifiedResponseHandler.handleWithRetry(requestFn, context);
  }

  /**
   * 发起诊断任务
   * @param {Object} config - 诊断配置
   * @returns {Promise<Object>} 任务信息
   */
  async startDiagnosis(config) {
    try {
      console.log('[DiagnosisService] Starting diagnosis with config:', config);

      // 【P0 临时修复 - 2026-03-13】开发环境直连后端 API，绕过云函数
      const envVersion = this._getEnvVersion();
      
      if (envVersion === 'develop' || envVersion === 'trial') {
        console.log('[DiagnosisService] 开发环境：使用 HTTP 直连后端 API');
        return await this._startDiagnosisViaHttp(config);
      }

      // 生产环境：使用云函数
      console.log('[DiagnosisService] 生产环境：使用云函数');
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
   * 【P0 新增 - 2026-03-13】通过 HTTP 发起诊断（开发环境）
   * @param {Object} config - 诊断配置
   * @returns {Promise<Object>} 任务信息
   * @private
   */
  async _startDiagnosisViaHttp(config) {
    const API_BASE_URL = 'http://localhost:5001';  // 本地后端地址

    try {
      const res = await wx.request({
        url: `${API_BASE_URL}/api/diagnosis/start`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json'
        },
        timeout: 30000,
        data: config
      });

      const taskInfo = res.data;

      console.log('[DiagnosisService] HTTP 诊断启动成功:', taskInfo);

      // 记录当前任务
      this.currentTask = {
        executionId: taskInfo.executionId || taskInfo.execution_id,
        reportId: taskInfo.reportId || taskInfo.report_id || null,
        startTime: Date.now(),
        config: config
      };

      // 保存到本地存储（用于恢复）
      this._saveToStorage(this.currentTask);

      return taskInfo;

    } catch (error) {
      console.error('[DiagnosisService] HTTP 启动诊断失败:', error);

      // 提供更友好的错误提示
      if (error.errMsg && error.errMsg.includes('timeout')) {
        throw new Error('请求超时，请检查后端服务是否启动');
      } else if (error.errMsg && error.errMsg.includes('fail')) {
        throw new Error('无法连接后端服务，请确认 localhost:5001 可访问');
      }

      throw error;
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

    // 【P0 优化 - 2026-03-09】开始轮询前重置 WebSocket 的永久失败标志
    this._resetWebSocketFailure();

    // 优先使用 WebSocket
    if (CONFIG.ENABLE_WEBSOCKET) {
      this._connectWebSocket(executionId, callbacks);
    } else {
      this._startPolling(executionId, callbacks);
    }

    return executionId;
  }

  /**
   * 【P0 优化 - 2026-03-09】重置 WebSocket 的永久失败标志
   * @private
   */
  _resetWebSocketFailure() {
    try {
      const webSocketClient = require('./webSocketClient').default;
      if (webSocketClient && typeof webSocketClient.resetPermanentFailure === 'function') {
        webSocketClient.resetPermanentFailure();
        console.log('[DiagnosisService] ✅ WebSocket failure flags reset');
      }
    } catch (error) {
      console.warn('[DiagnosisService] Failed to reset WebSocket failure:', error);
    }
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

    // 【P0 关键修复 - 2026-03-11】添加轮询启动标志，防止重复启动
    this.isPollingStarted = false;

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

        // 【P0 关键修复 - 2026-03-11】检查是否已启动轮询，防止重复
        if (this.isPollingStarted) {
          console.warn('[onError] ⚠️ 轮询已启动，跳过重复降级');
          return;
        }

        if (callbacks.onError) {
          callbacks.onError(error);
        }
      },

      // 【P1 修复 - 2026-03-11】降级前回调：停止轮询，防止回调冲突
      onBeforeFallback: () => {
        console.log('[DiagnosisService] 🛑 WebSocket 降级前通知，停止轮询...');
        try {
          pollingManager.stopAllPolling();
          console.log('[DiagnosisService] ✅ 已停止所有轮询任务');
        } catch (stopErr) {
          console.warn('[DiagnosisService] ⚠️ 停止轮询失败:', stopErr);
        }
      },

      onFallback: () => {
        console.warn('[DiagnosisService] ⚠️ WebSocket fallback to polling');

        // 【P0 关键修复 - 2026-03-11】检查是否已启动轮询，防止重复
        if (this.isPollingStarted) {
          console.warn('[onFallback] ⚠️ 轮询已启动，跳过重复降级');
          return;
        }

        this.isUsingWebSocket = false;
        this._startPolling(executionId, callbacks);
      }
    });

    // 连接超时处理
    if (!connected) {
      console.warn('[DiagnosisService] WebSocket connection timeout, falling back to polling');
      setTimeout(() => {
        // 【P0 关键修复 - 2026-03-11】检查是否已启动轮询，防止重复
        if (!this.isPollingStarted && !webSocketClient.isConnected()) {
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

    // 【P0 关键修复 - 2026-03-11】设置轮询启动标志，防止重复降级
    this.isPollingStarted = true;
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
        // 【P0 关键修复 - 2026-03-11】完成后重置标志
        this.isPollingStarted = false;
        this.isUsingWebSocket = false;
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

  /**
   * 【P0 关键修复 - 2026-03-13】获取完整报告
   * 从 API 获取完整的诊断报告数据
   *
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 完整报告数据
   */
  async getFullReport(executionId) {
    try {
      console.log('[DiagnosisService] Getting full report:', executionId);

      // 【P0 临时修复 - 2026-03-13】开发环境直连后端 API，绕过云函数
      // 解决云函数未部署导致的 FUNCTION_NOT_FOUND 错误
      const envVersion = this._getEnvVersion();
      
      if (envVersion === 'develop' || envVersion === 'trial') {
        console.log('[DiagnosisService] 开发环境：使用 HTTP 直连后端 API');
        return await this._getFullReportViaHttp(executionId);
      }

      // 生产环境：使用云函数
      console.log('[DiagnosisService] 生产环境：使用云函数');
      const res = await wx.cloud.callFunction({
        name: 'getDiagnosisReport',
        data: {
          executionId: executionId  // 使用 executionId 而不是 execution_id
        }
      });

      const result = res.result;
      console.log('[DiagnosisService] Full report received:', result);

      // 检查云函数调用是否成功
      if (!result) {
        throw new Error('云函数返回为空');
      }

      // 检查是否有错误
      if (result.error_code || result.error) {
        const error = new Error(result.error_message || result.error || '获取报告失败');
        error.code = result.error_code || 'REPORT_ERROR';
        throw error;
      }

      // 处理云函数返回格式：{ success: true, data: report }
      let report;
      if (result.success && result.data) {
        report = result.data;
        console.log('[DiagnosisService] 使用 result.data 作为报告数据');
      } else if (result.report) {
        // 兼容旧格式：{ report: {...}, results: [...] }
        report = result;
        console.log('[DiagnosisService] 使用 result 作为报告数据（兼容格式）');
      } else {
        // 直接返回 result
        report = result;
        console.log('[DiagnosisService] 使用 result 作为报告数据（直接返回）');
      }

      // 确保返回的数据格式一致
      // 后端可能返回 camelCase 或 snake_case，统一处理
      return this._normalizeReport(report);

    } catch (error) {
      console.error('[DiagnosisService] Failed to get full report:', error);
      throw error;
    }
  }

  /**
   * 【P0 新增 - 2026-03-13】通过 HTTP 获取报告（开发环境）
   * 【P0 架构级修复 - 2026-03-18】使用统一响应处理器
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 报告数据
   * @private
   */
  async _getFullReportViaHttp(executionId) {
    // 【修复 - 2026-03-15】使用全局配置中的服务器地址
    const API_BASE_URL = app.globalData.serverUrl || 'http://127.0.0.1:5001';

    try {
      const url = `${API_BASE_URL}/api/diagnosis/report/${executionId}`;
      console.log('[DiagnosisService] 开始请求报告:', url);
      console.log('[DiagnosisService] 当前 serverUrl:', API_BASE_URL);

      // 【P0 架构级修复】使用统一响应处理器（带重试）
      const result = await this._handleWithRetry(
        () => {
          return new Promise((resolve, reject) => {
            wx.request({
              url: url,
              method: 'GET',
              header: {
                'Content-Type': 'application/json'
              },
              timeout: 30000,
              responseType: 'text',
              success: (res) => {
                console.log('[DiagnosisService] wx.request success:', {
                  statusCode: res.statusCode,
                  hasData: !!res.data,
                  dataType: typeof res.data,
                  errMsg: res.errMsg
                });
                resolve(res);
              },
              fail: (err) => {
                console.error('[DiagnosisService] wx.request fail:', {
                  errMsg: err.errMsg,
                  statusCode: err.statusCode
                });
                reject(err);
              }
            });
          });
        },
        `getReport:${executionId}`
      );

      console.log('[DiagnosisService] ✅ 报告获取成功');

      // 【P0 修复 - 2026-03-15】检查后端返回的错误标志
      if (result.validation?.is_empty_data || result.qualityHints?.is_empty_data) {
        console.warn('[DiagnosisService] ⚠️ 后端返回空数据标志');
        const errorMsg = result.error?.message || result.validation?.errors?.[0] || '后端返回数据为空';
        const error = new Error(errorMsg);
        error.code = 'EMPTY_DATA';
        throw error;
      }

      // 检查是否有错误
      if (result.error_code || result.error) {
        const error = new Error(result.error_message || result.error || '获取报告失败');
        error.code = result.error_code || 'REPORT_ERROR';
        throw error;
      }

      // 处理响应格式
      let report;
      if (result.success && result.data) {
        report = result.data;
      } else {
        report = result;
      }

      return this._normalizeReport(report);

    } catch (error) {
      console.error('[DiagnosisService] HTTP 获取报告失败:', error);

      // 提供更友好的错误提示
      if (error.message) {
        if (error.message.includes('网络') || error.message.includes('timeout')) {
          throw new Error('网络连接失败，请检查网络或后端服务');
        }
        if (error.message.includes('为空')) {
          throw new Error('诊断数据为空，请尝试重新诊断');
        }
      }

      throw error;
    }
  }

  /**
   * 【P0 新增 - 2026-03-13】获取当前环境版本
   * @returns {string} 'develop' | 'trial' | 'release'
   * @private
   */
  _getEnvVersion() {
    // 微信开发者工具中可以通过 __wxConfig 获取环境信息
    if (typeof __wxConfig !== 'undefined' && __wxConfig.envVersion) {
      return __wxConfig.envVersion;
    }

    // 如果没有配置，默认为开发环境（便于调试）
    console.warn('[DiagnosisService] 无法获取环境版本，默认为开发环境');
    return 'develop';
  }

  /**
   * 【P0 关键修复 - 2026-03-13】获取历史报告
   * 从 API 获取历史诊断报告数据（不重新计算）
   *
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 历史报告数据
   */
  async getHistoryReport(executionId) {
    try {
      console.log('[DiagnosisService] Getting history report:', executionId);

      // 【P0 临时修复 - 2026-03-13】开发环境直连后端 API，绕过云函数
      const envVersion = this._getEnvVersion();
      
      if (envVersion === 'develop' || envVersion === 'trial') {
        console.log('[DiagnosisService] 开发环境：使用 HTTP 直连后端 API');
        return await this._getHistoryReportViaHttp(executionId);
      }

      // 生产环境：使用云函数
      console.log('[DiagnosisService] 生产环境：使用云函数');
      
      let res;
      try {
        res = await wx.cloud.callFunction({
          name: 'getDiagnosisReport',
          data: {
            executionId: executionId,
            isHistory: true  // 标记为历史报告查询
          },
          timeout: 15000
        });
      } catch (cloudError) {
        console.error('[DiagnosisService] 云函数调用失败:', cloudError);
        throw new Error('云函数调用失败：' + (cloudError.errMsg || cloudError.message || '未知错误'));
      }

      // 【死循环修复 - 2026-03-14】检查云函数返回是否为空
      if (!res || !res.result) {
        console.error('[DiagnosisService] 云函数返回为空:', res);
        throw new Error('云函数返回为空，请检查云函数是否部署成功');
      }

      const result = res.result;
      console.log('[DiagnosisService] History report received:', result);

      // 检查是否有错误
      if (result.error_code || result.error) {
        const error = new Error(result.error_message || result.error || '获取历史报告失败');
        error.code = result.error_code || 'REPORT_ERROR';
        throw error;
      }

      // 处理云函数返回格式
      let report;
      if (result.success && result.data) {
        report = result.data;
      } else if (result.report) {
        report = result;
      } else {
        report = result;
      }

      return this._normalizeReport(report);

    } catch (error) {
      console.error('[DiagnosisService] Failed to get history report:', error);
      throw error;
    }
  }

  /**
   * 【P0 新增 - 2026-03-13】通过 HTTP 获取历史报告（开发环境）
   * 【P0 架构级修复 - 2026-03-18】使用统一响应处理器
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 历史报告数据
   * @private
   */
  async _getHistoryReportViaHttp(executionId) {
    // 【修复 - 2026-03-15】使用全局配置中的服务器地址
    const API_BASE_URL = app.globalData.serverUrl || 'http://127.0.0.1:5001';

    try {
      const url = `${API_BASE_URL}/api/diagnosis/report/${executionId}/history`;
      console.log('[DiagnosisService] 开始请求历史报告:', url);

      // 【P0 架构级修复】使用统一响应处理器（带重试）
      const result = await this._handleWithRetry(
        () => wx.request({
          url: url,
          method: 'GET',
          header: {
            'Content-Type': 'application/json'
          },
          timeout: 30000,
          responseType: 'text'
        }),
        `getHistoryReport:${executionId}`
      );

      console.log('[DiagnosisService] ✅ 历史报告获取成功');

      // 检查是否有错误
      if (result.error_code || result.error) {
        const error = new Error(result.error_message || result.error || '获取历史报告失败');
        error.code = result.error_code || 'REPORT_ERROR';
        throw error;
      }

      return this._normalizeReport(result);

    } catch (error) {
      console.error('[DiagnosisService] HTTP 获取历史报告失败:', error);

      // 提供更友好的错误提示
      if (error.message) {
        if (error.message.includes('网络') || error.message.includes('timeout')) {
          throw new Error('网络连接失败，请检查网络或后端服务');
        }
        if (error.message.includes('为空')) {
          throw new Error('历史诊断数据为空');
        }
      }

      throw error;
    }
  }

  /**
   * 【P0 关键修复 - 2026-03-13】标准化报告数据格式
   * 确保返回的报告数据格式一致（camelCase）
   * 
   * @param {Object} report - 原始报告数据
   * @returns {Object} 标准化后的报告数据
   * @private
   */
  _normalizeReport(report) {
    // 如果已经是 camelCase，直接返回
    if (report.brandDistribution && report.sentimentDistribution) {
      return report;
    }

    // 将 snake_case 转换为 camelCase
    const normalized = {};

    for (const key in report) {
      if (report.hasOwnProperty(key)) {
        const camelKey = this._toCamelCase(key);
        normalized[camelKey] = report[key];
      }
    }

    return normalized;
  }

  /**
   * 【P0 关键修复 - 2026-03-13】将 snake_case 转换为 camelCase
   * 
   * @param {string} str - 输入字符串
   * @returns {string} camelCase 字符串
   * @private
   */
  _toCamelCase(str) {
    return str.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
  }
}

// 导出单例（CommonJS 语法，兼容微信小程序）
const diagnosisServiceInstance = new DiagnosisService();
module.exports = diagnosisServiceInstance;
module.exports.default = diagnosisServiceInstance; // 兼容 .default 导入方式
