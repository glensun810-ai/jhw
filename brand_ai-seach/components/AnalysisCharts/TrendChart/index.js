/**
 * 趋势图组件
 * 
 * 职责：
 * - ECharts 折线图渲染
 * - 数据格式化
 * - 空状态处理
 */

import * as echarts from '../../ec-canvas/echarts';

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 趋势图数据
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
    trendEc: {
      onInit: null
    },
    chartInstance: null
  },

  lifetimes: {
    attached() {
      console.log('[TrendChart] 组件已挂载');
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

      const { dates, values, predictions } = this.formatData(data);

      const series = [
        {
          name: '实际值',
          type: 'line',
          data: values,
          smooth: true,
          lineStyle: {
            color: '#667eea',
            width: 3
          },
          itemStyle: {
            color: '#667eea'
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.01)' }
            ])
          }
        }
      ];

      // 添加预测数据
      if (predictions && predictions.length > 0) {
        series.push({
          name: '预测值',
          type: 'line',
          data: predictions,
          smooth: true,
          lineStyle: {
            color: '#52c41a',
            width: 3,
            type: 'dashed'
          },
          itemStyle: {
            color: '#52c41a'
          }
        });
      }

      const option = {
        grid: {
          left: '10%',
          right: '5%',
          top: '10%',
          bottom: '15%'
        },
        xAxis: {
          type: 'category',
          data: dates,
          axisLabel: {
            rotate: 45,
            interval: 0
          }
        },
        yAxis: {
          type: 'value',
          max: 100,
          axisLabel: {
            formatter: '{value}'
          }
        },
        series: series
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
          text: '暂无趋势图数据',
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
      return {
        dates: data.dates || [],
        values: data.values || [],
        predictions: data.predictions || []
      };
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
