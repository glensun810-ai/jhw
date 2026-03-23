/**
 * 信源列表组件
 * 
 * 属性:
 * - title: 组件标题
 * - sources: 信源列表
 * - showCount: 是否显示数量
 */

Component({
  properties: {
    title: {
      type: String,
      value: '信源分析'
    },
    sources: {
      type: Array,
      value: []
    },
    showCount: {
      type: Boolean,
      value: true
    }
  },

  lifetimes: {
    attached: function() {
      this.processSources();
    }
  },

  observers: {
    'sources': function(newSources) {
      this.processSources();
    }
  },

  methods: {
    /**
     * 处理信源数据
     */
    processSources: function() {
      const sources = this.data.sources.map(item => {
        // 权威度等级
        let authorityClass = '';
        let authorityText = '';
        const authority = item.domain_authority || item.authority;
        
        if (authority === '高' || authority > 80) {
          authorityClass = 'authority-high';
          authorityText = '权威';
        } else if (authority === '中' || authority > 50) {
          authorityClass = 'authority-medium';
          authorityText = '一般';
        } else {
          authorityClass = 'authority-low';
          authorityText = '较低';
        }
        
        // 风险等级
        let riskClass = '';
        let riskLevel = '';
        const risk = item.risk_level || item.riskLevel;
        
        if (risk === 'High' || risk === '高') {
          riskClass = 'risk-high';
          riskLevel = '高';
        } else if (risk === 'Medium' || risk === '中') {
          riskClass = 'risk-medium';
          riskLevel = '中';
        } else if (risk === 'Low' || risk === '低') {
          riskClass = 'risk-low';
          riskLevel = '低';
        }
        
        return {
          ...item,
          authorityClass,
          authorityText,
          riskClass,
          riskLevel
        };
      });
      
      this.setData({ sources });
    }
  }
});
