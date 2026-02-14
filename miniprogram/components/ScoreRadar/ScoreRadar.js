// components/ScoreRadar/ScoreRadar.js
import * as echarts from '../ec-canvas/echarts';

Component({
  options: {
    addGlobalClass: true
  },

  /**
   * 组件的属性列表
   */
  properties: {
    scores: {
      type: Object,
      value: null
    },
    title: {
      type: String,
      value: '品牌认知评分雷达图'
    },
    loading: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    ec: {
      onInit: null
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    initChart(canvas, width, height, dpr) {
      const chart = echarts.init(canvas, null, {
        width: width,
        height: height,
        devicePixelRatio: dpr
      });
      canvas.setChart(chart);

      // 设置默认空图表
      this.renderEmptyChart(chart);
      
      // 保存图表实例
      this.setData({
        chartInstance: chart
      });

      return chart;
    },

    renderEmptyChart(chart) {
      const option = {
        title: {
          text: '暂无评分数据',
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

    renderChart() {
      if (!this.data.chartInstance || !this.properties.scores) {
        // 如果没有实例或数据，渲染空图表
        if (this.data.chartInstance) {
          this.renderEmptyChart(this.data.chartInstance);
        }
        return;
      }

      // 从 scores 属性中提取雷达图数据
      const scores = this.properties.scores;
      
      // 定义雷达图的维度
      const indicatorData = [
        { name: '准确性', max: 100, value: scores.accuracy || scores.Accuracy || 0 },
        { name: '完整性', max: 100, value: scores.completeness || scores.Completeness || 0 },
        { name: '相关性', max: 100, value: scores.relevance || scores.Relevance || 0 },
        { name: '安全性', max: 100, value: scores.security || scores.Security || 0 },
        { name: '情感分', max: 100, value: scores.sentiment || scores.Sentiment || 0 }
      ];

      // 提取数值数组
      const scoreValues = indicatorData.map(item => item.value);

      const option = {
        title: {
          text: this.properties.title,
          textStyle: {
            color: '#e8e8e8',
            fontSize: 16
          },
          left: 'center',
          top: 20
        },
        tooltip: {},
        radar: {
          indicator: indicatorData.map(indicator => ({
            name: indicator.name,
            max: indicator.max
          })),
          name: {
            textStyle: {
              color: '#e8e8e8'
            }
          },
          axisLine: {
            lineStyle: {
              color: '#3a3a3a'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#262626'
            }
          },
          splitArea: {
            show: false
          }
        },
        series: [{
          name: '品牌认知评分',
          type: 'radar',
          areaStyle: {
            color: 'rgba(0, 169, 255, 0.3)',
            opacity: 0.5
          },
          data: [
            {
              value: scoreValues,
              name: '当前评分',
              itemStyle: {
                color: '#00A9FF'
              },
              lineStyle: {
                color: '#00A9FF',
                width: 2
              }
            }
          ]
        }],
        backgroundColor: 'transparent'
      };

      this.data.chartInstance.setOption(option);
    }
  },
  
  lifetimes: {
    attached() {
      // 初始化 ECharts
      this.data.ec.onInit = this.initChart.bind(this);
    },
    
    ready() {
      // 数据准备好后渲染图表
      if (this.properties.scores && !this.properties.loading) {
        // 延迟渲染以确保图表容器已准备就绪
        setTimeout(() => {
          this.renderChart();
        }, 100);
      }
    }
  },
  
  observers: {
    'scores, loading': function(newScores, newLoading) {
      if (!newLoading && newScores) {
        // 数据更新时重新渲染图表
        setTimeout(() => {
          this.renderChart();
        }, 50);
      } else if (newLoading) {
        // 加载中时显示空图表
        if (this.data.chartInstance) {
          this.renderEmptyChart(this.data.chartInstance);
        }
      }
    }
  }
})