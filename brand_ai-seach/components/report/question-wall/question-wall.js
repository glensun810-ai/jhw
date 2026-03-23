/**
 * 问题诊断墙组件
 * 
 * 属性:
 * - title: 组件标题
 * - highRisks: 高风险问题列表
 * - mediumRisks: 中风险问题列表
 * - suggestions: 优化建议列表
 */

Component({
  properties: {
    title: {
      type: String,
      value: '问题诊断'
    },
    highRisks: {
      type: Array,
      value: []
    },
    mediumRisks: {
      type: Array,
      value: []
    },
    suggestions: {
      type: Array,
      value: []
    }
  },

  data: {
    hasContent: false
  },

  lifetimes: {
    attached: function() {
      this.checkContent();
    }
  },

  observers: {
    'highRisks,mediumRisks,suggestions': function(highRisks, mediumRisks, suggestions) {
      this.checkContent();
    }
  },

  methods: {
    /**
     * 检查是否有内容
     */
    checkContent: function() {
      const hasContent = 
        (this.data.highRisks && this.data.highRisks.length > 0) ||
        (this.data.mediumRisks && this.data.mediumRisks.length > 0) ||
        (this.data.suggestions && this.data.suggestions.length > 0);
      
      this.setData({ hasContent });
    }
  }
});
