const { debug, info, warn, error } = require('../utils/logger');
const { get } = require('../utils/request');

/**
 * 结果数据服务
 * 负责诊断结果数据的加载、处理、格式化
 */

/**
 * 从 Storage 加载结果数据
 * @param {string} executionId - 执行 ID
 * @param {string} brandName - 品牌名称
 * @returns {Object} 加载结果 { results, competitiveAnalysis, targetBrand, useStorageData }
 */
const loadResultFromStorage = (executionId, brandName) => {
  console.log('📦 从 Storage 加载结果数据，executionId:', executionId);

  // 1. 优先从统一 Storage 加载
  const lastDiagnosticResults = wx.getStorageSync('last_diagnostic_results');

  console.log('📦 检查统一 Storage:', {
    exists: !!lastDiagnosticResults,
    executionId: lastDiagnosticResults?.executionId,
    timestamp: lastDiagnosticResults?.timestamp,
    hasResults: !!(lastDiagnosticResults?.results && lastDiagnosticResults.results.length > 0),
    hasBrandScores: !!(lastDiagnosticResults?.brandScores)
  });

  let results = null;
  let competitiveAnalysis = null;
  let targetBrand = brandName;
  let useStorageData = false;

  // 从统一 Storage 加载
  if (lastDiagnosticResults &&
      lastDiagnosticResults.results &&
      Array.isArray(lastDiagnosticResults.results) &&
      lastDiagnosticResults.results.length > 0 &&
      (!executionId || lastDiagnosticResults.executionId === executionId)) {
    console.log('✅ 从统一 Storage 加载有效数据');
    results = lastDiagnosticResults.results;
    competitiveAnalysis = lastDiagnosticResults.competitiveAnalysis || {};
    targetBrand = lastDiagnosticResults.targetBrand || brandName;
    useStorageData = true;
  }
  // 从 executionId 缓存加载
  else if (executionId) {
    const cachedResults = wx.getStorageSync('latestTestResults_' + executionId);
    const cachedCompetitiveAnalysis = wx.getStorageSync('latestCompetitiveAnalysis_' + executionId);
    const cachedBrand = wx.getStorageSync('latestTargetBrand');

    if (cachedResults && Array.isArray(cachedResults) && cachedResults.length > 0) {
      results = cachedResults;
      competitiveAnalysis = cachedCompetitiveAnalysis || {};
      targetBrand = cachedBrand || brandName;
      useStorageData = true;
    }
  }

  // 数据完整性检查
  if (competitiveAnalysis && !competitiveAnalysis.brandScores) {
    if (lastDiagnosticResults && lastDiagnosticResults.brandScores) {
      competitiveAnalysis.brandScores = lastDiagnosticResults.brandScores;
    } else {
      competitiveAnalysis.brandScores = {};
    }
  }

  return {
    results,
    competitiveAnalysis,
    targetBrand,
    useStorageData
  };
};

/**
 * 从后端 API 拉取结果数据
 * @param {string} executionId - 执行 ID
 * @param {string} brandName - 品牌名称
 * @param {Function} onSuccess - 成功回调
 * @param {Function} onError - 错误回调
 */
const fetchResultsFromServer = async (executionId, brandName, onSuccess, onError) => {
  const app = getApp();
  const baseUrl = app.globalData?.apiUrl || 'http://127.0.0.1:5001';
  const accessToken = wx.getStorageSync('access_token') || '';

  console.log('📡 从后端 API 拉取结果，executionId:', executionId);

  try {
    const res = await get(`/test/status/${executionId}`, {}, {
      loading: true,
      header: {
        'Authorization': accessToken ? 'Bearer ' + accessToken : ''
      }
    });

    // 处理成功响应
    if (res && (res.detailed_results || res.results)) {
      const resultsToUse = res.detailed_results || res.results || [];
      const competitiveAnalysisToUse = res.competitive_analysis || {};
      const brandScoresToUse = res.brand_scores || competitiveAnalysisToUse.brandScores || {};

      // 保存到 Storage
      wx.setStorageSync('last_diagnostic_results', {
        results: resultsToUse,
        competitiveAnalysis: competitiveAnalysisToUse,
        brandScores: brandScoresToUse,
        targetBrand: brandName,
        executionId: executionId,
        timestamp: Date.now()
      });

      console.log('✅ 从后端 API 加载成功，结果数量:', resultsToUse.length);

      if (onSuccess) onSuccess({
        results: resultsToUse,
        competitiveAnalysis: competitiveAnalysisToUse,
        targetBrand: brandName
      });
    } else if (res && res.statusCode === 404) {
      console.error('❌ 后端 API 返回 404，结果不存在');
      if (onError) onError({ type: 'not_found', message: '未找到诊断结果' });
    } else {
      console.error('❌ 后端 API 返回数据为空');
      if (onError) onError({ type: 'error', message: '数据加载失败' });
    }
  } catch (err) {
    console.error('❌ 后端 API 请求失败:', err);
    
    // P0 增强：根据错误类型给出明确提示
    const isConnectionError = err.errMsg && (
      err.errMsg.includes('fail') ||
      err.errMsg.includes('network') ||
      err.errMsg.includes('timeout')
    );
    
    if (onError) {
      onError({
        type: isConnectionError ? 'network' : 'error',
        message: isConnectionError ? '网络连接失败，请检查后端服务是否启动' : '数据加载失败',
        error: err
      });
    }
  }
};

