/**
 * P1-1 修复：统一 Storage 管理器
 *
 * 功能：
 * 1. 统一 Storage key 命名规范
 * 2. 添加数据版本控制
 * 3. 添加数据过期检查
 * 4. 提供统一的读写接口
 * 5. 【产品架构优化 - 2026-03-10】自动保存到诊断记录列表
 */

const STORAGE_VERSION = '1.0';
const DATA_EXPIRY_TIME = 90 * 24 * 60 * 60 * 1000; // 90 天（诊断记录保留更长时间）
const DIAGNOSIS_HISTORY_KEY = 'diagnosis_history_list'; // 诊断记录列表

/**
 * Storage Key 枚举
 */
const StorageKey = {
  DIAGNOSIS_RESULT: 'diagnosis_result_',  // 诊断结果（带 executionId）
  LAST_DIAGNOSIS: 'last_diagnostic_results',  // 最后一次诊断（兼容旧 key）
  USER_PREFERENCES: 'user_preferences',
  DRAFT_DATA: 'draft_data'
};

/**
 * 保存诊断结果
 * @param {string} executionId - 执行 ID
 * @param {Object} data - 诊断数据
 * @returns {boolean} 是否保存成功
 */
function saveDiagnosisResult(executionId, data) {
  try {
    if (!executionId || !data) {
      console.error('[Storage] 保存失败：executionId 或 data 为空');
      return false;
    }

    // 【首席工程师修复 - 2026-03-15】排除 rawResponse，避免数据量过大
    // rawResponse 包含完整的 API 响应，可能有几百 KB 甚至几 MB
    // 详情页不需要完整的 rawResponse，只需要结构化的诊断数据
    
    // 创建数据的浅拷贝，排除 rawResponse
    const { rawResponse, ...dataWithoutRawResponse } = data;
    
    // 【P0 关键修复】构建完整的 Storage 数据结构，保存所有详细字段
    const storageData = {
      version: STORAGE_VERSION,
      timestamp: Date.now(),
      executionId: executionId,
      brandName: data.brandName || '',
      completedAt: data.completedAt || new Date().toISOString(),

      // 完整保存所有详细字段（排除 rawResponse）
      data: {
        // 基础信息
        competitorBrands: dataWithoutRawResponse.competitorBrands || [],
        selectedModels: dataWithoutRawResponse.selectedModels || [],
        customQuestions: dataWithoutRawResponse.customQuestions || [],

        // 详细诊断结果
        results: dataWithoutRawResponse.results || [],
        detailedResults: dataWithoutRawResponse.detailedResults || [],

        // 竞争分析（完整字段）
        competitiveAnalysis: dataWithoutRawResponse.competitiveAnalysis || {},
        brandScores: dataWithoutRawResponse.brandScores || {},
        firstMentionByPlatform: dataWithoutRawResponse.firstMentionByPlatform || [],
        interceptionRisks: dataWithoutRawResponse.interceptionRisks || [],
        competitorComparisonData: dataWithoutRawResponse.competitorComparisonData || [],

        // 语义偏移分析（完整字段）
        semanticDriftData: dataWithoutRawResponse.semanticDriftData || null,
        semanticContrastData: dataWithoutRawResponse.semanticContrastData || null,

        // 信源纯净度（完整字段）
        sourcePurityData: dataWithoutRawResponse.sourcePurityData || null,
        sourceIntelligenceMap: dataWithoutRawResponse.sourceIntelligenceMap || null,

        // 优化建议（完整字段）
        recommendationData: dataWithoutRawResponse.recommendationData || null,
        priorityRecommendations: dataWithoutRawResponse.priorityRecommendations || [],
        actionItems: dataWithoutRawResponse.actionItems || [],

        // 质量评分（完整字段）
        qualityScore: dataWithoutRawResponse.qualityScore || {},
        overallScore: dataWithoutRawResponse.overallScore || 0,
        dimensionScores: dataWithoutRawResponse.dimensionScores || {},

        // 模型性能统计
        modelPerformanceStats: dataWithoutRawResponse.modelPerformanceStats || [],

        // 响应时间统计
        responseTimeStats: dataWithoutRawResponse.responseTimeStats || {}
      }

      // ❌ 不保存 rawResponse - 这是导致卡死的根本原因
      // rawResponse: data.rawResponse || null
    };

    // 【首席工程师修复 - 2026-03-15】添加数据大小检查
    try {
      const storageStr = JSON.stringify(storageData);
      const storageSize = (storageStr.length / 1024).toFixed(2);
      console.log(`[Storage] 保存数据大小：${storageSize} KB`);
      
      if (storageSize > 500) {
        console.warn(`[Storage] ⚠️  数据过大 (${storageSize} KB)，可能影响性能`);
      }
      
      if (storageSize > 900) {
        // 接近微信存储限制（1MB），警告
        console.error(`[Storage] ❌ 数据过大 (${storageSize} KB)，接近 1MB 限制`);
      }
    } catch (e) {
      console.warn('[Storage] 无法序列化数据，可能存在循环引用:', e.message);
    }

    // 保存到统一 key
    const key = StorageKey.DIAGNOSIS_RESULT + executionId;
    wx.setStorageSync(key, storageData);

    // 同时保存到 last_diagnostic_results（兼容旧逻辑，保存完整数据）
    wx.setStorageSync(StorageKey.LAST_DIAGNOSIS, {
      version: STORAGE_VERSION,
      executionId: executionId,
      brandName: storageData.brandName,
      completedAt: storageData.completedAt,
      results: storageData.data.results,
      detailedResults: storageData.data.detailedResults,
      competitiveAnalysis: storageData.data.competitiveAnalysis,
      brandScores: storageData.data.brandScores,
      firstMentionByPlatform: storageData.data.firstMentionByPlatform,
      interceptionRisks: storageData.data.interceptionRisks,
      semanticDriftData: storageData.data.semanticDriftData,
      sourcePurityData: storageData.data.sourcePurityData,
      recommendationData: storageData.data.recommendationData,
      qualityScore: storageData.data.qualityScore,
      overallScore: storageData.data.overallScore,
      timestamp: storageData.timestamp
    });

    // 【产品架构优化 - 2026-03-10】自动添加到诊断记录列表
    addToDiagnosisHistory({
      executionId: executionId,
      brandName: storageData.brandName,
      createdAt: storageData.completedAt || new Date().toISOString(),
      status: 'completed',
      overallScore: storageData.data.overallScore || 0,
      aiModels: storageData.data.selectedModels || [],
      questionCount: (storageData.data.customQuestions || []).length,
      competitorCount: (storageData.data.competitorBrands || []).length,
      timestamp: storageData.timestamp
    });

    console.log(`[Storage] ✅ 诊断结果已完整保存并添加到记录列表：${executionId}`);
    return true;
  } catch (error) {
    console.error('[Storage] 保存诊断结果失败:', error);
    return false;
  }
}

