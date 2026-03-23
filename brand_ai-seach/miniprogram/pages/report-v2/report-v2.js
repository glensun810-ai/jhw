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
    pollingStartTime: null,
    // 【P0 修复 - 2026-03-13】页面卸载标志
    _isPageUnloaded: false
  },

  /**
   * 【P0 修复 - 2026-03-13】安全的 setData 方法
   * 防止在页面卸载后调用 setData
   * @param {Object} data 要设置的数据
   * @param {Function} callback 回调函数
   */
  safeSetData(data, callback) {
    if (this._isPageUnloaded) {
      console.warn('[ReportPageV2] ⚠️ 页面已卸载，跳过 setData');
      if (callback) callback();
      return;
    }
    
    this.setData(data, callback);
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
    
    // 标记页面已卸载，防止后续 setData
    this._isPageUnloaded = true;
    
    // 停止所有监听和定时器
    this.stopListening();
    this.stopElapsedTimer();
    
    // 清理可能的延迟回调
    if (this._pendingTimeout) {
      clearTimeout(this._pendingTimeout);
      this._pendingTimeout = null;
    }
    
    console.log('[ReportPageV2] ✅ Cleanup completed');
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
    console.log('[ReportPageV2] initPage, executionId:', options.executionId);

    // 设置加载状态，显示骨架屏
    this.setData({ isLoading: true });

    try {
      // 【P0 关键修复 - 2026-03-13 第 15 次】多数据源降级加载策略
      
      // 尝试 1: 检查全局变量（诊断刚完成）
      const app = getApp();
      if (app && app.globalData && app.globalData.pendingReport) {
        const pendingReport = app.globalData.pendingReport;
        
        if (pendingReport.executionId === options.executionId && pendingReport.saved) {
          console.log('[ReportPageV2] ✅ [尝试 1] 全局变量匹配，直接加载数据');
          this._loadFromGlobalData(pendingReport);
          return;  // 成功则不再执行后续
        }
      }

      // 尝试 2: 检查 Storage 备份
      const storageData = this._loadFromStorage(options.executionId);
      if (storageData && storageData.saved) {
        console.log('[ReportPageV2] ✅ [尝试 2] Storage 备份可用，加载数据');
        this._loadFromStorageData(storageData);
        return;  // 成功则不再执行后续
      }

      // 尝试 3: 从 API 获取
      console.log('[ReportPageV2] ⏳ [尝试 3] 从 API 获取报告...');
      this.setData({ 
        dataSource: 'api',
        executionId: options.executionId,
        reportId: options.reportId
      });
      
      await this._loadFromAPI(options.executionId);
      
    } catch (error) {
      console.error('[ReportPageV2] ❌ 所有数据源加载失败:', error);
      this._handleLoadError(error);
    }
  },

  /**
   * 【P0 新增】从 globalData 加载
   */
  _loadFromGlobalData(pendingReport) {
    this.setData({
      executionId: pendingReport.executionId,
      brandDistribution: pendingReport.dashboardData?.brandDistribution || {},
      sentimentDistribution: pendingReport.dashboardData?.sentimentDistribution || {},
      keywords: pendingReport.dashboardData?.keywords || [],
      brandScores: pendingReport.dashboardData?.brandScores || {},
      isLoading: false,
      hasError: false,
      dataSource: 'globalData'
    });
    console.log('[ReportPageV2] ✅ 从 globalData 加载成功');
  },

  /**
   * 【P0 新增】从 Storage 加载
   */
  _loadFromStorageData(storageData) {
    this.setData({
      executionId: storageData.executionId,
      brandDistribution: storageData.dashboardData?.brandDistribution || {},
      sentimentDistribution: storageData.dashboardData?.sentimentDistribution || {},
      keywords: storageData.dashboardData?.keywords || [],
      brandScores: storageData.dashboardData?.brandScores || {},
      isLoading: false,
      hasError: false,
      dataSource: 'storage'
    });
    console.log('[ReportPageV2] ✅ 从 Storage 加载成功');
  },

  /**
   * 【P0 新增】从 Storage 加载辅助方法
   */
  _loadFromStorage(executionId) {
    try {
      const key = `diagnosis_result_${executionId}`;
      const data = wx.getStorageSync(key);
      return data || null;
    } catch (error) {
      console.warn('[ReportPageV2] ⚠️ Storage 加载失败:', error);
      return null;
    }
  },

  /**
   * 【P0 新增】从 API 加载（增强版 - 2026-03-13 第 18 次）
   * 【P0 修复 - 2026-03-15】增强数据验证，检测空数据场景
   * 【P0 关键修复 - 2026-03-20】优化错误处理，显示诊断失败卡片而非空白页面
   */
  async _loadFromAPI(executionId) {
    try {
      const report = await diagnosisService.getFullReport(executionId);

      // 【P0 关键修复 - 2026-03-20】检查后端返回的错误标志
      const isEmptyData = report?.validation?.is_empty_data || 
                          report?.qualityHints?.is_empty_data ||
                          report?.error?.is_empty_data;
      
      if (isEmptyData) {
        console.error('[ReportPageV2] ❌ 后端明确返回空数据标志:', {
          executionId,
          error: report?.error,
          validation: report?.validation
        });
        
        // 提取错误信息
        const errorMsg = report?.error?.message || 
                         report?.validation?.errors?.[0] || 
                         report?.qualityHints?.warnings?.[0] ||
                         '诊断数据为空，请尝试重新诊断';
        
        // 提取恢复建议
        const recoveryActions = report?.error?.recovery_actions || 
                                report?.detail?.recovery_actions || [];
        
        // 显示错误卡片而非空白页面
        this._showDiagnosisFailureCard({
          errorMessage: errorMsg,
          errorType: 'empty_data',
          recoveryActions: recoveryActions,
          executionId: executionId
        });
        return;
      }

      // 【P0 关键修复 - 第 18 次】即使有部分成功标志，也展示数据
      // 【P0 修复 - 2026-03-15】增强验证：检查 brandDistribution.data 是否为空
      const hasValidBrandData = report?.brandDistribution?.data &&
                                 Object.keys(report.brandDistribution.data).length > 0;
      const hasResults = report?.results && report.results.length > 0;

      if (report && hasValidBrandData) {
        this.setData({
          brandDistribution: report.brandDistribution,
          sentimentDistribution: report.sentimentDistribution,
          keywords: report.keywords,
          brandScores: report.brandScores,
          isLoading: false,
          hasError: false,
          dataSource: 'api',
          // 显示部分成功提示
          hasPartialData: report.partialSuccess || report.hasPartialData || false,
          qualityWarnings: report.qualityWarnings || report.validationWarnings || []
        });

        console.log('[ReportPageV2] ✅ 从 API 加载成功:', {
          hasPartialData: this.data.hasPartialData,
          warningsCount: (report.qualityWarnings || []).length,
          brandDataCount: Object.keys(report.brandDistribution.data).length,
          resultsCount: report.results?.length || 0
        });

        // 【P0 关键】如果有警告，显示提示但不阻止使用
        if (this.data.hasPartialData || (report.qualityWarnings?.length > 0)) {
          this._showPartialDataWarning(report.qualityWarnings);
        }
      } else if (report?.error) {
        // 【P0 修复 - 2026-03-15】后端返回了错误对象
        console.warn('[ReportPageV2] ⚠️ 后端返回错误:', report.error);
        
        // 【P0 关键修复 - 2026-03-20】显示错误卡片
        this._showDiagnosisFailureCard({
          errorMessage: report.error.message || '诊断执行失败',
          errorType: report.error.status || 'business_error',
          recoveryActions: report.error.recovery_actions || [],
          fallbackInfo: report.error.fallback_info || {},
          executionId: executionId
        });
      } else if (!hasValidBrandData && !hasResults) {
        // 【P0 修复 - 2026-03-15】数据完全为空
        console.error('[ReportPageV2] ❌ 报告数据完全为空:', {
          hasBrandData: !!hasValidBrandData,
          hasResults: !!hasResults,
          brandDistribution: report?.brandDistribution
        });
        
        // 【P0 关键修复 - 2026-03-20】显示错误卡片而非抛出异常
        this._showDiagnosisFailureCard({
          errorMessage: '无法加载报告数据：后端返回数据为空',
          errorType: 'empty_data',
          recoveryActions: [
            '点击"重试"重新加载',
            '点击"重新诊断"创建新任务',
            '查看历史报告记录'
          ],
          executionId: executionId
        });
      } else {
        // 只有 results 但没有 brandDistribution，尝试使用 results
        console.warn('[ReportPageV2] ⚠️ 有 results 但无 brandDistribution，尝试重建');
        this._rebuildBrandDistributionFromResults(report);
      }
    } catch (error) {
      console.error('[ReportPageV2] ❌ API 加载失败:', error);
      
      // 【P0 关键修复 - 2026-03-20】区分网络错误和数据错误，显示友好卡片
      const errorType = error.code === 'NETWORK_ERROR' || error.message.includes('网络')
        ? 'network_error'
        : (error.code === 'EMPTY_DATA' || error.message.includes('为空') ? 'empty_data' : 'unknown');
      
      this._showDiagnosisFailureCard({
        errorMessage: error.message || '数据加载失败',
        errorType: errorType,
        recoveryActions: [
          '检查网络连接',
          '点击"重试"重新加载',
          '点击"重新诊断"创建新任务'
        ],
        executionId: executionId
      });
    }
  },

  /**
   * 【P0 修复 - 2026-03-15】从 results 重建 brandDistribution
   */
  _rebuildBrandDistributionFromResults(report) {
    try {
      const results = report.results || [];
      if (!results || results.length === 0) {
        throw new Error('results 为空，无法重建品牌分布');
      }

      // 从 results 中提取品牌分布
      const brandData = {};
      results.forEach(result => {
        const brand = result.extractedBrand || result.brand || result.extracted_brand || result.brand;
        if (brand) {
          brandData[brand] = (brandData[brand] || 0) + 1;
        }
      });

      if (Object.keys(brandData).length === 0) {
        throw new Error('无法从 results 中提取品牌信息');
      }

      // 重建 brandDistribution
      const brandDistribution = {
        data: brandData,
        totalCount: results.length,
        successRate: 1.0
      };

      this.setData({
        brandDistribution,
        sentimentDistribution: report.sentimentDistribution || { data: {}, totalCount: 0 },
        keywords: report.keywords || [],
        brandScores: report.brandScores || {},
        isLoading: false,
        hasError: false,
        dataSource: 'api',
        hasPartialData: true,
        qualityWarnings: ['品牌分布数据已重建，部分分析数据可能缺失']
      });

      console.log('[ReportPageV2] ✅ 从 results 重建 brandDistribution 成功:', {
        brandCount: Object.keys(brandData).length,
        resultsCount: results.length
      });

      this._showPartialDataWarning(['品牌分布数据已重建，部分分析数据可能缺失']);

    } catch (rebuildError) {
      console.error('[ReportPageV2] ❌ 重建 brandDistribution 失败:', rebuildError);
      throw new Error('报告数据不完整：' + rebuildError.message);
    }
  },

  /**
   * 【P0 新增 - 第 18 次】显示部分成功警告
   */
  _showPartialDataWarning(warnings) {
    showModal({
      title: '数据不完整提示',
      content: `诊断数据部分成功，但已有结果可供查看。\n\n` +
               `提示：${warnings?.join('\n') || '数据可能存在缺失'}\n\n` +
               `建议：\n` +
               `1. 点击"查看结果"查看已有数据\n` +
               `2. 点击"重新诊断"获取完整报告`,
      showCancel: true,
      confirmText: '查看结果',
      cancelText: '重新诊断',
      success: (res) => {
        if (res.confirm) {
          // 查看结果，关闭对话框
        } else {
          // 重新诊断
          wx.navigateTo({
            url: '/pages/diagnosis/diagnosis'
          });
        }
      }
    });
  },

  /**
   * 【P0 关键修复 - 2026-03-20】显示诊断失败卡片
   * 当数据为空或诊断失败时，显示友好的错误卡片而非空白页面
   * @param {Object} options - 配置选项
   * @param {string} options.errorMessage - 错误信息
   * @param {string} options.errorType - 错误类型 (empty_data, network_error, business_error, unknown)
   * @param {Array} options.recoveryActions - 恢复建议列表
   * @param {Object} options.fallbackInfo - 降级信息（包含图标、操作等）
   * @param {string} options.executionId - 执行 ID
   */
  _showDiagnosisFailureCard(options) {
    const {
      errorMessage,
      errorType = 'unknown',
      recoveryActions = [],
      fallbackInfo = {},
      executionId
    } = options;

    console.log('[ReportPageV2] 显示诊断失败卡片:', { errorType, errorMessage });

    // 【P0 关键修复 - 骨架屏管理】确保骨架屏保持显示直到错误 UI 渲染完成
    // 先停止加载状态，但不立即隐藏骨架屏
    this.setData({
      isLoading: false,
      hasError: true,
      errorMessage: errorMessage,
      errorType: errorType,
      recoveryActions: recoveryActions,
      fallbackInfo: fallbackInfo,
      executionId: executionId,
      // 【P0 关键修复】显示错误内容卡片
      showErrorCard: true,
      // 错误卡片配置
      errorCardConfig: this._getErrorCardConfig(errorType, errorMessage, recoveryActions, fallbackInfo)
    }, () => {
      // 【P0 关键修复】在 setData 完成后才显示错误提示
      console.log('[ReportPageV2] ✅ 错误卡片渲染完成');
    });
  },

  /**
   * 【P0 关键修复 - 2026-03-20】获取错误卡片配置
   * 根据错误类型返回对应的图标、标题、建议等
   */
  _getErrorCardConfig(errorType, errorMessage, recoveryActions, fallbackInfo) {
    const configMap = {
      empty_data: {
        icon: 'warning',
        iconColor: '#ff9900',
        title: '诊断数据为空',
        subtitle: '诊断已完成但未生成有效数据',
        tips: [
          '可能原因：AI 调用失败或数据保存失败',
          '建议查看后端日志获取详细错误信息'
        ],
        primaryAction: {
          text: '重新诊断',
          type: 'navigate',
          url: '/pages/diagnosis/diagnosis'
        },
        secondaryAction: {
          text: '查看历史',
          type: 'navigate',
          url: '/pages/history/history'
        }
      },
      network_error: {
        icon: 'wifi-off',
        iconColor: '#ff4444',
        title: '网络连接失败',
        subtitle: '无法连接到诊断服务',
        tips: [
          '请检查网络连接是否正常',
          '确认后端服务是否启动',
          '开发者工具中确认 serverUrl 配置'
        ],
        primaryAction: {
          text: '重试',
          type: 'retry'
        },
        secondaryAction: {
          text: '返回首页',
          type: 'navigate',
          url: '/pages/index/index'
        }
      },
      failed: {
        icon: 'error',
        iconColor: '#ff4444',
        title: '诊断执行失败',
        subtitle: fallbackInfo.title || '诊断过程中遇到错误',
        tips: [
          errorMessage,
          ...(fallbackInfo.description ? [fallbackInfo.description] : [])
        ],
        primaryAction: {
          text: '重新诊断',
          type: 'navigate',
          url: '/pages/diagnosis/diagnosis'
        },
        secondaryAction: {
          text: '查看错误详情',
          type: 'show_error_details'
        }
      },
      timeout: {
        icon: 'time',
        iconColor: '#ff9900',
        title: '诊断超时',
        subtitle: '诊断处理时间过长',
        tips: [
          '诊断任务执行时间超过限制',
          '建议查看历史记录或重新尝试'
        ],
        primaryAction: {
          text: '继续等待',
          type: 'wait'
        },
        secondaryAction: {
          text: '查看历史',
          type: 'navigate',
          url: '/pages/history/history'
        }
      },
      not_found: {
        icon: 'search',
        iconColor: '#999999',
        title: '报告不存在',
        subtitle: '未找到对应的诊断报告',
        tips: [
          '可能原因：报告已被删除或从未创建',
          '建议重新创建诊断任务'
        ],
        primaryAction: {
          text: '重新诊断',
          type: 'navigate',
          url: '/pages/diagnosis/diagnosis'
        },
        secondaryAction: {
          text: '查看历史',
          type: 'navigate',
          url: '/pages/history/history'
        }
      }
    };

    // 使用预设配置或默认配置
    const defaultConfig = {
      icon: 'error',
      iconColor: '#ff4444',
      title: '数据加载失败',
      subtitle: '发生未知错误',
      tips: [errorMessage],
      primaryAction: {
        text: '重试',
        type: 'retry'
      },
      secondaryAction: {
        text: '返回首页',
        type: 'navigate',
        url: '/pages/index/index'
      }
    };

    const config = configMap[errorType] || defaultConfig;

    // 如果有 recoveryActions，添加到 tips
    if (recoveryActions && recoveryActions.length > 0) {
      config.tips = [
        ...config.tips,
        '建议操作：',
        ...recoveryActions.map(action => `• ${action}`)
      ];
    }

    return config;
  },

  /**
   * 【P0 新增 - 2026-03-13】分类错误类型
   * @param {Error} error - 错误对象
   * @returns {string} 错误类型
   * @private
   */
  _classifyError(error) {
    if (!error) return 'unknown';
    
    const msg = error.message || '';
    const code = error.code || '';
    
    // 网络错误
    if (msg.includes('timeout') || msg.includes('超时')) {
      return 'timeout';
    }
    if (msg.includes('无法连接') || msg.includes('fail')) {
      return 'network';
    }
    // API 错误
    if (code === 'REPORT_ERROR' || msg.includes('获取报告失败')) {
      return 'api';
    }
    // 数据错误
    if (msg.includes('数据') || msg.includes('report')) {
      return 'data';
    }
    // 默认未知错误
    return 'unknown';
  },

  /**
   * 【P0 新增】处理加载错误（增强版 - 2026-03-13 第 18 次）
   */
  _handleLoadError(error) {
    // 【P0 关键】先检查是否有缓存数据
    const cachedData = this._loadFromStorage(this.data.executionId);

    if (cachedData && cachedData.saved) {
      console.log('[ReportPageV2] ⚠️ API 加载失败，但有 Storage 备份');

      // 使用 Storage 数据
      this._loadFromStorageData(cachedData);

      // 显示降级提示
      this._showFallbackWarning('使用缓存数据');
      return;
    }

    // 真的没有数据，显示错误
    this.setData({
      isLoading: false,
      hasError: true,
      errorMessage: error.message || '数据加载失败',
      errorType: this._classifyError(error)
    });

    showModal({
      title: '数据加载失败',
      content: `无法加载报告数据：${error.message}\n\n` +
               `建议：\n` +
               `1. 点击"重试"重新加载\n` +
               `2. 点击"返回"重新开始诊断`,
      showCancel: true,
      confirmText: '重试',
      cancelText: '返回',
      success: (res) => {
        if (res.confirm) {
          this.initPage({ executionId: this.data.executionId });
        } else {
          wx.navigateBack();
        }
      }
    });
  },

  /**
   * 【P0 新增 - 第 18 次】显示降级提示
   */
  _showFallbackWarning(reason) {
    showToast({
      title: `${reason}，已加载缓存数据`,
      icon: 'none',
      duration: 2000
    });
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

    // 【修复 - 2026-03-12】移除 Toast 提示，避免阻挡用户操作
    // showToast({
    //   title: '实时推送已连接',
    //   icon: 'success',
    //   duration: 1500
    // });
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
    console.log('[ReportPageV2] 诊断完成');
    this.stopListening();

    // P1-6 简化：使用统一状态机
    this.setData({ connectionState: ConnectionState.COMPLETED });

    // 显示成功提示
    showToast({
      title: '诊断完成',
      icon: 'success',
      duration: 2000
    });

    // 【P0 关键修复 - 2026-03-11】立即从全局变量或 Storage 加载数据
    setTimeout(() => {
      const app = getApp();
      if (app && app.globalData && app.globalData.pendingReport) {
        const pendingReport = app.globalData.pendingReport;
        this.setData({
          brandDistribution: pendingReport.dashboardData?.brandDistribution || {},
          sentimentDistribution: pendingReport.dashboardData?.sentimentDistribution || {},
          keywords: pendingReport.dashboardData?.keywords || [],
          brandScores: pendingReport.dashboardData?.brandScores || {},
          hasError: false,
          dataSource: 'globalData'
        });
        console.log('[ReportPageV2] ✅ 从全局变量加载数据');
      } else {
        this.loadReportData(this.data.executionId);
      }
    }, 1500);
  },

  /**
   * 处理超时（P1-6 简化版）
   * @param {Object} timeoutInfo
   */
  async handleTimeout(timeoutInfo) {
    console.warn('[ReportPageV2] 诊断超时:', timeoutInfo);
    this.stopListening();

    // 【P1 修复 - 2026-03-09】超时不阻塞用户，显示可关闭的错误提示
    this.setData({
      showErrorToast: true,
      errorType: 'timeout',
      errorTitle: '诊断超时',
      errorDetail: timeoutInfo.message || '诊断任务执行时间过长，但可能已有部分结果可供查看',
      errorCode: '',
      showRetry: true,
      showCancel: false,
      showConfirm: false,
      allowClose: true
    });
  },

  /**
   * 加载历史报告
   * @param {string} reportId - 报告 ID 或 executionId
   */
  async loadHistoryReport(reportId) {
    console.log('[ReportPageV2] 加载历史报告:', reportId);
    
    // 【死循环修复 - 2026-03-14】防止重复加载
    if (this._isLoadingHistory) {
      console.warn('[ReportPageV2] ⚠️ 正在加载中，跳过重复请求');
      return;
    }
    
    showLoading('加载中...');
    this._isLoadingHistory = true;

    try {
      // 1. 检查全局变量（可能已从 diagnosis.js 传递）
      const app = getApp();
      if (app && app.globalData && app.globalData.pendingReport) {
        const pendingReport = app.globalData.pendingReport;
        if (pendingReport.executionId === reportId && pendingReport.isHistory) {
          console.log('[ReportPageV2] ✅ 从全局变量加载历史数据');
          this.setData({
            brandDistribution: pendingReport.dashboardData?.brandDistribution || {},
            sentimentDistribution: pendingReport.dashboardData?.sentimentDistribution || {},
            keywords: pendingReport.dashboardData?.keywords || [],
            brandScores: pendingReport.dashboardData?.brandScores || {},
            isHistoryData: true,
            hasError: false,
            dataSource: 'globalData'
          });
          hideLoading();
          this._isLoadingHistory = false;
          return;
        }
      }

      // 2. 从云函数加载
      console.log('[ReportPageV2] 从云函数加载历史报告');
      const reportService = require('../../../services/reportService');
      const report = await reportService.getFullReport(reportId);

      if (report && report.brandDistribution && report.brandDistribution.data) {
        console.log('[ReportPageV2] ✅ 云函数加载成功');
        this.setData({
          brandDistribution: report.brandDistribution || {},
          sentimentDistribution: report.sentimentDistribution || {},
          keywords: report.keywords || [],
          brandScores: report.brandScores || {},
          isHistoryData: true,
          hasError: false,
          dataSource: 'cloudFunction'
        });

        // 缓存到 Storage
        wx.setStorageSync(`history_report_${reportId}`, {
          executionId: report.executionId || reportId,
          dashboardData: {
            brandDistribution: report.brandDistribution,
            sentimentDistribution: report.sentimentDistribution,
            keywords: report.keywords,
            brandScores: report.brandScores
          },
          rawResults: report.results || [],
          timestamp: Date.now(),
          expiresAt: Date.now() + (7 * 24 * 60 * 60 * 1000) // 7 天后过期
        });
        console.log('[ReportPageV2] ✅ 数据已缓存到 Storage');

        hideLoading();
        this._isLoadingHistory = false;
      } else {
        console.warn('[ReportPageV2] ⚠️ 云函数返回数据不完整');
        throw new Error('报告数据不完整');
      }
    } catch (error) {
      console.error('[ReportPageV2] ❌ 加载历史报告失败:', error);
      hideLoading();
      this._isLoadingHistory = false;

      // 尝试从 Storage 加载备份
      const cachedData = wx.getStorageSync(`history_report_${reportId}`);
      if (cachedData && cachedData.dashboardData) {
        console.log('[ReportPageV2] ⚠️ 从 Storage 备份加载');
        this.setData({
          brandDistribution: cachedData.dashboardData.brandDistribution || {},
          sentimentDistribution: cachedData.dashboardData.sentimentDistribution || {},
          keywords: cachedData.dashboardData.keywords || [],
          brandScores: cachedData.dashboardData.brandScores || {},
          isHistoryData: true,
          fromBackup: true,
          hasError: false,
          dataSource: 'storage'
        });
      } else {
        this.setData({
          hasError: true,
          errorType: 'load_history_failed',
          errorMessage: error.message || '加载失败',
          errorDetail: '历史报告加载失败，请检查网络或稍后重试'
        });

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
              if (currentPage && currentPage.options && currentPage.options.executionId) {
                currentPage.onLoad(currentPage.options);
              }
            } else {
              wx.navigateBack();
            }
          }
        });
      }
    }
  },

  /**
   * 加载报告数据
   * @param {string} executionId - 执行 ID
   * @param {string} reportId - 报告 ID（可选）
   */
  async loadReportData(executionId, reportId) {
    console.log('[ReportPageV2] 加载报告数据，id:', executionId || reportId);

    try {
      const id = executionId || this.data.executionId;

      if (!id) {
        throw new Error('缺少执行 ID');
      }

      showLoading('加载报告中...');

      let report = null;
      let dataSource = 'unknown';

      // Step 1: 检查全局变量
      const app = getApp();
      if (app && app.globalData && app.globalData.pendingReport) {
        const pendingReport = app.globalData.pendingReport;
        if (pendingReport.executionId === id) {
          report = {
            brandDistribution: pendingReport.dashboardData?.brandDistribution || {},
            sentimentDistribution: pendingReport.dashboardData?.sentimentDistribution || {},
            keywords: pendingReport.dashboardData?.keywords || [],
            brandScores: pendingReport.dashboardData?.brandScores || {},
            status: 'completed',
            progress: 100,
            stage: 'completed'
          };
          dataSource = 'globalData';
        }
      }

      // Step 2: 从云函数获取
      if (!report || !report.brandDistribution || Object.keys(report.brandDistribution).length === 0) {
        console.log('[ReportPageV2] 从云函数获取报告，executionId:', id);
        const reportService = require('../../../services/reportService');
        const cloudReport = await reportService.getFullReport(id);

        console.log('[ReportPageV2] 云函数返回报告:', {
          hasCloudReport: !!cloudReport,
          hasBrandDistribution: !!(cloudReport?.brandDistribution),
          brandDistributionKeys: cloudReport?.brandDistribution ? Object.keys(cloudReport.brandDistribution) : [],
          hasSentimentDistribution: !!(cloudReport?.sentimentDistribution),
          hasKeywords: !!(cloudReport?.keywords),
          keywordsLength: cloudReport?.keywords?.length || 0,
          hasBrandScores: !!(cloudReport?.brandScores),
          validation: cloudReport?.validation,
          error: cloudReport?.error
        });

        if (cloudReport && cloudReport.brandDistribution && Object.keys(cloudReport.brandDistribution).length > 0) {
          report = {
            brandDistribution: cloudReport.brandDistribution || {},
            sentimentDistribution: cloudReport.sentimentDistribution || {},
            keywords: cloudReport.keywords || [],
            brandScores: cloudReport.brandScores || {},
            status: cloudReport.status || 'completed',
            progress: cloudReport.progress || 100,
            stage: cloudReport.stage || 'completed'
          };
          dataSource = 'cloudFunction';
        } else if (cloudReport?.error) {
          // 【P0 关键修复 - 2026-03-12】云函数返回错误时也要记录
          console.warn('[ReportPageV2] 云函数返回错误:', cloudReport.error);
        }
      }

      // Step 3: 从 Storage 读取备份
      if (!report || !report.brandDistribution || Object.keys(report.brandDistribution).length === 0) {
        const storageKey = 'diagnosis_result_' + id;
        const storageData = wx.getStorageSync(storageKey);

        if (storageData && storageData.executionId === id) {
          report = {
            brandDistribution: storageData.data?.brandDistribution || {},
            sentimentDistribution: storageData.data?.sentimentDistribution || {},
            keywords: storageData.data?.keywords || [],
            brandScores: storageData.data?.brandScores || {},
            status: 'completed',
            progress: 100,
            stage: 'completed'
          };
          dataSource = 'storage';
        }
      }

      hideLoading();

      // 检查是否获取到有效数据
      // 【P0 关键修复 - 2026-03-12 第 10 次】修改验证逻辑，支持_debug_info 兜底
      // 之前只检查 data 和 total_count，但如果后端返回_debug_info 说明计算过，可以重建数据
      const hasBrandDistribution = report?.brandDistribution && (
        // 条件 1: data 非空且有数据
        (report.brandDistribution.data && Object.keys(report.brandDistribution.data).length > 0) ||
        // 条件 2: total_count > 0（即使 data 为空，也可能是后端计算逻辑问题）
        (report.brandDistribution.total_count && report.brandDistribution.total_count > 0) ||
        // 条件 3: 【新增 - 第 10 次】即使 data 和 total_count 都为 0，但有_debug_info 说明后端计算过
        (report.brandDistribution._debug_info && 
         report.brandDistribution._debug_info.distribution_keys && 
         report.brandDistribution._debug_info.distribution_keys.length > 0)
      );

      // 【P0 关键修复 - 2026-03-12 第 10 次】增强错误日志，帮助排查问题
      let rebuiltFromDebugInfo = false;  // 标记是否从 debug_info 重建
      
      if (!report || !hasBrandDistribution) {
        // 【P0 关键修复 - 2026-03-12 第 10 次】检查是否有_debug_info 可用于重建
        const debugInfo = report?.brandDistribution?._debug_info;
        
        if (debugInfo && debugInfo.distribution_keys && debugInfo.distribution_keys.length > 0) {
          console.warn('[ReportPageV2] ⚠️ 品牌分布数据异常，但有 distribution_keys，尝试重建...');
          
          // 使用 debug 信息重建品牌分布
          const reconstructedData = {};
          debugInfo.distribution_keys.forEach(brand => {
            reconstructedData[brand] = 0;  // 计数为 0，但至少显示品牌
          });
          
          report.brandDistribution.data = reconstructedData;
          report.brandDistribution.total_count = 0;
          
          console.log('[ReportPageV2] ✅ 使用_debug_info 重建品牌分布:', reconstructedData);
          
          // 标记已重建，跳过错误处理
          rebuiltFromDebugInfo = true;
        } else if (!report) {
          console.error('[ReportPageV2] ❌ 报告对象为空');
          this.setData({
            hasError: true,
            errorMessage: '未找到诊断数据，建议重新诊断'
          });
          showToast({
            title: '未找到诊断数据',
            icon: 'none',
            duration: 3000
          });
          return;
        }

        const resultCount = report?.results?.length || 0;

        console.error('[ReportPageV2] ❌ 数据无效，详细检查:', {
          hasReport: !!report,
          hasBrandDistribution,
          brandDistribution: report?.brandDistribution,
          brandDistribution_data: report?.brandDistribution?.data,
          brandDistribution_total_count: report?.brandDistribution?.total_count,
          results_count: resultCount,
          keywords_count: report?.keywords?.length || 0,
          sentimentDistribution: report?.sentimentDistribution
        });

        // 【P0 关键修复 - 2026-03-12 第 8 次】区分不同错误类型，给出不同提示
        let errorMessage = '未找到诊断结果数据';
        let errorType = 'no_data';

        if (report?.error) {
          console.error('[ReportPageV2] 后端返回错误:', report.error);
          errorMessage = report.error.message || report.error || '后端返回错误';
          errorType = 'backend_error';
        } else if (resultCount === 0) {
          // results 为 0，说明 AI 调用全部失败
          console.error('[ReportPageV2] ⚠️ AI 调用全部失败');
          errorMessage = 'AI 诊断未返回有效结果，建议优化配置后重试';
          errorType = 'no_ai_results';
        } else if (resultCount < 4) {
          // 数据不足（少于 4 个样本）- 显示部分数据 + 警告
          console.warn('[ReportPageV2] ⚠️ 数据不足，显示部分数据:', resultCount);
          this.setData({
            hasError: false,
            showPartialData: true,
            partialMessage: `当前只有 ${resultCount} 个有效样本（建议至少 4 个），报告可能不完整`,
            brandDistribution: report.brandDistribution || {},
            sentimentDistribution: report.sentimentDistribution || {},
            keywords: report.keywords || [],
            results: report.results || []
          });
          // 继续执行后续逻辑，显示部分数据
          // fall through to success path
        } else {
          // 其他情况
          errorMessage = '诊断数据异常，请联系技术支持';
          errorType = 'data_error';
        }

        // 如果不是部分数据的情况，显示错误
        // 【P0 关键修复 - 第 10 次】如果已从 debug_info 重建，跳过错误处理
        if (!rebuiltFromDebugInfo && (resultCount >= 4 || resultCount === 0 || report?.error)) {
          this.setData({
            hasError: true,
            errorMessage: errorMessage,
            errorType: errorType,
            noData: true
          });

          // 显示错误提示（根据错误类型显示不同文案）
          const toastMessages = {
            'no_data': '未找到诊断数据',
            'backend_error': '后端返回错误',
            'data_error': '数据异常',
            'no_ai_results': 'AI 未返回结果'
          };
          showToast({
            title: toastMessages[errorType] || '未找到诊断数据',
            icon: 'none',
            duration: 3000
          });
          return;
        }
        
        // 【P0 关键修复 - 第 10 次】如果从 debug_info 重建，显示警告但不报错
        if (rebuiltFromDebugInfo) {
          console.warn('[ReportPageV2] ⚠️ 使用 debug_info 重建数据，显示部分数据');
          this.setData({
            hasError: false,
            showPartialData: true,
            partialMessage: '数据尚未完全生成，显示品牌列表（计数为 0）',
            brandDistribution: report.brandDistribution || {},
            sentimentDistribution: report.sentimentDistribution || {},
            keywords: report.keywords || [],
            results: report.results || []
          });
          // 继续执行，显示重建后的数据
        }
      }

      console.log('[ReportPageV2] 数据加载成功，来源:', dataSource);

      // 更新页面数据
      this.setData({
        brandDistribution: report.brandDistribution || {},
        sentimentDistribution: report.sentimentDistribution || {},
        keywords: report.keywords || [],
        brandScores: report.brandScores || {},
        status: { status: report.status, progress: report.progress, stage: report.stage },
        lastUpdateTime: new Date().toLocaleTimeString(),
        hasError: false,
        dataSource: dataSource
      });
    } catch (error) {
      console.error('[ReportPageV2] 加载报告数据失败:', error);
      hideLoading();
      this.setData({
        hasError: true,
        errorMessage: '加载报告失败：' + (error.message || '未知错误')
      });
      showToast({
        title: '加载报告失败',
        icon: 'none'
      });
    }
  },

  /**
   * 【P0 关键修复 - 2026-03-22】更新报告数据
   * 用于刷新报告时更新页面数据
   * @param {Object} report - 完整的报告数据
   */
  _updateReportData(report) {
    console.log('[ReportPageV2] 📊 更新报告数据');
    
    if (!report) {
      console.error('[ReportPageV2] ❌ 报告对象为空');
      throw new Error('报告数据为空');
    }
    
    // 提取报告数据（兼容多种格式）
    let brandDistribution, sentimentDistribution, keywords, brandScores, results;
    
    // 格式 1: 直接包含数据字段
    if (report.brandDistribution) {
      brandDistribution = report.brandDistribution;
      sentimentDistribution = report.sentimentDistribution || {};
      keywords = report.keywords || [];
      brandScores = report.brandScores || {};
      results = report.results || [];
    }
    // 格式 2: 包含在 data 字段中
    else if (report.data && report.data.brandDistribution) {
      brandDistribution = report.data.brandDistribution;
      sentimentDistribution = report.data.sentimentDistribution || {};
      keywords = report.data.keywords || [];
      brandScores = report.data.brandScores || {};
      results = report.data.results || [];
    }
    // 格式 3: 包含在 dashboardData 中
    else if (report.dashboardData) {
      brandDistribution = report.dashboardData.brandDistribution || {};
      sentimentDistribution = report.dashboardData.sentimentDistribution || {};
      keywords = report.dashboardData.keywords || [];
      brandScores = report.dashboardData.brandScores || {};
      results = report.results || [];
    }
    // 格式 4: 只有 results
    else if (report.results) {
      results = report.results;
      brandDistribution = {};
      sentimentDistribution = {};
      keywords = [];
      brandScores = {};
    }
    else {
      console.error('[ReportPageV2] ❌ 无法识别的报告格式:', Object.keys(report));
      throw new Error('无法解析报告数据格式');
    }
    
    // 更新页面数据
    this.setData({
      brandDistribution: brandDistribution,
      sentimentDistribution: sentimentDistribution,
      keywords: keywords,
      brandScores: brandScores,
      results: results,
      status: { 
        status: report.status || 'completed', 
        progress: report.progress || 100, 
        stage: report.stage || 'completed' 
      },
      lastUpdateTime: new Date().toLocaleTimeString()
    });
    
    console.log('[ReportPageV2] ✅ 报告数据更新成功:', {
      hasBrandDistribution: Object.keys(brandDistribution).length > 0,
      hasSentimentDistribution: Object.keys(sentimentDistribution).length > 0,
      keywordsCount: keywords.length,
      resultsCount: results.length
    });
  },

  /**
   * 启动计时器
   */
  startElapsedTimer() {
    this.stopElapsedTimer();

    this.elapsedTimer = setInterval(() => {
      // 安全检查：页面已卸载则停止计时器
      if (this._isPageUnloaded) {
        this.stopElapsedTimer();
        return;
      }
      
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
  },

  /**
   * 辅助函数：获取对象的键数量（WXML 中使用）
   * @param {Object} obj - 对象
   * @returns {number} 键数量
   */
  objectKeys(obj) {
    if (!obj) return 0;
    try {
      return Object.keys(obj).length;
    } catch (e) {
      return 0;
    }
  },

  /**
   * 【修复 - 2026-03-12】标签页切换事件处理
   * @param {Object} e - 事件对象
   */
  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;

    console.log('[ReportPageV2] 切换标签页:', tab);
    wx.vibrateShort({ type: 'light' });
    this.setData({ activeTab: tab });
  },

  /**
   * 【修复 - 2026-03-12】返回首页事件处理
   */
  onGoHome() {
    console.log('[ReportPageV2] 返回首页');
    wx.vibrateShort({ type: 'light' });
    wx.navigateBack({ delta: 1 });
  },

  /**
   * 【修复 - 2026-03-12】导出报告事件处理
   */
  exportReport() {
    console.log('[ReportPageV2] 导出报告');
    wx.vibrateShort({ type: 'light' });

    wx.showActionSheet({
      itemList: ['导出 PDF', '导出图片', '分享报告'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.exportToPDF();
        } else if (res.tapIndex === 1) {
          this.exportToImage();
        } else if (res.tapIndex === 2) {
          this.shareReport();
        }
      }
    });
  },

  /**
   * 导出为 PDF
   */
  exportToPDF() {
    console.log('[ReportPageV2] 导出 PDF');
    wx.showToast({
      title: '正在生成 PDF...',
      icon: 'loading',
      duration: 2000
    });

    // TODO: 实现 PDF 导出逻辑
    setTimeout(() => {
      wx.showToast({
        title: 'PDF 导出功能开发中',
        icon: 'none'
      });
    }, 2000);
  },

  /**
   * 导出为图片
   */
  exportToImage() {
    console.log('[ReportPageV2] 导出图片');
    wx.showToast({
      title: '正在生成图片...',
      icon: 'loading',
      duration: 2000
    });

    // TODO: 实现图片导出逻辑
    setTimeout(() => {
      wx.showToast({
        title: '图片导出功能开发中',
        icon: 'none'
      });
    }, 2000);
  },

  /**
   * 分享报告
   */
  shareReport() {
    console.log('[ReportPageV2] 分享报告');
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    });
  },

  /**
   * 【P0 关键修复 - 2026-03-22】刷新报告事件处理
   * 确保诊断完成后能够完整加载报告
   */
  async refreshReport() {
    console.log('[ReportPageV2] 🔄 刷新报告');
    wx.vibrateShort({ type: 'light' });

    // 【关键修复】清除缓存，强制重新加载
    const executionId = this.data.executionId;
    const cacheKey = `diagnosis_report_${executionId}`;
    
    try {
      // 清除本地缓存的报告数据
      wx.removeStorageSync(cacheKey);
      console.log('[ReportPageV2] ✅ 已清除本地缓存:', cacheKey);
      
      // 清除全局待处理报告
      const app = getApp();
      if (app.globalData && app.globalData.pendingReport) {
        delete app.globalData.pendingReport[executionId];
        console.log('[ReportPageV2] ✅ 已清除全局待处理报告');
      }
    } catch (e) {
      console.warn('[ReportPageV2] ⚠️ 清除缓存失败:', e);
    }

    // 显示加载中状态
    this.setData({ 
      isRefreshing: true,
      isLoading: true,
      hasError: false,
      showErrorCard: false,
      retryCount: 0
    });

    try {
      // 【关键修复】强制从 API 重新加载，不使用缓存
      console.log('[ReportPageV2] 🔄 强制从 API 重新加载报告...');
      
      // 直接调用诊断服务的 getFullReport 方法，绕过缓存
      const diagnosisService = require('../../services/diagnosisService');
      const report = await diagnosisService.getFullReport(executionId);
      
      console.log('[ReportPageV2] ✅ 报告重新加载成功:', {
        executionId,
        hasResults: report?.results?.length > 0,
        hasMetrics: !!report?.metrics,
        hasDimensionScores: !!report?.dimensionScores,
        hasDiagnosticWall: !!report?.diagnosticWall
      });

      // 更新页面数据
      this._updateReportData(report);
      
      // 设置加载成功状态
      this.setData({
        isLoading: false,
        hasError: false,
        showErrorCard: false,
        dataSource: 'api-refresh' // 标记为刷新加载
      });
      
      // 显示成功提示
      wx.showToast({
        title: '加载成功',
        icon: 'success',
        duration: 1500
      });
      
    } catch (error) {
      console.error('[ReportPageV2] ❌ 重新加载失败:', error);
      
      // 设置错误状态
      this.setData({
        isLoading: false,
        hasError: true,
        showErrorCard: true,
        errorMessage: error.message || '加载失败，请重试',
        errorType: 'load_error'
      });
      
      // 显示错误提示
      wx.showToast({
        title: '加载失败，请重试',
        icon: 'none',
        duration: 2000
      });
    } finally {
      this.setData({ isRefreshing: false });
    }
  },

  /**
   * 【P0 关键修复 - 2026-03-22】处理错误卡片操作
   * 确保重试时能够完整加载报告
   * @param {Object} e - 事件对象
   */
  handleErrorCardAction(e) {
    const action = e.currentTarget.dataset.action;
    if (!action) return;

    console.log('[ReportPageV2] 🎯 错误卡片操作:', action);
    wx.vibrateShort({ type: 'light' });

    switch (action.type) {
      case 'retry':
        // 【关键修复】重试：清除缓存并重新加载
        console.log('[ReportPageV2] 🔄 重试：清除缓存并重新加载');
        this.setData({ hasError: false, showErrorCard: false, isLoading: true });
        
        // 调用刷新报告方法（已增强版本）
        this.refreshReport();
        break;

      case 'navigate':
        // 导航到其他页面
        if (action.url) {
          wx.navigateTo({ url: action.url });
        }
        break;

      case 'wait':
        // 继续等待：重新启动监听
        console.log('[ReportPageV2] ⏳ 继续等待：重新启动监听');
        this.startListening();
        break;

      case 'show_error_details':
        // 显示错误详情
        this._showErrorDetailsModal();
        break;

      case 'contact_support':
        // 联系客服
        wx.showModal({
          title: '联系客服',
          content: '客服微信：support\n\n请提供执行 ID：' + this.data.executionId,
          showCancel: false
        });
        break;

      default:
        console.warn('[ReportPageV2] ⚠️ 未知操作类型:', action.type);
    }
  },

  /**
   * 【P0 关键修复 - 2026-03-20】显示错误详情对话框
   */
  _showErrorDetailsModal() {
    const { errorMessage, errorType, executionId } = this.data;

    showModal({
      title: '错误详情',
      content: `错误类型：${errorType}\n\n` +
               `错误信息：${errorMessage}\n\n` +
               `执行 ID：${executionId}\n\n` +
               `建议：\n` +
               `1. 检查后端日志查看详细错误堆栈\n` +
               `2. 确认数据库连接正常\n` +
               `3. 查看 AI 调用是否成功`,
      showCancel: false,
      confirmText: '我知道了'
    });
  },

  /**
   * 【修复 - 2026-03-12】分享报告事件处理
   */
  onShareReport() {
    console.log('[ReportPageV2] 分享报告');
    wx.vibrateShort({ type: 'light' });
    this.shareReport();
  },

  /**
   * 品牌分布点击事件
   * @param {Object} e - 事件对象
   */
  onBrandDistributionTap(e) {
    console.log('[ReportPageV2] 品牌分布点击:', e.detail);
    wx.showToast({
      title: '品牌：' + (e.detail?.brand || '未知'),
      icon: 'none'
    });
  },

  /**
   * 情感分布点击事件
   * @param {Object} e - 事件对象
   */
  onSentimentTap(e) {
    console.log('[ReportPageV2] 情感分布点击:', e.detail);
    const sentiment = e.detail?.sentiment;
    const titles = {
      positive: '正面情感',
      negative: '负面情感',
      neutral: '中性情感'
    };
    wx.showToast({
      title: titles[sentiment] || '情感分析',
      icon: 'none'
    });
  },

  /**
   * 关键词点击事件
   * @param {Object} e - 事件对象
   */
  onKeywordTap(e) {
    console.log('[ReportPageV2] 关键词点击:', e.detail);
    wx.showToast({
      title: '关键词：' + (e.detail?.word || '未知'),
      icon: 'none'
    });
  }
});
