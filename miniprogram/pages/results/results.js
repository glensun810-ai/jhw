Page({
  data: {
    targetBrand: '',
    competitiveAnalysis: null,
    latestTestResults: null,
    pkDataByPlatform: {},
    platforms: [],
    platformDisplayNames: {}, // 存储显示名称
    currentSwiperIndex: 0,
    currentPlatform: '', // 当前选中的平台
    isPremium: false, // 模拟用户会员状态
    advantageInsight: '权威度表现突出，可见度良好',
    riskInsight: '品牌纯净度有待提升',
    opportunityInsight: '一致性方面有较大提升空间',
    currentViewMode: 'brand', // 当前视图模式：brand, dimension, detailed
    groupedResultsByBrand: [], // 按品牌分组的结果
    dimensionComparisonData: [], // 维度对比数据
    expandedBrands: {}, // 展开的品牌详情

    // 保存结果相关数据
    showSaveResultModal: false,
    saveBrandName: '',
    saveTags: [],
    saveCategories: ['未分类', '日常监测', '竞品分析', '季度报告', '年度总结'],
    saveCategoryIndex: 0,
    selectedSaveCategory: '未分类',
    saveNotes: '',
    saveAsFavorite: false,
    newSaveTag: ''
  },

  onLoad: function(options) {
    console.log('Results page loaded with options:', options);

    // 优先从URL参数加载数据
    if (options.results && options.targetBrand) {
      try {
        // 解析results参数（它可能是一个JSON字符串）
        let results;
        if (typeof options.results === 'string') {
          try {
            results = JSON.parse(decodeURIComponent(options.results));
          } catch (parseErr) {
            console.error('Failed to parse results:', parseErr);
            // 如果解析失败，尝试直接使用字符串
            results = options.results;
          }
        } else {
          results = options.results;
        }

        const targetBrand = options.targetBrand || '';

        // 如果competitiveAnalysis参数存在，解析它
        let competitiveAnalysis;
        if (options.competitiveAnalysis) {
          try {
            competitiveAnalysis = JSON.parse(decodeURIComponent(options.competitiveAnalysis));
          } catch (parseErr) {
            console.error('Failed to parse competitiveAnalysis:', parseErr);
            // 如果解析失败，尝试从results中提取
            competitiveAnalysis = results.competitiveAnalysis || null;
          }
        } else {
          // 从results中提取competitiveAnalysis
          competitiveAnalysis = results.competitiveAnalysis || null;
        }

        // 如果competitiveAnalysis不存在，尝试从results中构建
        if (!competitiveAnalysis && results && typeof results === 'object') {
          if (results.competitiveAnalysis) {
            competitiveAnalysis = results.competitiveAnalysis;
          } else if (results.brandScores) {
            competitiveAnalysis = {
              brandScores: results.brandScores,
              firstMentionByPlatform: results.firstMentionByPlatform || {},
              interceptionRisks: results.interceptionRisks || {}
            };
          } else {
            // 尝试从results中提取brandScores信息
            competitiveAnalysis = {
              brandScores: results,
              firstMentionByPlatform: {},
              interceptionRisks: {}
            };
          }
        } else if (!competitiveAnalysis) {
          // 如果仍然没有competitiveAnalysis，创建一个默认结构
          competitiveAnalysis = {
            brandScores: {},
            firstMentionByPlatform: {},
            interceptionRisks: {}
          };
        }

        console.log('Parsed data:', { targetBrand, competitiveAnalysis, results });

        // 生成平台对比数据
        const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(competitiveAnalysis, targetBrand, results);

        // 确定最终的测试结果数据
        let finalTestResults = [];
        if (results && typeof results === 'object') {
          if (results.detailed_results) {
            finalTestResults = results.detailed_results;
          } else if (results.results) {
            finalTestResults = results.results;
          } else if (Array.isArray(results)) {
            finalTestResults = results;
          } else {
            // 如果results是其他对象，尝试从中提取相关信息
            finalTestResults = [];
          }
        }

        // 设置当前选中的平台（默认为第一个）
        const currentPlatform = platforms.length > 0 ? platforms[0] : '';

        // 生成洞察摘要
        const insights = this.generateInsights(competitiveAnalysis, targetBrand);

        // 处理详细结果数据
        const groupedResults = this.groupResultsByBrand(finalTestResults, targetBrand);
        const dimensionComparison = this.generateDimensionComparison(finalTestResults, targetBrand);

        // 处理信源情报数据
        const sourceIntelligenceMap = results.sourceIntelligenceMap || {};

        this.setData({
          targetBrand,
          competitiveAnalysis: competitiveAnalysis || {},
          latestTestResults: finalTestResults,
          pkDataByPlatform,
          platforms,
          platformDisplayNames,
          currentPlatform,
          advantageInsight: insights.advantage,
          riskInsight: insights.risk,
          opportunityInsight: insights.opportunity,
          groupedResultsByBrand: groupedResults,
          dimensionComparisonData: dimensionComparison,
          sourceIntelligenceMap: sourceIntelligenceMap,
          showSourceIntelligence: !!sourceIntelligenceMap.nodes && sourceIntelligenceMap.nodes.length > 0
        });

        console.log('Set page data:', this.data);

      } catch (e) {
        console.error('解析结果数据失败', e);
        console.error('错误堆栈:', e.stack);

        // 解析失败时尝试从本地存储加载
        this.loadFromCache();
      }
    } else {
      // 如果URL参数不完整，尝试从本地存储加载
      this.loadFromCache();
    }
  },

  // 生成洞察摘要
  generateInsights: function(competitiveAnalysis, targetBrand) {
    if (!competitiveAnalysis || !competitiveAnalysis.brandScores || !targetBrand) {
      return {
        advantage: '数据不足，无法生成洞察',
        risk: '数据不足，无法生成洞察',
        opportunity: '数据不足，无法生成洞察'
      };
    }

    const brandData = competitiveAnalysis.brandScores[targetBrand];
    if (!brandData) {
      return {
        advantage: '品牌数据缺失',
        risk: '品牌数据缺失',
        opportunity: '品牌数据缺失'
      };
    }

    // 分析各维度分数
    const authority = brandData.overallAuthority || 0;
    const visibility = brandData.overallVisibility || 0;
    const purity = brandData.overallPurity || 0;
    const consistency = brandData.overallConsistency || 0;

    // 生成优势洞察
    let advantage = '表现良好的领域：';
    if (authority >= 80) advantage += '权威度优秀，';
    if (visibility >= 80) advantage += '可见度优秀，';
    if (purity >= 80) advantage += '纯净度优秀，';
    if (consistency >= 80) advantage += '一致性优秀，';
    if (advantage === '表现良好的领域：') advantage = '暂无特别突出的优势';

    // 生成风险洞察
    let risk = '需要关注的领域：';
    if (authority < 60) risk += '权威度较低，';
    if (visibility < 60) risk += '可见度较低，';
    if (purity < 60) risk += '纯净度较低，';
    if (consistency < 60) risk += '一致性较低，';
    if (risk === '需要关注的领域：') risk = '暂无明显风险';

    // 生成机会洞察
    let opportunity = '可提升的领域：';
    if (authority < 80 && authority >= 60) opportunity += '权威度有提升空间，';
    if (visibility < 80 && visibility >= 60) opportunity += '可见度有提升空间，';
    if (purity < 80 && purity >= 60) opportunity += '纯净度有提升空间，';
    if (consistency < 80 && consistency >= 60) opportunity += '一致性有提升空间，';
    if (opportunity === '可提升的领域：') opportunity = '各维度均有提升空间';

    return {
      advantage: advantage.replace(/,$/, ''),
      risk: risk.replace(/,$/, ''),
      opportunity: opportunity.replace(/,$/, '')
    };
  },

  // 获取维度状态描述
  getDimensionStatus: function(score, dimension) {
    if (score >= 85) return '优秀';
    if (score >= 70) return '良好';
    if (score >= 50) return '一般';
    return '待优化';
  },

  // 切换平台
  switchPlatform: function(e) {
    const platform = e.currentTarget.dataset.platform;
    this.setData({
      currentPlatform: platform
    });
  },

  // 切换视图模式
  switchViewMode: function(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({
      currentViewMode: mode
    });
  },

  // 按品牌分组结果
  groupResultsByBrand: function(results, mainBrand) {
    if (!results || !Array.isArray(results)) {
      return [];
    }

    // 按品牌分组
    const grouped = {};
    results.forEach(item => {
      const brand = item.brand;
      if (!grouped[brand]) {
        grouped[brand] = {
          brand: brand,
          isMainBrand: brand === mainBrand,
          scores: {
            authority_score: 0,
            visibility_score: 0,
            purity_score: 0,
            consistency_score: 0
          },
          overallScore: 0,
          questions: []
        };
      }

      // 累加分数
      grouped[brand].scores.authority_score += item.authority_score || 0;
      grouped[brand].scores.visibility_score += item.visibility_score || 0;
      grouped[brand].scores.purity_score += item.purity_score || 0;
      grouped[brand].scores.consistency_score += item.consistency_score || 0;

      // 添加问题
      grouped[brand].questions.push({
        question: item.question,
        response: item.response
      });
    });

    // 计算平均分
    Object.keys(grouped).forEach(brand => {
      const brandData = grouped[brand];
      const count = brandData.questions.length;
      brandData.scores.authority_score = Math.round(brandData.scores.authority_score / count) || 0;
      brandData.scores.visibility_score = Math.round(brandData.scores.visibility_score / count) || 0;
      brandData.scores.purity_score = Math.round(brandData.scores.purity_score / count) || 0;
      brandData.scores.consistency_score = Math.round(brandData.scores.consistency_score / count) || 0;
      brandData.overallScore = Math.round((brandData.scores.authority_score +
                                         brandData.scores.visibility_score +
                                         brandData.scores.purity_score +
                                         brandData.scores.consistency_score) / 4) || 0;
    });

    // 转换为数组并按是否为主品牌排序
    return Object.values(grouped).sort((a, b) => {
      if (a.isMainBrand && !b.isMainBrand) return -1;
      if (!a.isMainBrand && b.isMainBrand) return 1;
      return b.overallScore - a.overallScore; // 按分数降序排列
    });
  },

  // 生成维度对比数据
  generateDimensionComparison: function(results, mainBrand) {
    if (!results || !Array.isArray(results)) {
      return [];
    }

    // 按维度和品牌分组
    const dimensions = ['authority_score', 'visibility_score', 'purity_score', 'consistency_score'];
    const dimensionIcons = {
      'authority_score': '🏆',
      'visibility_score': '👁️',
      'purity_score': '✨',
      'consistency_score': '🔗'
    };
    const dimensionNames = {
      'authority_score': '权威度',
      'visibility_score': '可见度',
      'purity_score': '纯净度',
      'consistency_score': '一致性'
    };

    const comparisonData = [];

    dimensions.forEach(dim => {
      const brandScores = {};
      results.forEach(item => {
        const brand = item.brand;
        if (!brandScores[brand]) {
          brandScores[brand] = {
            brand: brand,
            isMainBrand: brand === mainBrand,
            score: 0,
            count: 0
          };
        }
        brandScores[brand].score += item[dim] || 0;
        brandScores[brand].count++;
      });

      // 计算平均分
      Object.keys(brandScores).forEach(brand => {
        brandScores[brand].score = Math.round(brandScores[brand].score / brandScores[brand].count) || 0;
      });

      // 计算平均分
      const allScores = Object.values(brandScores).map(b => b.score);
      const averageScore = allScores.length > 0 ? Math.round(allScores.reduce((a, b) => a + b, 0) / allScores.length) : 0;

      // 转换为数组并排序
      const brands = Object.values(brandScores).sort((a, b) => b.score - a.score);

      comparisonData.push({
        name: dimensionNames[dim],
        icon: dimensionIcons[dim],
        dimension: dim,
        averageScore: averageScore,
        brands: brands
      });
    });

    return comparisonData;
  },

  // 切换品牌问题详情
  toggleBrandQuestions: function(e) {
    const brand = e.currentTarget.dataset.brand;
    const expandedBrands = this.data.expandedBrands;
    expandedBrands[brand] = !expandedBrands[brand];

    this.setData({
      expandedBrands: {...expandedBrands}
    });
  },

  // 从本地存储加载数据
  loadFromCache: function() {
    const cachedResults = wx.getStorageSync('latestTestResults');
    const cachedAnalysis = wx.getStorageSync('latestCompetitiveAnalysis');
    const cachedBrand = wx.getStorageSync('latestTargetBrand');

    if (cachedResults && cachedAnalysis && cachedBrand) {
      try {
        const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(cachedAnalysis, cachedBrand, cachedResults);

        // 设置当前选中的平台（默认为第一个）
        const currentPlatform = platforms.length > 0 ? platforms[0] : '';

        // 生成洞察摘要
        const insights = this.generateInsights(cachedAnalysis, cachedBrand);

        // 处理详细结果数据
        const groupedResults = this.groupResultsByBrand(cachedResults, cachedBrand);
        const dimensionComparison = this.generateDimensionComparison(cachedResults, cachedBrand);

        this.setData({
          targetBrand: cachedBrand,
          competitiveAnalysis: cachedAnalysis,
          latestTestResults: cachedResults,
          pkDataByPlatform,
          platforms,
          platformDisplayNames,
          currentPlatform,
          advantageInsight: insights.advantage,
          riskInsight: insights.risk,
          opportunityInsight: insights.opportunity,
          groupedResultsByBrand: groupedResults,
          dimensionComparisonData: dimensionComparison
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

  generatePKDataByPlatform: function(competitiveAnalysis, targetBrand, results) {
    const pkDataByPlatform = {};
    const platforms = new Set();
    const platformDisplayNames = {};

    if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
      console.warn('Invalid competitive analysis data');
      return { pkDataByPlatform: {}, platforms: [], platformDisplayNames: {} };
    }

    const allBrands = Object.keys(competitiveAnalysis.brandScores);
    const competitors = allBrands.filter(b => b !== targetBrand);

    // 从results中提取平台信息
    if (results && Array.isArray(results)) {
      results.forEach(item => {
        if (item.aiModel) {
          platforms.add(item.aiModel);
          platformDisplayNames[item.aiModel] = item.aiModel; // 默认显示名称就是模型名
        }
      });
    } else if (competitiveAnalysis.firstMentionByPlatform) {
      // 从firstMentionByPlatform中获取平台列表
      Object.keys(competitiveAnalysis.firstMentionByPlatform).forEach(platform => {
        platforms.add(platform);
        platformDisplayNames[platform] = platform;
      });
    }

    // 为每个平台生成品牌对比数据
    Array.from(platforms).forEach(platform => {
      pkDataByPlatform[platform] = [];

      // 为每个竞品生成对比数据
      competitors.forEach(comp => {
        const myBrandData = competitiveAnalysis.brandScores[targetBrand] || { overallScore: 0, overallGrade: 'D' };
        const competitorData = competitiveAnalysis.brandScores[comp] || { overallScore: 0, overallGrade: 'D' };

        // 添加品牌名称
        const myBrandDataWithBrand = { ...myBrandData, brand: targetBrand };
        const competitorDataWithBrand = { ...competitorData, brand: comp };

        pkDataByPlatform[platform].push({
          myBrandData: myBrandDataWithBrand,
          competitorData: competitorDataWithBrand
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
    if (this.data.latestTestResults && this.data.competitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.competitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    wx.reLaunch({ url: '/pages/index/index' });
  },

  generateReport: function() {
    wx.showLoading({
      title: '正在生成战报...',
      mask: true
    });

    // 这里可以实现实际的报告生成功能
    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({
        title: '战报生成成功',
        icon: 'success'
      });
    }, 2000);
  },

  viewHistory: function() {
    // 保存当前结果到本地存储
    if (this.data.latestTestResults && this.data.competitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.competitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    wx.navigateTo({
      url: '/pages/history/history'
    });
  },

  // 保存结果功能
  saveResult: function() {
    this.setData({
      showSaveResultModal: true,
      saveBrandName: this.data.targetBrand,
      saveTags: [],
      saveNotes: '',
      saveAsFavorite: false,
      newSaveTag: '',
      saveCategoryIndex: 0,
      selectedSaveCategory: '未分类'
    });
  },

  hideSaveResultModal: function() {
    this.setData({
      showSaveResultModal: false
    });
  },

  onSaveBrandNameInput: function(e) {
    this.setData({
      saveBrandName: e.detail.value
    });
  },

  onNewSaveTagInput: function(e) {
    this.setData({
      newSaveTag: e.detail.value
    });
  },

  addSaveTag: function() {
    if (this.data.newSaveTag.trim() && !this.data.saveTags.includes(this.data.newSaveTag.trim())) {
      const tags = [...this.data.saveTags, this.data.newSaveTag.trim()];
      this.setData({
        saveTags: tags,
        newSaveTag: ''
      });
    }
  },

  removeSaveTag: function(e) {
    const index = e.currentTarget.dataset.index;
    const tags = [...this.data.saveTags];
    tags.splice(index, 1);
    this.setData({
      saveTags: tags
    });
  },

  onSaveCategoryChange: function(e) {
    const index = e.detail.value;
    const categories = ['未分类', '日常监测', '竞品分析', '季度报告', '年度总结'];
    const category = categories[index];
    this.setData({
      saveCategoryIndex: index,
      selectedSaveCategory: category
    });
  },

  onSaveNotesInput: function(e) {
    this.setData({
      saveNotes: e.detail.value
    });
  },

  onSaveFavoriteChange: function(e) {
    this.setData({
      saveAsFavorite: e.detail.value
    });
  },

  confirmSaveResult: function() {
    if (!this.data.saveBrandName.trim()) {
      wx.showToast({
        title: '请输入品牌名称',
        icon: 'none'
      });
      return;
    }

    try {
      // 准备保存的数据
      const saveData = {
        id: Date.now().toString(), // 使用时间戳作为唯一ID
        timestamp: Date.now(),
        brandName: this.data.saveBrandName.trim(),
        results: {
          ...this.data.competitiveAnalysis,
          overallScore: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallScore || 0,
          overallAuthority: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallAuthority || 0,
          overallVisibility: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallVisibility || 0,
          overallPurity: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallPurity || 0,
          overallConsistency: this.data.competitiveAnalysis.brandScores[this.data.targetBrand]?.overallConsistency || 0
        },
        tags: this.data.saveTags,
        category: this.data.selectedSaveCategory,
        notes: this.data.saveNotes,
        isFavorite: this.data.saveAsFavorite
      };

      // 读取现有保存的数据
      let savedResults = wx.getStorageSync('savedSearchResults') || [];

      // 添加新数据
      savedResults.unshift(saveData);

      // 保存到本地存储
      wx.setStorageSync('savedSearchResults', savedResults);

      // 关闭模态框
      this.setData({
        showSaveResultModal: false
      });

      wx.showToast({
        title: '保存成功',
        icon: 'success'
      });
    } catch (e) {
      console.error('保存搜索结果失败', e);
      wx.showToast({
        title: '保存失败',
        icon: 'none'
      });
    }
  },

  // 查看信源详情
  viewSourceDetails: function(e) {
    const sourceId = e.currentTarget.dataset.id;
    const source = this.data.sourceIntelligenceMap.nodes.find(node => node.id === sourceId);

    if (source) {
      wx.showModal({
        title: source.name,
        content: `类型: ${source.category}\n权重: ${source.value || 'N/A'}\n情感: ${source.sentiment || 'N/A'}`,
        showCancel: false,
        confirmText: '确定'
      });
    }
  }
})