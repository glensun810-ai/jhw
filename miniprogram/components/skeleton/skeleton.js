/**
 * 骨架屏组件逻辑
 * 
 * 支持多种显示模式：
 * - report: 报告页面骨架屏
 * - list: 列表骨架屏
 * - card: 卡片骨架屏
 * - text: 文本骨架屏
 */

Component({
  /**
   * 组件属性
   */
  properties: {
    // 骨架屏模式：report | list | card | text
    mode: {
      type: String,
      value: 'report'
    },
    // 列表/卡片模式时的数量
    count: {
      type: Number,
      value: 5
    },
    // 文本模式时的行数
    lines: {
      type: Number,
      value: 3
    },
    // 文本模式时每行的宽度百分比（可选）
    lineWidths: {
      type: Array,
      value: []
    }
  },

  /**
   * 组件数据
   */
  data: {
    // 默认每行宽度：100%, 90%, 80%
    defaultLineWidths: ['100%', '90%', '80%']
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      console.log('[Skeleton] Component attached with mode:', this.data.mode);
      
      // 如果 lineWidths 为空且为文本模式，使用默认值
      if (this.data.mode === 'text' && this.data.lineWidths.length === 0) {
        const defaultLineWidths = [];
        for (let i = 0; i < this.data.lines; i++) {
          defaultLineWidths.push(`${100 - i * 10}%`);
        }
        this.setData({ lineWidths: defaultLineWidths });
      }
    },
    
    detached() {
      console.log('[Skeleton] Component detached');
    }
  },

  /**
   * 组件方法
   */
  methods: {
    /**
     * 更新骨架屏模式
     * @param {string} mode - 新模式
     */
    updateMode(mode) {
      this.setData({ mode });
    },
    
    /**
     * 更新数量（用于 list/card 模式）
     * @param {number} count - 新数量
     */
    updateCount(count) {
      this.setData({ count });
    }
  }
});
