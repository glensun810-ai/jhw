const appid = 'wx8876348e089bc261'; // 您的 AppID
const serverUrl = 'http://127.0.0.1:5001'; // 后端服务器地址

Page({
  data: {
    // 用户状态
    userInfo: null,
    openid: '',
    loginStatus: '未登录',
    serverStatus: '未连接',

    // 品牌与竞品
    brandName: '',
    competitorBrands: [],
    currentCompetitor: '',

    // 问题设置
    customQuestions: ['', '', '', '', ''],
    selectedQuestionCount: 0,

    // AI模型选择
    domesticAiModels: [
      { name: 'DeepSeek', checked: true, logo: 'DS', tags: ['综合', '代码'] },
      { name: '豆包', checked: true, logo: 'DB', tags: ['综合', '创意'] },
      { name: '通义千问', checked: true, logo: 'QW', tags: ['综合', '长文本'] },
      { name: 'Kimi', checked: false, logo: 'KM', tags: ['长文本'] },
      { name: '文心一言', checked: false, logo: 'WX', tags: ['综合', '创意'] },
      { name: '讯飞星火', checked: false, logo: 'XF', tags: ['综合', '语音'] },
      { name: '元宝', checked: false, logo: 'YB', tags: ['综合'], disabled: true },
    ],
    overseasAiModels: [
      { name: 'ChatGPT', checked: true, logo: 'GPT', tags: ['综合', '代码'] },
      { name: 'Claude', checked: false, logo: 'CD', tags: ['长文本', '创意'] },
      { name: 'Gemini', checked: false, logo: 'GM', tags: ['综合', '多模态'] },
    ],
    selectedModelCount: 0,

    // 测试状态
    isTesting: false,
    testProgress: 0,
    progressText: '准备启动AI认知诊断...',
    testCompleted: false,

    // 高级设置控制
    showAdvancedSettings: false,

    // 存储后端返回的最终结果
    latestTestResults: null,
    latestCompetitiveAnalysis: null,
    
    // 动画
    particleAnimateId: null
  },

  onLoad: function () {
    console.log('品牌AI雷达 - 页面加载完成');
    this.checkServerConnection();
    this.updateSelectedModelCount();
    this.updateSelectedQuestionCount();
  },

  onReady: function () {
    this.initParticleCanvas();
  },

  onUnload: function () {
    if (this.data.particleAnimateId) {
      cancelAnimationFrame(this.data.particleAnimateId);
    }
  },

  initParticleCanvas: function() {
    const query = wx.createSelectorQuery();
    query.select('#particle-canvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res[0] || !res[0].node) {
          console.error("Cannot get canvas node.");
          return;
        }
        const canvas = res[0].node;
        const ctx = canvas.getContext('2d');
        const dpr = wx.getSystemInfoSync().pixelRatio;
        canvas.width = res[0].width * dpr;
        canvas.height = res[0].height * dpr;
        ctx.scale(dpr, dpr);

        const particles = [];
        const particleCount = 50;

        for (let i = 0; i < particleCount; i++) {
          particles.push({
            x: Math.random() * res[0].width,
            y: Math.random() * res[0].height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            radius: Math.random() * 1.5 + 0.5
          });
        }

        const animate = () => {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < 0 || p.x > res[0].width) p.vx *= -1;
            if (p.y < 0 || p.y > res[0].height) p.vy *= -1;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.fill();
          });
          for (let i = 0; i < particleCount; i++) {
            for (let j = i + 1; j < particleCount; j++) {
              const dist = Math.hypot(particles[i].x - particles[j].x, particles[i].y - particles[j].y);
              if (dist < 100) {
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.strokeStyle = `rgba(255, 255, 255, ${0.5 - dist / 200})`;
                ctx.stroke();
              }
            }
          }
          this.data.particleAnimateId = canvas.requestAnimationFrame(animate);
        };
        animate();
      });
  },

  checkServerConnection: function() {
    wx.request({
      url: `${serverUrl}/api/test`,
      method: 'GET',
      success: (res) => {
        this.setData({ serverStatus: '已连接' });
      },
      fail: (err) => {
        this.setData({ serverStatus: '连接失败' });
        wx.showToast({ title: '后端服务未启动', icon: 'error' });
      }
    });
  },

  toggleAdvancedSettings: function() {
    this.setData({
      showAdvancedSettings: !this.data.showAdvancedSettings
    });
  },

  onBrandNameInput: function(e) {
    this.setData({ brandName: e.detail.value });
  },

  onCompetitorInput: function(e) {
    this.setData({ currentCompetitor: e.detail.value });
  },

  addCompetitor: function() {
    const currentCompetitor = this.data.currentCompetitor.trim();
    let competitorBrands = this.data.competitorBrands;

    if (!currentCompetitor) {
      wx.showToast({ title: '请输入竞争对手名称', icon: 'none' });
      return;
    }
    if (competitorBrands.includes(currentCompetitor)) {
      wx.showToast({ title: '该竞争对手已存在', icon: 'none' });
      return;
    }
    if (currentCompetitor === this.data.brandName.trim()) {
      wx.showToast({ title: '不能添加主品牌作为竞品', icon: 'none' });
      return;
    }

    competitorBrands.push(currentCompetitor);
    this.setData({ competitorBrands: competitorBrands, currentCompetitor: '' });
    wx.showToast({ title: '添加成功', icon: 'success' });
  },

  removeCompetitor: function(e) {
    const index = e.currentTarget.dataset.index;
    let competitorBrands = this.data.competitorBrands;
    competitorBrands.splice(index, 1);
    this.setData({ competitorBrands: competitorBrands });
    wx.showToast({ title: '删除成功', icon: 'success' });
  },

  onCustomQuestionInput: function(e) {
    const index = e.currentTarget.dataset.index;
    const value = e.detail.value;
    let customQuestions = this.data.customQuestions;
    customQuestions[index] = value;
    this.setData({ customQuestions: customQuestions });
    this.updateSelectedQuestionCount();
  },

  getValidQuestions: function() {
    return this.data.customQuestions.filter(question => question.trim() !== '');
  },

  updateSelectedQuestionCount: function() {
    const validQuestions = this.data.customQuestions.filter(question => question.trim() !== '');
    this.setData({ selectedQuestionCount: validQuestions.length });
  },

  toggleModelSelection: function(e) {
    const { type, index } = e.currentTarget.dataset;
    const key = type === 'domestic' ? 'domesticAiModels' : 'overseasAiModels';
    const models = this.data[key];

    if (models[index].disabled) {
      wx.showToast({ title: '该模型暂未配置', icon: 'none' });
      return;
    }

    models[index].checked = !models[index].checked;
    this.setData({ [key]: models });
    this.updateSelectedModelCount();
  },

  selectAllModels: function(e) {
    const { type } = e.currentTarget.dataset;
    const key = type === 'domestic' ? 'domesticAiModels' : 'overseasAiModels';
    const models = this.data[key].map(model => ({ 
      ...model, 
      checked: !model.disabled
    }));
    this.setData({ [key]: models });
    this.updateSelectedModelCount();
  },

  updateSelectedModelCount: function() {
    const selectedDomesticCount = this.data.domesticAiModels.filter(model => model.checked).length;
    const selectedOverseasCount = this.data.overseasAiModels.filter(model => model.checked).length;
    const totalCount = selectedDomesticCount + selectedOverseasCount;
    this.setData({ selectedModelCount: totalCount });
  },

  startBrandTest: function() {
    const brandName = this.data.brandName.trim();
    if (!brandName) {
      wx.showToast({ title: '请输入您的品牌名称', icon: 'error' });
      return;
    }

    const brand_list = [brandName, ...this.data.competitorBrands];
    let selectedModels = [...this.data.domesticAiModels, ...this.data.overseasAiModels].filter(model => model.checked && !model.disabled);
    let customQuestions = this.getValidQuestions();

    if (selectedModels.length === 0) {
      wx.showToast({ title: '请选择至少一个AI模型', icon: 'error' });
      return;
    }
    if (customQuestions.length === 0) {
      customQuestions = ["介绍一下{brandName}", "{brandName}的主要产品是什么"];
    }

    this.setData({
      isTesting: true,
      testProgress: 0,
      progressText: '正在启动AI认知诊断...',
      testCompleted: false,
    });

    this.callBackendBrandTest(brand_list, selectedModels, customQuestions);
  },

  callBackendBrandTest: function(brand_list, selectedModels, customQuestions) {
    wx.showLoading({ title: '启动诊断...' });

    wx.request({
      url: `${serverUrl}/api/perform-brand-test`,
      method: 'POST',
      data: {
        brand_list: brand_list,
        selectedModels: selectedModels,
        customQuestions: customQuestions
      },
      header: { 'content-type': 'application/json' },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200 && res.data.status === 'success') {
          const executionId = res.data.executionId;
          this.pollTestProgress(executionId);
        } else {
          wx.showToast({ title: '启动诊断失败', icon: 'error' });
          this.setData({ isTesting: false });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('品牌诊断请求失败:', err);
        wx.showToast({ title: '网络请求失败', icon: 'error' });
        this.setData({ isTesting: false });
      }
    });
  },

  pollTestProgress: function(executionId) {
    const progressSteps = [
      '正在连接AI认知引擎...',
      '正在生成诊断任务...',
      '正在向AI平台发起请求...',
      '正在分析AI回复...',
      '正在进行语义一致性检测...',
      '正在评估品牌纯净度...',
      '正在聚合竞品数据...',
      '正在生成深度洞察报告...'
    ];
    let currentStepIndex = 0;

    const pollInterval = setInterval(() => {
      wx.request({
        url: `${serverUrl}/api/test-progress?executionId=${executionId}`,
        method: 'GET',
        success: (res) => {
          if (res.statusCode === 200) {
            const data = res.data;
            const newProgress = Math.round(data.progress);

            if (newProgress > this.data.testProgress) {
              this.setData({ testProgress: newProgress });
              if (newProgress < 100) {
                currentStepIndex = Math.min(Math.floor(newProgress / (100 / progressSteps.length)), progressSteps.length - 1);
                this.setData({ progressText: progressSteps[currentStepIndex] });
              }
            }

            if (data.status === 'completed') {
              clearInterval(pollInterval);
              this.setData({
                latestTestResults: data.results,
                latestCompetitiveAnalysis: data.competitiveAnalysis,
                isTesting: false,
                testCompleted: true,
                progressText: '诊断完成，正在生成报告...',
              });
              wx.showToast({ title: '诊断完成', icon: 'success' });
              this.viewDetailedResults();
            } else if (data.status === 'failed') {
              clearInterval(pollInterval);
              this.setData({ isTesting: false, testCompleted: false, progressText: '诊断失败' });
              wx.showToast({ title: '诊断失败: ' + (data.error || '未知错误'), icon: 'none' });
            }
          }
        },
        fail: (err) => {
          console.error('获取诊断进度失败:', err);
          this.setData({ progressText: '诊断连接异常...' });
        }
      });
    }, 1000);
  },

  viewDetailedResults: function() {
    if (this.data.latestTestResults) {
      const params = {
        results: JSON.stringify(this.data.latestTestResults),
        competitiveAnalysis: encodeURIComponent(JSON.stringify(this.data.latestCompetitiveAnalysis || {})),
        targetBrand: this.data.brandName
      };
      
      const queryString = Object.keys(params)
        .map(key => `${key}=${params[key]}`)
        .join('&');

      wx.navigateTo({ url: `/pages/results/results?${queryString}` });
    } else {
      wx.showToast({ title: '暂无诊断结果', icon: 'none' });
    }
  },

  viewHistory: function() {
    wx.navigateTo({ url: '/pages/history/history' });
  }
});