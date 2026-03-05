"""
SSE Service - 向后兼容层

注意：此模块是为了向后兼容而创建的适配层。
新代码应该直接使用 websocket_route 和 realtime_push_service。

SSE (Server-Sent Events) 用于 Web 管理后台的单向推送。
微信小程序使用 WebSocket（双向通信）。

@author: 系统架构组
@date: 2026-03-03
@version: 1.0.0 (兼容性适配层)
"""

import json
import threading
import time
from typing import Dict, Optional, Any
from datetime import datetime
from flask import Response, request
from wechat_backend.logging_config import api_logger


# ============================================================================
# SSE 管理器（向后兼容）
# ============================================================================

class SSEConnection:
    """SSE 连接"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self._send_func = None
    
    def send(self, data: dict):
        """发送数据"""
        if self._send_func:
            self._send_func(data)
        self.last_activity = datetime.now()


class SSEManager:
    """
    SSE 管理器（兼容性实现）
    
    注意：此实现是为了向后兼容，新代码应该使用 WebSocket。
    """
    
    def __init__(self):
        self._connections: Dict[str, SSEConnection] = {}
        self._lock = threading.Lock()
    
    def add_connection(self, client_id: str, connection: SSEConnection) -> None:
        """添加连接"""
        with self._lock:
            self._connections[client_id] = connection
            api_logger.debug(f"[SSE] 连接已添加：{client_id}")
    
    def remove_connection(self, client_id: str) -> None:
        """移除连接"""
        with self._lock:
            if client_id in self._connections:
                del self._connections[client_id]
                api_logger.debug(f"[SSE] 连接已移除：{client_id}")
    
    def get_connection(self, client_id: str) -> Optional[SSEConnection]:
        """获取连接"""
        with self._lock:
            return self._connections.get(client_id)
    
    def send_to_client(self, client_id: str, event: str, data: Any) -> bool:
        """
        发送事件到客户端
        
        参数：
            client_id: 客户端 ID
            event: 事件类型
            data: 数据
        
        返回：
            是否发送成功
        """
        connection = self.get_connection(client_id)
        if not connection:
            api_logger.warning(f"[SSE] 连接不存在：{client_id}")
            return False
        
        try:
            message = {
                'event': event,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            connection.send(message)
            return True
        except Exception as e:
            api_logger.error(f"[SSE] 发送失败：{e}")
            return False
    
    def cleanup_stale_connections(self, timeout_seconds: int = 300) -> int:
        """清理超时的连接"""
        cleaned = 0
        now = datetime.now()
        with self._lock:
            to_remove = []
            for client_id, conn in self._connections.items():
                if (now - conn.last_activity).total_seconds() > timeout_seconds:
                    to_remove.append(client_id)
            
            for client_id in to_remove:
                del self._connections[client_id]
                cleaned += 1
                api_logger.debug(f"[SSE] 清理超时连接：{client_id}")
        
        return cleaned


# ============================================================================
# 全局 SSE 管理器实例
# ============================================================================

_sse_manager: Optional[SSEManager] = None


def get_sse_manager() -> SSEManager:
    """获取全局 SSE 管理器"""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEManager()
        # 启动后台清理线程
        _start_cleanup_thread()
    return _sse_manager


def _start_cleanup_thread() -> None:
    """启动后台清理线程"""
    def cleanup_loop():
        while True:
            time.sleep(60)  # 每分钟清理一次
            manager = get_sse_manager()
            cleaned = manager.cleanup_stale_connections()
            if cleaned > 0:
                api_logger.info(f"[SSE] 清理了 {cleaned} 个超时连接")


# ============================================================================
# SSE 响应创建（Flask）
# ============================================================================

def create_sse_response(client_id: str) -> Response:
    """
    创建 SSE 响应
    
    参数：
        client_id: 客户端 ID
    
    返回：
        Flask Response 对象
    """
    manager = get_sse_manager()
    
    # 创建连接
    connection = SSEConnection(client_id)
    manager.add_connection(client_id, connection)
    
    # 消息队列
    messages = []
    messages_lock = threading.Lock()
    
    def send_message(data: dict):
        with messages_lock:
            messages.append(f"data: {json.dumps(data)}\n\n")
    
    connection._send_func = send_message
    
    def generate():
        """生成 SSE 事件流"""
        # 发送初始连接消息
        yield f"data: {json.dumps({'event': 'connected', 'client_id': client_id})}\n\n"
        
        try:
            while True:
                with messages_lock:
                    if messages:
                        msg = messages.pop(0)
                        yield msg
                    else:
                        # 保持连接，定期发送心跳
                        yield f": heartbeat\n\n"
                        time.sleep(30)
        except GeneratorExit:
            # 客户端断开连接
            manager.remove_connection(client_id)
            api_logger.info(f"[SSE] 客户端断开：{client_id}")
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用 Nginx 缓冲
        }
    )


# ============================================================================
# 便捷发送函数（兼容性 API）
# ============================================================================

def send_progress_update(
    client_id: str,
    progress: int,
    stage: str,
    status: str,
    status_text: str = "",
    data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    发送进度更新
    
    参数：
        client_id: 客户端 ID
        progress: 进度百分比 (0-100)
        stage: 阶段 (initializing, ai-fetching, analyzing, completed, failed)
        status: 状态 (running, success, failed)
        status_text: 状态文本描述
        data: 额外数据
    
    返回：
        是否发送成功
    """
    manager = get_sse_manager()
    
    payload = {
        'progress': progress,
        'stage': stage,
        'status': status,
        'status_text': status_text,
        'timestamp': datetime.now().isoformat()
    }
    
    if data:
        payload.update(data)
    
    return manager.send_to_client(client_id, 'progress', payload)


def send_intelligence_update(
    client_id: str,
    intelligence_type: str,
    data: Dict[str, Any]
) -> bool:
    """
    发送智能分析更新
    
    参数：
        client_id: 客户端 ID
        intelligence_type: 智能类型 (source_analysis, interception, monetization, etc.)
        data: 智能分析数据
    
    返回：
        是否发送成功
    """
    manager = get_sse_manager()
    
    payload = {
        'type': intelligence_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    
    return manager.send_to_client(client_id, 'intelligence', payload)


def send_task_complete(
    client_id: str,
    result: Dict[str, Any]
) -> bool:
    """
    发送任务完成通知
    
    参数：
        client_id: 客户端 ID
        result: 任务结果
    
    返回：
        是否发送成功
    """
    manager = get_sse_manager()
    
    payload = {
        'result': result,
        'timestamp': datetime.now().isoformat()
    }
    
    return manager.send_to_client(client_id, 'complete', payload)


def send_error(
    client_id: str,
    error: str,
    error_type: str = 'unknown',
    error_details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    发送错误通知
    
    参数：
        client_id: 客户端 ID
        error: 错误消息
        error_type: 错误类型
        error_details: 错误详情
    
    返回：
        是否发送成功
    """
    manager = get_sse_manager()
    
    payload = {
        'error': error,
        'error_type': error_type,
        'timestamp': datetime.now().isoformat()
    }
    
    if error_details:
        payload['details'] = error_details
    
    return manager.send_to_client(client_id, 'error', payload)


# ============================================================================
# 初始化
# ============================================================================

__all__ = [
    'SSEManager',
    'SSEConnection',
    'get_sse_manager',
    'create_sse_response',
    'send_progress_update',
    'send_intelligence_update',
    'send_task_complete',
    'send_error',
]
