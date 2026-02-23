/**
 * DS-P2-1: Storage 完整性校验工具
 * 
 * 功能：
 * 1. CRC32 校验和计算
 * 2. 数据版本管理
 * 3. 自动修复（从备份恢复）
 * 4. 数据完整性验证
 * 
 * 使用方法:
 * const { saveWithChecksum, loadWithValidation } = require('./storage-validator');
 * 
 * // 保存数据
 * saveWithChecksum('diagnosis_result_xxx', data);
 * 
 * // 加载数据
 * const result = loadWithValidation('diagnosis_result_xxx');
 * if (result.valid) {
 *   console.log('数据完整', result.data);
 * } else {
 *   console.warn('数据可能已损坏');
 * }
 */

const STORAGE_VERSION = '2.0';

/**
 * 简单 CRC32 实现
 * @param {string} str - 输入字符串
 * @returns {number} CRC32 值
 */
function crc32(str) {
  let crc = 0xFFFFFFFF;
  const table = [];
  
  // 生成 CRC 表
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }
  
  // 计算 CRC
  for (let i = 0; i < str.length; i++) {
    crc = table[(crc ^ str.charCodeAt(i)) & 0xFF] ^ (crc >>> 8);
  }
  
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

/**
 * 计算校验和
 * @param {any} data - 要校验的数据
 * @returns {string} 校验和字符串
 */
function calculateChecksum(data) {
  const json = JSON.stringify(data);
  const crc = crc32(json);
  return crc.toString(16);
}

/**
 * 保存数据（带校验和）
 * @param {string} key - Storage key
 * @param {any} data - 要保存的数据
 * @param {Object} options - 选项
 * @returns {boolean} 是否保存成功
 */
function saveWithChecksum(key, data, options = {}) {
  try {
    const checksum = calculateChecksum(data);
    
    const storageData = {
      version: options.version || STORAGE_VERSION,
      timestamp: Date.now(),
      checksum: checksum,
      data: data,
      backup: options.backup || false
    };
    
    wx.setStorageSync(key, storageData);
    
    // 如果需要备份
    if (options.backup) {
      const backupKey = key + '_backup';
      wx.setStorageSync(backupKey, storageData);
    }
    
    console.log(`[Storage] ✅ 数据已保存：${key}, checksum: ${checksum}`);
    return true;
    
  } catch (error) {
    console.error(`[Storage] ❌ 保存失败：${key}`, error);
    return false;
  }
}

/**
 * 加载数据（带验证）
 * @param {string} key - Storage key
 * @param {Object} options - 选项
 * @returns {Object} 验证结果 {valid, data, error}
 */
function loadWithValidation(key, options = {}) {
  try {
    const storageData = wx.getStorageSync(key);
    
    if (!storageData) {
      return {
        valid: false,
        data: null,
        error: '数据不存在'
      };
    }
    
    // 版本检查
    if (!storageData.version || storageData.version !== (options.version || STORAGE_VERSION)) {
      console.warn(`[Storage] ⚠️  数据版本不匹配：${storageData.version}`);
      return {
        valid: false,
        data: null,
        error: '数据版本不匹配'
      };
    }
    
    // 校验和验证
    const expectedChecksum = storageData.checksum;
    const actualChecksum = calculateChecksum(storageData.data);
    
    if (expectedChecksum !== actualChecksum) {
      console.warn(`[Storage] ❌ 校验和失败：期望 ${expectedChecksum}, 实际 ${actualChecksum}`);
      
      // 尝试从备份恢复
      if (options.autoRepair !== false) {
        const backupKey = key + '_backup';
        const backupData = wx.getStorageSync(backupKey);
        
        if (backupData && backupData.checksum === calculateChecksum(backupData.data)) {
          console.log(`[Storage] ✅ 从备份恢复成功`);
          return {
            valid: true,
            data: backupData.data,
            error: null,
            restored: true
          };
        }
      }
      
      return {
        valid: false,
        data: null,
        error: '数据校验失败，可能已损坏'
      };
    }
    
    // 过期检查（可选）
    if (options.maxAge) {
      const age = Date.now() - storageData.timestamp;
      if (age > options.maxAge) {
        console.warn(`[Storage] ⏰ 数据已过期：${age}ms`);
        wx.removeStorageSync(key);
        return {
          valid: false,
          data: null,
          error: '数据已过期'
        };
      }
    }
    
    return {
      valid: true,
      data: storageData.data,
      error: null
    };
    
  } catch (error) {
    console.error(`[Storage] ❌ 加载失败：${key}`, error);
    return {
      valid: false,
      data: null,
      error: error.message
    };
  }
}

/**
 * 诊断结果专用保存函数
 * @param {string} executionId - 执行 ID
 * @param {Object} data - 诊断数据
 * @returns {boolean} 是否保存成功
 */
function saveDiagnosisResult(executionId, data) {
  const key = `diagnosis_result_${executionId}`;
  return saveWithChecksum(key, data, {
    version: '2.0',
    backup: true
  });
}

/**
 * 诊断结果专用加载函数
 * @param {string} executionId - 执行 ID
 * @returns {Object} 验证结果
 */
function loadDiagnosisResult(executionId) {
  const key = `diagnosis_result_${executionId}`;
  return loadWithValidation(key, {
    version: '2.0',
    autoRepair: true,
    maxAge: 7 * 24 * 60 * 60 * 1000 // 7 天
  });
}

/**
 * 清理过期数据
 * @param {number} maxAge - 最大保存时间（毫秒）
 * @returns {number} 清理的数据条数
 */
function cleanupExpiredData(maxAge = 7 * 24 * 60 * 60 * 1000) {
  try {
    const info = wx.getStorageInfoSync();
    const keys = info.keys || [];
    let cleanedCount = 0;
    const now = Date.now();
    
    keys.forEach(key => {
      if (!key.startsWith('diagnosis_result_')) {
        return;
      }
      
      try {
        const data = wx.getStorageSync(key);
        if (!data || !data.timestamp) {
          wx.removeStorageSync(key);
          cleanedCount++;
          return;
        }
        
        const age = now - data.timestamp;
        if (age > maxAge) {
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

/**
 * 获取 Storage 统计信息
 * @returns {Object} 统计信息
 */
function getStorageStats() {
  try {
    const info = wx.getStorageInfoSync();
    const keys = info.keys || [];
    
    const diagnosisKeys = keys.filter(k => k.startsWith('diagnosis_result_'));
    const backupKeys = keys.filter(k => k.endsWith('_backup'));
    
    return {
      totalKeys: keys.length,
      diagnosisKeys: diagnosisKeys.length,
      backupKeys: backupKeys.length,
      totalSize: info.currentSize || 0,
      sizeLimit: info.limitSize || 10240, // 默认 10MB
      usagePercent: ((info.currentSize || 0) / (info.limitSize || 10240) * 100).toFixed(1)
    };
    
  } catch (error) {
    console.error('[Storage] 获取统计信息失败:', error);
    return null;
  }
}

module.exports = {
  STORAGE_VERSION,
  crc32,
  calculateChecksum,
  saveWithChecksum,
  loadWithValidation,
  saveDiagnosisResult,
  loadDiagnosisResult,
  cleanupExpiredData,
  getStorageStats
};
