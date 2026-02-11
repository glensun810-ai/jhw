const appid = 'wx8876348e089bc261'; // 您的 AppID
const serverUrl = 'http://127.0.0.1:5001'; // 后端服务器地址

Page({
  data: {
    targetBrand: '', // 目标品牌
    competitorBrands: [], // 竞争对手品牌列表
    currentCompetitor: '', // 当前输入的竞争对手
    domesticAiModels: [
      { name: 'DeepSeek', checked: true },
      { name: '豆包', checked: false },
      { name: '元宝', checked: false },
      { name: '通义千问', checked: true },
      { name: '文心一言', checked: false },
      { name: 'Kimi', checked: true },
      { name: '讯飞星火', checked: false }
    ], // 国内AI模型
    overseasAiModels: [
      { name: 'ChatGPT', checked: true },
      { name: 'Claude', checked: true },
      { name: 'Gemini', checked: false },
      { name: 'Perplexity', checked: false },
      { name: 'Grok', checked: false }
    ], // 海外AI模型
    isAnalyzing: false, // 是否正在分析
    analysisProgress: 0, // 分析进度
    analysisCompleted: false, // 分析是否完成
    competitiveAnalysis: null, // 竞争分析结果
    marketShareList: [], // 市场份额列表
    recommendationWeightList: [], // 推荐权重列表
    intelligenceList: [] // 情报列表
  },

  onLoad: function () {
    console.log('竞争分析页面加载完成');
  },

  // 输入目标品牌
  onTargetBrandInput: function(e) {
    this.setData({
      targetBrand: e.detail.value
    });
  },

  // 输入竞争对手
  onCompetitorInput: function(e) {
    this.setData({
      currentCompetitor: e.detail.value
    });
  },

  // 添加竞争对手
  addCompetitor: function() {
    const competitor = this.data.currentCompetitor.trim();
    if (!competitor) {
      wx.showToast({
        title: '请输入竞争对手名称',
        icon: 'none'
      });
      return;
    }

    // 检查是否已存在
    if (this.data.competitorBrands.includes(competitor)) {
      wx.showToast({
        title: '该竞争对手已添加',
        icon: 'none'
      });
      return;
    }

    // 检查是否与目标品牌相同
    if (competitor === this.data.targetBrand) {
      wx.showToast({
        title: '不能添加自己为竞争对手',
        icon: 'none'
      });
      return;
    }

    const newCompetitorBrands = [...this.data.competitorBrands, competitor];
    this.setData({
      competitorBrands: newCompetitorBrands,
      currentCompetitor: ''
    });

    wx.showToast({
      title: '添加成功',
      icon: 'success'
    });
  },

  // 删除竞争对手
  removeCompetitor: function(e) {
    const index = e.currentTarget.dataset.index;
    const competitorBrands = [...this.data.competitorBrands];
    competitorBrands.splice(index, 1);

    this.setData({
      competitorBrands: competitorBrands
    });
  },

  // 切换国内AI模型选择
  onDomesticAiModelChange: function(e) {
    const modelIndex = e.currentTarget.dataset.index;
    const domesticAiModels = this.data.domesticAiModels;
    domesticAiModels[modelIndex].checked = !domesticAiModels[modelIndex].checked;

    this.setData({
      domesticAiModels: domesticAiModels
    });
  },

  // 切换海外AI模型选择
  onOverseasAiModelChange: function(e) {
    const modelIndex = e.currentTarget.dataset.index;
    const overseasAiModels = this.data.overseasAiModels;
    overseasAiModels[modelIndex].checked = !overseasAiModels[modelIndex].checked;

    this.setData({
      overseasAiModels: overseasAiModels
    });
  },

  // 开始竞争分析
  startCompetitiveAnalysis: function() {
    const targetBrand = this.data.targetBrand;
    const competitorBrands = this.data.competitorBrands;
    const selectedDomesticModels = this.data.domesticAiModels.filter(model => model.checked);
    const selectedOverseasModels = this.data.overseasAiModels.filter(model => model.checked);
    const selectedModels = [...selectedDomesticModels, ...selectedOverseasModels];

    if (!targetBrand.trim()) {
      wx.showToast({
        title: '请输入目标品牌名称',
        icon: 'error'
      });
      return;
    }

    if (competitorBrands.length === 0) {
      wx.showToast({
        title: '请至少添加一个竞争对手',
        icon: 'error'
      });
      return;
    }

    if (selectedModels.length === 0) {
      wx.showToast({
        title: '请选择至少一个AI模型',
        icon: 'error'
      });
      return;
    }

    // 初始化分析状态
    this.setData({
      isAnalyzing: true,
      analysisProgress: 0,
      analysisCompleted: false,
      competitiveAnalysis: null
    });

    // 调用后端API进行竞争分析
    this.callBackendCompetitiveAnalysis(targetBrand, competitorBrands, selectedModels);
  },

  // 调用后端API进行竞争分析
  callBackendCompetitiveAnalysis: function(targetBrand, competitorBrands, selectedModels) {
    wx.showLoading({
      title: '启动分析...'
    });

    // First, we need to run a brand test to get AI responses
    const questions = [
      `介绍一下${targetBrand}`,
      `介绍一下${competitorBrands.join('和')}`,
      `比较一下${targetBrand}和${competitorBrands.join('、')}的优缺点`,
      `在${competitorBrands.join('、')}中，哪个品牌在同类产品中最受推荐？`,
      `${targetBrand}相比${competitorBrands.join('、')}有哪些优势和劣势？`
    ];

    // Get selected model names
    const selectedModelNames = [...selectedModels].map(model => ({ name: model.name, checked: true }));

    // Call the perform-brand-test API with competitor brands
    wx.request({
      url: `${serverUrl}/api/perform-brand-test`,
      method: 'POST',
      data: {
        brandName: targetBrand,
        selectedModels: selectedModelNames,
        customQuestions: questions,
        competitorBrands: competitorBrands
      },
      header: {
        'content-type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          const executionId = res.data.executionId;

          // Poll for the results
          this.pollForCompetitiveResults(executionId, targetBrand, competitorBrands);
        } else {
          wx.hideLoading();
          wx.showToast({
            title: '启动分析失败',
            icon: 'error'
          });
          this.setData({ isAnalyzing: false });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('启动分析请求失败:', err);
        wx.showToast({
          title: '网络请求失败',
          icon: 'error'
        });
        this.setData({ isAnalyzing: false });
      }
    });
  },

  // Poll for competitive analysis results
  pollForCompetitiveResults: function(executionId, targetBrand, competitorBrands) {
    const pollInterval = setInterval(() => {
      wx.request({
        url: `${serverUrl}/api/test-progress?executionId=${executionId}`,
        method: 'GET',
        success: (res) => {
          if (res.statusCode === 200) {
            const data = res.data;

            this.setData({
              analysisProgress: Math.round(data.progress)
            });

            if (data.status === 'completed') {
              clearInterval(pollInterval);

              // Check if competitive analysis data is available
              if (data.competitiveAnalysis) {
                wx.hideLoading();
                this.processCompetitiveAnalysisResult({
                  status: 'success',
                  targetBrand: targetBrand,
                  competitorBrands: competitorBrands,
                  ...data.competitiveAnalysis
                });
              } else {
                // If no competitive analysis data, run standalone analysis
                this.runStandaloneCompetitiveAnalysis(data.results, targetBrand, competitorBrands);
              }
            } else if (data.status === 'failed') {
              clearInterval(pollInterval);
              wx.hideLoading();
              this.setData({
                isAnalyzing: false
              });
              wx.showToast({
                title: '分析失败: ' + (data.error || '未知错误'),
                icon: 'none'
              });
            }
          }
        },
        fail: (err) => {
          console.error('获取进度失败:', err);
          // Don't clear interval, continue polling
        }
      });
    }, 1000); // Poll every second
  },

  // Run standalone competitive analysis if not included in test results
  runStandaloneCompetitiveAnalysis: function(results, targetBrand, competitorBrands) {
    // Format results for competitive analysis
    const aiResponses = results.map(result => ({
      aiModel: result.aiModel,
      question: result.question,
      response: result.response
    }));

    // Call the standalone competitive analysis API
    wx.request({
      url: `${serverUrl}/api/competitive-analysis`,
      method: 'POST',
      data: {
        targetBrand: targetBrand,
        competitorBrands: competitorBrands,
        aiResponses: aiResponses
      },
      header: {
        'content-type': 'application/json'
      },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200 && res.data.status === 'success') {
          this.processCompetitiveAnalysisResult(res.data);
        } else {
          wx.showToast({
            title: '竞争分析失败',
            icon: 'error'
          });
          this.setData({ isAnalyzing: false });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('竞争分析请求失败:', err);
        wx.showToast({
          title: '网络请求失败',
          icon: 'error'
        });
        this.setData({ isAnalyzing: false });
      }
    });
  },

  // 处理竞争分析结果
  processCompetitiveAnalysisResult: function(data) {
    // Format competitive analysis data for display
    let marketShareList = [];
    let recommendationWeightList = [];
    let intelligenceList = [];

    if (data.marketShareDistribution) {
      marketShareList = Object.entries(data.marketShareDistribution)
        .map(([brand, percentage]) => ({ brand, percentage }));
    }

    if (data.recommendationWeights) {
      recommendationWeightList = Object.entries(data.recommendationWeights)
        .map(([brand, weight]) => ({ brand, weight }));
    }

    if (data.competitorIntelligence) {
      intelligenceList = Object.entries(data.competitorIntelligence)
        .map(([brand, data]) => ({
          brand,
          positiveContexts: data.positive_contexts || [],
          sourceIndicators: data.source_indicators || [],
          comparativeStatements: data.comparative_statements || []
        }));
    }

    this.setData({
      competitiveAnalysis: data,
      marketShareList,
      recommendationWeightList,
      intelligenceList,
      isAnalyzing: false,
      analysisCompleted: true,
      analysisProgress: 100
    });

    wx.showToast({
      title: '分析完成',
      icon: 'success'
    });
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({
      url: '/pages/index/index'
    });
  }
})