Component({
  properties: {
    // 图表配置对象
    ec: {
      type: Object,
      value: {},
      observer: function(newVal, oldVal) {
        // 当 ec 属性变化时重新初始化图表
        if (this.data.isLoaded && newVal && newVal.onInit) {
          this.initChart();
        }
      }
    },
    // canvas ID
    canvasId: {
      type: String,
      value: 'ec-canvas'
    },
    // 是否自动加载
    autoLoad: {
      type: Boolean,
      value: true
    }
  },

  data: {
    isLoaded: false,
    isError: false
  },

  lifetimes: {
    attached() {
      // 组件实例进入页面节点树时执行
      if (this.data.autoLoad) {
        this.loadChart();
      }
    },
    detached() {
      // 组件实例被从页面节点树移除时执行
      if (this.chart) {
        this.chart.dispose && this.chart.dispose();
        this.chart = null;
      }
    }
  },

  methods: {
    loadChart() {
      // 模拟加载过程
      setTimeout(() => {
        if (this.properties.ec && this.properties.ec.onInit) {
          this.setData({
            isLoaded: true,
            isError: false
          });
          
          // 初始化图表
          this.initChart();
        } else {
          this.setData({
            isLoaded: false,
            isError: true
          });
        }
      }, 300); // 模拟加载延迟
    },

    initChart() {
      // 如果提供了初始化函数，则调用它
      if (this.properties.ec && this.properties.ec.onInit) {
        try {
          // 这里会由 ec-canvas 组件来实际执行图表初始化
          // 我们只需要确保数据传递正确
          this.triggerEvent('init', { success: true });
        } catch (error) {
          console.error('图表初始化失败:', error);
          this.setData({
            isError: true
          });
        }
      }
    },

    // 外部方法：手动刷新图表
    refreshChart() {
      this.setData({
        isLoaded: false,
        isError: false
      });

      setTimeout(() => {
        if (this.properties.ec && this.properties.ec.onInit) {
          this.setData({
            isLoaded: true
          });
          this.initChart();
        } else {
          this.setData({
            isLoaded: false,
            isError: true
          });
        }
      }, 100);
    },

    // 触发图表点击事件
    onChartClick(e) {
      this.triggerEvent('chartclick', e.detail);
    },

    // 触发图表完成渲染事件
    onChartRenderComplete() {
      this.triggerEvent('rendercomplete', { success: true });
    }
  }
})