/**
 * 【产品架构优化 - 2026-03-10】添加到诊断记录列表
 * @param {Object} record - 诊断记录摘要
 */
function addToDiagnosisHistory(record) {
  try {
    // 获取现有历史记录
    let history = wx.getStorageSync(DIAGNOSIS_HISTORY_KEY) || [];
    
    // 检查是否已存在（避免重复添加）
    const exists = history.some(item => item.executionId === record.executionId);
    if (exists) {
      console.log(`[Storage] ℹ️  记录已存在，跳过添加：${record.executionId}`);
      return;
    }
    
    // 添加到列表开头（最新的在前）
    history.unshift(record);
    
    // 限制最多保存 200 条记录
    if (history.length > 200) {
      history = history.slice(0, 200);
    }
    
    // 保存回 Storage
    wx.setStorageSync(DIAGNOSIS_HISTORY_KEY, history);
    
    console.log(`[Storage] ✅ 诊断记录已添加到列表：${record.executionId}`, history.length);
  } catch (error) {
    console.error('[Storage] 添加到诊断记录列表失败:', error);
  }
}

/**
 * 【产品架构优化 - 2026-03-10】从诊断记录列表移除
 * @param {string} executionId - 执行 ID
 */
function removeFromDiagnosisHistory(executionId) {
  try {
    let history = wx.getStorageSync(DIAGNOSIS_HISTORY_KEY) || [];
    history = history.filter(item => item.executionId !== executionId);
    wx.setStorageSync(DIAGNOSIS_HISTORY_KEY, history);
    console.log(`[Storage] ✅ 诊断记录已从列表移除：${executionId}`);
  } catch (error) {
    console.error('[Storage] 从诊断记录列表移除失败:', error);
  }
}

/**
 * 【产品架构优化 - 2026-03-10】获取诊断记录列表
 * @returns {Array} 诊断记录列表
 */
function getDiagnosisHistory() {
  try {
    return wx.getStorageSync(DIAGNOSIS_HISTORY_KEY) || [];
  } catch (error) {
    console.error('[Storage] 获取诊断记录列表失败:', error);
    return [];
  }
}

