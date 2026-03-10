/**
 * 趋势图组件
 * 
 * 属性:
 * - data: 数据数组 [{value: 85, label: '1 月'}]
 * - title: 图表标题
 * - color: 线条颜色
 * - showValue: 是否显示数值
 * - showYAxis: 是否显示 Y 轴
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
    color: {
      type: String,
      value: '#4A7BFF'
    },
    showValue: {
      type: Boolean,
      value: true
    },
    showYAxis: {
      type: Boolean,
      value: true
    }
  },

  data: {
    points: [],
    labels: [],
    maxValue: 100,
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
        this.setData({ points: [], labels: [] });
        return;
      }

      const data = this.data.data;
      const values = data.map(item => item.value);
      const labels = data.map(item => item.label);
      
      // 计算最大值
      const max = Math.max(...values);
      const maxValue = Math.ceil(max / 10) * 10 || 100;
      
      // 计算点位置
      const points = data.map((item, index) => {
        const x = (index / (data.length - 1)) * 100;
        const y = 100 - (item.value / maxValue * 100);
        return { x, y, value: item.value };
      });
      
      this.setData({ points, labels, maxValue });
    }
  }
});
