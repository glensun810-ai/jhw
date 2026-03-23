/**
 * WebSocket 连接管理器（增强版 - P1-08）
 * 
 * 功能:
 * - 自动重连
 * - 心跳检测
 * - 断线降级到 HTTP 轮询
 * - 连接状态管理
 * 
 * @author: 系统架构组
 * @date: 2026-03-14
 * @version: 2.0.0
 */

import { logError } from './errorHandler';

class WebSocketManager {
  constructor(options = {}) {
    this.url = options.url || 'ws://localhost:8765';
    this.reconnectInterval = options.reconnectInterval || 3000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    this.heartbeatInterval = options.heartbeatInterval || 30000;
    this.connectionTimeout = options.connectionTimeout || 10000;
    
    this.ws = null;
    this.reconnectAttempts = 0;
    this.heartbeatTimer = null;
    this.connectionTimeoutTimer = null;
    this.listeners = new Map();
    this.state = 'disconnected'; // disconnected | connecting | connected | reconnecting
    this.fallbackToPolling = false;
    
    console.log('[WebSocketManager] 初始化完成', {
      url: this.url,
      reconnectInterval: this.reconnectInterval,
      maxReconnectAttempts: this.maxReconnectAttempts
    });
  }
  
  /**
   * 连接 WebSocket
   */
  connect() {
    if (this.state === 'connected' || this.state === 'connecting') {
      console.log('[WebSocketManager] 已连接或正在连接，跳过');
      return;
    }
    
    this.state = 'connecting';
    this._emit('connecting', { attempts: this.reconnectAttempts });
    
    try {
      this.ws = wx.connectSocket({
        url: this.url,
        success: () => {
          console.log('[WebSocketManager] 连接请求已发送');
        },
        fail: (error) => {
          console.error('[WebSocketManager] 连接失败:', error);
          this._handleConnectionFail(error);
        }
      });
      
      // 设置连接超时
      this.connectionTimeoutTimer = setTimeout(() => {
        if (this.state === 'connecting') {
          console.warn('[WebSocketManager] 连接超时');
          this._handleConnectionFail(new Error('连接超时'));
        }
      }, this.connectionTimeout);
      
      // 监听打开事件
      this.ws.onOpen(() => {
        console.log('[WebSocketManager] ✅ 连接成功');
        clearTimeout(this.connectionTimeoutTimer);
        this.state = 'connected';
        this.reconnectAttempts = 0;
        this._emit('connected', {});
        this._startHeartbeat();
      });
      
      // 监听消息事件
      this.ws.onMessage((res) => {
        this._handleMessage(res.data);
      });
      
      // 监听关闭事件
      this.ws.onClose((res) => {
        console.log('[WebSocketManager] ❌ 连接关闭:', res);
        this._handleClose(res);
      });
      
      // 监听错误事件
      this.ws.onError((error) => {
        console.error('[WebSocketManager] ❌ 连接错误:', error);
        this._handleError(error);
      });
      
    } catch (error) {
      console.error('[WebSocketManager] 创建连接失败:', error);
      this._handleConnectionFail(error);
    }
  }
  
  /**
   * 发送消息
   */
  send(data) {
    if (this.state !== 'connected' || !this.ws) {
      console.warn('[WebSocketManager] 连接未建立，无法发送消息');
      return false;
    }
    
    try {
      this.ws.send({
        data: typeof data === 'string' ? data : JSON.stringify(data)
      });
      return true;
    } catch (error) {
      console.error('[WebSocketManager] 发送消息失败:', error);
      return false;
    }
  }
  
  /**
   * 发送心跳
   */
  _sendHeartbeat() {
    const heartbeatData = {
      type: 'heartbeat',
      timestamp: Date.now()
    };
    
    if (!this.send(heartbeatData)) {
      console.warn('[WebSocketManager] 心跳发送失败');
    } else {
      console.debug('[WebSocketManager] 💓 心跳已发送');
    }
  }
  
  /**
   * 启动心跳
   */
  _startHeartbeat() {
    this._stopHeartbeat();
    
    this.heartbeatTimer = setInterval(() => {
      this._sendHeartbeat();
    }, this.heartbeatInterval);
    
    console.log('[WebSocketManager] 心跳已启动，间隔:', this.heartbeatInterval, 'ms');
  }
  
  /**
   * 停止心跳
   */
  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
  
  /**
   * 处理消息
   */
  _handleMessage(data) {
    try {
      const message = typeof data === 'string' ? JSON.parse(data) : data;
      
      // 心跳响应
      if (message.type === 'heartbeat_ack') {
        console.debug('[WebSocketManager] 💓 心跳响应');
        return;
      }
      
      // 分发事件
      this._emit('message', message);
      
      // 分发特定类型事件
      if (message.type) {
        this._emit(message.type, message.data || message);
      }
      
    } catch (error) {
      console.error('[WebSocketManager] 解析消息失败:', error);
      logError(error, { context: 'WebSocketMessage', rawData: data });
    }
  }
  
  /**
   * 处理连接失败
   */
  _handleConnectionFail(error) {
    this.state = 'disconnected';
    this._emit('error', { error, type: 'connection_fail' });
    
    // 尝试重连
    this._scheduleReconnect();
  }
  
  /**
   * 处理关闭
   */
  _handleClose(res) {
    this.state = 'disconnected';
    this._stopHeartbeat();
    this._emit('disconnected', res);
    
    // 非正常关闭时尝试重连
    if (res && res.code !== 1000) {
      this._scheduleReconnect();
    }
  }
  
  /**
   * 处理错误
   */
  _handleError(error) {
    this._emit('error', error);
    logError(error, { context: 'WebSocketError' });
  }
  
  /**
   * 安排重连
   */
  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocketManager] 重连次数已达上限，降级到轮询');
      this.fallbackToPolling = true;
      this._emit('fallback_to_polling', {
        reason: 'max_reconnect_attempts',
        attempts: this.reconnectAttempts
      });
      return;
    }
    
    this.reconnectAttempts++;
    this.state = 'reconnecting';
    
    // 指数退避
    const delay = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000 // 最大 30 秒
    );
    
    console.log(`[WebSocketManager] ${delay}ms 后重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }
  
  /**
   * 监听事件
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
    
    return () => this.off(event, callback);
  }
  
  /**
   * 移除事件监听
   */
  off(event, callback) {
    if (!this.listeners.has(event)) {
      return;
    }
    
    const callbacks = this.listeners.get(event);
    const index = callbacks.indexOf(callback);
    if (index > -1) {
      callbacks.splice(index, 1);
    }
  }
  
  /**
   * 触发事件
   */
  _emit(event, data) {
    if (!this.listeners.has(event)) {
      return;
    }
    
    const callbacks = this.listeners.get(event);
    callbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`[WebSocketManager] 事件回调失败 [${event}]:`, error);
      }
    });
  }
  
  /**
   * 断开连接
   */
  disconnect() {
    console.log('[WebSocketManager] 主动断开连接');
    
    this.state = 'disconnected';
    this._stopHeartbeat();
    this.reconnectAttempts = 0;
    this.fallbackToPolling = false;
    
    if (this.ws) {
      this.ws.close({
        code: 1000,
        reason: '用户主动断开'
      });
      this.ws = null;
    }
  }
  
  /**
   * 获取连接状态
   */
  getState() {
    return this.state;
  }
  
  /**
   * 是否需要降级到轮询
   */
  shouldFallbackToPolling() {
    return this.fallbackToPolling;
  }
  
  /**
   * 销毁
   */
  destroy() {
    this.disconnect();
    this.listeners.clear();
  }
}

export default WebSocketManager;
