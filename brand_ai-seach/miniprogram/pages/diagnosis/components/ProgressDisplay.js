/**
 * 进度显示组件
 * 
 * 显示诊断进度、阶段、剩余时间等信息
 */

Component({
  /**
   * 组件属性
   */
  properties: {
    /**
     * 状态对象
     * { progress: number, stage: string, status: string }
     */
    status: {
      type: Object,
      value: null,
      observer: '_onStatusChange'
    },
    /**
     * 已用时间（秒）
     */
    elapsedTime: {
      type: Number,
      value: 0,
      observer: '_onElapsedTimeChange'
    }
  },

  /**
   * 组件数据
   */
  data: {
    progressText: '准备中...',
    stageText: '初始化中...',
    estimatedTime: '计算中...',
    progressColor: '#07c160',
    progressPercent: 0,
    stageIcon: 'loading'
  },

  /**
   * 监听器
   */
  observers: {
    'status': function(status) {
      if (!status) return;
      this._updateDisplay(status);
    },
    'elapsedTime': function(elapsedTime) {
      if (this.data.status) {
        this._updateEstimatedTime(this.data.status, elapsedTime);
      }
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 状态变化处理
     * @private
     */
    _onStatusChange(newStatus) {
      if (!newStatus) return;
      this._updateDisplay(newStatus);
    },

    /**
     * 时间变化处理
     * @private
     */
    _onElapsedTimeChange(newTime) {
      if (this.data.status) {
        this._updateEstimatedTime(this.data.status, newTime);
      }
    },

    /**
     * 更新显示内容
     * @private
     * @param {Object} status 
     */
    _updateDisplay(status) {
      this.setData({
        progressText: this._getProgressText(status),
        stageText: this._getStageText(status),
        progressColor: this._getProgressColor(status),
        progressPercent: Math.min(100, Math.max(0, status.progress || 0)),
        stageIcon: this._getStageIcon(status)
      });

      // 更新预计时间
      this._updateEstimatedTime(status, this.properties.elapsedTime);

      // 触发进度更新事件
      this.triggerEvent('progressupdate', {
        progress: status.progress,
        stage: status.stage,
        status: status.status
      });

      // 触发阶段变化事件
      this.triggerEvent('stagechange', {
        stage: status.stage,
        stageText: this._getStageText(status)
      });
    },

    /**
     * 更新预计时间
     * @private
     * @param {Object} status 
     * @param {number} elapsedTime 
     */
    _updateEstimatedTime(status, elapsedTime) {
      if (status.progress >= 100 || status.status === 'completed') {
        this.setData({
          estimatedTime: '已完成'
        });
        return;
      }

      if (status.progress > 0 && elapsedTime > 0) {
        const estimated = Math.round(elapsedTime / status.progress * (100 - status.progress));
        
        if (estimated < 60) {
          this.setData({
            estimatedTime: `预计剩余 ${estimated} 秒`
          });
        } else if (estimated < 3600) {
          const minutes = Math.ceil(estimated / 60);
          this.setData({
            estimatedTime: `预计剩余 ${minutes} 分钟`
          });
        } else {
          const hours = Math.ceil(estimated / 3600);
          this.setData({
            estimatedTime: `预计剩余 ${hours} 小时`
          });
        }
      } else {
        this.setData({
          estimatedTime: '正在估算时间...'
        });
      }
    },

    /**
     * 获取进度文本
     * @private
     * @param {Object} status 
     * @returns {string}
     */
    _getProgressText(status) {
      if (status.progress >= 100) {
        return '诊断完成';
      }
      if (status.status === 'failed' || status.status === 'timeout') {
        return '诊断中断';
      }
      if (status.status === 'partial_success') {
        return '部分完成';
      }
      return `诊断中 ${Math.round(status.progress || 0)}%`;
    },

    /**
     * 获取阶段文本
     * @private
     * @param {Object} status 
     * @returns {string}
     */
    _getStageText(status) {
      const stageMap = {
        'initializing': '正在初始化...',
        'init': '正在初始化...',
        'ai_fetching': '正在获取 AI 平台数据...',
        'analyzing': '正在分析数据...',
        'intelligence_analyzing': '正在进行深度分析...',
        'competition_analyzing': '正在生成竞争分析...',
        'completed': '已完成',
        'partial_success': '部分完成',
        'failed': '诊断失败',
        'timeout': '诊断超时'
      };

      const stage = status?.stage || status?.status || 'unknown';
      return stageMap[stage] || stage || '准备中...';
    },

    /**
     * 获取进度颜色
     * @private
     * @param {Object} status 
     * @returns {string}
     */
    _getProgressColor(status) {
      if (status.status === 'failed' || status.status === 'timeout') {
        return '#ff4d4f';
      }
      if (status.status === 'partial_success') {
        return '#faad14';
      }
      if (status.progress >= 100) {
        return '#52c41a';
      }
      if (status.progress > 80) {
        return '#73d13d';
      }
      if (status.progress > 50) {
        return '#1890ff';
      }
      return '#07c160';
    },

    /**
     * 获取阶段图标
     * @private
     * @param {Object} status 
     * @returns {string}
     */
    _getStageIcon(status) {
      if (status.status === 'failed' || status.status === 'timeout') {
        return 'close-circle';
      }
      if (status.status === 'partial_success') {
        return 'warning-circle';
      }
      if (status.progress >= 100) {
        return 'check-circle';
      }
      return 'loading';
    },

    /**
     * 刷新显示
     * @public
     */
    refresh() {
      if (this.data.status) {
        this._updateDisplay(this.data.status);
      }
    }
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      console.log('[ProgressDisplay] Component attached');
    },
    detached() {
      console.log('[ProgressDisplay] Component detached');
    }
  }
});
