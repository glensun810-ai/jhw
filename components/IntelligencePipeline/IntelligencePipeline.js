/**
 * 情报流水线主组件 - 重构简化版
 *
 * 重构说明:
 * - 阶段展示 → PipelineStage/index.js
 * - 进度指示 → PipelineProgress/index.js
 *
 * 本文件保留:
 * - 组件协调
 * - WebSocket 连接管理（替代 SSE，微信小程序不支持 SSE）
 * - 事件转发
 *
 * 【P0 关键修复 - 2026-03-03】
 * - 微信小程序不支持 SSE (EventSource API)
 * - 使用已有的 WebSocketClient 替代
 * - WebSocket 客户端路径：miniprogram/services/webSocketClient.js
 */

const app = getApp();
const logger = require('../../utils/logger');
// 【P0 关键修复】导入已有的 WebSocket 客户端，而非不存在的 SSE 客户端
const webSocketClient = require('../../miniprogram/services/webSocketClient').default;

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    items: {
      type: Array,
      value: [],
      observer: 'onItemsChange'
    },
    isLoading: {
      type: Boolean,
      value: false
    },
    isLive: {
      type: Boolean,
      value: true
    },
    collapsed: {
      type: Boolean,
      value: false
    },
    totalCount: {
      type: Number,
      value: 0
    },
    executionId: {
      type: String,
      value: ''
    },
    brandName: {
      type: String,
      value: ''
    },
    enableSSE: {
      type: Boolean,
      value: true
    },
    autoScroll: {
      type: Boolean,
      value: true
    }
  },

  data: {
    statusText: {
      pending: '等待中',
      processing: '处理中',
      success: '成功',
      error: '失败'
    },
    successCount: 0,
    processingCount: 0,
    errorCount: 0,
    pendingCount: 0,
    completedCount: 0,
    sseConnected: false,
    sseConnecting: false,
    sseError: null,
    scrollTop: 0
  },

  lifetimes: {
    attached() {
      logger.debug('[IntelligencePipeline] Component attached');
      this.initPipeline();
    },
    detached() {
      this.cleanup();
    }
  },

  methods: {
    /**
     * 初始化流水线
     */
    initPipeline() {
      if (this.data.isLive) {
        // 【P0 关键修复】使用 WebSocket 替代 SSE
        this.connectWebSocket();
      }
      this.calculateCounts();
    },

    /**
     * 连接 WebSocket
     * 【P0 关键修复 - 2026-03-03】使用已有的 WebSocketClient 替代 SSE
     */
    connectWebSocket() {
      if (!this.data.executionId) {
        logger.warn('[IntelligencePipeline] 缺少 executionId，无法连接 WebSocket');
        return;
      }

      this.setData({ sseConnecting: true });

      try {
        // 【P0 关键修复】使用已有的 WebSocket 客户端
        webSocketClient.connect(this.data.executionId, {
          // 连接成功回调
          onConnected: () => {
            logger.info('[IntelligencePipeline] WebSocket 已连接');
            this.setData({
              sseConnected: true,  // 保持变量名兼容
              sseConnecting: false
            });
          },

          // 状态变化回调
          onStateChange: (newState, oldState) => {
            logger.debug(`[IntelligencePipeline] WebSocket 状态变化：${oldState} -> ${newState}`);
            
            // 根据状态更新 UI
            if (newState === 'disconnected' || newState === 'fallback') {
              this.setData({
                sseConnected: false,
                sseConnecting: false
              });
            }
          },

          // 进度更新回调
          onProgress: (data) => {
            logger.debug('[IntelligencePipeline] WebSocket 进度更新:', data);
            this.triggerEvent('update', { 
              item: {
                type: 'intelligence',
                data: data
              }
            });
            this.calculateCounts();
          },

          // 中间结果回调
          onResult: (data) => {
            logger.debug('[IntelligencePipeline] WebSocket 结果更新:', data);
            this.triggerEvent('update', { 
              item: {
                type: 'intelligence',
                data: data
              }
            });
            this.calculateCounts();
          },

          // 完成回调
          onComplete: (data) => {
            logger.info('[IntelligencePipeline] WebSocket 诊断完成:', data);
            this.setData({ sseConnected: false });
            this.triggerEvent('complete', data);
            this.calculateCounts();
          },

          // 错误回调
          onError: (error) => {
            logger.error('[IntelligencePipeline] WebSocket 错误:', error);
            this.setData({
              sseError: error.message || '连接失败',
              sseConnecting: false
            });
          },

          // 断开连接回调
          onDisconnected: (res) => {
            logger.info('[IntelligencePipeline] WebSocket 连接已断开:', res);
            this.setData({
              sseConnected: false,
              sseConnecting: false
            });
          },

          // 降级回调（WebSocket 失败时使用轮询）
          onFallback: () => {
            logger.warn('[IntelligencePipeline] WebSocket 降级到轮询模式');
            // 可以在这里启动 HTTP 轮询作为后备
            this.setData({
              sseConnected: false,
              sseConnecting: false
            });
          }
        });
      } catch (error) {
        logger.error('[IntelligencePipeline] WebSocket 连接失败:', error);
        this.setData({
          sseError: error.message,
          sseConnecting: false
        });
      }
    },

    /**
     * 情报项变化监听
     */
    onItemsChange(newVal) {
      this.calculateCounts();
      
      if (newVal && newVal.length > 0) {
        this.triggerEvent('itemschange', { items: newVal });
      }
    },

    /**
     * 计算统计
     */
    calculateCounts() {
      const items = this.data.items || [];
      
      const successCount = items.filter(i => i.status === 'success').length;
      const processingCount = items.filter(i => i.status === 'processing').length;
      const errorCount = items.filter(i => i.status === 'error').length;
      const pendingCount = items.filter(i => i.status === 'pending').length;
      const completedCount = successCount + errorCount;

      this.setData({
        successCount,
        processingCount,
        errorCount,
        pendingCount,
        completedCount
      });
    },

    /**
     * 滚动到底部
     */
    scrollToBottom() {
      if (this.data.autoScroll) {
        this.setData({
          scrollTop: 99999
        });
      }
    },

    /**
     * 刷新连接
     */
    onRefresh() {
      this.setData({ 
        sseConnected: false, 
        sseError: null 
      });
      this.connectSSE();
    },

    /**
     * 进度变化
     */
    onProgressChange(e) {
      this.triggerEvent('progress', e.detail);
    },

    /**
     * 阶段展开
     */
    onStageExpand(e) {
      this.triggerEvent('stageexpand', e.detail);
    },

    /**
     * 查看详情
     */
    onViewDetails(e) {
      this.triggerEvent('viewdetails', e.detail);
    },

    /**
     * 清理资源
     */
    cleanup() {
      // 【P0 关键修复】断开 WebSocket 连接
      if (webSocketClient) {
        webSocketClient.disconnect();
      }
      logger.debug('[IntelligencePipeline] Component cleaned up');
    }
  }
});
