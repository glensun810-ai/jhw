// components/TrendChart/TrendChart.js
import * as echarts from '../ec-canvas/echarts';

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    chartData: {
      type: Object,
      value: null
    },
    predictionData: {
      type: Object,
      value: null
    },
    title: {
      type: String,
      value: '趋势图表'
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
      
      // 监听数据变化
      this.setData({
        chartInstance: chart
      });

      return chart;
    },

    renderEmptyChart(chart) {
      const option = {
        title: {
          text: '暂无数据',
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
      if (!this.data.chartInstance || (!this.properties.chartData && !this.properties.predictionData)) {
        // 如果没有实例或数据，渲染空图表
        if (this.data.chartInstance) {
          this.renderEmptyChart(this.data.chartInstance);
        }
        return;
      }

      // 优先使用预测数据，否则使用图表数据
      const predictionData = this.properties.predictionData;
      const chartData = this.properties.chartData;

      let option;

      if (predictionData && predictionData.forecast_points) {
        // 趋势预测折线图
        const forecastPoints = predictionData.forecast_points;
        const periods = forecastPoints.map((_, index) => `Week ${index + 1}`);
        const values = forecastPoints.map(point => point.value || point.score || 0);

        option = {
          title: {
            text: this.properties.title,
            textStyle: {
              color: '#e8e8e8',
              fontSize: 16
            },
            left: 'center'
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(26, 32, 44, 0.9)',
            borderColor: '#303030',
            textStyle: {
              color: '#e8e8e8'
            }
          },
          xAxis: {
            type: 'category',
            data: periods,
            axisLine: {
              lineStyle: {
                color: '#3a3a3a'
              }
            },
            axisLabel: {
              color: '#8c8c8c'
            }
          },
          yAxis: {
            type: 'value',
            min: 0,
            max: 100,
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
            axisLabel: {
              color: '#8c8c8c'
            }
          },
          series: [{
            name: 'GEO可见性得分',
            type: 'line',
            data: values,
            smooth: true, // 平滑曲线
            symbolSize: 8,
            itemStyle: {
              color: '#00F5A0'
            },
            lineStyle: {
              color: '#00F5A0',
              width: 3
            },
            areaStyle: { // 渐变色填充区域
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(0, 245, 160, 0.3)' // 起始颜色
                }, {
                  offset: 1, color: 'rgba(0, 245, 160, 0.05)' // 结束颜色
                }]
              }
            }
          }]
        };
      } else if (chartData && chartData.type === 'line') {
        // 常规线图
        option = {
          title: {
            text: this.properties.title,
            textStyle: {
              color: '#e8e8e8',
              fontSize: 16
            },
            left: 'center'
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(26, 32, 44, 0.9)',
            borderColor: '#303030',
            textStyle: {
              color: '#e8e8e8'
            }
          },
          legend: {
            data: chartData.series?.map(s => s.name) || [],
            textStyle: {
              color: '#e8e8e8'
            },
            top: 30
          },
          xAxis: {
            type: 'category',
            data: chartData.xAxis || [],
            axisLine: {
              lineStyle: {
                color: '#3a3a3a'
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
                color: '#3a3a3a'
              }
            },
            splitLine: {
              lineStyle: {
                color: '#262626'
              }
            },
            axisLabel: {
              color: '#8c8c8c'
            }
          },
          series: chartData.series?.map(series => ({
            ...series,
            type: 'line',
            smooth: true,
            itemStyle: {
              color: '#00A9FF'
            },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(0, 169, 255, 0.3)'
                }, {
                  offset: 1, color: 'rgba(0, 169, 255, 0.05)'
                }]
              }
            }
          })) || []
        };
      } else if (chartData && chartData.type === 'bar') {
        // 柱状图
        option = {
          title: {
            text: this.properties.title,
            textStyle: {
              color: '#e8e8e8',
              fontSize: 16
            },
            left: 'center'
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(26, 32, 44, 0.9)',
            borderColor: '#303030',
            textStyle: {
              color: '#e8e8e8'
            }
          },
          xAxis: {
            type: 'category',
            data: chartData.xAxis || [],
            axisLine: {
              lineStyle: {
                color: '#3a3a3a'
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
                color: '#3a3a3a'
              }
            },
            splitLine: {
              lineStyle: {
                color: '#262626'
              }
            },
            axisLabel: {
              color: '#8c8c8c'
            }
          },
          series: chartData.series?.map(series => ({
            ...series,
            type: 'bar',
            itemStyle: {
              color: '#00F5A0'
            }
          })) || []
        };
      } else {
        // 默认饼图
        option = {
          title: {
            text: this.properties.title,
            textStyle: {
              color: '#e8e8e8',
              fontSize: 16
            },
            left: 'center'
          },
          tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(26, 32, 44, 0.9)',
            borderColor: '#303030',
            textStyle: {
              color: '#e8e8e8'
            }
          },
          legend: {
            orient: 'vertical',
            left: 'left',
            textStyle: {
              color: '#e8e8e8'
            }
          },
          series: [{
            name: '数据分布',
            type: 'pie',
            radius: '50%',
            data: chartData.data || [],
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }]
        };
      }

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
      if (this.properties.chartData && !this.properties.loading) {
        // 延迟渲染以确保图表容器已准备就绪
        setTimeout(() => {
          this.renderChart();
        }, 100);
      }
    }
  },
  
  observers: {
    'chartData, loading': function(newChartData, newLoading) {
      if (!newLoading && newChartData) {
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