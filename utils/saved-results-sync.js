/**
 * 保存结果云端同步工具
 * 负责将本地保存的搜索结果同步到云端，支持多设备访问
 */

const { uploadResultApi, deleteResultApi, downloadDataApi, syncDataApi } = require('../api/data-sync');
const { authManager } = require('./auth');

/**
 * 将本地保存的结果同步到云端
 * @param {Array} localResults - 本地结果数组
 * @returns {Promise<Array>} - 云端同步后的结果
 */
const syncSavedResultsToCloud = async (localResults) => {
  try {
    // 检查登录状态
    if (!authManager.checkLoginStatus()) {
      console.log('用户未登录，跳过云端同步');
      return localResults;
    }

    const openid = authManager.getUserInfo()?.openid || wx.getStorageSync('openid');
    if (!openid) {
      console.log('未找到 openid，跳过云端同步');
      return localResults;
    }

    // 过滤出需要上传的结果（没有 cloudId 的）
    const resultsToUpload = localResults.filter(item => !item.cloudId);

    if (resultsToUpload.length > 0) {
      console.log(`准备上传 ${resultsToUpload.length} 个结果到云端`);

      // 批量上传结果
      for (const result of resultsToUpload) {
        try {
          const uploadData = {
            openid: openid,
            result: {
              id: result.id,
              brandName: result.brandName,
              results: result.results,
              tags: result.tags,
              category: result.category,
              notes: result.notes,
              timestamp: result.timestamp,
              createdAt: result.createdAt || new Date(result.timestamp).toISOString()
            }
          };

          const uploadRes = await uploadResultApi(uploadData);
          if (uploadRes.status === 'success' && uploadRes.data?.id) {
            // 更新本地结果，添加 cloudId
            result.cloudId = uploadRes.data.id;
            result.syncedAt = new Date().toISOString();
          }
        } catch (error) {
          console.error(`上传结果 ${result.id} 失败:`, error);
        }
      }

      // 更新本地存储
      wx.setStorageSync('savedSearchResults', localResults);
    }

    return localResults;
  } catch (error) {
    console.error('同步到云端失败:', error);
    return localResults;
  }
};

/**
 * 从云端下载用户保存的结果
 * @returns {Promise<Array>} - 云端结果数组
 */
const downloadSavedResultsFromCloud = async () => {
  try {
    // 检查登录状态
    if (!authManager.checkLoginStatus()) {
      console.log('用户未登录，跳过云端下载');
      return [];
    }

    const openid = authManager.getUserInfo()?.openid || wx.getStorageSync('openid');
    if (!openid) {
      console.log('未找到 openid，跳过云端下载');
      return [];
    }

    const downloadData = { openid: openid };
    const downloadRes = await downloadDataApi(downloadData);

    if (downloadRes.status === 'success' && downloadRes.data) {
      // 转换云端数据格式到本地格式
      const cloudResults = downloadRes.data.map(item => ({
        id: item.id || item._id,
        cloudId: item._id || item.id,
        brandName: item.brandName,
        results: item.results,
        tags: item.tags || [],
        category: item.category || '未分类',
        notes: item.notes || '',
        timestamp: new Date(item.createdAt).getTime(),
        createdAt: item.createdAt,
        syncedAt: item.updatedAt || item.createdAt
      }));

      console.log(`从云端下载 ${cloudResults.length} 个结果`);
      return cloudResults;
    }

    return [];
  } catch (error) {
    console.error('从云端下载失败:', error);
    return [];
  }
};

/**
 * 合并本地和云端结果
 * @param {Array} localResults - 本地结果
 * @param {Array} cloudResults - 云端结果
 * @returns {Array} - 合并后的结果（去重）
 */
const mergeLocalAndCloudResults = (localResults, cloudResults) => {
  const mergedMap = new Map();

  // 先添加云端结果
  cloudResults.forEach(item => {
    mergedMap.set(item.id, item);
  });

  // 添加本地结果（如果云端没有）
  localResults.forEach(item => {
    if (!mergedMap.has(item.id)) {
      mergedMap.set(item.id, item);
    } else {
      // 如果云端已有，但本地有 cloudId，保持同步状态
      const cloudItem = mergedMap.get(item.id);
      if (item.cloudId) {
        cloudItem.cloudId = item.cloudId;
        cloudItem.syncedAt = item.syncedAt;
      }
    }
  });

  // 转换为数组并按时间排序
  return Array.from(mergedMap.values()).sort((a, b) => b.timestamp - a.timestamp);
};

