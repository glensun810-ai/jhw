// components/AnalysisCharts/AnalysisCharts.js
import * as echarts from '../ec-canvas/echarts';

Component({
  options: {
    addGlobalClass: true
  },

  /**
   * 组件的属性列表
   */
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
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    radarEc: {
      onInit: null
    },
    trendEc: {
      onInit: null
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    // 初始化雷达图
    initRadarChart(canvas, width, height, dpr) {
      const chart = echarts.init(canvas, null, {
        width: width,
        height: height,
        devicePixelRatio: dpr
      });
      canvas.setChart(chart);

      // 设置默认空图表
      this.renderEmptyRadarChart(chart);

      // 保存图表实例
      this.setData({
        radarChartInstance: chart
      });

      return chart;
    },

    // 初始化趋势图
    initTrendChart(canvas, width, height, dpr) {
      const chart = echarts.init(canvas, null, {
        width: width,
        height: height,
        devicePixelRatio: dpr
      });
      canvas.setChart(chart);

      // 设置默认空图表
      this.renderEmptyTrendChart(chart);

      // 保存图表实例
      this.setData({
        trendChartInstance: chart
      });

      return chart;
    },

    // 渲染空雷达图
    renderEmptyRadarChart(chart) {
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

    // 渲染空趋势图
    renderEmptyTrendChart(chart) {
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

    // 渲染雷达图
    renderRadarChart() {
      if (!this.data.radarChartInstance || !this.properties.radarData) {
        if (this.data.radarChartInstance) {
          this.renderEmptyRadarChart(this.data.radarChartInstance);
        }
        return;
      }

      const radarData = this.properties.radarData;
      
      // 定义雷达图的维度
      const indicatorData = [
        { name: '准确度', max: 100, value: radarData.accuracy || 0 },
        { name: '完整性', max: 100, value: radarData.completeness || 0 },
        { name: '情感分', max: 100, value: radarData.sentiment || 0 },
        { name: '竞品隔离度', max: 100, value: radarData.competitiveness || 0 },
        { name: '信源权威度', max: 100, value: radarData.authority || 0 }
      ];

      // 提取数值数组
      const scoreValues = indicatorData.map(item => item.value);

      const option = {
        backgroundColor: 'transparent',
        color: ['#00E5FF'],
        tooltip: {},
        animationDuration: 1500, // 缓动效果
        radar: {
          indicator: indicatorData.map(indicator => ({
            name: indicator.name,
            max: indicator.max
          })),
          name: {
            textStyle: {
              color: '#e8e8e8',
              fontSize: 14
            }
          },
          axisLine: {
            lineStyle: {
              color: 'rgba(26, 35, 126, 0.5)' // 深海蓝色系
            }
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(26, 35, 126, 0.3)'
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
            color: 'rgba(0, 229, 255, 0.4)', // 半透明的青色
            opacity: 0.5
          },
          data: [
            {
              value: scoreValues,
              name: '当前评分',
              itemStyle: {
                color: '#00E5FF'
              },
              lineStyle: {
                color: '#00E5FF',
                width: 2
              }
            }
          ]
        }]
      };

      this.data.radarChartInstance.setOption(option);
    },

    // 渲染趋势图
    renderTrendChart() {
      if (!this.data.trendChartInstance || !this.properties.trendData) {
        if (this.data.trendChartInstance) {
          this.renderEmptyTrendChart(this.data.trendChartInstance);
        }
        return;
      }

      const trendData = this.properties.trendData;
      
      // 准备趋势图数据
      const dates = trendData.dates || [];
      const values = trendData.values || [];
      const predictions = trendData.predictions || [];

      const option = {
        backgroundColor: 'transparent',
        color: ['#00E5FF', '#1A237E'],
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(26, 35, 126, 0.9)',
          borderColor: '#303030',
          textStyle: {
            color: '#e8e8e8'
          }
        },
        legend: {
          data: ['历史数据', '预测数据'],
          textStyle: {
            color: '#e8e8e8'
          },
          top: 10
        },
        animationDuration: 1500, // 缓动效果
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: dates,
          axisLine: {
            lineStyle: {
              color: 'rgba(26, 35, 126, 0.5)'
            }
          },
          axisLabel: {
            color: '#8c8c8c'
          }
        },
        yAxis: {
          type: 'value',
          axisLine: {
            lineStyle: {
              color: 'rgba(26, 35, 126, 0.5)'
            }
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(26, 35, 126, 0.3)'
            }
          },
          axisLabel: {
            color: '#8c8c8c'
          }
        },
        series: [
          {
            name: '历史数据',
            type: 'line',
            data: values,
            smooth: true, // 平滑曲线
            symbolSize: 8,
            itemStyle: {
              color: '#00E5FF'
            },
            lineStyle: {
              color: '#00E5FF',
              width: 3
            },
            areaStyle: { // 渐变色填充区域
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(0, 229, 255, 0.3)' // 起始颜色
                }, {
                  offset: 1, color: 'rgba(0, 229, 255, 0.05)' // 结束颜色
                }]
              }
            }
          },
          {
            name: '预测数据',
            type: 'line',
            data: predictions,
            smooth: true, // 平滑曲线
            symbolSize: 8,
            itemStyle: {
              color: '#1A237E'
            },
            lineStyle: {
              color: '#1A237E',
              width: 2,
              type: 'dashed' // 虚线表示预测
            },
            areaStyle: { // 渐变色填充区域
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(26, 35, 126, 0.3)' // 起始颜色
                }, {
                  offset: 1, color: 'rgba(26, 35, 126, 0.05)' // 结束颜色
                }]
              }
            }
          }
        ]
      };

      this.data.trendChartInstance.setOption(option);
    }
  },

  lifetimes: {
    attached() {
      // 初始化 ECharts
      this.data.radarEc.onInit = this.initRadarChart.bind(this);
      this.data.trendEc.onInit = this.initTrendChart.bind(this);
    },

    ready() {
      // 数据准备好后渲染图表
      if (!this.properties.loading) {
        // 延迟渲染以确保图表容器已准备就绪
        setTimeout(() => {
          this.renderRadarChart();
          this.renderTrendChart();
        }, 100);
      }
    }
  },

  observers: {
    'radarData, trendData, loading': function(radarData, trendData, loading) {
      if (!loading && (radarData || trendData)) {
        // 数据更新时重新渲染图表
        setTimeout(() => {
          if (radarData) {
            this.renderRadarChart();
          }
          if (trendData) {
            this.renderTrendChart();
          }
        }, 50);
      } else if (loading) {
        // 加载中时显示空图表
        if (this.data.radarChartInstance) {
          this.renderEmptyRadarChart(this.data.radarChartInstance);
        }
        if (this.data.trendChartInstance) {
          this.renderEmptyTrendChart(this.data.trendChartInstance);
        }
      }
    }
  }
})