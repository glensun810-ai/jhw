import * as echarts from '../ec-canvas/echarts';

Component({
  properties: {
    graphData: {
      type: Object,
      value: null,
      observer: 'initChart'
    }
  },

  data: {
    ec: {
      onInit: null
    },
    chart: null
  },

  lifetimes: {
    attached() {
      this.setData({
        'ec.onInit': this.initChartInstance
      });
    },
    detached() {
      if (this.data.chart) {
        this.data.chart.dispose();
        this.data.chart = null;
      }
    }
  },

  methods: {
    initChartInstance(canvas, width, height, dpr) {
      const chart = echarts.init(canvas, null, {
        width: width,
        height: height,
        devicePixelRatio: dpr
      });
      canvas.setChart(chart);
      this.data.chart = chart;

      // 绑定事件
      this.bindChartEvents();

      if (this.properties.graphData) {
        this.updateChart(this.properties.graphData);
      }
      
      return chart;
    },

    initChart(newVal) {
      if (newVal && this.data.chart) {
        this.updateChart(newVal);
      }
    },

    updateChart(graphData) {
      if (!graphData || !graphData.nodes) {
        return;
      }

      // 1. 数据预处理
      const nodes = graphData.nodes.map(node => {
        // 节点分级与样式
        switch (node.level) {
          case 0: // 品牌核心
            node.symbolSize = 60;
            node.itemStyle = { color: '#00F5A0' };
            break;
          case 1: // 高权重信源
            node.symbolSize = 45;
            node.itemStyle = { color: '#00A9FF' };
            break;
          case 2: // 次级信源
            node.symbolSize = 30;
            node.itemStyle = { color: '#8c8c8c' };
            break;
        }
        // 风险节点特殊样式
        if (node.source_type === 'competitor_controlled') {
            node.itemStyle = { color: '#F5222D' };
        }
        return node;
      });

      const links = graphData.links.map(link => {
        // 情感色彩
        if (link.sentiment_bias > 0.4) {
          link.lineStyle = { color: '#52C41A' }; // 翡翠绿
        } else if (link.sentiment_bias < -0.4) {
          link.lineStyle = { color: '#F5222D' }; // 警告深红
        } else {
          link.lineStyle = { color: '#595959' }; // 中性灰
        }
        // 连线粗细
        link.lineStyle.width = 1 + link.contribution_score * 4;

        // 闪烁报警
        if (link.source_type === 'competitor_controlled' && link.sentiment_bias < -0.4) {
          link.lineStyle.type = 'dashed';
          link.lineStyle.opacity = 1;
          link.emphasis = {
            lineStyle: {
              opacity: 0.5
            }
          };
        }
        return link;
      });

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          formatter: params => {
            if (params.dataType === 'node') {
              return `信源: ${params.name}`;
            }
            if (params.dataType === 'edge') {
              return `贡献度: ${params.data.contribution_score.toFixed(2)}<br/>情感偏差: ${params.data.sentiment_bias.toFixed(2)}`;
            }
          }
        },
        series: [
          {
            type: 'graph',
            layout: 'force',
            force: {
              repulsion: 150,
              gravity: 0.1,
              edgeLength: [100, 150]
            },
            roam: true,
            draggable: true,
            label: {
              show: true,
              position: 'bottom',
              color: '#e8e8e8',
              fontSize: 10
            },
            data: nodes,
            links: links,
            // 动态能量流
            edgeSymbol: ['none', 'arrow'],
            edgeSymbolSize: [4, 8],
            lineStyle: {
              curveness: 0.1
            },
            effect: {
              show: true,
              period: 4,
              trailLength: 0.1,
              symbol: 'circle',
              symbolSize: 3
            },
            // 悬浮高亮
            emphasis: {
              focus: 'adjacency',
              label: {
                show: true,
                fontSize: 14,
                fontWeight: 'bold'
              }
            }
          }
        ]
      };

      this.data.chart.setOption(option);
    },

    bindChartEvents() {
      if (!this.data.chart) return;

      // 点击事件
      this.data.chart.on('click', params => {
        if (params.dataType === 'node' || params.dataType === 'edge') {
          this.triggerEvent('sourceclick', {
            type: params.dataType,
            data: params.data
          });
        }
      });

      // 悬浮事件 (ECharts的emphasis已处理大部分)
      this.data.chart.on('mouseover', params => {
        // 可以在这里做更复杂的交互，如显示自定义浮窗
      });
    }
  }
});