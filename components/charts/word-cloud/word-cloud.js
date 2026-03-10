/**
 * 词云组件
 * 
 * 属性:
 * - data: 数据数组 [{name: '问题 1', value: 156}, {name: '问题 2', value: 132}]
 * - title: 标题
 * - subtitle: 副标题
 * - showCount: 是否显示数量
 * - showList: 是否显示列表模式
 * - maxTags: 最大标签数
 */

Component({
  properties: {
    data: {
      type: Array,
      value: [],
      observer: 'onDataChange'
    },
    title: {
      type: String,
      value: '高频问题'
    },
    subtitle: {
      type: String,
      value: 'TOP10'
    },
    showCount: {
      type: Boolean,
      value: true
    },
    showList: {
      type: Boolean,
      value: true
    },
    maxTags: {
      type: Number,
      value: 10
    }
  },

  data: {
    tags: [],
    maxValue: 100
  },

  lifetimes: {
    attached: function() {
      this.initChart();
    }
  },

  methods: {
    onDataChange: function(newData) {
      this.initChart();
    },

    /**
     * 初始化图表
     */
    initChart: function() {
      if (!this.data.data || this.data.data.length === 0) {
        this.setData({ tags: [], maxValue: 0 });
        return;
      }

      const data = this.data.data.slice(0, this.data.maxTags);
      const values = data.map(item => item.value);
      const maxValue = Math.max(...values) || 100;
      
      // 生成标签
      const tags = data.map((item, index) => {
        // 字体大小 (28-56rpx)
        const size = 28 + (item.value / maxValue) * 28;
        
        // 颜色 (根据排名)
        const colors = ['#4A7BFF', '#00F5A0', '#f39c12', '#3498db', '#e74c3c', '#9b59b6'];
        const color = colors[index % colors.length];
        
        // 透明度 (根据值大小)
        const opacity = 0.6 + (item.value / maxValue) * 0.4;
        
        return {
          id: index,
          text: item.name,
          count: item.value,
          size,
          color,
          opacity
        };
      });
      
      this.setData({ tags, maxValue });
    }
  }
});
