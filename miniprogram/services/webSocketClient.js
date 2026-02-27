/**
 * WebSocket 客户端服务（增强稳定版）
 *
 * 功能：
 * - WebSocket 连接管理
 * - 消息接收和处理
 * - 智能重连（指数退避 + 随机抖动）
 * - 双向心跳保活
 * - 连接健康检查
 * - 降级到轮询
 *
 * 优化点：
 * 1. 指数退避 + 随机抖动，避免重连风暴
 * 2. 双向心跳检测（客户端 + 服务端）
 * 3. 连接健康检查，及时发现问题
 * 4. 更智能的降级策略
 * 5. 详细的连接状态监控
 *
 * @author: 系统架构组
 * @date: 2026-02-28
 * @version: 2.1.0
 */

// WebSocket 服务器地址（从配置读取）
const WS_SERVER_URL = 'wxs://your-app-id.cloud.tencent.com/ws';

// 配置常量（优化版）
const CONFIG = {
  // 最大重连次数
  MAX_RECONNECT_ATTEMPTS: 10, // 增加到 10 次
  // 初始重连间隔（毫秒）
  INITIAL_RECONNECT_INTERVAL: 1000,
  // 最大重连间隔（毫秒）
  MAX_RECONNECT_INTERVAL: 30000,
  // 心跳间隔（毫秒）- 缩短以更快发现问题
  HEARTBEAT_INTERVAL: 15000,
  // 心跳超时（毫秒）- 超过这个时间没有响应认为连接已断开
  HEARTBEAT_TIMEOUT: 10000,
  // 连接超时（毫秒）
  CONNECTION_TIMEOUT: 8000,
  // 是否启用 WebSocket（可通过特性开关控制）
  ENABLE_WEBSOCKET: true,
  // 健康检查间隔（毫秒）
  HEALTH_CHECK_INTERVAL: 5000,
  // 连接空闲超时（毫秒）- 超过这个时间没有消息认为需要检查
  IDLE_TIMEOUT: 60000,
  // 随机抖动因子（0-1）- 避免重连同步化
  JITTER_FACTOR: 0.3
};

