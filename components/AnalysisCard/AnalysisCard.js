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
      'report_aggregating': '正在深度汇总分析报告...',
      'completed': '诊断完成，正在生成报告...',
      'failed': '报告聚合异常',  // 【P0 修复】失败状态文案
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
      // 【P0 修复 - 2026-03-06】进度条颜色由业务状态驱动
      switch(status) {
        case 'failed':
          return '#FF6B6B'; // 珊瑚红 - 警示色
        case 'completed':
          return '#00F5A0'; // 绿色 - 成功色
        case 'ai_fetching':
        case 'intelligence_analyzing':
        case 'competition_analyzing':
        case 'report_aggregating':
          return '#00A9FF'; // 蓝色 - 进行中
        case 'init':
          return '#8c8c8c'; // 灰色 - 初始化
        default:
          return '#8c8c8c'; // 灰色 - 未知状态
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