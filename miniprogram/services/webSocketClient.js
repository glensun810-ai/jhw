/**
 * WebSocket 客户端服务
 * 
 * 功能：
 * - WebSocket 连接管理
 * - 消息接收和处理
 * - 自动重连
 * - 心跳保活
 * - 降级到轮询
 * 
 * @author: 系统架构组
 * @date: 2026-02-27
 * @version: 2.0.0
 */

// WebSocket 服务器地址（从配置读取）
const WS_SERVER_URL = 'wxs://your-app-id.cloud.tencent.com/ws';

// 配置常量
const CONFIG = {
  // 最大重连次数
  MAX_RECONNECT_ATTEMPTS: 5,
  // 重连间隔（毫秒）
  RECONNECT_INTERVAL: 3000,
  // 心跳间隔（毫秒）
  HEARTBEAT_INTERVAL: 30000,
  // 连接超时（毫秒）
  CONNECTION_TIMEOUT: 10000,
  // 是否启用 WebSocket（可通过特性开关控制）
  ENABLE_WEBSOCKET: true
};

/**
 * WebSocket 客户端类
 */
class WebSocketClient {
  /**
   * 构造函数
   */
  constructor() {
    this.socket = null;
    this.executionId = null;
    this.reconnectAttempts = 0;
    this.heartbeatTimer = null;
    this.connectionTimeout = null;
    this.callbacks = {
      onProgress: null,
      onResult: null,
      onComplete: null,
      onError: null,
      onConnected: null,
      onDisconnected: null
    };
    this.isConnected = false;
  }

  /**
   * 连接到 WebSocket 服务器
   * @param {string} executionId - 诊断执行 ID
   * @param {Object} callbacks - 回调函数
   */
  connect(executionId, callbacks = {}) {
    // 保存参数
    this.executionId = executionId;
    this.callbacks = { ...this.callbacks, ...callbacks };

    // 检查是否启用 WebSocket
    if (!CONFIG.ENABLE_WEBSOCKET) {
      console.log('[WebSocket] 未启用，使用轮询降级方案');
      if (this.callbacks.onFallback) {
        this.callbacks.onFallback();
      }
      return false;
    }

    // 检查是否已连接
    if (this.isConnected) {
      console.log('[WebSocket] 已连接，跳过');
      return true;
    }

    try {
      // 构建 WebSocket URL
      const url = `${WS_SERVER_URL}/diagnosis/${executionId}`;

      // 创建连接
      this.socket = wx.connectSocket({
        url: url,
        success: () => {
          console.log('[WebSocket] 连接请求已发送');
        },
        fail: (error) => {
          console.error('[WebSocket] 连接失败:', error);
          this._handleConnectionFailed();
        }
      });

      // 设置连接超时
      this.connectionTimeout = setTimeout(() => {
        if (!this.isConnected) {
          console.error('[WebSocket] 连接超时');
          this._handleConnectionFailed();
        }
      }, CONFIG.CONNECTION_TIMEOUT);

      // 注册事件处理
      this._registerEventHandlers();

      return true;
    } catch (error) {
      console.error('[WebSocket] 创建连接失败:', error);
      this._handleConnectionFailed();
      return false;
    }
  }

  /**
   * 注册事件处理
   * @private
   */
  _registerEventHandlers() {
    if (!this.socket) return;

    // 连接打开
    this.socket.onOpen(() => {
      console.log('[WebSocket] 连接已建立');
      clearTimeout(this.connectionTimeout);
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // 启动心跳
      this._startHeartbeat();

      // 调用连接回调
      if (this.callbacks.onConnected) {
        this.callbacks.onConnected();
      }
    });

    // 接收消息
    this.socket.onMessage((res) => {
      console.log('[WebSocket] 收到消息:', res.data);
      this._handleMessage(res.data);
    });

    // 连接关闭
    this.socket.onClose(() => {
      console.log('[WebSocket] 连接已关闭');
      this.isConnected = false;
      this._stopHeartbeat();

      // 调用断开回调
      if (this.callbacks.onDisconnected) {
        this.callbacks.onDisconnected();
      }

      // 尝试重连
      this._attemptReconnect();
    });

    // 连接错误
    this.socket.onError((error) => {
      console.error('[WebSocket] 发生错误:', error);
      this._handleError(error);
    });
  }

