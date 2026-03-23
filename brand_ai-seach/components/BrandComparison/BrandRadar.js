/**
 * 品牌对比雷达图组件
 * 
 * 功能：
 * - 展示用户品牌与竞品的多维度对比
 * - 支持多个品牌同时对比
 * - 自动计算雷达图指标
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
    // 品牌对比数据
    comparisonData: {
      type: Array,
      value: [],
      observer: 'onDataChange'
    },
    // 用户品牌数据
    userBrandData: {
      type: Object,
      value: null,
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
      value: '品牌竞争力对比'
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
      console.log('[BrandRadar] 组件已挂载');
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
      const { userBrandData, comparisonData } = this.data;

      // 构建雷达图指标
      const indicators = [
        { name: '提及率', max: 100 },
        { name: '排名', max: 5 },
        { name: '情感', max: 1, min: -1 },
        { name: '曝光度', max: 100 },
        { name: '影响力', max: 100 }
      ];

      // 构建系列数据
      const series = [];

      // 用户品牌数据
      if (userBrandData) {
        series.push({
          value: [
            (userBrandData.mention_rate || 0) * 100,
            userBrandData.average_rank > 0 ? userBrandData.average_rank : 5,
            userBrandData.average_sentiment || 0,
            this.calculateExposure(userBrandData),
            this.calculateInfluence(userBrandData)
          ],
          name: userBrandData.brand || '用户品牌',
          itemStyle: { color: '#e74c3c' },
          areaStyle: {
            color: 'rgba(231, 76, 60, 0.3)'
          }
        });
      }

      // 竞品品牌数据（最多 3 个）
      const colors = ['#3498db', '#2ecc71', '#f39c12'];
      if (comparisonData && comparisonData.length > 0) {
        comparisonData.slice(0, 3).forEach((brand, index) => {
          series.push({
            value: [
              (brand.mention_rate || 0) * 100,
              brand.average_rank > 0 ? brand.average_rank : 5,
              brand.average_sentiment || 0,
              this.calculateExposure(brand),
              this.calculateInfluence(brand)
            ],
            name: brand.brand || `竞品${index + 1}`,
            itemStyle: { color: colors[index] },
            areaStyle: {
              color: `rgba(${this.hexToRgb(colors[index])}, 0.2)`
            }
          });
        });
      }

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
          trigger: 'item',
          formatter: (params) => {
            const indicators = ['提及率', '排名', '情感', '曝光度', '影响力'];
            const values = params.value;
            let result = `<div style="font-weight:bold;">${params.name}</div>`;
            indicators.forEach((ind, i) => {
              let value = values[i];
              if (ind === '提及率' || ind === '曝光度' || ind === '影响力') {
                value = value.toFixed(1) + '%';
              } else if (ind === '情感') {
                value = value.toFixed(2);
              } else if (ind === '排名') {
                value = value === 5 ? '未入榜' : value.toFixed(1);
              }
              result += `<div>${ind}: ${value}</div>`;
            });
            return result;
          }
        },
        legend: {
          data: series.map(s => s.name),
          bottom: 10,
          textStyle: {
            fontSize: 12
          }
        },
        radar: {
          indicator: indicators,
          radius: '60%',
          center: ['50%', '45%'],
          shape: 'circle',
          splitNumber: 5,
          axisName: {
            color: '#666',
            fontSize: 12,
            formatter: (name) => {
              if (name === '排名') {
                return '排名↓';
              } else if (name === '情感') {
                return '情感±';
              }
              return name;
            }
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          },
          splitArea: {
            show: true,
            areaStyle: {
              color: ['rgba(245, 245, 245, 0.3)', 'rgba(240, 240, 240, 0.3)',
                      'rgba(235, 235, 235, 0.3)', 'rgba(230, 230, 230, 0.3)']
            }
          },
          axisLine: {
            lineStyle: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          }
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
    },

    /**
     * 计算曝光度
     */
    calculateExposure(brandData) {
      const mentionRate = (brandData.mention_rate || 0) * 100;
      const rankScore = brandData.average_rank > 0 
        ? Math.max(0, 100 - (brandData.average_rank - 1) * 20) 
        : 0;
      return (mentionRate + rankScore) / 2;
    },

    /**
     * 计算影响力
     */
    calculateInfluence(brandData) {
      const mentionRate = (brandData.mention_rate || 0) * 100;
      const sentiment = (brandData.average_sentiment || 0) * 50 + 50;
      const rankScore = brandData.average_rank > 0 
        ? Math.max(0, 100 - (brandData.average_rank - 1) * 20) 
        : 0;
      return (mentionRate + sentiment + rankScore) / 3;
    },

    /**
     * HEX 转 RGB
     */
    hexToRgb(hex) {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      return result ? 
        `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : 
        '0, 0, 0';
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
