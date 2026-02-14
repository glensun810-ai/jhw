/**
 * 本地数据管理工具
 * 用于管理本地存储的数据
 */

const STORAGE_KEYS = {
  USER_INFO: 'userInfo',
  USER_TOKEN: 'userToken',
  IS_LOGGED_IN: 'isLoggedIn',
  USER_PERMISSIONS: 'userPermissions',
  LATEST_TEST_RESULTS: 'latestTestResults',
  LATEST_COMPETITIVE_ANALYSIS: 'latestCompetitiveAnalysis',
  LATEST_TARGET_BRAND: 'latestTargetBrand',
  SAVED_SEARCH_RESULTS: 'savedSearchResults',
  PUBLIC_HISTORY: 'publicHistory',
  TEMP_CONFIG: 'tempConfig'
};

class LocalStorageManager {
  constructor() {
    this.version = '1.0.0';
    this.init();
  }

  init() {
    // 初始化本地存储
    this.ensureStorageStructure();
  }

  /**
   * 确保存储结构完整
   */
  ensureStorageStructure() {
    // 检查并初始化必要的存储项
    if (!wx.getStorageSync(STORAGE_KEYS.SAVED_SEARCH_RESULTS)) {
      wx.setStorageSync(STORAGE_KEYS.SAVED_SEARCH_RESULTS, []);
    }
    
    if (!wx.getStorageSync(STORAGE_KEYS.PUBLIC_HISTORY)) {
      wx.setStorageSync(STORAGE_KEYS.PUBLIC_HISTORY, []);
    }
  }

  /**
   * 获取存储项
   * @param {string} key 存储键
   * @param {*} defaultValue 默认值
   * @returns {*} 存储的值
   */
  getItem(key, defaultValue = null) {
    try {
      const value = wx.getStorageSync(key);
      return value !== '' ? value : defaultValue;
    } catch (e) {
      console.error(`获取存储项 ${key} 失败:`, e);
      return defaultValue;
    }
  }

  /**
   * 设置存储项
   * @param {string} key 存储键
   * @param {*} value 存储值
   */
  setItem(key, value) {
    try {
      wx.setStorageSync(key, value);
    } catch (e) {
      console.error(`设置存储项 ${key} 失败:`, e);
    }
  }

  /**
   * 删除存储项
   * @param {string} key 存储键
   */
  removeItem(key) {
    try {
      wx.removeStorageSync(key);
    } catch (e) {
      console.error(`删除存储项 ${key} 失败:`, e);
    }
  }

  /**
   * 清空所有存储
   */
  clear() {
    try {
      wx.clearStorageSync();
    } catch (e) {
      console.error('清空存储失败:', e);
    }
  }

  /**
   * 获取所有存储的键
   */
  getAllKeys() {
    try {
      return wx.getStorageInfoSync().keys;
    } catch (e) {
      console.error('获取存储键失败:', e);
      return [];
    }
  }

  /**
   * 获取存储大小
   */
  getStorageSize() {
    try {
      const info = wx.getStorageInfoSync();
      return {
        keys: info.keys,
        currentSize: info.currentSize,
        limitSize: info.limitSize
      };
    } catch (e) {
      console.error('获取存储信息失败:', e);
      return null;
    }
  }

  /**
   * 保存用户数据
   * @param {Object} userData 用户数据
   */
  saveUserData(userData) {
    this.setItem(STORAGE_KEYS.USER_INFO, userData);
    this.setItem(STORAGE_KEYS.IS_LOGGED_IN, true);
  }

  /**
   * 获取用户数据
   */
  getUserData() {
    return this.getItem(STORAGE_KEYS.USER_INFO, {});
  }

  /**
   * 保存登录令牌
   * @param {string} token 登录令牌
   */
  saveToken(token) {
    this.setItem(STORAGE_KEYS.USER_TOKEN, token);
  }

  /**
   * 获取登录令牌
   */
  getToken() {
    return this.getItem(STORAGE_KEYS.USER_TOKEN, '');
  }

  /**
   * 保存用户权限
   * @param {Array} permissions 权限列表
   */
  savePermissions(permissions) {
    this.setItem(STORAGE_KEYS.USER_PERMISSIONS, permissions);
  }

  /**
   * 获取用户权限
   */
  getPermissions() {
    return this.getItem(STORAGE_KEYS.USER_PERMISSIONS, ['basic']);
  }

  /**
   * 保存最新测试结果
   * @param {Object} results 测试结果
   */
  saveLatestTestResults(results) {
    this.setItem(STORAGE_KEYS.LATEST_TEST_RESULTS, results);
  }

  /**
   * 获取最新测试结果
   */
  getLatestTestResults() {
    return this.getItem(STORAGE_KEYS.LATEST_TEST_RESULTS, null);
  }

  /**
   * 保存最新竞品分析
   * @param {Object} analysis 竞品分析
   */
  saveLatestCompetitiveAnalysis(analysis) {
    this.setItem(STORAGE_KEYS.LATEST_COMPETITIVE_ANALYSIS, analysis);
  }

  /**
   * 获取最新竞品分析
   */
  getLatestCompetitiveAnalysis() {
    return this.getItem(STORAGE_KEYS.LATEST_COMPETITIVE_ANALYSIS, null);
  }

  /**
   * 保存最新目标品牌
   * @param {string} brand 目标品牌
   */
  saveLatestTargetBrand(brand) {
    this.setItem(STORAGE_KEYS.LATEST_TARGET_BRAND, brand);
  }

  /**
   * 获取最新目标品牌
   */
  getLatestTargetBrand() {
    return this.getItem(STORAGE_KEYS.LATEST_TARGET_BRAND, '');
  }