/**
 * 构建竞争分析数据结构
 * @param {Array} results - 结果数组
 * @param {string} targetBrand - 目标品牌
 * @param {Array} competitorBrands - 竞品品牌列表
 * @returns {Object} 竞争分析数据
 */
const buildCompetitiveAnalysis = (results, targetBrand, competitorBrands) => {
  const brandScores = {};
  const firstMentionByPlatform = {};

  // 按品牌分组计算分数
  const brandResults = {};
  results.forEach(result => {
    const brand = result.brand || result.main_brand || targetBrand;
    if (!brandResults[brand]) {
      brandResults[brand] = [];
    }
    brandResults[brand].push(result);
  });

  // 计算每个品牌的分数
  Object.keys(brandResults).forEach(brand => {
    const scores = brandResults[brand];

    let totalScore = 0;
    let totalAuthority = 0;
    let totalVisibility = 0;
    let totalPurity = 0;
    let totalConsistency = 0;
    let count = 0;

    scores.forEach(s => {
      let score = s.score;
      let authority = s.authority_score;
      let visibility = s.visibility_score;
      let purity = s.purity_score;
      let consistency = s.consistency_score;

      // 从 geo_data 中提取
      if (s.geo_data) {
        const geo = s.geo_data;
        if (score === undefined || score === null) {
          const rank = geo.rank || -1;
          const sentiment = geo.sentiment || 0;
          if (rank <= 3) score = 90 + (3 - rank) * 3 + sentiment * 10;
          else if (rank <= 6) score = 70 + (6 - rank) * 3 + sentiment * 10;
          else if (rank > 0) score = 50 + (10 - rank) * 2 + sentiment * 10;
          else score = 30 + sentiment * 10;
          score = Math.min(100, Math.max(0, score));
        }
        if (authority === undefined || authority === null) {
          authority = 50 + sentiment * 25;
        }
        if (visibility === undefined || visibility === null) {
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

      // 使用默认值
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
        overallSummary: getScoreSummary(avgScore)
      };
    }
  });

  return {
    brandScores,
    firstMentionByPlatform,
    interceptionRisks: {}
  };
};

/**
 * 获取分数摘要
 * @param {number} score - 分数
 * @returns {string} 分数摘要
 */
const getScoreSummary = (score) => {
  if (score >= 90) return '表现卓越';
  if (score >= 80) return '表现良好';
  if (score >= 70) return '表现一般';
  if (score >= 60) return '有待提升';
  return '需要改进';
};

/**
 * 保存结果到 Storage
 * @param {Object} resultData - 结果数据
 * @param {string} executionId - 执行 ID
 * @param {string} brandName - 品牌名称
 */
const saveResultToStorage = (resultData, executionId, brandName) => {
  const resultsToSave = resultData.detailed_results || resultData.results || [];
  const competitiveAnalysisToSave = resultData.competitive_analysis || {};
  const brandScoresToSave = resultData.brand_scores || (competitiveAnalysisToSave && competitiveAnalysisToSave.brandScores) || {};

  wx.setStorageSync('last_diagnostic_results', {
    results: resultsToSave,
    competitiveAnalysis: competitiveAnalysisToSave,
    brandScores: brandScoresToSave,
    targetBrand: brandName,
    executionId: executionId,
    timestamp: Date.now()
  });

  // 兼容旧逻辑
  wx.setStorageSync('latestTestResults_' + executionId, resultsToSave);
  wx.setStorageSync('latestCompetitiveAnalysis_' + executionId, competitiveAnalysisToSave);
  wx.setStorageSync('latestBrandScores_' + executionId, brandScoresToSave);
  wx.setStorageSync('latestTargetBrand', brandName);

  console.log('✅ 结果数据已保存到 Storage:', {
    resultsCount: resultsToSave.length,
    hasCompetitiveAnalysis: Object.keys(competitiveAnalysisToSave).length > 0,
    hasBrandScores: Object.keys(brandScoresToSave).length > 0
  });
};

module.exports = {
  loadResultFromStorage,
  fetchResultsFromServer,
  buildCompetitiveAnalysis,
  saveResultToStorage,
  getScoreSummary
};