/**
 * 获取保存的结果（支持云端同步）
 * @returns {Promise<Array>} - 合并后的结果数组
 */
const getSavedResults = async () => {
  try {
    // 获取本地结果
    const localResults = wx.getStorageSync('savedSearchResults') || [];

    // 如果未登录，只返回本地结果
    if (!authManager.checkLoginStatus()) {
      return localResults;
    }

    // 下载云端结果
    const cloudResults = await downloadSavedResultsFromCloud();

    // 合并本地和云端结果
    const mergedResults = mergeLocalAndCloudResults(localResults, cloudResults);

    // 同步本地结果到云端
    await syncSavedResultsToCloud(mergedResults);

    return mergedResults;
  } catch (error) {
    console.error('获取保存结果失败:', error);
    // 降级处理：返回本地结果
    return wx.getStorageSync('savedSearchResults') || [];
  }
};

/**
 * 保存结果（支持云端同步）
 * @param {Object} result - 结果对象
 * @returns {Promise<Object>} - 保存后的结果
 */
const saveResult = async (result) => {
  try {
    // 获取现有结果
    const savedResults = wx.getStorageSync('savedSearchResults') || [];

    // 检查是否已存在
    const existingIndex = savedResults.findIndex(item => item.id === result.id);

    if (existingIndex >= 0) {
      // 更新现有结果
      savedResults[existingIndex] = result;
    } else {
      // 添加新结果
      savedResults.push(result);
    }

    // 保存到本地
    wx.setStorageSync('savedSearchResults', savedResults);

    // 如果已登录，同步到云端
    if (authManager.checkLoginStatus()) {
      await syncSavedResultsToCloud([result]);
    }

    return result;
  } catch (error) {
    console.error('保存结果失败:', error);
    throw error;
  }
};

/**
 * 删除结果（支持云端同步）
 * @param {string} resultId - 结果 ID
 * @returns {Promise<boolean>} - 是否删除成功
 */
const deleteResult = async (resultId) => {
  try {
    // 获取现有结果
    const savedResults = wx.getStorageSync('savedSearchResults') || [];
    const resultToDelete = savedResults.find(item => item.id === resultId);

    if (!resultToDelete) {
      console.log('结果不存在:', resultId);
      return false;
    }

    // 从本地删除
    const updatedResults = savedResults.filter(item => item.id !== resultId);
    wx.setStorageSync('savedSearchResults', updatedResults);

    // 如果已登录且结果有 cloudId，从云端删除
    if (authManager.checkLoginStatus() && resultToDelete.cloudId) {
      try {
        const openid = authManager.getUserInfo()?.openid || wx.getStorageSync('openid');
        await deleteResultApi({
          openid: openid,
          id: resultToDelete.cloudId
        });
        console.log(`已从云端删除结果 ${resultToDelete.cloudId}`);
      } catch (error) {
        console.error(`从云端删除结果 ${resultToDelete.cloudId} 失败:`, error);
      }
    }

    return true;
  } catch (error) {
    console.error('删除结果失败:', error);
    return false;
  }
};

/**
 * 更新结果（支持云端同步）
 * @param {Object} result - 更新后的结果对象
 * @returns {Promise<Object>} - 更新后的结果
 */
const updateResult = async (result) => {
  try {
    // 获取现有结果
    const savedResults = wx.getStorageSync('savedSearchResults') || [];
    const existingIndex = savedResults.findIndex(item => item.id === result.id);

    if (existingIndex < 0) {
      throw new Error('结果不存在');
    }

    // 更新本地结果
    savedResults[existingIndex] = { ...savedResults[existingIndex], ...result };
    wx.setStorageSync('savedSearchResults', savedResults);

    // 如果已登录且有 cloudId，同步到云端
    if (authManager.checkLoginStatus() && savedResults[existingIndex].cloudId) {
      try {
        const openid = authManager.getUserInfo()?.openid || wx.getStorageSync('openid');
        await uploadResultApi({
          openid: openid,
          result: {
            ...result,
            _id: savedResults[existingIndex].cloudId
          }
        });
        savedResults[existingIndex].syncedAt = new Date().toISOString();
        wx.setStorageSync('savedSearchResults', savedResults);
      } catch (error) {
        console.error(`更新云端结果失败:`, error);
      }
    }

    return savedResults[existingIndex];
  } catch (error) {
    console.error('更新结果失败:', error);
    throw error;
  }
};

module.exports = {
  syncSavedResultsToCloud,
  downloadSavedResultsFromCloud,
  mergeLocalAndCloudResults,
  getSavedResults,
  saveResult,
  deleteResult,
  updateResult
};
