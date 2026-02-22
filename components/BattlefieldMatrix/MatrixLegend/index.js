/**
 * 矩阵图例组件
 * 
 * 职责：
 * - 图例显示
 * - 状态说明
 * - 视图切换
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 当前视图
    currentView: {
      type: String,
      value: 'standard'
    },
    // 视图选项
    viewOptions: {
      type: Array,
      value: [
        { value: 'standard', label: '标准视图', icon: '📊' },
        { value: 'model', label: '模型视图', icon: '🤖' },
        { value: 'question', label: '问题视图', icon: '❓' }
      ]
    }
  },

  data: {
    // 图例项
    legendItems: [
      { status: 'success', label: '成功', icon: '✅', color: '#52c41a' },
      { status: 'error', label: '失败', icon: '❌', color: '#ff4d4f' },
      { status: 'positive', label: '正面', icon: '😊', color: '#1890ff' },
      { status: 'negative', label: '负面', icon: '😟', color: '#fa8c16' },
      { status: 'neutral', label: '中性', icon: '😐', color: '#d9d9d9' }
    ]
  },

  lifetimes: {
    attached() {
      console.log('[MatrixLegend] 组件已挂载');
    }
  },

  methods: {
    /**
     * 视图切换
     */
    onViewChange(e) {
      const { view } = e.currentTarget.dataset;
      this.triggerEvent('viewchange', { view });
    },

    /**
     * 获取图例样式
     */
    getLegendItemClass(item) {
      return `legend-item legend-${item.status}`;
    }
  }
});
