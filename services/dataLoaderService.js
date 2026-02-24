const { debug, info, warn, error } = require('../../utils/logger');

/**
 * 统一数据加载服务
 *
 * 简化版数据加载策略：
 * 1. 优先从 Storage 加载（快速）
 * 2. Storage 无数据时从 API 加载（可靠）
 *
 * 废弃多层降级策略，简化为两层：Storage → API
 */

const { loadDiagnosisResult } = require('../utils/storage-manager');

/**
 * 数据加载配置
 */
const LOAD_CONFIG = {
  // Storage 键名前缀
  STORAGE_KEY_PREFIX: 'diagnosis_',
  // 缓存过期时间（毫秒）- 1 小时
  CACHE_TTL: 60 * 60 * 1000,
  // 是否启用缓存
  ENABLE_CACHE: true,
  // P2-014 新增：质量评分阈值
  QUALITY_THRESHOLDS: {
    EXCELLENT: 90,  // 优秀，可直接使用
    GOOD: 75,       // 良好，建议使用
    FAIR: 60,       // 一般，提示用户
    POOR: 0         // 较差，建议重测
  }
};

/**
 * 加载策略结果
 */
class LoadResult {
  constructor() {
    this.data = null;         // 加载的数据
    this.fromCache = false;   // 是否来自缓存
    this.error = null;        // 错误信息
    this.success = false;     // 是否成功
  }

  static success(data, fromCache = false) {
    const result = new LoadResult();
    result.success = true;
    result.data = data;
    result.fromCache = fromCache;
    return result;
  }

  static error(message) {
    const result = new LoadResult();
    result.error = message;
    return result;
  }
}

/**
 * 从 Storage 加载数据
 * @param {string} executionId - 执行 ID
 * @returns {LoadResult} 加载结果
 */
function loadFromStorage(executionId) {
  try {
    if (!executionId) {
      return LoadResult.error('缺少 executionId');
    }

    // 从统一 Storage 加载
    const storageData = loadDiagnosisResult(executionId);
    
    if (storageData && storageData.data) {
      // 检查数据完整性
      const hasResults = storageData.data.results && 
                        Array.isArray(storageData.data.results) && 
                        storageData.data.results.length > 0;
      
      if (hasResults) {
        console.log(`✅ 从 Storage 加载成功：${storageData.data.results.length} 条结果`);
        return LoadResult.success(storageData.data, true);
      }
    }

    console.log('⚠️ Storage 无有效数据');
    return LoadResult.error('Storage 无有效数据');
  } catch (error) {
    console.error('❌ Storage 加载失败:', error);
    return LoadResult.error(`Storage 加载失败：${error.message}`);
  }
}

/**
 * 从 API 加载数据
 * @param {string} executionId - 执行 ID
 * @returns {Promise<LoadResult>} 加载结果
 */
async function loadFromApi(executionId) {
  try {
    if (!executionId) {
      return LoadResult.error('缺少 executionId');
    }

    console.log('🔄 从 API 加载数据...');
    
    // 调用后端 API
    const { get } = require('../utils/request');
    const res = await get(`/test/status/${executionId}`);
    
    if (!res) {
      return LoadResult.error('API 返回空数据');
    }

    // 提取数据
    const data = {
      results: res.detailed_results || res.results || [],
      competitive_analysis: res.competitive_analysis || {},
      brand_scores: res.brand_scores || {},
      semantic_drift_data: res.semantic_drift_data || null,
      recommendation_data: res.recommendation_data || null,
      negative_sources: res.negative_sources || [],
      insights: res.insights || null,
      source_purity_data: res.source_purity_data || null,
      source_intelligence_map: res.source_intelligence_map || null,
      // P0-012 新增：提取警告和质量评分
      warning: res.warning || null,
      missing_count: res.missing_count || 0,
      quality_score: res.quality_score || null,
      quality_level: res.quality_level || null
    };

    // 验证数据完整性
    if (!data.results || data.results.length === 0) {
      return LoadResult.error('API 返回空结果');
    }

    // P2-014 新增：质量评分评估
    if (data.quality_score !== null && data.quality_score !== undefined) {
      const thresholds = LOAD_CONFIG.QUALITY_THRESHOLDS;
      
      if (data.quality_score < thresholds.FAIR) {
        // 质量较差，添加警告
        data.quality_warning = `报告质量较低（${data.quality_score}分），建议重新诊断`;
        data.quality_suggestion = 'retry';
      } else if (data.quality_score < thresholds.GOOD) {
        // 质量一般，提示用户
        data.quality_warning = `报告质量一般（${data.quality_score}分），仅供参考`;
        data.quality_suggestion = 'caution';
      }
    }

    console.log(`✅ 从 API 加载成功：${data.results.length} 条结果`);
    return LoadResult.success(data, false);
  } catch (error) {
    console.error('❌ API 加载失败:', error);
    return LoadResult.error(`API 加载失败：${error.message}`);
  }
}