  /**
   * 处理接收到的消息
   * @private
   * @param {string} data - 消息数据
   */
  _handleMessage(data) {
    try {
      const message = JSON.parse(data);

      // 根据消息类型调用相应回调
      switch (message.event) {
        case 'progress':
          if (this.callbacks.onProgress) {
            this.callbacks.onProgress(message.data);
          }
          break;

        case 'result':
          if (this.callbacks.onResult) {
            this.callbacks.onResult(message.data);
          }
          break;

        case 'complete':
          if (this.callbacks.onComplete) {
            this.callbacks.onComplete(message.data);
          }
          // 完成后关闭连接
          this.close();
          break;

        case 'error':
          if (this.callbacks.onError) {
            this.callbacks.onError(message.data);
          }
          break;

        case 'heartbeat_ack':
          // 心跳响应，无需处理
          break;

        default:
          console.warn('[WebSocket] 未知消息类型:', message.type);
      }
    } catch (error) {
      console.error('[WebSocket] 解析消息失败:', error);
    }
  }

  /**
   * 处理连接失败
   * @private
   */
  _handleConnectionFailed() {
    this.isConnected = false;
    clearTimeout(this.connectionTimeout);
    this._stopHeartbeat();

    // 尝试重连
    this._attemptReconnect();
  }

  /**
   * 处理错误
   * @private
   * @param {Object} error - 错误对象
   */
  _handleError(error) {
    console.error('[WebSocket] 错误:', error);

    // 调用错误回调
    if (this.callbacks.onError) {
      this.callbacks.onError({
        type: 'WEBSOCKET_ERROR',
        message: 'WebSocket 连接错误',
        error: error
      });
    }
  }

  /**
   * 尝试重连
   * @private
   */
  _attemptReconnect() {
    if (this.reconnectAttempts >= CONFIG.MAX_RECONNECT_ATTEMPTS) {
      console.error('[WebSocket] 重连次数已达上限，使用轮询降级方案');
      if (this.callbacks.onFallback) {
        this.callbacks.onFallback();
      }
      return;
    }

    this.reconnectAttempts++;
    const delay = CONFIG.RECONNECT_INTERVAL * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`[WebSocket] ${delay}ms 后尝试第 ${this.reconnectAttempts} 次重连`);

    setTimeout(() => {
      if (this.executionId) {
        console.log('[WebSocket] 开始重连...');
        this.connect(this.executionId, this.callbacks);
      }
    }, delay);
  }

  /**
   * 启动心跳
   * @private
   */
  _startHeartbeat() {
    this._stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected && this.socket) {
        this.socket.send({
          data: JSON.stringify({
            type: 'heartbeat',
            timestamp: new Date().toISOString()
          })
        });
      }
    }, CONFIG.HEARTBEAT_INTERVAL);
  }

  /**
   * 停止心跳
   * @private
   */
  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 关闭连接
   */
  close() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.isConnected = false;
    this._stopHeartbeat();
    console.log('[WebSocket] 连接已关闭');
  }

  /**
   * 断开连接（不重连）
   */
  disconnect() {
    this.reconnectAttempts = CONFIG.MAX_RECONNECT_ATTEMPTS; // 阻止重连
    this.close();
  }

  /**
   * 检查是否支持 WebSocket
   * @returns {boolean} 是否支持
   */
  static isSupported() {
    return typeof wx !== 'undefined' && wx.connectSocket;
  }

  /**
   * 获取连接状态
   * @returns {boolean} 是否已连接
   */
  getConnectionStatus() {
    return this.isConnected;
  }

  /**
   * 获取重连次数
   * @returns {number} 重连次数
   */
  getReconnectAttempts() {
    return this.reconnectAttempts;
  }
}

// 导出单例
export default new WebSocketClient();

/**
 * 使用示例:
 * 
 * import webSocketClient from './services/webSocketClient';
 * 
 * // 连接
 * webSocketClient.connect(executionId, {
 *   onConnected: () => {
 *     console.log('WebSocket 已连接');
 *   },
 *   onProgress: (data) => {
 *     console.log('进度更新:', data);
 *     // 更新 UI
 *   },
 *   onResult: (data) => {
 *     console.log('中间结果:', data);
 *   },
 *   onComplete: (data) => {
 *     console.log('诊断完成:', data);
 *     // 跳转到报告页面
 *   },
 *   onError: (error) => {
 *     console.error('错误:', error);
 *     // 显示错误提示
 *   },
 *   onDisconnected: () => {
 *     console.log('连接已断开');
 *   },
 *   onFallback: () => {
 *     console.log('降级到轮询模式');
 *     // 启动轮询
 *   }
 * });
 * 
 * // 页面卸载时断开
 * onUnload() {
 *   webSocketClient.disconnect();
 * }
 */
