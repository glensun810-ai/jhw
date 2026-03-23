/**
 * 情感对比柱状图组件
 * 
 * 功能：
 * - 展示各品牌情感分布对比
 * - 正面/中性/负面情感可视化
 * - 支持堆叠柱状图
 * 
 * @author 系统架构组
 * @date 2026-02-28
 */

import * as echarts from '../ec-canvas/echarts';

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 情感数据
    sentimentData: {
      type: Array,
      value: [],
      observer: 'onDataChange'
    },
    // 是否加载中
    loading: {
      type: Boolean,
      value: false
    },
    // 图表高度
    height: {
      type: Number,
      value: 350
    },
    // 标题
    title: {
      type: String,
      value: '品牌情感对比'
    }
  },

  data: {
    barEc: {
      onInit: null
    },
    chartInstance: null
  },

  lifetimes: {
    attached() {
      console.log('[SentimentBar] 组件已挂载');
    },
    detached() {
      this.disposeChart();
    }
  },

  methods: {
    /**
     * 数据变化监听
     */
    onDataChange() {
      if (this.data.chartInstance) {
        this.renderChart();
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

      // 渲染图表
      this.renderChart();

      return chart;
    },

    /**
     * 渲染图表
     */
    renderChart() {
      const chart = this.data.chartInstance;
      if (!chart) return;

      const option = this.getChartOption();
      chart.setOption(option, true);
    },

    /**
     * 获取图表配置
     */
    getChartOption() {
      const { sentimentData } = this.data;

      // 品牌名称
      const brands = sentimentData.map(item => item.brand || '未知品牌');

      // 情感分布数据
      const positiveData = sentimentData.map(item => {
        const positiveCount = item.positive_count || 0;
        const totalCount = item.mentioned_count || 1;
        return Math.round((positiveCount / totalCount) * 100);
      });

      const neutralData = sentimentData.map(item => {
        const mentionRate = item.mention_rate || 0;
        const positiveRate = (item.positive_count || 0) / (item.mentioned_count || 1);
        const negativeRate = (item.negative_count || 0) / (item.mentioned_count || 1);
        return Math.round((1 - positiveRate - negativeRate) * 100);
      });

      const negativeData = sentimentData.map(item => {
        const negativeCount = item.negative_count || 0;
        const totalCount = item.mentioned_count || 1;
        return Math.round((negativeCount / totalCount) * 100);
      });

      return {
        title: {
          text: this.properties.title,
          left: 'center',
          textStyle: {
            fontSize: 16,
            fontWeight: 'bold',
            color: '#2c3e50'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          },
          formatter: (params) => {
            let result = `<div style="font-weight:bold;">${params[0].name}</div>`;
            params.forEach(param => {
              const color = param.color;
              const value = param.value;
              const name = param.seriesName;
              result += `<div style="display:flex;align-items:center;margin-top:4px;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:8px;"></span>
                <span>${name}: ${value}%</span>
              </div>`;
            });
            return result;
          }
        },
        legend: {
          data: ['正面', '中性', '负面'],
          bottom: 10,
          textStyle: {
            fontSize: 12
          },
          itemWidth: 16,
          itemHeight: 10
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: brands,
          axisLabel: {
            interval: 0,
            rotate: 0,
            fontSize: 12,
            color: '#666',
            formatter: (value) => {
              if (value.length > 4) {
                return value.substring(0, 4) + '...';
              }
              return value;
            }
          },
          axisLine: {
            lineStyle: {
              color: '#ddd'
            }
          },
          axisTick: {
            show: false
          }
        },
        yAxis: {
          type: 'value',
          name: '占比 (%)',
          min: 0,
          max: 100,
          interval: 20,
          axisLabel: {
            formatter: '{value}%',
            color: '#666'
          },
          splitLine: {
            lineStyle: {
              color: '#eee',
              type: 'dashed'
            }
          },
          axisLine: {
            show: false
          },
          axisTick: {
            show: false
          }
        },
        series: [
          {
            name: '正面',
            type: 'bar',
            stack: 'total',
            barWidth: '50%',
            data: positiveData,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#2ecc71' },
                { offset: 1, color: '#27ae60' }
              ]),
              borderRadius: [4, 4, 0, 0]
            },
            emphasis: {
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#27ae60' },
                  { offset: 1, color: '#2ecc71' }
                ])
              }
            }
          },
          {
            name: '中性',
            type: 'bar',
            stack: 'total',
            data: neutralData,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#f39c12' },
                { offset: 1, color: '#e67e22' }
              ]),
              borderRadius: [0, 0, 0, 0]
            },
            emphasis: {
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#e67e22' },
                  { offset: 1, color: '#f39c12' }
                ])
              }
            }
          },
          {
            name: '负面',
            type: 'bar',
            stack: 'total',
            data: negativeData,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#e74c3c' },
                { offset: 1, color: '#c0392b' }
              ]),
              borderRadius: [0, 0, 4, 4]
            },
            emphasis: {
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#c0392b' },
                  { offset: 1, color: '#e74c3c' }
                ])
              }
            }
          }
        ]
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
    }
  }
});
