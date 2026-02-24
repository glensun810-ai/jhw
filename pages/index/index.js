const { debug, info, warn, error } = require('../../utils/logger');

// ==================== 模块化重构后引入的服务 ====================
// 工具函数
const {
  calculateTotalScore,
  getTrendIndicator,
  getCompletedTimeText
} = require('../../utils/helperUtils');

// 数据处理服务
const {
  processReportData,
  extractPredictionData,
  extractScoreData,
  extractCompetitionData,
  extractSourceListData,
  generateTrendChartData
} = require('../../services/dataProcessorService');

// 诊断执行服务
const {
  validateInput,
  buildPayload,
  startDiagnosis,
  createPollingController,
  generateDashboardData
} = require('../../services/brandTestService');

// P1-1 修复：统一 Storage 管理器
const {
  saveDiagnosisResult,
  cleanupExpiredData
} = require('../../utils/storage-manager');

// 缓存服务（P2 优化）
const {
  getCachedDiagnosis,
  cacheDiagnosis,
  clearAllCache,
  getCacheStats,
  isCacheHit
} = require('../../services/cacheService');

// 草稿管理服务
const {
  saveDraft,
  restoreDraft,
  clearDraft,
  formatDraftQuestions,
  formatDraftModels,
  STORAGE_KEY: DRAFT_STORAGE_KEY,
  DRAFT_EXPIRY
} = require('../../services/draftService');

// 配置管理服务
const {
  saveConfig,
  loadConfig,
  deleteConfig,
  getAllConfigs,
  configExists,
  STORAGE_KEY: CONFIG_STORAGE_KEY
} = require('../../services/configService');

// 导航服务
const {
  saveAndNavigateToResults,
  navigateToDashboard,
  navigateToReportDetail,
  navigateToHistory,
  navigateToConfigManager,
  navigateToPermissionManager,
  navigateToDataManager,
  navigateToUserGuide
} = require('../../services/navigationService');

// 初始化服务
const {
  initializeDefaults,
  checkServerConnection,
  loadUserPlatformPreferences,
  saveUserPlatformPreferences,
  DEFAULT_AI_PLATFORMS,
  STORAGE_KEY_PLATFORM_PREFS
} = require('../../services/initService');

// 原有引入保留
const { checkServerConnectionApi, startBrandTestApi, getTestProgressApi, getTaskStatusApi } = require('../../api/home');
const { parseTaskStatus } = require('../../services/taskStatusService');
const { aggregateReport } = require('../../services/reportAggregator');