/**
 * 【修复 - 2026-03-20】保存诊断记录列表
 * @param {Array} historyList - 诊断记录列表
 */
function saveDiagnosisHistory(historyList) {
  try {
    if (!Array.isArray(historyList)) {
      console.warn('[Storage] 保存诊断记录列表失败：参数不是数组');
      return;
    }
    
    wx.setStorageSync(DIAGNOSIS_HISTORY_KEY, historyList);
    console.log(`[Storage] ✅ 诊断记录列表已保存，共 ${historyList.length} 条`);
  } catch (error) {
    console.error('[Storage] 保存诊断记录列表失败:', error);
  }
}

/**
 * 加载诊断结果
 * @param {string} executionId - 执行 ID
 * @returns {Object|null} 诊断数据，如果不存在或过期则返回 null
 */
function loadDiagnosisResult(executionId) {
  try {
    if (!executionId) {
      console.warn('[Storage] 加载失败：executionId 为空');
      return null;
    }

    // 优先从统一 key 加载
    const key = StorageKey.DIAGNOSIS_RESULT + executionId;
    const storageData = wx.getStorageSync(key);

    // 数据验证
    if (!storageData) {
      console.log(`[Storage] ℹ️  未找到诊断结果：${executionId}`);
      return null;
    }

    // 版本检查
    if (!storageData.version || storageData.version !== STORAGE_VERSION) {
      console.warn('[Storage] ⚠️  数据版本不匹配，清除旧数据');
      wx.removeStorageSync(key);
      return null;
    }

    // executionId 检查
    if (storageData.executionId !== executionId) {
      console.warn('[Storage] ⚠️  executionId 不匹配');
      return null;
    }

    // 过期检查
    const now = Date.now();
    if (now - storageData.timestamp > DATA_EXPIRY_TIME) {
      console.warn('[Storage] ⏰ 数据已过期，清除');
      wx.removeStorageSync(key);
      return null;
    }

    console.log(`[Storage] ✅ 诊断结果加载成功：${executionId}`);
    
    // 【首席工程师修复 - 2026-03-15】返回完整数据，包括元数据字段
    // 之前的设计只返回 storageData.data，导致丢失 brandName、executionId 等关键信息
    // 现在返回合并后的对象，确保详情页能正常访问所有字段
    return {
      // 元数据字段（详情页必需）
      executionId: storageData.executionId,
      brandName: storageData.brandName,
      completedAt: storageData.completedAt,
      timestamp: storageData.timestamp,
      version: storageData.version,
      
      // 诊断数据字段
      ...storageData.data,
      
      // 不返回 rawResponse，避免大数据量
      // rawResponse: storageData.rawResponse  // ❌ 排除，太大
    };
  } catch (error) {
    console.error('[Storage] 加载诊断结果失败:', error);
    return null;
  }
}

/**
 * 加载最后一次诊断结果（兼容旧逻辑）
 * @returns {Object|null} 诊断数据
 */
function loadLastDiagnosis() {
  try {
    const storageData = wx.getStorageSync(StorageKey.LAST_DIAGNOSIS);

    if (!storageData) {
      return null;
    }

    // 版本检查
    if (!storageData.version || storageData.version !== STORAGE_VERSION) {
      console.warn('[Storage] ⚠️  旧数据版本不匹配');
      wx.removeStorageSync(StorageKey.LAST_DIAGNOSIS);
      return null;
    }

    // 过期检查
    const now = Date.now();
    if (now - storageData.timestamp > DATA_EXPIRY_TIME) {
      console.warn('[Storage] ⏰ 最后诊断数据已过期');
      wx.removeStorageSync(StorageKey.LAST_DIAGNOSIS);
      return null;
    }

    return storageData;
  } catch (error) {
    console.error('[Storage] 加载最后诊断结果失败:', error);
    return null;
  }
}

/**
 * 清除诊断结果
 * @param {string} executionId - 执行 ID
 * @returns {boolean} 是否清除成功
 */
function clearDiagnosisResult(executionId) {
  try {
    if (executionId) {
      const key = StorageKey.DIAGNOSIS_RESULT + executionId;
      wx.removeStorageSync(key);
      console.log(`[Storage] ✅ 已清除诊断结果：${executionId}`);
    }
    return true;
  } catch (error) {
    console.error('[Storage] 清除诊断结果失败:', error);
    return false;
  }
}

/**
 * 批量清除诊断结果
 * @param {Array} executionIds - 执行 ID 列表
 * @returns {Object} 清除结果统计
 */
