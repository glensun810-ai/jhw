/**
 * 数据同步服务
 * 负责本地数据与云端数据的同步
 */

const { syncData, uploadResult } = require('../api/sync');

// 同步状态
const SYNC_STATUS = {
  IDLE: 'idle',
  SYNCING: 'syncing',
  SUCCESS: 'success',
  ERROR: 'error'
};

// 同步配置
const SYNC_CONFIG = {
  AUTO_SYNC_INTERVAL: 5 * 60 * 1000, // 5 分钟自动同步
  MAX_RETRY_COUNT: 3,
  RETRY_DELAY: 1000 // 1 秒后重试
};

class SyncService {
  constructor() {
    this.status = SYNC_STATUS.IDLE;
    this.lastSyncTimestamp = null;
    this.pendingResults = [];
    this.autoSyncTimer = null;
    
    // 加载上次同步时间戳
    this.loadLastSyncTimestamp();
  }

  /**
   * 加载上次同步时间戳
   */
  loadLastSyncTimestamp() {
    const timestamp = wx.getStorageSync('lastSyncTimestamp');
    if (timestamp) {
      this.lastSyncTimestamp = timestamp;
    }
  }

  /**
   * 保存同步时间戳
   */
  saveLastSyncTimestamp(timestamp) {
    this.lastSyncTimestamp = timestamp;
    wx.setStorageSync('lastSyncTimestamp', timestamp);
  }

  /**
   * 添加待同步结果
   */
  addPendingResult(result) {
    this.pendingResults.push({
      ...result,
      syncStatus: 'pending',
      addedAt: Date.now()
    });
    
    // 如果结果数量超过阈值，立即同步
    if (this.pendingResults.length >= 5) {
      this.sync();
    }
  }

