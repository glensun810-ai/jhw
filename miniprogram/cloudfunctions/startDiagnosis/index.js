/**
 * 云函数：startDiagnosis - 启动品牌诊断任务
 *
 * 功能：
 * 1. 接收前端诊断请求参数
 * 2. 调用后端 API 启动诊断任务
 * 3. 返回执行 ID 给前端用于轮询进度
 *
 * 请求参数：
 * - brand_list: 品牌列表 [主品牌，竞品 1, 竞品 2, ...]
 * - selectedModels: 选中的 AI 模型列表
 * - custom_question: 自定义问题（字符串）
 * - customQuestions: 自定义问题列表（数组，可选）
 * - userOpenid: 用户 OpenID（可选，从云函数上下文自动获取）
 * - userLevel: 用户等级（可选，默认 'Free'）
 *
 * 返回结果：
 * - success: 是否成功
 * - execution_id: 执行 ID（用于轮询进度）
 * - report_id: 报告 ID（可选）
 * - error: 错误信息（如果失败）
 *
 * @author 系统架构组
 * @date 2026-03-02
 * @version 1.0.0
 */

const cloud = require('wx-server-sdk');

// 初始化云开发环境
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
});

// 后端 API 配置
// 开发环境
const API_BASE_URL_DEV = 'http://localhost:5001';
// 生产环境（请替换为实际域名，例如：https://api.jinshuai.wang）
const API_BASE_URL_PROD = process.env.API_BASE_URL || 'https://your-domain.com';

// 获取当前环境
// 在微信云开发中，process.env.NODE_ENV 通常为 undefined 或 'production'
const isDevelopment = process.env.NODE_ENV === 'development' || !process.env.NODE_ENV;
const API_BASE_URL = isDevelopment ? API_BASE_URL_DEV : API_BASE_URL_PROD;

// 超时配置（毫秒）
const API_TIMEOUT = 30000; // 30 秒

/**
 * 验证请求参数
 * @param {Object} params - 请求参数
 * @returns {Object} 验证结果 { valid: boolean, error: string }
 */
function validateParams(params) {
  // 验证品牌列表
  if (!params.brand_list || !Array.isArray(params.brand_list)) {
    return {
      valid: false,
      error: 'brand_list 必须是非空数组'
    };
  }

  if (params.brand_list.length === 0) {
    return {
      valid: false,
      error: 'brand_list 不能为空'
    };
  }

  // 验证每个品牌名称
  for (let i = 0; i < params.brand_list.length; i++) {
    const brand = params.brand_list[i];
    if (typeof brand !== 'string') {
      return {
        valid: false,
        error: `第 ${i + 1} 个品牌必须是字符串`
      };
    }
    if (brand.length === 0 || brand.length > 100) {
      return {
        valid: false,
        error: `第 ${i + 1} 个品牌名称长度必须在 1-100 字符`
      };
    }
  }

  // 验证模型列表
  if (!params.selectedModels || !Array.isArray(params.selectedModels)) {
    return {
      valid: false,
      error: 'selectedModels 必须是非空数组'
    };
  }

  if (params.selectedModels.length === 0) {
    return {
      valid: false,
      error: '至少选择一个 AI 模型'
    };
  }

  // 验证问题（custom_question 或 customQuestions 至少有一个）
  const hasQuestion = params.custom_question || 
                      (params.customQuestions && Array.isArray(params.customQuestions));
  
  if (!hasQuestion) {
    return {
      valid: false,
      error: '必须提供 custom_question 或 customQuestions'
    };
  }

  if (params.custom_question && typeof params.custom_question !== 'string') {
    return {
      valid: false,
      error: 'custom_question 必须是字符串'
    };
  }

  if (params.customQuestions && !Array.isArray(params.customQuestions)) {
    return {
      valid: false,
      error: 'customQuestions 必须是数组'
    };
  }

  return { valid: true, error: null };
}

/**
 * 规范化请求参数
 * @param {Object} params - 原始参数
 * @param {string} userOpenid - 用户 OpenID
 * @returns {Object} 规范化后的参数
 */
function normalizeParams(params, userOpenid) {
  const normalized = {
    brand_list: params.brand_list,
    selectedModels: params.selectedModels,
    userOpenid: params.userOpenid || userOpenid,
    userLevel: params.userLevel || 'Free'
  };

  // 处理问题参数
  if (params.custom_question) {
    normalized.custom_question = params.custom_question;
  } else if (params.customQuestions) {
    normalized.customQuestions = params.customQuestions;
  }

  return normalized;
}

/**
 * 云函数入口函数
 * @param {Object} event - 触发事件
 * @param {Object} context - 云函数上下文
 * @returns {Promise<Object>} 诊断任务启动结果
 */
