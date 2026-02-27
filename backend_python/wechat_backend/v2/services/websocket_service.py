"""
WebSocket 实时推送服务

功能：
- WebSocket 服务器管理
- 诊断进度实时推送
- 客户端连接管理
- 消息广播

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

import asyncio
import websockets
import json
from typing import Dict, Set, Any, Optional
from datetime import datetime
from wechat_backend.logging_config import api_logger


class WebSocketService:
    """
    WebSocket 服务
    
    管理客户端连接和消息推送
    """
    
    def __init__(self):
        """初始化 WebSocket 服务"""
        # 客户端连接存储：execution_id -> Set[websocket]
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        # 连接总数统计
        self.connection_count = 0
        self.logger = api_logger
    
    async def register(
        self,
        execution_id: str,
        websocket: websockets.WebSocketServerProtocol
    ) -> None:
        """
        注册客户端连接
        
        参数:
            execution_id: 诊断执行 ID
            websocket: WebSocket 连接对象
        """
        if execution_id not in self.clients:
            self.clients[execution_id] = set()
        
        self.clients[execution_id].add(websocket)
        self.connection_count += 1
        
        self.logger.info("websocket_client_registered", extra={
            'event': 'websocket_client_registered',
            'execution_id': execution_id,
            'total_connections': self.connection_count,
            'timestamp': datetime.now().isoformat()
        })
    
    async def unregister(
        self,
        execution_id: str,
        websocket: websockets.WebSocketServerProtocol
    ) -> None:
        """
        注销客户端连接
        
        参数:
            execution_id: 诊断执行 ID
            websocket: WebSocket 连接对象
        """
        if execution_id in self.clients:
            self.clients[execution_id].discard(websocket)
            
            # 如果没有客户端了，删除该 execution_id 的记录
            if not self.clients[execution_id]:
                del self.clients[execution_id]
            
            self.connection_count -= 1
            
            self.logger.info("websocket_client_unregistered", extra={
                'event': 'websocket_client_unregistered',
                'execution_id': execution_id,
                'total_connections': self.connection_count,
                'timestamp': datetime.now().isoformat()
            })
    
    async def broadcast(
        self,
        execution_id: str,
        message: Dict[str, Any]
    ) -> None:
        """
        广播消息给所有订阅该 execution_id 的客户端
        
        参数:
            execution_id: 诊断执行 ID
            message: 消息内容
        """
        if execution_id not in self.clients:
            return
        
        # 构建完整消息
        full_message = {
            'type': 'diagnosis_update',
            'execution_id': execution_id,
            'timestamp': datetime.now().isoformat(),
            **message
        }
        
        message_json = json.dumps(full_message, ensure_ascii=False)
        
        # 异步发送给所有客户端
        await asyncio.gather(
            *[self._send_to_client(client, message_json) 
              for client in self.clients[execution_id]],
            return_exceptions=True
        )
    
    async def _send_to_client(
        self,
        client: websockets.WebSocketServerProtocol,
        message: str
    ) -> None:
        """
        发送给单个客户端
        
        参数:
            client: WebSocket 连接对象
            message: 消息内容
        """
        try:
            await client.send(message)
        except websockets.exceptions.ConnectionClosed:
            # 客户端已断开，忽略
            pass
        except Exception as e:
            self.logger.error("websocket_send_failed", extra={
                'event': 'websocket_send_failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    async def send_progress(
        self,
        execution_id: str,
        progress: int,
        stage: str,
        status: str,
        status_text: Optional[str] = None
    ) -> None:
        """
        发送进度更新
        
        参数:
            execution_id: 诊断执行 ID
            progress: 进度 (0-100)
            stage: 阶段
            status: 状态
            status_text: 状态文本
        """
        await self.broadcast(execution_id, {
            'event': 'progress',
            'data': {
                'progress': progress,
                'stage': stage,
                'status': status,
                'status_text': status_text or ''
            }
        })
    
    async def send_result(
        self,
        execution_id: str,
        result: Dict[str, Any]
    ) -> None:
        """
        发送中间结果
        
        参数:
            execution_id: 诊断执行 ID
            result: 结果数据
        """
        await self.broadcast(execution_id, {
            'event': 'result',
            'data': result
        })
    
    async def send_complete(
        self,
        execution_id: str,
        final_report: Dict[str, Any]
    ) -> None:
        """
        发送完成通知
        
        参数:
            execution_id: 诊断执行 ID
            final_report: 最终报告
        """
        await self.broadcast(execution_id, {
            'event': 'complete',
            'data': final_report
        })
    
    async def send_error(
        self,
        execution_id: str,
        error: str,
        error_type: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发送错误通知
        
        参数:
            execution_id: 诊断执行 ID
            error: 错误消息
            error_type: 错误类型
            error_details: 详细错误信息
        """
        await self.broadcast(execution_id, {
            'event': 'error',
            'data': {
                'error': error,
                'error_type': error_type,
                'error_details': error_details or {}
            }
        })
    
    def get_active_connection_count(self) -> int:
        """
        获取活跃连接数
        
        返回:
            活跃连接数
        """
        return self.connection_count
    
    def get_execution_subscribers(self, execution_id: str) -> int:
        """
        获取指定 execution_id 的订阅者数量
        
        参数:
            execution_id: 诊断执行 ID
            
        返回:
            订阅者数量
        """
        if execution_id not in self.clients:
            return 0
        return len(self.clients[execution_id])


