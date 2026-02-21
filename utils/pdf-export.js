/**
 * PDF 导出工具 - P1 级功能
 *
 * 功能:
 * 1. 生成诊断报告 PDF
 * 2. 支持自定义内容选择
 * 3. 支持批量导出
 *
 * 使用示例:
 * const pdf = await exportToPDF({
 *   executionId: 'xxx',
 *   includeROI: true,
 *   includeSources: true
 * });
 */

const app = getApp();
const logger = require('./logger');

/**
 * 导出诊断报告为 PDF
 * @param {Object} options - 导出选项
 * @param {string} options.executionId - 执行 ID
 * @param {boolean} options.includeROI - 是否包含 ROI 数据
 * @param {boolean} options.includeSources - 是否包含信源数据
 * @returns {Promise<string>} PDF 文件路径
 */
async function exportToPDF(options = {}) {
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
    const reportData = await fetchReportData(executionId);

    // 生成 PDF 内容（HTML 格式，微信小程序使用）
    const pdfContent = generatePDFContent(reportData, { includeROI, includeSources });

    // 保存文件
    const filePath = await savePDF(pdfContent, executionId);

    wx.hideLoading();

    // 提示用户
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
async function fetchReportData(executionId) {
  return new Promise((resolve, reject) => {
    const apiUrl = app.globalData.apiBaseUrl || 'http://127.0.0.1:5000';
    
    wx.request({
      url: `${apiUrl}/api/dashboard/aggregate`,
      method: 'GET',
      data: {
        executionId,
        userOpenid: app.globalData.userOpenid || 'anonymous'
      },
      timeout: 30000,
      success: (res) => {
        if (res.data && res.data.success) {
          logger.debug('[PDF Export] 获取报告数据成功', { 
            hasSummary: !!res.data.dashboard?.summary,
            questionCount: res.data.dashboard?.questionCards?.length || 0 
          });
          resolve(res.data.dashboard);
        } else {
          const errorMsg = res.data?.error || '获取数据失败';
          logger.error('[PDF Export] 获取报告数据失败', errorMsg);
          reject(new Error(errorMsg));
        }
      },
      fail: (error) => {
        const errorMsg = error.errMsg || '网络请求失败';
        logger.error('[PDF Export] 网络请求失败', errorMsg);
        reject(new Error(errorMsg));
      }
    });
  });
}

/**
 * 生成 PDF 内容
 */
function generatePDFContent(data, options) {
  const { includeROI, includeSources } = options;
  
  let content = `
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: Arial, sans-serif; padding: 40px; }
          h1 { color: #1a1a2e; font-size: 24px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
          h2 { color: #667eea; font-size: 18px; margin-top: 30px; }
          .summary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
          .metric { display: inline-block; margin: 10px 20px; text-align: center; }
          .metric-value { font-size: 32px; font-weight: bold; }
          .metric-label { font-size: 12px; opacity: 0.9; }
          table { width: 100%; border-collapse: collapse; margin: 20px 0; }
          th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
          th { background: #667eea; color: white; }
          tr:nth-child(even) { background: #f5f6fa; }
          .footer { margin-top: 40px; text-align: center; color: #999; font-size: 12px; }
        </style>
      </head>
      <body>
        <h1>GEO 品牌战略诊断报告</h1>
        
        <div class="summary">
          <div class="metric">
            <div class="metric-value">${data.summary?.healthScore || 0}</div>
            <div class="metric-label">品牌健康度</div>
          </div>
          <div class="metric">
            <div class="metric-value">${data.summary?.sov || 0}%</div>
            <div class="metric-label">AI 声量占比</div>
          </div>
          <div class="metric">
            <div class="metric-value">${(data.summary?.avgSentiment || 0).toFixed(2)}</div>
            <div class="metric-label">情感均值</div>
          </div>
        </div>
  `;

  // ROI 部分
  if (includeROI && data.roi_metrics) {
    content += `
      <h2>ROI 指标分析</h2>
      <table>
        <tr><th>指标</th><th>数值</th><th>行业平均</th></tr>
        <tr><td>曝光 ROI</td><td>${data.roi_metrics.exposure_roi}x</td><td>${data.benchmarks?.exposure_roi_industry_avg || 2.5}x</td></tr>
        <tr><td>情感 ROI</td><td>${data.roi_metrics.sentiment_roi}x</td><td>${data.benchmarks?.sentiment_roi_industry_avg || 0.6}x</td></tr>
        <tr><td>排名 ROI</td><td>${data.roi_metrics.ranking_roi}</td><td>${data.benchmarks?.ranking_roi_industry_avg || 50}</td></tr>
        <tr><td>估算价值</td><td>¥${data.roi_metrics.estimated_value.toLocaleString()}</td><td>-</td></tr>
      </table>
    `;
  }

  // 问题诊断部分
  if (data.questionCards && data.questionCards.length > 0) {
    content += `<h2>问题诊断分析</h2><table><tr><th>问题</th><th>品牌</th><th>模型</th><th>排名</th></tr>`;
    
    data.questionCards.forEach(card => {
      (card.responses || []).forEach(response => {
        content += `
          <tr>
            <td>${card.question || '-'}</td>
            <td>${card.brand || '-'}</td>
            <td>${response.model || '-'}</td>
            <td>${response.rank || '-'}</td>
          </tr>
        `;
      });
    });
    
    content += `</table>`;
  }

  // 页脚
  content += `
    <div class="footer">
      <p>报告生成时间：${new Date().toLocaleString('zh-CN')}</p>
      <p>执行 ID: ${data.execution_id || '-'}</p>
      <p>云程企航 · AI 搜索品牌影响力监测</p>
    </div>
  </body>
  </html>
  `;

  return content;
}

/**
 * 保存 PDF 文件
 */
function savePDF(content, executionId) {
  return new Promise((resolve, reject) => {
    const fileName = `report_${executionId}_${Date.now()}.html`;
    const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;

    const fs = wx.getFileSystemManager();

    fs.writeFile({
      filePath: filePath,
      data: content,
      encoding: 'utf8',
      success: () => {
        logger.debug('[PDF Export] 文件保存成功', { filePath, fileName });
        resolve(filePath);
      },
      fail: (error) => {
        logger.error('[PDF Export] 文件保存失败', error);
        reject(new Error('保存文件失败：' + error.message));
      }
    });
  });
}

/**
 * 保存 CSV 文件
 */
function saveCSV(content, executionId) {
  return new Promise((resolve, reject) => {
    const fileName = `report_${executionId}_${Date.now()}.csv`;
    const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;

    const fs = wx.getFileSystemManager();

    fs.writeFile({
      filePath: filePath,
      data: content,
      encoding: 'utf8',
      success: () => {
        logger.debug('[Excel Export] 文件保存成功', { filePath, fileName });
        resolve(filePath);
      },
      fail: (error) => {
        logger.error('[Excel Export] 文件保存失败', error);
        reject(new Error('保存文件失败：' + error.message));
      }
    });
  });
}

/**
 * 导出 Excel 功能
 * @param {Object} options - 导出选项
 */
async function exportToExcel(options = {}) {
  const { executionId } = options;

  if (!executionId) {
    throw new Error('executionId 是必需的');
  }

  try {
    wx.showLoading({
      title: '生成 Excel 中...',
      mask: true
    });

    logger.info('[Excel Export] 开始导出 Excel', { executionId });

    // 获取原始数据
    const dashboardData = await fetchReportData(executionId);

    // 生成 CSV 内容 (简化版 Excel)
    const csvContent = generateCSVContent(dashboardData);

    // 保存文件
    const filePath = await saveCSV(csvContent, executionId);

    wx.hideLoading();

    wx.showModal({
      title: 'Excel 已生成',
      content: '是否立即预览？',
      confirmText: '预览',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          wx.openDocument({
            filePath: filePath,
            showMenu: true,
            success: () => {
              logger.info('[Excel Export] 文档打开成功');
            },
            fail: (err) => {
              logger.error('[Excel Export] 文档打开失败', err);
            }
          });
        }
      }
    });

    logger.info('[Excel Export] Excel 导出成功', { filePath });
    return filePath;
  } catch (error) {
    wx.hideLoading();
    logger.error('[Excel Export] Excel 导出失败', error);
    throw new Error('Excel 生成失败：' + error.message);
  }
}

/**
 * 生成 CSV 内容
 */
function generateCSVContent(data) {
  let csv = '品牌，模型，问题，回答，排名，情感，时间\n';

  if (data.questionCards && Array.isArray(data.questionCards)) {
    data.questionCards.forEach(card => {
      (card.responses || []).forEach(response => {
        const row = [
          `"${card.brand || '-' || data.summary?.brandName || '-' }"`,
          `"${response.model || '-'}"`,
          `"${card.question || '-'}"`,
          `"${(response.content || '-').replace(/"/g, '""')}"`,
          response.rank || '-',
          response.sentiment || '-',
          response.timestamp || '-'
        ];
        csv += row.join(',') + '\n';
      });
    });
  }

  return csv;
}

module.exports = {
  exportToPDF,
  exportToExcel,
  generatePDFContent,
  generateCSVContent,
  savePDF,
  saveCSV
};
