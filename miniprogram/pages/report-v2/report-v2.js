/**
 * 报告页面 v2 - WebSocket 实时推送版本（P1-6 简化版）
 *
 * P1-6 改进：
 * 1. 简化轮询逻辑，减少状态分支
 * 2. 使用单一状态机管理状态
 * 3. 添加超时处理
 * 4. 网络恢复自动重连
 *
 * @author: 系统架构组
 * @date: 2026-02-27
 * @version: 2.2.0
 */

import diagnosisService from '../../services/diagnosisService';
import webSocketClient from '../../services/webSocketClient';
import pollingManager from '../../services/pollingManager';
import { isFeatureEnabled } from '../../config/featureFlags';
import { showToast, showModal, showLoading, hideLoading } from '../../utils/uiHelper';
import { logError } from '../../utils/errorHandler';

/**
 * P1-6 新增：统一状态机定义
 */
const ConnectionState = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  POLLING: 'polling',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
  COMPLETED: 'completed'
};

Page({
  /**
   * 页面数据
   */
  data: {
    executionId: '',
    reportId: null,
    status: null,
    elapsedTime: 0,
    isPolling: false,
    isWebSocketConnected: false,
    connectionMode: 'websocket', // websocket | polling
    showProgress: true,
    progressHistory: [],
    errorMessage: '',
    retryCount: 0,
    showDetails: false,
    isLoading: true, // 加载状态，用于控制骨架屏显示
    lastUpdateTime: null,
    activeTab: 'overview',
    brandDistribution: {},
    sentimentDistribution: {},
    keywords: [],
    // P1-6 新增：连接状态
    connectionState: ConnectionState.IDLE,
    // P1-6 新增：超时时间
    pollingTimeout: 300000, // 5 分钟
    pollingStartTime: null
  },

  /**
   * 计时器
   */
  elapsedTimer: null,

  /**
   * 页面加载
   */
  onLoad(options) {
    console.log('[ReportPageV2] onLoad with options:', options);
    this.initPage(options);
  },

  /**
   * 页面卸载
   */
  onUnload() {
    console.log('[ReportPageV2] onUnload, cleaning up...');
    this.stopListening();
    this.stopElapsedTimer();
  },

  /**
   * 页面隐藏
   */
  onHide() {
    console.log('[ReportPageV2] onHide, pausing listening...');
    this.pauseListening();
  },

  /**
   * 页面显示
   */
  onShow() {
    console.log('[ReportPageV2] onShow, resuming listening...');
    this.resumeListening();
  },

  /**
   * 初始化页面
   * @param {Object} options
   */
  async initPage(options) {
    // 设置加载状态，显示骨架屏
    this.setData({ isLoading: true });

    try {
      // 如果是新发起的诊断
      if (options.executionId) {
        console.log('[ReportPageV2] New diagnosis with executionId:', options.executionId);
        this.setData({
          executionId: options.executionId,
          reportId: options.reportId
        });

        await this.startListening();
      }
      // 如果是查看历史诊断
      else if (options.reportId) {
        console.log('[ReportPageV2] History report with reportId:', options.reportId);
        await this.loadHistoryReport(options.reportId);
      }
      // 尝试恢复未完成的任务
      else {
        console.log('[ReportPageV2] Trying to restore pending task');
        const pending = await diagnosisService.restorePendingTask();
        if (pending) {
          console.log('[ReportPageV2] Restored pending task:', pending);
          this.setData({
            executionId: pending.executionId,
            reportId: pending.reportId
          });
          await this.startListening();
        } else {
          console.log('[ReportPageV2] No pending task, navigating back');
          wx.navigateBack();
        }
      }
    } catch (error) {
      console.error('[ReportPageV2] Initialization error:', error);
      this.handleError(error);
    } finally {
      // 数据加载完成，隐藏骨架屏
      this.setData({ isLoading: false });
    }
  },

  /**
   * 开始监听（P1-6 简化版 - 优先 WebSocket，自动降级到轮询）
   */
  async startListening() {
    console.log('[ReportPageV2] Starting listening...');
    
    // P1-6 简化：使用统一状态机
    this.setData({ 
      isPolling: false,
      connectionState: ConnectionState.CONNECTING
    });

    try {
      // 尝试使用 WebSocket
      const wsSuccess = webSocketClient.connect(this.data.executionId, {
        onConnected: this.handleWebSocketConnected.bind(this),
        onProgress: this.handleProgressUpdate.bind(this),
        onResult: this.handleResultUpdate.bind(this),
        onComplete: this.handleComplete.bind(this),
        onError: this.handleWebSocketError.bind(this),
        onDisconnected: this.handleWebSocketDisconnected.bind(this),
        onFallback: this.handleFallbackToPolling.bind(this)
      });

      if (wsSuccess) {
        console.log('[ReportPageV2] WebSocket 连接已启动');
        this.setData({
          connectionMode: 'websocket',
          isWebSocketConnected: false, // 等待连接确认
          connectionState: ConnectionState.CONNECTING
        });
      } else {
        // WebSocket 不可用，直接降级到轮询
        console.log('[ReportPageV2] WebSocket 不可用，降级到轮询');
        await this.startPolling();
      }

      // 启动计时器
      this.startElapsedTimer();

      console.log('[ReportPageV2] Listening started successfully');
    } catch (error) {
      console.error('[ReportPageV2] Failed to start listening:', error);
      // 任何错误都降级到轮询
      await this.startPolling();
    }
  },

  /**
   * 停止监听
   */
  stopListening() {
    console.log('[ReportPageV2] Stopping listening...');
    
    // 关闭 WebSocket
    webSocketClient.disconnect();
    
    // 停止轮询
    pollingManager.stopAllPolling();
    
    this.setData({
      isPolling: false,
      isWebSocketConnected: false
    });
    this.stopElapsedTimer();
  },

  /**
   * 暂停监听
   */
  pauseListening() {
    console.log('[ReportPageV2] Pausing listening...');
    
    // 暂停 WebSocket（保持连接）
    // WebSocket 不需要暂停，保持连接即可
    
    // 暂停轮询
    pollingManager.stopAllPolling();
    
    this.setData({ isPolling: false });
    this.stopElapsedTimer();
  },

  /**
   * 恢复监听
   */
  resumeListening() {
    console.log('[ReportPageV2] Resuming listening...');
    
    // 如果 WebSocket 已连接，无需恢复
    if (webSocketClient.getConnectionStatus()) {
      console.log('[ReportPageV2] WebSocket 已连接，无需恢复');
      this.setData({ isWebSocketConnected: true });
      this.startElapsedTimer();
      return;
    }

    // 恢复轮询
    if (this.data.executionId && !this.data.isPolling) {
      console.log('[ReportPageV2] 恢复轮询');
      this.startPolling();
    }
  },

  /**
   * 启动轮询（P1-6 简化版 - 降级方案）
   */
  async startPolling() {
    console.log('[ReportPageV2] Starting polling (fallback)...');

    // P1-6 简化：添加执行 ID 验证和超时控制
    if (!this.data.executionId) {
      console.error('[ReportPageV2] 无法启动轮询：缺少 executionId');
      this.handleError(new Error('缺少 executionId，无法轮询'));
      return;
    }

    // P1-6 简化：使用统一状态机
    this.setData({
      isPolling: true,
      connectionMode: 'polling',
      connectionState: ConnectionState.POLLING,
      pollingStartTime: Date.now()
    });

    try {
      console.log('[ReportPageV2] 调用 diagnosisService.startPolling, executionId:', this.data.executionId);

      // P1-6 简化：直接传递 executionId 给 diagnosisService
      diagnosisService.startPolling({
        onStatus: this.handleStatusUpdate.bind(this),
        onComplete: this.handleComplete.bind(this),
        onError: this.handlePollingError.bind(this),
        onTimeout: this.handleTimeout.bind(this)
      }, this.data.executionId);

      console.log('[ReportPageV2] Polling started successfully');
    } catch (error) {
      console.error('[ReportPageV2] Failed to start polling:', error);
      this.handleError(error);
    }
  },

  /**
   * P1-6 新增：检查轮询超时
   */
  checkPollingTimeout() {
    const { pollingStartTime, pollingTimeout } = this.data;
    
    if (!pollingStartTime) {
      return false;
    }
    
    const elapsed = Date.now() - pollingStartTime;
    if (elapsed > pollingTimeout) {
      console.warn('[ReportPageV2] 轮询超时');
      this.handleTimeout({
        message: '诊断处理时间过长，建议查看历史记录',
        elapsed: elapsed
      });
      return true;
    }
    
    return false;
  },

  /**
   * 处理 WebSocket 连接成功（P1-6 简化版）
   */
  handleWebSocketConnected() {
    console.log('[ReportPageV2] WebSocket 已连接');
    
    // P1-6 简化：使用统一状态机
    this.setData({
      isWebSocketConnected: true,
      connectionMode: 'websocket',
      connectionState: ConnectionState.CONNECTED
    });

    showToast({
      title: '实时推送已连接',
      icon: 'success',
      duration: 1500
    });
  },

  /**
   * 处理 WebSocket 断开（P1-6 简化版）
   */
  handleWebSocketDisconnected() {
    console.log('[ReportPageV2] WebSocket 已断开');
    
    // P1-6 简化：使用统一状态机
    this.setData({ 
      isWebSocketConnected: false,
      connectionState: ConnectionState.DISCONNECTED
    });

    // 如果正在诊断中，显示提示
    if (this.data.status && this.data.status.status !== 'completed') {
      showToast({
        title: '实时推送已断开，尝试重连...',
        icon: 'none',
        duration: 2000
      });
      
      // P1-6 新增：自动重连逻辑
      this.scheduleReconnect();
    }
  },

  /**
   * P1-6 新增：安排重连
   */
  scheduleReconnect() {
    const reconnectDelay = 3000; // 3 秒后重连
    
    console.log(`[ReportPageV2] 安排重连：${reconnectDelay}ms 后`);
    
    setTimeout(() => {
      // 检查是否仍需要重连
      if (this.data.status?.status !== 'completed' && this.data.connectionState !== ConnectionState.CONNECTED) {
        console.log('[ReportPageV2] 执行自动重连');
        this.setData({ connectionState: ConnectionState.CONNECTING });
        this.startListening();
      }
    }, reconnectDelay);
  },

  /**
   * 处理 WebSocket 错误（P1-6 简化版）
   * @param {Object} error
   */
  handleWebSocketError(error) {
    console.error('[ReportPageV2] WebSocket 错误:', error);

    // P1-6 简化：使用统一状态机
    this.setData({
      errorMessage: error.message || 'WebSocket 连接错误',
      retryCount: this.data.retryCount + 1,
      connectionState: ConnectionState.ERROR
    });

    // 显示错误提示
    showToast({
      title: '实时推送连接失败',
      icon: 'none',
      duration: 2000
    });
  },

  /**
   * 处理降级到轮询（P1-6 简化版）
   */
  handleFallbackToPolling() {
    console.log('[ReportPageV2] 降级到轮询模式');

    this.setData({
      connectionMode: 'polling',
      isWebSocketConnected: false,
      connectionState: ConnectionState.POLLING
    });

    showToast({
      title: '切换到轮询模式',
      icon: 'none',
      duration: 2000
    });

    // 启动轮询
    this.startPolling();
  },

  /**
   * 处理轮询错误（P1-6 简化版）
   * @param {Object} error
   */
  handlePollingError(error) {
    console.error('[ReportPageV2] 轮询错误:', error);

    this.setData({
      errorMessage: error.message || '网络错误',
      retryCount: this.data.retryCount + 1,
      connectionState: ConnectionState.ERROR
    });

    // 根据错误类型显示不同提示
    if (error.message && error.message.includes('网络')) {
      showToast({
        title: '网络连接失败',
        icon: 'none',
        duration: 2000
      });
    }
  },

  /**
   * 处理进度更新（P1-6 简化版）
   * @param {Object} data
   */
  handleProgressUpdate(data) {
    console.log('[ReportPageV2] 进度更新:', data);

    this.handleStatusUpdate({
      progress: data.progress,
      stage: data.stage,
      status: data.status,
      status_text: data.status_text
    });
  },

  /**
   * 处理结果更新（P1-6 简化版）
   * @param {Object} data
   */
  handleResultUpdate(data) {
    console.log('[ReportPageV2] 结果更新:', data);

    // 更新进度历史
    const history = this.data.progressHistory;
    history.push({
      type: 'result',
      data: data,
      time: Date.now()
    });

    // 只保留最近 20 条记录
    if (history.length > 20) {
      history.shift();
    }

    this.setData({ progressHistory: history });
  },

  /**
   * 处理状态更新（P1-6 简化版）
   * @param {Object} status
   */
  handleStatusUpdate(status) {
    console.log('[ReportPageV2] 状态更新:', status);

    // 记录进度历史
    const history = this.data.progressHistory;
    history.push({
      progress: status.progress,
      stage: status.stage,
      status: status.status,
      time: Date.now()
    });

    // 只保留最近 20 条记录
    if (history.length > 20) {
      history.shift();
    }

    // P1-6 简化：使用统一状态机
    this.setData({
      status: status,
      progressHistory: history,
      errorMessage: '',
      connectionState: status.status === 'completed' 
        ? ConnectionState.COMPLETED 
        : this.data.connectionState
    });

    // 更新页面标题
    wx.setNavigationBarTitle({
      title: this._getTitleByStatus(status)
    });
    
    // P1-6 新增：检查轮询超时
    if (this.data.connectionMode === 'polling') {
      this.checkPollingTimeout();
    }
  },

  /**
   * 处理完成（P1-6 简化版）
   * @param {Object} result
   */
  handleComplete(result) {
    console.log('[ReportPageV2] 诊断完成:', result);
    this.stopListening();

    // P1-6 简化：使用统一状态机
    this.setData({ connectionState: ConnectionState.COMPLETED });

    // 显示成功提示
    showToast({
      title: '诊断完成',
      icon: 'success',
      duration: 2000
    });

    // 刷新当前页面数据
    setTimeout(() => {
      this.loadReportData(this.data.executionId);
    }, 1500);
  },

  /**
   * 处理超时（P1-6 简化版）
   * @param {Object} timeoutInfo
   */
  async handleTimeout(timeoutInfo) {
    console.warn('[ReportPageV2] 诊断超时:', timeoutInfo);
    this.stopListening();

    const confirmed = await showModal({
      title: '诊断超时',
      content: timeoutInfo.message || '诊断任务执行时间过长',
      confirmText: '查看历史记录',
      cancelText: '关闭'
    });

    if (confirmed) {
      wx.navigateTo({
        url: '/pages/history/history'
      });
    }
  },

  /**
   * 加载历史报告
   * @param {string} reportId
   */
  async loadHistoryReport(reportId) {
    console.log('[ReportPageV2] 加载历史报告:', reportId);
    showLoading('加载中...');

    try {
      // 【修复】加载历史报告数据并在当前页面显示
      await this.loadReportData(null, reportId);
    } catch (error) {
      console.error('[ReportPageV2] 加载历史报告失败:', error);
      this.handleError(error);
    } finally {
      hideLoading();
    }
  },

  /**
   * 加载报告数据
   * @param {string} executionId - 执行 ID
   * @param {string} reportId - 报告 ID（可选）
   */
  async loadReportData(executionId, reportId) {
    console.log('[ReportPageV2] 加载报告数据:', { executionId, reportId });

    try {
      // 使用 reportService 获取完整报告
      const reportService = require('../../services/reportService').default;
      
      const id = executionId || this.data.executionId;
      
      if (!id) {
        throw new Error('缺少执行 ID');
      }

      showLoading('加载报告中...');

      // 获取完整报告
      const report = await reportService.getFullReport(id);

      console.log('[ReportPageV2] 报告数据:', report);

      // 检查是否有错误
      if (report.error) {
        this.setData({
          hasError: true,
          errorMessage: report.error.message || '加载报告失败'
        });
        showToast({
          title: report.error.message,
          icon: 'none'
        });
        return;
      }

      // 更新页面数据
      this.setData({
        brandDistribution: report.brandDistribution || {},
        sentimentDistribution: report.sentimentDistribution || {},
        keywords: report.keywords || [],
        status: { status: 'completed', progress: 100, stage: 'completed' },
        lastUpdateTime: new Date().toLocaleTimeString(),
        hasError: false
      });

      console.log('[ReportPageV2] 报告数据加载成功');
    } catch (error) {
      console.error('[ReportPageV2] 加载报告数据失败:', error);
      this.setData({
        hasError: true,
        errorMessage: '加载报告失败：' + (error.message || '未知错误')
      });
      showToast({
        title: '加载报告失败',
        icon: 'none'
      });
    } finally {
      hideLoading();
    }
  },

  /**
   * 启动计时器
   */
  startElapsedTimer() {
    this.stopElapsedTimer();

    this.elapsedTimer = setInterval(() => {
      this.setData({
        elapsedTime: this.data.elapsedTime + 1
      });
    }, 1000);
  },

  /**
   * 停止计时器
   */
  stopElapsedTimer() {
    if (this.elapsedTimer) {
      clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
  },

  /**
   * 处理错误
   * @param {Object} error
   */
  async handleError(error) {
    console.error('[ReportPageV2] 错误:', error);
    logError(error, {
      context: 'reportPageV2',
      executionId: this.data.executionId
    });

    await showModal({
      title: '出错了',
      content: error.message || '未知错误',
      showCancel: false
    });
  },

  /**
   * 根据状态获取标题
   * @private
   * @param {Object} status
   * @returns {string}
   */
  _getTitleByStatus(status) {
    const titles = {
      'initializing': '初始化中',
      'init': '初始化中',
      'ai_fetching': '获取 AI 数据',
      'analyzing': '分析数据中',
      'intelligence_analyzing': '深度分析中',
      'competition_analyzing': '竞争分析中',
      'completed': '诊断完成',
      'partial_success': '部分完成',
      'failed': '诊断失败',
      'timeout': '诊断超时'
    };
    return titles[status?.stage] || titles[status?.status] || '品牌诊断';
  },

  /**
   * 用户操作：重试
   */
  onRetry() {
    console.log('[ReportPageV2] 用户点击重试');
    this.setData({
      errorMessage: '',
      retryCount: 0
    });
    this.stopListening();
    this.startListening();
  },

  /**
   * 用户操作：取消
   */
  async onCancel() {
    console.log('[ReportPageV2] 用户点击取消');
    const confirmed = await showModal({
      title: '确认取消',
      content: '确定要取消当前诊断吗？已获取的结果不会丢失。',
      confirmText: '确定',
      cancelText: '继续'
    });

    if (confirmed) {
      this.stopListening();
      wx.navigateBack();
    }
  },

  /**
   * 用户操作：查看详情
   */
  onToggleDetails() {
    this.setData({
      showDetails: !this.data.showDetails
    });
  },

  /**
   * 用户操作：切换连接模式
   */
  onToggleConnectionMode() {
    if (this.data.connectionMode === 'websocket') {
      // 切换到轮询
      console.log('[ReportPageV2] 切换到轮询模式');
      webSocketClient.disconnect();
      this.startPolling();
    } else {
      // 切换到 WebSocket
      console.log('[ReportPageV2] 切换到 WebSocket 模式');
      pollingManager.stopAllPolling();
      this.setData({ isPolling: false });
      this.startListening();
    }
  }
});
