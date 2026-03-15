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
        const pending = diagnosisService.restoreFromStorage();
        if (pending && pending.executionId) {
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
      // 启动轮询，传入 executionId
      diagnosisService.startPolling({
        onStatus: this.handleStatusUpdate.bind(this),
        onComplete: this.handleComplete.bind(this),
        onError: this.handlePollingError.bind(this),
        onTimeout: this.handleTimeout.bind(this)
      }, this.data.executionId);

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
    this.stopPolling();
  },

  /**
   * 恢复轮询
   */
  resumePolling() {
    console.log('[DiagnosisPage] Resuming polling...');
    if (this.data.executionId && !this.data.isPolling) {
      this.startPolling();
    }
  },

  /**
   * 刷新状态
   */
  async refreshStatus() {
    console.log('[DiagnosisPage] Refreshing status...');
    try {
      // 重新连接 WebSocket 或轮询
      diagnosisService.startPolling({
        onStatus: this.handleStatusUpdate.bind(this),
        onComplete: this.handleComplete.bind(this),
        onError: this.handlePollingError.bind(this),
        onTimeout: this.handleTimeout.bind(this)
      }, this.data.executionId);

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

    // 【P0 优化 - 2026-03-09】检测到失败状态立即停止轮询并跳转
    if (status.status === 'failed' || status.status === 'timeout') {
      console.warn('[DiagnosisPage] ⚠️ 检测到失败状态，停止轮询并显示错误页面');
      this.stopPolling();
      this._handleFailedStatus(status);
      return;
    }

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
   * 【P0 优化 - 2026-03-09】处理失败状态
   * @private
   * @param {Object} status
   */
  _handleFailedStatus(status) {
    console.log('[DiagnosisPage] Handling failed status:', status);

    // 【P1 修复 - 2026-03-09】显示可关闭的错误提示，允许用户查看已有结果
    this.setData({
      showErrorToast: true,
      errorType: 'error',
      errorTitle: '诊断失败',
      errorDetail: status.error_message || '诊断过程中遇到错误，但可能已有部分结果可供查看',
      errorCode: status.error_code || '',
      showRetry: true,
      showCancel: false,  // 不显示取消按钮，避免用户误操作丢失结果
      showConfirm: true,  // 显示确认按钮
      confirmText: '查看结果',  // 确认按钮文本
      allowClose: true     // 允许关闭
    });

    // 更新页面标题
    wx.setNavigationBarTitle({
      title: '诊断失败'
    });
  },

  /**
   * 处理完成
   * @param {Object} result
   */
  async handleComplete(result) {
    console.log('[DiagnosisPage] Task completed:', result);
    this.stopPolling();

    // 【P0 关键修复 - 2026-03-13 第 15 次】确保数据保存完成后再跳转
    // 使用 Promise 确保异步操作完成
    
    try {
      // 1. 从 result 中提取原始数据
      const rawResults = result.detailed_results || result.results || result.data?.detailed_results || result.data?.results || [];

      console.log('[DiagnosisPage] 提取的原始数据:', {
        count: rawResults.length,
        hasData: rawResults.length > 0
      });

      if (rawResults && rawResults.length > 0) {
        // 2. 导入数据处理函数
        const { generateDashboardData } = require('../../../services/brandTestService');

        // 3. 生成看板数据
        const dashboardData = generateDashboardData(rawResults, {
          brandName: this.data.brandName || '',
          competitorBrands: this.data.competitorBrands || []
        });

        console.log('[DiagnosisPage] 看板数据生成完成:', {
          hasBrandDistribution: !!(dashboardData?.brandDistribution && Object.keys(dashboardData.brandDistribution).length > 0),
          hasSentimentDistribution: !!(dashboardData?.sentimentDistribution && Object.keys(dashboardData.sentimentDistribution).length > 0),
          keywordsCount: dashboardData?.keywords?.length || 0
        });

        // 4. 【P0 关键】保存到 globalData（使用 Promise 确保完成）
        await this._saveToGlobalData(dashboardData, rawResults);

        // 5. 【P0 关键】备份到 Storage（作为额外保障）
        await this._backupToStorage(dashboardData, rawResults);

        console.log('[DiagnosisPage] ✅ 数据保存完成');
      } else {
        console.warn('[DiagnosisPage] ⚠️ 没有可用的原始结果数据');
      }
    } catch (error) {
      console.error('[DiagnosisPage] ❌ 数据处理失败:', error);
      console.error('[DiagnosisPage] 错误堆栈:', error.stack);
      
      // 数据处理失败，显示错误提示
      this._showDataProcessingError(error);
      return; // 不执行跳转
    }

    // 【P0 关键修复】显示成功提示，等待用户准备后再跳转
    showToast({
      title: '诊断完成',
      icon: 'success',
      duration: 1500
    });

    // 【P0 关键】等待提示显示完成后再跳转
    setTimeout(() => {
      console.log('[DiagnosisPage] 跳转到报告页');
      wx.navigateTo({
        url: `/pages/report-v2/report-v2?executionId=${this.data.executionId}`
      });
    }, 1500);
  },

  /**
   * 【P0 新增】保存到 globalData
   */
  async _saveToGlobalData(dashboardData, rawResults) {
    return new Promise((resolve, reject) => {
      try {
        const app = getApp();
        if (app && app.globalData) {
          app.globalData.pendingReport = {
            executionId: this.data.executionId,
            dashboardData: dashboardData,
            rawResults: rawResults,
            timestamp: Date.now(),
            saved: true  // 标记已保存
          };
          console.log('[DiagnosisPage] ✅ 数据已保存到 globalData.pendingReport');
          resolve();
        } else {
          console.warn('[DiagnosisPage] ⚠️ getApp() 或 globalData 不可用');
          reject(new Error('globalData 不可用'));
        }
      } catch (error) {
        reject(error);
      }
    });
  },

  /**
   * 【P0 新增】备份到 Storage
   */
  async _backupToStorage(dashboardData, rawResults) {
    return new Promise((resolve, reject) => {
      try {
        wx.setStorageSync(`diagnosis_result_${this.data.executionId}`, {
          executionId: this.data.executionId,
          dashboardData: dashboardData,
          rawResults: rawResults,
          timestamp: Date.now(),
          saved: true  // 标记已保存
        });
        console.log('[DiagnosisPage] ✅ 数据已备份到 Storage');
        resolve();
      } catch (storageErr) {
        console.warn('[DiagnosisPage] ⚠️ Storage 备份失败:', storageErr);
        resolve(); // 备份失败不影响主流程
      }
    });
  },

  /**
   * 【P0 新增】显示数据处理错误
   */
  _showDataProcessingError(error) {
    showModal({
      title: '数据处理失败',
      content: `诊断完成但数据处理失败：${error.message}\n\n建议：\n1. 点击"重试"重新处理数据\n2. 点击"取消"返回重新开始`,
      showCancel: true,
      confirmText: '重试',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 重试逻辑
          this._retryDataProcessing();
        } else {
          // 返回
          wx.navigateBack();
        }
      }
    });
  },

  /**
   * 【P0 新增】重试数据处理
   */
  async _retryDataProcessing() {
    console.log('[DiagnosisPage] 重试数据处理');
    // 重新获取数据并处理
    try {
      const result = await diagnosisService.getStatus(this.data.executionId);
      await this.handleComplete(result);
    } catch (error) {
      this._showDataProcessingError(error);
    }
  },

  /**
   * 处理轮询错误
   * @param {Object} error
   */
  handlePollingError(error) {
    console.error('[DiagnosisPage] Polling error:', error);

    // 【P0 优化 - 2026-03-09】如果是任务失败错误，直接显示失败页面
    if (error.type === 'TASK_FAILED' || error.status === 'failed') {
      console.warn('[DiagnosisPage] ⚠️ 任务失败错误，显示失败页面');
      this._handleFailedStatus({
        status: error.status || 'failed',
        error_message: error.message || '诊断任务失败',
        error_code: error.error_code || ''
      });
      this.stopPolling();
      return;
    }

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

    // 【P1 修复 - 2026-03-09】超时不阻塞用户，显示可关闭的错误提示
    this.setData({
      showErrorToast: true,
      errorType: 'timeout',
      errorTitle: '诊断超时',
      errorDetail: timeoutInfo.message || '诊断任务执行时间过长，但可能已有部分结果',
      errorCode: '',
      showRetry: true,
      showCancel: true,
      showConfirm: false,  // 不显示确认按钮
      allowClose: true     // 允许关闭
    });

    // 更新页面标题
    wx.setNavigationBarTitle({
      title: '诊断超时'
    });
  },

  /**
   * 加载历史报告
   * @param {string} reportId - 报告 ID 或 executionId
   */
  async loadHistoryReport(reportId) {
    console.log('[DiagnosisPage] 加载历史报告:', reportId);
    
    // 【死循环修复 - 2026-03-14】防止重复加载
    if (this._isLoadingHistory) {
      console.warn('[DiagnosisPage] ⚠️ 正在加载中，跳过重复请求');
      return;
    }
    
    showLoading('加载中...');
    this._isLoadingHistory = true;

    try {
      // 1. 优先从本地缓存加载（P0-08 修复版 - 带 TTL 检查）
      const cachedData = this._getHistoryReportFromCache(reportId);
      if (cachedData && cachedData.executionId) {
        console.log('[DiagnosisPage] ✅ 从本地缓存加载历史报告');

        // 跳转到报告页，传递缓存数据
        const app = getApp();
        if (app && app.globalData) {
          app.globalData.pendingReport = {
            executionId: cachedData.executionId,
            dashboardData: cachedData.dashboardData,
            rawResults: cachedData.rawResults,
            timestamp: cachedData.timestamp,
            isHistory: true  // 标记为历史数据
          };
        }

        hideLoading();
        this._isLoadingHistory = false;
        wx.navigateTo({
          url: `/pages/report-v2/report-v2?executionId=${cachedData.executionId}`
        });
        return;
      }

      // 2. 从服务器加载
      console.log('[DiagnosisPage] 从服务器加载历史报告');
      const reportService = require('../../services/reportService').default;
      const report = await reportService.getFullReport(reportId);

      if (report && report.brandDistribution && report.brandDistribution.data) {
        console.log('[DiagnosisPage] ✅ 服务器加载成功');

        // 处理数据
        const { generateDashboardData } = require('../../../services/brandTestService');
        const rawResults = report.results || report.detailed_results || [];
        const dashboardData = generateDashboardData(rawResults, {
          brandName: report.brandName || '',
          competitorBrands: report.competitorBrands || []
        });

        // 保存到全局变量
        const app = getApp();
        if (app && app.globalData) {
          app.globalData.pendingReport = {
            executionId: report.executionId || reportId,
            dashboardData: dashboardData,
            rawResults: rawResults,
            timestamp: Date.now(),
            isHistory: true
          };
          console.log('[DiagnosisPage] ✅ 数据已保存到 globalData.pendingReport');
        }

        // 缓存到本地（P0-08 修复版 - 带 TTL）
        this._saveHistoryReportToCache(reportId, {
          executionId: report.executionId || reportId,
          dashboardData: dashboardData,
          rawResults: rawResults,
          timestamp: Date.now()
        });
        console.log('[DiagnosisPage] ✅ 数据已缓存到本地');

        hideLoading();
        this._isLoadingHistory = false;
        wx.navigateTo({
          url: `/pages/report-v2/report-v2?executionId=${report.executionId || reportId}`
        });
      } else {
        console.warn('[DiagnosisPage] ⚠️ 报告数据不完整');
        throw new Error('报告数据不完整');
      }
    } catch (error) {
      console.error('[DiagnosisPage] ❌ 加载历史报告失败:', error);
      hideLoading();
      this._isLoadingHistory = false;

      // 【死循环修复 - 2026-03-14】使用页面导航而非递归调用
      wx.showModal({
        title: '加载失败',
        content: error.message || '无法加载历史报告，请稍后重试',
        showCancel: true,
        confirmText: '重试',
        cancelText: '返回',
        success: (res) => {
          if (res.confirm) {
            // 【修复】使用页面重新加载而非递归调用
            const pages = getCurrentPages();
            const currentPage = pages[pages.length - 1];
            if (currentPage && currentPage.options && currentPage.options.reportId) {
              currentPage.onLoad(currentPage.options);
            }
          } else {
            wx.navigateBack();
          }
        }
      });
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

    // 【P0 优化 - 2026-03-09】重试前重置 WebSocket 的永久失败标志
    const webSocketClient = require('../../services/webSocketClient').default;
    if (webSocketClient && typeof webSocketClient.resetPermanentFailure === 'function') {
      webSocketClient.resetPermanentFailure();
    }

    // 关闭错误提示
    this.setData({
      showErrorToast: false,
      errorMessage: '',
      retryCount: 0
    });

    // 重新启动轮询
    this.startPolling();
  },

  /**
   * 【P1 新增 - 2026-03-09】用户操作：确认（查看结果）
   */
  onConfirm() {
    console.log('[DiagnosisPage] User clicked confirm, navigating to report');

    // 关闭错误提示
    this.setData({
      showErrorToast: false
    });

    // 跳转到报告页面，尝试查看已有结果
    wx.navigateTo({
      url: `/pages/report-v2/report-v2?executionId=${this.data.executionId}`
    });
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
  },

  /**
   * 【P0-08 新增 - 2026-03-14】从缓存获取历史报告（带 TTL 检查）
   * @param {string} reportId - 报告 ID
   * @returns {Object|null} 缓存的数据，不存在或已过期则返回 null
   * @private
   */
  _getHistoryReportFromCache(reportId) {
    const cacheKey = `history_report_${reportId}`;
    const CACHE_TTL = 7 * 24 * 60 * 60 * 1000; // 7 天缓存 TTL

    try {
      const cachedData = wx.getStorageSync(cacheKey);
      if (!cachedData) {
        return null;
      }

      // 检查是否过期
      const now = Date.now();
      const cacheAge = now - cachedData.timestamp;

      if (cacheAge > CACHE_TTL) {
        console.log('[DiagnosisPage] ⏰ 缓存已过期，清理:', cacheKey);
        wx.removeStorageSync(cacheKey);
        return null;
      }

      // 计算剩余时间
      const remainingTime = CACHE_TTL - cacheAge;
      const remainingHours = Math.round(remainingTime / (1000 * 60 * 60));

      console.log(
        '[DiagnosisPage] ✅ 缓存命中:', cacheKey,
        `剩余时间：${remainingHours}小时`
      );

      return cachedData;

    } catch (error) {
      console.error('[DiagnosisPage] ❌ 读取缓存失败:', error);
      return null;
    }
  },

  /**
   * 【P0-08 新增 - 2026-03-14】保存历史报告到缓存（带 TTL 标记）
   * @param {string} reportId - 报告 ID
   * @param {Object} data - 要缓存的数据
   * @private
   */
  _saveHistoryReportToCache(reportId, data) {
    const cacheKey = `history_report_${reportId}`;
    const CACHE_TTL = 7 * 24 * 60 * 60 * 1000; // 7 天缓存 TTL

    try {
      const cacheData = {
        ...data,
        expiresAt: Date.now() + CACHE_TTL, // 过期时间戳
        ttl: CACHE_TTL // TTL 毫秒数
      };

      wx.setStorageSync(cacheKey, cacheData);

      const expiresAt = new Date(cacheData.expiresAt);
      console.log(
        '[DiagnosisPage] ✅ 缓存已保存:', cacheKey,
        `过期时间：${expiresAt.toLocaleString('zh-CN')}`
      );

    } catch (error) {
      console.error('[DiagnosisPage] ❌ 保存缓存失败:', error);
    }
  },

  /**
   * 【P0-08 新增 - 2026-03-14】清理过期历史报告缓存
   * @private
   */
  _cleanupExpiredHistoryCache() {
    const CACHE_TTL = 7 * 24 * 60 * 60 * 1000; // 7 天缓存 TTL
    const now = Date.now();
    let cleanedCount = 0;

    try {
      // 获取所有缓存键
      const info = wx.getStorageInfoSync();
      const keys = info.keys || [];

      for (const key of keys) {
        if (key.startsWith('history_report_')) {
          try {
            const cachedData = wx.getStorageSync(key);
            if (cachedData && cachedData.timestamp) {
              const cacheAge = now - cachedData.timestamp;
              if (cacheAge > CACHE_TTL) {
                wx.removeStorageSync(key);
                cleanedCount++;
                console.log('[DiagnosisPage] 🗑️ 清理过期缓存:', key);
              }
            }
          } catch (err) {
            console.warn('[DiagnosisPage] ⚠️ 清理缓存失败:', key, err);
          }
        }
      }

      if (cleanedCount > 0) {
        console.log('[DiagnosisPage] ✅ 清理完成，共清理', cleanedCount, '个过期缓存');
      }

    } catch (error) {
      console.error('[DiagnosisPage] ❌ 清理缓存失败:', error);
    }
  }
});
