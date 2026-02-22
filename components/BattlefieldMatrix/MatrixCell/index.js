/**
 * 矩阵单元格组件
 * 
 * 职责：
 * - 单个单元格渲染
 * - 状态显示
 * - 点击交互
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 单元格数据
    cellData: {
      type: Object,
      value: null
    },
    // 行列索引
    rowIndex: {
      type: Number,
      value: 0
    },
    colIndex: {
      type: Number,
      value: 0
    },
    // 是否高亮
    highlight: {
      type: Boolean,
      value: false
    },
    // 是否禁用
    disabled: {
      type: Boolean,
      value: false
    }
  },

  data: {
    // 本地状态
  },

  lifetimes: {
    attached() {
      console.log('[MatrixCell] 组件已挂载');
    }
  },

  methods: {
    /**
     * 单元格点击
     */
    onTap() {
      if (this.data.disabled) return;
      
      this.triggerEvent('tap', {
        rowIndex: this.data.rowIndex,
        colIndex: this.data.colIndex,
        cellData: this.data.cellData
      });
    },

    /**
     * 获取状态样式类
     */
    getStatusClass() {
      const { cellData } = this.data;
      if (!cellData) return '';
      
      const { status, sentiment } = cellData;
      
      if (status === 'success') return 'cell-success';
      if (status === 'error') return 'cell-error';
      if (sentiment > 0.5) return 'cell-positive';
      if (sentiment < -0.5) return 'cell-negative';
      
      return 'cell-neutral';
    },

    /**
     * 获取状态图标
     */
    getStatusIcon() {
      const { cellData } = this.data;
      if (!cellData) return '';
      
      const { status, sentiment } = cellData;
      
      if (status === 'success') return '✅';
      if (status === 'error') return '❌';
      if (sentiment > 0.5) return '😊';
      if (sentiment < -0.5) return '😟';
      
      return '😐';
    },

    /**
     * 格式化分数
     */
    formatScore(score) {
      if (score === undefined || score === null) return '-';
      return Math.round(score);
    }
  }
});
