/**
 * EC-Canvas 组件
 * 基于 echarts-for-weixin 的图表组件
 */

Component({
  properties: {
    canvasId: {
      type: String,
      value: 'ec-canvas'
    },
    ec: {
      type: Object,
      value: null
    },
    height: {
      type: Number,
      value: 400
    },
    width: {
      type: Number,
      value: null
    }
  },

  data: {
    canvasWidth: 0,
    canvasHeight: 0
  },

  ready: function() {
    if (!this.data.ec) {
      console.warn('组件必需传入 ec 配置项');
      return;
    }

    // 【兼容性修复】使用 wx.getWindowInfo() 替代已废弃的 wx.getSystemInfoSync()
    const windowInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const query = wx.createSelectorQuery().in(this);

    query.select('.ec-canvas').boundingClientRect((res) => {
      if (!res) {
        console.error('无法获取 canvas 元素');
        return;
      }

      this.setData({
        canvasWidth: res.width || windowInfo.windowWidth,
        canvasHeight: this.data.height
      });

      this.initChart();
    }).exec();
  },

  methods: {
    initChart: function() {
      const canvasNode = this.selectComponent('#' + this.data.canvasId);

      if (!canvasNode) {
        console.error('无法找到 canvas 节点');
        return;
      }

      const ctx = canvasNode.getContext('2d');
      // 【兼容性修复】使用 wx.getWindowInfo() 替代已废弃的 wx.getSystemInfoSync()
      const windowInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const dpr = windowInfo.pixelRatio;

      canvasNode.width = this.data.canvasWidth * dpr;
      canvasNode.height = this.data.canvasHeight * dpr;
      ctx.scale(dpr, dpr);

      // 初始化 ECharts
      const echarts = require('./echarts');
      const chart = echarts.init(canvasNode, null, {
        width: this.data.canvasWidth,
        height: this.data.canvasHeight,
        devicePixelRatio: dpr
      });

      this.chart = chart;

      // 设置配置项
      if (this.data.ec) {
        chart.setOption(this.data.ec);
      }

      // 触发初始化完成事件
      this.triggerEvent('chartReady', { chart });
    },

    setOption: function(option) {
      if (this.chart) {
        this.chart.setOption(option, true);
      }
    },

    dispose: function() {
      if (this.chart) {
        this.chart.dispose();
      }
    }
  }
});
