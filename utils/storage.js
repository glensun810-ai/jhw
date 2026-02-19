/**
 * 本地存储工具模块
 *
 * 功能:
 * 1. 诊断历史记录保存
 * 2. 配置信息保存
 * 3. 存储容量管理
 * 4. 自动清理机制
 *
 * 存储限制:
 * - 微信小程序总存储上限：10MB
 * - 建议阈值：8MB (80%)
 * - 自动清理：30 天以上记录
 *
 * 使用示例:
 * const storage = require('../../utils/storage');
 *
 * // 保存诊断记录
 * await storage.saveDiagnosisRecord(record);
 *
 * // 获取历史记录
 * const history = await storage.getDiagnosisHistory();
 *
 * // 检查存储空间
 * const usage = await storage.checkStorageUsage();
 * if (usage.percent > 80) {
 *   // 提醒用户清理
 * }
 */

// 存储键名
const STORAGE_KEYS = {
  DIAGNOSIS_HISTORY: 'diagnosis_history',  // 诊断历史记录
  USER_CONFIG: 'user_config',              // 用户配置
  STORAGE_META: 'storage_meta'             // 存储元数据
};

// 存储限制配置
const STORAGE_CONFIG = {
  MAX_SIZE_MB: 10,              // 微信小程序总存储上限 10MB
  WARNING_THRESHOLD: 0.8,       // 警告阈值 80%
  AUTO_CLEAN_DAYS: 30,          // 自动清理 30 天以上记录
  MAX_HISTORY_COUNT: 100        // 最多保存 100 条历史记录
};

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
 * 获取当前时间戳
 */
function now() {
  return Date.now();
}

/**
 * 计算过期时间戳
 */
function expireAfterDays(days) {
  return now() - (days * 24 * 60 * 60 * 1000);
}

/**
 * 本地存储工具类
 */
class StorageUtil {
  /**
   * 检查存储空间使用情况
   * @returns {Promise<Object>} 存储使用信息
   */
  static async checkStorageUsage() {
    try {
      const info = await wx.getStorageInfo();
      const currentSize = info.currentSize || 0; // KB
      const limitSize = STORAGE_CONFIG.MAX_SIZE_MB * 1024; // KB
      const percent = currentSize / limitSize;

      return {
        currentSize: formatBytes(currentSize * 1024),
        limitSize: formatBytes(limitSize * 1024),
        percent: Math.round(percent * 100),
        isWarning: percent >= STORAGE_CONFIG.WARNING_THRESHOLD,
        raw: info
      };
    } catch (error) {
      console.error('检查存储空间失败:', error);
      return {
        currentSize: '未知',
        limitSize: formatBytes(STORAGE_CONFIG.MAX_SIZE_MB * 1024 * 1024),
        percent: 0,
        isWarning: false,
        raw: null
      };
    }
  }

  /**
   * 保存诊断记录
   * @param {Object} record - 诊断记录
   * @returns {Promise<boolean>} 是否保存成功
   */
  static async saveDiagnosisRecord(record) {
    try {
      // 添加元数据
      const recordWithMeta = {
        ...record,
        id: this._generateId(),
        createdAt: now(),
        updatedAt: now(),
        version: 1
      };

      // 获取现有历史记录
      const history = await this.getDiagnosisHistory();

      // 添加到历史记录
      history.unshift(recordWithMeta);

      // 限制历史记录数量
      if (history.length > STORAGE_CONFIG.MAX_HISTORY_COUNT) {
        history.splice(STORAGE_CONFIG.MAX_HISTORY_COUNT);
      }

      // 保存到本地存储
      await wx.setStorage({
        key: STORAGE_KEYS.DIAGNOSIS_HISTORY,
        data: history
      });

      console.log('诊断记录保存成功:', recordWithMeta.id);
      return true;

    } catch (error) {
      console.error('保存诊断记录失败:', error);

      // 如果存储空间不足，尝试清理后重试
      if (error.errMsg && error.errMsg.includes('exceeded')) {
        console.log('存储空间不足，尝试清理...');
        await this.autoClean();

        // 重试保存
        try {
          const history = await this.getDiagnosisHistory();
          history.unshift({
            ...record,
            id: this._generateId(),
            createdAt: now(),
            updatedAt: now(),
            version: 1
          });

          await wx.setStorage({
            key: STORAGE_KEYS.DIAGNOSIS_HISTORY,
            data: history
          });

          return true;
        } catch (retryError) {
          console.error('重试保存失败:', retryError);
          return false;
        }
      }

      return false;
    }
  }

