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
      console.log('📊 加载用户 AI 平台偏好', userPrefs);
    } else {
      // P3 修复：使用完整的默认 AI 平台列表
      selectedDomestic = ['DeepSeek', '豆包', '通义千问', '智谱 AI'];
      selectedOverseas = ['ChatGPT'];
      console.log('📊 使用默认 AI 平台配置', selectedDomestic, selectedOverseas);
    }

    // P3 修复：始终使用完整的默认模型列表，然后更新选中状态
    // 不依赖 pageContext.data 中的值，避免数据丢失
    let domesticAiModels = [
      { name: 'DeepSeek', id: 'deepseek', checked: selectedDomestic.includes('DeepSeek'), logo: 'DS', tags: ['综合', '代码'] },
      { name: '豆包', id: 'doubao', checked: selectedDomestic.includes('豆包'), logo: 'DB', tags: ['综合', '创意'] },
      { name: '通义千问', id: 'qwen', checked: selectedDomestic.includes('通义千问'), logo: 'QW', tags: ['综合', '长文本'] },
      { name: '元宝', id: 'yuanbao', checked: selectedDomestic.includes('元宝'), logo: 'YB', tags: ['综合']},
      { name: 'Kimi', id: 'kimi', checked: selectedDomestic.includes('Kimi'), logo: 'KM', tags: ['长文本'] },
      { name: '文心一言', id: 'wenxin', checked: selectedDomestic.includes('文心一言'), logo: 'WX', tags: ['综合', '创意'] },
      { name: '讯飞星火', id: 'xinghuo', checked: selectedDomestic.includes('讯飞星火'), logo: 'XF', tags: ['综合', '语音'] },
      { name: '智谱 AI', id: 'zhipu', checked: selectedDomestic.includes('智谱 AI'), logo: 'ZP', tags: ['综合', 'GLM'] }
    ];
    console.log('📊 初始化国内 AI 平台列表，数量:', domesticAiModels.length);

    let overseasAiModels = [
      { name: 'ChatGPT', id: 'chatgpt', checked: selectedOverseas.includes('ChatGPT'), logo: 'GPT', tags: ['综合', '代码'] },
      { name: 'Gemini', id: 'gemini', checked: selectedOverseas.includes('Gemini'), logo: 'GM', tags: ['综合', '多模态'] },
      { name: 'Claude', id: 'claude', checked: selectedOverseas.includes('Claude'), logo: 'CD', tags: ['长文本', '创意'] },
      { name: 'Perplexity', id: 'perplexity', checked: selectedOverseas.includes('Perplexity'), logo: 'PE', tags: ['综合', '长文本'] },
      { name: 'Grok', id: 'grok', checked: selectedOverseas.includes('Grok'), logo: 'GR', tags: ['推理', '多模态'] }
    ];
    console.log('📊 初始化海外 AI 平台列表，数量:', overseasAiModels.length);

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
      console.log('✅ AI 平台矩阵已设置');
    }

    return { domestic: selectedDomestic, overseas: selectedOverseas };
  } catch (error) {
    console.error('❌ 加载用户平台偏好失败', error);
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
