"""
SSE (Server-Sent Events) 实时推送服务
用于向客户端推送诊断进度和情报更新
"""

import json
import time
import threading
from typing import Dict, Set, Any, Optional
from datetime import datetime
from flask import Response, request
from wechat_backend.logging_config import api_logger


class SSEConnection:
    """SSE 连接"""
    
    def __init__(self, execution_id: str, client_id: str):
        self.execution_id = execution_id
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.message_queue = []
        self.is_active = True
    
    def send(self, event_type: str, data: Dict[str, Any]):
        """发送消息到队列"""
        message = {
            'id': int(time.time() * 1000),
            'event': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.message_queue.append(message)
        api_logger.debug(f"[SSE] Queued message for {self.client_id}: {event_type}")
    
    def get_pending_messages(self) -> list:
        """获取待发送的消息"""
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages
    
    def heartbeat(self):
        """更新心跳"""
        self.last_heartbeat = datetime.now()
    
    def close(self):
        """关闭连接"""
        self.is_active = False


class SSEManager:
    """SSE 连接管理器"""
    
    def __init__(self):
        # execution_id -> Set[client_id]
        self.execution_connections: Dict[str, Set[str]] = {}
        # client_id -> SSEConnection
        self.connections: Dict[str, SSEConnection] = {}
        self._lock = threading.Lock()
    
    def add_connection(self, execution_id: str, client_id: str) -> SSEConnection:
        """添加新连接"""
        with self._lock:
            connection = SSEConnection(execution_id, client_id)
            self.connections[client_id] = connection
            
            if execution_id not in self.execution_connections:
                self.execution_connections[execution_id] = set()
            self.execution_connections[execution_id].add(client_id)
            
            api_logger.info(f"[SSE] New connection: {client_id} for execution {execution_id}")
            return connection
    
    def remove_connection(self, client_id: str):
        """移除连接"""
        with self._lock:
            if client_id in self.connections:
                connection = self.connections[client_id]
                execution_id = connection.execution_id
                
                del self.connections[client_id]
                
                if execution_id in self.execution_connections:
                    self.execution_connections[execution_id].discard(client_id)
                    if not self.execution_connections[execution_id]:
                        del self.execution_connections[execution_id]
                
                api_logger.info(f"[SSE] Connection removed: {client_id}")
    
    def broadcast(self, execution_id: str, event_type: str, data: Dict[str, Any]):
        """向指定执行 ID 的所有连接广播消息"""
        with self._lock:
            if execution_id not in self.execution_connections:
                return
            
            client_ids = list(self.execution_connections[execution_id])
        
        for client_id in client_ids:
            if client_id in self.connections:
                connection = self.connections[client_id]
                if connection.is_active:
                    connection.send(event_type, data)
    
    def get_connection(self, client_id: str) -> Optional[SSEConnection]:
        """获取连接"""
        return self.connections.get(client_id)
    
    def cleanup_inactive(self, timeout_seconds: int = 300):
        """清理非活动连接"""
        now = datetime.now()
        to_remove = []
        
        with self._lock:
            for client_id, connection in self.connections.items():
                elapsed = (now - connection.last_heartbeat).total_seconds()
                if elapsed > timeout_seconds:
                    to_remove.append(client_id)
        
        for client_id in to_remove:
            self.remove_connection(client_id)
            api_logger.info(f"[SSE] Cleaned up inactive connection: {client_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                'total_connections': len(self.connections),
                'total_executions': len(self.execution_connections),
                'connections_by_execution': {
                    exec_id: len(client_ids) 
                    for exec_id, client_ids in self.execution_connections.items()
                }
            }


# 全局 SSE 管理器实例
_sse_manager = None


def get_sse_manager() -> SSEManager:
    """获取全局 SSE 管理器"""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEManager()
    return _sse_manager


def create_sse_response(client_id: str) -> Response:
    """
    创建 SSE 响应
    
    Args:
        client_id: 客户端 ID
    
    Returns:
        Flask Response object for SSE
    """
    manager = get_sse_manager()
    connection = manager.get_connection(client_id)
    
    if not connection:
        api_logger.error(f"[SSE] Connection not found for client: {client_id}")
        return Response(
            "event: error\ndata: {\"error\": \"Connection not found\"}\n\n",
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    
    def generate():
        """生成 SSE 事件流"""
        # 发送连接成功消息
        yield f"event: connected\ndata: {json.dumps({'client_id': client_id, 'timestamp': datetime.now().isoformat()})}\n\n"
        
        try:
            while connection.is_active:
                # 获取待发送的消息
                messages = connection.get_pending_messages()
                
                for message in messages:
                    yield f"event: {message['event']}\nid: {message['id']}\ndata: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
                
                # 心跳消息（每 30 秒）
                connection.heartbeat()
                
                # 短暂休眠
                time.sleep(0.5)
                
        except GeneratorExit:
            api_logger.info(f"[SSE] Client disconnected: {client_id}")
            manager.remove_connection(client_id)
        except Exception as e:
            api_logger.error(f"[SSE] Error in stream for {client_id}: {e}")
            manager.remove_connection(client_id)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )


def send_progress_update(execution_id: str, progress: int, stage: str, status_text: str, **extra):
    """
    发送进度更新
    
    Args:
        execution_id: 执行 ID
        progress: 进度百分比 (0-100)
        stage: 当前阶段
        status_text: 状态文本
        **extra: 额外数据
    """
    manager = get_sse_manager()
    data = {
        'progress': progress,
        'stage': stage,
        'statusText': status_text,
        'timestamp': datetime.now().isoformat(),
        **extra
    }
    manager.broadcast(execution_id, 'progress', data)


def send_intelligence_update(execution_id: str, item: Dict[str, Any]):
    """
    发送情报更新
    
    Args:
        execution_id: 执行 ID
        item: 情报项数据
    """
    manager = get_sse_manager()
    data = {
        'item': item,
        'timestamp': datetime.now().isoformat()
    }
    manager.broadcast(execution_id, 'intelligence', data)


def send_task_complete(execution_id: str, results: Dict[str, Any]):
    """
    发送任务完成通知
    
    Args:
        execution_id: 执行 ID
        results: 结果数据
    """
    manager = get_sse_manager()
    data = {
        'results': results,
        'timestamp': datetime.now().isoformat()
    }
    manager.broadcast(execution_id, 'complete', data)


def send_error(execution_id: str, error: str, error_code: str = None):
    """
    发送错误通知
    
    Args:
        execution_id: 执行 ID
        error: 错误信息
        error_code: 错误代码
    """
    manager = get_sse_manager()
    data = {
        'error': error,
        'errorCode': error_code,
        'timestamp': datetime.now().isoformat()
    }
    manager.broadcast(execution_id, 'error', data)


# 后台清理线程
_cleanup_thread = None


def start_cleanup_thread(interval: int = 60):
    """启动后台清理线程"""
    global _cleanup_thread
    
    def cleanup_loop():
        while True:
            time.sleep(interval)
            get_sse_manager().cleanup_inactive()
    
    _cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    _cleanup_thread.start()
    api_logger.info("[SSE] Cleanup thread started")


# 自动启动清理线程
start_cleanup_thread()
