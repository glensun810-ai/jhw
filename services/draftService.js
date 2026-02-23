/**
 * 草稿管理服务
 * 负责用户输入的保存、恢复、清理
 */

const STORAGE_KEY = 'draft_diagnostic_input';
const DRAFT_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7 天

/**
 * 保存草稿
 * @param {Object} inputData - 输入数据
 */
const saveDraft = (inputData) => {
  try {
    const draft = {
      brandName: inputData.brandName || '',
      currentCompetitor: inputData.currentCompetitor || '',
      competitorBrands: inputData.competitorBrands || [],
      customQuestions: inputData.customQuestions || [],
      selectedModels: inputData.selectedModels || {
        domestic: [],
        overseas: []
      },
      updatedAt: Date.now()
    };

    wx.setStorageSync(STORAGE_KEY, draft);
    console.log('草稿已自动保存', {
      brandName: draft.brandName,
      competitorCount: draft.competitorBrands.length,
      questionCount: draft.customQuestions.length
    });
  } catch (error) {
    console.error('保存草稿失败:', error);
  }
};

/**
 * 恢复草稿
 * @returns {Object|null} 草稿数据，如果不存在或过期则返回 null
 */
const restoreDraft = () => {
  try {
    const draft = wx.getStorageSync(STORAGE_KEY);

    // 防御性检查：确保 draft 是对象
    if (!draft || typeof draft !== 'object') {
      return null;
    }

    // 类型强制转换：确保 brandName 是字符串
    const brandName = String(draft.brandName || '');
    if (!brandName) {
      return null;
    }

    // 检查是否过期
    const now = Date.now();
    const draftAge = now - (draft.updatedAt || 0);

    if (draftAge >= DRAFT_EXPIRY) {
      console.log('草稿已过期，已清除');
      wx.removeStorageSync(STORAGE_KEY);
      return null;
    }

    // 返回经过类型清洗的数据
    const cleanedDraft = {
      brandName: brandName,
      currentCompetitor: String(draft.currentCompetitor || ''),
      competitorBrands: Array.isArray(draft.competitorBrands) ? draft.competitorBrands : [],
      customQuestions: Array.isArray(draft.customQuestions) ? draft.customQuestions : [],
      selectedModels: {
        domestic: Array.isArray(draft.selectedModels?.domestic) ? draft.selectedModels.domestic : [],
        overseas: Array.isArray(draft.selectedModels?.overseas) ? draft.selectedModels.overseas : []
      },
      updatedAt: draft.updatedAt || 0
    };

    console.log('草稿已恢复', cleanedDraft);
    return cleanedDraft;
  } catch (error) {
    console.error('恢复草稿失败:', error);
    return null;
  }
};

/**
 * 清除草稿
 */
const clearDraft = () => {
  try {
    wx.removeStorageSync(STORAGE_KEY);
    console.log('草稿已清除');
  } catch (error) {
    console.error('清除草稿失败:', error);
  }
};

/**
 * 验证草稿数据
 * @param {Object} draft - 草稿数据
 * @returns {boolean} 是否有效
 */
const validateDraft = (draft) => {
  if (!draft || typeof draft !== 'object') {
    return false;
  }

  if (!draft.brandName || typeof draft.brandName !== 'string') {
    return false;
  }

  if (!Array.isArray(draft.competitorBrands)) {
    return false;
  }

  if (!Array.isArray(draft.customQuestions)) {
    return false;
  }

  return true;
};

/**
 * 检查草稿是否过期
 * @returns {boolean} 是否过期
 */
const isDraftExpired = () => {
  try {
    const draft = wx.getStorageSync(STORAGE_KEY);

    if (!draft || !draft.updatedAt) {
      return true;
    }

    const now = Date.now();
    const draftAge = now - draft.updatedAt;

    return draftAge >= DRAFT_EXPIRY;
  } catch (error) {
    console.error('检查草稿过期失败:', error);
    return true;
  }
};

/**
 * 格式化草稿问题数据
 * @param {Array} customQuestions - 自定义问题数组
 * @returns {Array} 格式化后的问题
 */
const formatDraftQuestions = (customQuestions) => {
  if (!Array.isArray(customQuestions) || customQuestions.length === 0) {
    return [
      { text: '', show: true },
      { text: '', show: true },
      { text: '', show: true }
    ];
  }

  return customQuestions.map(q => ({
    text: (q && q.text) || '',
    show: (q && q.show !== undefined) ? q.show : true
  }));
};

/**
 * 格式化草稿 AI 模型数据
 * @param {Array} currentModels - 当前模型数组
 * @param {Object} savedModels - 保存的模型选择
 * @returns {Array} 格式化后的模型
 */
const formatDraftModels = (currentModels, savedModels) => {
  if (!Array.isArray(currentModels)) {
    return [];
  }

  const selectedDomestic = savedModels?.domestic || [];
  const selectedOverseas = savedModels?.overseas || [];

  return {
    domestic: currentModels.map(model => ({
      ...model,
      checked: selectedDomestic.includes(model.name) && !model.disabled
    })),
    overseas: currentModels.map(model => ({
      ...model,
      checked: selectedOverseas.includes(model.name)
    }))
  };
};

module.exports = {
  saveDraft,
  restoreDraft,
  clearDraft,
  validateDraft,
  isDraftExpired,
  formatDraftQuestions,
  formatDraftModels,
  STORAGE_KEY,
  DRAFT_EXPIRY
};
