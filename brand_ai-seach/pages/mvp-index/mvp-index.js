/**
 * MVP 首页 - 简化版品牌诊断入口
 * 遵循 DEVELOPMENT_SOP.md 第四阶段规范
 * 不修改现有 pages/index/，创建独立页面
 */

const { 
  startMVPBrandTest, 
  getDefaultMVPQuestions
} = require('../../services/mvpService');

Page({
  data: {
    // 核心输入
    brandName: '',
    competitorBrand: '',
    questions: [],
    
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

  // ==================== 核心功能 ====================

  /**
   * 启动MVP品牌测试（同步执行版本）
   */
  async startTest() {
    const { brandName, competitorBrand, questions } = this.data;
    
    // 显示加载状态
    this.setData({ 
      isTesting: true, 
      progress: 0, 
      statusText: '正在分析，请稍候...' 
    });

    try {
      // 调用Service层启动测试（同步执行，等待完整结果）
      const result = await startMVPBrandTest({
        brandName,
        competitorBrand,
        questions
      });

      if (result.success && result.results) {
        // 直接拿到结果，跳转到结果页
        this.handleTestComplete(result.results);
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
   * 测试完成处理
   */
  handleTestComplete(results) {
    const { brandName } = this.data;
    
    // 重置状态
    this.setData({ 
      isTesting: false,
      progress: 100,
      statusText: '诊断完成'
    });
    
    // 跳转到结果页
    wx.navigateTo({
      url: `/pages/mvp-results/mvp-results?results=${encodeURIComponent(JSON.stringify(results))}&brand=${encodeURIComponent(brandName)}`
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
