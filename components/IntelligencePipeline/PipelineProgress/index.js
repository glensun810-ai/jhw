/**
 * 流水线进度指示器组件
 * 
 * 职责：
 * - 进度条展示
 * - 统计数据
 * - 连接状态
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    // 总数
    totalCount: {
      type: Number,
      value: 0
    },
    // 成功数
    successCount: {
      type: Number,
      value: 0
    },
    // 处理中数
    processingCount: {
      type: Number,
      value: 0
    },
    // 错误数
    errorCount: {
      type: Number,
      value: 0
    },
    // 等待中数
    pendingCount: {
      type: Number,
      value: 0
    },
    // SSE 连接状态
    sseConnected: {
      type: Boolean,
      value: false
    },
    // SSE 连接中
    sseConnecting: {
      type: Boolean,
      value: false
    },
    // SSE 错误
    sseError: {
      type: String,
      value: null
    }
  },

  data: {
    // 进度百分比
    progressPercent: 0,
    // 完成数
    completedCount: 0
  },

  lifetimes: {
    attached() {
      this.calculateProgress();
    }
  },

  methods: {
    /**
     * 属性变化时重新计算
     */
    onCountsChange() {
      this.calculateProgress();
    },

    /**
     * 计算进度
     */
    calculateProgress() {
      const { totalCount, successCount, errorCount } = this.data;
      
      const completed = successCount + errorCount;
      const percent = totalCount > 0 
        ? Math.round((completed / totalCount) * 100) 
        : 0;

      this.setData({
        completedCount: completed,
        progressPercent: percent
      });

      // 触发进度变化事件
      this.triggerEvent('progresschange', {
        completed,
        percent
      });
    },

    /**
     * 获取状态文本
     */
    getStatusText() {
      const { successCount, processingCount, errorCount, pendingCount } = this.data;
      
      if (processingCount > 0) {
        return `处理中 ${processingCount} 项...`;
      } else if (errorCount > 0) {
        return `完成（${errorCount} 项失败）`;
      } else if (successCount > 0) {
        return '已完成';
      } else {
        return '等待中...';
      }
    },

    /**
     * 刷新连接
     */
    refreshConnection() {
      this.triggerEvent('refresh');
    }
  },

  observers: {
    'successCount,processingCount,errorCount,pendingCount': function() {
      this.calculateProgress();
    }
  }
});
