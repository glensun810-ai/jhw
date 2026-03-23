/**
 * 导出进度指示器组件
 * 
 * 职责：
 * - 进度条展示
 * - 状态信息
 * - 取消操作
 */

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    // 是否正在生成
    generating: {
      type: Boolean,
      value: false
    },
    // 进度百分比
    progress: {
      type: Number,
      value: 0
    },
    // 状态信息
    statusMessage: {
      type: String,
      value: ''
    },
    // 是否异步
    isAsync: {
      type: Boolean,
      value: false
    },
    // 任务 ID
    taskId: {
      type: String,
      value: ''
    }
  },

  data: {
    // 状态映射
    statusText: {
      pending: '准备中...',
      processing: '生成中...',
      success: '生成成功',
      error: '生成失败'
    }
  },

  lifetimes: {
    attached() {
      console.log('[ExportProgress] 组件已挂载');
    }
  },

  methods: {
    /**
     * 取消导出
     */
    onCancel() {
      this.triggerEvent('cancel');
    },

    /**
     * 查看结果
     */
    viewResult() {
      this.triggerEvent('viewresult', {
        taskId: this.data.taskId
      });
    },

    /**
     * 重新生成
     */
    retry() {
      this.triggerEvent('retry');
    },

    /**
     * 获取状态图标
     */
    getStatusIcon() {
      if (this.data.generating) {
        return '🔄';
      } else if (this.data.progress === 100) {
        return '✅';
      } else {
        return '⏳';
      }
    }
  }
});
