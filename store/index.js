/**
 * 轻量级状态管理 Store
 * 
 * 功能：
 * - 全局状态管理
 * - 状态变更通知
 * - 持久化支持
 * 
 * 使用示例：
 * import store from '../../store/index';
 * 
 * // 读取状态
 * const executionId = store.getState('diagnosis.currentExecutionId');
 * 
 * // 更新状态
 * store.setState('diagnosis.status', 'running');
 * 
 * // 订阅状态变化
 * store.subscribe('diagnosis', (newState) => {
 *   console.log('诊断状态变化:', newState);
 * });
 */

// 存储键名
const STORAGE_KEYS = {
  APP_STATE: 'app_state'
};

// 初始状态
const initialState = {
  // 用户状态
  user: {
    openid: '',
    userInfo: null,
    permissions: [],
    isLoggedIn: false,
    token: null
  },

  // 诊断状态
  diagnosis: {
    currentExecutionId: null,
    status: 'idle', // idle | running | completed | failed
    progress: 0,
    stage: 'init',
    results: null,
    error: null
  },

  // UI 状态
  ui: {
    loading: false,
    error: null,
    theme: 'light',
    toast: null
  },

  // 缓存数据
  cache: {
    lastDiagnosticResults: null,
    lastUpdateTime: null
  }
};

// 状态变更监听器
const listeners = {};

// 当前状态
let currentState = JSON.parse(JSON.stringify(initialState));

/**
 * 获取嵌套对象的值
 */
function getNestedValue(obj, path) {
  return path.split('.').reduce((acc, part) => {
    return acc && acc[part] !== undefined ? acc[part] : undefined;
  }, obj);
}

/**
 * 设置嵌套对象的值
 */
function setNestedValue(obj, path, value) {
  const keys = path.split('.');
  const lastKey = keys.pop();
  const target = keys.reduce((acc, key) => {
    if (acc[key] === undefined) {
      acc[key] = {};
    }
    return acc[key];
  }, obj);
  target[lastKey] = value;
}

/**
 * 深度比较两个对象
 */
function deepEqual(obj1, obj2) {
  if (obj1 === obj2) return true;
  
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object') {
    return obj1 === obj2;
  }
  
  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);
  
  if (keys1.length !== keys2.length) return false;
  
  for (let key of keys1) {
    if (!keys2.includes(key)) return false;
    if (!deepEqual(obj1[key], obj2[key])) return false;
  }
  
  return true;
}

/**
 * Store 类
 */
class Store {
  /**
   * 获取状态
   * @param {string} path - 状态路径，如 'user.openid'
   * @returns {*} 状态值
   */
  getState(path) {
    if (!path) return currentState;
    return getNestedValue(currentState, path);
  }

  /**
   * 设置状态
   * @param {string} path - 状态路径
   * @param {*} value - 状态值
   * @param {boolean} persist - 是否持久化
   */
  setState(path, value, persist = false) {
    const oldValue = getNestedValue(currentState, path);
    
    // 如果值没有变化，不触发更新
    if (deepEqual(oldValue, value)) {
      return;
    }
    
    // 更新状态
    setNestedValue(currentState, path, value);
    
    // 触发监听器
    this.notifyListeners(path, value, oldValue);
    
    // 持久化
    if (persist) {
      this.persist();
    }
  }

  /**
   * 批量设置状态
   * @param {Object} updates - 状态更新对象
   * @param {boolean} persist - 是否持久化
   */
  batchSetState(updates, persist = false) {
    Object.keys(updates).forEach(path => {
      this.setState(path, updates[path], false);
    });
    
    if (persist) {
      this.persist();
    }
  }

  /**
   * 订阅状态变化
   * @param {string} path - 状态路径
   * @param {Function} listener - 监听函数
   * @returns {Function} 取消订阅函数
   */
  subscribe(path, listener) {
    if (!listeners[path]) {
      listeners[path] = [];
    }
    
    listeners[path].push(listener);
    
    // 返回取消订阅函数
    return () => {
      listeners[path] = listeners[path].filter(l => l !== listener);
    };
  }

