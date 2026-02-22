/**
 * 分析图表主组件 - 重构简化版
 * 
 * 重构说明:
 * - 雷达图 → RadarChart/index.js
 * - 趋势图 → TrendChart/index.js
 * 
 * 本文件保留:
 * - 组件协调
 * - 数据传递
 * - 事件转发
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    radarData: {
      type: Object,
      value: null
    },
    trendData: {
      type: Object,
      value: null
    },
    loading: {
      type: Boolean,
      value: false
    },
    // 图表高度
    chartHeight: {
      type: Number,
      value: 300
    }
  },

  data: {
    // 本地状态
  },

  lifetimes: {
    attached() {
      console.log('[AnalysisCharts] 组件已挂载');
    }
  },

  methods: {
    /**
     * 雷达图渲染完成
     */
    onRadarComplete() {
      console.log('[AnalysisCharts] 雷达图渲染完成');
      this.triggerEvent('radarcomplete');
    },

    /**
     * 趋势图渲染完成
     */
    onTrendComplete() {
      console.log('[AnalysisCharts] 趋势图渲染完成');
      this.triggerEvent('trendcomplete');
    },

    /**
     * 所有图表渲染完成
     */
    onAllComplete() {
      this.triggerEvent('allcomplete');
    },

    /**
     * 刷新图表
     */
    refreshCharts() {
      // 触发子组件刷新
      this.triggerEvent('refresh');
    }
  },

  observers: {
    'radarData,trendData': function(radarData, trendData) {
      // 数据变化时，子组件会自动监听并更新
    }
  }
});
