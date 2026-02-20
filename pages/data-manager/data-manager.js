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
    const that = this;
    wx.showModal({
      title: '数据备份',
      content: '即将备份您的数据到本地存储',
      success: (res) => {
        if (res.confirm) {
          that.executeBackup();
        }
      }
    });
  },

  // 执行备份
  executeBackup: function() {
    wx.showLoading({
      title: '备份中...',
      mask: true
    });

    try {
      // 收集需要备份的数据
      const backupData = {
        // 用户数据
        userInfo: wx.getStorageSync('userInfo') || null,
        // 历史记录
        diagnosisHistory: wx.getStorageSync('diagnosisHistory') || [],
        // 收藏列表
        favorites: wx.getStorageSync('favorites') || [],
        // 保存的配置
        savedConfigs: wx.getStorageSync('savedConfigs') || [],
        // 备份时间戳
        backupTime: Date.now(),
        backupVersion: '1.0.0'
      };

      // 保存到本地存储
      wx.setStorageSync('backup_data', JSON.stringify(backupData));
      
      // 同时保存到云开发数据库（如果已启用）
      if (wx.cloud) {
        this.saveToCloud(backupData);
      }

      wx.hideLoading();
      wx.showToast({
        title: '备份完成',
        icon: 'success'
      });

      // 更新备份时间显示
      this.setData({
        lastBackupTime: this.formatBackupTime(Date.now())
      });

      logger.info('数据备份成功', { backupData });
    } catch (error) {
      wx.hideLoading();
      logger.error('数据备份失败', error);
      wx.showToast({
        title: '备份失败：' + error.message,
        icon: 'none'
      });
    }
  },

  // 保存到云开发数据库
  saveToCloud: function(backupData) {
    try {
      const db = wx.cloud.database();
      const backupCollection = db.collection('user_backups');
      
      backupCollection.add({
        data: {
          _openid: app.globalData.openid || 'anonymous',
          backup_data: backupData,
          create_time: new Date()
        }
      }).then(res => {
        logger.info('云备份成功', res);
      }).catch(err => {
        logger.warn('云备份失败', err);
      });
    } catch (error) {
      logger.warn('云备份异常', error);
    }
  },

  // 恢复数据
  restoreData: function() {
    const that = this;
    wx.showModal({
      title: '数据恢复',
      content: '确定要恢复数据吗？这将覆盖当前所有数据。',
      confirmText: '恢复',
      confirmColor: '#e74c3c',
      success: (res) => {
        if (res.confirm) {
          // 二次确认
          wx.showModal({
            title: '再次确认',
            content: '此操作不可逆，确定要继续吗？',
            confirmText: '确定恢复',
            confirmColor: '#e74c3c',
            success: (res2) => {
              if (res2.confirm) {
                that.executeRestore();
              }
            }
          });
        }
      }
    });
  },

  // 执行恢复
  executeRestore: function() {
    wx.showLoading({
      title: '恢复中...',
      mask: true
    });

    try {
      // 从本地存储读取备份数据
      const backupStr = wx.getStorageSync('backup_data');
      
      if (!backupStr) {
        wx.hideLoading();
        wx.showToast({
          title: '未找到备份数据',
          icon: 'none'
        });
        return;
      }

      const backupData = JSON.parse(backupStr);

      // 恢复各项数据
      if (backupData.userInfo) {
        wx.setStorageSync('userInfo', backupData.userInfo);
      }
      if (backupData.diagnosisHistory) {
        wx.setStorageSync('diagnosisHistory', backupData.diagnosisHistory);
      }
      if (backupData.favorites) {
        wx.setStorageSync('favorites', backupData.favorites);
      }
      if (backupData.savedConfigs) {
        wx.setStorageSync('savedConfigs', backupData.savedConfigs);
      }

      wx.hideLoading();
      wx.showToast({
        title: '恢复完成',
        icon: 'success'
      });

      // 更新显示数据
      this.loadStorageStats();

      logger.info('数据恢复成功', { backupTime: backupData.backupTime });
    } catch (error) {
      wx.hideLoading();
      logger.error('数据恢复失败', error);
      wx.showToast({
        title: '恢复失败：' + error.message,
        icon: 'none'
      });
    }
  },

  // 切换加密
  toggleEncryption: function(e) {
    const encrypted = e.detail.value;
    this.setData({
      dataEncrypted: encrypted
    });

    // 保存加密设置
    wx.setStorageSync('data_encrypted', encrypted);
    
    wx.showToast({
      title: encrypted ? '加密已启用' : '加密已禁用',
      icon: 'none'
    });

    logger.info('数据加密设置已更新', { encrypted });
  },

  // 切换自动备份
  toggleAutoBackup: function(e) {
    const enabled = e.detail.value;
    this.setData({
      autoBackupEnabled: enabled
    });

    // 保存自动备份设置
    wx.setStorageSync('auto_backup_enabled', enabled);

    if (enabled) {
      // 启用自动备份：每天凌晨 2 点备份
      this.scheduleAutoBackup();
    } else {
      // 取消自动备份
      this.cancelAutoBackup();
    }
    
    wx.showToast({
      title: enabled ? '自动备份已启用' : '自动备份已禁用',
      icon: 'none'
    });

    logger.info('自动备份设置已更新', { enabled });
  },

  // 设置自动备份
  scheduleAutoBackup: function() {
    // 微信小程序不支持定时任务，这里使用后台任务方式
    // 实际项目中可以使用云开发定时触发器
    logger.info('自动备份已设置（需要云开发支持）');
  },

  // 取消自动备份
  cancelAutoBackup: function() {
    logger.info('自动备份已取消');
  },

  // 格式化备份时间
  formatBackupTime: function(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // 今天
    if (diff < 24 * 60 * 60 * 1000) {
      return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
    
    // 昨天
    if (diff < 48 * 60 * 60 * 1000) {
      return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
    
    // 更早
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  },

  // 返回首页
  goHome: function() {
    wx.reLaunch({
      url: '/pages/index/index'
    });
  }
})