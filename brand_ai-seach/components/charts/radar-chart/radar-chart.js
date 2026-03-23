/**
 * 雷达图组件
 * 
 * 属性:
 * - data: 数据数组 [{name: '声量', value: 85}, {name: '情感', value: 72}]
 * - title: 图表标题
 * - color: 填充颜色
 * - maxValue: 最大值
 * - showDataList: 是否显示数据列表
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
      value: ''
    },
    color: {
      type: String,
      value: '#4A7BFF'
    },
    maxValue: {
      type: Number,
      value: 100
    },
    showDataList: {
      type: Boolean,
      value: true
    }
  },

  data: {
    gridLevels: [20, 40, 60, 80, 100],
    axes: [1, 2, 3, 4, 5, 6],
    points: [],
    labels: [],
    labelStyle: [],
    dataStyle: ''
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
        this.setData({ points: [], labels: [], dataStyle: '' });
        return;
      }

      const data = this.data.data;
      const labels = data.map(item => item.name);
      const values = data.map(item => item.value);
      const maxValue = this.data.maxValue || Math.max(...values);
      
      // 计算点和标签位置
      const points = [];
      const labelStyle = [];
      const centerX = 50;
      const centerY = 50;
      const radius = 40;
      
      data.forEach((item, index) => {
        const angle = (index / data.length) * 2 * Math.PI - Math.PI / 2;
        const valueRatio = item.value / maxValue;
        
        // 数据点位置
        const x = centerX + Math.cos(angle) * radius * valueRatio;
        const y = centerY + Math.sin(angle) * radius * valueRatio;
        points.push({ x, y });
        
        // 标签位置
        const labelX = centerX + Math.cos(angle) * (radius + 10);
        const labelY = centerY + Math.sin(angle) * (radius + 10);
        labelStyle.push({
          left: `${labelX}%`,
          top: `${labelY}%`,
          transform: 'translate(-50%, -50%)'
        });
      });
      
      // 生成数据区域样式
      const path = points.map((point, index) => {
        return `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`;
      }).join(' ') + ' Z';
      
      const dataStyle = `
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cpath d='${path}' fill='${this.data.color.replace('#', '%23')}' opacity='0.3'/%3E%3C/svg%3E");
      `;
      
      this.setData({ 
        points, 
        labels, 
        labelStyle,
        dataStyle,
        axes: new Array(data.length).fill(1)
      });
    }
  }
});
