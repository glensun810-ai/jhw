/**
 * 配置管理服务
 * 负责保存的搜索配置的 CRUD
 */

const STORAGE_KEY = 'savedSearchConfigs';

/**
 * 保存配置
 * @param {Object} config - 配置对象
 * @returns {boolean} 是否成功
 */
const saveConfig = (config) => {
  try {
    if (!config || !config.name) {
      console.error('配置名称不能为空');
      return false;
    }

    let savedConfigs = wx.getStorageSync(STORAGE_KEY) || [];

    // 检查是否已存在同名配置
    const existingIndex = savedConfigs.findIndex(c => c.name === config.name);

    if (existingIndex !== -1) {
      savedConfigs[existingIndex] = config;
      console.log('配置已更新:', config.name);
    } else {
      savedConfigs.push(config);
      console.log('配置已保存:', config.name);
    }

    wx.setStorageSync(STORAGE_KEY, savedConfigs);
    return true;
  } catch (error) {
    console.error('保存配置失败:', error);
    return false;
  }
};

/**
 * 加载配置
 * @param {string} configName - 配置名称
 * @returns {Object|null} 配置对象
 */
const loadConfig = (configName) => {
  try {
    const savedConfigs = wx.getStorageSync(STORAGE_KEY) || [];
    const config = savedConfigs.find(c => c.name === configName);

    if (!config) {
      console.warn('配置不存在:', configName);
      return null;
    }

    console.log('配置已加载:', configName);
    return config;
  } catch (error) {
    console.error('加载配置失败:', error);
    return null;
  }
};

/**
 * 删除配置
 * @param {string} configName - 配置名称
 * @returns {boolean} 是否成功
 */
const deleteConfig = (configName) => {
  try {
    let savedConfigs = wx.getStorageSync(STORAGE_KEY) || [];
    const filteredConfigs = savedConfigs.filter(c => c.name !== configName);

    if (filteredConfigs.length === savedConfigs.length) {
      console.warn('配置不存在，无法删除:', configName);
      return false;
    }

    wx.setStorageSync(STORAGE_KEY, filteredConfigs);
    console.log('配置已删除:', configName);
    return true;
  } catch (error) {
    console.error('删除配置失败:', error);
    return false;
  }
};

/**
 * 获取所有配置
 * @returns {Array} 配置列表
 */
const getAllConfigs = () => {
  try {
    return wx.getStorageSync(STORAGE_KEY) || [];
  } catch (error) {
    console.error('获取配置列表失败:', error);
    return [];
  }
};

/**
 * 检查配置是否存在
 * @param {string} configName - 配置名称
 * @returns {boolean} 是否存在
 */
const configExists = (configName) => {
  try {
    const savedConfigs = wx.getStorageSync(STORAGE_KEY) || [];
    return savedConfigs.some(c => c.name === configName);
  } catch (error) {
    console.error('检查配置存在失败:', error);
    return false;
  }
};

module.exports = {
  saveConfig,
  loadConfig,
  deleteConfig,
  getAllConfigs,
  configExists,
  STORAGE_KEY
};
