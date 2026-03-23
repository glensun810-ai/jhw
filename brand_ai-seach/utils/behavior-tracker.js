/**
 * 用户行为追踪工具
 * 用于记录和分析用户操作轨迹
 */

const { post } = require('../utils/request');
const { API_ENDPOINTS } = require('./config');
const logger = require('./logger');

// 事件分类
const EVENT_CATEGORIES = {
  PAGE_VIEW: 'page_view',
  BUTTON_CLICK: 'button_click',
  API_CALL: 'api_call',
  FORM_SUBMIT: 'form_submit',
  ERROR: 'error',
  CUSTOM: 'custom'
};

// 会话管理
let sessionId = null;
let sessionStartTime = null;

/**
 * 初始化行为追踪
 */
function initTracking() {
  sessionId = generateSessionId();
  sessionStartTime = Date.now();
  
  logger.debug('[BehaviorTracker] 初始化完成', { sessionId });
  
  // 记录页面浏览事件
  trackPageView();
}

/**
 * 生成会话 ID
 */
function generateSessionId() {
  return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 追踪事件
 * @param {string} event - 事件名称
 * @param {string} category - 事件分类
 * @param {Object} properties - 事件属性
 */
function trackEvent(event, category = EVENT_CATEGORIES.CUSTOM, properties = {}) {
  const eventData = {
    event,
    category,
    properties: {
      ...properties,
      sessionId,
      sessionDuration: Date.now() - sessionStartTime,
      page: getCurrentPage(),
      timestamp: Date.now()
    }
  };
  
  logger.debug('[BehaviorTracker] 追踪事件', eventData);
  
  // 异步发送，不阻塞主流程
  post(API_ENDPOINTS.ANALYTICS.TRACK, eventData, { loading: false })
    .then(response => {
      logger.debug('[BehaviorTracker] 事件上报成功', response);
    })
    .catch(error => {
      logger.warn('[BehaviorTracker] 事件上报失败', error);
      // 失败时保存到本地，稍后重试
      saveEventLocally(eventData);
    });
  
  return eventData;
}

/**
 * 追踪页面浏览
 * @param {string} pageName - 页面名称
 */
function trackPageView(pageName = null) {
  const page = pageName || getCurrentPage();
  
  return trackEvent('page_view', EVENT_CATEGORIES.PAGE_VIEW, {
    page,
    pageTitle: getPageTitle(),
    referrer: document.referrer || ''
  });
}

/**
 * 追踪按钮点击
 * @param {string} buttonName - 按钮名称
 * @param {Object} extraData - 额外数据
 */
function trackButtonClick(buttonName, extraData = {}) {
  return trackEvent('button_click', EVENT_CATEGORIES.BUTTON_CLICK, {
    buttonName,
    page: getCurrentPage(),
    ...extraData
  });
}

/**
 * 追踪 API 调用
 * @param {string} apiName - API 名称
 * @param {string} method - HTTP 方法
 * @param {Object} response - 响应数据
 */
function trackApiCall(apiName, method = 'GET', response = {}) {
  return trackEvent('api_call', EVENT_CATEGORIES.API_CALL, {
    apiName,
    method,
    statusCode: response.statusCode,
    duration: response.duration,
    success: response.statusCode >= 200 && response.statusCode < 300
  });
}

/**
 * 追踪表单提交
 * @param {string} formName - 表单名称
 * @param {Object} formData - 表单数据（过滤敏感信息）
 */
function trackFormSubmit(formName, formData = {}) {
  // 过滤敏感信息
  const safeData = filterSensitiveData(formData);
  
  return trackEvent('form_submit', EVENT_CATEGORIES.FORM_SUBMIT, {
    formName,
    fieldCount: Object.keys(safeData).length,
    ...safeData
  });
}

/**
 * 追踪错误
 * @param {string} errorMessage - 错误消息
 * @param {Object} errorDetails - 错误详情
 */
function trackError(errorMessage, errorDetails = {}) {
  return trackEvent('error', EVENT_CATEGORIES.ERROR, {
    errorMessage,
    errorStack: errorDetails.stack || '',
    errorCode: errorDetails.code || 'UNKNOWN',
    page: getCurrentPage()
  });
}

/**
 * 获取当前页面
 */
function getCurrentPage() {
  try {
    const pages = getCurrentPages();
    if (pages && pages.length > 0) {
      return pages[pages.length - 1].route;
    }
  } catch (e) {
    // 忽略错误
  }
  return 'unknown';
}

/**
 * 获取页面标题
 */
function getPageTitle() {
  try {
    return getCurrentPages()[0]?.data?.title || '';
  } catch (e) {
    return '';
  }
}

/**
 * 过滤敏感数据
 */
function filterSensitiveData(data) {
  const sensitiveKeys = ['password', 'token', 'secret', 'api_key', 'openid'];
  const filtered = {};
  
  for (const key in data) {
    if (!sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive))) {
      filtered[key] = data[key];
    }
  }
  
  return filtered;
}

/**
 * 本地保存事件（失败重试用）
 */
function saveEventLocally(eventData) {
  try {
    const pendingEvents = wx.getStorageSync('pending_events') || [];
    pendingEvents.push({
      ...eventData,
      savedAt: Date.now()
    });
    
    // 限制本地存储数量
    if (pendingEvents.length > 100) {
      pendingEvents.shift();
    }
    
    wx.setStorageSync('pending_events', pendingEvents);
    logger.debug('[BehaviorTracker] 事件已保存到本地', { count: pendingEvents.length });
  } catch (e) {
    logger.warn('[BehaviorTracker] 本地保存失败', e);
  }
}

/**
 * 重试发送本地保存的事件
 */
function retryPendingEvents() {
  try {
    const pendingEvents = wx.getStorageSync('pending_events') || [];
    
    if (pendingEvents.length === 0) return;
    
    logger.info('[BehaviorTracker] 开始重试本地事件', { count: pendingEvents.length });
    
    // 逐个发送
    pendingEvents.forEach((event, index) => {
      post(API_ENDPOINTS.ANALYTICS.TRACK, event, { loading: false })
        .then(() => {
          logger.debug('[BehaviorTracker] 本地事件重试成功', { index });
          // 成功后从本地删除
          pendingEvents.splice(index, 1);
        })
        .catch(error => {
          logger.warn('[BehaviorTracker] 本地事件重试失败', { index, error });
        });
    });
    
    wx.setStorageSync('pending_events', pendingEvents);
  } catch (e) {
    logger.warn('[BehaviorTracker] 重试本地事件失败', e);
  }
}

/**
 * 获取会话信息
 */
function getSessionInfo() {
  return {
    sessionId,
    sessionStartTime,
    sessionDuration: Date.now() - sessionStartTime,
    page: getCurrentPage()
  };
}

/**
 * 重置会话
 */
function resetSession() {
  sessionId = generateSessionId();
  sessionStartTime = Date.now();
  logger.debug('[BehaviorTracker] 会话已重置', { sessionId });
}

module.exports = {
  // 初始化
  initTracking,
  
  // 追踪方法
  trackEvent,
  trackPageView,
  trackButtonClick,
  trackApiCall,
  trackFormSubmit,
  trackError,
  
  // 会话管理
  getSessionInfo,
  resetSession,
  
  // 重试
  retryPendingEvents,
  
  // 常量
  EVENT_CATEGORIES
};
