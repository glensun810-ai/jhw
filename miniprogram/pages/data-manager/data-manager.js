const { getSearchResults, getPublicHistory, getUsageStats, cleanupSpace } = require('../../utils/local-storage.js');
const { manualSync } = require('../../utils/data-sync.js');

Page({
  data: {
    storageUsed: 0,
    storageTotal: 10,
    storagePercent: 0,
    storageStatus: '安全',
    storageStatusClass: 'safe',
    localHistoryCount: 0,
    savedResultsCount: 0,
    syncedResultsCount: 0,
    pendingSyncCount: 0,
    dataEncrypted: false,
    autoBackupEnabled: true
  },

  onLoad: function(options) {
    this.loadDataStats();
  },

  onShow: function() {
    this.loadDataStats();
  },

  // 加载数据统计
  loadDataStats: function() {
    try {
      // 获取本地存储使用情况
      const usageStats = getUsageStats();
      if (usageStats) {
        this.setData({
          storageUsed: usageStats.usedSize,
          storageTotal: usageStats.totalSize,
          storagePercent: usageStats.usagePercent,
          storageStatus: this.getStorageStatus(usageStats.usagePercent),
          storageStatusClass: this.getStorageStatusClass(usageStats.usagePercent)
        });
      }

      // 获取本地历史记录数量
      const publicHistory = getPublicHistory();
      const savedResults = getSearchResults();

      this.setData({
        localHistoryCount: publicHistory.length,
        savedResultsCount: savedResults.length,
        syncedResultsCount: savedResults.filter(r => r.synced).length,
        pendingSyncCount: savedResults.filter(r => !r.synced).length
      });
    } catch (e) {
      console.error('加载数据统计失败', e);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  // 获取存储状态
  getStorageStatus: function(percent) {
    if (percent > 90) return '危险';
    if (percent > 80) return '警告';
    return '安全';
  },

  // 获取存储状态样式类
  getStorageStatusClass: function(percent) {
    if (percent > 90) return 'danger';
    if (percent > 80) return 'warning';
    return 'safe';
  },

  // 同步数据
  syncData: function() {
    wx.showLoading({
      title: '同步中...',
      mask: true
    });

    manualSync().then(() => {
      wx.hideLoading();
      wx.showToast({
        title: '同步成功',
        icon: 'success'
      });
      this.loadDataStats(); // 重新加载统计数据
    }).catch((error) => {
      wx.hideLoading();
      wx.showToast({
        title: '同步失败',
        icon: 'none'
      });
      console.error('数据同步失败', error);
    });
  },

  // 清理缓存
  cleanCache: function() {
    wx.showModal({
      title: '确认清理',
      content: '确定要清理本地缓存吗？此操作不可撤销。',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({
            title: '清理中...',
            mask: true
          });

          // 执行清理操作
          cleanupSpace();

          setTimeout(() => {
            wx.hideLoading();
            wx.showToast({
              title: '清理完成',
              icon: 'success'
            });
            this.loadDataStats(); // 重新加载统计数据
          }, 1000);
        }
      }
    });
  },

  // 备份数据
  backupData: function() {
    wx.showModal({
      title: '数据备份',
      content: '即将备份您的数据到云端',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({
            title: '备份中...',
            mask: true
          });

          // 这期实现数据备份逻辑
          setTimeout(() => {
            wx.hideLoading();
            wx.showToast({
              title: '备份完成',
              icon: 'success'
            });
          }, 2000);
        }
      }
    });
  },

  // 恢复数据
  restoreData: function() {
    wx.showModal({
      title: '数据恢复',
      content: '确定要恢复数据吗？这将覆盖当前数据。',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({
            title: '恢复中...',
            mask: true
          });

          // 这期实现数据恢复逻辑
          setTimeout(() => {
            wx.hideLoading();
            wx.showToast({
              title: '恢复完成',
              icon: 'success'
            });
          }, 2000);
        }
      }
    });
  },

  // 切换加密
  toggleEncryption: function(e) {
    const encrypted = e.detail.value;
    this.setData({
      dataEncrypted: encrypted
    });

    // 这期实现数据加密逻辑
    wx.showToast({
      title: encrypted ? '加密已启用' : '加密已禁用',
      icon: 'none'
    });
  },

  // 切换自动备份
  toggleAutoBackup: function(e) {
    const enabled = e.detail.value;
    this.setData({
      autoBackupEnabled: enabled
    });

    // 这期实现自动备份逻辑
    wx.showToast({
      title: enabled ? '自动备份已启用' : '自动备份已禁用',
      icon: 'none'
    });
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({
      url: '/pages/index/index'
    });
  }
})