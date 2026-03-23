/**
 * 基础存储工具模块
 * 
 * 功能：
 * - 诊断历史记录保存
 * - 配置信息保存
 * - 基础 CRUD 操作
 */

// 存储键名
const STORAGE_KEYS = {
  DIAGNOSIS_HISTORY: 'diagnosis_history',
  USER_CONFIG: 'user_config',
  STORAGE_META: 'storage_meta'
};

// 存储限制配置
const STORAGE_CONFIG = {
  MAX_SIZE_MB: 10,
  WARNING_THRESHOLD: 0.8,
  AUTO_CLEAN_DAYS: 30,
  MAX_HISTORY_COUNT: 100
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
 * 存储工具类
 */
class StorageUtil {
  /**
   * 检查存储空间使用情况
   */
  static async checkStorageUsage() {
    try {
      const info = await wx.getStorageInfo();
      const currentSize = info.currentSize || 0;
      const limitSize = STORAGE_CONFIG.MAX_SIZE_MB * 1024;
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
        isWarning: false
      };
    }
  }

  /**
   * 保存诊断记录
   */
  static async saveDiagnosisRecord(record) {
    try {
      const history = await this.getDiagnosisHistory();
      
      // 添加到列表开头
      history.unshift({
        ...record,
        savedAt: Date.now()
      });

      // 限制数量
      if (history.length > STORAGE_CONFIG.MAX_HISTORY_COUNT) {
        history.splice(STORAGE_CONFIG.MAX_HISTORY_COUNT);
      }

      wx.setStorageSync(STORAGE_KEYS.DIAGNOSIS_HISTORY, history);
      console.log('诊断记录已保存');
      
      return true;
    } catch (error) {
      console.error('保存诊断记录失败:', error);
      return false;
    }
  }

  /**
   * 获取诊断历史
   */
  static async getDiagnosisHistory(limit = 20) {
    try {
      const history = wx.getStorageSync(STORAGE_KEYS.DIAGNOSIS_HISTORY) || [];
      return history.slice(0, limit);
    } catch (error) {
      console.error('获取诊断历史失败:', error);
      return [];
    }
  }

  /**
   * 获取单条诊断记录
   */
  static getDiagnosisRecord(executionId) {
    try {
      const history = wx.getStorageSync(STORAGE_KEYS.DIAGNOSIS_HISTORY) || [];
      return history.find(item => item.executionId === executionId) || null;
    } catch (error) {
      console.error('获取诊断记录失败:', error);
      return null;
    }
  }

  /**
   * 删除诊断记录
   */
  static deleteDiagnosisRecord(executionId) {
    try {
      const history = wx.getStorageSync(STORAGE_KEYS.DIAGNOSIS_HISTORY) || [];
      const filtered = history.filter(item => item.executionId !== executionId);
      wx.setStorageSync(STORAGE_KEYS.DIAGNOSIS_HISTORY, filtered);
      return true;
    } catch (error) {
      console.error('删除诊断记录失败:', error);
      return false;
    }
  }

  /**
   * 保存用户配置
   */
  static saveUserConfig(config) {
    try {
      wx.setStorageSync(STORAGE_KEYS.USER_CONFIG, {
        ...config,
        updatedAt: Date.now()
      });
      console.log('用户配置已保存');
      return true;
    } catch (error) {
      console.error('保存用户配置失败:', error);
      return false;
    }
  }

  /**
   * 获取用户配置
   */
  static getUserConfig() {
    try {
      return wx.getStorageSync(STORAGE_KEYS.USER_CONFIG) || {};
    } catch (error) {
      console.error('获取用户配置失败:', error);
      return {};
    }
  }

  /**
   * 通用保存方法
   */
  static save(key, data) {
    try {
      wx.setStorageSync(key, {
        data,
        timestamp: Date.now()
      });
      return true;
    } catch (error) {
      console.error('保存数据失败:', error);
      return false;
    }
  }

  /**
   * 通用获取方法
   */
  static get(key) {
    try {
      const stored = wx.getStorageSync(key);
      return stored ? stored.data : null;
    } catch (error) {
      console.error('获取数据失败:', error);
      return null;
    }
  }

  /**
   * 通用删除方法
   */
  static remove(key) {
    try {
      wx.removeStorageSync(key);
      return true;
    } catch (error) {
      console.error('删除数据失败:', error);
      return false;
    }
  }

  /**
   * 清空所有存储
   */
  static clear() {
    try {
      wx.clearStorageSync();
      console.log('已清空所有存储');
      return true;
    } catch (error) {
      console.error('清空存储失败:', error);
      return false;
    }
  }
}

module.exports = {
  StorageUtil,
  STORAGE_KEYS,
  STORAGE_CONFIG,
  formatBytes
};