  /**
   * 获取诊断历史记录
   * @param {Object} options - 查询选项
   * @returns {Promise<Array>} 历史记录列表
   */
  static async getDiagnosisHistory(options = {}) {
    try {
      const { limit = 50, offset = 0, days = null } = options;

      const res = await wx.getStorage({
        key: STORAGE_KEYS.DIAGNOSIS_HISTORY
      });

      let history = res.data || [];

      // 按时间筛选
      if (days) {
        const expireTime = expireAfterDays(days);
        history = history.filter(item => item.createdAt >= expireTime);
      }

      // 分页
      return history.slice(offset, offset + limit);

    } catch (error) {
      // 如果没有历史记录，返回空数组
      if (error.errMsg && error.errMsg.includes('data not found')) {
        return [];
      }

      console.error('获取诊断历史失败:', error);
      return [];
    }
  }

  /**
   * 获取单条诊断记录
   * @param {string} id - 记录 ID
   * @returns {Promise<Object|null>} 诊断记录
   */
  static async getDiagnosisRecord(id) {
    try {
      const history = await this.getDiagnosisHistory({ limit: 1000 });
      return history.find(item => item.id === id) || null;
    } catch (error) {
      console.error('获取诊断记录失败:', error);
      return null;
    }
  }

  /**
   * 删除诊断记录
   * @param {string} id - 记录 ID
   * @returns {Promise<boolean>} 是否删除成功
   */
  static async deleteDiagnosisRecord(id) {
    try {
      const history = await this.getDiagnosisHistory({ limit: 1000 });
      const newHistory = history.filter(item => item.id !== id);

      await wx.setStorage({
        key: STORAGE_KEYS.DIAGNOSIS_HISTORY,
        data: newHistory
      });

      console.log('诊断记录删除成功:', id);
      return true;
    } catch (error) {
      console.error('删除诊断记录失败:', error);
      return false;
    }
  }

  /**
   * 保存用户配置
   * @param {Object} config - 配置信息
   * @returns {Promise<boolean>} 是否保存成功
   */
  static async saveUserConfig(config) {
    try {
      const configWithMeta = {
        ...config,
        updatedAt: now()
      };

      await wx.setStorage({
        key: STORAGE_KEYS.USER_CONFIG,
        data: configWithMeta
      });

      console.log('用户配置保存成功');
      return true;
    } catch (error) {
      console.error('保存用户配置失败:', error);
      return false;
    }
  }

  /**
   * 获取用户配置
   * @returns {Promise<Object>} 配置信息
   */
  static async getUserConfig() {
    try {
      const res = await wx.getStorage({
        key: STORAGE_KEYS.USER_CONFIG
      });
      return res.data || {};
    } catch (error) {
      // 如果没有配置，返回默认配置
      if (error.errMsg && error.errMsg.includes('data not found')) {
        return this._getDefaultConfig();
      }

      console.error('获取用户配置失败:', error);
      return this._getDefaultConfig();
    }
  }

