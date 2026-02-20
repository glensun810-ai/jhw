/**
 * 用户输入管理器
 * 
 * 功能:
 * 1. 自动保存用户输入
 * 2. 恢复上次输入
 * 3. 保存/加载配置
 * 4. 配置管理
 * 
 * 存储结构:
 * - last_diagnosis_input: 最近输入 (临时)
 * - saved_diagnosis_configs: 保存配置 (永久)
 * - favorite_diagnosis_config: 默认配置
 */

const STORAGE_KEYS = {
  LAST_INPUT: 'last_diagnosis_input',
  SAVED_CONFIGS: 'saved_diagnosis_configs',
  FAVORITE_CONFIG: 'favorite_diagnosis_config'
};

class InputManager {
  constructor() {
    this.currentInput = null;
    this.savedConfigs = this.loadConfigs();
  }

  /**
   * 加载保存的配置
   */
  loadConfigs() {
    try {
      return wx.getStorageSync(STORAGE_KEYS.SAVED_CONFIGS) || [];
    } catch (e) {
      console.error('加载配置失败', e);
      return [];
    }
  }

  /**
   * 保存配置
   */
  saveConfigs() {
    try {
      wx.setStorageSync(STORAGE_KEYS.SAVED_CONFIGS, this.savedConfigs);
      return true;
    } catch (e) {
      console.error('保存配置失败', e);
      return false;
    }
  }

  /**
   * 保存当前输入 (自动)
   */
  saveCurrentInput(input) {
    try {
      const data = {
        ...input,
        lastUsedAt: Date.now()
      };
      
      this.currentInput = data;
      wx.setStorageSync(STORAGE_KEYS.LAST_INPUT, data);
      
      console.log('✅ 已保存当前输入');
      return true;
    } catch (e) {
      console.error('保存输入失败', e);
      return false;
    }
  }

  /**
   * 恢复上次输入
   */
  restoreLastInput() {
    try {
      const lastInput = wx.getStorageSync(STORAGE_KEYS.LAST_INPUT);
      
      if (lastInput && lastInput.brandName) {
        console.log('✅ 已恢复上次输入');
        return {
          success: true,
          data: lastInput,
          timeAgo: this.getTimeAgo(lastInput.lastUsedAt)
        };
      }
      
      return { success: false, data: null };
    } catch (e) {
      console.error('恢复输入失败', e);
      return { success: false, data: null };
    }
  }

  /**
   * 保存配置
   */
  saveConfig(config) {
    const newConfig = {
      id: 'config_' + Date.now(),
      name: config.name,
      brandName: config.brandName,
      competitorBrands: config.competitorBrands || [],
      customQuestions: config.customQuestions || [],
      selectedModels: config.selectedModels || {},
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isFavorite: false
    };

    // 检查是否已存在同名配置
    const existingIndex = this.savedConfigs.findIndex(
      c => c.name === config.name
    );

    if (existingIndex !== -1) {
      // 更新已有配置
      this.savedConfigs[existingIndex] = {
        ...this.savedConfigs[existingIndex],
        ...newConfig,
        id: this.savedConfigs[existingIndex].id,
        createdAt: this.savedConfigs[existingIndex].createdAt
      };
    } else {
      // 添加新配置
      this.savedConfigs.push(newConfig);
    }

    const success = this.saveConfigs();
    
    if (success) {
      console.log('✅ 已保存配置:', newConfig.name);
      return { success: true, config: newConfig };
    }
    
    return { success: false, error: '保存失败' };
  }

  /**
   * 加载配置
   */
  loadConfig(configId) {
    const config = this.savedConfigs.find(c => c.id === configId);
    
    if (config) {
      console.log('✅ 已加载配置:', config.name);
      return { success: true, data: config };
    }
    
    return { success: false, error: '配置不存在' };
  }

  /**
   * 删除配置
   */
  deleteConfig(configId) {
    const initialLength = this.savedConfigs.length;
    this.savedConfigs = this.savedConfigs.filter(
      c => c.id !== configId
    );

    if (this.savedConfigs.length < initialLength) {
      const success = this.saveConfigs();
      
      if (success) {
        console.log('✅ 已删除配置');
        return { success: true };
      }
    }

    return { success: false, error: '删除失败' };
  }

  /**
   * 设置默认配置
   */
  setFavoriteConfig(configId) {
    // 取消所有默认
    this.savedConfigs.forEach(c => c.isFavorite = false);
    
    // 设置新的默认
    const config = this.savedConfigs.find(c => c.id === configId);
    if (config) {
      config.isFavorite = true;
      const success = this.saveConfigs();
      
      if (success) {
        console.log('✅ 已设置默认配置:', config.name);
        return { success: true };
      }
    }
    
    return { success: false, error: '设置失败' };
  }

  /**
   * 获取默认配置
   */
  getFavoriteConfig() {
    const favorite = this.savedConfigs.find(c => c.isFavorite);
    
    if (favorite) {
      return { success: true, data: favorite };
    }
    
    return { success: false, data: null };
  }

  /**
   * 获取所有配置
   */
  getAllConfigs() {
    return {
      success: true,
      data: this.savedConfigs,
      count: this.savedConfigs.length
    };
  }

  /**
   * 清空临时输入
   */
  clearTempInput() {
    try {
      this.currentInput = null;
      wx.removeStorageSync(STORAGE_KEYS.LAST_INPUT);
      console.log('✅ 已清空临时输入');
      return true;
    } catch (e) {
      console.error('清空输入失败', e);
      return false;
    }
  }

  /**
   * 清空所有配置
   */
  clearAllConfigs() {
    try {
      this.savedConfigs = [];
      wx.removeStorageSync(STORAGE_KEYS.SAVED_CONFIGS);
      wx.removeStorageSync(STORAGE_KEYS.FAVORITE_CONFIG);
      console.log('✅ 已清空所有配置');
      return true;
    } catch (e) {
      console.error('清空配置失败', e);
      return false;
    }
  }

  /**
   * 格式化时间
   */
  formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  }

  /**
   * 获取相对时间
   */
  getTimeAgo(timestamp) {
    return this.formatTime(timestamp);
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return {
      tempInputExists: !!this.currentInput || !!wx.getStorageSync(STORAGE_KEYS.LAST_INPUT),
      savedConfigsCount: this.savedConfigs.length,
      hasFavorite: this.savedConfigs.some(c => c.isFavorite)
    };
  }
}

module.exports = InputManager;