// 连接状态枚举
const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  FALLBACK: 'fallback'
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
    this.heartbeatTimeoutTimer = null;
    this.connectionTimeout = null;
    this.healthCheckTimer = null;
    this.lastMessageTime = null;
    this.state = ConnectionState.DISCONNECTED;
    this.callbacks = {
      onProgress: null,
      onResult: null,
      onComplete: null,
      onError: null,
      onConnected: null,
      onDisconnected: null,
      onFallback: null,
      onStateChange: null
    };
    this.statistics = {
      totalReconnects: 0,
      successfulReconnects: 0,
      failedReconnects: 0,
      lastConnectedAt: null,
      lastDisconnectedAt: null,
      totalDowntime: 0
    };
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
      this._setState(ConnectionState.FALLBACK);
      if (this.callbacks.onFallback) {
        this.callbacks.onFallback();
      }
      return false;
    }

    // 检查是否已连接
    if (this.state === ConnectionState.CONNECTED) {
      console.log('[WebSocket] 已连接，跳过');
      return true;
    }

    // 检查是否正在连接中
    if (this.state === ConnectionState.CONNECTING) {
      console.log('[WebSocket] 正在连接中，请稍候');
      return true;
    }

    try {
      // 构建 WebSocket URL（添加时间戳避免缓存）
      const timestamp = new Date().getTime();
      const url = `${WS_SERVER_URL}/diagnosis/${executionId}?t=${timestamp}`;

      console.log(`[WebSocket] 开始连接：${url}`);
      this._setState(ConnectionState.CONNECTING);

      // 创建连接
      this.socket = wx.connectSocket({
        url: url,
        multiple: true, // 支持多个连接
        success: () => {
          console.log('[WebSocket] 连接请求已发送');
        },
        fail: (error) => {
          console.error('[WebSocket] 连接失败:', error);
          this._handleConnectionFailed(error);
        }
      });

      // 设置连接超时
      this.connectionTimeout = setTimeout(() => {
        if (this.state !== ConnectionState.CONNECTED) {
          console.error('[WebSocket] 连接超时（' + CONFIG.CONNECTION_TIMEOUT + 'ms）');
          this._handleConnectionFailed({ code: 'TIMEOUT', message: '连接超时' });
        }
      }, CONFIG.CONNECTION_TIMEOUT);

      // 注册事件处理
      this._registerEventHandlers();

      return true;
    } catch (error) {
      console.error('[WebSocket] 创建连接失败:', error);
      this._handleConnectionFailed(error);
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
      this._setState(ConnectionState.CONNECTED);
      this.reconnectAttempts = 0;
      this.lastMessageTime = Date.now();
      this.statistics.lastConnectedAt = new Date().toISOString();

      // 启动心跳和健康检查
      this._startHeartbeat();
      this._startHealthCheck();

      // 调用连接回调
      if (this.callbacks.onConnected) {
        this.callbacks.onConnected();
      }

      // 发送连接确认消息
      this._sendConnectionAck();
    });

    // 接收消息
    this.socket.onMessage((res) => {
      console.log('[WebSocket] 收到消息:', res.data);
      this.lastMessageTime = Date.now();
      this._handleMessage(res.data);
    });

    // 连接关闭
    this.socket.onClose((res) => {
      console.log('[WebSocket] 连接已关闭:', res);
      this._setState(ConnectionState.DISCONNECTED);
      this._stopHeartbeat();
      this._stopHealthCheck();
      this.statistics.lastDisconnectedAt = new Date().toISOString();

      // 调用断开回调
      if (this.callbacks.onDisconnected) {
        this.callbacks.onDisconnected(res);
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
   * 发送连接确认消息
   * @private
   */
  _sendConnectionAck() {
    if (this.socket && this.state === ConnectionState.CONNECTED) {
      this.socket.send({
        data: JSON.stringify({
          type: 'connection_ack',
          executionId: this.executionId,
          timestamp: new Date().toISOString()
        })
      });
    }
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
          // 心跳响应，重置超时计时器
          this._resetHeartbeatTimeout();
          break;

        case 'ping':
          // 服务端 ping，回复 pong
          this._sendPong();
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
   * @param {Object} error - 错误对象
   */
  _handleConnectionFailed(error) {
    this._setState(ConnectionState.DISCONNECTED);
    clearTimeout(this.connectionTimeout);
    this._stopHeartbeat();
    this._stopHealthCheck();
    this.statistics.failedReconnects++;

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
   * 尝试重连（指数退避 + 随机抖动）
   * @private
   */
  _attemptReconnect() {
    if (this.reconnectAttempts >= CONFIG.MAX_RECONNECT_ATTEMPTS) {
      console.error('[WebSocket] 重连次数已达上限（' + CONFIG.MAX_RECONNECT_ATTEMPTS + '次），使用轮询降级方案');
      this._setState(ConnectionState.FALLBACK);
      if (this.callbacks.onFallback) {
        this.callbacks.onFallback();
      }
      return;
    }

    this.reconnectAttempts++;
    this.statistics.totalReconnects++;

    // 计算重连间隔：指数退避 + 随机抖动
    const baseDelay = Math.min(
      CONFIG.INITIAL_RECONNECT_INTERVAL * Math.pow(2, this.reconnectAttempts - 1),
      CONFIG.MAX_RECONNECT_INTERVAL
    );

    // 添加随机抖动（±30%）
    const jitter = (Math.random() - 0.5) * 2 * CONFIG.JITTER_FACTOR * baseDelay;
    const delay = Math.max(1000, baseDelay + jitter);

    console.log(`[WebSocket] ${Math.round(delay)}ms 后尝试第 ${this.reconnectAttempts} 次重连` +
                `（基础：${baseDelay}ms, 抖动：${Math.round(jitter)}ms）`);

    this._setState(ConnectionState.RECONNECTING);

    setTimeout(() => {
      if (this.executionId) {
        console.log('[WebSocket] 开始重连...');
        const success = this.connect(this.executionId, this.callbacks);
        if (success) {
          this.statistics.successfulReconnects++;
        } else {
          this.statistics.failedReconnects++;
        }
      }
    }, delay);
  }

  /**
   * 启动心跳
   * @private
   */
  _startHeartbeat() {
    this._stopHeartbeat();

    // 定期发送心跳
    this.heartbeatTimer = setInterval(() => {
      if (this.state === ConnectionState.CONNECTED && this.socket) {
        console.log('[WebSocket] 发送心跳');
        this.socket.send({
          data: JSON.stringify({
            type: 'heartbeat',
            timestamp: new Date().toISOString(),
            reconnectAttempts: this.reconnectAttempts
          })
        });

        // 启动心跳超时计时器
        this._startHeartbeatTimeout();
      }
    }, CONFIG.HEARTBEAT_INTERVAL);
  }

  /**
   * 启动心跳超时计时器
   * @private
   */
  _startHeartbeatTimeout() {
    this._stopHeartbeatTimeout();

    this.heartbeatTimeoutTimer = setTimeout(() => {
      console.warn('[WebSocket] 心跳超时，可能连接已断开');
      // 不立即断开，等待下一次心跳或健康检查
      if (this.callbacks.onDisconnected) {
        this.callbacks.onDisconnected({ reason: 'heartbeat_timeout' });
      }
    }, CONFIG.HEARTBEAT_TIMEOUT);
  }

  /**
   * 重置心跳超时计时器
   * @private
   */
  _resetHeartbeatTimeout() {
    clearTimeout(this.heartbeatTimeoutTimer);
    this.heartbeatTimeoutTimer = null;
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
    this._stopHeartbeatTimeout();
  }

  /**
   * 停止心跳超时计时器
   * @private
   */
  _stopHeartbeatTimeout() {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  /**
   * 发送 Pong 响应
   * @private
   */
  _sendPong() {
    if (this.socket && this.state === ConnectionState.CONNECTED) {
      this.socket.send({
        data: JSON.stringify({
          type: 'pong',
          timestamp: new Date().toISOString()
        })
      });
    }
  }

  /**
   * 启动健康检查
   * @private
   */
  _startHealthCheck() {
    this._stopHealthCheck();

    // 定期检查连接健康状态
    this.healthCheckTimer = setInterval(() => {
      if (this.state !== ConnectionState.CONNECTED) {
        return;
      }

      const now = Date.now();
      const idleTime = this.lastMessageTime ? (now - this.lastMessageTime) : 0;

      // 如果长时间没有收到消息，主动检查
      if (idleTime > CONFIG.IDLE_TIMEOUT) {
        console.warn(`[WebSocket] 连接空闲时间过长（${idleTime}ms），执行健康检查`);

        // 发送 ping 消息检查连接
        this.socket.send({
          data: JSON.stringify({
            type: 'ping',
            timestamp: new Date().toISOString()
          })
        });

        // 如果还是没有响应，考虑断开重连
        if (idleTime > CONFIG.IDLE_TIMEOUT * 2) {
          console.warn('[WebSocket] 连接可能已断开，尝试重连');
          this.socket.close();
        }
      }

      // 记录连接统计
      this._logConnectionStats();
    }, CONFIG.HEALTH_CHECK_INTERVAL);
  }

  /**
   * 停止健康检查
   * @private
   */
  _stopHealthCheck() {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
  }

  /**
   * 记录连接统计
   * @private
   */
  _logConnectionStats() {
    const downtime = this.statistics.totalDowntime;
    const uptime = this.statistics.lastConnectedAt ?
      (Date.now() - new Date(this.statistics.lastConnectedAt).getTime()) : 0;
    const availability = uptime / (uptime + downtime) * 100;

    console.log(`[WebSocket] 连接统计 - 可用性：${availability.toFixed(2)}%, ` +
                `重连：${this.statistics.totalReconnects}, ` +
                `成功：${this.statistics.successfulReconnects}, ` +
                `失败：${this.statistics.failedReconnects}`);
  }

  /**
   * 设置连接状态
   * @private
   * @param {string} newState - 新状态
   */
  _setState(newState) {
    const oldState = this.state;
    this.state = newState;

    console.log(`[WebSocket] 状态变更：${oldState} -> ${newState}`);

    // 调用状态变更回调
    if (this.callbacks.onStateChange) {
      this.callbacks.onStateChange(newState, oldState);
    }

    // 更新统计
    if (newState === ConnectionState.DISCONNECTED && oldState === ConnectionState.CONNECTED) {
      this.statistics.totalDowntime += Date.now() - (this.lastMessageTime || Date.now());
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
    this._setState(ConnectionState.DISCONNECTED);
    this._stopHeartbeat();
    this._stopHealthCheck();
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
   * @returns {string} 连接状态
   */
  getConnectionStatus() {
    return this.state;
  }

  /**
   * 获取连接状态（布尔值，兼容旧接口）
   * @returns {boolean} 是否已连接
   */
  isConnected() {
    return this.state === ConnectionState.CONNECTED;
  }

  /**
   * 获取重连次数
   * @returns {number} 重连次数
   */
  getReconnectAttempts() {
    return this.reconnectAttempts;
  }

  /**
   * 获取连接统计信息
   * @returns {Object} 统计信息
   */
  getStatistics() {
    return { ...this.statistics };
  }

  /**
   * 重置统计信息
   */
  resetStatistics() {
    this.statistics = {
      totalReconnects: 0,
      successfulReconnects: 0,
      failedReconnects: 0,
      lastConnectedAt: null,
      lastDisconnectedAt: null,
      totalDowntime: 0
    };
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
 *   onStateChange: (newState, oldState) => {
 *     console.log(`状态变更：${oldState} -> ${newState}`);
 *     // 更新 UI 状态指示器
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
 *   onDisconnected: (res) => {
 *     console.log('连接已断开:', res);
 *   },
 *   onFallback: () => {
 *     console.log('降级到轮询模式');
 *     // 启动轮询
 *   }
 * });
 *
 * // 获取连接统计
 * const stats = webSocketClient.getStatistics();
 * console.log('连接统计:', stats);
 *
 * // 页面卸载时断开
 * onUnload() {
 *   webSocketClient.disconnect();
 * }
 */
