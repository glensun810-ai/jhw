/**
 * SSE (Server-Sent Events) 客户端工具
 * 用于实时接收服务器推送的情报更新
 * 
 * 注意：微信小程序不支持原生 SSE，此工具使用轮询作为替代方案
 */

const app = getApp();
const logger = require('./logger');
const { request } = require('./request');

/**
 * SSE 客户端类
 * 自动在原生 SSE 和轮询之间切换
 */
class SSEClient {
  constructor(url, options = {}) {
    this.url = url;
    this.options = {
      // 轮询间隔（毫秒）
      pollingInterval: options.pollingInterval || 3000,
      // 重连间隔（毫秒）
      reconnectInterval: options.reconnectInterval || 5000,
      // 最大重连次数
      maxReconnects: options.maxReconnects || 10,
      // 心跳检测间隔（毫秒）
      heartbeatInterval: options.heartbeatInterval || 30000,
      // 是否自动重连
      autoReconnect: options.autoReconnect !== false,
      // 事件回调
      onOpen: options.onOpen || (() => {}),
      onMessage: options.onMessage || (() => {}),
      onError: options.onError || (() => {}),
      onClose: options.onClose || (() => {})
    };

    this.state = 'closed'; // closed, connecting, connected, error
    this.reconnectCount = 0;
    this.pollingTimer = null;
    this.heartbeatTimer = null;
    this.lastEventId = null;
    this.listeners = {};

    logger.debug('[SSEClient] 初始化', { url: this.url, options: this.options });
  }

  /**
   * 连接服务器
   */
  connect() {
    if (this.state === 'connected' || this.state === 'connecting') {
      logger.warn('[SSEClient] 已在连接中');
      return;
    }

    this.state = 'connecting';
    logger.info('[SSEClient] 开始连接');

    // 微信小程序使用轮询
    this._startPolling();
  }

  /**
   * 启动轮询
   */
  _startPolling() {
    const poll = async () => {
      try {
        const response = await request({
          url: this.url.replace('/stream', '/pipeline'),
          method: 'GET',
          data: {
            executionId: this._extractExecutionId(),
            limit: 50
          },
          loading: false
        });

        if (response.status === 'success') {
          // 检查是否有新数据
          if (this.lastData && JSON.stringify(this.lastData) !== JSON.stringify(response.data)) {
            this._emit('message', {
              data: JSON.stringify(response.data),
              lastEventId: this.lastEventId
            });
          }

          this.lastData = response.data;
          this.lastEventId = Date.now().toString();

          // 连接成功
          if (this.state !== 'connected') {
            this.state = 'connected';
            this.reconnectCount = 0;
            this._emit('open');
            this.options.onOpen();
          }

          // 启动心跳检测
          this._startHeartbeat();
        } else {
          throw new Error(response.error || '轮询失败');
        }
      } catch (error) {
        logger.error('[SSEClient] 轮询失败', error);
        
        if (this.state === 'connected') {
          this.state = 'error';
          this._emit('error', { error: error.message });
          this.options.onError(error);
        }

        // 自动重连
        if (this.options.autoReconnect && this.reconnectCount < this.options.maxReconnects) {
          this._scheduleReconnect();
        }
      }
    };

    // 立即执行一次
    poll();

    // 定时轮询
    this.pollingTimer = setInterval(poll, this.options.pollingInterval);
    logger.info('[SSEClient] 轮询已启动', { interval: this.options.pollingInterval });
  }

  /**
   * 启动心跳检测
   */
  _startHeartbeat() {
    this._stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.state === 'connected') {
        this._emit('heartbeat');
        logger.debug('[SSEClient] 心跳检测');
      }
    }, this.options.heartbeatInterval);
  }

  /**
   * 停止心跳检测
   */
  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 调度重连
   */
  _scheduleReconnect() {
    this.reconnectCount++;
    const delay = Math.min(
      this.options.reconnectInterval * Math.pow(2, this.reconnectCount - 1),
      60000 // 最大 60 秒
    );

    logger.info('[SSEClient] 调度重连', {
      attempt: this.reconnectCount,
      delay: delay
    });

    setTimeout(() => {
      if (this.state !== 'closed') {
        this.connect();
      }
    }, delay);
  }

  /**
   * 从 URL 提取 executionId
   */
  _extractExecutionId() {
    const url = new URL(this.url, 'http://localhost');
    return url.searchParams.get('executionId') || '';
  }

  /**
   * 发送事件
   */
  _emit(type, data) {
    const listeners = this.listeners[type] || [];
    listeners.forEach(listener => {
      try {
        listener(data);
      } catch (error) {
        logger.error('[SSEClient] 事件处理错误', error);
      }
    });
  }

  /**
   * 添加事件监听
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    return this;
  }

  /**
   * 移除事件监听
   */
  off(event, callback) {
    if (!this.listeners[event]) return this;

    if (callback) {
      this.listeners[event] = this.listeners[event].filter(
        listener => listener !== callback
      );
    } else {
      this.listeners[event] = [];
    }
    return this;
  }

  /**
   * 关闭连接
   */
  close() {
    logger.info('[SSEClient] 关闭连接');

    this.state = 'closed';
    this._stopPolling();
    this._stopHeartbeat();
    this._emit('close');
    this.options.onClose();
  }

  /**
   * 停止轮询
   */
  _stopPolling() {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
      logger.info('[SSEClient] 轮询已停止');
    }
  }

  /**
   * 获取连接状态
   */
  getState() {
    return this.state;
  }

  /**
   * 是否已连接
   */
  isConnected() {
    return this.state === 'connected';
  }
}

/**
 * 创建 SSE 客户端实例
 * @param {string} executionId - 执行 ID
 * @param {object} options - 配置选项
 * @returns {SSEClient}
 */
function createIntelligenceSSE(executionId, options = {}) {
  const baseUrl = app.globalData.apiBaseUrl || 'http://127.0.0.1:5001';
  const sseUrl = `${baseUrl}/api/intelligence/stream?executionId=${executionId}`;

  logger.info('[SSE] 创建情报流水线 SSE 客户端', { executionId, sseUrl });

  return new SSEClient(sseUrl, options);
}

/**
 * 监听情报更新
 * @param {string} executionId - 执行 ID
 * @param {function} onIntelligenceUpdate - 更新回调
 * @returns {SSEClient}
 */
function watchIntelligenceUpdates(executionId, onIntelligenceUpdate) {
  const client = createIntelligenceSSE(executionId, {
    onOpen: () => {
      logger.info('[SSE] 情报流水线连接已建立');
    },
    onMessage: (event) => {
      try {
        const data = JSON.parse(event.data);
        onIntelligenceUpdate(data);
      } catch (error) {
        logger.error('[SSE] 解析情报数据失败', error);
      }
    },
    onError: (error) => {
      logger.error('[SSE] 情报流水线错误', error);
    },
    onClose: () => {
      logger.info('[SSE] 情报流水线连接已关闭');
    }
  });

  client.connect();
  return client;
}

module.exports = {
  SSEClient,
  createIntelligenceSSE,
  watchIntelligenceUpdates
};
