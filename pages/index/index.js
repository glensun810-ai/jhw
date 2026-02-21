const { checkServerConnectionApi, startBrandTestApi, getTestProgressApi, getTaskStatusApi } = require('../../api/home');
const {
  processTestProgress,
  getProgressTextByValue,
  formatTestResults,
  formatCompetitiveAnalysis,
  isTestCompleted,
  isTestFailed
} = require('../../services/homeService.js');
const { parseTaskStatus } = require('../../services/taskStatusService');
const { aggregateReport } = require('../../services/reportAggregator');

const appid = 'wx8876348e089bc261'; // 您的 AppID

/**
 * P2 新增：AI 平台默认配置
 * 原则：默认选择已验证可用的中文平台，降低首诊用户配置门槛
 */
const DEFAULT_AI_PLATFORMS = {
  // 国内平台默认选中（已验证可用）
  domestic: ['DeepSeek', '豆包', '通义千问', '智谱 AI'],
  // 海外平台默认不选中（网络延迟高，需手动开启）
  overseas: []
};

// 存储 Key
const STORAGE_KEY_PLATFORM_PREFS = 'user_ai_platform_preferences';

Page({
  /**
   * 【P1 新增】输入管理器
   */
  inputManager: null,

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

    // 新增：用于存储完整报告数据
    reportData: null,

    // 【新增】最新诊断结果标记
    hasLatestDiagnosis: false,
    latestDiagnosisInfo: null,

    // 控制是否启用新的分析图表组件
    analysisChartsEnabled: true,

    // 控制内容区域入场动画
    contentVisible: false,

    // 控制吸顶效果
    isSticky: false,

    // 当前任务阶段
    currentStage: 'init',

    // 趋势图表数据
    trendChartData: null,

    // 评分数据
    scoreData: null,

    // 竞争分析数据
    competitionData: null,

    // 预测数据
    predictionData: null,

    // 信源列表数据
    sourceListData: [],

    // 保存配置相关
    showSaveModal: false,
    configName: '',

    // Debug 区域显示的原始JSON
    debugJson: '',

    // 动画
    particleAnimateId: null,

    // 【新增】是否有上次诊断报告
    hasLastReport: false,

    // 【P2 新增】配置对象（包含诊断预估信息）- 严禁设为 null
    config: {
      estimate: { duration: '30s', steps: 5 },
      brandName: '',
      competitorBrands: [],
      customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}]
    },

    // 诊断配置兜底数据 - 严禁设为 null
    diagnosticConfig: {
      estimate: { duration: '30s', steps: 5 }
    }
  },

  onLoad: function (options) {
    try {
      console.log('品牌 AI 雷达 - 页面加载完成');

      // 1. 初始化默认值（确保 config.estimate 有默认值）
      this.initializeDefaults();

      // 2. 检查服务器连接
      this.checkServerConnection();

      // 3. 加载用户 AI 平台偏好
      this.loadUserPlatformPreferences();
      this.updateSelectedModelCount();
      this.updateSelectedQuestionCount();

      // 4. 防御性读取 config.estimate（多层保护）
      // 先检查 this.data 是否存在
      let estimate = { duration: '30s', steps: 5 }; // 默认值
      
      // 使用最安全的访问方式，避免访问 null 对象的属性
      if (this.data && this.data.config) {
        const config = this.data.config;
        if (config.estimate && typeof config.estimate === 'object') {
          estimate = config.estimate;
        }
      }
      
      console.log('诊断预估配置:', estimate);

      // 5. 检查是否需要立即启动快速搜索
      if (options && options.quickSearch === 'true') {
        setTimeout(() => {
          this.startBrandTest();
        }, 1000);
      }

      // 注意：restoreDraft 移到 onShow 中调用，避免 onLoad 中重复 setData
    } catch (error) {
      // 隔离报错环境：记录日志并维持默认状态
      console.error('onLoad 初始化失败:', error);
      console.error('错误堆栈:', error.stack);

      // 维持默认状态，确保页面可用
      this.setData({
        serverStatus: '初始化失败',
        config: {
          estimate: { duration: '30s', steps: 5 },
          brandName: '',
          competitorBrands: [],
          customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}]
        },
        diagnosticConfig: {
          estimate: { duration: '30s', steps: 5 }
        }
      });

      // 不影响用户其他操作
      wx.showToast({
        title: '初始化失败，请刷新重试',
        icon: 'none',
        duration: 2000
      });
    }
  },

  /**
   * 初始化默认值（独立方法）
   */
  initializeDefaults: function() {
    // 防御性检查：确保 this.data 存在
    if (!this.data) {
      console.warn('initializeDefaults: this.data is null, initializing...');
      // 如果 this.data 不存在，先初始化一个基础结构
      this.setData({
        config: {
          estimate: { duration: '30s', steps: 5 },
          brandName: '',
          competitorBrands: [],
          customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}]
        },
        diagnosticConfig: {
          estimate: { duration: '30s', steps: 5 }
        }
      });
      return;
    }

    // 确保 config 和 diagnosticConfig 始终有默认值
    // 使用安全的属性访问方式，处理可能为 null 的情况
    const config = this.data.config;
    const hasConfigEstimate = config && typeof config === 'object' && config.estimate && typeof config.estimate === 'object';

    if (!hasConfigEstimate) {
      this.setData({
        config: {
          estimate: { duration: '30s', steps: 5 },
          brandName: '',
          competitorBrands: [],
          customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}]
        }
      });
    }

    const diagnosticConfig = this.data.diagnosticConfig;
    const hasDiagnosticEstimate = diagnosticConfig && typeof diagnosticConfig === 'object' && diagnosticConfig.estimate && typeof diagnosticConfig.estimate === 'object';

    if (!hasDiagnosticEstimate) {
      this.setData({
        diagnosticConfig: {
          estimate: { duration: '30s', steps: 5 }
        }
      });
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

    // P2 修复：恢复草稿
    this.restoreDraft();

    // 【关键修复】检查是否有最新的诊断结果
    this.checkLatestDiagnosis();
  },

  /**
   * 【新增】检查最新诊断结果
   */
  checkLatestDiagnosis: function() {
    try {
      const latestExecutionId = wx.getStorageSync('latestExecutionId');
      const latestTargetBrand = wx.getStorageSync('latestTargetBrand');
      const latestDiagnosisTime = wx.getStorageSync('latestDiagnosisTime');

      if (latestExecutionId && latestTargetBrand) {
        console.log('✅ 检测到最新诊断结果:', {
          executionId: latestExecutionId,
          brand: latestTargetBrand,
          time: latestDiagnosisTime
        });

        // 显示查看最新诊断结果的提示
        this.setData({
          hasLatestDiagnosis: true,
          latestDiagnosisInfo: {
            executionId: latestExecutionId,
            brand: latestTargetBrand,
            time: latestDiagnosisTime
          }
        });
      }
    } catch (e) {
      console.error('检查最新诊断结果失败:', e);
    }
  },

  /**
   * P2 修复：应用配置（增强数据防御性）
   */
  applyConfig: function(config) {
    // 防御性检查：确保 config 存在
    if (!config || typeof config !== 'object') {
      console.warn('applyConfig: 配置数据无效', config);
      return;
    }

    // 确保自定义问题格式正确（每个问题都应该有 text 和 show 属性）
    const customQuestionsConfig = Array.isArray(config.customQuestions) ? config.customQuestions : [];
    const formattedQuestions = customQuestionsConfig.map(q => ({
      text: (q && q.text) || '',
      show: (q && q.show !== undefined) ? q.show : true
    }));

    // 防御性检查：确保 competitorBrands 是数组
    const competitorBrandsConfig = Array.isArray(config.competitorBrands) ? config.competitorBrands : [];

    // 防御性检查：确保 domesticAiModels 是数组
    const domesticAiModelsConfig = Array.isArray(config.domesticAiModels) ? config.domesticAiModels : [];
    const overseasAiModelsConfig = Array.isArray(config.overseasAiModels) ? config.overseasAiModels : [];

    this.setData({
      brandName: (config && config.brandName) || '',
      competitorBrands: competitorBrandsConfig,
      customQuestions: formattedQuestions,
      // 仅更新选中状态，保留模型的其他属性，处理可能不存在的模型
      domesticAiModels: this.data.domesticAiModels.map(model => {
        const savedModel = domesticAiModelsConfig.find(saved => saved && saved.name === model.name);
        return {
          ...model,
          checked: savedModel ? (savedModel.checked !== undefined ? savedModel.checked : false) : false
        };
      }),
      overseasAiModels: this.data.overseasAiModels.map(model => {
        const savedModel = overseasAiModelsConfig.find(saved => saved && saved.name === model.name);
        return {
          ...model,
          checked: savedModel ? (savedModel.checked !== undefined ? savedModel.checked : false) : false
        };
      })
    });

    // 只在配置有效时显示提示
    if (Object.keys(config).length > 0) {
      wx.showToast({
        title: '配置已加载',
        icon: 'success'
      });
    }
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

  /**
   * P2 修复：品牌名称输入处理
   */
  onBrandNameInput: function(e) {
    const value = e.detail.value;
    this.setData({ brandName: value });

    // 防抖保存 (500ms)
    clearTimeout(this.saveInputTimer);
    this.saveInputTimer = setTimeout(() => {
      this.saveCurrentInput();
    }, 500);
  },

  /**
   * P2 修复：竞品输入处理
   */
  onCompetitorInput: function(e) {
    const value = e.detail.value;
    this.setData({ currentCompetitor: value });

    // 防抖保存 (500ms)
    clearTimeout(this.saveInputTimer);
    this.saveInputTimer = setTimeout(() => {
      this.saveCurrentInput();
    }, 500);
  },

  /**
   * P2 修复：保存当前输入到本地存储
   */
  saveCurrentInput: function() {
    const { brandName, currentCompetitor, competitorBrands, customQuestions, domesticAiModels, overseasAiModels } = this.data;

    // 提取选中的国内平台
    const selectedDomestic = domesticAiModels
      .filter(model => model.checked)
      .map(model => model.name);

    // 提取选中的海外平台
    const selectedOverseas = overseasAiModels
      .filter(model => model.checked)
      .map(model => model.name);

    wx.setStorageSync('draft_diagnostic_input', {
      brandName: brandName || '',
      currentCompetitor: currentCompetitor || '',
      competitorBrands: competitorBrands || [],
      customQuestions: customQuestions || [],
      selectedModels: {
        domestic: selectedDomestic,
        overseas: selectedOverseas
      },
      updatedAt: Date.now()
    });

    console.log('草稿已自动保存', { brandName, currentCompetitor, customQuestionsCount: customQuestions?.length });
  },

  /**
   * P2 修复：从本地存储恢复草稿（增强完整性校验 + 合并 setData）
   */
  restoreDraft: function() {
    try {
      const draft = wx.getStorageSync('draft_diagnostic_input');

      // 完整性校验：只有数据完整才更新
      if (draft && draft.brandName) {
        // 检查是否是 7 天内的草稿
        const now = Date.now();
        const draftAge = now - (draft.updatedAt || 0);
        const sevenDays = 7 * 24 * 60 * 60 * 1000;

        if (draftAge < sevenDays) {
          // 恢复自定义问题（确保格式正确）
          const customQuestionsConfig = Array.isArray(draft.customQuestions) ? draft.customQuestions : [];
          const formattedQuestions = customQuestionsConfig.map(q => ({
            text: (q && q.text) || '',
            show: (q && q.show !== undefined) ? q.show : true
          }));

          // 恢复 AI 平台选择状态
          const selectedDomestic = draft.selectedModels?.domestic || [];
          const selectedOverseas = draft.selectedModels?.overseas || [];

          const updatedDomestic = this.data.domesticAiModels.map(model => ({
            ...model,
            checked: selectedDomestic.includes(model.name) && !model.disabled
          }));

          const updatedOverseas = this.data.overseasAiModels.map(model => ({
            ...model,
            checked: selectedOverseas.includes(model.name)
          }));

          // 合并为一次 setData，提高性能
          const updateData = {
            brandName: draft.brandName || '',
            currentCompetitor: draft.currentCompetitor || '',
            competitorBrands: Array.isArray(draft.competitorBrands) ? draft.competitorBrands : [],
            customQuestions: formattedQuestions.length > 0 ? formattedQuestions : this.data.customQuestions,
            domesticAiModels: updatedDomestic,
            overseasAiModels: updatedOverseas
          };
          
          this.setData(updateData);
          console.log('草稿已恢复', draft);
          
          // 更新计数（这些不依赖 setData，可以直接调用）
          this.updateSelectedModelCount();
          this.updateSelectedQuestionCount();
        } else {
          // 草稿过期，清除
          wx.removeStorageSync('draft_diagnostic_input');
          console.log('草稿已过期，已清除');
        }
      }
    } catch (error) {
      // 恢复失败不影响页面使用
      console.error('恢复草稿失败:', error);
    }
  },

  /**
   * P2 新增：加载用户 AI 平台偏好
   * 优先级：用户上次选择 > 默认配置
   */
  loadUserPlatformPreferences: function() {
    try {
      // 尝试从存储加载用户偏好
      const userPrefs = wx.getStorageSync(STORAGE_KEY_PLATFORM_PREFS);
      
      let selectedDomestic = [];
      let selectedOverseas = [];
      
      if (userPrefs && typeof userPrefs === 'object') {
        // 有用户偏好，使用用户上次选择
        selectedDomestic = userPrefs.domestic || [];
        selectedOverseas = userPrefs.overseas || [];
        console.log('加载用户 AI 平台偏好', userPrefs);
      } else {
        // 无用户偏好，使用默认配置
        selectedDomestic = DEFAULT_AI_PLATFORMS.domestic;
        selectedOverseas = DEFAULT_AI_PLATFORMS.overseas;
        console.log('使用默认 AI 平台配置', selectedDomestic);
      }
      
      // 更新国内平台选中状态
      const updatedDomestic = this.data.domesticAiModels.map(model => ({
        ...model,
        checked: selectedDomestic.includes(model.name) && !model.disabled
      }));
      
      // 更新海外平台选中状态
      const updatedOverseas = this.data.overseasAiModels.map(model => ({
        ...model,
        checked: selectedOverseas.includes(model.name)
      }));
      
      this.setData({
        domesticAiModels: updatedDomestic,
        overseasAiModels: updatedOverseas
      });
      
      // 更新选中数量
      this.updateSelectedModelCount();
      
    } catch (error) {
      console.error('加载用户平台偏好失败', error);
      // 降级：使用默认配置
      this.applyDefaultPlatformConfig();
    }
  },

  /**
   * P2 新增：应用默认平台配置
   */
  applyDefaultPlatformConfig: function() {
    const updatedDomestic = this.data.domesticAiModels.map(model => ({
      ...model,
      checked: DEFAULT_AI_PLATFORMS.domestic.includes(model.name) && !model.disabled
    }));
    
    const updatedOverseas = this.data.overseasAiModels.map(model => ({
      ...model,
      checked: DEFAULT_AI_PLATFORMS.overseas.includes(model.name)
    }));
    
    this.setData({
      domesticAiModels: updatedDomestic,
      overseasAiModels: updatedOverseas
    });
    
    this.updateSelectedModelCount();
  },

  /**
   * P2 新增：保存用户 AI 平台偏好
   */
  saveUserPlatformPreferences: function() {
    try {
      // 获取当前选中的平台
      const selectedDomestic = this.data.domesticAiModels
        .filter(model => model.checked)
        .map(model => model.name);
      
      const selectedOverseas = this.data.overseasAiModels
        .filter(model => model.checked)
        .map(model => model.name);
      
      // 保存到存储
      const userPrefs = {
        domestic: selectedDomestic,
        overseas: selectedOverseas,
        updatedAt: Date.now()
      };
      
      wx.setStorageSync(STORAGE_KEY_PLATFORM_PREFS, userPrefs);
      console.log('用户 AI 平台偏好已保存', userPrefs);
      
    } catch (error) {
      console.error('保存用户平台偏好失败', error);
    }
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
    this.saveCurrentInput();
  },

  addCustomQuestion: function() {
    let customQuestions = this.data.customQuestions;
    customQuestions.push({text: '', show: true});
    this.setData({ customQuestions: customQuestions });
    this.updateSelectedQuestionCount();
    this.saveCurrentInput();
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
    this.saveCurrentInput();
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
    this.saveCurrentInput();
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
    this.saveCurrentInput();
  },

  updateSelectedModelCount: function() {
    const selectedDomesticCount = this.data.domesticAiModels.filter(model => model.checked).length;
    const selectedOverseasCount = this.data.overseasAiModels.filter(model => model.checked).length;
    const totalCount = selectedDomesticCount + selectedOverseasCount;
    this.setData({ selectedModelCount: totalCount });
  },

  /**
   * P2 新增：重置所有输入
   * 清空品牌、竞品、自定义问题，恢复 AI 平台默认配置
   */
  resetAllInput: function() {
    // 重置品牌名称
    this.setData({ brandName: '' });

    // 重置竞品列表
    this.setData({ competitorBrands: [], currentCompetitor: '' });

    // 重置自定义问题为 3 个空的初始问题结构
    this.setData({ customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}] });

    // 重置 AI 平台偏好为默认配置（国内已验证平台默认选中）
    this.setData({ 
      selectedModels: DEFAULT_AI_PLATFORMS.domestic 
    });

    // 更新国内平台选中状态
    const updatedDomestic = this.data.domesticAiModels.map(model => ({
      ...model,
      checked: DEFAULT_AI_PLATFORMS.domestic.includes(model.name) && !model.disabled
    }));

    // 更新海外平台选中状态（默认不选中）
    const updatedOverseas = this.data.overseasAiModels.map(model => ({
      ...model,
      checked: DEFAULT_AI_PLATFORMS.overseas.includes(model.name)
    }));

    this.setData({
      domesticAiModels: updatedDomestic,
      overseasAiModels: updatedOverseas
    });

    // 清除本地缓存
    wx.removeStorageSync('draft_diagnostic_input');

    // 更新计数
    this.updateSelectedModelCount();
    this.updateSelectedQuestionCount();

    console.log('所有输入已重置');
  },

  /**
   * P2 新增：处理重置所有输入的确认交互
   */
  handleResetAll: function() {
    wx.showModal({
      title: '确认清空',
      content: '是否清空所有输入并重置配置？',
      success: (res) => {
        if (res.confirm) {
          this.resetAllInput();
          wx.showToast({
            title: '已清空所有输入',
            icon: 'success'
          });
        }
      }
    });
  },

  /**
   * 计算预估诊断时间
   * 基于 Questions × Models 计算
   */
  calculateEstimatedDuration: function() {
    const questionCount = this.getValidQuestions().length;
    const modelCount = this.getSelectedModelCount();
    
    // 基于 Questions × Models 计算预估时间
    // 假设每个 Q×M 组合平均耗时 15 秒
    const baseDuration = questionCount * modelCount * 15; // 秒
    
    // 添加缓冲时间（网络延迟、API 响应波动）
    const bufferTime = 30; // 秒
    
    const totalSeconds = baseDuration + bufferTime;
    
    // 格式化为"X 分 Y 秒"
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    return {
      duration: `${minutes}分${seconds}秒`,
      totalSeconds: totalSeconds
    };
  },

  /**
   * 启动进度伪装（AI 响应前匀速步进到 15%）
   */
  startProgressSimulation: function() {
    const that = this;
    let currentProgress = 0;
    const targetProgress = 15; // AI 响应前进度到 15%
    const duration = 5000; // 5 秒内完成
    const interval = 100;
    const step = (targetProgress / (duration / interval)) * 0.8; // 80% 速度，留余量
    
    const timer = setInterval(() => {
      currentProgress += step;
      
      if (currentProgress >= targetProgress) {
        clearInterval(timer);
        that.setData({ testProgress: targetProgress });
      } else {
        that.setData({ testProgress: Math.floor(currentProgress) });
      }
    }, interval);
    
    return timer;
  },

  /**
   * 添加研判日志
   */
  addIntelligenceLog: function(stage, model, message, type = 'info') {
    const logs = this.data.intelligenceLogs || [];
    const now = new Date();
    const timestamp = now.toLocaleTimeString('zh-CN', { hour12: false });
    
    logs.push({
      id: Date.now(),
      timestamp,
      stage,
      model,
      message,
      type  // 'info' | 'success' | 'error'
    });
    
    // 保持最近 20 条日志
    if (logs.length > 20) {
      logs.shift();
    }
    
    this.setData({
      intelligenceLogs: logs,
      showIntelligenceView: true
    });
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
      completedTime: null
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
      const requestData = {
        brand_list: brand_list,
        selectedModels: processedSelectedModels, // 确保格式正确并标准化模型名称
        custom_question: custom_question  // 修正字段名和类型
      };

      console.log('Sending request to API:', requestData);

      const res = await startBrandTestApi(requestData);

      console.log('API Response:', res);

      // 强制兼容多种返回格式
      const responseData = res.data || res;
      const executionId = responseData.execution_id || responseData.id || (responseData.data && responseData.data.execution_id);

      if (executionId) {
        console.log('✅ 战局指令下达成功，执行ID:', executionId);
        wx.hideLoading(); // 确保配对关闭
        // 【P0 修复】删除 detail 页后，直接在首页显示进度
        this.setData({
          isTesting: true,
          executionId: executionId,
          testProgress: 0,
          progressText: '正在启动 AI 认知诊断...'
        });
        
        // 启动进度轮询
        if (typeof this.pollTestProgress === 'function') {
          this.pollTestProgress(executionId);
        } // 调用跳转
      } else {
        throw new Error('未能从响应中提取有效ID');
      }
    } catch (err) {
      // 错误捕获防御：彻底重写 catch(err) 块
      // 要求：第一时间执行 wx.hideLoading()
      wx.hideLoading();
    
      console.error("Diagnostic Error:", err);
      console.error("Error details:", err.errMsg, err.data);
    
      // 要求：使用 err.data?.error || err.data?.message || err.errMsg 提取信息
      let extractedError = err.data?.error || err.data?.message || err.errMsg || "任务创建失败";
    
      // 如果错误信息包含网络相关错误，提供更友好的提示
      if (extractedError && (extractedError.includes('request:fail') || extractedError.includes('network'))) {
        extractedError = '网络连接失败，请检查网络设置或稍后重试';
      }
            
      // 如果是400错误，特别处理AI模型未配置的情况
      if (typeof extractedError === 'string' && (extractedError.includes('not registered or not configured') || extractedError.includes('API key'))) {
        extractedError = '所选AI模型未正确配置，请检查API密钥设置或选择其他AI模型\n\n请确保：\n1. 已在 .env 文件中配置相应API密钥\n2. 后端服务已重启加载新配置\n3. API密钥格式正确且有效';
      }
    
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
    // 使用新的 /api/test/status/{id} 接口进行轮询
    const pollInterval = setInterval(async () => {
      try {
        const res = await getTaskStatusApi(executionId);
        console.log("返回数据：",res)//调试用，上线前删除
        // 【P0 修复】getTaskStatusApi 返回的是 res.data，不是完整 res
        // 检查是否有有效数据
        if (res && (res.progress !== undefined || res.stage)) {
          // 更新调试区域显示原始JSON
          this.setData({ debugJson: JSON.stringify(res, null, 2) });

          // 使用服务层解析任务状态数据
          const parsedStatus = parseTaskStatus(res);

          // 更新进度条、状态文本和当前阶段
          this.setData({
            testProgress: parsedStatus.progress,
            progressText: parsedStatus.statusText,
            currentStage: parsedStatus.stage
          });

          // 如果状态为 completed，停止轮询并处理结果
          if (parsedStatus.stage === 'completed') {
            clearInterval(pollInterval);

            // 存储完整的报告数据
            const reportData = parsedStatus.detailed_results || parsedStatus.results;

            // 使用数据防御机制处理报告数据
            const processedReportData = this.processReportData(reportData);

            // 生成战略看板数据（第二阶段：聚合引擎）
            const dashboardData = this.generateDashboardData(processedReportData);

            this.setData({
              reportData: processedReportData,
              isTesting: false,
              testCompleted: true,
              completedTime: this.getCompletedTimeText(),
              progressText: '诊断完成，正在生成报告...',
              // 设置趋势图表数据
              trendChartData: this.generateTrendChartData(processedReportData),
              // 设置预测数据
              predictionData: this.extractPredictionData(processedReportData),
              // 设置评分数据
              scoreData: this.extractScoreData(processedReportData),
              // 设置竞争分析数据
              competitionData: this.extractCompetitionData(processedReportData),
              // 设置信源列表数据
              sourceListData: this.extractSourceListData(processedReportData),
              // 设置战略看板数据
              dashboardData: dashboardData
            });

            wx.showToast({ title: '诊断完成', icon: 'success' });
            this.renderReport(); // 触发报告渲染
            
            // 自动跳转到战略看板（第三阶段：麦肯锡看板）
            // 【P0 修复】删除 detail 页后，直接跳转到结果页
            wx.navigateTo({
              url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(this.data.brandName)}`
            });
          }
        } else {
          console.error('获取任务状态失败:', res);
          this.setData({ progressText: '获取状态失败...' });
        }
      } catch (err) {
        console.error('获取任务状态异常:', err);
        this.setData({ progressText: '状态连接异常...' });
      }
    }, 2000); // 每2秒轮询一次
  },

  viewDetailedResults: function() {
    // 优先使用新的 reportData，如果不存在则使用旧的 latestTestResults
    const resultsToUse = this.data.reportData || this.data.latestTestResults;

    if (resultsToUse) {
      // 直接传递对象，让微信小程序处理URL编码
      wx.navigateTo({
        url: `/pages/results/results?results=${encodeURIComponent(JSON.stringify(resultsToUse))}&competitiveAnalysis=${encodeURIComponent(JSON.stringify(this.data.latestCompetitiveAnalysis || {}))}&targetBrand=${encodeURIComponent(this.data.brandName)}`
      });
    } else {
      wx.showToast({ title: '暂无诊断结果', icon: 'none' });
    }
  },

  /**
   * 生成趋势图表数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 图表配置对象
   */
  generateTrendChartData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法生成趋势图表');
      return null;
    }

    try {
      // 检查 reportData 是否包含时间序列数据
      if (reportData.timeSeries && Array.isArray(reportData.timeSeries)) {
        // 如果有实际的时间序列数据，基于这些数据构建图表配置
        const timeSeries = reportData.timeSeries;
        const dates = timeSeries.map(item => item.period || item.date || '未知时间');
        const values = timeSeries.map(item => item.value || 0);

        // 如果有预测数据，也提取出来
        const predictions = reportData.prediction && Array.isArray(reportData.prediction.forecast_points)
          ? reportData.prediction.forecast_points.map(point => point.value || 0)
          : [];

        return {
          dates: dates,
          values: values,
          predictions: predictions
        };
      } else {
        // 如果没有实际数据，返回默认的示例数据
        return {
          dates: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
          values: [30, 45, 60, 75, 80, 85, 90],
          predictions: [88, 92, 95, 97, 98, 99, 100]
        };
      }
    } catch (error) {
      console.error('生成趋势图表数据失败:', error);
      // 返回默认的空数据结构
      return {
        dates: [],
        values: [],
        predictions: []
      };
    }
  },

  /**
   * 提取信源列表数据
   * @param {Object} reportData - 报告数据
   * @returns {Array} 信源列表
   */
  extractSourceListData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取信源列表');
      return [];
    }

    try {
      // 检查 reportData 是否包含 sources 属性
      if (reportData.sources && Array.isArray(reportData.sources)) {
        // 如果有实际的信源数据，直接返回
        return reportData.sources.map(source => ({
          title: source.title || source.name || '未知信源',
          url: source.url || source.link || '',
          score: source.score || source.confidence || 0,
          type: source.type || '未知类型'
        }));
      } else if (reportData.results && Array.isArray(reportData.results)) {
        // 如果没有 sources，尝试从 results 中提取信源信息
        const sources = [];
        reportData.results.forEach(result => {
          if (result.sources && Array.isArray(result.sources)) {
            result.sources.forEach(source => {
              sources.push({
                title: source.title || source.name || '未知信源',
                url: source.url || source.link || '',
                score: source.score || source.confidence || 0,
                type: source.type || '未知类型'
              });
            });
          }
        });
        return sources;
      } else {
        // 如果没有实际数据，返回默认的示例数据
        return [
          {
            title: '品牌官网',
            url: 'https://brand.example.com',
            score: 95,
            type: '官方'
          },
          {
            title: '行业报告',
            url: 'https://industry-report.com',
            score: 87,
            type: '第三方'
          },
          {
            title: '社交媒体',
            url: 'https://social-media.com',
            score: 78,
            type: 'UGC'
          }
        ];
      }
    } catch (error) {
      console.error('提取信源列表数据失败:', error);
      // 返回空数组作为最后的防线
      return [];
    }
  },

  /**
   * 信源点击事件处理
   */
  onSourceTap: function(event) {
    const { source, index } = event.detail;
    console.log('信源被点击:', source, index);

    // 可以在这里处理信源点击事件，比如打开详情页或外部链接
    if (source.url) {
      // 在浏览器中打开链接
      wx.setClipboardData({
        data: source.url,
        success: () => {
          wx.showToast({
            title: '链接已复制',
            icon: 'success'
          });
        }
      });
    }
  },

  /**
   * 提取评分数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 评分数据
   */
  extractScoreData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取评分数据');
      return {};
    }

    try {
      // 根据 API 文档规范，查找 scores 属性
      if (reportData.scores) {
        // 直接返回 scores 对象，确保字段名符合契约
        return {
          accuracy: reportData.scores.accuracy || reportData.scores.Accuracy || 0,
          completeness: reportData.scores.completeness || reportData.scores.Completeness || 0,
          relevance: reportData.scores.relevance || reportData.scores.Relevance || 0,
          security: reportData.scores.security || reportData.scores.Security || 0,
          sentiment: reportData.scores.sentiment || reportData.scores.Sentiment || 0,
          competitiveness: reportData.scores.competitiveness || reportData.scores.Competitiveness || 0,
          authority: reportData.scores.authority || reportData.scores.Authority || 0
        };
      } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
        // 如果没有直接的 scores 属性，尝试从第一个结果中提取
        const firstResult = reportData.results[0];
        if (firstResult.scores) {
          return {
            accuracy: firstResult.scores.accuracy || firstResult.scores.Accuracy || 0,
            completeness: firstResult.scores.completeness || firstResult.scores.Completeness || 0,
            relevance: firstResult.scores.relevance || firstResult.scores.Relevance || 0,
            security: firstResult.scores.security || firstResult.scores.Security || 0,
            sentiment: firstResult.scores.sentiment || firstResult.scores.Sentiment || 0,
            competitiveness: firstResult.scores.competitiveness || firstResult.scores.Competitiveness || 0,
            authority: firstResult.scores.authority || firstResult.scores.Authority || 0
          };
        }
      }

      // 如果没有找到评分数据，返回默认值
      return {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        security: 0,
        sentiment: 0,
        competitiveness: 0,
        authority: 0
      };
    } catch (error) {
      console.error('提取评分数据失败:', error);
      // 返回默认结构作为最后的防线
      return {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        security: 0,
        sentiment: 0,
        competitiveness: 0,
        authority: 0
      };
    }
  },

  /**
   * 提取竞争分析数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 竞争分析数据
   */
  extractCompetitionData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取竞争分析数据');
      return {};
    }

    try {
      // 根据 API 文档规范，查找竞争分析相关属性
      if (reportData.competition) {
        // 直接返回竞争分析对象
        return {
          brand_keywords: reportData.competition.brand_keywords || reportData.competition.brandKeywords || [],
          shared_keywords: reportData.competition.shared_keywords || reportData.competition.sharedKeywords || [],
          competitors: reportData.competition.competitors || []
        };
      } else if (reportData.competitive_analysis) {
        // 兼容另一种命名方式
        return {
          brand_keywords: reportData.competitive_analysis.brand_keywords || reportData.competitive_analysis.brandKeywords || [],
          shared_keywords: reportData.competitive_analysis.shared_keywords || reportData.competitive_analysis.sharedKeywords || [],
          competitors: reportData.competitive_analysis.competitors || []
        };
      } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
        // 如果没有直接的竞争分析属性，尝试从第一个结果中提取
        const firstResult = reportData.results[0];
        if (firstResult.competition) {
          return {
            brand_keywords: firstResult.competition.brand_keywords || firstResult.competition.brandKeywords || [],
            shared_keywords: firstResult.competition.shared_keywords || firstResult.competition.sharedKeywords || [],
            competitors: firstResult.competition.competitors || []
          };
        } else if (firstResult.competitive_analysis) {
          return {
            brand_keywords: firstResult.competitive_analysis.brand_keywords || firstResult.competitive_analysis.brandKeywords || [],
            shared_keywords: firstResult.competitive_analysis.shared_keywords || firstResult.competitive_analysis.sharedKeywords || [],
            competitors: firstResult.competitive_analysis.competitors || []
          };
        }
      }

      // 如果没有找到竞争分析数据，返回默认值
      return {
        brand_keywords: [],
        shared_keywords: [],
        competitors: []
      };
    } catch (error) {
      console.error('提取竞争分析数据失败:', error);
      // 返回默认结构作为最后的防线
      return {
        brand_keywords: [],
        shared_keywords: [],
        competitors: []
      };
    }
  },

  /**
   * 处理报告数据，应用数据防御机制
   * @param {Object} reportData - 原始报告数据
   * @returns {Object} 处理后的报告数据
   */
  processReportData: function(reportData) {
    // 数据防御：永远假设后端可能返回 null、undefined 或空数组
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，返回默认结构');
      return this.getDefaultReportStructure();
    }

    // 使用数据防御法则处理各个数据部分
    return {
      // 预测数据防御
      prediction: this.defensiveGet(reportData, 'prediction', {}) || {},

      // 评分数据防御
      scores: this.defensiveGet(reportData, 'scores', {}) || {},

      // 竞争分析数据防御
      competition: this.defensiveGet(reportData, 'competition', {}) || {},

      // 信源数据防御
      sources: this.defensiveGet(reportData, 'sources', []) || [],

      // 趋势数据防御
      trends: this.defensiveGet(reportData, 'trends', {}) || {},

      // 结果数据防御
      results: this.defensiveGet(reportData, 'results', []) || [],

      // 原始数据备份
      original: reportData
    };
  },

  /**
   * 安全获取对象属性，防止 null/undefined 错误
   * @param {Object} obj - 源对象
   * @param {String} prop - 属性路径，支持点号分隔如 'data.prediction.points'
   * @param {*} defaultValue - 默认值
   * @returns {*} 属性值或默认值
   */
  defensiveGet: function(obj, prop, defaultValue = null) {
    try {
      // 如果对象为空，返回默认值
      if (!obj || typeof obj !== 'object') {
        return defaultValue;
      }

      // 支持点号路径访问
      const props = prop.split('.');
      let result = obj;

      for (const p of props) {
        if (result == null || typeof result !== 'object') {
          return defaultValue;
        }
        result = result[p];

        // 如果中间某个属性为 null 或 undefined，返回默认值
        if (result == null) {
          return defaultValue;
        }
      }

      // 如果结果是数组但为空，返回默认值（根据需要调整）
      if (Array.isArray(defaultValue) && Array.isArray(result) && result.length === 0) {
        return defaultValue;
      }

      return result;
    } catch (error) {
      console.error(`获取属性 ${prop} 时出错:`, error);
      return defaultValue;
    }
  },

  /**
   * 获取默认报告结构
   * @returns {Object} 默认报告结构
   */
  getDefaultReportStructure: function() {
    return {
      prediction: {
        forecast_points: [],
        confidence: 0,
        trend: 'neutral'
      },
      scores: {
        accuracy: 0,
        completeness: 0,
        relevance: 0,
        security: 0,
        sentiment: 0,
        competitiveness: 0
      },
      competition: {
        brand_keywords: [],
        shared_keywords: [],
        competitor_keywords: [],
        competitors: []
      },
      sources: [],
      trends: {
        historical: [],
        projected: []
      },
      results: [],
      original: {}
    };
  },

  /**
   * 渲染报告 - 触发报告展示逻辑
   */
  renderReport: function() {
    console.log('开始渲染报告...');

    // 更新UI以反映报告已准备好
    this.setData({
      reportReady: true
    });

    // 可以在这里添加额外的报告渲染逻辑
    // 例如：动画效果、数据可视化初始化等
  },

  /**
   * 提取预测数据
   * @param {Object} reportData - 报告数据
   * @returns {Object} 预测数据
   */
  extractPredictionData: function(reportData) {
    // 防御性处理：检查参数是否存在且为对象
    if (!reportData || typeof reportData !== 'object') {
      console.warn('报告数据无效，无法提取预测数据');
      return {};
    }

    try {
      // 根据 API 文档规范，查找预测相关属性
      if (reportData.prediction) {
        // 直接返回预测对象
        return {
          forecast_points: (reportData.prediction.forecast_points || reportData.prediction.forecastPoints) || [],
          confidence: reportData.prediction.confidence || 0,
          trend: reportData.prediction.trend || 'neutral'
        };
      } else if (reportData.results && Array.isArray(reportData.results) && reportData.results.length > 0) {
        // 如果没有直接的预测属性，尝试从第一个结果中提取
        const firstResult = reportData.results[0];
        if (firstResult.prediction) {
          return {
            forecast_points: (firstResult.prediction.forecast_points || firstResult.prediction.forecastPoints) || [],
            confidence: firstResult.prediction.confidence || 0,
            trend: firstResult.prediction.trend || 'neutral'
          };
        }
      }

      // 如果没有找到预测数据，返回默认值
      return {
        forecast_points: [],
        confidence: 0,
        trend: 'neutral'
      };
    } catch (error) {
      console.error('提取预测数据失败:', error);
      // 返回默认结构作为最后的防线
      return {
        forecast_points: [],
        confidence: 0,
        trend: 'neutral'
      };
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
    // 跳转到个人历史记录页面（查看本地保存的结果，无需登录）
    wx.navigateTo({ url: '/pages/personal-history/personal-history' });
  },

  /**
   * 【新增】查看最新诊断结果
   */
  viewLatestDiagnosis: function() {
    try {
      const executionId = this.data.latestDiagnosisInfo.executionId;
      const brandList = [
        this.data.latestDiagnosisInfo.brand,
        ...(wx.getStorageSync('latestCompetitorBrands') || [])
      ];

      if (executionId) {
        // 跳转到详情页面
        // 【P0 修复】删除 detail 页后，进度轮询在首页进行
        wx.navigateTo({
          url: url,
          success: () => {
            console.log('✅ 跳转到最新诊断结果页面');
          },
          fail: (err) => {
            console.error('❌ 跳转失败:', err);
            wx.showToast({
              title: '跳转失败，请重试',
              icon: 'none'
            });
          }
        });
      } else {
        wx.showToast({
          title: '暂无诊断结果',
          icon: 'none'
        });
      }
    } catch (e) {
      console.error('查看最新诊断结果失败:', e);
      wx.showToast({
        title: '操作失败，请重试',
        icon: 'none'
      });
    }
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
  },

  /**
   * 页面滚动事件处理，用于吸顶效果
   */
  onPageScroll: function(e) {
    // 当页面滚动超过一定距离时，激活吸顶效果
    const scrollTop = e.scrollTop || 0;
    const shouldStick = scrollTop > 100; // 滚动超过100rpx时激活吸顶

    if (shouldStick !== this.data.isSticky) {
      this.setData({
        isSticky: shouldStick
      });
    }
  },

  /**
   * 分享功能
   */
  onShareAppMessage: function() {
    // 获取当前报告的总分，如果没有则使用默认值
    const totalScore = this.calculateTotalScore();
    const brandName = this.data.brandName || '品牌';

    return {
      title: `[${totalScore}分] ${brandName} GEO 品牌诊断报告已生成`,
      path: `/pages/index/index?brandName=${encodeURIComponent(brandName)}`,
      imageUrl: '/images/share-image.png' // 如果有分享图片的话
    };
  },

  /**
   * 清理系统缓存
   */
  clearSystemCache: function() {
    wx.showModal({
      title: '确认清理',
      content: '确定要清理系统缓存吗？这将删除临时文件和日志，但不会影响您的配置和数据。',
      success: (res) => {
        if (res.confirm) {
          // 清理本地存储
          wx.clearStorage({
            success: () => {
              console.log('本地存储清理成功');
            },
            fail: (err) => {
              console.error('本地存储清理失败:', err);
            }
          });

          // 清理本地文件
          wx.getSavedFileList({
            success: (res) => {
              const fileList = res.fileList || [];
              let cleanedCount = 0;

              fileList.forEach(file => {
                // 删除后缀为 .log、.tmp 或 .txt 的测试记录文件
                if (file.filePath.endsWith('.log') ||
                    file.filePath.endsWith('.tmp') ||
                    file.filePath.endsWith('.txt')) {
                  wx.removeSavedFile({
                    filePath: file.filePath,
                    success: () => {
                      cleanedCount++;
                    },
                    fail: (err) => {
                      console.error('删除文件失败:', file.filePath, err);
                    }
                  });
                }
              });

              if (cleanedCount > 0) {
                console.log(`清理了 ${cleanedCount} 个临时文件`);
              }

              // 清理缓存
              wx.clearStorageSync();

              wx.showToast({
                title: `清理完成，共清理${cleanedCount}个文件`,
                icon: 'success'
              });
            },
            fail: (err) => {
              console.error('获取文件列表失败:', err);
              wx.showToast({
                title: '获取文件列表失败',
                icon: 'none'
              });
            }
          });
        }
      }
    });
  },

  /**
   * 计算总分
   */
  calculateTotalScore: function() {
    if (!this.data.scoreData) {
      return 0;
    }

    const scores = this.data.scoreData;
    const total = (scores.accuracy || 0) +
                  (scores.completeness || 0) +
                  (scores.relevance || 0) +
                  (scores.security || 0) +
                  (scores.sentiment || 0) +
                  (scores.competitiveness || 0) +
                  (scores.authority || 0);

    return Math.round(total / 7); // 平均分
  },

  /**
   * 获取趋势指示器
   */
  getTrendIndicator: function() {
    if (!this.data.scoreData) {
      return '→'; // 默认水平箭头
    }

    // 简单的趋势判断逻辑，可以根据实际需求调整
    const scores = this.data.scoreData;
    const currentScore = this.calculateTotalScore();

    // 这里可以加入与历史数据比较的逻辑来确定趋势
    // 暂时返回一个示例趋势
    if (currentScore > 80) {
      return '↑'; // 上升趋势
    } else if (currentScore < 60) {
      return '↓'; // 下降趋势
    } else {
      return '→'; // 平稳趋势
    }
  },

  /**
   * 触发内容入场动画
   */
  triggerContentAnimation: function() {
    // 延迟显示内容以触发动画
    setTimeout(() => {
      this.setData({
        contentVisible: true
      });
    }, 100);
  },

  /**
   * 渲染报告 - 触发报告展示逻辑
   */
  renderReport: function() {
    console.log('开始渲染报告...');

    // 更新UI以反映报告已准备好
    this.setData({
      reportReady: true
    });

    // 触发内容入场动画
    this.triggerContentAnimation();

    // 可以在这里添加额外的报告渲染逻辑
    // 例如：动画效果、数据可视化初始化等
  },



  /**
   * 设置自定义API服务器地址
   */
  setCustomServerUrl: function() {
    wx.showModal({
      title: '设置API服务器地址',
      editable: true,
      placeholderText: '请输入API服务器地址，例如：http://192.168.1.100:5000',
      success: (res) => {
        if (res.cancel) {
          return;
        }

        const inputUrl = res.content.trim();
        if (!inputUrl) {
          wx.showToast({
            title: '请输入有效的服务器地址',
            icon: 'none'
          });
          return;
        }

        if (!inputUrl.startsWith('http://') && !inputUrl.startsWith('https://')) {
          wx.showToast({
            title: '地址必须以http://或https://开头',
            icon: 'none'
          });
          return;
        }

        // 保存到本地存储
        wx.setStorageSync('custom_base_url', inputUrl);

        wx.showToast({
          title: '服务器地址已更新',
          icon: 'success'
        });
      }
    });
  },

  /**
   * 生成战略看板数据（第二阶段：聚合引擎）
   * @param {Object} processedReportData - 处理后的报告数据
   * @returns {Object} 看板数据
   */
  generateDashboardData: function(processedReportData) {
    try {
      // 提取原始结果数组
      const rawResults = Array.isArray(processedReportData)
        ? processedReportData
        : (processedReportData.detailed_results || processedReportData.results || []);

      if (!rawResults || rawResults.length === 0) {
        console.warn('没有可用的原始结果数据');
        return null;
      }

      // 调用聚合引擎
      const brandName = this.data.brandName;
      const competitors = this.data.competitorBrands || [];

      // 【新增】传递后端分析数据
      const additionalData = {
        semantic_drift_data: processedReportData.semantic_drift_data || null,
        semantic_contrast_data: processedReportData.semantic_contrast_data || null,
        recommendation_data: processedReportData.recommendation_data || null,
        negative_sources: processedReportData.negative_sources || null,
        brand_scores: processedReportData.brand_scores || null,
        competitive_analysis: processedReportData.competitive_analysis || null,
        overall_score: processedReportData.overall_score || null
      };

      const dashboardData = aggregateReport(rawResults, brandName, competitors, additionalData);

      // 保存到全局存储（供 dashboard 页面使用）
      const app = getApp();
      app.globalData.lastReport = {
        raw: rawResults,
        dashboard: dashboardData,
        competitors: competitors
      };

      return dashboardData;
    } catch (error) {
      console.error('生成战略看板数据失败:', error);
      return null;
    }
  },

  /**
   * 跳转到战略看板（第三阶段：麦肯锡看板）
   * 【P0 修复】使用 redirectTo 替换 navigateTo，避免页面栈堆积
   */
  navigateToDashboard: function() {
    try {
      // 保存报告数据到存储
      const reportData = this.data.reportData || this.data.dashboardData;
      const executionId = reportData?.executionId || this.data.executionId || Date.now().toString();
      
      if (reportData) {
        wx.setStorageSync('lastReport', reportData);
        console.log('✅ 报告数据已保存到本地存储');

        // 【新增】保存 detailed_results 供结果页使用
        const detailedResults = reportData.detailed_results || reportData.results || [];
        if (detailedResults && detailedResults.length > 0) {
          wx.setStorageSync('latestTestResults_' + executionId, detailedResults);
          wx.setStorageSync('latestTestResults', detailedResults);  // 兼容旧 key
          console.log('✅ 测试结果已保存到本地存储:', detailedResults.length, '条');
        }

        // 保存品牌和竞品信息（确保 brandName 不为空）
        const brandName = this.data.brandName || reportData.brand_name || '品牌';
        wx.setStorageSync('latestTargetBrand', brandName);
        console.log('✅ 品牌名称已保存:', brandName);
        
        if (this.data.competitorBrands) {
          wx.setStorageSync('latestCompetitorBrands', this.data.competitorBrands);
        }

        // 【新增】保存 competitiveAnalysis 和 negativeSources
        if (reportData.competitiveAnalysis) {
          wx.setStorageSync('latestCompetitiveAnalysis_' + executionId, reportData.competitiveAnalysis);
          wx.setStorageSync('latestCompetitiveAnalysis', reportData.competitiveAnalysis);
          console.log('✅ 竞品分析已保存');
        }
        if (reportData.negativeSources) {
          wx.setStorageSync('latestNegativeSources_' + executionId, reportData.negativeSources);
          console.log('✅ 负面信源已保存');
        }

        // 【新增】保存语义偏移数据和优化建议
        if (reportData.semanticDriftData) {
          wx.setStorageSync('latestSemanticDrift_' + executionId, reportData.semanticDriftData);
          console.log('✅ 语义偏移数据已保存');
        }
        if (reportData.recommendationData) {
          wx.setStorageSync('latestRecommendations_' + executionId, reportData.recommendationData);
          console.log('✅ 优化建议已保存');
        }
      }

      // 延迟 500ms 跳转，让用户看到完成提示
      setTimeout(() => {
        wx.redirectTo({
          url: '/pages/report/dashboard/index?executionId=' + (reportData.executionId || ''),
          success: () => {
            console.log('✅ 诊断完成，已跳转到 Dashboard');
          },
          fail: (err) => {
            console.error('跳转到战略看板失败:', err);
            // 如果跳转失败，显示提示
            wx.showToast({
              title: '请前往"我的"查看报告',
              icon: 'none'
            });
          }
        });
      }, 500);
    } catch (error) {
      console.error('导航到战略看板失败:', error);
    }
  },

  /**
   * 查看诊断报告（跳转到 Dashboard）
   */
  viewReport: function() {
    const reportData = this.data.reportData || this.data.dashboardData;
    if (reportData) {
      // 保存报告数据到存储
      if (reportData.executionId) {
        wx.setStorageSync('lastReport', reportData);
      }
      
      wx.navigateTo({
        url: '/pages/report/dashboard/index?executionId=' + (reportData.executionId || ''),
        fail: (err) => {
          console.error('跳转报告页面失败:', err);
          wx.showToast({
            title: '跳转失败',
            icon: 'none'
          });
        }
      });
    } else {
      wx.showToast({
        title: '暂无报告数据',
        icon: 'none'
      });
    }
  },

  /**
   * 重新诊断
   */
  retryDiagnosis: function() {
    wx.showModal({
      title: '确认重新诊断',
      content: '重新诊断将覆盖当前的诊断结果，是否继续？',
      success: (res) => {
        if (res.confirm) {
          // 清空完成状态
          this.setData({
            testCompleted: false,
            completedTime: null
          });
          // 开始新的诊断
          this.startBrandTest();
        }
      }
    });
  },

  /**
   * 获取完成时间文本
   */
  getCompletedTimeText: function() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    return `完成于 ${hours}:${minutes}`;
  },

});
