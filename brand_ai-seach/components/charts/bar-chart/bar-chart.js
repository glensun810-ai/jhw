/**
 * 柱状图组件
 * 
 * 属性:
 * - data: 数据数组 [{name: '品牌 A', value: 85, color: '#4A7BFF'}]
 * - title: 图表标题
 * - maxValue: Y 轴最大值 (默认 100)
 * - showValue: 是否显示数值
 * - showYAxis: 是否显示 Y 轴
 * - defaultColor: 默认颜色
 */

Component({
  properties: {
    data: {
      type: Array,
      value: [],
      observer: 'onDataChange'
    },
    title: {
      type: String,
      value: ''
    },
    maxValue: {
      type: Number,
      value: 100
    },
    showValue: {
      type: Boolean,
      value: true
    },
    showYAxis: {
      type: Boolean,
      value: true
    },
    defaultColor: {
      type: String,
      value: '#4A7BFF'
    }
  },

  data: {
    Math: Math
  },

  lifetimes: {
    attached: function() {
      this.initChart();
    }
  },

  methods: {
    onDataChange: function(newData) {
      this.initChart();
    },

    /**
     * 初始化图表
     */
    initChart: function() {
      if (!this.data.data || this.data.data.length === 0) {
        return;
      }

      // 计算最大值
      const values = this.data.data.map(item => item.value);
      const max = Math.max(...values);
      
      // 设置最大值为稍大于实际最大值的整数
      const maxValue = Math.ceil(max / 10) * 10 || 100;
      
      this.setData({ maxValue });
    }
  }
});
