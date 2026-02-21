/**
 * 情报流水线组件 - 增强版
 * 功能：实时显示 AI 诊断情报流，支持 SSE 实时更新
 */

const app = getApp();
const logger = require('../../../utils/logger');
const { request } = require('../../../utils/request');

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  /**
   * 组件属性
   */
  properties: {
    // 情报项列表
    items: {
      type: Array,
      value: [],
      observer: 'onItemsChange'
    },
    // 是否正在加载
    isLoading: {
      type: Boolean,
      value: false
    },
    // 是否实时模式
    isLive: {
      type: Boolean,
      value: true
    },
    // 是否折叠
    collapsed: {
      type: Boolean,
      value: false
    },
    // 总数
    totalCount: {
      type: Number,
      value: 0
    },
    // 执行 ID（用于获取数据）
    executionId: {
      type: String,
      value: ''
    },
    // 品牌名称
    brandName: {
      type: String,
      value: ''
    },
    // 是否启用 SSE
    enableSSE: {
      type: Boolean,
      value: true
    },
    // 自动滚动
    autoScroll: {
      type: Boolean,
      value: true
    }
  },

  /**
   * 组件数据
   */
  data: {
    statusText: {
      pending: '等待中',
      processing: '处理中',
      success: '成功',
      error: '失败'
    },
    // 统计数据
    successCount: 0,
    processingCount: 0,
    errorCount: 0,
    pendingCount: 0,
    completedCount: 0,
    // SSE 连接状态
    sseConnected: false,
    sseConnecting: false,
    // 滚动控制
    scrollTop: 0,
    scrollIntoView: ''
  },

  /**
   * 生命周期
   */
  lifetimes: {
    attached() {
      logger.debug('[IntelligencePipeline] Component attached');
      this.initPipeline();
    },

    ready() {
      logger.debug('[IntelligencePipeline] Component ready');
    },

    detached() {
      logger.debug('[IntelligencePipeline] Component detached');
      this.cleanup();
    }
  },

  /**
   * 数据监听器
   */
  observers: {
    items: function(newItems) {
      this.calculateStats(newItems);
    },
    executionId: function(newId) {
      if (newId && newId !== this.data.executionId) {
        this.initPipeline();
      }
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 初始化流水线
     */
    async initPipeline() {
      const { executionId, brandName, enableSSE } = this.data;

      if (!executionId) {
        logger.warn('[IntelligencePipeline] 缺少 executionId，无法初始化');
        return;
      }

      logger.info('[IntelligencePipeline] 初始化流水线', { executionId, brandName });

      // 加载历史数据
      await this.loadPipelineData();

      // 连接 SSE（如果启用）
      if (enableSSE) {
        this.connectSSE();
      }
    },

    /**
     * 加载流水线数据
     */
    async loadPipelineData() {
      const { executionId, brandName } = this.data;

      try {
        this.setData({ isLoading: true });

        const result = await request({
          url: '/api/intelligence/pipeline',
          method: 'GET',
          data: {
            executionId,
            brandName,
            limit: 50
          },
          loading: false
        });

        if (result.status === 'success' && result.data) {
          const items = result.data.items || [];
          const stats = result.data.stats || {};

          logger.info('[IntelligencePipeline] 数据加载成功', {
            itemCount: items.length,
            stats
          });

          this.setData({
            items,
            isLoading: false,
            ...stats
          });

          // 触发数据加载完成事件
          this.triggerEvent('loaded', {
            items,
            stats,
            metadata: result.data.metadata
          });

          // 自动滚动到底部
          if (this.data.autoScroll) {
            this.scrollToBottom();
          }
        } else {
          throw new Error(result.error || '数据加载失败');
        }
      } catch (error) {
        logger.error('[IntelligencePipeline] 数据加载失败', error);
        this.setData({ isLoading: false });

        // 触发错误事件
        this.triggerEvent('error', {
          type: 'load',
          error: error.message || '数据加载失败'
        });
      }
    },

    /**
     * 连接 SSE 实时流
     */
    connectSSE() {
      if (this.sseSource) {
        this.sseSource.close();
      }

      const { executionId } = this.data;
      const baseUrl = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';
      const sseUrl = `${baseUrl}/api/intelligence/stream?executionId=${executionId}`;

      logger.info('[IntelligencePipeline] 连接 SSE 流', { sseUrl });

      this.setData({ sseConnecting: true });

      try {
        // 微信小程序不支持原生 SSE，使用轮询替代
        this.startPolling();
      } catch (error) {
        logger.error('[IntelligencePipeline] SSE 连接失败', error);
        this.setData({
          sseConnecting: false,
          sseConnected: false
        });

        this.triggerEvent('sseError', {
          error: error.message || 'SSE 连接失败'
        });
      }
    },

    /**
     * 启动轮询（替代 SSE）
     */
    startPolling() {
      const { executionId } = this.data;

      // 清除之前的轮询
      if (this.pollingTimer) {
        clearInterval(this.pollingTimer);
      }

      this.setData({ sseConnecting: false, sseConnected: true });

      // 每 3 秒轮询一次
      this.pollingTimer = setInterval(() => {
        this.pollUpdates();
      }, 3000);

      logger.info('[IntelligencePipeline] 轮询已启动', { executionId });
    },

    /**
     * 轮询更新
     */
    async pollUpdates() {
      const { executionId, items } = this.data;

      try {
        const result = await request({
          url: '/api/intelligence/pipeline',
          method: 'GET',
          data: {
            executionId,
            limit: 50
          },
          loading: false
        });

        if (result.status === 'success' && result.data) {
          const newItems = result.data.items || [];

          // 检查是否有新数据
          if (newItems.length > items.length) {
            logger.debug('[IntelligencePipeline] 检测到新数据', {
              oldCount: items.length,
              newCount: newItems.length
            });

            this.setData({ items: newItems });

            // 触发更新事件
            this.triggerEvent('update', {
              items: newItems,
              addedCount: newItems.length - items.length
            });

            // 自动滚动到底部
            if (this.data.autoScroll) {
              this.scrollToBottom();
            }
          }
        }
      } catch (error) {
        logger.warn('[IntelligencePipeline] 轮询失败', error);
      }
    },

    /**
     * 停止轮询
     */
    stopPolling() {
      if (this.pollingTimer) {
        clearInterval(this.pollingTimer);
        this.pollingTimer = null;
        logger.info('[IntelligencePipeline] 轮询已停止');
      }
    },

    /**
     * 计算统计数据
     */
    calculateStats(items) {
      const stats = {
        successCount: 0,
        processingCount: 0,
        errorCount: 0,
        pendingCount: 0,
        completedCount: 0
      };

      items.forEach(item => {
        switch (item.status) {
          case 'success':
            stats.successCount++;
            stats.completedCount++;
            break;
          case 'processing':
            stats.processingCount++;
            break;
          case 'error':
            stats.errorCount++;
            stats.completedCount++;
            break;
          case 'pending':
            stats.pendingCount++;
            break;
        }
      });

      this.setData({
        successCount: stats.successCount,
        processingCount: stats.processingCount,
        errorCount: stats.errorCount,
        pendingCount: stats.pendingCount,
        completedCount: stats.completedCount
      });
    },

    /**
     * 切换折叠状态
     */
    toggleCollapse() {
      const newCollapsed = !this.data.collapsed;
      this.setData({ collapsed: newCollapsed });
      this.triggerEvent('collapse', { collapsed: newCollapsed });
    },

    /**
     * 清空情报列表
     */
    clearItems() {
      const { executionId } = this.data;

      wx.showModal({
        title: '确认清空',
        content: '确定要清空所有情报记录吗？',
        confirmColor: '#E94560',
        success: (res) => {
          if (res.confirm) {
            // 调用后端清空接口
            request({
              url: '/api/intelligence/clear',
              method: 'POST',
              data: { executionId },
              loading: false
            }).then(() => {
              this.setData({ items: [] });
              this.triggerEvent('clear', { executionId });

              wx.showToast({
                title: '已清空',
                icon: 'success'
              });
            }).catch((error) => {
              logger.error('[IntelligencePipeline] 清空失败', error);
              wx.showToast({
                title: '清空失败',
                icon: 'none'
              });
            });
          }
        }
      });
    },

    /**
     * 添加情报项
     */
    addItem(item) {
      const newItem = {
        id: item.id || Date.now().toString(),
        question: item.question || '',
        model: item.model || 'Unknown',
        status: item.status || 'pending',
        time: item.time || new Date().toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }),
        timestamp: item.timestamp || Date.now() / 1000,
        latency: item.latency,
        brand: item.brand || this.data.brandName,
        preview: item.preview,
        error: item.error,
        metadata: item.metadata || {}
      };

      const newItems = [...this.data.items, newItem];
      this.setData({ items: newItems });
      this.triggerEvent('change', { items: newItems, action: 'add', item: newItem });

      // 自动滚动到底部
      if (this.data.autoScroll) {
        this.scrollToBottom();
      }
    },

    /**
     * 更新情报项状态
     */
    updateItemStatus(id, status, extra = {}) {
      const newItems = this.data.items.map(item => {
        if (item.id === id) {
          return {
            ...item,
            status,
            ...extra
          };
        }
        return item;
      });

      this.setData({ items: newItems });
      this.triggerEvent('change', { items: newItems, action: 'update', itemId: id, status });
    },

    /**
     * 滚动到底部
     */
    scrollToBottom() {
      // 使用 scroll-into-view 方式
      if (this.data.items.length > 0) {
        const lastItem = this.data.items[this.data.items.length - 1];
        this.setData({
          scrollIntoView: `item-${lastItem.id}`
        });
      }
    },

    /**
     * 监听滚动
     */
    onScroll(event) {
      const { scrollTop } = event.detail;
      this.setData({ scrollTop });
      this.triggerEvent('scroll', { scrollTop });
    },

    /**
     * 情报项点击
     */
    onItemTap(event) {
      const { item } = event.currentTarget.dataset;
      logger.debug('[IntelligencePipeline] 情报项点击', item);
      this.triggerEvent('itemtap', { item });
    },

    /**
     * 清理资源
     */
    cleanup() {
      this.stopPolling();
      if (this.sseSource) {
        this.sseSource.close();
        this.sseSource = null;
      }
    },

    /**
     * 数据变化监听
     */
    onItemsChange(newItems) {
      this.calculateStats(newItems);
    }
  }
});
