/**
 * 前端特性开关配置
 *
 * 用于控制新功能的灰度发布和调试
 */

/**
 * 特性开关配置
 */
export const FeatureFlags = {
  // 诊断相关
  diagnosis: {
    useNewPolling: true,        // 使用新的轮询机制
    enableRetryStrategy: true,   // 启用重试策略
    showProgressHistory: false,   // 显示进度历史
    enableAutoResume: true,       // 启用自动恢复
    useHttpDirect: false,         // 使用 HTTP 直连（false = 云函数模式）
    enableLogging: true           // 启用详细日志
  },

  // 灰度配置
  gray: {
    users: [],                     // 灰度用户列表
    percentage: 100                 // 灰度百分比（0-100）
  },

  // 调试配置
  debug: {
    enableLogging: true,          // 启用详细日志
    simulateSlowNetwork: false,    // 模拟慢网络
    skipServerCall: false          // 跳过服务器调用（用于测试）
  }
};

/**
 * 检查是否启用功能
 * @param {string} featurePath - 功能路径（如 'diagnosis.useNewPolling'）
 * @returns {boolean} 是否启用
 */
export function isFeatureEnabled(featurePath) {
  const parts = featurePath.split('.');
  let current = FeatureFlags;
  
  for (const part of parts) {
    if (current[part] === undefined) {
      console.warn(`Feature flag not found: ${featurePath}`);
      return false;
    }
    current = current[part];
  }
  
  return current === true;
}

/**
 * 检查用户是否在灰度中
 * @param {string} userId - 用户 ID
 * @returns {boolean} 是否在灰度中
 */
export function isUserInGray(userId) {
  // 检查是否在灰度名单
  if (FeatureFlags.gray.users.includes(userId)) {
    return true;
  }

  // 检查灰度百分比
  const hash = hashCode(userId) % 100;
  return hash < FeatureFlags.gray.percentage;
}

/**
 * 简单的哈希函数
 * @param {string} str - 输入字符串
 * @returns {number} 哈希值
 */
function hashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

/**
 * 获取特性开关配置（用于调试）
 * @returns {Object} 特性开关配置
 */
export function getFeatureFlags() {
  return { ...FeatureFlags };
}

/**
 * 更新特性开关（仅用于调试模式）
 * @param {string} featurePath - 功能路径
 * @param {any} value - 新值
 */
export function setFeatureFlag(featurePath, value) {
  if (!FeatureFlags.debug.enableLogging) {
    console.warn('Cannot modify feature flags in production mode');
    return;
  }

  const parts = featurePath.split('.');
  let current = FeatureFlags;
  
  for (let i = 0; i < parts.length - 1; i++) {
    if (current[parts[i]] === undefined) {
      console.warn(`Feature flag path not found: ${featurePath}`);
      return;
    }
    current = current[parts[i]];
  }
  
  const lastPart = parts[parts.length - 1];
  current[lastPart] = value;
  
  console.log(`Feature flag updated: ${featurePath} = ${value}`);
}