exports.main = async (event, context) => {
  const startTime = Date.now();
  const wxContext = cloud.getWXContext();

  console.log('[startDiagnosis] ========== 开始启动诊断 ==========');
  console.log('[startDiagnosis] 请求参数:', JSON.stringify(event, null, 2));
  console.log('[startDiagnosis] 用户 OpenID:', wxContext.OPENID);
  console.log('[startDiagnosis] 环境:', isDevelopment ? '开发' : '生产');
  console.log('[startDiagnosis] API 地址:', API_BASE_URL);

  // 1. 参数验证
  const validation = validateParams(event);
  if (!validation.valid) {
    console.error('[startDiagnosis] 参数验证失败:', validation.error);
    return {
      success: false,
      error: validation.error,
      errorCode: 'INVALID_PARAMS'
    };
  }

  // 2. 规范化参数
  const normalizedParams = normalizeParams(event, wxContext.OPENID);
  console.log('[startDiagnosis] 规范化后的参数:', JSON.stringify(normalizedParams, null, 2));

  try {
    // 3. 调用后端 API
    console.log('[startDiagnosis] 正在调用后端 API...');
    
    const axios = require('axios');
    
    const response = await axios.post(
      `${API_BASE_URL}/api/perform-brand-test`,
      normalizedParams,
      {
        timeout: API_TIMEOUT,
        headers: {
          'Content-Type': 'application/json',
          // 如果需要认证，可以在此添加
          // 'Authorization': `Bearer ${token}`
        }
      }
    );

    const elapsed = Date.now() - startTime;
    console.log('[startDiagnosis] 后端 API 响应时间:', elapsed, 'ms');
    console.log('[startDiagnosis] 后端 API 响应:', JSON.stringify(response.data, null, 2));

    // 4. 检查后端响应
    if (!response.data) {
      throw new Error('后端 API 返回空响应');
    }

    // 5. 返回结果给前端
    const result = {
      success: true,
      execution_id: response.data.execution_id || response.data.data?.execution_id,
      report_id: response.data.report_id || response.data.data?.report_id,
      message: response.data.message || '诊断任务已启动',
      elapsedTime: elapsed
    };

    // 如果后端返回了额外数据，也传递给前端
    if (response.data.status) {
      result.status = response.data.status;
    }

    console.log('[startDiagnosis] ========== 诊断启动成功 ==========');
    console.log('[startDiagnosis] 返回结果:', JSON.stringify(result, null, 2));

    return result;

  } catch (error) {
    const elapsed = Date.now() - startTime;
    console.error('[startDiagnosis] ========== 诊断启动失败 ==========');
    console.error('[startDiagnosis] 错误类型:', error.constructor.name);
    console.error('[startDiagnosis] 错误消息:', error.message);
    console.error('[startDiagnosis] 耗时:', elapsed, 'ms');

    // 详细错误日志
    if (error.response) {
      // 后端返回了错误响应
      console.error('[startDiagnosis] 后端错误响应:', error.response.status, error.response.data);
      return {
        success: false,
        error: `后端 API 错误 (${error.response.status}): ${JSON.stringify(error.response.data)}`,
        errorCode: 'BACKEND_ERROR',
        statusCode: error.response.status,
        backendError: error.response.data
      };
    } else if (error.request) {
      // 请求已发送但未收到响应
      console.error('[startDiagnosis] 未收到后端响应:', error.request);
      return {
        success: false,
        error: '未收到后端 API 响应，请检查网络连接或后端服务状态',
        errorCode: 'NO_RESPONSE',
        requestPath: error.request.path
      };
    } else {
      // 其他错误
      console.error('[startDiagnosis] 请求配置错误:', error.message);
      return {
        success: false,
        error: `启动诊断失败：${error.message}`,
        errorCode: 'UNKNOWN_ERROR'
      };
    }
  }
};

/**
 * 使用示例:
 *
 * // 在小程序中调用
 * wx.cloud.callFunction({
 *   name: 'startDiagnosis',
 *   data: {
 *     brand_list: ['华为', '小米', 'OPPO'],
 *     selectedModels: [
 *       { name: 'doubao', checked: true },
 *       { name: 'deepseek', checked: true }
 *     ],
 *     custom_question: '请分析华为的品牌优势和市场定位？',
 *     userLevel: 'Premium'
 *   }
 * }).then(res => {
 *   if (res.result.success) {
 *     console.log('诊断启动成功:', res.result.execution_id);
 *     // 使用 execution_id 轮询进度
 *   } else {
 *     console.error('诊断启动失败:', res.result.error);
 *   }
 * });
 */