  /**
   * 通知监听器
   */
  notifyListeners(path, newValue, oldValue) {
    // 触发精确路径的监听器
    if (listeners[path]) {
      listeners[path].forEach(listener => {
        try {
          listener(newValue, oldValue, path);
        } catch (error) {
          console.error(`[Store] 监听器执行失败 (${path}):`, error);
        }
      });
    }
    
    // 触发父级路径的监听器
    const parts = path.split('.');
    while (parts.length > 0) {
      parts.pop();
      const parentPath = parts.join('.');
      if (listeners[parentPath]) {
        listeners[parentPath].forEach(listener => {
          try {
            listener(getNestedValue(currentState, parentPath), null, parentPath);
          } catch (error) {
            console.error(`[Store] 监听器执行失败 (${parentPath}):`, error);
          }
        });
      }
    }
  }

  /**
   * 持久化状态
   */
  persist() {
    try {
      const stateToSave = {
        user: currentState.user,
        cache: currentState.cache,
        savedAt: Date.now()
      };
      wx.setStorageSync(STORAGE_KEYS.APP_STATE, stateToSave);
      console.log('[Store] 状态已持久化');
    } catch (error) {
      console.error('[Store] 持久化失败:', error);
    }
  }

  /**
   * 加载持久化状态
   */
  loadPersistedState() {
    try {
      const savedState = wx.getStorageSync(STORAGE_KEYS.APP_STATE);
      
      if (savedState && savedState.user) {
        // 合并用户状态
        this.batchSetState({
          'user.openid': savedState.user.openid || '',
          'user.userInfo': savedState.user.userInfo || null,
          'user.permissions': savedState.user.permissions || [],
          'user.isLoggedIn': savedState.user.isLoggedIn || false,
          'cache.lastDiagnosticResults': savedState.cache?.lastDiagnosticResults || null,
          'cache.lastUpdateTime': savedState.cache?.lastUpdateTime || null
        });
        
        console.log('[Store] 已加载持久化状态');
      }
    } catch (error) {
      console.error('[Store] 加载持久化状态失败:', error);
    }
  }

  /**
   * 重置状态
   */
  reset() {
    currentState = JSON.parse(JSON.stringify(initialState));
    console.log('[Store] 状态已重置');
  }

  /**
   * 获取完整状态
   */
  getFullState() {
    return JSON.parse(JSON.stringify(currentState));
  }

  /**
   * 诊断状态相关方法
   */
  diagnosis = {
    start: (executionId) => {
      store.batchSetState({
        'diagnosis.currentExecutionId': executionId,
        'diagnosis.status': 'running',
        'diagnosis.progress': 0,
        'diagnosis.stage': 'init',
        'diagnosis.error': null
      });
    },
    
    updateProgress: (progress, stage) => {
      store.batchSetState({
        'diagnosis.progress': progress,
        'diagnosis.stage': stage || 'processing'
      });
    },
    
    complete: (results) => {
      store.batchSetState({
        'diagnosis.status': 'completed',
        'diagnosis.progress': 100,
        'diagnosis.results': results,
        'cache.lastDiagnosticResults': results,
        'cache.lastUpdateTime': Date.now()
      }, true);
    },
    
    fail: (error) => {
      store.batchSetState({
        'diagnosis.status': 'failed',
        'diagnosis.error': error?.message || '未知错误'
      });
    },
    
    reset: () => {
      store.batchSetState({
        'diagnosis.currentExecutionId': null,
        'diagnosis.status': 'idle',
        'diagnosis.progress': 0,
        'diagnosis.stage': 'init',
        'diagnosis.results': null,
        'diagnosis.error': null
      });
    }
  };

  /**
   * UI 状态相关方法
   */
  ui = {
    showLoading: (title = '加载中...') => {
      store.batchSetState({
        'ui.loading': true,
        'ui.toast': { type: 'loading', message: title }
      });
      
      wx.showLoading({ title, mask: true });
    },
    
    hideLoading: () => {
      store.setState('ui.loading', false);
      store.setState('ui.toast', null);
      
      wx.hideLoading();
    },
    
    showToast: (message, type = 'success') => {
      store.setState('ui.toast', { type, message });
      
      wx.showToast({
        title: message,
        icon: type,
        duration: 2000
      });
    },
    
    showError: (message) => {
      store.batchSetState({
        'ui.error': message,
        'ui.toast': { type: 'error', message }
      });
      
      wx.showToast({
        title: message,
        icon: 'none',
        duration: 3000
      });
    }
  };
}

// 创建单例
const store = new Store();

// 导出默认实例
export default store;

// 同时支持 CommonJS
module.exports = store;
