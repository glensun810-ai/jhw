/**
 * 缓存管理工具类
 * 
 * 提供缓存操作的便捷方法
 */

const cacheConfig = require('./config/cacheConfig');

/**
 * 缓存管理器
 */
class CacheManager {
  constructor() {
    this.cacheVersion = cacheConfig.CACHE_CONFIG.version;
    this.prefix = cacheConfig.CACHE_CONFIG.prefix;
  }

  /**
   * 设置缓存
   * @param {string} key - 缓存键
   * @param {any} data - 缓存数据
   * @param {Object} options - 选项
   * @returns {Promise<boolean>} 是否成功
   */
  async set(key, data, options = {}) {
    try {
      const {
        type = 'temp',
        expiration = null
      } = options;

      const cacheData = {
        data,
        timestamp: Date.now(),
        expiration: expiration || cacheConfig.getCacheExpiration(type)
      };

      wx.setStorageSync(key, JSON.stringify(cacheData));
      console.log('[Cache] 设置缓存:', key);
      return true;
    } catch (error) {
      console.error('[Cache] 设置缓存失败:', key, error);
      return false;
    }
  }

  /**
   * 获取缓存
   * @param {string} key - 缓存键
   * @param {Object} options - 选项
   * @returns {Promise<any>} 缓存数据，如果不存在或已过期则返回 null
   */
  async get(key, options = {}) {
    try {
      const { checkExpiration = true } = options;

      const cacheDataStr = wx.getStorageSync(key);
      if (!cacheDataStr) {
        return null;
      }

      const cacheData = JSON.parse(cacheDataStr);

      // 检查是否过期
      if (checkExpiration) {
        const now = Date.now();
        const isExpired = now - cacheData.timestamp > cacheData.expiration;

        if (isExpired) {
          console.log('[Cache] 缓存已过期:', key);
          this.remove(key);
          return null;
        }
      }

      console.log('[Cache] 获取缓存:', key);
      return cacheData.data;
    } catch (error) {
      console.error('[Cache] 获取缓存失败:', key, error);
      return null;
    }
  }

  /**
   * 删除缓存
   * @param {string} key - 缓存键
   * @returns {Promise<boolean>} 是否成功
   */
  async remove(key) {
    try {
      wx.removeStorageSync(key);
      console.log('[Cache] 删除缓存:', key);
      return true;
    } catch (error) {
      console.error('[Cache] 删除缓存失败:', key, error);
      return false;
    }
  }

  /**
   * 清空所有缓存
   * @returns {Promise<boolean>} 是否成功
   */
  async clear() {
    try {
      wx.clearStorageSync();
      console.log('[Cache] 清空所有缓存');
      return true;
    } catch (error) {
      console.error('[Cache] 清空缓存失败:', error);
      return false;
    }
  }

  /**
   * 批量设置缓存
   * @param {Array<Object>} items - 缓存项数组 [{key, data, options}]
   * @returns {Promise<Object>} 结果统计
   */
  async setBatch(items) {
    const results = {
      success: 0,
      failed: 0,
      errors: []
    };

    for (const item of items) {
      const { key, data, options } = item;
      const success = await this.set(key, data, options);

      if (success) {
        results.success++;
      } else {
        results.failed++;
        results.errors.push(key);
      }
    }

    return results;
  }

  /**
   * 批量获取缓存
   * @param {Array<string>} keys - 缓存键数组
   * @returns {Promise<Object>} 缓存数据对象
   */
  async getBatch(keys) {
    const results = {};

    for (const key of keys) {
      results[key] = await this.get(key);
    }

    return results;
  }

  /**
   * 批量删除缓存
   * @param {Array<string>} keys - 缓存键数组
   * @returns {Promise<Object>} 结果统计
   */
  async removeBatch(keys) {
    const results = {
      success: 0,
      failed: 0,
      errors: []
    };

    for (const key of keys) {
      const success = await this.remove(key);

      if (success) {
        results.success++;
      } else {
        results.failed++;
        results.errors.push(key);
      }
    }

    return results;
  }

  /**
   * 获取所有缓存键
   * @returns {Promise<Array<string>>} 缓存键数组
   */
  async keys() {
    try {
      // 微信小程序没有直接获取所有 key 的方法
      // 需要应用自己维护 key 列表
      return wx.getStorageSync('cache_keys') || [];
    } catch (error) {
      console.error('[Cache] 获取缓存键失败:', error);
      return [];
    }
  }

  /**
   * 注册缓存键（用于追踪）
   * @param {string} key - 缓存键
   */
  async registerKey(key) {
    try {
      const keys = await this.keys();
      if (!keys.includes(key)) {
        keys.push(key);
        wx.setStorageSync('cache_keys', JSON.stringify(keys));
      }
    } catch (error) {
      console.error('[Cache] 注册缓存键失败:', error);
    }
  }

  /**
   * 检查缓存是否存在
   * @param {string} key - 缓存键
   * @returns {Promise<boolean>} 是否存在
   */
  async has(key) {
    const data = await this.get(key, { checkExpiration: false });
    return data !== null;
  }

  /**
   * 获取缓存信息
   * @param {string} key - 缓存键
   * @returns {Promise<Object|null>} 缓存信息
   */
  async info(key) {
    try {
      const cacheDataStr = wx.getStorageSync(key);
      if (!cacheDataStr) {
        return null;
      }

      const cacheData = JSON.parse(cacheDataStr);
      const now = Date.now();
      const age = now - cacheData.timestamp;
      const remaining = cacheData.expiration - age;

      return {
        key,
        timestamp: cacheData.timestamp,
        expiration: cacheData.expiration,
        age,
        remaining,
        isExpired: remaining <= 0
      };
    } catch (error) {
      console.error('[Cache] 获取缓存信息失败:', key, error);
      return null;
    }
  }

  /**
   * 刷新缓存（重新设置过期时间）
   * @param {string} key - 缓存键
   * @param {Object} options - 选项
   * @returns {Promise<boolean>} 是否成功
   */
  async refresh(key, options = {}) {
    const data = await this.get(key, { checkExpiration: false });
    if (data === null) {
      return false;
    }

    return await this.set(key, data, options);
  }
}

// 导出单例
const cacheManager = new CacheManager();
module.exports = cacheManager;
