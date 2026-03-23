// components/DashboardCard/DashboardCard.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    title: {
      type: String,
      value: '决策驾驶舱'
    },
    score: {
      type: Number,
      value: 0
    },
    status: {
      type: String,
      value: 'init' // init, ai_fetching, intelligence_analyzing, competition_analyzing, completed
    },
    trend: {
      type: String,
      value: 'neutral' // up, down, neutral
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
    statusTextMap: {
      'init': '任务初始化中...',
      'ai_fetching': '正在连接全网大模型... (30%)',
      'intelligence_analyzing': 'AI 正在进行深度语义研判... (60%)',
      'competition_analyzing': '正在扫描竞争对手攻防策略... (85%)',
      'completed': '报告生成完毕 (100%)',
      'unknown': '处理中...'
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    getStatusText(status) {
      return this.data.statusTextMap[status] || this.data.statusTextMap['unknown'];
    },
    
    getTrendIcon(trend) {
      switch(trend) {
        case 'up':
          return '↗️';
        case 'down':
          return '↘️';
        default:
          return '➡️';
      }
    },
    
    getTrendColor(trend) {
      switch(trend) {
        case 'up':
          return '#00F5A0'; // Green
        case 'down':
          return '#FF6B6B'; // Red
        default:
          return '#8c8c8c'; // Gray
      }
    }
  },
  
  lifetimes: {
    attached() {
      // 组件实例进入页面节点树时执行
    },
    detached() {
      // 组件实例被从页面节点树移除时执行
    }
  }
})