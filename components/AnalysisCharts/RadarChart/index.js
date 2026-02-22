/**
 * 雷达图组件
 * 
 * 职责：
 * - ECharts 雷达图渲染
 * - 数据格式化
 * - 空状态处理
 */

import * as echarts from '../../ec-canvas/echarts';

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 雷达图数据
    data: {
      type: Object,
      value: null,
      observer: 'onDataChange'
    },
    // 是否加载中
    loading: {
      type: Boolean,
      value: false
    },
    // 高度
    height: {
      type: Number,
      value: 300
    }
  },

  data: {
    radarEc: {
      onInit: null
    },
    chartInstance: null
  },

  lifetimes: {
    attached() {
      console.log('[RadarChart] 组件已挂载');
    },
    detached() {
      this.disposeChart();
    }
  },

  methods: {
    /**
     * 数据变化监听
     */
    onDataChange(newVal) {
      if (newVal && this.data.chartInstance) {
        this.renderChart(newVal);
      }
    },

    /**
     * 初始化图表
     */
    initChart(canvas, width, height, dpr) {
      const chart = echarts.init(canvas, null, {
        width: width,
        height: height,
        devicePixelRatio: dpr
      });
      canvas.setChart(chart);

      // 保存图表实例
      this.setData({ chartInstance: chart });

      // 如果有数据，渲染图表
      if (this.data.data) {
        this.renderChart(this.data.data);
      } else {
        this.renderEmptyChart(chart);
      }

      return chart;
    },

    /**
     * 渲染图表
     */
    renderChart(data) {
      const chart = this.data.chartInstance;
      if (!chart) return;

      const { indicators, series } = this.formatData(data);

      const option = {
        radar: {
          indicator: indicators,
          radius: '65%',
          center: ['50%', '50%']
        },
        series: [{
          type: 'radar',
          data: series,
          emphasis: {
            lineStyle: {
              width: 4
            }
          }
        }]
      };

      chart.setOption(option);
      this.triggerEvent('rendercomplete');
    },

    /**
     * 渲染空图表
     */
    renderEmptyChart(chart) {
      const option = {
        title: {
          text: '暂无雷达图数据',
          left: 'center',
          top: 'center',
          textStyle: {
            color: '#8c8c8c',
            fontSize: 16
          }
        },
        backgroundColor: 'transparent'
      };
      chart.setOption(option);
    },

    /**
     * 格式化数据
     */
    formatData(data) {
      const indicators = (data.indicators || []).map(item => ({
        name: item.name,
        max: item.max || 100
      }));

      const series = (data.series || []).map(item => ({
        name: item.name,
        value: item.value,
        areaStyle: {
          color: item.color || 'rgba(102, 126, 234, 0.3)'
        },
        lineStyle: {
          color: item.color || '#667eea'
        }
      }));

      return { indicators, series };
    },

    /**
     * 销毁图表
     */
    disposeChart() {
      if (this.data.chartInstance) {
        this.data.chartInstance.dispose();
        this.setData({ chartInstance: null });
      }
    },

    /**
     * 刷新图表
     */
    refresh() {
      if (this.data.chartInstance) {
        this.data.chartInstance.resize();
      }
    }
  }
});
