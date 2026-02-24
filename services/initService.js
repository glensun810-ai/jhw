/**
 * 初始化服务
 * 负责页面初始化相关的业务逻辑
 */

const { checkServerConnectionApi } = require('../api/home');

const DEFAULT_AI_PLATFORMS = {
  domestic: ['DeepSeek', '豆包', '通义千问', '智谱 AI'],
  overseas: []
};

const STORAGE_KEY_PLATFORM_PREFS = 'user_ai_platform_preferences';

/**
 * 初始化默认值
 * @param {Object} pageContext - 页面上下文
 */
const initializeDefaults = (pageContext) => {
  if (!pageContext || !pageContext.setData) {
    console.warn('initializeDefaults: pageContext is invalid');
    return;
  }

  // 确保 config 和 diagnosticConfig 始终有默认值
  const config = pageContext.data?.config;
  const hasConfigEstimate = config && typeof config === 'object' && config.estimate && typeof config.estimate === 'object';

  if (!hasConfigEstimate) {
    pageContext.setData({
      config: {
        estimate: { duration: '30s', steps: 5 },
        brandName: '',
        competitorBrands: [],
        customQuestions: [{ text: '', show: true }, { text: '', show: true }, { text: '', show: true }]
      }
    });
  }

  const diagnosticConfig = pageContext.data?.diagnosticConfig;
  const hasDiagnosticEstimate = diagnosticConfig && typeof diagnosticConfig === 'object' && diagnosticConfig.estimate && typeof diagnosticConfig.estimate === 'object';

  if (!hasDiagnosticEstimate) {
    pageContext.setData({
      diagnosticConfig: {
        estimate: { duration: '30s', steps: 5 }
      }
    });
  }
};

/**
 * 检查服务器连接
 * @param {Object} pageContext - 页面上下文
 * @returns {Promise<boolean>} 是否连接成功
 */
const checkServerConnection = async (pageContext) => {
  try {
    await checkServerConnectionApi();
    if (pageContext && pageContext.setData) {
      pageContext.setData({ serverStatus: '已连接' });
    }
    return true;
  } catch (err) {
    console.error('服务器连接失败:', err);
    if (pageContext && pageContext.setData) {
      pageContext.setData({ serverStatus: '连接失败' });
    }
    
    // 根据错误类型显示不同的提示
    let errorMessage = '后端服务未启动';
    if (err.statusCode === 403) {
      errorMessage = '权限验证失败，请重新登录';
    } else if (err.statusCode === 401) {
      errorMessage = '认证失效，请重新登录';
    } else if (err.errMsg && err.errMsg.includes('request:fail')) {
      errorMessage = '网络连接失败，请检查服务器';
    }
    
    wx.showToast({ title: errorMessage, icon: 'error', duration: 2000 });
    return false;
  }
};

/**
 * 加载用户 AI 平台偏好
 * @param {Object} pageContext - 页面上下文
 * @returns {Object} 偏好数据
 */
const loadUserPlatformPreferences = (pageContext) => {
  try {
    const userPrefs = wx.getStorageSync(STORAGE_KEY_PLATFORM_PREFS);

    let selectedDomestic = [];
    let selectedOverseas = [];

    if (userPrefs && typeof userPrefs === 'object') {
      selectedDomestic = userPrefs.domestic || [];
      selectedOverseas = userPrefs.overseas || [];
      console.log('加载用户 AI 平台偏好', userPrefs);
    } else {
      selectedDomestic = DEFAULT_AI_PLATFORMS.domestic;
      selectedOverseas = DEFAULT_AI_PLATFORMS.overseas;
      console.log('使用默认 AI 平台配置', selectedDomestic);
    }

    const domesticAiModels = pageContext.data?.domesticAiModels || [];
    const overseasAiModels = pageContext.data?.overseasAiModels || [];

    const updatedDomestic = domesticAiModels.map(model => ({
      ...model,
      checked: selectedDomestic.includes(model.name) && !model.disabled
    }));

    const updatedOverseas = overseasAiModels.map(model => ({
      ...model,
      checked: selectedOverseas.includes(model.name)
    }));

    if (pageContext && pageContext.setData) {
      pageContext.setData({
        domesticAiModels: updatedDomestic,
        overseasAiModels: updatedOverseas
      });
    }

    return { domestic: selectedDomestic, overseas: selectedOverseas };
  } catch (error) {
    console.error('加载用户平台偏好失败', error);
    return null;
  }
};

/**
 * 保存用户 AI 平台偏好
 * @param {Object} preferences - 偏好数据
 */
const saveUserPlatformPreferences = (preferences) => {
  try {
    const userPrefs = {
      domestic: preferences.domestic || [],
      overseas: preferences.overseas || [],
      updatedAt: Date.now()
    };

    wx.setStorageSync(STORAGE_KEY_PLATFORM_PREFS, userPrefs);
    console.log('用户 AI 平台偏好已保存', userPrefs);
  } catch (error) {
    console.error('保存用户平台偏好失败', error);
  }
};

module.exports = {
  initializeDefaults,
  checkServerConnection,
  loadUserPlatformPreferences,
  saveUserPlatformPreferences,
  DEFAULT_AI_PLATFORMS,
  STORAGE_KEY_PLATFORM_PREFS
};
