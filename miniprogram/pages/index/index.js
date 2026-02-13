const { checkServerConnectionApi, startBrandTestApi, getTestProgressApi } = require('../../api/home');
const {
  processTestProgress,
  getProgressTextByValue,
  formatTestResults,
  formatCompetitiveAnalysis,
  isTestCompleted,
  isTestFailed
} = require('../../services/homeService.js');

const appid = 'wx8876348e089bc261'; // 您的 AppID

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
    customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}],
    selectedQuestionCount: 0,

    // AI模型选择
    domesticAiModels: [
      { name: 'DeepSeek', checked: true, logo: 'DS', tags: ['综合', '代码'] },
      { name: '豆包', checked: true, logo: 'DB', tags: ['综合', '创意'] },
      { name: '通义千问', checked: true, logo: 'QW', tags: ['综合', '长文本'] },
      { name: '元宝', checked: false, logo: 'YB', tags: ['综合']},
      { name: 'Kimi', checked: false, logo: 'KM', tags: ['长文本'] },
      { name: '文心一言', checked: false, logo: 'WX', tags: ['综合', '创意'] },
      { name: '讯飞星火', checked: false, logo: 'XF', tags: ['综合', '语音'] },
      { name: '智谱AI', checked: false, logo: 'ZP', tags: ['综合', 'GLM'] },      
    ],
    overseasAiModels: [
      { name: 'ChatGPT', checked: true, logo: 'GPT', tags: ['综合', '代码'] },
      { name: 'Gemini', checked: false, logo: 'GM', tags: ['综合', '多模态'] },
      { name: 'Claude', checked: false, logo: 'CD', tags: ['长文本', '创意'] },
      { name: 'Perplexity', checked: false, logo: 'PE', tags: ['综合', '长文本'] },
      { name: 'Grok', checked: false, logo: 'GR', tags: ['推理', '多模态'] },
      
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

    // 保存配置相关
    showSaveModal: false,
    configName: '',

    // 动画
    particleAnimateId: null
  },

  onLoad: function (options) {
    console.log('品牌AI雷达 - 页面加载完成');
    this.checkServerConnection();
    this.updateSelectedModelCount();
    this.updateSelectedQuestionCount();

    // 检查是否需要立即启动快速搜索
    if (options && options.quickSearch === 'true') {
      // 延迟执行，确保页面已完全加载
      setTimeout(() => {
        this.startBrandTest();
      }, 1000); // 延迟稍长一些，确保配置已完全加载
    }
  },

  onShow: function() {
    // 检查是否有从配置管理页面传回的临时配置
    const app = getApp();
    if (app.globalData && app.globalData.tempConfig) {
      this.applyConfig(app.globalData.tempConfig);
      // 清除临时配置
      app.globalData.tempConfig = null;
    }
  },

  // 应用配置
  applyConfig: function(config) {
    // 确保自定义问题格式正确（每个问题都应该有text和show属性）
    const formattedQuestions = config.customQuestions.map(q => ({
      text: q.text || '',
      show: q.show !== undefined ? q.show : true
    }));

    this.setData({
      brandName: config.brandName || '',
      competitorBrands: Array.isArray(config.competitorBrands) ? config.competitorBrands : [],
      customQuestions: formattedQuestions,
      // 仅更新选中状态，保留模型的其他属性，处理可能不存在的模型
      domesticAiModels: this.data.domesticAiModels.map(model => {
        const savedModel = Array.isArray(config.domesticAiModels)
          ? config.domesticAiModels.find(saved => saved.name === model.name)
          : null;
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      }),
      overseasAiModels: this.data.overseasAiModels.map(model => {
        const savedModel = Array.isArray(config.overseasAiModels)
          ? config.overseasAiModels.find(saved => saved.name === model.name)
          : null;
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      })
    });

    wx.showToast({
      title: '配置已加载',
      icon: 'success'
    });
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
        const systemSetting = wx.getSystemSetting();
        const appAuthorizeSetting = wx.getAppAuthorizeSetting();
        const deviceInfo = wx.getDeviceInfo();
        const windowInfo = wx.getWindowInfo();
        const appBaseInfo = wx.getAppBaseInfo();

        // 合并需要的字段
        const systemInfo = {
            ...deviceInfo,
            ...windowInfo,
            ...appBaseInfo,
            system: appBaseInfo.system,
            platform: appBaseInfo.platform,
        };
        const dpr = systemInfo.pixelRatio;
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

  async checkServerConnection() {
    try {
      await checkServerConnectionApi();
      this.setData({ serverStatus: '已连接' });
    } catch (err) {
      this.setData({ serverStatus: '连接失败' });
      wx.showToast({ title: '后端服务未启动', icon: 'error' });
    }
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
    customQuestions[index].text = value;
    this.setData({ customQuestions: customQuestions });
    this.updateSelectedQuestionCount();
  },

  addCustomQuestion: function() {
    let customQuestions = this.data.customQuestions;
    customQuestions.push({text: '', show: true});
    this.setData({ customQuestions: customQuestions });
    this.updateSelectedQuestionCount();
  },

  removeCustomQuestion: function(e) {
    const index = e.currentTarget.dataset.index;
    let customQuestions = this.data.customQuestions;

    // 如果只有一个问题，则清空内容而不是删除
    if (customQuestions.length === 1) {
      customQuestions[0].text = '';
      this.setData({ customQuestions: customQuestions });
    } else {
      customQuestions.splice(index, 1);
      this.setData({ customQuestions: customQuestions });
    }

    this.updateSelectedQuestionCount();
  },

  getValidQuestions: function() {
    return this.data.customQuestions
      .filter(questionObj => questionObj.show !== false && questionObj.text && questionObj.text.trim() !== '')
      .map(questionObj => questionObj.text.trim());
  },

  updateSelectedQuestionCount: function() {
    const validQuestions = this.data.customQuestions
      .filter(questionObj => questionObj.show !== false && questionObj.text && questionObj.text.trim() !== '');
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

  async callBackendBrandTest(brand_list, selectedModels, customQuestions) {
    wx.showLoading({ title: '启动诊断...' });

    // 载荷标准化：将 selectedModels 对象数组平滑化为纯字符串 ID 数组
    const processedSelectedModels = selectedModels.map(item => {
      if (typeof item === 'object' && item !== null) {
        // 如果 item 是对象，提取其 id 或 value
        return item.id || item.value || item.name || item.label || '';
      } else {
        // 如果是字符串，直接保留
        return item;
      }
    }).filter(id => id !== ''); // 过滤掉空字符串

    // 类型降维处理：将问题数组转换为字符串
    const custom_question = customQuestions.join(' ');

    // 调试增强：打印请求数据
    console.log('Request Payload:', {
      brand_list: brand_list,
      selectedModels: processedSelectedModels, // 确保格式正确并标准化模型名称
      custom_question: custom_question  // 修正字段名和类型
    });

    try {
      const res = await startBrandTestApi({
        brand_list: brand_list,
        selectedModels: processedSelectedModels, // 确保格式正确并标准化模型名称
        custom_question: custom_question  // 修正字段名和类型
      });

      if (res.statusCode === 200 && res.data.status === 'success') {
        const executionId = res.data.executionId;
        this.pollTestProgress(executionId);
      } else {
        // 防御性编程：安全地访问响应数据
        let errorMessage = '启动诊断失败';
        if (res.data && typeof res.data === 'object') {
          errorMessage = res.data.message || res.data.error || res.data.details || '启动诊断失败';
        }
        wx.hideLoading();
        wx.showModal({
          title: '诊断启动失败',
          content: errorMessage,
          showCancel: false
        });
        this.setData({ isTesting: false });
      }
    } catch (err) {
      // 错误捕获防御：彻底重写 catch(err) 块
      // 要求：第一时间执行 wx.hideLoading()
      wx.hideLoading();

      console.error("Diagnostic Error:", err);

      // 要求：使用 err.data?.error || err.data?.message || err.errMsg 提取信息
      const extractedError = err.data?.error || err.data?.message || err.errMsg || "任务创建失败";

      // 要求：使用 wx.showModal 弹出提取到的真实错误信息
      wx.showModal({
        title: '启动失败',
        content: String(extractedError),
        showCancel: false
      });

      this.setData({ isTesting: false });
    } finally {
      // 交互修复：确保在所有情况下都隐藏加载提示
      // 注意：这里不再重复调用 wx.hideLoading()，因为在 catch 块中已经调用了
      // 避免重复调用可能引起的错误
    }
  },

  pollTestProgress(executionId) {
    const pollInterval = setInterval(async () => {
      try {
        const res = await getTestProgressApi(executionId);
        if (res.statusCode === 200) {
          // 使用服务层处理进度数据
          const processedData = processTestProgress(res, this.data.testProgress);

          if (processedData.shouldUpdateProgress) {
            this.setData({ testProgress: processedData.newProgressValue });

            if (processedData.newProgressValue < 100) {
              const progressText = getProgressTextByValue(processedData.newProgressValue);
              this.setData({ progressText });
            }
          }

          if (isTestCompleted(processedData.status)) {
            clearInterval(pollInterval);
            this.setData({
              latestTestResults: formatTestResults(processedData.results),
              latestCompetitiveAnalysis: formatCompetitiveAnalysis(processedData.competitiveAnalysis),
              isTesting: false,
              testCompleted: true,
              progressText: '诊断完成，正在生成报告...',
            });
            wx.showToast({ title: '诊断完成', icon: 'success' });
            this.viewDetailedResults();
          } else if (isTestFailed(processedData.status)) {
            clearInterval(pollInterval);
            this.setData({ isTesting: false, testCompleted: false, progressText: '诊断失败' });
            wx.showToast({ title: '诊断失败: ' + (processedData.error || '未知错误'), icon: 'none' });
          }
        }
      } catch (err) {
        console.error('获取诊断进度失败:', err);
        this.setData({ progressText: '诊断连接异常...' });
      }
    }, 1000);
  },

  viewDetailedResults: function() {
    if (this.data.latestTestResults) {
      // 直接传递对象，让微信小程序处理URL编码
      wx.navigateTo({
        url: `/pages/results/results?results=${encodeURIComponent(JSON.stringify(this.data.latestTestResults))}&competitiveAnalysis=${encodeURIComponent(JSON.stringify(this.data.latestCompetitiveAnalysis || {}))}&targetBrand=${encodeURIComponent(this.data.brandName)}`
      });
    } else {
      wx.showToast({ title: '暂无诊断结果', icon: 'none' });
    }
  },

  viewConfigManager: function() {
    wx.navigateTo({ url: '/pages/config-manager/config-manager' });
  },

  viewPermissionManager: function() {
    wx.navigateTo({ url: '/pages/permission-manager/permission-manager' });
  },

  viewDataManager: function() {
    wx.navigateTo({ url: '/pages/data-manager/data-manager' });
  },

  viewUserGuide: function() {
    wx.navigateTo({ url: '/pages/user-guide/user-guide' });
  },

  viewHistory: function() {
    wx.navigateTo({ url: '/pages/history/history' });
  },

  // 显示保存配置模态框
  showSaveConfigModal: function() {
    this.setData({
      showSaveModal: true,
      configName: ''
    });
  },

  // 隐藏保存配置模态框
  hideSaveConfigModal: function() {
    this.setData({
      showSaveModal: false,
      configName: ''
    });
  },

  // 处理配置名称输入
  onConfigNameInput: function(e) {
    this.setData({
      configName: e.detail.value
    });
  },

  // 保存当前配置
  saveCurrentConfig: function() {
    const configName = this.data.configName.trim();

    if (!configName) {
      wx.showToast({
        title: '请输入配置名称',
        icon: 'none'
      });
      return;
    }

    // 获取当前配置，只保存有效的自定义问题（show为true且有内容）
    const validQuestions = this.data.customQuestions
      .filter(questionObj => questionObj.show !== false && questionObj.text && questionObj.text.trim() !== '')
      .map(questionObj => ({ ...questionObj })); // 创建副本以避免引用问题

    const currentConfig = {
      name: configName,
      brandName: this.data.brandName,
      competitorBrands: this.data.competitorBrands,
      customQuestions: validQuestions,
      domesticAiModels: this.data.domesticAiModels.map(model => ({
        name: model.name,
        checked: model.checked
      })),
      overseasAiModels: this.data.overseasAiModels.map(model => ({
        name: model.name,
        checked: model.checked
      }))
    };

    // 读取现有的配置列表
    let savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];

    // 检查是否已存在同名配置
    const existingIndex = savedConfigs.findIndex(config => config.name === configName);
    if (existingIndex !== -1) {
      // 如果存在，询问用户是否覆盖
      wx.showModal({
        title: '配置已存在',
        content: `配置 "${configName}" 已存在，是否覆盖？`,
        success: (res) => {
          if (res.confirm) {
            savedConfigs[existingIndex] = currentConfig;
            wx.setStorageSync('savedSearchConfigs', savedConfigs);
            wx.showToast({
              title: '配置已更新',
              icon: 'success'
            });
            this.hideSaveConfigModal();
          }
        }
      });
    } else {
      // 添加新配置
      savedConfigs.push(currentConfig);
      wx.setStorageSync('savedSearchConfigs', savedConfigs);
      wx.showToast({
        title: '配置已保存',
        icon: 'success'
      });
      this.hideSaveConfigModal();
    }
  },

  // 加载保存的配置
  loadSavedConfig: function(configName) {
    const savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];
    const configToLoad = savedConfigs.find(config => config.name === configName);

    if (!configToLoad) {
      wx.showToast({
        title: '配置不存在',
        icon: 'none'
      });
      return;
    }

    // 更新页面数据
    this.setData({
      brandName: configToLoad.brandName,
      competitorBrands: configToLoad.competitorBrands,
      customQuestions: configToLoad.customQuestions,
      // 仅更新选中状态，保留模型的其他属性
      domesticAiModels: this.data.domesticAiModels.map(model => {
        const savedModel = configToLoad.domesticAiModels.find(saved => saved.name === model.name);
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      }),
      overseasAiModels: this.data.overseasAiModels.map(model => {
        const savedModel = configToLoad.overseasAiModels.find(saved => saved.name === model.name);
        return {
          ...model,
          checked: savedModel ? savedModel.checked : false
        };
      })
    });

    wx.showToast({
      title: '配置已加载',
      icon: 'success'
    });
  }
});