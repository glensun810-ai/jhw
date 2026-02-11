// 平台名称映射表
const PLATFORM_NAME_MAP = {
  'DeepSeek': 'DeepSeek',
  'Kimi': 'Kimi',
  'TongyiQianwen': '通义千问'
};

Page({
  data: {
    targetBrand: '',
    competitiveAnalysis: null,
    pkDataByPlatform: {},
    platforms: [],
    platformDisplayNames: {}, // 存储显示名称
    currentSwiperIndex: 0,
    isPremium: false, // 模拟用户会员状态
  },

  onLoad: function(options) {
    // 在真实应用中，这里会从全局状态或用户信息中获取
    // const app = getApp();
    // this.setData({ isPremium: app.globalData.isPremium });

    // 优先从URL参数加载数据
    if (options.competitiveAnalysis && options.results && options.targetBrand) {
      try {
        const competitiveAnalysis = JSON.parse(decodeURIComponent(options.competitiveAnalysis));
        const results = JSON.parse(options.results);
        const targetBrand = options.targetBrand || '';

        const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(competitiveAnalysis, targetBrand);

        this.setData({
          targetBrand,
          competitiveAnalysis,
          latestTestResults: results, // 保存结果数据
          latestCompetitiveAnalysis: competitiveAnalysis, // 保存分析数据
          pkDataByPlatform,
          platforms,
          platformDisplayNames
        });

      } catch (e) {
        console.error('解析竞品分析数据失败', e);

        // 解析失败时尝试从本地存储加载
        this.loadFromCache();
      }
    } else {
      // 如果URL参数不完整，尝试从本地存储加载
      this.loadFromCache();
    }
  },

  // 从本地存储加载数据
  loadFromCache: function() {
    const cachedResults = wx.getStorageSync('latestTestResults');
    const cachedAnalysis = wx.getStorageSync('latestCompetitiveAnalysis');
    const cachedBrand = wx.getStorageSync('latestTargetBrand');

    if (cachedResults && cachedAnalysis && cachedBrand) {
      try {
        const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(cachedAnalysis, cachedBrand);

        this.setData({
          targetBrand: cachedBrand,
          competitiveAnalysis: cachedAnalysis,
          latestTestResults: cachedResults,
          latestCompetitiveAnalysis: cachedAnalysis,
          pkDataByPlatform,
          platforms,
          platformDisplayNames
        });

        wx.showToast({
          title: '已从缓存加载上次结果',
          icon: 'none'
        });
      } catch (e) {
        console.error('从缓存加载数据失败', e);
        wx.showToast({
          title: '无可用结果数据',
          icon: 'none'
        });
      }
    } else {
      wx.showToast({
        title: '无可用结果数据',
        icon: 'none'
      });
    }
  },

  generatePKDataByPlatform: function(competitiveAnalysis, targetBrand) {
    const pkDataByPlatform = {};
    const platforms = new Set();
    const platformDisplayNames = {};

    const allBrands = Object.keys(competitiveAnalysis.brandScores);
    const competitors = allBrands.filter(b => b !== targetBrand);

    const aiModels = ['DeepSeek', 'Kimi', 'TongyiQianwen'];
    aiModels.forEach(model => {
      platforms.add(model);
      platformDisplayNames[model] = PLATFORM_NAME_MAP[model] || model; // 使用映射表获取显示名称
      pkDataByPlatform[model] = [];
      competitors.forEach(comp => {
        const myBrandData = competitiveAnalysis.brandScores[targetBrand];
        const competitorData = competitiveAnalysis.brandScores[comp];

        const randomFactor = () => 1 + (Math.random() - 0.5) * 0.2;
        const adjustedMyData = { ...myBrandData, brand: targetBrand, overallScore: Math.round(myBrandData.overallScore * randomFactor()) };
        const adjustedCompData = { ...competitorData, brand: comp, overallScore: Math.round(competitorData.overallScore * randomFactor()) };

        pkDataByPlatform[model].push({
          myBrandData: adjustedMyData,
          competitorData: adjustedCompData
        });
      });
    });

    return {
      pkDataByPlatform,
      platforms: Array.from(platforms),
      platformDisplayNames
    };
  },

  onSwiperChange: function(e) {
    this.setData({
      currentSwiperIndex: e.detail.current
    });
  },

  goHome: function() {
    // 保存当前结果到本地存储，以便后续访问
    if (this.data.latestTestResults && this.data.latestCompetitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.latestCompetitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    wx.reLaunch({ url: '/pages/index/index' });
  },

  generateReport: function() {
    wx.showLoading({
      title: '正在生成战报...',
      mask: true
    });

    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({
        title: '战报已生成 (模拟)',
        icon: 'success'
      });
    }, 2000);
  },

  viewHistory: function() {
    // 保存当前结果到本地存储
    if (this.data.latestTestResults && this.data.latestCompetitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.latestCompetitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    wx.navigateTo({
      url: '/pages/history/history'
    });
  }
})