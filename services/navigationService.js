/**
 * 导航服务
 * 负责页面跳转和 Storage 数据保存
 */

/**
 * 保存到 Storage 并跳转到结果页
 * @param {Object} resultData - 结果数据
 * @param {string} executionId - 执行 ID
 * @param {string} brandName - 品牌名称
 */
const saveAndNavigateToResults = (resultData, executionId, brandName) => {
  try {
    const resultsToSave = resultData.detailed_results || resultData.results || [];
    const competitiveAnalysisToSave = resultData.competitive_analysis || {};
    const brandScoresToSave = resultData.brand_scores || (competitiveAnalysisToSave && competitiveAnalysisToSave.brandScores) || {};

    // 保存到统一 Storage
    wx.setStorageSync('last_diagnostic_results', {
      results: resultsToSave,
      competitiveAnalysis: competitiveAnalysisToSave,
      brandScores: brandScoresToSave,
      targetBrand: brandName,
      executionId: executionId,
      timestamp: Date.now()
    });

    // 兼容旧逻辑
    wx.setStorageSync('latestTestResults_' + executionId, resultsToSave);
    wx.setStorageSync('latestCompetitiveAnalysis_' + executionId, competitiveAnalysisToSave);
    wx.setStorageSync('latestBrandScores_' + executionId, brandScoresToSave);
    wx.setStorageSync('latestTargetBrand', brandName);

    console.log('✅ 数据已保存到本地存储:', {
      resultsCount: resultsToSave.length,
      hasCompetitiveAnalysis: Object.keys(competitiveAnalysisToSave).length > 0,
      hasBrandScores: Object.keys(brandScoresToSave).length > 0
    });

    // 跳转
    wx.navigateTo({
      url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(brandName)}`,
      success: () => {
        console.log('✅ 已跳转到结果页');
      },
      fail: (err) => {
        console.error('跳转失败:', err);
        wx.showToast({ title: '跳转失败，请重试', icon: 'none' });
      }
    });
  } catch (error) {
    console.error('保存并跳转失败:', error);
    wx.showToast({ title: '保存失败', icon: 'none' });
  }
};

/**
 * 跳转到战略看板
 * @param {Object} reportData - 报告数据
 * @param {string} brandName - 品牌名称
 */
const navigateToDashboard = (reportData, brandName) => {
  try {
    const executionId = reportData?.executionId || Date.now().toString();

    if (reportData) {
      wx.setStorageSync('lastReport', reportData);

      const detailedResults = reportData.detailed_results || reportData.results || [];
      if (detailedResults && detailedResults.length > 0) {
        wx.setStorageSync('latestTestResults_' + executionId, detailedResults);
        wx.setStorageSync('latestTestResults', detailedResults);
      }

      wx.setStorageSync('latestTargetBrand', brandName || reportData.brand_name || '品牌');

      const competitiveAnalysis = reportData.competitiveAnalysis || {
        brandScores: {},
        firstMentionByPlatform: {},
        interceptionRisks: []
      };
      wx.setStorageSync('latestCompetitiveAnalysis_' + executionId, competitiveAnalysis);
      wx.setStorageSync('latestCompetitiveAnalysis', competitiveAnalysis);

      const brandScores = reportData.brand_scores ||
                         (reportData.competitiveAnalysis && reportData.competitiveAnalysis.brandScores) ||
                         {};
      if (brandScores && Object.keys(brandScores).length > 0) {
        wx.setStorageSync('latestBrandScores_' + executionId, brandScores);
        wx.setStorageSync('latestBrandScores', brandScores);
      }
    }

    setTimeout(() => {
      wx.redirectTo({
        url: `/pages/results/results?executionId=${executionId}&brandName=${encodeURIComponent(brandName || '品牌')}`,
        success: () => {
          console.log('✅ 诊断完成，已跳转到结果页');
        },
        fail: (err) => {
          console.error('跳转失败:', err);
          wx.showToast({ title: '请前往"我的"查看报告', icon: 'none' });
        }
      });
    }, 500);
  } catch (error) {
    console.error('导航失败:', error);
  }
};

/**
 * 跳转到报告详情页
 * @param {Object} reportData - 报告数据
 */
const navigateToReportDetail = (reportData) => {
  try {
    if (reportData) {
      const executionId = reportData.executionId || '';
      wx.setStorageSync('lastReport', reportData);

      wx.navigateTo({
        url: `/pages/report/dashboard/index?executionId=${executionId}`,
        fail: (err) => {
          console.error('跳转报告页面失败:', err);
          wx.showToast({ title: '跳转失败', icon: 'none' });
        }
      });
    } else {
      wx.showToast({ title: '暂无报告数据', icon: 'none' });
    }
  } catch (error) {
    console.error('跳转报告失败:', error);
  }
};

/**
 * 跳转到历史记录
 */
const navigateToHistory = () => {
  wx.navigateTo({
    url: '/pages/personal-history/personal-history',
    fail: (err) => {
      console.error('跳转历史失败:', err);
    }
  });
};

/**
 * 跳转到配置管理
 */
const navigateToConfigManager = () => {
  wx.navigateTo({
    url: '/pages/config-manager/config-manager',
    fail: (err) => {
      console.error('跳转配置管理失败:', err);
    }
  });
};

/**
 * 跳转到权限管理
 */
const navigateToPermissionManager = () => {
  wx.navigateTo({
    url: '/pages/permission-manager/permission-manager',
    fail: (err) => {
      console.error('跳转权限管理失败:', err);
    }
  });
};

/**
 * 跳转到数据管理
 */
const navigateToDataManager = () => {
  wx.navigateTo({
    url: '/pages/data-manager/data-manager',
    fail: (err) => {
      console.error('跳转数据管理失败:', err);
    }
  });
};

/**
 * 跳转到用户指南
 */
const navigateToUserGuide = () => {
  wx.navigateTo({
    url: '/pages/user-guide/user-guide',
    fail: (err) => {
      console.error('跳转用户指南失败:', err);
    }
  });
};

module.exports = {
  saveAndNavigateToResults,
  navigateToDashboard,
  navigateToReportDetail,
  navigateToHistory,
  navigateToConfigManager,
  navigateToPermissionManager,
  navigateToDataManager,
  navigateToUserGuide
};
