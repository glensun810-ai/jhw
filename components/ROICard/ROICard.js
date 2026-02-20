// components/ROICard/ROICard.js
/**
 * P0 级空缺修复：ROI 指标卡片组件
 * 
 * 属性:
 * - title: 卡片标题
 * - subtitle: 副标题
 * - roiData: ROI 数据 {exposure_roi, sentiment_roi, ranking_roi, estimated_value}
 * - impactScores: 影响力评分 {authority_impact, visibility_impact, sentiment_impact, overall_impact}
 * - benchmarks: 行业基准数据
 * - showDelta: 是否显示与行业基准的对比
 * - showImpact: 是否显示影响力评分
 * - showDetail: 是否显示查看详情按钮
 */
Component({
  properties: {
    title: {
      type: String,
      value: 'ROI 指标'
    },
    subtitle: {
      type: String,
      value: ''
    },
    roiData: {
      type: Object,
      value: {
        exposure_roi: 0,
        sentiment_roi: 0,
        ranking_roi: 0,
        estimated_value: 0
      }
    },
    impactScores: {
      type: Object,
      value: {
        authority_impact: 0,
        visibility_impact: 0,
        sentiment_impact: 0,
        overall_impact: 0
      }
    },
    benchmarks: {
      type: Object,
      value: {
        exposure_roi_industry_avg: 2.5,
        sentiment_roi_industry_avg: 0.6,
        ranking_roi_industry_avg: 50
      }
    },
    showDelta: {
      type: Boolean,
      value: true
    },
    showImpact: {
      type: Boolean,
      value: true
    },
    showDetail: {
      type: Boolean,
      value: false
    }
  },

  data: {
  },

  methods: {
    /**
     * 格式化价值数字
     */
    formatValue(value) {
      if (value >= 10000) {
        return (value / 10000).toFixed(1) + '万';
      } else if (value >= 1000) {
        return (value / 1000).toFixed(1) + '千';
      }
      return value.toFixed(0);
    },

    /**
     * 点击卡片
     */
    onCardTap() {
      this.triggerEvent('cardtap', {
        roiData: this.data.roiData,
        impactScores: this.data.impactScores
      });
    },

    /**
     * 获取 ROI 等级
     */
    getROILevel(value, benchmark) {
      if (value >= benchmark * 1.5) return 'excellent';
      if (value >= benchmark) return 'good';
      if (value >= benchmark * 0.8) return 'average';
      return 'poor';
    }
  },

  lifetimes: {
    attached() {
      console.log('[ROICard] attached');
    },
    detached() {
      console.log('[ROICard] detached');
    }
  }
});
