/**
 * 流水线阶段组件
 * 
 * 职责：
 * - 单个情报项展示
 * - 状态图标
 * - 时间戳
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    // 情报项数据
    item: {
      type: Object,
      value: null,
      observer: 'onItemChange'
    },
    // 索引
    index: {
      type: Number,
      value: 0
    },
    // 状态映射
    statusText: {
      type: Object,
      value: {
        pending: '等待中',
        processing: '处理中',
        success: '成功',
        error: '失败'
      }
    }
  },

  data: {
    // 本地状态
    isExpanded: false,
    showDetails: false
  },

  lifetimes: {
    attached() {
      console.log('[PipelineStage] 组件已挂载');
    }
  },

  methods: {
    /**
     * 情报项变化监听
     */
    onItemChange(newVal) {
      if (newVal && newVal.status === 'error') {
        this.setData({ showDetails: true });
      }
    },

    /**
     * 切换展开状态
     */
    toggleExpand() {
      this.setData({
        isExpanded: !this.data.isExpanded
      });
      this.triggerEvent('expand', { 
        index: this.data.index, 
        expanded: this.data.isExpanded 
      });
    },

    /**
     * 查看详情
     */
    viewDetails() {
      this.setData({ showDetails: true });
      this.triggerEvent('viewdetails', { 
        index: this.data.index,
        item: this.data.item 
      });
    },

    /**
     * 关闭详情
     */
    closeDetails() {
      this.setData({ showDetails: false });
    },

    /**
     * 获取状态图标
     */
    getStatusIcon(status) {
      const icons = {
        pending: '⏳',
        processing: '🔄',
        success: '✅',
        error: '❌'
      };
      return icons[status] || '⏳';
    },

    /**
     * 获取状态样式类
     */
    getStatusClass(status) {
      return `status-${status}`;
    },

    /**
     * 格式化时间
     */
    formatTime(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      const seconds = date.getSeconds().toString().padStart(2, '0');
      return `${hours}:${minutes}:${seconds}`;
    }
  }
});
