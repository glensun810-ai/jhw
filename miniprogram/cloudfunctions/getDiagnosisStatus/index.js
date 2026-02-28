/**
 * 云函数：获取诊断任务状态
 *
 * 功能：
 * 1. 调用后端 API 获取任务状态
 * 2. 返回给前端轮询使用
 *
 * @author 系统架构组
 * @date 2026-02-28
 */

const cloud = require('wx-server-sdk');

// 初始化云开发环境
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
});

// 后端 API 配置
const API_BASE_URL = 'http://localhost:5001';  // 开发环境
// const API_BASE_URL = 'https://your-domain.com';  // 生产环境

/**
 * 云函数入口函数
 * @param {Object} event - 触发事件
 * @param {string} event.executionId - 任务执行 ID
 * @returns {Promise<Object>} 任务状态数据
 */
exports.main = async (event, context) => {
  const { executionId } = event;

  console.log('[getDiagnosisStatus] 开始获取任务状态，executionId:', executionId);

  if (!executionId) {
    console.error('[getDiagnosisStatus] 缺少执行 ID');
    return {
      success: false,
      error: '缺少执行 ID'
    };
  }

  try {
    // P0 修复：使用 wx-cloud-http 代替 fetch（微信云函数不支持 fetch）
    const axios = require('axios');
    
    const response = await axios.get(`${API_BASE_URL}/test/status/${executionId}`, {
      timeout: 10000
    });

    const data = response.data;

    console.log('[getDiagnosisStatus] 获取成功:', {
      executionId,
      status: data?.status,
      progress: data?.progress,
      stage: data?.stage,
      should_stop_polling: data?.should_stop_polling
    });

    return {
      success: true,
      data: data
    };

  } catch (error) {
    console.error('[getDiagnosisStatus] 调用失败:', executionId, error.message);

    return {
      success: false,
      error: error.message,
      errorCode: error.code || 'UNKNOWN_ERROR'
    };
  }
};
