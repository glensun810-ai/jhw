/**
 * Store 观察者工具
 * 
 * 功能：
 * - 状态变化监听
 * - 自动更新页面数据
 * - 清理订阅
 * 
 * 使用示例：
 * import { observer, useStore } from '../../utils/observer';
 * 
 * Page({
 *   onLoad() {
 *     // 观察状态变化
 *     this.storeObserver = observer(this, ['diagnosis.status', 'diagnosis.progress']);
 *   },
 *   
 *   onUnload() {
 *     // 清理订阅
 *     this.storeObserver.dispose();
 *   }
 * });
 */

import store from '../store/index';

/**
 * 获取嵌套对象的值
 */
function getNestedValue(obj, path) {
  return path.split('.').reduce((acc, part) => {
    return acc && acc[part] !== undefined ? acc[part] : undefined;
  }, obj);
}

/**
 * 观察者类
 */
class StoreObserver {
  /**
   * 构造函数
   * @param {Object} pageContext - 页面上下文
   * @param {Array} paths - 观察的路径列表
   */
  constructor(pageContext, paths = []) {
    this.pageContext = pageContext;
    this.paths = paths;
    this.subscriptions = [];
    
    // 订阅所有路径
    paths.forEach(path => {
      this.subscribe(path);
    });
    
    console.log('[Observer] 观察者已创建，观察路径:', paths);
  }

  /**
   * 订阅路径
   */
  subscribe(path) {
    const unsubscribe = store.subscribe(path, (newValue, oldValue, changedPath) => {
      this.onStateChange(changedPath, newValue, oldValue);
    });
    
    this.subscriptions.push({ path, unsubscribe });
  }

  /**
   * 状态变化处理
   */
  onStateChange(path, newValue, oldValue) {
    if (!this.pageContext) return;
    
    // 更新页面数据
    const updateData = {};
    
    // 如果是顶层路径，更新整个对象
    if (!path.includes('.')) {
      updateData[path] = newValue;
    } else {
      // 否则更新具体字段
      const parts = path.split('.');
      const rootKey = parts[0];
      
      // 获取当前页面数据中的根对象
      const currentRootData = this.pageContext.data[rootKey] || {};
      
      // 创建新对象
      const newRootData = {
        ...currentRootData
      };
      
      // 设置新值
      let target = newRootData;
      for (let i = 1; i < parts.length - 1; i++) {
        const key = parts[i];
        target[key] = { ...target[key] };
        target = target[key];
      }
      
      const lastKey = parts[parts.length - 1];
      target[lastKey] = newValue;
      
      updateData[rootKey] = newRootData;
    }
    
    // 执行 setData
    if (Object.keys(updateData).length > 0) {
      this.pageContext.setData(updateData);
    }
  }

  /**
   * 添加观察路径
   */
  addPath(path) {
    if (!this.paths.includes(path)) {
      this.paths.push(path);
      this.subscribe(path);
    }
  }

  /**
   * 移除观察路径
   */
  removePath(path) {
    const index = this.paths.findIndex(p => p === path);
    if (index !== -1) {
      this.paths.splice(index, 1);
      
      const subIndex = this.subscriptions.findIndex(s => s.path === path);
      if (subIndex !== -1) {
        this.subscriptions[subIndex].unsubscribe();
        this.subscriptions.splice(subIndex, 1);
      }
    }
  }

  /**
   * 销毁观察者
   */
  dispose() {
    this.subscriptions.forEach(sub => {
      sub.unsubscribe();
    });
    this.subscriptions = [];
    this.pageContext = null;
    
    console.log('[Observer] 观察者已销毁');
  }
}

/**
 * 创建观察者
 * @param {Object} pageContext - 页面上下文
 * @param {Array} paths - 观察的路径列表
 * @returns {StoreObserver} 观察者实例
 */
export function observer(pageContext, paths = []) {
  return new StoreObserver(pageContext, paths);
}

/**
 * 获取 Store 实例
 * @returns {Object} Store 实例
 */
export function useStore() {
  return store;
}

/**
 * 获取状态
 * @param {string} path - 状态路径
 * @returns {*} 状态值
 */
export function useState(path) {
  return store.getState(path);
}

/**
 * 设置状态
 * @param {string} path - 状态路径
 * @param {*} value - 状态值
 * @param {boolean} persist - 是否持久化
 */
export function setState(path, value, persist = false) {
  store.setState(path, value, persist);
}

/**
 * 订阅状态变化
 * @param {string} path - 状态路径
 * @param {Function} listener - 监听函数
 * @returns {Function} 取消订阅函数
 */
export function subscribe(path, listener) {
  return store.subscribe(path, listener);
}

// CommonJS 导出
module.exports = {
  observer,
  useStore,
  useState,
  setState,
  subscribe,
  StoreObserver
};
