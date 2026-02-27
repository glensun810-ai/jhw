/**
 * 诊断页面 - 前端状态轮询优化版本
 * 
 * 主要改进：
 * 1. 使用 PollingManager 统一管理轮询
 * 2. 基于 should_stop_polling 智能终止轮询
 * 3. 指数退避重试策略
 * 4. 进度显示组件
 * 5. 任务恢复机制
 * 6. 友好的错误处理
 * 
 * @author 系统架构组
 * @date 2026-02-27
 * @version 2.0.0
 */

import diagnosisService from '../../services/diagnosisService';
import { isFeatureEnabled } from '../../config/featureFlags';
import { showToast, showModal, showLoading, hideLoading, showErrorToast } from '../../utils/uiHelper';
import { logError, handleApiError, isRetryableError } from '../../utils/errorHandler';

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
    showProgress: true,
    progressHistory: [],  // 记录进度变化
    errorMessage: '',
    retryCount: 0,
    showDetails: false,
    // 错误提示组件相关
    showErrorToast: false,
    errorType: 'default',
    errorTitle: '',
    errorDetail: '',
    errorCode: '',
    showRetry: false,
    showCancel: false
  },

  /**
   * 计时器
   */
  elapsedTimer: null,

  /**
   * 页面加载
   */
  onLoad(options) {
    console.log('[DiagnosisPage] onLoad with options:', options);
    this.initPage(options);
  },

  /**
   * 页面卸载
   */
  onUnload() {
    console.log('[DiagnosisPage] onUnload, cleaning up...');
    this.stopPolling();
    this.stopElapsedTimer();
  },

  /**
   * 页面隐藏
   */
  onHide() {
    console.log('[DiagnosisPage] onHide, pausing polling...');
    this.pausePolling();
  },

  /**
   * 页面显示
   */
  onShow() {
    console.log('[DiagnosisPage] onShow, resuming polling...');
    this.resumePolling();
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    console.log('[DiagnosisPage] onPullDownRefresh');
    // 刷新当前状态
    this.refreshStatus();
  },

  /**
   * 初始化页面
   * @param {Object} options 
   */
  async initPage(options) {
    showLoading('初始化中...');

    try {
      // 如果是新发起的诊断
      if (options.executionId) {
        console.log('[DiagnosisPage] New diagnosis with executionId:', options.executionId);
        this.setData({
          executionId: options.executionId,
          reportId: options.reportId
        });
        
        await this.startPolling();
      } 
      // 如果是查看历史诊断
      else if (options.reportId) {
        console.log('[DiagnosisPage] History report with reportId:', options.reportId);
        await this.loadHistoryReport(options.reportId);
      }
      // 尝试恢复未完成的任务
      else {
        console.log('[DiagnosisPage] Trying to restore pending task');
        const pending = await diagnosisService.restorePendingTask();
        if (pending) {
          console.log('[DiagnosisPage] Restored pending task:', pending);
          this.setData({
            executionId: pending.executionId,
            reportId: pending.reportId
          });
          await this.startPolling();
        } else {
          console.log('[DiagnosisPage] No pending task, navigating back');
          wx.navigateBack();
        }
      }
    } catch (error) {
      console.error('[DiagnosisPage] Initialization error:', error);
      this.handleError(error);
    } finally {
      hideLoading();
    }
  },

  /**
   * 开始轮询
   */
  async startPolling() {
    console.log('[DiagnosisPage] Starting polling...');
    this.setData({ isPolling: true });

    try {
      // 启动轮询
      diagnosisService.startPolling({
        onStatus: this.handleStatusUpdate.bind(this),
        onComplete: this.handleComplete.bind(this),
        onError: this.handlePollingError.bind(this),
        onTimeout: this.handleTimeout.bind(this)
      });

      // 启动计时器
      this.startElapsedTimer();
      
      console.log('[DiagnosisPage] Polling started successfully');
    } catch (error) {
      console.error('[DiagnosisPage] Failed to start polling:', error);
      throw error;
    }
  },

  /**
   * 停止轮询
   */
  stopPolling() {
    console.log('[DiagnosisPage] Stopping polling...');
    diagnosisService.stopPolling();
    this.setData({ isPolling: false });
    this.stopElapsedTimer();
  },

  /**
   * 暂停轮询
   */
  pausePolling() {
    console.log('[DiagnosisPage] Pausing polling...');
    diagnosisService.pausePolling();
    this.setData({ isPolling: false });
    this.stopElapsedTimer();
  },

  /**
   * 恢复轮询
   */
  resumePolling() {
    console.log('[DiagnosisPage] Resuming polling...');
    if (this.data.executionId && !this.data.isPolling) {
      diagnosisService.resumePolling();
      this.setData({ isPolling: true });
      this.startElapsedTimer();
    }
  },

  /**
   * 刷新状态
   */
  async refreshStatus() {
    console.log('[DiagnosisPage] Refreshing status...');
    try {
      const status = await diagnosisService.getStatus(this.data.executionId);
      this.handleStatusUpdate(status);
      showToast({
        title: '刷新成功',
        icon: 'success'
      });
    } catch (error) {
      console.error('[DiagnosisPage] Refresh failed:', error);
      showToast({
        title: '刷新失败，请稍后重试',
        icon: 'none'
      });
    } finally {
      wx.stopPullDownRefresh();
    }
  },

  /**
   * 处理状态更新
   * @param {Object} status 
   */
  handleStatusUpdate(status) {
    console.log('[DiagnosisPage] Status update:', status);

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
    console.log('[DiagnosisPage] Task completed:', result);
    this.stopPolling();

    // 显示成功提示
    showToast({
      title: '诊断完成',
      icon: 'success',
      duration: 2000
    });

    // 跳转到报告页面
    setTimeout(() => {
      wx.navigateTo({
        url: `/pages/report/report?executionId=${this.data.executionId}`
      });
    }, 1500);
  },

  /**
   * 处理轮询错误
   * @param {Object} error 
   */
  handlePollingError(error) {
    console.error('[DiagnosisPage] Polling error:', error);

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
    console.warn('[DiagnosisPage] Task timeout:', timeoutInfo);
    this.stopPolling();

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
    console.log('[DiagnosisPage] Loading history report:', reportId);
    showLoading('加载中...');

    try {
      // 这里应该调用获取历史报告的 API
      // 暂时直接跳转到报告页面
      wx.navigateTo({
        url: `/pages/report/report?reportId=${reportId}`
      });
    } catch (error) {
      console.error('[DiagnosisPage] Failed to load history report:', error);
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
    console.error('[DiagnosisPage] Error:', error);
    logError(error, {
      context: 'diagnosisPage',
      executionId: this.data.executionId
    });

    // 使用统一错误提示组件
    const handled = handleApiError(error);
    
    this.setData({
      showErrorToast: true,
      errorType: handled.type,
      errorTitle: handled.title,
      errorMessage: handled.message,
      errorDetail: error.detail || '',
      errorCode: handled.code,
      showRetry: handled.retryable,
      showCancel: false
    });
  },

  /**
   * 关闭错误提示
   */
  onErrorClose() {
    this.setData({
      showErrorToast: false,
      errorMessage: ''
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
    console.log('[DiagnosisPage] User clicked retry');
    
    // 关闭错误提示
    this.setData({
      showErrorToast: false,
      errorMessage: '',
      retryCount: 0
    });
    
    this.startPolling();
  },

  /**
   * 用户操作：取消
   */
  async onCancel() {
    console.log('[DiagnosisPage] User clicked cancel');
    const confirmed = await showModal({
      title: '确认取消',
      content: '确定要取消当前诊断吗？已获取的结果不会丢失。',
      confirmText: '确定',
      cancelText: '继续'
    });

    if (confirmed) {
      this.stopPolling();
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
  }
});
