#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix results.js onLoad function - robust version using line-by-line parsing
"""

with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find onLoad function start
onload_start = -1
for i, line in enumerate(lines):
    if 'onLoad: function(options)' in line:
        onload_start = i
        break

if onload_start == -1:
    print('❌ Could not find onLoad function')
    exit(1)

# Find the end of onLoad function (next function or closing brace)
brace_count = 0
onload_end = -1
in_onload = False

for i in range(onload_start, len(lines)):
    line = lines[i]
    if 'onLoad:' in line or 'onLoad :' in line:
        in_onload = True
        brace_count = 0
    
    if in_onload:
        brace_count += line.count('{') - line.count('}')
        if brace_count <= 0 and '{' in ''.join(lines[onload_start:i+1]):
            onload_end = i + 1
            break

if onload_end == -1:
    print('❌ Could not find end of onLoad function')
    exit(1)

print(f'Found onLoad function from line {onload_start+1} to {onload_end}')

# Create new onLoad function
new_onload = '''  /**
   * P0-1 修复：支持从 executionId 加载本地存储的数据
   * 【关键优化】优先从 Storage 加载，支持后端 API 拉取
   */
  onLoad: function(options) {
    console.log('📥 结果页加载 options:', options);

    const executionId = decodeURIComponent(options.executionId || '');
    const brandName = decodeURIComponent(options.brandName || '');

    // 【关键修复】优先从统一 Storage 加载（避免 URL 编码 2KB 限制）
    const lastDiagnosticResults = wx.getStorageSync('last_diagnostic_results');
    
    console.log('📦 检查统一 Storage (last_diagnostic_results):', {
      exists: !!lastDiagnosticResults,
      executionId: lastDiagnosticResults?.executionId,
      timestamp: lastDiagnosticResults?.timestamp
    });

    // 【多层降级策略】
    let results = null;
    let competitiveAnalysis = null;
    let targetBrand = brandName;

    // 1. 优先从统一 Storage 加载（最新策略）
    if (lastDiagnosticResults && lastDiagnosticResults.results) {
      console.log('✅ 从统一 Storage 加载数据');
      results = lastDiagnosticResults.results;
      competitiveAnalysis = lastDiagnosticResults.competitiveAnalysis || {};
      targetBrand = lastDiagnosticResults.targetBrand || brandName;
    } 
    // 2. 从 executionId 缓存加载（兼容旧逻辑）
    else if (executionId) {
      const cachedResults = wx.getStorageSync('latestTestResults_' + executionId);
      const cachedCompetitiveAnalysis = wx.getStorageSync('latestCompetitiveAnalysis_' + executionId);
      const cachedBrandScores = wx.getStorageSync('latestBrandScores_' + executionId);
      const cachedBrand = wx.getStorageSync('latestTargetBrand');

      console.log('📦 本地存储数据 (executionId 缓存):', {
        hasResults: !!cachedResults && cachedResults.length > 0,
        hasCompetitiveAnalysis: !!cachedCompetitiveAnalysis,
        hasBrandScores: !!cachedBrandScores
      });

      if (cachedResults && cachedResults.length > 0) {
        results = cachedResults;
        competitiveAnalysis = cachedCompetitiveAnalysis || {};
        targetBrand = cachedBrand || brandName;
      }
    }

    // 3. 数据完整性检查
    if (!competitiveAnalysis || !competitiveAnalysis.brandScores) {
      if (lastDiagnosticResults && lastDiagnosticResults.brandScores) {
        competitiveAnalysis.brandScores = lastDiagnosticResults.brandScores;
      } else {
        competitiveAnalysis = {
          brandScores: competitiveAnalysis.brandScores || {},
          firstMentionByPlatform: {},
          interceptionRisks: []
        };
      }
    }

    // 4. 初始化页面或从后端拉取
    if (results && results.length > 0) {
      console.log('✅ 使用本地数据初始化页面，结果数量:', results.length);
      this.initializePageWithData(
        results,
        targetBrand || '',
        [],
        competitiveAnalysis,
        null, null, null
      );
    } else if (executionId) {
      // 【专家调优】从后端 API 拉取最新数据
      console.log('🔄 本地无数据，从后端 API 拉取...');
      this.fetchResultsFromServer(executionId, targetBrand);
    } else {
      console.error('❌ 无有效数据，显示友好提示');
      this.showNoDataModal();
    }
  },

  /**
   * 【新增】从后端 API 拉取结果数据
   */
  fetchResultsFromServer: function(executionId, brandName) {
    const app = getApp();
    const baseUrl = app.globalData?.apiUrl || 'http://localhost:5000';
    
    wx.request({
      url: `${baseUrl}/api/test-progress?executionId=${executionId}`,
      method: 'GET',
      success: (res) => {
        console.log('📡 后端 API 响应:', res.data);
        
        if (res.data && (res.data.detailed_results || res.data.results)) {
          const resultsToUse = res.data.detailed_results || res.data.results || [];
          const competitiveAnalysisToUse = res.data.competitive_analysis || {};
          
          // 保存到 Storage
          wx.setStorageSync('last_diagnostic_results', {
            results: resultsToUse,
            competitiveAnalysis: competitiveAnalysisToUse,
            brandScores: res.data.brand_scores || competitiveAnalysisToUse.brandScores || {},
            targetBrand: brandName,
            executionId: executionId,
            timestamp: Date.now()
          });
          
          // 初始化页面
          this.initializePageWithData(
            resultsToUse,
            brandName,
            [],
            competitiveAnalysisToUse,
            null, null, null
          );
          
          wx.showToast({ title: '数据加载成功', icon: 'success' });
        } else {
          console.error('❌ 后端 API 返回数据为空');
          this.showNoDataModal();
        }
      },
      fail: (err) => {
        console.error('❌ 后端 API 请求失败:', err);
        this.showNoDataModal();
      }
    });
  },

  /**
   * 【新增】显示无数据提示
   */
  showNoDataModal: function() {
    wx.showModal({
      title: '暂无数据',
      content: '未找到诊断结果数据，请重新运行诊断或返回首页。',
      confirmText: '返回首页',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          wx.reLaunch({ url: '/pages/index/index' });
        }
      }
    });
  },

'''

# Replace onLoad function
new_lines = lines[:onload_start] + [new_onload] + lines[onload_end:]

with open('/Users/sgl/PycharmProjects/PythonProject/pages/results/results.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ results.js onLoad function updated successfully')
