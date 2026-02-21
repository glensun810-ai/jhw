const { saveResult } = require('../../utils/saved-results-sync');
const { generateFullReport } = require('../../utils/pdf-export');

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

    // P0-3 竞争分析相关数据
    brandRankingList: [], // 品牌排名列表
    firstMentionByPlatform: [], // 首次提及率
    interceptionRisks: [], // 拦截风险
    competitorComparisonData: [], // 竞品对比详情

    // P1-1 语义偏移相关数据
    semanticDriftData: null, // 语义偏移分析结果
    semanticContrastData: null, // 语义对比数据（官方关键词 vs AI 关键词）

    // P1-2 信源纯净度相关数据
    sourcePurityData: null, // 信源纯净度分析结果
    sourceIntelligenceMap: null, // 信源情报图谱

    // P1-3 优化建议相关数据
    recommendationData: null, // 优化建议数据

    // P2-2 雷达图相关数据
    radarChartData: [],      // 雷达图数据
    canvasWidth: 300,        // Canvas 宽度
    canvasHeight: 300,       // Canvas 高度
    radarChartRendered: false, // 是否已渲染

    // P2-3 关键词云相关数据
    keywordCloudData: [],      // 词云数据
    topKeywords: [],           // 高频词列表
    keywordStats: {            // 关键词统计
      positiveCount: 0,
      neutralCount: 0,
      negativeCount: 0
    },
    wordCloudCanvasWidth: 350, // Canvas 宽度
    wordCloudCanvasHeight: 350, // Canvas 高度
    wordCloudRendered: false,   // 是否已渲染

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

  /**
   * P0-1 修复：支持从 executionId 加载本地存储的数据
   */
  onLoad: function(options) {
    console.log('Results page loaded with options:', options);

    // P0-1 修复：支持从 executionId 加载本地存储的数据
    if (options.executionId) {
      const executionId = decodeURIComponent(options.executionId);
      const brandName = decodeURIComponent(options.brandName || '');
      
      console.log('📥 从 executionId 加载数据:', executionId, brandName);
      
      // 从本地存储获取数据
      const cachedResults = wx.getStorageSync('latestTestResults_' + executionId);
      const cachedBrand = wx.getStorageSync('latestTargetBrand');
      const cachedCompetitors = wx.getStorageSync('latestCompetitorBrands');
      
      if (cachedResults && Array.isArray(cachedResults) && cachedResults.length > 0) {
        console.log('✅ 从本地存储加载成功，结果数量:', cachedResults.length);
        
        // 使用加载的数据初始化页面
        this.initializePageWithData(cachedResults, cachedBrand || brandName, cachedCompetitors || []);
      } else {
        console.warn('⚠️ 本地存储无数据，尝试从 URL 参数加载');
        this.loadFromUrlParams(options);
      }
    } else if (options.results && options.targetBrand) {
      // 原有的 URL 参数加载逻辑
      this.loadFromUrlParams(options);
    } else {
      // 如果 URL 参数不完整，尝试从本地存储加载
      this.loadFromCache();
    }
  },

  /**
   * 从 URL 参数加载数据
   */
  loadFromUrlParams: function(options) {
    try {
      // 解析 results 参数（它可能是一个 JSON 字符串）
      let results;
      if (typeof options.results === 'string') {
        try {
          results = JSON.parse(decodeURIComponent(options.results));
        } catch (parseErr) {
          console.error('Failed to parse results:', parseErr);
          results = options.results;
        }
      } else {
        results = options.results;
      }

      const targetBrand = options.targetBrand || '';

      // 如果 competitiveAnalysis 参数存在，解析它
      let competitiveAnalysis;
      if (options.competitiveAnalysis) {
        try {
          competitiveAnalysis = JSON.parse(decodeURIComponent(options.competitiveAnalysis));
        } catch (parseErr) {
          competitiveAnalysis = results.competitiveAnalysis || null;
        }
      } else {
        competitiveAnalysis = results.competitiveAnalysis || null;
      }

      // 如果 competitiveAnalysis 不存在，尝试从 results 中构建
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
          competitiveAnalysis = {
            brandScores: results,
            firstMentionByPlatform: {},
            interceptionRisks: {}
          };
        }
      } else if (!competitiveAnalysis) {
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
        }
      }

      const currentPlatform = platforms.length > 0 ? platforms[0] : '';
      const insights = this.generateInsights(competitiveAnalysis, targetBrand);
      const groupedResults = this.groupResultsByBrand(finalTestResults, targetBrand);
      const dimensionComparison = this.generateDimensionComparison(finalTestResults, targetBrand);
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
      this.loadFromCache();
    }
  },

  /**
   * P0-1 修复：使用加载的数据初始化页面
   */
  initializePageWithData: function(results, targetBrand, competitorBrands) {
    try {
      console.log('📊 初始化页面数据，结果数量:', results.length);

      // 构建 competitiveAnalysis 数据结构
      const competitiveAnalysis = this.buildCompetitiveAnalysis(results, targetBrand, competitorBrands);

      // 生成平台对比数据
      const { pkDataByPlatform, platforms, platformDisplayNames } = this.generatePKDataByPlatform(competitiveAnalysis, targetBrand, results);

      const currentPlatform = platforms.length > 0 ? platforms[0] : '';
      const insights = this.generateInsights(competitiveAnalysis, targetBrand);
      const groupedResults = this.groupResultsByBrand(results, targetBrand);
      const dimensionComparison = this.generateDimensionComparison(results, targetBrand);
      
      // P0-3 修复：处理竞争分析数据
      const competitiveAnalysisData = this.processCompetitiveAnalysisData(competitiveAnalysis, results, targetBrand, competitorBrands);
      
      // P1-1 修复：处理语义偏移数据
      const semanticDriftAnalysisData = this.processSemanticDriftData(competitiveAnalysis, results, targetBrand);
      
      // P1-2 修复：处理信源纯净度数据
      const sourcePurityAnalysisData = this.processSourcePurityData(competitiveAnalysis, results);
      
      // P1-3 修复：处理优化建议数据
      const recommendationAnalysisData = this.processRecommendationData(competitiveAnalysis, results);
      
      // P2-2 修复：准备雷达图数据
      const radarData = this.prepareRadarChartData(competitiveAnalysis, targetBrand, competitorBrands);
      
      // P2-3 修复：准备关键词云数据
      const keywordCloudResult = this.prepareKeywordCloudData(semanticDriftAnalysisData.semanticDriftData, results, targetBrand);

      this.setData({
        targetBrand: targetBrand,
        competitiveAnalysis: competitiveAnalysis,
        latestTestResults: results,
        pkDataByPlatform,
        platforms,
        platformDisplayNames,
        currentPlatform,
        advantageInsight: insights.advantage,
        riskInsight: insights.risk,
        opportunityInsight: insights.opportunity,
        groupedResultsByBrand: groupedResults,
        dimensionComparisonData: dimensionComparison,
        // P0-3 修复：设置竞争分析数据
        ...competitiveAnalysisData,
        // P1-1 修复：设置语义偏移数据
        ...semanticDriftAnalysisData,
        // P1-2 修复：设置信源纯净度数据
        ...sourcePurityAnalysisData,
        // P1-3 修复：设置优化建议数据
        ...recommendationAnalysisData,
        // P2-2 修复：设置雷达图数据
        radarChartData: radarData,
        // P2-3 修复：设置关键词云数据
        keywordCloudData: keywordCloudResult.keywordCloudData,
        topKeywords: keywordCloudResult.topKeywords,
        keywordStats: keywordCloudResult.keywordStats
      }, () => {
        // 数据设置完成后渲染雷达图
        if (radarData.length > 0) {
          setTimeout(() => {
            this.renderRadarChart();
          }, 100);
        }
        
        // 渲染词云
        if (keywordCloudResult.keywordCloudData.length > 0) {
          setTimeout(() => {
            this.renderWordCloud();
          }, 200);
        }
      });

      console.log('✅ 页面数据初始化完成');

      wx.showToast({
        title: '数据加载成功',
        icon: 'success'
      });

    } catch (e) {
      console.error('初始化页面数据失败', e);
      wx.showToast({
        title: '数据加载失败',
        icon: 'none'
      });
    }
  },

  /**
   * P0-1 修复：构建竞争分析数据结构
   */
  buildCompetitiveAnalysis: function(results, targetBrand, competitorBrands) {
    const brandScores = {};
    const firstMentionByPlatform = {};

    // 按品牌分组计算分数
    const brandResults = {};
    results.forEach(result => {
      // 兼容不同数据格式
      const brand = result.brand || result.main_brand || targetBrand;
      if (!brandResults[brand]) {
        brandResults[brand] = [];
      }
      brandResults[brand].push(result);
    });

    // 计算每个品牌的分数
    Object.keys(brandResults).forEach(brand => {
      const scores = brandResults[brand];
      
      // 从 geo_data 中提取分数（兼容后端数据格式）
      let totalScore = 0;
      let totalAuthority = 0;
      let totalVisibility = 0;
      let totalPurity = 0;
      let totalConsistency = 0;
      let count = 0;
      
      scores.forEach(s => {
        // 尝试多种字段名
        let score = s.score;
        let authority = s.authority_score;
        let visibility = s.visibility_score;
        let purity = s.purity_score;
        let consistency = s.consistency_score;
        
        // 如果没有直接字段，从 geo_data 中提取
        if (s.geo_data) {
          const geo = s.geo_data;
          if (score === undefined || score === null) {
            // 从 rank 和 sentiment 计算分数
            const rank = geo.rank || -1;
            const sentiment = geo.sentiment || 0;
            // 排名 1-3 得 90-100 分，4-6 得 70-89 分，7-10 得 50-69 分，未入榜得 30 分
            if (rank > 0) {
              if (rank <= 3) score = 90 + (3 - rank) * 3 + sentiment * 10;
              else if (rank <= 6) score = 70 + (6 - rank) * 3 + sentiment * 10;
              else score = 50 + (10 - rank) * 2 + sentiment * 10;
            } else {
              score = 30 + sentiment * 10;
            }
            score = Math.min(100, Math.max(0, score));
          }
          if (authority === undefined || authority === null) {
            // 从 sentiment 推断权威度
            authority = 50 + sentiment * 25;
          }
          if (visibility === undefined || visibility === null) {
            // 从 rank 推断可见度
            const rank = geo.rank || -1;
            if (rank <= 3) visibility = 90 + sentiment * 10;
            else if (rank <= 6) visibility = 70 + sentiment * 10;
            else if (rank > 0) visibility = 50 + sentiment * 10;
            else visibility = 30 + sentiment * 10;
          }
          if (purity === undefined || purity === null) {
            purity = 70 + sentiment * 15;
          }
          if (consistency === undefined || consistency === null) {
            consistency = 75 + sentiment * 10;
          }
        }
        
        // 如果还是 undefined，使用默认值
        if (score === undefined || score === null) score = 50;
        if (authority === undefined || authority === null) authority = 50;
        if (visibility === undefined || visibility === null) visibility = 50;
        if (purity === undefined || purity === null) purity = 50;
        if (consistency === undefined || consistency === null) consistency = 50;
        
        totalScore += score;
        totalAuthority += authority;
        totalVisibility += visibility;
        totalPurity += purity;
        totalConsistency += consistency;
        count++;
      });
      
      if (count > 0) {
        const avgScore = totalScore / count;
        const avgAuthority = totalAuthority / count;
        const avgVisibility = totalVisibility / count;
        const avgPurity = totalPurity / count;
        const avgConsistency = totalConsistency / count;
        
        // 计算等级
        let grade = 'D';
        if (avgScore >= 90) grade = 'A+';
        else if (avgScore >= 80) grade = 'A';
        else if (avgScore >= 70) grade = 'B';
        else if (avgScore >= 60) grade = 'C';
        
        brandScores[brand] = {
          overallScore: Math.round(avgScore),
          overallGrade: grade,
          overallAuthority: Math.round(avgAuthority),
          overallVisibility: Math.round(avgVisibility),
          overallPurity: Math.round(avgPurity),
          overallConsistency: Math.round(avgConsistency),
          overallSummary: this.getScoreSummary(avgScore)
        };
      }
    });

    return {
      brandScores,
      firstMentionByPlatform,
      interceptionRisks: {}
    };
  },

  /**
   * P0-3 修复：处理竞争分析数据
   */
  processCompetitiveAnalysisData: function(competitiveAnalysis, results, targetBrand, competitorBrands) {
    try {
      // 1. 品牌排名列表（按综合得分排序）
      const brandRankingList = Object.keys(competitiveAnalysis.brandScores || {})
        .sort((a, b) => {
          const scoreA = (competitiveAnalysis.brandScores[a] || {}).overallScore || 0;
          const scoreB = (competitiveAnalysis.brandScores[b] || {}).overallScore || 0;
          return scoreB - scoreA;
        });

      // 2. 首次提及率（从 competitiveAnalysis 中提取）
      const firstMentionByPlatform = [];
      const firstMentionData = competitiveAnalysis.firstMentionByPlatform || {};
      Object.keys(firstMentionData).forEach(platform => {
        const rate = firstMentionData[platform] || 0;
        firstMentionByPlatform.push({
          platform: this.getPlatformDisplayName(platform),
          rate: Math.round(rate * 100)
        });
      });

      // 3. 拦截风险（从 competitiveAnalysis 中提取）
      const interceptionRisks = [];
      const interceptionRiskData = competitiveAnalysis.interceptionRisks || {};
      Object.keys(interceptionRiskData).forEach(type => {
        const risk = interceptionRiskData[type];
        interceptionRisks.push({
          type: this.getRiskTypeName(type),
          level: risk.level || 'medium',
          description: risk.description || '暂无描述'
        });
      });

      // 4. 竞品对比详情（从结果中提取）
      const competitorComparisonData = [];
      const allBrands = [...competitorBrands];
      allBrands.forEach(competitor => {
        // 查找该竞品的对比数据
        const competitorResults = results.filter(r => r.brand === competitor);
        const targetResults = results.filter(r => r.brand === targetBrand);
        
        if (competitorResults.length > 0 && targetResults.length > 0) {
          // 计算差异化评分（基于维度分数差异）
          const competitorAvgScore = competitorResults.reduce((sum, r) => sum + (r.score || 0), 0) / competitorResults.length;
          const targetAvgScore = targetResults.reduce((sum, r) => sum + (r.score || 0), 0) / targetResults.length;
          const differentiationScore = Math.round(100 - Math.abs(competitorAvgScore - targetAvgScore));

          // 提取共同关键词（从响应中提取高频词）
          const commonKeywords = this.extractCommonKeywords(targetResults, competitorResults);
          
          // 提取独特关键词
          const uniqueToBrand = this.extractUniqueKeywords(targetResults, competitorResults);
          const uniqueToCompetitor = this.extractUniqueKeywords(competitorResults, targetResults);

          competitorComparisonData.push({
            competitor: competitor,
            differentiationScore: differentiationScore,
            commonKeywords: commonKeywords.slice(0, 5), // 限制显示数量
            uniqueToBrand: uniqueToBrand.slice(0, 5),
            uniqueToCompetitor: uniqueToCompetitor.slice(0, 5),
            differentiationGap: this.generateDifferentiationGap(targetBrand, competitor, differentiationScore)
          });
        }
      });

      return {
        brandRankingList,
        firstMentionByPlatform,
        interceptionRisks,
        competitorComparisonData
      };
    } catch (e) {
      console.error('处理竞争分析数据失败:', e);
      return {
        brandRankingList: [],
        firstMentionByPlatform: [],
        interceptionRisks: [],
        competitorComparisonData: []
      };
    }
  },

  /**
   * 获取平台显示名称
   */
  getPlatformDisplayName: function(platform) {
    const platformNames = {
      'deepseek': 'DeepSeek',
      'qwen': '通义千问',
      'zhipu': '智谱 AI',
      'doubao': '豆包'
    };
    return platformNames[platform] || platform;
  },

  /**
   * 获取风险类型名称
   */
  getRiskTypeName: function(type) {
    const riskTypes = {
      'visibility': '可见度拦截',
      'sentiment': '情感风险',
      'accuracy': '准确性风险',
      'purity': '纯净度风险'
    };
    return riskTypes[type] || type;
  },

  /**
   * 提取共同关键词
   */
  extractCommonKeywords: function(results1, results2) {
    const keywords1 = this.extractKeywordsFromResults(results1);
    const keywords2 = this.extractKeywordsFromResults(results2);
    return keywords1.filter(k => keywords2.includes(k));
  },

  /**
   * 提取独特关键词
   */
  extractUniqueKeywords: function(results1, results2) {
    const keywords1 = this.extractKeywordsFromResults(results1);
    const keywords2 = this.extractKeywordsFromResults(results2);
    return keywords1.filter(k => !keywords2.includes(k));
  },

  /**
   * 从结果中提取关键词
   */
  extractKeywordsFromResults: function(results) {
    const text = results.map(r => r.response || '').join(' ');
    // 简单的中文分词（实际应用中应该使用更好的分词库）
    const words = text.split(/[\s,，.。！？!？]+/);
    // 过滤停用词和短词
    const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等', '等', '一个', '这个', '这些'];
    return words
      .filter(w => w.length > 1 && !stopWords.includes(w))
      .slice(0, 20); // 限制数量
  },

  /**
   * 生成差异化建议
   */
  generateDifferentiationGap: function(brand1, brand2, score) {
    if (score >= 80) {
      return `${brand1}与${brand2}差异化明显，保持当前优势`;
    } else if (score >= 60) {
      return `${brand1}与${brand2}有一定差异化，建议强化独特卖点`;
    } else {
      return `${brand1}与${brand2}差异化不足，急需建立独特品牌形象`;
    }
  },

  /**
   * P1-1 修复：处理语义偏移数据
   */
  processSemanticDriftData: function(competitiveAnalysis, results, targetBrand) {
    try {
      // 从 backend 获取语义对比数据
      const semanticContrastData = competitiveAnalysis.semanticContrastData || null;
      
      // 计算语义偏移分数
      let driftScore = 0;
      let driftSeverity = 'low';
      let driftSeverityText = '偏移轻微';
      let similarityScore = 0;
      
      // 如果有语义对比数据，计算偏移分数
      if (semanticContrastData) {
        const officialWords = semanticContrastData.official_words || [];
        const aiWords = semanticContrastData.ai_generated_words || [];
        
        // 计算偏移分数（基于 AI 生成词中的风险词比例）
        const riskyWords = aiWords.filter(w => w.category === 'AI_Generated_Risky');
        const totalWords = officialWords.length + aiWords.length;
        
        if (totalWords > 0) {
          driftScore = Math.round((riskyWords.length / totalWords) * 100);
        }
        
        // 计算相似度分数
        const commonKeywords = this.extractCommonKeywordsFromWords(officialWords, aiWords);
        const allKeywords = [...new Set([...officialWords.map(w => w.name), ...aiWords.map(w => w.name)])];
        
        if (allKeywords.length > 0) {
          similarityScore = Math.round((commonKeywords.length / allKeywords.length) * 100);
        }
        
        // 判断偏移严重程度
        if (driftScore >= 60) {
          driftSeverity = 'high';
          driftSeverityText = '严重偏移';
        } else if (driftScore >= 30) {
          driftSeverity = 'medium';
          driftSeverityText = '中度偏移';
        } else {
          driftSeverity = 'low';
          driftSeverityText = '偏移轻微';
        }
      }
      
      // 提取缺失和意外的关键词
      let missingKeywords = [];
      let unexpectedKeywords = [];
      let negativeTerms = [];
      let positiveTerms = [];
      
      if (semanticContrastData) {
        const officialWords = semanticContrastData.official_words || [];
        const aiWords = semanticContrastData.ai_generated_words || [];
        
        // 官方有但 AI 没有的词
        const officialNames = officialWords.map(w => w.name);
        const aiNames = aiWords.map(w => w.name);
        
        missingKeywords = officialNames.filter(name => !aiNames.includes(name));
        unexpectedKeywords = aiNames.filter(name => !officialNames.includes(name));
        
        // 提取负面和正面术语
        negativeTerms = aiWords
          .filter(w => w.sentiment_valence < 0 || w.category === 'AI_Generated_Risky')
          .map(w => w.name);
        
        positiveTerms = aiWords
          .filter(w => w.sentiment_valence > 0 && w.category !== 'AI_Generated_Risky')
          .map(w => w.name);
      }
      
      // 如果没有语义对比数据，尝试从结果中提取
      if (!semanticContrastData) {
        const targetResults = results.filter(r => r.brand === targetBrand);
        const allResponses = targetResults.map(r => r.response || '').join(' ');
        
        // 简单的关键词提取
        const words = allResponses.split(/[\s,，.。！？!？]+/);
        const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等'];
        const filteredWords = words
          .filter(w => w.length > 1 && !stopWords.includes(w))
          .slice(0, 20);
        
        unexpectedKeywords = filteredWords.slice(0, 10);
        positiveTerms = filteredWords.slice(10, 15);
        negativeTerms = [];
        
        driftScore = 20; // 默认低偏移
        similarityScore = 80;
        driftSeverity = 'low';
        driftSeverityText = '偏移轻微';
      }
      
      return {
        semanticDriftData: {
          driftScore: driftScore,
          driftSeverity: driftSeverity,
          driftSeverityText: driftSeverityText,
          similarityScore: similarityScore,
          missingKeywords: missingKeywords,
          unexpectedKeywords: unexpectedKeywords,
          negativeTerms: negativeTerms,
          positiveTerms: positiveTerms
        },
        semanticContrastData: semanticContrastData
      };
    } catch (e) {
      console.error('处理语义偏移数据失败:', e);
      return {
        semanticDriftData: null,
        semanticContrastData: null
      };
    }
  },

  /**
   * 从词对象数组中提取共同关键词
   */
  extractCommonKeywordsFromWords: function(words1, words2) {
    const names1 = words1.map(w => w.name);
    const names2 = words2.map(w => w.name);
    return names1.filter(name => names2.includes(name));
  },

  /**
   * P2-3 修复：准备关键词云数据
   */
  prepareKeywordCloudData: function(semanticDriftData, results, targetBrand) {
    try {
      let allKeywords = [];
      
      // 从语义偏移数据中提取关键词
      if (semanticDriftData) {
        // 添加正面术语
        if (semanticDriftData.positiveTerms) {
          semanticDriftData.positiveTerms.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'positive' });
          });
        }
        
        // 添加负面术语
        if (semanticDriftData.negativeTerms) {
          semanticDriftData.negativeTerms.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'negative' });
          });
        }
        
        // 添加意外关键词（中性）
        if (semanticDriftData.unexpectedKeywords) {
          semanticDriftData.unexpectedKeywords.forEach(word => {
            allKeywords.push({ word: word, sentiment: 'neutral' });
          });
        }
      }
      
      // 从 AI 响应中提取更多关键词
      const targetResults = results.filter(r => r.brand === targetBrand);
      const allResponses = targetResults.map(r => r.response || '').join(' ');
      
      // 简单分词和统计
      const words = allResponses.split(/[\s,.。！？!？]+/);
      const stopWords = ['的', '了', '是', '在', '和', '与', '及', '等', '一个', '这个', '这些'];
      
      const wordCount = {};
      words.forEach(word => {
        if (word.length > 1 && !stopWords.includes(word)) {
          wordCount[word] = (wordCount[word] || 0) + 1;
        }
      });
      
      // 合并词频数据
      const keywordMap = {};
      allKeywords.forEach(item => {
        keywordMap[item.word] = {
          word: item.word,
          count: wordCount[item.word] || 1,
          sentiment: item.sentiment
        };
      });
      
      // 转换为数组并排序
      const keywordData = Object.values(keywordMap)
        .sort((a, b) => b.count - a.count)
        .slice(0, 50);  // 限制最多 50 个词
      
      // 计算权重（用于字体大小）
      const maxCount = keywordData.length > 0 ? keywordData[0].count : 1;
      keywordData.forEach(item => {
        item.weight = item.count / maxCount;
      });
      
      // 统计情感分布
      const stats = {
        positiveCount: keywordData.filter(k => k.sentiment === 'positive').length,
        neutralCount: keywordData.filter(k => k.sentiment === 'neutral').length,
        negativeCount: keywordData.filter(k => k.sentiment === 'negative').length
      };
      
      // 高频词（Top 10）
      const topKeywords = keywordData.slice(0, 10);
      
      return {
        keywordCloudData: keywordData,
        topKeywords: topKeywords,
        keywordStats: stats
      };
    } catch (e) {
      console.error('准备关键词云数据失败:', e);
      return {
        keywordCloudData: [],
        topKeywords: [],
        keywordStats: {
          positiveCount: 0,
          neutralCount: 0,
          negativeCount: 0
        }
      };
    }
  },

  /**
   * P2-3 修复：渲染关键词云
   */
  renderWordCloud: function() {
    try {
      const query = wx.createSelectorQuery();
      query.select('#wordCloudCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0] || !res[0].node) {
            console.error('Canvas not found');
            return;
          }
          
          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;
          
          // 设置 Canvas 尺寸
          const width = this.data.wordCloudCanvasWidth;
          const height = this.data.wordCloudCanvasHeight;
          canvas.width = width * dpr;
          canvas.height = height * dpr;
          ctx.scale(dpr, dpr);
          
          const data = this.data.keywordCloudData;
          const centerX = width / 2;
          const centerY = height / 2;
          
          // 清空画布
          ctx.clearRect(0, 0, width, height);
          
          // 绘制词云
          this.drawWordCloud(ctx, centerX, centerY, data);
          
          this.setData({ wordCloudRendered: true });
        });
    } catch (e) {
      console.error('渲染词云失败:', e);
    }
  },

  /**
   * 绘制关键词云
   */
  drawWordCloud: function(ctx, centerX, centerY, data) {
    const placedWords = [];
    const maxRadius = Math.min(centerX, centerY) - 40;
    
    // 情感颜色映射
    const sentimentColors = {
      'positive': '#00F5A0',  // 绿色
      'neutral': '#00A9FF',   // 蓝色
      'negative': '#F44336'   // 红色
    };
    
    data.forEach((item, index) => {
      // 计算字体大小（12-28px）
      const fontSize = Math.round(12 + item.weight * 16);
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = sentimentColors[item.sentiment] || '#FFFFFF';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // 计算位置（螺旋布局）
      const angle = index * 0.5;  // 黄金角度
      const radius = (index / data.length) * maxRadius;
      let x = centerX + Math.cos(angle) * radius;
      let y = centerY + Math.sin(angle) * radius;
      
      // 简单的碰撞检测
      let overlap = false;
      const wordWidth = ctx.measureText(item.word).width;
      const wordHeight = fontSize;
      
      for (let placed of placedWords) {
        const dx = x - placed.x;
        const dy = y - placed.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < (wordWidth + placed.width) / 2) {
          overlap = true;
          break;
        }
      }
      
      // 如果不重叠，绘制并记录
      if (!overlap || index < 5) {  // 前 5 个词强制显示
        ctx.fillText(item.word, x, y);
        placedWords.push({
          x: x,
          y: y,
          width: wordWidth,
          height: wordHeight
        });
      }
    });
  },

  /**
   * P2-2 修复：准备雷达图数据
   */
  prepareRadarChartData: function(competitiveAnalysis, targetBrand, competitorBrands) {
    try {
      if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
        return [];
      }
      
      const brandScores = competitiveAnalysis.brandScores;
      const targetScores = brandScores[targetBrand] || {};
      
      // 计算竞品平均分
      let competitorScores = {};
      let competitorCount = 0;
      
      competitorBrands.forEach(brand => {
        if (brandScores[brand]) {
          competitorCount++;
          const scores = brandScores[brand];
          Object.keys(scores).forEach(key => {
            if (key.startsWith('overall') && key !== 'overallScore' && key !== 'overallGrade' && key !== 'overallSummary') {
              competitorScores[key] = (competitorScores[key] || 0) + (scores[key] || 0);
            }
          });
        }
      });
      
      // 计算平均值
      if (competitorCount > 0) {
        Object.keys(competitorScores).forEach(key => {
          competitorScores[key] = Math.round(competitorScores[key] / competitorCount);
        });
      }
      
      // 构建雷达图数据（5 个维度）
      const dimensionMap = {
        'overallAuthority': '权威度',
        'overallVisibility': '可见度',
        'overallSentiment': '好感度',
        'overallPurity': '纯净度',
        'overallConsistency': '一致性'
      };
      
      const radarData = [];
      Object.keys(dimensionMap).forEach(key => {
        radarData.push({
          dimension: dimensionMap[key],
          myBrand: targetScores[key] || 0,
          competitor: competitorScores[key] || 0
        });
      });
      
      return radarData;
    } catch (e) {
      console.error('准备雷达图数据失败:', e);
      return [];
    }
  },

  /**
   * P2-2 修复：渲染雷达图
   */
  renderRadarChart: function() {
    try {
      const query = wx.createSelectorQuery();
      query.select('#radarChartCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res[0] || !res[0].node) {
            console.error('Canvas not found');
            return;
          }
          
          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;
          
          // 设置 Canvas 尺寸
          const width = this.data.canvasWidth;
          const height = this.data.canvasHeight;
          canvas.width = width * dpr;
          canvas.height = height * dpr;
          ctx.scale(dpr, dpr);
          
          const centerX = width / 2;
          const centerY = height / 2;
          const radius = Math.min(width, height) / 2 - 40;
          const data = this.data.radarChartData;
          
          // 清空画布
          ctx.clearRect(0, 0, width, height);
          
          // 绘制背景网格（5 边形）
          this.drawRadarGrid(ctx, centerX, centerY, radius);
          
          // 绘制数据区域
          this.drawRadarData(ctx, centerX, centerY, radius, data);
          
          this.setData({ radarChartRendered: true });
        });
    } catch (e) {
      console.error('渲染雷达图失败:', e);
    }
  },

  /**
   * 绘制雷达图网格
   */
  drawRadarGrid: function(ctx, centerX, centerY, radius) {
    const levels = 5;
    const angleStep = (Math.PI * 2) / 5;
    
    for (let level = 1; level <= levels; level++) {
      const levelRadius = (radius / levels) * level;
      ctx.beginPath();
      
      for (let i = 0; i <= 5; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const x = centerX + Math.cos(angle) * levelRadius;
        const y = centerY + Math.sin(angle) * levelRadius;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      ctx.closePath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    
    // 绘制维度轴线
    for (let i = 0; i < 5; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
      
      // 绘制维度标签
      const labelAngle = i * angleStep - Math.PI / 2;
      const labelRadius = radius + 20;
      const labelX = centerX + Math.cos(labelAngle) * labelRadius;
      const labelY = centerY + Math.sin(labelAngle) * labelRadius;
      
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(this.data.radarChartData[i].dimension, labelX, labelY);
    }
  },

  /**
   * 绘制雷达图数据
   */
  drawRadarData: function(ctx, centerX, centerY, radius, data) {
    const angleStep = (Math.PI * 2) / 5;
    
    // 绘制目标品牌区域（绿色）
    ctx.beginPath();
    for (let i = 0; i <= 5; i++) {
      const dataIndex = i % 5;
      const angle = i * angleStep - Math.PI / 2;
      const value = data[dataIndex].myBrand;
      const pointRadius = (value / 100) * radius;
      const x = centerX + Math.cos(angle) * pointRadius;
      const y = centerY + Math.sin(angle) * pointRadius;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 245, 160, 0.3)';
    ctx.fill();
    ctx.strokeStyle = '#00F5A0';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 绘制竞品平均区域（蓝色）
    ctx.beginPath();
    for (let i = 0; i <= 5; i++) {
      const dataIndex = i % 5;
      const angle = i * angleStep - Math.PI / 2;
      const value = data[dataIndex].competitor;
      const pointRadius = (value / 100) * radius;
      const x = centerX + Math.cos(angle) * pointRadius;
      const y = centerY + Math.sin(angle) * pointRadius;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 169, 255, 0.3)';
    ctx.fill();
    ctx.strokeStyle = '#00A9FF';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 绘制数据点
    for (let i = 0; i < 5; i++) {
      const angle = i * angleStep - Math.PI / 2;
      
      // 目标品牌数据点
      const myBrandRadius = (data[i].myBrand / 100) * radius;
      const myBrandX = centerX + Math.cos(angle) * myBrandRadius;
      const myBrandY = centerY + Math.sin(angle) * myBrandRadius;
      
      ctx.beginPath();
      ctx.arc(myBrandX, myBrandY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00F5A0';
      ctx.fill();
      
      // 竞品平均数据点
      const competitorRadius = (data[i].competitor / 100) * radius;
      const competitorX = centerX + Math.cos(angle) * competitorRadius;
      const competitorY = centerY + Math.sin(angle) * competitorRadius;
      
      ctx.beginPath();
      ctx.arc(competitorX, competitorY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00A9FF';
      ctx.fill();
    }
  },

  /**
   * P1-3 修复：处理优化建议数据
   */
  processRecommendationData: function(competitiveAnalysis, results) {
    try {
      // 从 backend 获取建议数据
      const recommendations = competitiveAnalysis.recommendations || [];
      
      if (!recommendations || recommendations.length === 0) {
        return { recommendationData: null };
      }
      
      // 统计各优先级数量
      let highPriorityCount = 0;
      let mediumPriorityCount = 0;
      let lowPriorityCount = 0;
      
      // 处理每条建议
      const processedRecommendations = recommendations.map(rec => {
        // 统计优先级
        if (rec.priority === 'high') highPriorityCount++;
        else if (rec.priority === 'medium') mediumPriorityCount++;
        else if (rec.priority === 'low') lowPriorityCount++;
        
        // 转换优先级文本
        const priorityTextMap = {
          'high': '高优先级',
          'medium': '中优先级',
          'low': '低优先级'
        };
        
        // 转换类型文本
        const typeTextMap = {
          'content_correction': '内容纠偏',
          'brand_strengthening': '品牌强化',
          'source_attack': '信源攻坚',
          'risk_mitigation': '风险缓解'
        };
        
        // 转换预估影响文本
        const impactTextMap = {
          'high': '高影响',
          'medium': '中影响',
          'low': '低影响'
        };
        
        return {
          priority: rec.priority || 'medium',
          priorityText: priorityTextMap[rec.priority] || '中优先级',
          type: rec.type || 'content_correction',
          typeText: typeTextMap[rec.type] || '内容纠偏',
          title: rec.title || '优化建议',
          description: rec.description || '',
          target: rec.target || '',
          estimatedImpact: rec.estimated_impact || 'medium',
          estimatedImpactText: impactTextMap[rec.estimated_impact] || '中影响',
          actionSteps: rec.action_steps || [],
          urgency: rec.urgency || 5
        };
      });
      
      return {
        recommendationData: {
          totalCount: recommendations.length,
          highPriorityCount: highPriorityCount,
          mediumPriorityCount: mediumPriorityCount,
          lowPriorityCount: lowPriorityCount,
          recommendations: processedRecommendations
        }
      };
    } catch (e) {
      console.error('处理优化建议数据失败:', e);
      return {
        recommendationData: null
      };
    }
  },

  /**
   * P1-2 修复：处理信源纯净度数据
   */
  processSourcePurityData: function(competitiveAnalysis, results) {
    try {
      // 从 backend 获取信源情报图谱
      const sourceIntelligenceMap = competitiveAnalysis.sourceIntelligenceMap || null;
      
      let purityScore = 0;
      let purityLevel = 'high';
      let purityLevelText = '优秀';
      let highWeightRatio = 0;
      let pollutionCount = 0;
      let categoryDistribution = [];
      let topSources = [];
      let pollutionSources = [];
      
      if (sourceIntelligenceMap && sourceIntelligenceMap.nodes) {
        const nodes = sourceIntelligenceMap.nodes;
        
        // 过滤掉品牌节点
        const sourceNodes = nodes.filter(n => n.level > 0);
        
        // 计算纯净度分数
        const highWeightSources = sourceNodes.filter(n => n.value >= 7);
        const mediumWeightSources = sourceNodes.filter(n => n.value >= 4 && n.value < 7);
        const lowWeightSources = sourceNodes.filter(n => n.value < 4);
        const riskSources = sourceNodes.filter(n => n.category === 'risk' || n.sentiment === 'negative');
        
        const totalSources = sourceNodes.length;
        
        if (totalSources > 0) {
          // 纯净度 = (高权重源数量 * 100 + 中权重源数量 * 70 + 低权重源数量 * 30) / 总源数量
          purityScore = Math.round(
            (highWeightSources.length * 100 + mediumWeightSources.length * 70 + lowWeightSources.length * 30) / totalSources
          );
          
          // 高权重信源占比
          highWeightRatio = Math.round((highWeightSources.length / totalSources) * 100);
          
          // 污染源数量
          pollutionCount = riskSources.length;
          
          // 判断纯净度等级
          if (purityScore >= 80) {
            purityLevel = 'high';
            purityLevelText = '优秀';
          } else if (purityScore >= 60) {
            purityLevel = 'medium';
            purityLevelText = '良好';
          } else if (purityScore >= 40) {
            purityLevel = 'low';
            purityLevelText = '一般';
          } else {
            purityLevel = 'critical';
            purityLevelText = '较差';
          }
        }
        
        // 信源类别分布
        const categoryCount = {};
        sourceNodes.forEach(node => {
          const cat = node.category || 'other';
          if (!categoryCount[cat]) {
            categoryCount[cat] = 0;
          }
          categoryCount[cat]++;
        });
        
        const categoryNames = {
          'social': '社交媒体',
          'wiki': '百科',
          'tech': '科技媒体',
          'news': '新闻媒体',
          'official': '官方',
          'finance': '财经',
          'risk': '风险源',
          'other': '其他'
        };
        
        Object.keys(categoryCount).forEach(cat => {
          const count = categoryCount[cat];
          categoryDistribution.push({
            category: cat,
            categoryName: categoryNames[cat] || cat,
            count: count,
            percentage: totalSources > 0 ? Math.round((count / totalSources) * 100) : 0
          });
        });
        
        // 信源权重排名（Top 10）
        topSources = sourceNodes
          .sort((a, b) => (b.value || 0) - (a.value || 0))
          .slice(0, 10)
          .map(node => ({
            name: node.name,
            weight: node.value || 0,
            isHighWeight: node.value >= 7
          }));
        
        // 污染源
        pollutionSources = riskSources.map(node => ({
          name: node.name,
          reason: node.sentiment === 'negative' ? '负面情感' : '风险源'
        }));
      }
      
      // 如果没有信源情报数据，使用默认值
      if (!sourceIntelligenceMap || !sourceIntelligenceMap.nodes) {
        purityScore = 70;
        purityLevel = 'medium';
        purityLevelText = '良好';
        highWeightRatio = 50;
        pollutionCount = 0;
        categoryDistribution = [
          { category: 'social', categoryName: '社交媒体', count: 3, percentage: 50 },
          { category: 'news', categoryName: '新闻媒体', count: 2, percentage: 33 },
          { category: 'official', categoryName: '官方', count: 1, percentage: 17 }
        ];
        topSources = [
          { name: '知乎', weight: 7, isHighWeight: true },
          { name: '36Kr', weight: 6, isHighWeight: false },
          { name: '官网', weight: 9, isHighWeight: true }
        ];
        pollutionSources = [];
      }
      
      return {
        sourcePurityData: {
          purityScore: purityScore,
          purityLevel: purityLevel,
          purityLevelText: purityLevelText,
          highWeightRatio: highWeightRatio,
          pollutionCount: pollutionCount,
          categoryDistribution: categoryDistribution,
          topSources: topSources,
          pollutionSources: pollutionSources
        },
        sourceIntelligenceMap: sourceIntelligenceMap
      };
    } catch (e) {
      console.error('处理信源纯净度数据失败:', e);
      return {
        sourcePurityData: null,
        sourceIntelligenceMap: null
      };
    }
  },

  /**
   * 获取分数对应的总结描述
   */
  getScoreSummary: function(score) {
    if (score >= 90) return '表现卓越，行业标杆';
    if (score >= 80) return '表现优秀，保持领先';
    if (score >= 70) return '表现良好，稳中有进';
    if (score >= 60) return '表现一般，有待提升';
    return '表现较弱，急需改进';
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

      grouped[brand].scores.authority_score += item.authority_score || 0;
      grouped[brand].scores.visibility_score += item.visibility_score || 0;
      grouped[brand].scores.purity_score += item.purity_score || 0;
      grouped[brand].scores.consistency_score += item.consistency_score || 0;

      grouped[brand].questions.push({
        question: item.question,
        response: item.response
      });
    });

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

    return Object.values(grouped).sort((a, b) => {
      if (a.isMainBrand && !b.isMainBrand) return -1;
      if (!a.isMainBrand && b.isMainBrand) return 1;
      return b.overallScore - a.overallScore;
    });
  },

  // 生成维度对比数据
  generateDimensionComparison: function(results, mainBrand) {
    if (!results || !Array.isArray(results)) {
      return [];
    }

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

      Object.keys(brandScores).forEach(brand => {
        brandScores[brand].score = Math.round(brandScores[brand].score / brandScores[brand].count) || 0;
      });

      const allScores = Object.values(brandScores).map(b => b.score);
      const averageScore = allScores.length > 0 ? Math.round(allScores.reduce((a, b) => a + b, 0) / allScores.length) : 0;

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

        const currentPlatform = platforms.length > 0 ? platforms[0] : '';
        const insights = this.generateInsights(cachedAnalysis, cachedBrand);
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

    if (results && Array.isArray(results)) {
      results.forEach(item => {
        if (item.aiModel) {
          platforms.add(item.aiModel);
          platformDisplayNames[item.aiModel] = item.aiModel;
        }
      });
    } else if (competitiveAnalysis.firstMentionByPlatform) {
      Object.keys(competitiveAnalysis.firstMentionByPlatform).forEach(platform => {
        platforms.add(platform);
        platformDisplayNames[platform] = platform;
      });
    }

    Array.from(platforms).forEach(platform => {
      pkDataByPlatform[platform] = [];

      competitors.forEach(comp => {
        const myBrandData = competitiveAnalysis.brandScores[targetBrand] || { overallScore: 0, overallGrade: 'D' };
        const competitorData = competitiveAnalysis.brandScores[comp] || { overallScore: 0, overallGrade: 'D' };

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
    if (this.data.latestTestResults && this.data.competitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.competitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    wx.reLaunch({ url: '/pages/index/index' });
  },

  generateReport: function() {
    // 使用 PDF 导出工具生成完整报告
    generateFullReport(this);
  },

  viewHistory: function() {
    if (this.data.latestTestResults && this.data.competitiveAnalysis && this.data.targetBrand) {
      wx.setStorageSync('latestTestResults', this.data.latestTestResults);
      wx.setStorageSync('latestCompetitiveAnalysis', this.data.competitiveAnalysis);
      wx.setStorageSync('latestTargetBrand', this.data.targetBrand);
    }

    // 跳转到个人历史记录页面（查看本地保存的结果，无需登录）
    wx.navigateTo({
      url: '/pages/personal-history/personal-history'
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

    const that = this;

    try {
      const saveData = {
        id: Date.now().toString(),
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

      // 使用云端同步工具保存结果
      saveResult(saveData)
        .then(() => {
          that.setData({
            showSaveResultModal: false
          });

          wx.showToast({
            title: '保存成功',
            icon: 'success'
          });
        })
        .catch(error => {
          console.error('保存搜索结果失败', error);
          wx.showToast({
            title: '保存失败',
            icon: 'none'
          });
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
        content: `类型：${source.category}\n权重：${source.value || 'N/A'}\n情感：${source.sentiment || 'N/A'}`,
        showCancel: false,
        confirmText: '确定'
      });
    }
  }
})
