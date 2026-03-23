/**
 * 页面状态管理服务
 * 解决 Tab 切换时状态丢失问题
 * 
 * 作者：产品架构优化项目
 * 日期：2026-03-10
 * 版本：v1.0
 */

const STORAGE_PREFIX = 'page_state_';
const STATE_EXPIRY = 24 * 60 * 60 * 1000; // 24 小时过期

const pageStateService = {
  /**
   * 保存页面状态
   * @param {string} pageKey - 页面标识
   * @param {object} state - 状态数据
   */
  saveState: function(pageKey, state) {
    try {
      const serializedState = JSON.stringify({
        data: state,
        timestamp: Date.now()
      });
      wx.setStorageSync(STORAGE_PREFIX + pageKey, serializedState);
      console.log(`✅ 页面状态已保存：${pageKey}`);
    } catch (error) {
      console.error(`❌ 保存页面状态失败：${pageKey}`, error);
    }
  },

  /**
   * 获取页面状态
   * @param {string} pageKey - 页面标识
   * @returns {object|null} 状态数据
   */
  getState: function(pageKey) {
    try {
      const serializedState = wx.getStorageSync(STORAGE_PREFIX + pageKey);
      if (!serializedState) {
        return null;
      }
      
      const { data, timestamp } = JSON.parse(serializedState);
      
      // 检查状态是否过期
      const isExpired = Date.now() - timestamp > STATE_EXPIRY;
      if (isExpired) {
        this.clearState(pageKey);
        return null;
      }
      
      return data;
    } catch (error) {
      console.error(`❌ 获取页面状态失败：${pageKey}`, error);
      return null;
    }
  },

  /**
   * 清除页面状态
   * @param {string} pageKey - 页面标识
   */
  clearState: function(pageKey) {
    try {
      wx.removeStorageSync(STORAGE_PREFIX + pageKey);
      console.log(`✅ 页面状态已清除：${pageKey}`);
    } catch (error) {
      console.error(`❌ 清除页面状态失败：${pageKey}`, error);
    }
  },

  /**
   * 清除所有页面状态
   */
  clearAllStates: function() {
    try {
      const keys = wx.getStorageInfoSync().keys;
      keys.forEach(key => {
        if (key.startsWith(STORAGE_PREFIX)) {
          wx.removeStorageSync(key);
        }
      });
      console.log('✅ 所有页面状态已清除');
    } catch (error) {
      console.error('❌ 清除所有页面状态失败', error);
    }
  },

  /**
   * 获取所有页面状态键
   * @returns {string[]} 状态键列表
   */
  getAllStateKeys: function() {
    try {
      const keys = wx.getStorageInfoSync().keys;
      return keys.filter(key => key.startsWith(STORAGE_PREFIX));
    } catch (error) {
      console.error('❌ 获取状态键失败', error);
      return [];
    }
  },

  /**
   * 检查状态是否存在
   * @param {string} pageKey - 页面标识
   * @returns {boolean} 是否存在
   */
  hasState: function(pageKey) {
    try {
      return wx.getStorageSync(STORAGE_PREFIX + pageKey) !== '';
    } catch (error) {
      console.error('❌ 检查状态失败', error);
      return false;
    }
  }
};

/**
 * 页面键常量
 */
pageStateService.PAGE_KEYS = {
  INDEX: 'index',
  HISTORY: 'history',
  ANALYTICS: 'analytics',
  PROFILE: 'profile',
  SAVED_RESULTS: 'saved_results'
};

module.exports = pageStateService;
