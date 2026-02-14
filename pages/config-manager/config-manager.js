// pages/config-manager/config-manager.js

Page({
  data: {
    savedConfigs: []
  },

  onLoad: function () {
    this.loadSavedConfigs();
  },

  onShow: function() {
    this.loadSavedConfigs();
  },

  loadSavedConfigs: function() {
    const savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];

    // 为每个配置添加统计信息，以便在WXML中显示
    const configsForDisplay = savedConfigs.map(config => {
      // 计算有效问题数量
      const validQuestionsCount = Array.isArray(config.customQuestions)
        ? config.customQuestions.filter(q => q.text && q.text.trim()).length
        : 0;

      return {
        ...config,
        validQuestionsCount: validQuestionsCount
      };
    });

    this.setData({
      savedConfigs: configsForDisplay
    });
  },

  loadConfig: function(e) {
    const configName = e.currentTarget.dataset.name;

    // 从本地存储获取配置
    const savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];
    const configToLoad = savedConfigs.find(config => config.name === configName);

    if (!configToLoad) {
      wx.showToast({
        title: '配置不存在',
        icon: 'none'
      });
      return;
    }

    // 验证配置数据完整性
    if (!configToLoad.brandName || !Array.isArray(configToLoad.competitorBrands) || !Array.isArray(configToLoad.customQuestions)) {
      wx.showToast({
        title: '配置数据不完整',
        icon: 'none'
      });
      return;
    }

    // 将配置存储到全局数据中，以便返回首页时使用
    getApp().globalData.tempConfig = configToLoad;

    // 返回首页
    wx.navigateBack({
      delta: 1
    });
  },

  quickSearchWithConfig: function(e) {
    const configName = e.currentTarget.dataset.name;

    // 从本地存储获取配置
    const savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];
    const configToLoad = savedConfigs.find(config => config.name === configName);

    if (!configToLoad) {
      wx.showToast({
        title: '配置不存在',
        icon: 'none'
      });
      return;
    }

    // 验证配置数据完整性
    if (!configToLoad.brandName || !Array.isArray(configToLoad.competitorBrands) || !Array.isArray(configToLoad.customQuestions)) {
      wx.showToast({
        title: '配置数据不完整',
        icon: 'none'
      });
      return;
    }

    // 将配置存储到全局数据中，以便返回首页时使用
    getApp().globalData.tempConfig = configToLoad;

    // 跳转到首页并立即启动搜索
    wx.redirectTo({
      url: '/pages/index/index?quickSearch=true'
    });
  },

  deleteConfig: function(e) {
    const configName = e.currentTarget.dataset.name;
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除配置 "${configName}" 吗？`,
      success: (res) => {
        if (res.confirm) {
          let savedConfigs = wx.getStorageSync('savedSearchConfigs') || [];
          savedConfigs = savedConfigs.filter(config => config.name !== configName);
          wx.setStorageSync('savedSearchConfigs', savedConfigs);
          
          this.setData({
            savedConfigs: savedConfigs
          });
          
          wx.showToast({
            title: '配置已删除',
            icon: 'success'
          });
        }
      }
    });
  },

  goBack: function() {
    wx.navigateBack({
      delta: 1
    });
  }
})