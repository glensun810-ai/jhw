import * as echarts from './echarts';

function wrapTouch(event) {
  for (let i = 0; i < event.touches.length; ++i) {
    const touch = event.touches[i];
    touch.offsetX = touch.x;
    touch.offsetY = touch.y;
  }
  return event;
}

Component({
  properties: {
    canvasId: {
      type: String,
      value: 'ec-canvas'
    },
    ec: {
      type: Object
    }
  },

  data: {
    isUseNewCanvas: false
  },

  ready: function () {
    if (!this.data.ec) {
      console.warn('组件需绑定 ec 变量，例：<ec-canvas ec="{{ ec }}"></ec-canvas>');
      return;
    }

    if (!this.data.ec.lazyLoad) {
      this.init();
    }
  },

  methods: {
    init: function (callback) {
      const version = wx.getSystemInfoSync().SDKVersion;
      const canUseNewCanvas = version.split('.').map(n => parseInt(n, 10)).reduce((a, b, i) => a + b * Math.pow(100, 2 - i)) >= 10602;
      this.setData({ isUseNewCanvas: canUseNewCanvas });

      if (canUseNewCanvas) {
        this.initByNewWay(callback);
      } else {
        console.error('微信版本过低，无法使用新版 canvas 接口');
      }
    },

    initByNewWay: function (callback) {
      const query = wx.createSelectorQuery().in(this);
      query
        .select(`#${this.data.canvasId}`)
        .fields({ node: true, size: true })
        .exec(res => {
          const canvasNode = res[0].node;
          this.canvasNode = canvasNode;

          const canvasDpr = wx.getSystemInfoSync().pixelRatio;
          const canvasWidth = res[0].width;
          const canvasHeight = res[0].height;

          const ctx = canvasNode.getContext('2d');

          const canvas = {
            width: canvasWidth,
            height: canvasHeight,
            getContext: () => ctx,
            setChart: function(chart) {
              this.chart = chart;
            },
            addEventListener: () => {}, // mock
            removeEventListener: () => {}, // mock
            dispatchEvent: () => {} // mock
          };

          if (typeof callback === 'function') {
            this.chart = callback(canvas, canvasWidth, canvasHeight, canvasDpr);
          } else if (this.data.ec && typeof this.data.ec.onInit === 'function') {
            this.chart = this.data.ec.onInit(canvas, canvasWidth, canvasHeight, canvasDpr);
          }
        });
    },

    touchStart(e) {
      if (this.chart && e.touches.length > 0) {
        const touch = e.touches[0];
        this.chart.getZr().handler.dispatch('mousedown', {
          zrX: touch.x,
          zrY: touch.y
        });
        this.chart.getZr().handler.dispatch('mousemove', {
          zrX: touch.x,
          zrY: touch.y
        });
      }
    },

    touchMove(e) {
      if (this.chart && e.touches.length > 0) {
        const touch = e.touches[0];
        this.chart.getZr().handler.dispatch('mousemove', {
          zrX: touch.x,
          zrY: touch.y
        });
      }
    },

    touchEnd(e) {
      if (this.chart) {
        const touch = e.changedTouches ? e.changedTouches[0] : {};
        this.chart.getZr().handler.dispatch('mouseup', {
          zrX: touch.x,
          zrY: touch.y
        });
        this.chart.getZr().handler.dispatch('click', {
          zrX: touch.x,
          zrY: touch.y
        });
      }
    }
  }
});