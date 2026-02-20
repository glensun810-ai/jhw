// components/ImpactGauge/ImpactGauge.js
/**
 * P0 级空缺修复：影响力仪表盘组件
 * 
 * 属性:
 * - impactScores: 影响力评分 {authority_impact, visibility_impact, sentiment_impact, overall_impact}
 * - showInsight: 是否显示解读建议
 * - title: 组件标题
 */
Component({
  properties: {
    impactScores: {
      type: Object,
      value: {
        authority_impact: 0,
        visibility_impact: 0,
        sentiment_impact: 0,
        overall_impact: 0
      }
    },
    showInsight: {
      type: Boolean,
      value: true
    },
    title: {
      type: String,
      value: '品牌影响力'
    }
  },

  data: {
    circumference: 502, // 2 * PI * 80
    dashOffset: 502,
    insightText: ''
  },

  observers: {
    'impactScores.overall_impact': function(score) {
      this.updateGauge(score);
      this.updateInsight(score);
    }
  },

  methods: {
    /**
     * 更新仪表盘
     */
    updateGauge(score) {
      // 限制分数在 0-100 之间
      const normalizedScore = Math.min(Math.max(score, 0), 100);
      const offset = this.data.circumference - (normalizedScore / 100) * this.data.circumference * 0.75;
      this.setData({ dashOffset: offset });
    },

    /**
     * 更新解读文本
     */
    updateInsight(score) {
      let text = '';
      if (score >= 80) {
        text = '品牌影响力优秀！继续保持当前的品牌策略和内容质量。';
      } else if (score >= 60) {
        text = '品牌影响力良好，可在弱势维度加大投入以提升整体表现。';
      } else if (score >= 40) {
        text = '品牌影响力一般，建议重点关注权威性和可见度的提升。';
      } else {
        text = '品牌影响力较弱，需要全面优化品牌策略和内容质量。';
      }
      this.setData({ insightText: text });
    },

    /**
     * 获取等级文本
     */
    getLevelText(score) {
      if (score >= 80) return '优秀';
      if (score >= 60) return '良好';
      if (score >= 40) return '一般';
      return '待提升';
    },

    /**
     * 获取等级样式类
     */
    getLevelClass(score) {
      if (score >= 80) return 'impact-gauge__level--excellent';
      if (score >= 60) return 'impact-gauge__level--good';
      if (score >= 40) return 'impact-gauge__level--average';
      return 'impact-gauge__level--poor';
    }
  },

  lifetimes: {
    attached() {
      this.updateGauge(this.data.impactScores.overall_impact);
      this.updateInsight(this.data.impactScores.overall_impact);
    }
  }
});