  /**
   * 保存搜索结果
   * @param {Array} results 搜索结果
   */
  saveSearchResults(results) {
    this.setItem(STORAGE_KEYS.SAVED_SEARCH_RESULTS, results);
  }

  /**
   * 获取搜索结果
   */
  getSearchResults() {
    return this.getItem(STORAGE_KEYS.SAVED_SEARCH_RESULTS, []);
  }

  /**
   * 添加搜索结果
   * @param {Object} result 搜索结果
   */
  addSearchResult(result) {
    const results = this.getSearchResults();
    results.unshift(result);
    this.saveSearchResults(results);
  }

  /**
   * 删除搜索结果
   * @param {string} id 结果ID
   */
  removeSearchResult(id) {
    const results = this.getSearchResults();
    const filteredResults = results.filter(result => result.id !== id);
    this.saveSearchResults(filteredResults);
  }

  /**
   * 更新搜索结果
   * @param {string} id 结果ID
   * @param {Object} newData 新数据
   */
  updateSearchResult(id, newData) {
    const results = this.getSearchResults();
    const index = results.findIndex(result => result.id === id);
    if (index !== -1) {
      results[index] = { ...results[index], ...newData };
      this.saveSearchResults(results);
    }
  }

  /**
   * 保存公共历史记录
   * @param {Array} history 历史记录
   */
  savePublicHistory(history) {
    this.setItem(STORAGE_KEYS.PUBLIC_HISTORY, history);
  }

  /**
   * 获取公共历史记录
   */
  getPublicHistory() {
    return this.getItem(STORAGE_KEYS.PUBLIC_HISTORY, []);
  }

  /**
   * 添加公共历史记录
   * @param {Object} record 历史记录
   */
  addPublicHistory(record) {
    const history = this.getPublicHistory();
    history.unshift(record);
    this.savePublicHistory(history);
  }

  /**
   * 清理过期数据
   */
  cleanupExpiredData() {
    // 这期清理过期的临时数据
    const now = Date.now();
    const tempConfig = this.getItem(STORAGE_KEYS.TEMP_CONFIG);
    
    // 如果临时配置存在且超过一定时间（比如30分钟），则清理
    if (tempConfig && tempConfig.timestamp && (now - tempConfig.timestamp) > 30 * 60 * 1000) {
      this.removeItem(STORAGE_KEYS.TEMP_CONFIG);
    }
  }

  /**
   * 获取存储使用情况
   */
  getUsageStats() {
    const info = this.getStorageSize();
    if (!info) return null;

    const totalSize = info.limitSize; // KB
    const usedSize = info.currentSize; // KB
    const usagePercent = totalSize > 0 ? Math.round((usedSize / totalSize) * 100) : 0;

    return {
      totalSize,
      usedSize,
      usagePercent,
      remainingSize: totalSize - usedSize
    };
  }

  /**
   * 检查存储是否接近满载
   */
  isNearLimit() {
    const stats = this.getUsageStats();
    if (!stats) return false;
    return stats.usagePercent > 80; // 超过80%认为接近满载
  }

  /**
   * 清理部分数据以释放空间
   */
  cleanupSpace() {
    if (!this.isNearLimit()) return;

    // 清理一些非关键数据
    const publicHistory = this.getPublicHistory();
    if (publicHistory.length > 50) {
      // 只留最近50条记录
      this.savePublicHistory(publicHistory.slice(0, 50));
    }

    // 清理过期的临时数据
    this.cleanupExpiredData();
  }
}

// 创建全局实例
const localStorageManager = new LocalStorageManager();

module.exports = {
  localStorageManager,
  STORAGE_KEYS,
  getItem: localStorageManager.getItem.bind(localStorageManager),
  setItem: localStorageManager.setItem.bind(localStorageManager),
  removeItem: localStorageManager.removeItem.bind(localStorageManager),
  clear: localStorageManager.clear.bind(localStorageManager),
  saveUserData: localStorageManager.saveUserData.bind(localStorageManager),
  getUserData: localStorageManager.getUserData.bind(localStorageManager),
  saveToken: localStorageManager.saveToken.bind(localStorageManager),
  getToken: localStorageManager.getToken.bind(localStorageManager),
  savePermissions: localStorageManager.savePermissions.bind(localStorageManager),
  getPermissions: localStorageManager.getPermissions.bind(localStorageManager),
  saveLatestTestResults: localStorageManager.saveLatestTestResults.bind(localStorageManager),
  getLatestTestResults: localStorageManager.getLatestTestResults.bind(localStorageManager),
  saveLatestCompetitiveAnalysis: localStorageManager.saveLatestCompetitiveAnalysis.bind(localStorageManager),
  getLatestCompetitiveAnalysis: localStorageManager.getLatestCompetitiveAnalysis.bind(localStorageManager),
  saveLatestTargetBrand: localStorageManager.saveLatestTargetBrand.bind(localStorageManager),
  getLatestTargetBrand: localStorageManager.getLatestTargetBrand.bind(localStorageManager),
  saveSearchResults: localStorageManager.saveSearchResults.bind(localStorageManager),
  getSearchResults: localStorageManager.getSearchResults.bind(localStorageManager),
  addSearchResult: localStorageManager.addSearchResult.bind(localStorageManager),
  removeSearchResult: localStorageManager.removeSearchResult.bind(localStorageManager),
  updateSearchResult: localStorageManager.updateSearchResult.bind(localStorageManager),
  savePublicHistory: localStorageManager.savePublicHistory.bind(localStorageManager),
  getPublicHistory: localStorageManager.getPublicHistory.bind(localStorageManager),
  addPublicHistory: localStorageManager.addPublicHistory.bind(localStorageManager),
  getUsageStats: localStorageManager.getUsageStats.bind(localStorageManager),
  cleanupSpace: localStorageManager.cleanupSpace.bind(localStorageManager)
};