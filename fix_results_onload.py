#!/usr/bin/env python3
"""
修复结果页数据加载逻辑，实现多层降级策略
"""

# 读取文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: onLoad 函数
old_onload = '''onLoad: function(options) {
    console.log('Results page loaded with options:', options);

    // P0-1 修复：支持从 executionId 加载本地存储的数据
    if (options.executionId) {
      const executionId = decodeURIComponent(options.executionId);
      const brandName = decodeURIComponent(options.brandName || '');

      console.log('📥 从 executionId 加载数据:', executionId, brandName);

      // 【P0 修复】从本地存储获取数据，优先获取 brand_scores
      const cachedResults = wx.getStorageSync('latestTestResults_' + executionId);
      const cachedBrand = wx.getStorageSync('latestTargetBrand');
      const cachedCompetitors = wx.getStorageSync('latestCompetitorBrands');
      
      // 优先从 brand_scores 获取（最准确）
      let cachedBrandScores = wx.getStorageSync('latestBrandScores_' + executionId);
      if (!cachedBrandScores || !cachedBrandScores[brandName]) {
        cachedBrandScores = wx.getStorageSync('latestBrandScores');
      }
      
      // 从 competitiveAnalysis 获取
      let cachedCompetitiveAnalysis = wx.getStorageSync('latestCompetitiveAnalysis_' + executionId);
      if (!cachedCompetitiveAnalysis || !cachedCompetitiveAnalysis.brandScores) {
        cachedCompetitiveAnalysis = wx.getStorageSync('latestCompetitiveAnalysis');
      }
      
      // 如果有 brand_scores，构建 competitiveAnalysis
      if (cachedBrandScores && Object.keys(cachedBrandScores).length > 0) {
        if (!cachedCompetitiveAnalysis) {
          cachedCompetitiveAnalysis = {
            brandScores: cachedBrandScores,
            firstMentionByPlatform: {},
            interceptionRisks: []
          };
        } else {
          cachedCompetitiveAnalysis.brandScores = cachedBrandScores;
        }
        console.log('✅ 使用 brand_scores:', Object.keys(cachedBrandScores));
      }
      
      const cachedNegativeSources = wx.getStorageSync('latestNegativeSources_' + executionId);
      const cachedSemanticDrift = wx.getStorageSync('latestSemanticDrift_' + executionId);
      const cachedRecommendations = wx.getStorageSync('latestRecommendations_' + executionId);

      if (cachedResults && Array.isArray(cachedResults) && cachedResults.length > 0) {
        console.log('✅ 从本地存储加载成功，结果数量:', cachedResults.length);

        // 使用加载的数据初始化页面
        this.initializePageWithData(
          cachedResults,
          cachedBrand || brandName,
          cachedCompetitors || [],
          cachedCompetitiveAnalysis,
          cachedNegativeSources,
          cachedSemanticDrift,
          cachedRecommendations
        );
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
  },'''

new_onload = '''onLoad: function(options) {
    console.log('📥 结果页加载 options:', options);
    
    const executionId = decodeURIComponent(options.executionId || '');
    const brandName = decodeURIComponent(options.brandName || '');
    
    // 【多层降级策略】
    // 1. 优先从本地存储加载
    const cachedResults = wx.getStorageSync('latestTestResults_' + executionId);
    const cachedCompetitiveAnalysis = wx.getStorageSync('latestCompetitiveAnalysis_' + executionId);
    const cachedBrandScores = wx.getStorageSync('latestBrandScores_' + executionId);
    const cachedBrand = wx.getStorageSync('latestTargetBrand');
    
    console.log('📦 本地存储数据:', {
      hasResults: !!cachedResults && cachedResults.length > 0,
      hasCompetitiveAnalysis: !!cachedCompetitiveAnalysis,
      hasBrandScores: !!cachedBrandScores
    });
    
    // 2. 从 URL 参数加载（降级）
    let results = null;
    let competitiveAnalysis = null;
    
    if (cachedResults && cachedResults.length > 0) {
      results = cachedResults;
    } else if (options.results) {
      try {
        results = JSON.parse(decodeURIComponent(options.results));
      } catch (e) {
        console.error('解析 URL results 失败:', e);
      }
    }
    
    if (cachedCompetitiveAnalysis) {
      competitiveAnalysis = cachedCompetitiveAnalysis;
    } else if (options.competitiveAnalysis) {
      try {
        competitiveAnalysis = JSON.parse(decodeURIComponent(options.competitiveAnalysis));
      } catch (e) {
        console.error('解析 URL competitiveAnalysis 失败:', e);
      }
    }
    
    // 3. 数据完整性检查
    if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
      if (cachedBrandScores) {
        competitiveAnalysis = {
          brandScores: cachedBrandScores,
          firstMentionByPlatform: {},
          interceptionRisks: []
        };
      } else {
        competitiveAnalysis = {
          brandScores: {},
          firstMentionByPlatform: {},
          interceptionRisks: []
        };
      }
    }
    
    // 4. 初始化页面
    if (results && results.length > 0) {
      this.initializePageWithData(
        results,
        brandName || cachedBrand || '',
        [],
        competitiveAnalysis,
        null, null, null
      );
    } else {
      console.error('❌ 无有效数据，加载缓存');
      this.loadFromCache();
    }
  },'''

if old_onload in content:
    content = content.replace(old_onload, new_onload)
    print('✅ 修复 1 成功：onLoad 多层降级策略')
else:
    print('❌ 修复 1 失败：未找到匹配内容')

# 保存文件
with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 文件保存成功')
