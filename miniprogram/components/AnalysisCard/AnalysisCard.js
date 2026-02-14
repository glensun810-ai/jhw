// components/AnalysisCard/AnalysisCard.js
Component({
  options: {
    addGlobalClass: true
  },

  /**
   * 组件的属性列表
   */
  properties: {
    title: {
      type: String,
      value: '分析卡片'
    },
    subtitle: {
      type: String,
      value: ''
    },
    status: {
      type: String,
      value: 'init' // init, ai_fetching, intelligence_analyzing, competition_analyzing, completed
    },
    progress: {
      type: Number,
      value: 0
    },
    data: {
      type: Object,
      value: null
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
      'ai_fetching': '正在连接大模型...',
      'intelligence_analyzing': '正在进行语义冲突分析...',
      'competition_analyzing': '正在比对竞争对手...',
      'completed': '诊断完成，正在生成报告...',
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
    
    getStatusColor(status) {
      switch(status) {
        case 'completed':
          return '#00F5A0'; // Green
        case 'ai_fetching':
        case 'intelligence_analyzing':
        case 'competition_analyzing':
          return '#00A9FF'; // Blue
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