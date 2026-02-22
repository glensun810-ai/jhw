/**
 * 导出选项主组件 - 重构简化版
 * 
 * 重构说明:
 * - 格式选择 → ExportFormatSelector/index.js
 * - 进度指示 → ExportProgress/index.js
 * 
 * 本文件保留:
 * - 组件协调
 * - API 调用
 * - 事件转发
 */

const { request } = require('../../utils/request');

Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared'
  },

  properties: {
    executionId: {
      type: String,
      value: ''
    },
    visible: {
      type: Boolean,
      value: false
    },
    brandName: {
      type: String,
      value: ''
    }
  },

  data: {
    format: 'pdf',
    level: 'full',
    selectedSections: {
      executiveSummary: true,
      brandHealth: true,
      platformAnalysis: true,
      competitiveAnalysis: true,
      negativeSources: false,
      roiAnalysis: false,
      actionPlan: false
    },
    isAsync: false,
    generating: false,
    progress: 0,
    statusMessage: '',
    taskId: ''
  },

  lifetimes: {
    attached() {
      console.log('[ExportOptions] 组件已挂载');
    },
    detached() {
      this.cleanup();
    }
  },

  methods: {
    /**
     * 关闭组件
     */
    close() {
      if (!this.data.generating) {
        this.triggerEvent('close');
      }
    },

    /**
     * 格式变化
     */
    onFormatChange(e) {
      this.setData({ format: e.detail.format });
    },

    /**
     * 级别变化
     */
    onLevelChange(e) {
      this.setData({ level: e.detail.level });
    },

    /**
     * 章节变化
     */
    onSectionChange(e) {
      this.setData({ selectedSections: e.detail.selectedSections });
    },

    /**
     * 开始导出
     */
    startExport() {
      const { executionId, format, level, selectedSections } = this.data;

      if (!executionId) {
        wx.showToast({ title: '缺少执行 ID', icon: 'none' });
        return;
      }

      this.setData({
        generating: true,
        progress: 0,
        statusMessage: '正在准备生成...'
      });

      // 调用导出 API
      request({
        url: '/api/export/generate',
        method: 'POST',
        data: {
          execution_id: executionId,
          format,
          level,
          sections: selectedSections
        }
      }).then(res => {
        if (res.task_id) {
          this.setData({
            taskId: res.task_id,
            isAsync: true
          });
          this.startPolling(res.task_id);
        } else {
          this.onExportComplete();
        }
      }).catch(err => {
        this.onExportError(err.message || '生成失败');
      });
    },

    /**
     * 开始轮询进度
     */
    startPolling(taskId) {
      this.pollTimer = setInterval(() => {
        request({
          url: '/api/export/status',
          method: 'GET',
          data: { task_id: taskId }
        }).then(res => {
          const { progress, status } = res;
          
          this.setData({
            progress,
            statusMessage: status
          });

          if (status === 'completed') {
            this.onExportComplete();
          } else if (status === 'failed') {
            this.onExportError('生成失败');
          }
        }).catch(err => {
          this.onExportError(err.message || '查询失败');
        });
      }, 2000);
    },

    /**
     * 导出完成
     */
    onExportComplete() {
      this.clearPolling();
      this.setData({
        generating: false,
        progress: 100,
        statusMessage: '生成成功'
      });
      this.triggerEvent('complete', {
        taskId: this.data.taskId
      });
    },

    /**
     * 导出失败
     */
    onExportError(message) {
      this.clearPolling();
      this.setData({
        generating: false,
        statusMessage: message
      });
      this.triggerEvent('error', { message });
    },

    /**
     * 取消导出
     */
    onCancel() {
      if (this.data.taskId) {
        request({
          url: '/api/export/cancel',
          method: 'POST',
          data: { task_id: this.data.taskId }
        });
      }
      this.clearPolling();
      this.setData({
        generating: false,
        progress: 0,
        statusMessage: ''
      });
      this.triggerEvent('cancel');
    },

    /**
     * 查看结果
     */
    onViewResult() {
      this.triggerEvent('viewresult', {
        taskId: this.data.taskId,
        format: this.data.format
      });
    },

    /**
     * 重试
     */
    onRetry() {
      this.setData({
        generating: false,
        progress: 0,
        statusMessage: ''
      });
      this.startExport();
    },

    /**
     * 清除轮询
     */
    clearPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    },

    /**
     * 清理资源
     */
    cleanup() {
      this.clearPolling();
    }
  }
});