  /**
   * 执行同步
   */
  async sync() {
    if (this.status === SYNC_STATUS.SYNCING) {
      console.log('Sync already in progress');
      return;
    }

    this.status = SYNC_STATUS.SYNCING;
    console.log('Starting sync...');

    try {
      // 准备同步数据
      const syncDataPayload = {
        lastSyncTimestamp: this.lastSyncTimestamp,
        localResults: this.pendingResults.map(r => ({
          result_id: r.result_id || r.executionId || `result_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          brand_name: r.brandName || r.brand_name,
          ai_models_used: r.aiModelsUsed || r.ai_models_used,
          questions_used: r.questionsUsed || r.questions_used,
          overall_score: r.overallScore || r.overall_score,
          total_tests: r.totalTests || r.total_tests,
          results_summary: r.resultsSummary || r.results_summary,
          detailed_results: r.detailedResults || r.detailed_results,
          test_date: r.testDate || r.test_date || new Date().toISOString()
        }))
      };

      // 执行同步
      const response = await this._syncWithRetry(syncDataPayload);

      if (response && response.status === 'success') {
        // 更新同步时间戳
        this.saveLastSyncTimestamp(response.last_sync_timestamp);
        
        // 清空待同步队列
        this.pendingResults = [];
        
        // 合并云端数据到本地
        if (response.cloud_results && response.cloud_results.length > 0) {
          this._mergeCloudResults(response.cloud_results);
        }

        this.status = SYNC_STATUS.SUCCESS;
        console.log(`Sync completed: ${response.uploaded_count} uploaded, ${response.cloud_results.length} downloaded`);
        
        return {
          success: true,
          uploadedCount: response.uploaded_count,
          downloadedCount: response.cloud_results.length
        };
      } else {
        throw new Error(response?.message || 'Sync failed');
      }
    } catch (error) {
      console.error('Sync failed:', error);
      this.status = SYNC_STATUS.ERROR;
      
      return {
        success: false,
        error: error.message
      };
    } finally {
      this.status = SYNC_STATUS.IDLE;
    }
  }

  /**
   * 同步（带重试）
   */
  async _syncWithRetry(syncData, retryCount = 0) {
    try {
      return await syncData(syncData);
    } catch (error) {
      if (retryCount < SYNC_CONFIG.MAX_RETRY_COUNT) {
        console.log(`Sync failed, retrying (${retryCount + 1}/${SYNC_CONFIG.MAX_RETRY_COUNT})...`);
        await this._delay(SYNC_CONFIG.RETRY_DELAY * (retryCount + 1));
        return this._syncWithRetry(syncData, retryCount + 1);
      }
      throw error;
    }
  }

  /**
   * 合并云端结果到本地
   */
  _mergeCloudResults(cloudResults) {
    // 获取本地保存的结果
    const localResults = this._getLocalResults();
    
    // 创建本地结果的 Map（以 result_id 为键）
    const localResultsMap = new Map();
    localResults.forEach(result => {
      localResultsMap.set(result.result_id, result);
    });
    
    // 合并云端结果
    cloudResults.forEach(cloudResult => {
      const localResult = localResultsMap.get(cloudResult.result_id);
      
      if (!localResult) {
        // 本地没有，添加云端结果
        localResults.push(cloudResult);
      } else if (this._isNewer(cloudResult.sync_timestamp, localResult.sync_timestamp)) {
        // 云端结果更新，更新本地结果
        Object.assign(localResult, cloudResult);
      }
    });
    
    // 保存合并后的结果
    this._saveLocalResults(localResults);
    
    console.log(`Merged ${cloudResults.length} cloud results to local storage`);
  }

  /**
   * 获取本地结果
   */
  _getLocalResults() {
    const results = wx.getStorageSync('syncedResults');
    return results ? JSON.parse(results) : [];
  }

  /**
   * 保存本地结果
   */
  _saveLocalResults(results) {
    try {
      wx.setStorageSync('syncedResults', JSON.stringify(results));
    } catch (error) {
      // 存储空间不足，清理旧数据
      console.warn('Storage full, cleaning old results...');
      this._cleanOldResults(10); // 只保留最近 10 条
      this._saveLocalResults(results);
    }
  }

  /**
   * 清理旧结果
   */
  _cleanOldResults(keepCount) {
    const results = this._getLocalResults();
    if (results.length <= keepCount) return;
    
    // 按同步时间戳排序，保留最新的
    results.sort((a, b) => {
      const timeA = a.sync_timestamp || a.test_date || '';
      const timeB = b.sync_timestamp || b.test_date || '';
      return timeB.localeCompare(timeA);
    });
    
    // 保留最新的 keepCount 条
    const keptResults = results.slice(0, keepCount);
    this._saveLocalResults(keptResults);
  }

  /**
   * 比较时间戳
   */
  _isNewer(timeA, timeB) {
    if (!timeA) return false;
    if (!timeB) return true;
    return timeA > timeB;
  }

  /**
   * 延迟
   */
  _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 启动自动同步
   */
  startAutoSync() {
    this.stopAutoSync();
    
    this.autoSyncTimer = setInterval(() => {
      if (this.status === SYNC_STATUS.IDLE) {
        this.sync();
      }
    }, SYNC_CONFIG.AUTO_SYNC_INTERVAL);
    
    console.log('Auto sync started');
  }

  /**
   * 停止自动同步
   */
  stopAutoSync() {
    if (this.autoSyncTimer) {
      clearInterval(this.autoSyncTimer);
      this.autoSyncTimer = null;
      console.log('Auto sync stopped');
    }
  }

  /**
   * 获取同步状态
   */
  getStatus() {
    return this.status;
  }

  /**
   * 获取待同步数量
   */
  getPendingCount() {
    return this.pendingResults.length;
  }
}

// 创建全局实例
const syncService = new SyncService();

module.exports = {
  syncService,
  SYNC_STATUS,
  sync: syncService.sync.bind(syncService),
  startAutoSync: syncService.startAutoSync.bind(syncService),
  stopAutoSync: syncService.stopAutoSync.bind(syncService),
  addPendingResult: syncService.addPendingResult.bind(syncService)
};