  /**
   * 自动清理过期记录
   * @returns {Promise<Object>} 清理结果
   */
  static async autoClean() {
    try {
      const history = await this.getDiagnosisHistory({ limit: 1000 });
      const expireTime = expireAfterDays(STORAGE_CONFIG.AUTO_CLEAN_DAYS);

      // 过滤出过期记录
      const expiredRecords = history.filter(item => item.createdAt < expireTime);
      const validRecords = history.filter(item => item.createdAt >= expireTime);

      if (expiredRecords.length > 0) {
        // 保存有效记录
        await wx.setStorage({
          key: STORAGE_KEYS.DIAGNOSIS_HISTORY,
          data: validRecords
        });

        console.log(`自动清理完成：清理${expiredRecords.length}条过期记录`);

        return {
          success: true,
          cleanedCount: expiredRecords.length,
          remainingCount: validRecords.length
        };
      }

      return {
        success: true,
        cleanedCount: 0,
        remainingCount: history.length
      };

    } catch (error) {
      console.error('自动清理失败:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * 手动清理所有历史记录
   * @returns {Promise<boolean>} 是否清理成功
   */
  static async clearAllHistory() {
    try {
      await wx.removeStorage({
        key: STORAGE_KEYS.DIAGNOSIS_HISTORY
      });

      console.log('所有历史记录已清理');
      return true;
    } catch (error) {
      console.error('清理历史记录失败:', error);
      return false;
    }
  }

  /**
   * 获取存储统计信息
   * @returns {Promise<Object>} 统计信息
   */
  static async getStorageStats() {
    try {
      const usage = await this.checkStorageUsage();
      const history = await this.getDiagnosisHistory({ limit: 1000 });

      // 按日期分组统计
      const statsByDate = {};
      history.forEach(item => {
        const date = new Date(item.createdAt).toISOString().split('T')[0];
        if (!statsByDate[date]) {
          statsByDate[date] = {
            date,
            count: 0,
            brands: new Set()
          };
        }
        statsByDate[date].count++;
        if (item.summary?.brandName) {
          statsByDate[date].brands.add(item.summary.brandName);
        }
      });

      // 转换为数组
      const statsArray = Object.values(statsByDate).map(item => ({
        ...item,
        brandCount: item.brands.size,
        brands: Array.from(item.brands)
      })).sort((a, b) => b.date.localeCompare(a.date));

      return {
        storage: usage,
        history: {
          totalCount: history.length,
          recentStats: statsArray.slice(0, 7)  // 最近 7 天
        }
      };
    } catch (error) {
      console.error('获取存储统计失败:', error);
      return null;
    }
  }

  /**
   * 对比两条诊断记录
   * @param {string} id1 - 记录 ID 1
   * @param {string} id2 - 记录 ID 2
   * @returns {Promise<Object>} 对比结果
   */
  static async compareRecords(id1, id2) {
    try {
      const record1 = await this.getDiagnosisRecord(id1);
      const record2 = await this.getDiagnosisRecord(id2);

      if (!record1 || !record2) {
        return {
          success: false,
          error: '记录不存在'
        };
      }

      const summary1 = record1.summary || {};
      const summary2 = record2.summary || {};

      return {
        success: true,
        comparison: {
          record1: {
            id: record1.id,
            date: new Date(record1.createdAt).toLocaleDateString(),
            brand: summary1.brandName,
            healthScore: summary1.healthScore,
            sov: summary1.sov,
            avgSentiment: summary1.avgSentiment
          },
          record2: {
            id: record2.id,
            date: new Date(record2.createdAt).toLocaleDateString(),
            brand: summary2.brandName,
            healthScore: summary2.healthScore,
            sov: summary2.sov,
            avgSentiment: summary2.avgSentiment
          },
          diff: {
            healthScore: (summary2.healthScore || 0) - (summary1.healthScore || 0),
            sov: (summary2.sov || 0) - (summary1.sov || 0),
            avgSentiment: parseFloat(summary2.avgSentiment || 0) - parseFloat(summary1.avgSentiment || 0)
          }
        }
      };
    } catch (error) {
      console.error('对比记录失败:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * 生成唯一 ID
   * @private
   * @returns {string} 唯一 ID
   */
  static _generateId() {
    return 'diag_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  /**
   * 获取默认配置
   * @private
   * @returns {Object} 默认配置
   */
  static _getDefaultConfig() {
    return {
      autoClean: true,           // 自动清理
      cleanDays: 30,             // 清理天数
      maxHistory: 100,           // 最大历史记录数
      notifyThreshold: 80,       // 存储警告阈值 (%)
      createdAt: now()
    };
  }
}

module.exports = StorageUtil;
