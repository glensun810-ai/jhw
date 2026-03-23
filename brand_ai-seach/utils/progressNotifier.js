/**
 * 进度通知管理器 - 微信订阅消息
 * 
 * 功能:
 * 1. 请求订阅权限
 * 2. 发送进度通知
 * 3. 完成通知
 * 4. 通知历史记录
 */

const STORAGE_KEY = 'notification_history';
const TEMPLATE_ID = 'xxx';  // 需要申请微信订阅消息模板

class ProgressNotifier {
  constructor() {
    this.subscribed = false;
    this.history = this.loadHistory();
  }

  /**
   * 加载通知历史
   */
  loadHistory() {
    try {
      return wx.getStorageSync(STORAGE_KEY) || [];
    } catch (e) {
      console.error('加载通知历史失败', e);
      return [];
    }
  }

  /**
   * 保存通知历史
   */
  saveHistory() {
    try {
      wx.setStorageSync(STORAGE_KEY, this.history);
    } catch (e) {
      console.error('保存通知历史失败', e);
    }
  }

  /**
   * 请求订阅权限
   */
  async requestSubscription() {
    try {
      const res = await wx.requestSubscribeMessage({
        tmplIds: [TEMPLATE_ID]
      });

      if (res[TEMPLATE_ID] === 'accept') {
        this.subscribed = true;
        console.log('✅ 用户同意订阅消息');
        return { success: true, subscribed: true };
      } else {
        this.subscribed = false;
        console.log('❌ 用户拒绝订阅消息');
        return { success: true, subscribed: false };
      }
    } catch (e) {
      console.error('请求订阅失败', e);
      return { success: false, error: e.message };
    }
  }

  /**
   * 发送进度通知
   * @param {Object} params - 通知参数
   */
  async sendProgressNotification(params) {
    if (!this.subscribed) {
      console.log('⚠️ 用户未订阅，跳过通知');
      return { success: false, reason: 'not_subscribed' };
    }

    try {
      // 注意：实际发送需要在后端调用微信 API
      // 这里只是前端请求
      const notification = {
        touser: params.openid,
        template_id: TEMPLATE_ID,
        data: {
          thing1: { value: params.brandName || '品牌诊断' },
          thing2: { value: `进度 ${params.progress}%` },
          time3: { value: this.formatTime(new Date()) }
        }
      };

      // 记录通知历史
      this.recordNotification('progress', params.progress);

      console.log('📤 发送进度通知:', notification);
      
      // 实际发送需要后端配合
      return { success: true, notificationId: Date.now() };
    } catch (e) {
      console.error('发送通知失败', e);
      return { success: false, error: e.message };
    }
  }

  /**
   * 发送完成通知
   */
  async sendCompletionNotification(params) {
    if (!this.subscribed) {
      return { success: false, reason: 'not_subscribed' };
    }

    try {
      const notification = {
        touser: params.openid,
        template_id: TEMPLATE_ID,
        data: {
          thing1: { value: params.brandName || '品牌诊断' },
          thing2: { value: '诊断已完成' },
          time3: { value: this.formatTime(new Date()) }
        }
      };

      this.recordNotification('complete', 100);

      console.log('📤 发送完成通知:', notification);
      
      return { success: true, notificationId: Date.now() };
    } catch (e) {
      console.error('发送完成通知失败', e);
      return { success: false, error: e.message };
    }
  }

  /**
   * 记录通知历史
   */
  recordNotification(type, progress) {
    const record = {
      type: type,
      progress: progress,
      timestamp: Date.now(),
      success: true
    };

    this.history.push(record);

    // 保留最近 50 条
    if (this.history.length > 50) {
      this.history = this.history.slice(-50);
    }

    this.saveHistory();
  }

  /**
   * 格式化时间
   */
  formatTime(date) {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hour = date.getHours();
    const minute = date.getMinutes();

    return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')} ${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
  }

  /**
   * 获取通知历史
   */
  getHistory(limit = 10) {
    return this.history.slice(-limit);
  }

  /**
   * 清除通知历史
   */
  clearHistory() {
    this.history = [];
    wx.removeStorageSync(STORAGE_KEY);
  }

  /**
   * 获取订阅状态
   */
  getSubscriptionStatus() {
    return {
      subscribed: this.subscribed,
      historyCount: this.history.length,
      lastNotification: this.history.length > 0 ? this.history[this.history.length - 1] : null
    };
  }
}

module.exports = ProgressNotifier;
