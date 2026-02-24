/**
 * P1-016 后台诊断服务
 * 
 * 支持后台运行诊断任务，完成后通知用户
 * 降低轮询频率，节省资源
 * 
 * BUG-001 修复：添加内存泄漏防护
 */

const { getTaskStatusApi } = require('../api/home');
const { parseTaskStatus } = require('./taskStatusService');

/**
 * 后台任务管理器
 */
class BackgroundTaskManager {
  constructor() {
    this.tasks = [];
    this.pollingIntervals = {};
    this.cleanupTimer = null;
  }
  
  /**
   * 添加后台任务
   */
  addTask(executionId, brandName) {
    const task = {
      executionId,
      brandName,
      startTime: Date.now(),
      status: 'running',
      progress: 0
    };
    
    this.tasks.push(task);
    this.saveTasks();
    
    // 启动后台轮询
    this.startPolling(executionId);
    
    return task;
  }
  
  /**
   * 启动后台轮询（低频）
   * BUG-001 修复：添加清理机制
   */
  startPolling(executionId) {
    // 清除旧的轮询
    if (this.pollingIntervals[executionId]) {
      clearInterval(this.pollingIntervals[executionId]);
      delete this.pollingIntervals[executionId];
    }
    
    // 新轮询：10 秒一次
    this.pollingIntervals[executionId] = setInterval(() => {
      this.checkTaskStatus(executionId);
    }, 10000);
  }
  
  /**
   * BUG-001 修复：清理所有轮询
   */
  cleanup() {
    // 清除所有轮询
    Object.keys(this.pollingIntervals).forEach(executionId => {
      if (this.pollingIntervals[executionId]) {
        clearInterval(this.pollingIntervals[executionId]);
        delete this.pollingIntervals[executionId];
      }
    });
    
    // 清除清理定时器
    if (this.cleanupTimer) {
      clearTimeout(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    
    console.log('[后台任务] 已清理所有轮询');
  }
  
  /**
   * BUG-001 修复：页面卸载时自动清理
   */
  initAutoCleanup() {
    // 小程序页面卸载时清理
    if (typeof Page !== 'undefined') {
      const originalPage = Page;
      Page = function(config) {
        const originalOnUnload = config.onUnload;
        config.onUnload = function() {
          if (originalOnUnload) {
            originalOnUnload.call(this);
          }
          backgroundTaskManager.cleanup();
        };
        return originalPage(config);
      };
    }
  }
  
  /**
   * 检查任务状态
   */
  checkTaskStatus(executionId) {
    getTaskStatusApi(executionId)
      .then((res) => {
        const parsedStatus = parseTaskStatus(res);
        
        // 更新任务进度
        const taskIndex = this.tasks.findIndex(t => t.executionId === executionId);
        if (taskIndex !== -1) {
          this.tasks[taskIndex].progress = parsedStatus.progress;
          
          // 检查是否完成
          if (parsedStatus.is_completed || parsedStatus.stage === 'completed') {
            this.completeTask(executionId);
          }
        }
      })
      .catch((error) => {
        console.error(`[后台轮询] 检查任务状态失败：${executionId}`, error);
      });
  }
  
  /**
   * 完成任务
   */
  completeTask(executionId) {
    // 停止轮询
    if (this.pollingIntervals[executionId]) {
      clearInterval(this.pollingIntervals[executionId]);
      delete this.pollingIntervals[executionId];
    }
    
    // 更新任务状态
    const taskIndex = this.tasks.findIndex(t => t.executionId === executionId);
    if (taskIndex !== -1) {
      this.tasks[taskIndex].status = 'completed';
      this.tasks[taskIndex].endTime = Date.now();
      this.saveTasks();
      
      // 发送通知
      this.sendCompletionNotification(this.tasks[taskIndex]);
    }
  }
  
  /**
   * 发送完成通知
   */
  sendCompletionNotification(task) {
    // 检查是否已订阅
    const subscribed = wx.getStorageSync('diagnosis_notification_subscribed');
    
    if (subscribed) {
      // 发送微信通知
      wx.requestSubscribeMessage({
        tmplIds: ['DIAGNOSIS_COMPLETE_TEMPLATE_ID'],
        success: () => {
          console.log(`✅ 已发送完成通知：${task.brandName}`);
        },
        fail: (err) => {
          console.warn('⚠️ 通知订阅失败:', err);
        }
      });
    }
    
    // 本地通知（弹窗）
    wx.showModal({
      title: '诊断完成',
      content: `"${task.brandName}"的品牌洞察报告已生成完成！`,
      confirmText: '查看报告',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          // 跳转到结果页
          wx.navigateTo({
            url: `/pages/results/results?executionId=${task.executionId}&brandName=${encodeURIComponent(task.brandName)}`
          });
        }
      }
    });
  }
  
  /**
   * BUG-006 修复：保存任务到 Storage（添加防抖）
   */
  saveTasks() {
    // 清除之前的保存定时器
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }
    
    // 防抖：1 秒后保存，避免频繁写入
    this.saveTimeout = setTimeout(() => {
      try {
        wx.setStorageSync('background_diagnosis_tasks', this.tasks);
        console.log('[后台任务] 任务已保存');
      } catch (error) {
        console.error('[后台任务] 保存失败:', error);
      }
    }, 1000);
  }
  
  /**
   * 从 Storage 加载任务
   */
  loadTasks() {
    this.tasks = wx.getStorageSync('background_diagnosis_tasks') || [];
    
    // 恢复运行中的任务的轮询
    this.tasks.forEach(task => {
      if (task.status === 'running') {
        this.startPolling(task.executionId);
      }
    });
  }
  
  /**
   * 获取所有任务
   */
  getTasks() {
    return this.tasks;
  }
  
  /**
   * 清除已完成任务（超过 1 小时）
   */
  cleanup() {
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    
    this.tasks = this.tasks.filter(task => {
      if (task.status === 'completed' && task.endTime < oneHourAgo) {
        return false;  // 删除 1 小时前的已完成任务
      }
      return true;
    });
    
    this.saveTasks();
  }
}

// 单例
const backgroundTaskManager = new BackgroundTaskManager();

/**
 * 启动后台诊断
 * @param {string} executionId - 执行 ID
 * @param {string} brandName - 品牌名称
 */
function startBackgroundDiagnosis(executionId, brandName) {
  return backgroundTaskManager.addTask(executionId, brandName);
}

/**
 * 获取所有后台任务
 */
function getBackgroundTasks() {
  backgroundTaskManager.loadTasks();
  return backgroundTaskManager.getTasks();
}

/**
 * 清除已完成任务
 */
function cleanupBackgroundTasks() {
  backgroundTaskManager.cleanup();
}

module.exports = {
  startBackgroundDiagnosis,
  getBackgroundTasks,
  cleanupBackgroundTasks,
  backgroundTaskManager
};
