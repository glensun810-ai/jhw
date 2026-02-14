Page({
  data: {
    features: [
      {
        id: 1,
        icon: '🔍',
        title: '品牌认知诊断',
        description: '通过AI平台分析品牌在市场中的认知度和影响力'
      },
      {
        id: 2,
        icon: '📊',
        title: '多维度分析',
        description: '从权威度、可见度、纯净度、一致性四个维度全面分析'
      },
      {
        id: 3,
        icon: '🔄',
        title: '竞品对比',
        description: '与竞争对手进行多维度对比分析'
      },
      {
        id: 4,
        icon: '💾',
        title: '结果保存',
        description: '保存和管理您的诊断结果'
      }
    ],
    steps: [
      {
        id: 1,
        number: '1',
        title: '设置品牌信息',
        description: '输入您的品牌名称和竞争品牌'
      },
      {
        id: 2,
        number: '2',
        title: '选择AI平台',
        description: '选择您想要测试的AI平台'
      },
      {
        id: 3,
        number: '3',
        title: '自定义问题',
        description: '设置您关心的问题，或使用系统推荐'
      },
      {
        id: 4,
        number: '4',
        title: '开始诊断',
        description: '点击按钮开始品牌认知诊断'
      },
      {
        id: 5,
        number: '5',
        title: '查看报告',
        description: '查看详细的诊断报告和分析结果'
      }
    ],
    faqs: [
      {
        id: 1,
        question: '如何开始品牌认知诊断？',
        answer: '在首页输入您的品牌名称，选择AI平台，设置问题，然后点击"AI品牌战略诊断"按钮即可开始。',
        showAnswer: false
      },
      {
        id: 2,
        question: '诊断结果如何保存？',
        answer: '在结果页面点击"保存结果"按钮，您可以为结果添加标签和备注，方便后续查看。',
        showAnswer: false
      },
      {
        id: 3,
        question: '如何查看历史诊断记录？',
        answer: '点击首页的"查看历史诊断报告"链接，可以查看您所有的历史诊断记录。',
        showAnswer: false
      },
      {
        id: 4,
        question: '支持哪些AI平台？',
        answer: '目前支持DeepSeek、豆包、通义千问等主流AI平台，您可以根据需要选择。',
        showAnswer: false
      }
    ]
  },

  onLoad: function(options) {
    // 页面加载时的初始化
  },

  // 切换答案显示
  toggleAnswer: function(e) {
    const index = e.currentTarget.dataset.index;
    const faqs = this.data.faqs;
    faqs[index].showAnswer = !faqs[index].showAnswer;
    
    this.setData({
      faqs: faqs
    });
  },

  // 开始诊断
  startDiagnosis: function() {
    wx.reLaunch({
      url: '/pages/index/index'
    });
  },

  // 联系客服
  contactSupport: function() {
    wx.showModal({
      title: '联系客服',
      content: '客服电话：400-123-4567\n客服QQ：123456789',
      showCancel: false,
      confirmText: '确定'
    });
  }
})