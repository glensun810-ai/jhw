/**
 * MVP 平台选择器页面 - 支持DeepSeek、通义千问、智谱AI
 */

const { 
  startDeepSeekMVPTest,
  startQwenMVPTest,
  startZhipuMVPTest,
  getPlatformOptions,
  getDefaultMVPQuestions,
  validateMVPInput
} = require('../../services/platformSpecificMVPService');

Page({
  data: {
    // 核心输入
    brandName: '',
    competitorBrand: '',
    questions: [],
    
    // 平台选择
    platformOptions: getPlatformOptions(),
    selectedPlatform: 'deepseek', // 默认选择DeepSeek
    
    // 测试状态
    isTesting: false,
    progress: 0,
    statusText: '准备中...',
    taskId: null
  },

  onLoad() {
    // 初始化默认问题
    this.resetQuestions();
  },

  /**
   * 重置为默认问题
   */
  resetQuestions() {
    const defaultQuestions = getDefaultMVPQuestions();
    this.setData({ questions: defaultQuestions });
  },

  // ==================== 输入处理 ====================

  onBrandInput(e) {
    this.setData({ brandName: e.detail.value });
  },

  onCompetitorInput(e) {
    this.setData({ competitorBrand: e.detail.value });
  },

  onQuestionChange(e) {
    const { index } = e.currentTarget.dataset;
    const { value } = e.detail;
    const questions = [...this.data.questions];
    questions[index] = value;
    this.setData({ questions });
  },

  // ==================== 平台选择 ====================

  onPlatformChange(e) {
    const selectedPlatform = e.detail.value;
    this.setData({ selectedPlatform });
  },

  // ==================== 核心功能 ====================

  /**
   * 启动MVP品牌测试（根据选择的平台）
   */
  async startTest() {
    const { brandName, competitorBrand, questions, selectedPlatform } = this.data;
    
    // 参数验证
    const validation = validateMVPInput({ brandName, questions });
    if (!validation.valid) {
      wx.showToast({ 
        title: validation.error, 
        icon: 'none',
        duration: 2000
      });
      return;
    }
    
    // 显示加载状态
    this.setData({ 
      isTesting: true, 
      progress: 0, 
      statusText: `正在使用${this.getPlatformLabel(selectedPlatform)}分析，请稍候...` 
    });

    try {
      let result;
      
      // 根据选择的平台调用相应的测试方法
      switch (selectedPlatform) {
        case 'deepseek':
          result = await startDeepSeekMVPTest({
            brandName,
            competitorBrand,
            questions
          });
          break;
          
        case 'qwen':
          result = await startQwenMVPTest({
            brandName,
            competitorBrand,
            questions
          });
          break;
          
        case 'zhipu':
          result = await startZhipuMVPTest({
            brandName,
            competitorBrand,
            questions
          });
          break;
          
        case 'doubao':
          // 使用原有的豆包测试方法
          const { startMVPBrandTest } = require('../../services/mvpService');
          result = await startMVPBrandTest({
            brandName,
            competitorBrand,
            questions
          });
          break;
          
        default:
          throw new Error('请选择有效的AI平台');
      }

      if (result.success && result.results) {
        // 直接拿到结果，跳转到结果页
        this.handleTestComplete(result.results, selectedPlatform);
      } else {
        throw new Error(result.error || '诊断失败');
      }
    } catch (error) {
      console.error('测试失败:', error);
      wx.showToast({ 
        title: error.message || '测试失败', 
        icon: 'none',
        duration: 3000
      });
      this.setData({ isTesting: false });
    }
  },

  /**
   * 获取平台标签
   */
  getPlatformLabel(platformValue) {
    const platformMap = {
      'doubao': '豆包',
      'deepseek': 'DeepSeek',
      'qwen': '通义千问',
      'zhipu': '智谱AI'
    };
    return platformMap[platformValue] || platformValue;
  },

  /**
   * 测试完成处理
   */
  handleTestComplete(results, platform) {
    const { brandName } = this.data;
    
    // 重置状态
    this.setData({ 
      isTesting: false,
      progress: 100,
      statusText: '诊断完成'
    });
    
    // 跳转到结果页
    wx.navigateTo({
      url: `/pages/mvp-results/mvp-results?results=${encodeURIComponent(JSON.stringify(results))}&brand=${encodeURIComponent(brandName)}&platform=${encodeURIComponent(this.getPlatformLabel(platform))}`
    });
  },

  /**
   * 返回标准首页
   */
  goToStandardIndex() {
    wx.switchTab({
      url: '/pages/index/index'
    });
  }
});