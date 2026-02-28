/**
 * 报告页面 v2 - WebSocket 实时推送版本
 * 
 * 主要改进：
 * 1. 使用 WebSocket 实时接收诊断进度
 * 2. 自动降级到轮询模式
 * 3. 友好的错误提示
 * 4. 连接状态显示
 * 
 * @author: 系统架构组
 * @date: 2026-02-27
 * @version: 2.1.0
 */

import diagnosisService from '../../services/diagnosisService';
import webSocketClient from '../../services/webSocketClient';
import pollingManager from '../../services/pollingManager';
import { isFeatureEnabled } from '../../config/featureFlags';
import { showToast, showModal, showLoading, hideLoading } from '../../utils/uiHelper';
import { logError } from '../../utils/errorHandler';

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
    keywords: []
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
   * 开始监听（优先 WebSocket，降级到轮询）
   */
  async startListening() {
    console.log('[ReportPageV2] Starting listening...');
    this.setData({ isPolling: false });

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
          isWebSocketConnected: false // 等待连接确认
        });
      } else {
        // WebSocket 不可用，降级到轮询
        console.log('[ReportPageV2] WebSocket 不可用，降级到轮询');
        await this.startPolling();
      }

      // 启动计时器
      this.startElapsedTimer();

      console.log('[ReportPageV2] Listening started successfully');
    } catch (error) {
      console.error('[ReportPageV2] Failed to start listening:', error);
      // 降级到轮询
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
   * 启动轮询（降级方案）
   */
  async startPolling() {
    console.log('[ReportPageV2] Starting polling (fallback)...');

    // P0 修复：添加执行 ID 验证
    if (!this.data.executionId) {
      console.error('[ReportPageV2] 无法启动轮询：缺少 executionId');
      this.handleError(new Error('缺少 executionId，无法轮询'));
      return;
    }

    this.setData({
      isPolling: true,
      connectionMode: 'polling'
    });

    try {
      console.log('[ReportPageV2] 调用 diagnosisService.startPolling, executionId:', this.data.executionId);

      // P0 修复：直接传递 executionId 给 diagnosisService
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
   * 处理 WebSocket 连接成功
   */
  handleWebSocketConnected() {
    console.log('[ReportPageV2] WebSocket 已连接');
    this.setData({
      isWebSocketConnected: true,
      connectionMode: 'websocket'
    });

    showToast({
      title: '实时推送已连接',
      icon: 'success',
      duration: 1500
    });
  },

  /**
   * 处理 WebSocket 断开
   */
  handleWebSocketDisconnected() {
    console.log('[ReportPageV2] WebSocket 已断开');
    this.setData({ isWebSocketConnected: false });

    // 如果正在诊断中，显示提示
    if (this.data.status && this.data.status.status !== 'completed') {
      showToast({
        title: '实时推送已断开，尝试重连...',
        icon: 'none',
        duration: 2000
      });
    }
  },

  /**
   * 处理 WebSocket 错误
   * @param {Object} error
   */
  handleWebSocketError(error) {
    console.error('[ReportPageV2] WebSocket 错误:', error);

    this.setData({
      errorMessage: error.message || 'WebSocket 连接错误',
      retryCount: this.data.retryCount + 1
    });

    // 显示错误提示
    showToast({
      title: '实时推送连接失败',
      icon: 'none',
      duration: 2000
    });
  },

  /**
   * 处理降级到轮询
   */
  handleFallbackToPolling() {
    console.log('[ReportPageV2] 降级到轮询模式');
    
    this.setData({
      connectionMode: 'polling',
      isWebSocketConnected: false
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
   * 处理进度更新
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
   * 处理结果更新
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
   * 处理状态更新
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

    this.setData({
      status: status,
      progressHistory: history,
      errorMessage: ''
    });

    // 更新页面标题
    wx.setNavigationBarTitle({
      title: this._getTitleByStatus(status)
    });
  },

  /**
   * 处理完成
   * @param {Object} result
   */
  handleComplete(result) {
    console.log('[ReportPageV2] 诊断完成:', result);
    this.stopListening();

    // 显示成功提示
    showToast({
      title: '诊断完成',
      icon: 'success',
      duration: 2000
    });

    // 跳转到报告详情页
    setTimeout(() => {
      wx.navigateTo({
        url: `/pages/report-detail/report-detail?executionId=${this.data.executionId}`
      });
    }, 1500);
  },

  /**
   * 处理轮询错误
   * @param {Object} error
   */
  handlePollingError(error) {
    console.error('[ReportPageV2] 轮询错误:', error);

    this.setData({
      errorMessage: error.message || '网络错误',
      retryCount: this.data.retryCount + 1
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
   * 处理超时
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
      // 直接跳转到报告详情页
      wx.navigateTo({
        url: `/pages/report-detail/report-detail?reportId=${reportId}`
      });
    } catch (error) {
      console.error('[ReportPageV2] 加载历史报告失败:', error);
      this.handleError(error);
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
