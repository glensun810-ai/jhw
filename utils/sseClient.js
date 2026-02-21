/**
 * SSE (Server-Sent Events) 客户端工具
 * 用于连接后端 SSE 推送服务
 */

class SSEClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.eventSource = null;
    this.clientId = null;
    this.executionId = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.listeners = {};
    this.isConnected = false;
  }

  /**
   * 连接到 SSE 服务
   * @param {string} executionId - 执行 ID
   */
  connect(executionId) {
    if (this.eventSource) {
      this.disconnect();
    }

    this.executionId = executionId;
    const url = `${this.baseUrl}/api/stream/progress/${executionId}`;

    console.log('[SSE] Connecting to:', url);

    try {
      this.eventSource = new EventSource(url);
      this.setupEventListeners();
    } catch (error) {
      console.error('[SSE] Connection failed:', error);
      this.handleReconnect();
    }
  }

  /**
   * 设置事件监听器
   */
  setupEventListeners() {
    // 连接成功
    this.eventSource.addEventListener('connected', (event) => {
      console.log('[SSE] Connected:', event.data);
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.trigger('connected', JSON.parse(event.data));
    });

    // 进度更新
    this.eventSource.addEventListener('progress', (event) => {
      console.log('[SSE] Progress:', event.data);
      this.trigger('progress', JSON.parse(event.data));
    });

    // 情报更新
    this.eventSource.addEventListener('intelligence', (event) => {
      console.log('[SSE] Intelligence:', event.data);
      this.trigger('intelligence', JSON.parse(event.data));
    });

    // 任务完成
    this.eventSource.addEventListener('complete', (event) => {
      console.log('[SSE] Complete:', event.data);
      this.trigger('complete', JSON.parse(event.data));
      this.disconnect();
    });

    // 错误通知
    this.eventSource.addEventListener('error', (event) => {
      console.error('[SSE] Error:', event.data);
      this.trigger('error', JSON.parse(event.data));
    });

    // 连接错误
    this.eventSource.onerror = (error) => {
      console.error('[SSE] EventSource failed:', error);
      this.isConnected = false;
      this.trigger('disconnected', {});
      this.handleReconnect();
    };
  }

  /**
   * 处理重连
   */
  handleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[SSE] Max reconnect attempts reached');
      this.trigger('maxReconnectReached', {
        attempts: this.reconnectAttempts
      });
      return;
    }

    this.reconnectAttempts++;
    console.log(`[SSE] Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (this.executionId) {
        this.connect(this.executionId);
      }
    }, this.reconnectDelay);
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.isConnected = false;
      console.log('[SSE] Disconnected');
    }
  }

  /**
   * 注册事件监听器
   * @param {string} event - 事件名称
   * @param {function} callback - 回调函数
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  /**
   * 移除事件监听器
   * @param {string} event - 事件名称
   * @param {function} callback - 回调函数
   */
  off(event, callback) {
    if (!this.listeners[event]) return;

    if (callback) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    } else {
      this.listeners[event] = [];
    }
  }

  /**
   * 触发事件
   * @param {string} event - 事件名称
   * @param {any} data - 事件数据
   */
  trigger(event, data) {
    if (!this.listeners[event]) return;

    this.listeners[event].forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`[SSE] Error in ${event} listener:`, error);
      }
    });
  }

  /**
   * 获取连接状态
   */
  getStatus() {
    return {
      isConnected: this.isConnected,
      executionId: this.executionId,
      clientId: this.clientId,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

// 全局单例
let _sseClient = null;

/**
 * 获取 SSE 客户端单例
 */
function getSSEClient(baseUrl) {
  if (!_sseClient) {
    _sseClient = new SSEClient(baseUrl);
  }
  return _sseClient;
}

module.exports = {
  SSEClient,
  getSSEClient
};
