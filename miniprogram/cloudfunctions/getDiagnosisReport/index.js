/**
 * 云函数：获取完整诊断报告
 *
 * 功能：
 * 1. 调用后端 API 获取完整诊断报告
 * 2. 支持错误处理和降级策略
 * 3. 确保用户始终获得有意义的反馈
 *
 * 架构设计：
 * - 使用 Axios 调用后端 HTTP API
 * - 失败时返回友好的错误信息
 * - 支持超时保护
 *
 * @author 系统架构组
 * @date: 2026-03-07
 * @version: 1.0.0
 */

const cloud = require('wx-server-sdk');

// 初始化云开发环境
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
});

// ==================== P0-6 修复：API 配置 ====================
// 使用环境变量配置 API 地址，支持开发/生产环境区分
// 配置优先级：环境变量 > 云函数配置 > 默认值
const API_BASE_URL = (function() {
  // 1. 优先使用环境变量（云函数控制台配置）
  if (process.env.API_BASE_URL) {
    console.log('[配置] 使用环境变量 API_BASE_URL:', process.env.API_BASE_URL);
    return process.env.API_BASE_URL;
  }
  
  // 2. 使用云函数配置（config 集合）
  // 注意：需要在云开发控制台创建 config 集合，并添加文档 { _id: 'system', apiBaseUrl: 'xxx' }
  // 由于云函数初始化时无法异步获取，这里使用硬编码的生产环境配置
  // 生产环境配置 - 请根据实际部署域名修改
  const PRODUCTION_API_URL = 'https://api.your-domain.com';  // TODO: 替换为实际生产域名
  
  // 3. 开发环境配置
  const DEVELOPMENT_API_URL = 'http://localhost:5001';
  
  // 根据云函数环境判断使用哪个配置
  const env = process.env.WX_CONTEXT_ENV_ID || 'production';
  if (env.includes('dev') || env.includes('test')) {
    console.log('[配置] 开发环境:', DEVELOPMENT_API_URL);
    return DEVELOPMENT_API_URL;
  }
  
  console.log('[配置] 生产环境:', PRODUCTION_API_URL);
  return PRODUCTION_API_URL;
})();

// P0-6 修复：配置验证
function validateApiConfig() {
  if (!API_BASE_URL) {
    console.error('[配置错误] API_BASE_URL 未配置');
    return false;
  }
  
  if (API_BASE_URL === 'YOUR_API_URL_HERE' || 
      API_BASE_URL === 'https://api.example.com' ||
      API_BASE_URL === 'http://localhost:5001') {
    console.warn('[配置警告] API_BASE_URL 使用默认值，可能无法连接：', API_BASE_URL);
    // 注意：不阻止执行，仅记录警告
  }
  
  // 验证 URL 格式
  try {
    new URL(API_BASE_URL);
    return true;
  } catch (e) {
    console.error('[配置错误] API_BASE_URL 格式不正确:', API_BASE_URL);
    return false;
  }
}

// 在模块加载时验证配置
const isConfigValid = validateApiConfig();
if (!isConfigValid) {
  console.error('[严重错误] API 配置验证失败，云函数可能无法正常工作');
}
// ==================== P0-6 修复结束 ====================

/**
 * 云函数入口函数
 * @param {Object} event - 触发事件
 * @param {string} event.executionId - 执行 ID
 * @returns {Promise<Object>} 报告数据或错误信息
 */
exports.main = async (event, context) => {
  const { executionId } = event;

  console.log('[getDiagnosisReport] 开始获取报告，executionId:', executionId);

  if (!executionId) {
    console.error('[getDiagnosisReport] 缺少执行 ID');
    return {
      success: false,
      error: '缺少执行 ID',
      suggestion: '请检查执行 ID 是否正确'
    };
  }

  try {
    // 使用 axios 调用后端 API
    const axios = require('axios');

    console.log('[getDiagnosisReport] 调用后端 API:', `${API_BASE_URL}/api/diagnosis/report/${executionId}`);

    const response = await axios.get(`${API_BASE_URL}/api/diagnosis/report/${executionId}`, {
      timeout: 30000,  // 30 秒超时
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'WeChat-Miniprogram/1.0'
      }
    });

    const report = response.data;

    console.log('[getDiagnosisReport] 获取成功:', {
      executionId,
      hasReport: !!report,
      hasResults: !!(report && report.results),
      hasValidation: !!(report && report.validation)
    });

    // 检查报告是否为空或错误
    if (!report) {
      console.warn('[getDiagnosisReport] 报告为空');
      return createEmptyReport('报告不存在', 'not_found', executionId);
    }

    // 检查报告是否为错误响应
    if (report.error) {
      console.warn('[getDiagnosisReport] 报告包含错误:', report.error);
      return {
        success: false,
        ...report
      };
    }

    // 返回成功结果
    return {
      success: true,
      data: report
    };

  } catch (error) {
    console.error('[getDiagnosisReport] 调用失败:', executionId, error.message);

    // 根据错误类型返回不同的降级响应
    if (error.code === 'ECONNREFUSED') {
      return createEmptyReport('后端服务不可连接', 'server_error', executionId);
    } else if (error.code === 'ETIMEDOUT') {
      return createEmptyReport('请求超时，请稍后重试', 'timeout', executionId);
    } else if (error.response && error.response.status === 404) {
      return createEmptyReport('报告不存在或尚未生成', 'not_found', executionId);
    } else if (error.response && error.response.status >= 500) {
      return createEmptyReport('服务器错误，请稍后重试', 'server_error', executionId);
    } else {
      return createEmptyReport('获取报告失败：' + (error.message || '未知错误'), 'error', executionId);
    }
  }
};

/**
 * 创建空报告响应（降级策略）
 * @param {string} message - 错误信息
 * @param {string} type - 错误类型
 * @param {string} executionId - 执行 ID
 * @returns {Object} 空报告结构
 */
function createEmptyReport(message, type, executionId) {
  const suggestions = {
    'not_found': '请检查执行 ID 是否正确，或重新进行诊断',
    'error': '请稍后重试或联系技术支持',
    'timeout': '诊断处理时间过长，建议减少品牌数量后重试',
    'server_error': '服务器暂时不可用，请稍后重试'
  };

  return {
    success: false,
    error: {
      status: type,
      message: message,
      suggestion: suggestions[type] || '请稍后重试'
    },
    report: {},
    results: [],
    analysis: {},
    brandDistribution: { data: {}, total_count: 0 },
    sentimentDistribution: { data: { positive: 0, neutral: 0, negative: 0 }, total_count: 0 },
    keywords: [],
    validation: {
      is_valid: false,
      errors: [message],
      warnings: [],
      quality_score: 0
    },
    meta: {
      generated_at: new Date().toISOString(),
      execution_id: executionId || '',
      version: '2.0.0'
    }
  };
}