/**
 * 统一数据加载接口
 * 
 * 加载策略：
 * 1. 优先从 Storage 加载（快速）
 * 2. Storage 失败时从 API 加载（可靠）
 * 
 * @param {string} executionId - 执行 ID
 * @param {Object} options - 加载选项
 * @param {boolean} options.forceRefresh - 强制刷新（忽略缓存）
 * @param {boolean} options.useCacheOnly - 仅使用缓存
 * @returns {Promise<LoadResult>} 加载结果
 */
async function loadDiagnosisData(executionId, options = {}) {
  const { forceRefresh = false, useCacheOnly = false } = options;

  console.log('📦 开始加载诊断数据:', { executionId, forceRefresh, useCacheOnly });

  // 策略 1: 强制刷新时跳过缓存
  if (forceRefresh) {
    console.log('⚡ 强制刷新模式，跳过缓存');
    return await loadFromApi(executionId);
  }

  // 策略 2: 优先从 Storage 加载
  if (!useCacheOnly) {
    const storageResult = loadFromStorage(executionId);
    
    if (storageResult.success) {
      console.log('✅ 使用缓存数据');
      return storageResult;
    }

    console.log('⚠️ 缓存未命中，从 API 加载');
  }

  // 策略 3: 从 API 加载
  if (useCacheOnly) {
    console.log('⚠️ 仅使用缓存模式，API 加载被跳过');
    return LoadResult.error('缓存未命中且仅使用缓存模式');
  }

  const apiResult = await loadFromApi(executionId);
  
  // API 加载成功后，可选保存到缓存
  if (apiResult.success && LOAD_CONFIG.ENABLE_CACHE) {
    console.log('💾 保存数据到缓存');
    // 这里可以添加缓存保存逻辑
  }

  return apiResult;
}

/**
 * 保存到 Storage
 * @param {string} executionId - 执行 ID
 * @param {Object} data - 数据
 */
function saveToStorage(executionId, data) {
  try {
    const { saveDiagnosisResult } = require('../utils/storage-manager');
    saveDiagnosisResult(executionId, {
      version: '2.0',
      data: data,
      timestamp: Date.now()
    });
    console.log('✅ 数据已保存到 Storage');
  } catch (error) {
    console.error('❌ 保存到 Storage 失败:', error);
  }
}

/**
 * 清除缓存
 * @param {string} executionId - 执行 ID
 */
function clearCache(executionId) {
  try {
    wx.removeStorageSync(`diagnosis_${executionId}`);
    console.log('✅ 缓存已清除');
  } catch (error) {
    console.error('❌ 清除缓存失败:', error);
  }
}

/**
 * 预加载数据（后台加载到缓存）
 * @param {string} executionId - 执行 ID
 */
async function preloadData(executionId) {
  console.log('🔄 预加载数据...');
  const result = await loadFromApi(executionId);
  
  if (result.success) {
    saveToStorage(executionId, result.data);
  }
  
  return result;
}

module.exports = {
  // 核心接口
  loadDiagnosisData,
  loadFromStorage,
  loadFromApi,
  
  // 辅助函数
  saveToStorage,
  clearCache,
  preloadData,
  
  // 配置
  LOAD_CONFIG,
  LoadResult
};
