/**
 * 缓存管理工具模块
 * 
 * 功能：
 * - 带过期时间的缓存
 * - 自动清理机制
 * - 缓存统计
 */

// 缓存配置
const CACHE_CONFIG = {
  DEFAULT_TTL_HOURS: 24,        // 默认过期时间 24 小时
  MAX_CACHE_SIZE_MB: 5,         // 最大缓存大小 5MB
  AUTO_CLEAN_DAYS: 7            // 自动清理 7 天以上缓存
};

// 缓存键前缀
const CACHE_PREFIX = 'cache_';

/**
 * 格式化字节数
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * 缓存管理工具类
 */
class CacheUtil {
  /**
   * 设置缓存（带过期时间）
   */
  static set(key, data, ttlHours = CACHE_CONFIG.DEFAULT_TTL_HOURS) {
    try {
      const cacheKey = CACHE_PREFIX + key;
      const expiresAt = Date.now() + (ttlHours * 60 * 60 * 1000);
      
      wx.setStorageSync(cacheKey, {
        data,
        expiresAt,
        createdAt: Date.now()
      });
      
      console.log(`缓存已设置：${key}, 过期时间：${ttlHours}小时`);
      return true;
    } catch (error) {
      console.error('设置缓存失败:', error);
      return false;
    }
  }

  /**
   * 获取缓存
   */
  static get(key) {
    try {
      const cacheKey = CACHE_PREFIX + key;
      const cached = wx.getStorageSync(cacheKey);
      
      if (!cached) {
        return null;
      }

      // 检查是否过期
      if (cached.expiresAt && Date.now() > cached.expiresAt) {
        this.remove(key);
        return null;
      }

      return cached.data;
    } catch (error) {
      console.error('获取缓存失败:', error);
      return null;
    }
  }

  /**
   * 删除缓存
   */
  static remove(key) {
    try {
      const cacheKey = CACHE_PREFIX + key;
      wx.removeStorageSync(cacheKey);
      return true;
    } catch (error) {
      console.error('删除缓存失败:', error);
      return false;
    }
  }

  /**
   * 清空所有缓存
   */
  static clear() {
    try {
      const info = wx.getStorageInfo();
      const keys = info.keys || [];
      
      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          wx.removeStorageSync(key);
        }
      });
      
      console.log('已清空所有缓存');
      return true;
    } catch (error) {
      console.error('清空缓存失败:', error);
      return false;
    }
  }

  /**
   * 清理过期缓存
   */
  static cleanExpired() {
    try {
      const info = wx.getStorageInfo();
      const keys = info.keys || [];
      let cleaned = 0;

      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          try {
            const cached = wx.getStorageSync(key);
            if (cached && cached.expiresAt && Date.now() > cached.expiresAt) {
              wx.removeStorageSync(key);
              cleaned++;
            }
          } catch (e) {
            // 忽略单个缓存清理错误
          }
        }
      });

      if (cleaned > 0) {
        console.log(`清理了 ${cleaned} 个过期缓存`);
      }
      
      return cleaned;
    } catch (error) {
      console.error('清理过期缓存失败:', error);
      return 0;
    }
  }

  /**
   * 清理旧缓存（按时间）
   */
  static cleanOldCache(days = CACHE_CONFIG.AUTO_CLEAN_DAYS) {
    try {
      const info = wx.getStorageInfo();
      const keys = info.keys || [];
      const threshold = Date.now() - (days * 24 * 60 * 60 * 1000);
      let cleaned = 0;

      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          try {
            const cached = wx.getStorageSync(key);
            if (cached && cached.createdAt && cached.createdAt < threshold) {
              wx.removeStorageSync(key);
              cleaned++;
            }
          } catch (e) {
            // 忽略单个缓存清理错误
          }
        }
      });

      if (cleaned > 0) {
        console.log(`清理了 ${cleaned} 个旧缓存（>${days}天）`);
      }
      
      return cleaned;
    } catch (error) {
      console.error('清理旧缓存失败:', error);
      return 0;
    }
  }

  /**
   * 获取缓存统计信息
   */
  static getCacheStats() {
    try {
      const info = wx.getStorageInfo();
      const keys = info.keys || [];
      
      let cacheCount = 0;
      let cacheSize = 0;
      let expiredCount = 0;

      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          cacheCount++;
          
          try {
            const cached = wx.getStorageSync(key);
            if (cached) {
              // 估算大小
              const size = JSON.stringify(cached).length;
              cacheSize += size;
              
              // 检查是否过期
              if (cached.expiresAt && Date.now() > cached.expiresAt) {
                expiredCount++;
              }
            }
          } catch (e) {
            // 忽略单个缓存统计错误
          }
        }
      });

      return {
        count: cacheCount,
        size: formatBytes(cacheSize),
        sizeBytes: cacheSize,
        expiredCount,
        validCount: cacheCount - expiredCount
      };
    } catch (error) {
      console.error('获取缓存统计失败:', error);
      return {
        count: 0,
        size: '0 B',
        sizeBytes: 0,
        expiredCount: 0,
        validCount: 0
      };
    }
  }

  /**
   * 检查缓存空间
   */
  static checkCacheSpace() {
    try {
      const info = wx.getStorageInfo();
      const currentSize = info.currentSize || 0; // KB
      const limitSize = CACHE_CONFIG.MAX_CACHE_SIZE_MB * 1024; // KB
      const percent = currentSize / limitSize;

      return {
        currentSize: formatBytes(currentSize * 1024),
        limitSize: formatBytes(limitSize * 1024),
        percent: Math.round(percent * 100),
        isWarning: percent >= 0.8
      };
    } catch (error) {
      console.error('检查缓存空间失败:', error);
      return {
        currentSize: '未知',
        limitSize: formatBytes(CACHE_CONFIG.MAX_CACHE_SIZE_MB * 1024 * 1024),
        percent: 0,
        isWarning: false
      };
    }
  }

  /**
   * 自动清理（推荐定期调用）
   */
  static autoClean() {
    const expiredCleaned = this.cleanExpired();
    const oldCleaned = this.cleanOldCache();
    return expiredCleaned + oldCleaned;
  }
}

module.exports = {
  CacheUtil,
  CACHE_CONFIG,
  CACHE_PREFIX,
  formatBytes
};
