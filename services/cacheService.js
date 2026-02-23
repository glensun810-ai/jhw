/**
 * 诊断结果缓存服务
 * P2 优化：避免重复诊断，提升用户体验
 */

// 缓存配置
const CACHE_CONFIG = {
  STORAGE_KEY: 'diagnosis_cache_',
  EXPIRY_TIME: 24 * 60 * 60 * 1000,  // 24 小时缓存
  MAX_CACHE_SIZE: 50,  // 最多缓存 50 个结果
  CLEANUP_THRESHOLD: 10  // 超过此数量时清理最旧的缓存
};

/**
 * 生成缓存键
 * @param {string} brandName - 品牌名称
 * @param {Array} models - 模型列表
 * @param {Array} questions - 问题列表
 * @returns {string} 缓存键
 */
const generateCacheKey = (brandName, models, questions) => {
  const modelsHash = Array.isArray(models) ? models.sort().join(',') : '';
  const questionsHash = Array.isArray(questions) ? questions.sort().join('|') : '';
  const hash = `${brandName}|${modelsHash}|${questionsHash}`;
  
  // 使用简单的 hash 算法生成短键
  let hashValue = 0;
  for (let i = 0; i < hash.length; i++) {
    hashValue = ((hashValue << 5) - hashValue) + hash.charCodeAt(i);
    hashValue = hashValue & hashValue; // Convert to 32bit integer
  }
  
  return `${CACHE_CONFIG.STORAGE_KEY}${Math.abs(hashValue).toString(16)}`;
};

/**
 * 获取缓存的诊断结果
 * @param {string} brandName - 品牌名称
 * @param {Array} models - 模型列表
 * @param {Array} questions - 问题列表
 * @returns {Object|null} 缓存的数据，如果不存在或已过期则返回 null
 */
const getCachedDiagnosis = (brandName, models, questions) => {
  try {
    const cacheKey = generateCacheKey(brandName, models, questions);
    const cached = wx.getStorageSync(cacheKey);
    
    if (!cached || !cached.timestamp) {
      return null;
    }
    
    // 检查是否过期
    const now = Date.now();
    const cacheAge = now - cached.timestamp;
    
    if (cacheAge >= CACHE_CONFIG.EXPIRY_TIME) {
      console.log('缓存已过期，清除');
      wx.removeStorageSync(cacheKey);
      return null;
    }
    
    console.log(`使用缓存数据，剩余有效期：${Math.round((CACHE_CONFIG.EXPIRY_TIME - cacheAge) / 1000 / 60)}分钟`);
    return cached.data;
  } catch (e) {
    console.error('获取缓存失败:', e);
    return null;
  }
};

/**
 * 保存诊断结果到缓存
 * @param {string} brandName - 品牌名称
 * @param {Array} models - 模型列表
 * @param {Array} questions - 问题列表
 * @param {Object} data - 要缓存的数据
 * @returns {boolean} 是否保存成功
 */
const cacheDiagnosis = (brandName, models, questions, data) => {
  try {
    const cacheKey = generateCacheKey(brandName, models, questions);
    const cacheEntry = {
      timestamp: Date.now(),
      data: data,
      brandName: brandName,
      models: models,
      questions: questions
    };
    
    wx.setStorageSync(cacheKey, cacheEntry);
    
    // 检查缓存大小，如果超出限制则清理
    cleanupCache();
    
    console.log('诊断结果已缓存');
    return true;
  } catch (e) {
    console.error('保存缓存失败:', e);
    return false;
  }
};

/**
 * 清理缓存
 * @returns {number} 清理的缓存数量
 */
const cleanupCache = () => {
  try {
    // 获取所有缓存键
    const info = wx.getStorageInfoSync();
    const cacheKeys = info.keys.filter(key => key.startsWith(CACHE_CONFIG.STORAGE_KEY));
    
    if (cacheKeys.length <= CACHE_CONFIG.MAX_CACHE_SIZE) {
      return 0;
    }
    
    // 读取所有缓存，按时间排序
    const caches = cacheKeys.map(key => {
      try {
        const cached = wx.getStorageSync(key);
        return {
          key,
          timestamp: cached?.timestamp || 0
        };
      } catch (e) {
        return { key, timestamp: 0 };
      }
    });
    
    // 按时间排序，删除最旧的
    caches.sort((a, b) => a.timestamp - b.timestamp);
    const toDelete = caches.slice(0, CACHE_CONFIG.CLEANUP_THRESHOLD);
    
    toDelete.forEach(item => {
      try {
        wx.removeStorageSync(item.key);
      } catch (e) {
        console.error(`清理缓存失败 ${item.key}:`, e);
      }
    });
    
    console.log(`清理了 ${toDelete.length} 个过期缓存`);
    return toDelete.length;
  } catch (e) {
    console.error('清理缓存失败:', e);
    return 0;
  }
};

/**
 * 清除所有诊断缓存
 */
const clearAllCache = () => {
  try {
    const info = wx.getStorageInfoSync();
    const cacheKeys = info.keys.filter(key => key.startsWith(CACHE_CONFIG.STORAGE_KEY));
    
    cacheKeys.forEach(key => {
      wx.removeStorageSync(key);
    });
    
    console.log(`已清除所有诊断缓存，共 ${cacheKeys.length} 个`);
    return cacheKeys.length;
  } catch (e) {
    console.error('清除所有缓存失败:', e);
    return 0;
  }
};

/**
 * 获取缓存统计信息
 * @returns {Object} 统计信息
 */
const getCacheStats = () => {
  try {
    const info = wx.getStorageInfoSync();
    const cacheKeys = info.keys.filter(key => key.startsWith(CACHE_CONFIG.STORAGE_KEY));
    
    let totalSize = 0;
    let oldestTime = Date.now();
    let newestTime = 0;
    
    cacheKeys.forEach(key => {
      try {
        const cached = wx.getStorageSync(key);
        if (cached?.timestamp) {
          oldestTime = Math.min(oldestTime, cached.timestamp);
          newestTime = Math.max(newestTime, cached.timestamp);
        }
      } catch (e) {
        // Ignore
      }
    });
    
    return {
      count: cacheKeys.length,
      maxSize: CACHE_CONFIG.MAX_CACHE_SIZE,
      oldest: oldestTime < Date.now() ? new Date(oldestTime).toISOString() : 'N/A',
      newest: newestTime > 0 ? new Date(newestTime).toISOString() : 'N/A',
      expiryHours: CACHE_CONFIG.EXPIRY_TIME / 1000 / 60 / 60
    };
  } catch (e) {
    console.error('获取缓存统计失败:', e);
    return null;
  }
};

/**
 * 检查缓存是否命中
 * @param {string} brandName - 品牌名称
 * @param {Array} models - 模型列表
 * @param {Array} questions - 问题列表
 * @returns {boolean}
 */
const isCacheHit = (brandName, models, questions) => {
  const cached = getCachedDiagnosis(brandName, models, questions);
  return cached !== null;
};

module.exports = {
  CACHE_CONFIG,
  getCachedDiagnosis,
  cacheDiagnosis,
  cleanupCache,
  clearAllCache,
  getCacheStats,
  isCacheHit,
  generateCacheKey
};
