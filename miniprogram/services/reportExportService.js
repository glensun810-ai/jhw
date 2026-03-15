/**
 * 报告导出服务
 * 
 * 功能:
 * - 导出 Excel 格式
 * - 导出 HTML 格式（用于转长图）
 * - 导出长图
 * - 批量导出
 * 
 * @author: 系统架构组
 * @date: 2026-03-14
 * @version: 1.0.0
 */

import { request } from '../../utils/request';

class ReportExportService {
  /**
   * 导出 Excel 格式报告
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Blob>} Excel 文件 Blob
   */
  async exportToExcel(executionId) {
    try {
      const envVersion = this._getEnvVersion();
      
      // 开发环境：HTTP 直连
      if (envVersion === 'develop' || envVersion === 'trial') {
        return await this._exportToExcelViaHttp(executionId);
      }
      
      // 生产环境：云函数
      return await this._exportToExcelViaCloudFunction(executionId);
      
    } catch (error) {
      console.error('[ExportService] Excel 导出失败:', error);
      throw error;
    }
  }
  
  /**
   * HTTP 方式导出 Excel
   * @private
   */
  async _exportToExcelViaHttp(executionId) {
    const baseUrl = this._getBaseUrl();
    const url = `${baseUrl}/api/diagnosis/export/${executionId}/excel`;
    
    try {
      const response = await wx.request({
        url: url,
        method: 'GET',
        responseType: 'arraybuffer',
        header: {
          'Content-Type': 'application/json'
        }
      });
      
      if (response.statusCode === 200) {
        // 创建 Blob
        const blob = new Blob([response.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        });
        
        console.log('[ExportService] ✅ Excel 导出成功');
        return blob;
      } else {
        throw new Error(`HTTP ${response.statusCode}`);
      }
    } catch (error) {
      console.error('[ExportService] HTTP Excel 导出失败:', error);
      throw error;
    }
  }
  
  /**
   * 云函数方式导出 Excel
   * @private
   */
  async _exportToExcelViaCloudFunction(executionId) {
    try {
      const res = await wx.cloud.callFunction({
        name: 'exportReport',
        data: {
          executionId,
          format: 'excel'
        },
        timeout: 30000
      });
      
      console.log('[ExportService] ✅ 云函数 Excel 导出成功');
      return res.result.file;
      
    } catch (error) {
      console.error('[ExportService] 云函数 Excel 导出失败:', error);
      throw error;
    }
  }
  
  /**
   * 导出 HTML 格式报告
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} HTML 内容
   */
  async exportToHtml(executionId) {
    try {
      const res = await request({
        url: `/api/diagnosis/export/${executionId}/html`,
        method: 'GET'
      });
      
      return res.data || {};
    } catch (error) {
      console.error('[ExportService] HTML 导出失败:', error);
      throw error;
    }
  }
  
  /**
   * 导出长图
   * @param {string} executionId - 执行 ID
   * @returns {Promise<Object>} 长图数据
   */
  async exportToImage(executionId) {
    try {
      const res = await request({
        url: `/api/diagnosis/export/${executionId}/image`,
        method: 'POST'
      });
      
      return res.data || {};
    } catch (error) {
      console.error('[ExportService] 长图导出失败:', error);
      throw error;
    }
  }
  
  /**
   * 保存文件到本地
   * @param {Blob} blob - 文件 Blob
   * @param {string} filename - 文件名
   */
  async saveFile(blob, filename) {
    try {
      // 微信小程序使用文件系统保存
      const fs = wx.getFileSystemManager();
      
      // 保存到临时目录
      const filePath = `${wx.env.USER_DATA_PATH}/${filename}`;
      
      // 将 Blob 转换为 ArrayBuffer
      const arrayBuffer = await this._blobToArrayBuffer(blob);
      
      // 写入文件
      fs.writeFileSync(filePath, arrayBuffer);
      
      console.log('[ExportService] ✅ 文件已保存:', filePath);
      
      // 提示用户
      wx.showModal({
        title: '导出成功',
        content: `文件已保存到：${filename}\n\n请在电脑端使用微信打开，或转发给文件传输助手`,
        showCancel: false,
        confirmText: '知道了'
      });
      
      return filePath;
      
    } catch (error) {
      console.error('[ExportService] 保存文件失败:', error);
      
      wx.showModal({
        title: '保存失败',
        content: '文件保存失败，请重试',
        showCancel: false
      });
      
      throw error;
    }
  }
  
  /**
   * Blob 转 ArrayBuffer
   * @private
   */
  async _blobToArrayBuffer(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsArrayBuffer(blob);
    });
  }
  
  /**
   * 批量导出
   * @param {Array<string>} executionIds - 执行 ID 列表
   * @param {string} format - 导出格式 (excel | html)
   * @returns {Promise<Object>} 导出结果
   */
  async batchExport(executionIds, format = 'excel') {
    try {
      const res = await request({
        url: '/api/diagnosis/export/batch',
        method: 'POST',
        data: {
          execution_ids: executionIds,
          format
        }
      });
      
      return res.data || {};
    } catch (error) {
      console.error('[ExportService] 批量导出失败:', error);
      throw error;
    }
  }
  
  /**
   * 生成环境版本
   * @private
   */
  _getEnvVersion() {
    const accountInfo = wx.getAccountInfoSync();
    return accountInfo.miniProgram.envVersion || 'release';
  }
  
  /**
   * 获取基础 URL
   * @private
   */
  _getBaseUrl() {
    // 开发环境使用本地服务器
    return 'http://localhost:5001';
  }
  
  /**
   * 下载文件（通用）
   * @param {string} url - 文件 URL
   * @param {string} filename - 文件名
   */
  async downloadFile(url, filename) {
    try {
      const filePath = `${wx.env.USER_DATA_PATH}/${filename}`;
      
      await wx.downloadFile({
        url: url,
        filePath: filePath,
        success: (res) => {
          if (res.statusCode === 200) {
            wx.showModal({
              title: '下载成功',
              content: `文件已保存到：${filename}`,
              showCancel: false
            });
          }
        },
        fail: (error) => {
          console.error('[ExportService] 下载失败:', error);
          wx.showModal({
            title: '下载失败',
            content: '文件下载失败，请重试',
            showCancel: false
          });
        }
      });
      
    } catch (error) {
      console.error('[ExportService] 下载文件失败:', error);
      throw error;
    }
  }
}

export default new ReportExportService();
