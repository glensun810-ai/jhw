/**
 * 统计分析 - 主页面
 * 功能：多维度数据分析入口
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v3.0 - API 集成版
 */

const pageStateService = require('../../services/pageStateService');
const navigationService = require('../../services/navigationService');
const analyticsApi = require('../../api/analytics');

Page({
  data: {
    // 分析维度 Tab
    analysisTabs: [
      { id: 'brand', name: '品牌对比', icon: '📊' },
      { id: 'trend', name: '趋势分析', icon: '📈' },
      { id: 'platform', name: 'AI 平台', icon: '🤖' },
      { id: 'question', name: '问题聚合', icon: '❓' }
    ],
    currentTab: 'brand',
    
    // 时间范围
    timeRange: 'all',
    timeRangeIndex: 0,
    timeRangeOptions: [
      { label: '全部时间', value: 'all' },
      { label: '近 7 天', value: 'last7days' },
      { label: '近 30 天', value: 'last30days' },
      { label: '近 90 天', value: 'last90days' }
    ],
    timeRangeLabel: '全部时间',
    
    // 品牌筛选
    selectedBrand: 'all',
    brandIndex: 0,
    brandOptions: [{ label: '全部品牌', value: 'all' }],
    selectedBrandLabel: '全部品牌',
    
    // 数据状态
    loading: false,
    hasData: false,
    diagnosisCount: 0,
    hasActiveFilters: false,
    useApi: false, // 是否使用 API 数据
    
    // 图表数据
    brandCompareData: [],
    trendData: [],
    platformData: [],
    questionData: [],
    
    // 加载状态
    brandLoaded: false,
    trendLoaded: false,
    platformLoaded: false,
    questionLoaded: false
  },

  onLoad: function(options) {
    console.log('📊 统计分析页面加载');
    
    // 检查是否有传入的 tabId
    if (options && options.tabId) {
      this.setData({ currentTab: options.tabId });
    }
    
    this.initPage();
  },

  onShow: function() {
    // 每次显示时检查数据
    this.checkDataStatus();
    // 加载品牌选项
    this.loadBrandOptions();
  },

  onPullDownRefresh: function() {
    this.refreshData().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 初始化页面
   */
  async initPage() {
    try {
      this.setData({ loading: true });
      
      // 检查是否有足够的诊断数据
      const hasEnoughData = await this.checkDiagnosisCount();
      
      if (!hasEnoughData) {
        this.setData({ 
          hasData: false,
          loading: false 
        });
        return;
      }
      
      // 加载默认分析数据
      await this.loadAnalysisData(this.data.currentTab);
      
      this.setData({ 
        hasData: true,
        loading: false 
      });
    } catch (error) {
      console.error('初始化失败:', error);
      this.setData({ loading: false });
    }
  },

  /**
   * 加载品牌选项
   */
  loadBrandOptions: function() {
    try {
      const history = wx.getStorageSync('diagnosis_history_list') || [];
      
      // 提取所有品牌
      const brandSet = new Set();
      history.forEach(record => {
        if (record.brandName) {
          brandSet.add(record.brandName);
        }
      });
      
      // 转换为选项
      const brandOptions = [
        { label: '全部品牌', value: 'all' },
        ...Array.from(brandSet).map(brand => ({ label: brand, value: brand }))
      ];
      
      this.setData({ brandOptions });
    } catch (error) {
      console.error('加载品牌选项失败:', error);
    }
  },

  /**
   * 检查诊断记录数量
   */
  async checkDiagnosisCount() {
    return new Promise((resolve) => {
      try {
        const history = wx.getStorageSync('diagnosis_history_list') || [];
        const count = history.length;
        
        this.setData({ diagnosisCount: count });
        resolve(count >= 1); // 至少 1 条记录
      } catch (error) {
        console.error('检查诊断数量失败:', error);
        resolve(false);
      }
    });
  },

  /**
   * Tab 切换
   */
  onTabChange: function(e) {
    const { tabId } = e.currentTarget.dataset;

    if (tabId === this.data.currentTab) return;

    console.log(`切换分析维度：${tabId}`);
    this.setData({ currentTab: tabId });
    this.loadAnalysisData(tabId);
  },

  /**
   * 品牌筛选
   */
  onBrandChange: function(e) {
    const index = e.detail.value;
    const brand = this.data.brandOptions[index];
    
    this.setData({
      brandIndex: index,
      selectedBrand: brand.value,
      selectedBrandLabel: brand.label
    });
    
    this.updateActiveFilters();
    this.refreshData();
  },

  /**
   * 时间范围筛选
   */
  onTimeRangeChange: function(e) {
    const index = e.detail.value;
    const timeRange = this.data.timeRangeOptions[index];
    
    this.setData({
      timeRangeIndex: index,
      timeRange: timeRange.value,
      timeRangeLabel: timeRange.label
    });
    
    this.updateActiveFilters();
    this.refreshData();
  },

  /**
   * 重置筛选
   */
  resetFilters: function() {
    this.setData({
      brandIndex: 0,
      selectedBrand: 'all',
      selectedBrandLabel: '全部品牌',
      timeRangeIndex: 0,
      timeRange: 'all',
      timeRangeLabel: '全部时间',
      hasActiveFilters: false
    });
    
    this.refreshData();
  },

  /**
   * 清除品牌筛选
   */
  clearBrandFilter: function() {
    this.setData({
      brandIndex: 0,
      selectedBrand: 'all',
      selectedBrandLabel: '全部品牌'
    });
    
    this.updateActiveFilters();
    this.refreshData();
  },

  /**
   * 清除时间筛选
   */
  clearTimeRangeFilter: function() {
    this.setData({
      timeRangeIndex: 0,
      timeRange: 'all',
      timeRangeLabel: '全部时间'
    });
    
    this.updateActiveFilters();
    this.refreshData();
  },

  /**
   * 更新激活的筛选条件
   */
  updateActiveFilters: function() {
    const hasActiveFilters = 
      this.data.selectedBrand !== 'all' || 
      this.data.timeRange !== 'all';
    
    this.setData({ hasActiveFilters });
  },

  /**
   * 加载分析数据
   */
  async loadAnalysisData(tabId) {
    switch (tabId) {
      case 'brand':
        await this.loadBrandCompare();
        break;
      case 'trend':
        await this.loadTrendAnalysis();
        break;
      case 'platform':
        await this.loadPlatformCompare();
        break;
      case 'question':
        await this.loadQuestionAnalysis();
        break;
    }
  },

  /**
   * 加载品牌对比数据
   */
  async loadBrandCompare() {
    if (this.data.brandLoaded && !this.hasNewFilters()) return;

    try {
      const history = this.getFilteredHistory();
      
      // 【性能优化】限制处理数据量，最多 100 条
      const limitedHistory = history.slice(0, 100);

      // 聚合品牌数据
      const brandMap = {};
      limitedHistory.forEach(record => {
        const brandName = record.brandName || '未知品牌';
        const score = record.overallScore || 0;

        if (!brandMap[brandName]) {
          brandMap[brandName] = {
            name: brandName,
            scores: [],
            count: 0
          };
        }

        brandMap[brandName].scores.push(score);
        brandMap[brandName].count += 1;
      });

      // 计算平均分
      const brandList = Object.values(brandMap).map(brand => ({
        name: brand.name,
        value: Math.round(brand.scores.reduce((sum, s) => sum + s, 0) / brand.scores.length)
      }));

      // 按分数排序
      brandList.sort((a, b) => b.value - a.value);

      this.setData({
        brandCompareData: brandList,
        brandLoaded: true
      });

      console.log('品牌对比数据加载完成:', brandList.length, '个品牌');
    } catch (error) {
      console.error('加载品牌对比失败:', error);
    }
  },

  /**
   * 获取筛选后的历史记录
   */
  getFilteredHistory: function() {
    let history = wx.getStorageSync('diagnosis_history_list') || [];
    
    // 品牌筛选
    if (this.data.selectedBrand !== 'all') {
      history = history.filter(record => record.brandName === this.data.selectedBrand);
    }
    
    // 时间范围筛选
    if (this.data.timeRange !== 'all') {
      const now = Date.now();
      let timeThreshold = 0;
      
      switch (this.data.timeRange) {
        case 'last7days':
          timeThreshold = now - 7 * 24 * 60 * 60 * 1000;
          break;
        case 'last30days':
          timeThreshold = now - 30 * 24 * 60 * 60 * 1000;
          break;
        case 'last90days':
          timeThreshold = now - 90 * 24 * 60 * 60 * 1000;
          break;
      }
      
      if (timeThreshold > 0) {
        history = history.filter(record => {
          const recordTime = new Date(record.createdAt || 0).getTime();
          return recordTime >= timeThreshold;
        });
      }
    }
    
    return history;
  },

  /**
   * 检查是否有新的筛选条件
   */
  hasNewFilters: function() {
    // 简化检查，实际应该比较筛选条件
    return false;
  },

  /**
   * 加载趋势分析数据
   */
  async loadTrendAnalysis() {
    if (this.data.trendLoaded && !this.hasNewFilters()) return;

    try {
      const history = this.getFilteredHistory();
      
      // 【性能优化】限制处理数据量，最多 100 条
      const limitedHistory = history.slice(0, 100);

      // 按时间排序，取最近 10 条
      const sortedHistory = limitedHistory.sort((a, b) => {
        const timeA = new Date(a.createdAt || 0).getTime();
        const timeB = new Date(b.createdAt || 0).getTime();
        return timeA - timeB;
      }).slice(-10);

      // 提取趋势数据
      const trendData = sortedHistory.map(record => {
        const date = new Date(record.createdAt || 0);
        const label = `${date.getMonth() + 1}/${date.getDate()}`;
        return {
          value: record.overallScore || 0,
          label: label
        };
      });

      this.setData({
        trendData: trendData,
        trendLoaded: true
      });

      console.log('趋势分析数据加载完成:', trendData.length, '条记录');
    } catch (error) {
      console.error('加载趋势分析失败:', error);
    }
  },

  /**
   * 加载 AI 平台对比数据
   */
  async loadPlatformCompare() {
    if (this.data.platformLoaded && !this.hasNewFilters()) return;

    try {
      const history = this.getFilteredHistory();
      
      // 【性能优化】限制处理数据量，最多 100 条
      const limitedHistory = history.slice(0, 100);

      // 聚合平台数据
      const platformMap = {};
      limitedHistory.forEach(record => {
        const platforms = record.aiModels || [];
        const score = record.overallScore || 0;
        
        platforms.forEach(model => {
          const modelName = model.name || model.model_name || '未知';
          
          if (!platformMap[modelName]) {
            platformMap[modelName] = {
              name: modelName,
              scores: [],
              count: 0
            };
          }
          
          platformMap[modelName].scores.push(score);
          platformMap[modelName].count += 1;
        });
      });

      // 计算平均分
      const platformList = Object.values(platformMap).map(platform => ({
        name: platform.name,
        value: Math.round(platform.scores.reduce((sum, s) => sum + s, 0) / platform.scores.length)
      }));

      // 按使用次数排序
      platformList.sort((a, b) => b.value - a.value);

      // 转换为雷达图格式（6 个维度）
      const radarData = platformList.slice(0, 6).map((platform, index) => ({
        name: platform.name,
        value: platform.value
      }));

      this.setData({
        platformData: radarData,
        platformLoaded: true
      });

      console.log('AI 平台对比数据加载完成:', radarData.length, '个平台');
    } catch (error) {
      console.error('加载 AI 平台对比失败:', error);
    }
  },

  /**
   * 加载问题聚合数据
   */
  async loadQuestionAnalysis() {
    if (this.data.questionLoaded && !this.hasNewFilters()) return;

    try {
      const history = this.getFilteredHistory();
      
      // 【性能优化】限制处理数据量，最多 100 条
      const limitedHistory = history.slice(0, 100);

      // 聚合问题数据
      const questionMap = {};
      limitedHistory.forEach(record => {
        const questions = record.questions || record.custom_questions || [];
        questions.forEach(q => {
          const questionText = typeof q === 'string' ? q : (q.text || q.question || '未知问题');
          
          if (!questionMap[questionText]) {
            questionMap[questionText] = {
              name: questionText,
              count: 0
            };
          }
          
          questionMap[questionText].count += 1;
        });
      });

      // 转换为数组并按频次排序
      const questionList = Object.values(questionMap)
        .sort((a, b) => b.count - a.count)
        .slice(0, 10);

      this.setData({
        questionData: questionList,
        questionLoaded: true
      });

      console.log('问题聚合数据加载完成:', questionList.length, '个问题');
    } catch (error) {
      console.error('加载问题聚合失败:', error);
    }
  },

  /**
   * 刷新数据
   */
  async refreshData() {
    // 重置加载状态
    this.setData({
      brandLoaded: false,
      trendLoaded: false,
      platformLoaded: false,
      questionLoaded: false
    });
    
    await this.loadAnalysisData(this.data.currentTab);
    
    wx.showToast({
      title: '刷新成功',
      icon: 'success'
    });
  },

  /**
   * 检查数据状态
   */
  checkDataStatus() {
    // 检查是否需要刷新
    if (!this.data.hasData) {
      this.initPage();
    }
  },

  /**
   * 跳转到诊断
   */
  goToDiagnosis: function() {
    navigationService.navigateToHome();
  },

  /**
   * 跳转到品牌维度分析
   */
  goToBrandDimension: function() {
    wx.navigateTo({
      url: './brand-dimension/brand-dimension'
    });
  },

  /**
   * 跳转到时间维度分析
   */
  goToTimeDimension: function() {
    wx.navigateTo({
      url: './time-dimension/time-dimension'
    });
  }
});