# 全局 WebSocket 服务实例
websocket_service = WebSocketService()


# WebSocket 服务器处理器
async def websocket_handler(
    websocket: websockets.WebSocketServerProtocol,
    path: str
) -> None:
    """
    WebSocket 连接处理器
    
    参数:
        websocket: WebSocket 连接对象
        path: 连接路径（格式：/ws/diagnosis/{execution_id}）
    """
    # 从路径中提取 execution_id
    # 路径格式：/ws/diagnosis/{execution_id}
    parts = path.strip('/').split('/')
    if len(parts) >= 3 and parts[0] == 'ws' and parts[1] == 'diagnosis':
        execution_id = parts[2]
    else:
        await websocket.close(1008, 'Invalid path')
        return
    
    # 注册客户端
    await websocket_service.register(execution_id, websocket)
    
    try:
        # 保持连接，接收客户端消息（心跳等）
        async for message in websocket:
            # 处理客户端消息（如心跳）
            try:
                data = json.loads(message)
                if data.get('type') == 'heartbeat':
                    # 响应心跳
                    await websocket.send(json.dumps({
                        'type': 'heartbeat_ack',
                        'timestamp': datetime.now().isoformat()
                    }))
            except json.JSONDecodeError:
                # 忽略无效消息
                pass
    except websockets.exceptions.ConnectionClosed:
        # 客户端正常断开
        pass
    except Exception as e:
        api_logger.error("websocket_handler_error", extra={
            'event': 'websocket_handler_error',
            'error': str(e),
            'execution_id': execution_id,
            'timestamp': datetime.now().isoformat()
        })
    finally:
        # 注销客户端
        await websocket_service.unregister(execution_id, websocket)


class WebSocketServer:
    """
    WebSocket 服务器
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8765):
        """
        初始化 WebSocket 服务器
        
        参数:
            host: 监听地址
            port: 监听端口
        """
        self.host = host
        self.port = port
        self.server = None
    
    def start(self) -> None:
        """
        启动服务器（同步方法，用于生产环境）
        """
        self.server = websockets.serve(
            websocket_handler,
            self.host,
            self.port
        )
        
        api_logger.info("websocket_server_started", extra={
            'event': 'websocket_server_started',
            'host': self.host,
            'port': self.port,
            'timestamp': datetime.now().isoformat()
        })
        
        asyncio.get_event_loop().run_until_complete(self.server)
        asyncio.get_event_loop().run_forever()
    
    async def start_async(self) -> None:
        """
        启动服务器（异步方法，用于测试环境）
        """
        self.server = websockets.serve(
            websocket_handler,
            self.host,
            self.port
        )
        
        await self.server
        
        api_logger.info("websocket_server_started", extra={
            'event': 'websocket_server_started',
            'host': self.host,
            'port': self.port,
            'timestamp': datetime.now().isoformat()
        })
    
    def stop(self) -> None:
        """
        停止服务器
        """
        if self.server:
            self.server.close()
            asyncio.get_event_loop().run_until_complete(self.server.wait_closed())
        
        api_logger.info("websocket_server_stopped", extra={
            'event': 'websocket_server_stopped',
            'timestamp': datetime.now().isoformat()
        })


# 便捷函数
def get_websocket_service() -> WebSocketService:
    """
    获取 WebSocket 服务实例
    
    返回:
        WebSocket 服务实例
    """
    return websocket_service