const appid = 'wx8876348e089bc261'; // 您的 AppID

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
    competitorInputFocus: false,  // 【用户体验优化】竞品输入框焦点控制

    // 问题设置
    customQuestions: [{text: '', show: true}, {text: '', show: true}, {text: '', show: true}],
    selectedQuestionCount: 0,

    // AI模型选择
    domesticAiModels: [
      { name: 'DeepSeek', id: 'deepseek', checked: true, logo: 'DS', tags: ['综合', '代码'] },
      { name: '豆包', id: 'doubao', checked: true, logo: 'DB', tags: ['综合', '创意'] },
      { name: '通义千问', id: 'qwen', checked: true, logo: 'QW', tags: ['综合', '长文本'] },
      { name: '元宝', id: 'yuanbao', checked: false, logo: 'YB', tags: ['综合']},
      { name: 'Kimi', id: 'kimi', checked: false, logo: 'KM', tags: ['长文本'] },
      { name: '文心一言', id: 'wenxin', checked: false, logo: 'WX', tags: ['综合', '创意'] },
      { name: '讯飞星火', id: 'xinghuo', checked: false, logo: 'XF', tags: ['综合', '语音'] },
      { name: '智谱AI', id: 'zhipu', checked: false, logo: 'ZP', tags: ['综合', 'GLM'] },      
    ],
    overseasAiModels: [
      { name: 'ChatGPT', id: 'chatgpt', checked: true, logo: 'GPT', tags: ['综合', '代码'] },
      { name: 'Gemini', id: 'gemini', checked: false, logo: 'GM', tags: ['综合', '多模态'] },
      { name: 'Claude', id: 'claude', checked: false, logo: 'CD', tags: ['长文本', '创意'] },
      { name: 'Perplexity', id: 'perplexity', checked: false, logo: 'PE', tags: ['综合', '长文本'] },
      { name: 'Grok', id: 'grok', checked: false, logo: 'GR', tags: ['推理', '多模态'] },
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

      // 1. 初始化默认值（使用服务）
      initializeDefaults(this);

      // 2. 检查服务器连接（使用服务，异步）
      checkServerConnection(this);

      // 3. 加载用户 AI 平台偏好（使用服务）
      loadUserPlatformPreferences(this);
      this.updateSelectedModelCount();
      this.updateSelectedQuestionCount();

      // 4. 防御性读取 config.estimate（多层保护）
      let estimate = { duration: '30s', steps: 5 };
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
    // 停止轮询控制器
    if (this.pollingController && typeof this.pollingController.stop === 'function') {
      this.pollingController.stop();
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
   * P2 修复：保存当前输入到本地存储（使用服务）
   */
  saveCurrentInput: function() {
    const { brandName, currentCompetitor, competitorBrands, customQuestions, domesticAiModels, overseasAiModels } = this.data;

    const selectedDomestic = domesticAiModels
      .filter(model => model.checked)
      .map(model => model.name);

    const selectedOverseas = overseasAiModels
      .filter(model => model.checked)
      .map(model => model.name);

    saveDraft({
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
  },

  /**
   * P2 修复：从本地存储恢复草稿（使用服务）
   */
  restoreDraft: function() {
    const draft = restoreDraft(); // 调用服务函数

    if (draft) {
      // 恢复自定义问题（确保格式正确）
      const formattedQuestions = formatDraftQuestions(draft.customQuestions);

      // 恢复 AI 平台选择状态
      const formattedModels = formatDraftModels(
        this.data.domesticAiModels.concat(this.data.overseasAiModels),
        draft.selectedModels
      );

      // 合并为一次 setData，提高性能
      const updateData = {
        brandName: draft.brandName || '',
        currentCompetitor: draft.currentCompetitor || '',
        competitorBrands: Array.isArray(draft.competitorBrands) ? draft.competitorBrands : [],
        customQuestions: formattedQuestions.length > 0 ? formattedQuestions : this.data.customQuestions,
        domesticAiModels: formattedModels.domestic || this.data.domesticAiModels,
        overseasAiModels: formattedModels.overseas || this.data.overseasAiModels
      };

      this.setData(updateData);
      console.log('草稿已恢复', draft);

      // 更新计数
      this.updateSelectedModelCount();
      this.updateSelectedQuestionCount();
    }
  },

  /**
   * P2 新增：加载用户 AI 平台偏好（使用服务）
   * 优先级：用户上次选择 > 默认配置
   */
  loadUserPlatformPreferences: function() {
    // 已由 initService.loadUserPlatformPreferences 处理
  },

  /**
   * P2 新增：应用默认平台配置
   */
  applyDefaultPlatformConfig: function() {
    // 已由 initService 处理
  },

  /**
   * P2 新增：保存用户 AI 平台偏好（使用服务）
   */
  saveUserPlatformPreferences: function() {
    const selectedDomestic = this.data.domesticAiModels
      .filter(model => model.checked)
      .map(model => model.name);

    const selectedOverseas = this.data.overseasAiModels
      .filter(model => model.checked)
      .map(model => model.name);

    saveUserPlatformPreferences({ domestic: selectedDomestic, overseas: selectedOverseas });
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

    // 添加竞品
    competitorBrands.push(currentCompetitor);
    
    // 【用户体验优化】添加成功后清空输入框，但保持焦点方便连续输入
    this.setData({ 
      competitorBrands: competitorBrands,
      currentCompetitor: '',  // 清空输入框
      competitorInputFocus: true  // 保持焦点，方便继续输入下一个竞品
    });
    
    wx.showToast({ title: '添加成功', icon: 'success', duration: 1500 });
    
    // 保存输入状态
    this.saveCurrentInput();
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
    // P1-007 新增：使用更专业的默认问题列表
    if (customQuestions.length === 0) {
      customQuestions = [
        "{brandName}的核心竞争优势是什么？",
        "{brandName}在目标用户群体中的认知度如何？",
        "{brandName}与竞品的主要差异化体现在哪里？"
      ];
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

  async callBackendBrandTest(brandList, selectedModels, customQuestions) {
    wx.showLoading({ title: '启动诊断...' });

    try {
      // 从品牌列表中提取主品牌名称（第一个元素）
      const mainBrandName = Array.isArray(brandList) ? brandList[0] : brandList;

      const inputData = {
        brandName: mainBrandName,
        competitorBrands: Array.isArray(brandList) ? brandList.slice(1) : [],
        selectedModels,
        customQuestions
      };

      // P0-011 修复：只启动诊断，不轮询（统一使用 pollingController）
      const executionId = await startDiagnosis(inputData);

      // 统一使用 pollingController 轮询
      this.pollingController = createPollingController(
        executionId,
        (parsedStatus) => {
          this.setData({
            testProgress: parsedStatus.progress,
            progressText: parsedStatus.statusText,
            currentStage: parsedStatus.stage,
            debugJson: JSON.stringify(parsedStatus, null, 2)
          });
        },
        (parsedStatus) => {
          wx.hideLoading();
          this.handleDiagnosisComplete(parsedStatus, executionId);
        },
        (error) => {
          wx.hideLoading();
          this.handleDiagnosisError(error);
        }
      );

      // P2 优化：轮询间隔从 2000ms 缩短到 800ms，并立即触发第一次轮询
      this.pollingController.start(800, true);
    } catch (err) {
      wx.hideLoading();
      this.handleDiagnosisError(err);
    }
  },

  /**
   * 处理诊断完成
   * @param {Object} parsedStatus - 解析后的状态
   * @param {string} executionId - 执行 ID
   */
  handleDiagnosisComplete(parsedStatus, executionId) {
    try {
      // 【P1-2 新增】部分完成警告提示
      if (parsedStatus.warning || parsedStatus.missing_count > 0) {
        const resultsCount = (parsedStatus.results || []).length || (parsedStatus.detailed_results || []).length;
        const totalCount = resultsCount + (parsedStatus.missing_count || 0);
        wx.showModal({
          title: '诊断提示',
          content: `诊断部分完成：已获取 ${resultsCount}/${totalCount} 个结果\n${parsedStatus.warning || '部分 AI 调用失败，已展示可用结果'}`,
          showCancel: false,
          confirmText: '查看结果'
        });
      }

      // P2 优化：先跳转结果页，再异步处理数据，减少等待时间
      // 保存核心数据并跳转
      const resultsToSave = parsedStatus.detailed_results || parsedStatus.results || [];
      const competitiveAnalysisToSave = parsedStatus.competitive_analysis || {};
      const brandScoresToSave = competitiveAnalysisToSave.brandScores || {};

      // P1-1 修复：使用统一 Storage 管理器保存
      const saveSuccess = saveDiagnosisResult(executionId, {
        brandName: this.data.brandName,
        results: resultsToSave,
        competitiveAnalysis: competitiveAnalysisToSave,
        brandScores: brandScoresToSave,
        detailedResults: parsedStatus.detailed_results || {},
        semanticDriftData: parsedStatus.semantic_drift_data || null,
        recommendationData: parsedStatus.recommendation_data || null
      });

      if (saveSuccess) {
        console.log('✅ P1-1 数据已保存到统一 Storage:', executionId);
      } else {
        console.warn('⚠️  Storage 保存失败，使用备用方案');
        // 备用方案：旧格式保存（但添加 version 字段）
        wx.setStorageSync('last_diagnostic_results', {
          version: '2.0',  // P2 修复：添加版本号
          results: resultsToSave,
          competitiveAnalysis: competitiveAnalysisToSave,
          brandScores: brandScoresToSave,
          targetBrand: this.data.brandName,
          executionId: executionId,
          timestamp: Date.now()
        });
      }

      // P1-1 修复：清理过期数据（定期执行）
      try {
        cleanupExpiredData();
      } catch (cleanupError) {
        console.warn('[Storage] 清理过期数据失败:', cleanupError);
      }

      console.log('✅ 数据已保存到本地存储');

      // P2 优化：立即跳转，不等待本地数据处理完成
      wx.navigateTo({
        url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(this.data.brandName)}`
      });

      // P2 优化：异步处理本地数据聚合（不阻塞跳转）
      // 使用 setTimeout 将计算任务放到下一个事件循环
      setTimeout(() => {
        try {
          // 【关键修复】直接使用 detailed_results 数组
          const rawResults = parsedStatus.detailed_results || parsedStatus.results || [];
          
          console.log('[异步数据处理] 原始结果数量:', rawResults.length);
          
          // 生成看板数据（直接传入数组）
          const dashboardData = generateDashboardData(rawResults, {
            brandName: this.data.brandName,
            competitorBrands: this.data.competitorBrands
          });

          // 处理报告数据（用于其他图表）
          const processedReportData = processReportData({
            results: rawResults,
            detailed_results: rawResults,
            semantic_drift_data: parsedStatus.semantic_drift_data,
            recommendation_data: parsedStatus.recommendation_data,
            competitive_analysis: parsedStatus.competitive_analysis
          });

          this.setData({
            reportData: processedReportData,
            isTesting: false,
            testCompleted: true,
            completedTime: this.getCompletedTimeText(),
            trendChartData: generateTrendChartData(processedReportData),
            predictionData: extractPredictionData(processedReportData),
            scoreData: extractScoreData(processedReportData),
            competitionData: extractCompetitionData(processedReportData),
            sourceListData: extractSourceListData(processedReportData),
            dashboardData: dashboardData
          });

          console.log('✅ 异步数据处理完成');
        } catch (error) {
          console.error('异步数据处理失败:', error);
        }
      }, 0);

    } catch (error) {
      console.error('处理诊断完成失败:', error);
      wx.showToast({ title: '处理结果失败', icon: 'none' });
    }
  },

  /**
   * 【防御性异常拦截器】统一处理所有核心请求的异常
   * 确保任何报错都能弹出友好提示而不是直接白屏
   * @param {Error} error - 错误对象
   * @param {string} context - 错误发生的上下文
   * @returns {string} 处理后的错误信息
   */
  handleException(error, context = '操作') {
    // 记录完整错误堆栈用于调试
    console.error(`[${context}] 异常捕获:`, error);
    console.error(`[${context}] 错误堆栈:`, error?.stack);

    // 提取错误信息
    let extractedError = '系统繁忙，请稍后重试';

    // 多层错误提取
    if (error) {
      extractedError = error?.data?.error || 
                       error?.data?.message || 
                       error?.errMsg || 
                       error?.message || 
                       error?.toString() || 
                       extractedError;
    }

    // 确保错误信息是字符串
    extractedError = String(extractedError);

    // 网络错误友好提示
    if (extractedError.includes('request:fail') || 
        extractedError.includes('network') || 
        extractedError.includes('timeout') ||
        extractedError.includes('ETIMEDOUT') ||
        extractedError.includes('ENOTFOUND')) {
      extractedError = '网络连接失败，请检查：\n1. 设备是否已连接互联网\n2. 后端服务是否已启动\n3. 防火墙设置是否允许访问';
    }

    // 403 权限错误
    if (extractedError.includes('403') || extractedError.includes('Unauthorized') || extractedError.includes('Token')) {
      extractedError = '权限验证失败，请：\n1. 检查是否已登录\n2. 确认 Token 是否有效\n3. 联系管理员获取权限';
    }

    // 404 路径错误
    if (extractedError.includes('404') || extractedError.includes('Not Found')) {
      extractedError = '服务接口不存在，请：\n1. 检查后端服务是否已启动\n2. 确认 API 路径配置是否正确\n3. 联系开发人员修复';
    }

    // AI 模型配置错误
    if (extractedError.includes('not registered or not configured') || 
        extractedError.includes('API key') ||
        extractedError.includes('API_KEY')) {
      extractedError = '所选 AI 模型未正确配置，请：\n1. 在 .env 文件中配置相应 API 密钥\n2. 重启后端服务加载新配置\n3. 确认 API 密钥格式正确且有效\n4. 或选择其他已配置的 AI 模型';
    }

    // 画布/渲染错误
    if (extractedError.includes('canvas') || 
        extractedError.includes('Canvas') ||
        extractedError.includes('getContext') ||
        extractedError.includes('requestAnimationFrame')) {
      extractedError = '页面渲染异常，请：\n1. 刷新页面重试\n2. 清除缓存后重试\n3. 如问题持续，请联系技术支持';
    }

    // 数据类型错误
    if (extractedError.includes('trim') || 
        extractedError.includes('TypeError') ||
        extractedError.includes('Cannot read')) {
      extractedError = '数据处理异常，请：\n1. 检查输入数据格式\n2. 清除本地缓存\n3. 刷新页面重试';
    }

    // 显示友好错误提示
    wx.showModal({
      title: `${context}失败`,
      content: extractedError,
      showCancel: false,
      confirmText: '我知道了'
    });

    // 返回处理后的错误信息
    return extractedError;
  },

  /**
   * 处理诊断错误
   * @param {Error} error - 错误对象
   */
  handleDiagnosisError(error) {
    // Step 1: 确保隐藏加载框
    wx.hideLoading();
    
    // 使用统一异常拦截器处理
    const friendlyError = this.handleException(error, '诊断启动');

    // 重置测试状态
    this.setData({ isTesting: false });
  },



  viewDetailedResults: function() {
    // 优先使用新的 reportData，如果不存在则使用旧的 latestTestResults
    const resultsToUse = this.data.reportData || this.data.latestTestResults;

    if (resultsToUse) {
      // 【关键修复】使用 Storage 传递大数据，避免 URL 编码 2KB 限制
      const executionId = wx.getStorageSync('latestExecutionId') || Date.now().toString();
      wx.setStorageSync('last_diagnostic_results', {
        results: resultsToUse,
        competitiveAnalysis: this.data.latestCompetitiveAnalysis || {},
        brandScores: this.data.latestBrandScores || {},
        targetBrand: this.data.brandName,
        executionId: executionId,
        timestamp: Date.now()
      });

      // 【优化】只传递 executionId 和 brandName
      wx.navigateTo({
        url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(this.data.brandName)}`
      });
    } else {
      wx.showToast({ title: '暂无诊断结果', icon: 'none' });
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


  viewConfigManager: function() {
    wx.navigateTo({ url: '/pages/config-manager/config-manager' });
  },

  viewPermissionManager: function() {
    wx.navigateTo({ url: '/pages/permission-manager/permission-manager' });
  },

  viewDataManager: function() {
    navigateToDataManager();
  },

  viewUserGuide: function() {
    navigateToUserGuide();
  },

  viewHistory: function() {
    navigateToHistory();
  },

  /**
   * 【新增】查看最新诊断结果（使用服务）
   */
  viewLatestDiagnosis: function() {
    try {
      const executionId = this.data.latestDiagnosisInfo.executionId;
      const brandName = this.data.latestDiagnosisInfo.brand;

      if (executionId) {
        const resultData = {
          executionId: executionId,
          brand_name: brandName
        };
        navigateToReportDetail(resultData);
      } else {
        wx.showToast({ title: '暂无诊断结果', icon: 'none' });
      }
    } catch (e) {
      console.error('查看最新诊断结果失败:', e);
      wx.showToast({ title: '操作失败，请重试', icon: 'none' });
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

        // 【P0 修复】保存 competitiveAnalysis（确保不为空）
        const competitiveAnalysis = reportData.competitiveAnalysis || 
                                    this.data.latestCompetitiveAnalysis || 
                                    { brandScores: {}, firstMentionByPlatform: {}, interceptionRisks: [] };
        wx.setStorageSync('latestCompetitiveAnalysis_' + executionId, competitiveAnalysis);
        wx.setStorageSync('latestCompetitiveAnalysis', competitiveAnalysis);
        console.log('✅ 竞品分析已保存:', competitiveAnalysis.brandScores ? '有 brandScores' : '无 brandScores');
        if (reportData.negativeSources) {
          wx.setStorageSync('latestNegativeSources_' + executionId, reportData.negativeSources);
          console.log('✅ 负面信源已保存');
        }

        // 【P0 修复】保存 brand_scores（最关键！）
        const brandScores = reportData.brand_scores || 
                           (reportData.competitiveAnalysis && reportData.competitiveAnalysis.brandScores) ||
                           {};
        if (brandScores && Object.keys(brandScores).length > 0) {
          wx.setStorageSync('latestBrandScores_' + executionId, brandScores);
          wx.setStorageSync('latestBrandScores', brandScores);
          console.log('✅ 品牌分数已保存:', Object.keys(brandScores));
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
        // 【P0 修复】直接跳转到结果页，而不是 dashboard 页
        // 确保保存了所有必要的数据
        const reportData = this.data.reportData || this.data.dashboardData;
        const executionId = reportData?.executionId || this.data.executionId || Date.now().toString();
        const brandName = this.data.brandName || reportData?.brand_name || '品牌';
        
        // 保存 detailed_results
        const detailedResults = reportData?.detailed_results || reportData?.results || this.data.latestTestResults || [];
        if (detailedResults && detailedResults.length > 0) {
          wx.setStorageSync('latestTestResults_' + executionId, detailedResults);
          wx.setStorageSync('latestTestResults', detailedResults);
          console.log('✅ 测试结果已保存到本地存储:', detailedResults.length, '条');
        }
        
        // 保存 competitiveAnalysis
        const competitiveAnalysis = reportData?.competitiveAnalysis || 
                                    this.data.latestCompetitiveAnalysis || 
                                    { brandScores: {}, firstMentionByPlatform: {}, interceptionRisks: [] };
        wx.setStorageSync('latestCompetitiveAnalysis_' + executionId, competitiveAnalysis);
        wx.setStorageSync('latestCompetitiveAnalysis', competitiveAnalysis);
        console.log('✅ 竞品分析已保存');
        
        // 保存 brandScores
        const brandScores = reportData?.brand_scores || 
                           (reportData?.competitiveAnalysis && reportData.competitiveAnalysis.brandScores) || 
                           {};
        if (brandScores && Object.keys(brandScores).length > 0) {
          wx.setStorageSync('latestBrandScores_' + executionId, brandScores);
          wx.setStorageSync('latestBrandScores', brandScores);
          console.log('✅ 品牌分数已保存:', Object.keys(brandScores));
        }
        
        // 保存品牌名称
        wx.setStorageSync('latestTargetBrand', brandName);
        console.log('✅ 品牌名称已保存:', brandName);
        
        wx.redirectTo({
          url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`,
          success: () => {
            console.log('✅ 诊断完成，已跳转到结果页');
          },
          fail: (err) => {
            console.error('跳转到结果页失败:', err);
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
