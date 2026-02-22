/**
 * 情报流水线主组件 - 重构简化版
 * 
 * 重构说明:
 * - 阶段展示 → PipelineStage/index.js
 * - 进度指示 → PipelineProgress/index.js
 * 
 * 本文件保留:
 * - 组件协调
 * - SSE 连接管理
 * - 事件转发
 */

const app = getApp();
const logger = require('../../utils/logger');
const { watchIntelligenceUpdates } = require('../../utils/sse-client');

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
      if (this.data.enableSSE && this.data.isLive) {
        this.connectSSE();
      }
      this.calculateCounts();
    },

    /**
     * 连接 SSE
     */
    connectSSE() {
      if (!this.data.executionId) return;

      this.setData({ sseConnecting: true });

      try {
        this.sseClient = watchIntelligenceUpdates(
          this.data.executionId,
          (event) => {
            this.onSSEUpdate(event);
          },
          () => {
            this.setData({ 
              sseConnected: true, 
              sseConnecting: false 
            });
          },
          (error) => {
            this.setData({ 
              sseError: error.message, 
              sseConnecting: false 
            });
          }
        );
      } catch (error) {
        logger.error('[IntelligencePipeline] SSE 连接失败:', error);
        this.setData({ 
          sseError: error.message, 
          sseConnecting: false 
        });
      }
    },

    /**
     * SSE 更新处理
     */
    onSSEUpdate(event) {
      const { type, data } = event;
      
      logger.debug('[IntelligencePipeline] SSE update:', type, data);

      if (type === 'intelligence') {
        this.triggerEvent('update', { item: data });
      } else if (type === 'complete') {
        this.setData({ sseConnected: false });
        this.triggerEvent('complete');
      }

      this.calculateCounts();
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
      if (this.sseClient) {
        this.sseClient.close();
        this.sseClient = null;
      }
      logger.debug('[IntelligencePipeline] Component cleaned up');
    }
  }
});
