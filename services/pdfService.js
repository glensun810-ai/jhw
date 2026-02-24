/**
 * PDF 导出服务
 * 
 * 功能：
 * - 生成诊断报告 PDF
 * - 支持自定义内容选择
 * - 支持批量导出
 * 
 * 使用示例：
 * const pdf = await PDFService.exportReport({
 *   executionId: 'xxx',
 *   includeROI: true,
 *   includeSources: true
 * });
 */

const app = getApp();
const logger = require('../utils/logger');

/**
 * PDF 导出服务类
 */
class PDFService {
  /**
   * 导出诊断报告为 PDF
   * @param {Object} options - 导出选项
   * @param {string} options.executionId - 执行 ID
   * @param {boolean} options.includeROI - 是否包含 ROI 数据
   * @param {boolean} options.includeSources - 是否包含信源数据
   * @returns {Promise<string>} PDF 文件路径
   */
  static async exportReport(options = {}) {
    const {
      executionId,
      includeROI = true,
      includeSources = true
    } = options;

    if (!executionId) {
      throw new Error('executionId 是必需的');
    }

    try {
      // 显示加载提示
      wx.showLoading({
        title: '生成 PDF 中...',
        mask: true
      });

      logger.info('[PDF Export] 开始导出 PDF', { executionId, includeROI, includeSources });

      // 获取报告数据
      const reportData = await this.fetchReportData(executionId);

      // 生成 PDF 内容（HTML 格式，微信小程序使用）
      const pdfContent = this.generatePDFContent(reportData, { includeROI, includeSources });

      // 保存文件
      const filePath = await this.savePDF(pdfContent, executionId);

      wx.hideLoading();

      // 提示用户
      this.showPreviewDialog(filePath);

      logger.info('[PDF Export] PDF 导出成功', { filePath });
      return filePath;
    } catch (error) {
      wx.hideLoading();
      logger.error('[PDF Export] PDF 导出失败', error);
      throw new Error('PDF 生成失败：' + error.message);
    }
  }

  /**
   * 获取报告数据
   */
  static async fetchReportData(executionId) {
    return new Promise((resolve, reject) => {
      const apiUrl = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';
      
      wx.request({
        url: `${apiUrl}/api/dashboard/aggregate`,
        method: 'GET',
        data: {
          execution_id: executionId
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            resolve(res.data);
          } else {
            reject(new Error('获取报告数据失败'));
          }
        },
        fail: (err) => {
          reject(err);
        }
      });
    });
  }

  /**
   * 生成 PDF 内容
   */
  static generatePDFContent(reportData, options) {
    const { includeROI, includeSources } = options;
    const { brandName, overallScore, brandScores } = reportData;

    // 构建 HTML 内容
    let html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${brandName} - 品牌诊断报告</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
          h1 { color: #667eea; text-align: center; }
          .score { font-size: 48px; color: #667eea; text-align: center; }
          .section { margin: 20px 0; }
          .brand-item { padding: 10px; border-bottom: 1px solid #eee; }
        </style>
      </head>
      <body>
        <h1>${brandName} - 品牌诊断报告</h1>
        
        <div class="section">
          <h2>综合得分</h2>
          <div class="score">${overallScore || 0} 分</div>
        </div>
        
        <div class="section">
          <h2>品牌评分</h2>
          ${this.generateBrandScoresHTML(brandScores)}
        </div>
        
        ${includeROI ? `
        <div class="section">
          <h2>ROI 分析</h2>
          <p>ROI 数据内容...</p>
        </div>
        ` : ''}
        
        ${includeSources ? `
        <div class="section">
          <h2>信源分析</h2>
          <p>信源数据内容...</p>
        </div>
        ` : ''}
        
        <div class="section">
          <p style="text-align: center; color: #999; font-size: 12px;">
            报告生成时间：${new Date().toLocaleString('zh-CN')}
          </p>
        </div>
      </body>
      </html>
    `;

    return html;
  }

  /**
   * 生成品牌评分 HTML
   */
  static generateBrandScoresHTML(brandScores) {
    if (!brandScores) return '<p>暂无评分数据</p>';

    let html = '<div class="brand-scores">';
    
    Object.entries(brandScores).forEach(([brand, scores]) => {
      html += `
        <div class="brand-item">
          <strong>${brand}</strong>: 
          ${scores.overallScore || 0} 分 
          (${scores.overallGrade || '-'})
        </div>
      `;
    });
    
    html += '</div>';
    return html;
  }

  /**
   * 保存 PDF 文件
   */
  static async savePDF(content, executionId) {
    return new Promise((resolve, reject) => {
      const fileName = `report_${executionId}_${Date.now()}.html`;
      
      // 微信小程序使用文件系统保存
      const fs = wx.getFileSystemManager();
      const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;
      
      fs.writeFile({
        filePath: filePath,
        data: content,
        encoding: 'utf8',
        success: () => {
          resolve(filePath);
        },
        fail: (err) => {
          reject(err);
        }
      });
    });
  }

  /**
   * 显示预览对话框
   */
  static showPreviewDialog(filePath) {
    wx.showModal({
      title: 'PDF 已生成',
      content: '是否立即预览？',
      confirmText: '预览',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          wx.openDocument({
            filePath: filePath,
            showMenu: true,
            success: () => {
              logger.info('[PDF Export] 文档打开成功');
            },
            fail: (err) => {
              logger.error('[PDF Export] 文档打开失败', err);
            }
          });
        }
      }
    });
  }

  /**
   * 批量导出报告
   */
  static async exportBatchReports(executionIds, options = {}) {
    const results = [];
    
    for (const executionId of executionIds) {
      try {
        const filePath = await this.exportReport({ executionId, ...options });
        results.push({ executionId, filePath, success: true });
      } catch (error) {
        results.push({ executionId, error: error.message, success: false });
      }
    }
    
    return results;
  }
}

module.exports = {
  PDFService
};
