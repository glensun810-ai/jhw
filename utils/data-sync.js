/**
 * 数据同步工具
 * 用于同步本地数据到云端
 */

const { checkLoginStatus, getUserInfo } = require('./auth.js');
const { getSearchResults, saveSearchResults } = require('./local-storage.js');
const { syncDataApi, downloadDataApi, uploadResultApi, deleteResultApi } = require('../api/data-sync.js');

class DataSyncManager {
  constructor() {
    this.syncQueue = [];
    this.isSyncing = false;
    this.syncInterval = 30000; // 30秒同步一次
    this.syncTimer = null;
  }

  /**
   * 初始化数据同步
   */
  init() {
    // 检查是否登录，如果登录则启动定时同步
    if (checkLoginStatus()) {
      this.startAutoSync();
    }
  }

  /**
   * 开始自动同步
   */
  startAutoSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
    }

    this.syncTimer = setInterval(() => {
      this.syncData();
    }, this.syncInterval);
  }

  /**
   * 停止自动同步
   */
  stopAutoSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
  }

  /**
   * 同步数据到云端
   */
  async syncData() {
    if (!checkLoginStatus()) {
      console.log('用户未登录，跳过数据同步');
      return;
    }

    try {
      // 获取本地保存的搜索结果
      const localResults = getSearchResults();

      if (localResults.length === 0) {
        console.log('没有需要同步的数据');
        return;
      }

      // 获取用户信息
      const userInfo = getUserInfo();
      if (!userInfo || !userInfo.openid) {
        console.error('用户信息不完整，无法同步数据');
        return;
      }

      // 调用API进行数据同步
      const res = await syncDataApi({
        openid: userInfo.openid,
        localResults: localResults
      });

      if (res.status === 'success') {
        console.log('数据同步成功');

        // 如果同步成功，可以考虑清理本地数据（根据策略决定）
        // this.cleanupLocalData(localResults, res.syncedIds);
      } else {
        console.error('数据同步失败:', res.message);
      }
    } catch (error) {
      console.error('数据同步过程出错:', error);
    }
  }

  /**
   * 从云端下载数据
   */
  async downloadData() {
    if (!checkLoginStatus()) {
      console.log('用户未登录，无法下载云端数据');
      return;
    }

    try {
      const userInfo = getUserInfo();
      if (!userInfo || !userInfo.openid) {
        console.error('用户信息不完整，无法下载数据');
        return;
      }

      // 调用API进行数据下载
      const res = await downloadDataApi({
        openid: userInfo.openid
      });

      if (res.status === 'success') {
        console.log('数据下载成功');

        // 合并云端数据到本地
        this.mergeCloudDataToLocal(res.cloudResults);
      } else {
        console.error('数据下载失败:', res.message);
      }
    } catch (error) {
      console.error('数据下载过程出错:', error);
    }
  }

  /**
   * 合并云端数据到本地
   * @param {Array} cloudResults 云端数据
   */
  mergeCloudDataToLocal(cloudResults) {
    if (!cloudResults || !Array.isArray(cloudResults)) {
      return;
    }

    const localResults = getSearchResults();

    // 创建云端数据的ID映射，便于快速查找
    const cloudMap = {};
    cloudResults.forEach(item => {
      cloudMap[item.id] = item;
    });

    // 合并逻辑：云端数据优先，但保留本地更新的数据
    const mergedResults = [];
    const processedIds = new Set();

    // 首先添加云端数据
    cloudResults.forEach(cloudItem => {
      mergedResults.push(cloudItem);
      processedIds.add(cloudItem.id);
    });

    // 然后添加本地独有的数据
    localResults.forEach(localItem => {
      if (!processedIds.has(localItem.id)) {
        mergedResults.push(localItem);
      }
    });

    // 保存合并后的数据
    saveSearchResults(mergedResults);
  }

  /**
   * 上传单个结果
   * @param {Object} result 要上传的结果
   */
  async uploadSingleResult(result) {
    if (!checkLoginStatus()) {
      console.log('用户未登录，无法上传单个结果');
      return Promise.reject(new Error('用户未登录'));
    }

    try {
      const userInfo = getUserInfo();
      if (!userInfo || !userInfo.openid) {
        throw new Error('用户信息不完整');
      }

      const res = await uploadResultApi({
        openid: userInfo.openid,
        result: result
      });

      if (res.status === 'success') {
        console.log('单个结果上传成功');
        return res;
      } else {
        console.error('单个结果上传失败:', res.message);
        throw new Error(res.message);
      }
    } catch (error) {
      console.error('单个结果上传请求失败:', error);
      throw error;
    }
  }

  /**
   * 删除云端数据
   * @param {string} id 要删除的数据ID
   */
  async deleteCloudResult(id) {
    if (!checkLoginStatus()) {
      console.log('用户未登录，无法删除云端数据');
      throw new Error('用户未登录');
    }

    try {
      const userInfo = getUserInfo();
      if (!userInfo || !userInfo.openid) {
        throw new Error('用户信息不完整');
      }

      const res = await deleteResultApi({
        openid: userInfo.openid,
        id: id
      });

      if (res.status === 'success') {
        console.log('云端数据删除成功');
        return res;
      } else {
        console.error('云端数据删除失败:', res.message);
        throw new Error(res.message);
      }
    } catch (error) {
      console.error('云端数据删除请求失败:', error);
      throw error;
    }
  }

  /**
   * 清理本地数据（保留云端已同步的数据）
   * @param {Array} localResults 本地数据
   * @param {Array} syncedIds 已同步的ID列表
   */
  cleanupLocalData(localResults, syncedIds) {
    if (!syncedIds || !Array.isArray(syncedIds)) {
      return;
    }

    // 只留未同步的数据
    const unsyncedResults = localResults.filter(result => !syncedIds.includes(result.id));

    if (unsyncedResults.length !== localResults.length) {
      saveSearchResults(unsyncedResults);
      console.log(`清理了 ${localResults.length - unsyncedResults.length} 条已同步的数据`);
    }
  }

  /**
   * 手动触发同步
   */
  manualSync() {
    console.log('手动触发数据同步');
    return this.syncData();
  }

  /**
   * 获取同步状态
   */
  getSyncStatus() {
    return {
      isSyncing: this.isSyncing,
      queueSize: this.syncQueue.length,
      lastSyncTime: wx.getStorageSync('lastSyncTime') || null
    };
  }

  /**
   * 销毁实例
   */
  destroy() {
    this.stopAutoSync();
  }
}

// 创建全局实例
const dataSyncManager = new DataSyncManager();

module.exports = {
  dataSyncManager,
  init: dataSyncManager.init.bind(dataSyncManager),
  syncData: dataSyncManager.syncData.bind(dataSyncManager),
  downloadData: dataSyncManager.downloadData.bind(dataSyncManager),
  uploadSingleResult: dataSyncManager.uploadSingleResult.bind(dataSyncManager),
  deleteCloudResult: dataSyncManager.deleteCloudResult.bind(dataSyncManager),
  manualSync: dataSyncManager.manualSync.bind(dataSyncManager),
  getSyncStatus: dataSyncManager.getSyncStatus.bind(dataSyncManager)
};