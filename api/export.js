/**
 * PDF 导出 API
 */

const { get } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

/**
 * 导出测试报告为 PDF
 * @param {Object} params - 导出参数
 * @param {string} params.executionId - 测试执行 ID
 * @returns {Promise}
 */
const exportPdfReport = (params) => {
  return new Promise((resolve, reject) => {
    // 注意：PDF 下载需要使用 wx.downloadFile
    const token = wx.getStorageSync('token');
    const header = {
      'Content-Type': 'application/json'
    };
    
    if (token) {
      header['Authorization'] = `Bearer ${token}`;
    }
    
    const url = `${API_ENDPOINTS.EXPORT.PDF}?executionId=${params.executionId}`;
    
    wx.downloadFile({
      url: url,
      header: header,
      success: (res) => {
        if (res.statusCode === 200) {
          // 保存文件
          wx.saveFile({
            tempFilePath: res.tempFilePath,
            success: (saveRes) => {
              resolve({
                status: 'success',
                filePath: saveRes.savedFilePath
              });
            },
            fail: (saveErr) => {
              // 保存失败，但文件已下载
              resolve({
                status: 'success',
                filePath: res.tempFilePath,
                message: '文件已下载，但未保存到相册'
              });
            }
          });
        } else {
          // 请求失败，尝试读取错误信息
          wx.getFileSystemManager().readFile({
            filePath: res.tempFilePath,
            encoding: 'utf8',
            success: (readRes) => {
              try {
                const errorData = JSON.parse(readRes.data);
                reject(new Error(errorData.error || '导出失败'));
              } catch (e) {
                reject(new Error(`导出失败：${res.statusCode}`));
              }
            },
            fail: () => {
              reject(new Error(`导出失败：${res.statusCode}`));
            }
          });
        }
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '网络错误'));
      }
    });
  });
};

module.exports = {
  exportPdfReport
};
