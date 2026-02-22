/**
 * PDF 导出工具 - 兼容层
 * 
 * 说明：此文件为向后兼容的导出层
 * 新功能请使用：const { PDFService } = require('../services/pdfService');
 */

const { PDFService } = require('../services/pdfService');

/**
 * 导出诊断报告为 PDF（兼容旧接口）
 * @deprecated 请使用 PDFService.exportReport()
 */
async function exportToPDF(options = {}) {
  console.warn('[DEPRECATED] exportToPDF 已废弃，请使用 PDFService.exportReport()');
  return PDFService.exportReport(options);
}

/**
 * 批量导出报告（兼容旧接口）
 * @deprecated 请使用 PDFService.exportBatchReports()
 */
async function exportBatchReports(executionIds, options = {}) {
  console.warn('[DEPRECATED] exportBatchReports 已废弃，请使用 PDFService.exportBatchReports()');
  return PDFService.exportBatchReports(executionIds, options);
}

module.exports = {
  exportToPDF,
  exportBatchReports,
  PDFService
};