function batchClearDiagnosisResults(executionIds) {
  try {
    let successCount = 0;
    let failCount = 0;
    
    executionIds.forEach(id => {
      try {
        const key = StorageKey.DIAGNOSIS_RESULT + id;
        wx.removeStorageSync(key);
        successCount++;
        console.log(`[Storage] ✅ 已清除诊断结果：${id}`);
      } catch (error) {
        failCount++;
        console.warn(`[Storage] ⚠️  清除诊断结果失败：${id}`, error);
      }
    });
    
    return {
      successCount,
      failCount,
      totalCount: executionIds.length
    };
  } catch (error) {
    console.error('[Storage] 批量清除诊断结果失败:', error);
    return {
      successCount: 0,
      failCount: executionIds.length,
      totalCount: executionIds.length
    };
  }
}

/**
 * 获取所有本地诊断结果列表
 * @returns {Array} 本地诊断结果列表
 */
function getAllLocalDiagnosisResults() {
  try {
    const info = wx.getStorageInfoSync();
    const keys = info.keys || [];
    const results = [];
    
    keys.forEach(key => {
      if (key.startsWith(StorageKey.DIAGNOSIS_RESULT)) {
        try {
          const data = wx.getStorageSync(key);
          if (data && data.version === STORAGE_VERSION) {
            results.push({
              executionId: data.executionId,
              brandName: data.brandName,
              completedAt: data.completedAt,
              timestamp: data.timestamp,
              overallScore: data.data?.overallScore || 0,
              storageKey: key
            });
          }
        } catch (error) {
          console.warn(`[Storage] 读取诊断结果失败：${key}`, error);
        }
      }
    });
    
    // 按时间倒序排序
    results.sort((a, b) => b.timestamp - a.timestamp);
    
    return results;
  } catch (error) {
    console.error('[Storage] 获取所有诊断结果失败:', error);
    return [];
  }
}

/**
 * 获取 Storage 统计信息
 * @returns {Object} 统计信息
 */
function getStorageStats() {
  try {
    const info = wx.getStorageInfoSync();
    const keys = info.keys || [];

    const stats = {
      totalKeys: keys.length,
      diagnosisKeys: keys.filter(k => k.startsWith(StorageKey.DIAGNOSIS_RESULT)).length,
      lastDiagnosis: !!wx.getStorageSync(StorageKey.LAST_DIAGNOSIS),
      totalSize: info.currentSize || 0,
      sizeLimit: info.limitSize || 10240 // 默认 10MB
    };

    return stats;
  } catch (error) {
    console.error('[Storage] 获取统计信息失败:', error);
    return null;
  }
}

/**
 * 清理过期数据
 * @returns {number} 清理的数据条数
 */
function cleanupExpiredData() {
  try {
    const info = wx.getStorageInfoSync();
    const keys = info.keys || [];
    let cleanedCount = 0;
    const now = Date.now();

    keys.forEach(key => {
      // 只处理诊断结果相关的 key
      if (!key.startsWith(StorageKey.DIAGNOSIS_RESULT) && key !== StorageKey.LAST_DIAGNOSIS) {
        return;
      }

      try {
        const data = wx.getStorageSync(key);
        if (!data || !data.timestamp) {
          wx.removeStorageSync(key);
          cleanedCount++;
          return;
        }

        // 过期数据清除
        if (now - data.timestamp > DATA_EXPIRY_TIME) {
          wx.removeStorageSync(key);
          cleanedCount++;
          console.log(`[Storage] 🗑️  清理过期数据：${key}`);
        }
      } catch (error) {
        console.warn(`[Storage] 清理数据失败：${key}`, error);
      }
    });

    console.log(`[Storage] ✅ 清理完成，共清理 ${cleanedCount} 条数据`);
    return cleanedCount;
  } catch (error) {
    console.error('[Storage] 清理过期数据失败:', error);
    return 0;
  }
}

module.exports = {
  StorageKey,
  STORAGE_VERSION,
  DATA_EXPIRY_TIME,
  DIAGNOSIS_HISTORY_KEY,
  saveDiagnosisResult,
  loadDiagnosisResult,
  loadLastDiagnosis,
  clearDiagnosisResult,
  batchClearDiagnosisResults,
  getAllLocalDiagnosisResults,
  getStorageStats,
  getDiagnosisHistory,
  saveDiagnosisHistory,  // 【修复 - 2026-03-20】新增导出
  removeFromDiagnosisHistory,
  addToDiagnosisHistory,
  cleanupExpiredData
};
