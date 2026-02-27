"""
WebSocket 实时推送服务（增强稳定版）

功能：
- WebSocket 服务器管理
- 诊断进度实时推送
- 客户端连接管理
- 消息广播
- 双向心跳检测
- 连接健康检查
- 自动清理僵尸连接

优化点：
1. 服务端主动心跳（ping/pong）
2. 连接超时自动清理
3. 心跳响应处理
4. 连接统计监控
5. 优雅的错误处理

@author: 系统架构组
@date: 2026-02-28
@version: 2.1.0
"""

import asyncio
import websockets
import json
from typing import Dict, Set, Any, Optional
from datetime import datetime, timedelta
from wechat_backend.logging_config import api_logger


# WebSocket 配置常量
WS_CONFIG = {
    # 心跳间隔（秒）
    'ping_interval': 20,
    # 心跳超时（秒）- 超过这个时间没有响应认为连接已断开
    'ping_timeout': 10,
    # 连接超时（秒）
    'connect_timeout': 10,
    # 最大消息大小（字节）
    'max_size': 1024 * 1024,  # 1MB
    # 最大队列大小
    'max_queue': 32,
}


class WebSocketService:
    """
    WebSocket 服务

    管理客户端连接和消息推送
    """

    def __init__(self):
        """初始化 WebSocket 服务"""
        # 客户端连接存储：execution_id -> Set[websocket]
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        # 连接元数据：websocket -> {execution_id, connected_at, last_heartbeat, message_count}
        self.connection_metadata: Dict[websockets.WebSocketServerProtocol, Dict[str, Any]] = {}
        # 连接总数统计
        self.connection_count = 0
        self.logger = api_logger
        # 健康检查任务
        self._health_check_task: Optional[asyncio.Task] = None

    async def start_health_check(self) -> None:
        """启动连接健康检查任务"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self.logger.info("websocket_health_check_started", extra={
                'event': 'websocket_health_check_started',
                'timestamp': datetime.now().isoformat()
            })

    async def stop_health_check(self) -> None:
        """停止连接健康检查任务"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    async def _health_check_loop(self) -> None:
        """
        健康检查循环
        定期检查所有连接的健康状态，清理僵尸连接
        """
        while True:
            try:
                await asyncio.sleep(30)  # 每 30 秒检查一次
                await self._check_connections_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("websocket_health_check_error", extra={
                    'event': 'websocket_health_check_error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

    async def _check_connections_health(self) -> None:
        """检查所有连接的健康状态"""
        now = datetime.now()
        stale_connections = []

        # 查找长时间没有心跳的连接
        for ws, metadata in list(self.connection_metadata.items()):
            last_heartbeat = metadata.get('last_heartbeat')
            if last_heartbeat:
                idle_time = (now - last_heartbeat).total_seconds()
                if idle_time > WS_CONFIG['ping_timeout'] * 3:
                    stale_connections.append((ws, metadata, idle_time))

        # 清理僵尸连接
        for ws, metadata, idle_time in stale_connections:
            self.logger.warning("websocket_stale_connection_detected", extra={
                'event': 'websocket_stale_connection_detected',
                'execution_id': metadata.get('execution_id'),
                'idle_seconds': idle_time,
                'timestamp': datetime.now().isoformat()
            })
            try:
                await self.unregister(metadata['execution_id'], ws)
                await ws.close(1001, 'Connection stale')
            except Exception as e:
                self.logger.error("websocket_stale_connection_cleanup_failed", extra={
                    'event': 'websocket_stale_connection_cleanup_failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

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

        # 记录连接元数据
        self.connection_metadata[websocket] = {
            'execution_id': execution_id,
            'connected_at': datetime.now(),
            'last_heartbeat': datetime.now(),
            'message_count': 0,
            'bytes_sent': 0,
            'bytes_received': 0
        }

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

            # 清理元数据
            if websocket in self.connection_metadata:
                metadata = self.connection_metadata.pop(websocket)
                connected_duration = (datetime.now() - metadata['connected_at']).total_seconds()
                self.logger.info("websocket_client_unregistered_details", extra={
                    'event': 'websocket_client_unregistered_details',
                    'execution_id': execution_id,
                    'connected_duration_seconds': connected_duration,
                    'message_count': metadata.get('message_count', 0),
                    'bytes_sent': metadata.get('bytes_sent', 0),
                    'total_connections': self.connection_count,
                    'timestamp': datetime.now().isoformat()
                })

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
        message_bytes = len(message_json.encode('utf-8'))

        # 异步发送给所有客户端
        results = await asyncio.gather(
            *[self._send_to_client(client, message_json, message_bytes)
              for client in self.clients[execution_id]],
            return_exceptions=True
        )

        # 统计发送结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failed_count = len(results) - success_count

        if failed_count > 0:
            self.logger.warning("websocket_broadcast_partial_failure", extra={
                'event': 'websocket_broadcast_partial_failure',
                'execution_id': execution_id,
                'success_count': success_count,
                'failed_count': failed_count,
                'timestamp': datetime.now().isoformat()
            })

    async def _send_to_client(
        self,
        client: websockets.WebSocketServerProtocol,
        message: str,
        message_bytes: int
    ) -> None:
        """
        发送给单个客户端

        参数:
            client: WebSocket 连接对象
            message: 消息内容
            message_bytes: 消息字节数
        """
        try:
            await client.send(message)

            # 更新统计
            if client in self.connection_metadata:
                self.connection_metadata[client]['bytes_sent'] += message_bytes
        except websockets.exceptions.ConnectionClosed:
            # 客户端已断开，从列表中移除
            if client in self.connection_metadata:
                execution_id = self.connection_metadata[client].get('execution_id')
                await self.unregister(execution_id, client)
        except websockets.exceptions.WebSocketException as e:
            self.logger.error("websocket_send_failed", extra={
                'event': 'websocket_send_failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error("websocket_send_failed", extra={
                'event': 'websocket_send_failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    async def handle_client_message(
        self,
        websocket: websockets.WebSocketServerProtocol,
        message: str
    ) -> Optional[Dict[str, Any]]:
        """
        处理客户端消息

        参数:
            websocket: WebSocket 连接对象
            message: 消息内容

        返回:
            响应消息（如果有）
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            # 更新统计
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]['message_count'] += 1
                self.connection_metadata[websocket]['bytes_received'] += len(message)
                self.connection_metadata[websocket]['last_heartbeat'] = datetime.now()

            # 处理不同类型的消息
            if msg_type == 'heartbeat':
                # 响应心跳
                return {
                    'type': 'heartbeat_ack',
                    'timestamp': datetime.now().isoformat(),
                    'server_time': datetime.now().isoformat()
                }
            elif msg_type == 'ping':
                # 响应 ping
                return {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }
            elif msg_type == 'connection_ack':
                # 连接确认
                self.logger.info("websocket_connection_ack_received", extra={
                    'event': 'websocket_connection_ack_received',
                    'execution_id': self.connection_metadata.get(websocket, {}).get('execution_id'),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                self.logger.warning("websocket_unknown_message_type", extra={
                    'event': 'websocket_unknown_message_type',
                    'type': msg_type,
                    'timestamp': datetime.now().isoformat()
                })

        except json.JSONDecodeError:
            self.logger.warning("websocket_invalid_message", extra={
                'event': 'websocket_invalid_message',
                'message': message[:100] if len(message) > 100 else message,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error("websocket_handle_message_error", extra={
                'event': 'websocket_handle_message_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

        return None

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

    def get_connection_statistics(self) -> Dict[str, Any]:
        """
        获取连接统计信息

        返回:
            统计信息字典
        """
        now = datetime.now()
        stats = {
            'total_connections': self.connection_count,
            'by_execution_id': {},
            'connection_details': []
        }

        # 按 execution_id 分组统计
        for execution_id, clients in self.clients.items():
            stats['by_execution_id'][execution_id] = len(clients)

        # 详细连接信息
        for ws, metadata in self.connection_metadata.items():
            last_heartbeat = metadata.get('last_heartbeat')
            idle_seconds = (now - last_heartbeat).total_seconds() if last_heartbeat else None

            stats['connection_details'].append({
                'execution_id': metadata.get('execution_id'),
                'connected_duration_seconds': (now - metadata['connected_at']).total_seconds(),
                'message_count': metadata.get('message_count', 0),
                'bytes_sent': metadata.get('bytes_sent', 0),
                'bytes_received': metadata.get('bytes_received', 0),
                'idle_seconds': idle_seconds,
                'is_healthy': idle_seconds is None or idle_seconds < WS_CONFIG['ping_timeout']
            })

        return stats


# 全局 WebSocket 服务实例
websocket_service = WebSocketService()


# WebSocket 服务器处理器
async def websocket_handler(
    websocket: websockets.WebSocketServerProtocol,
    path: str
) -> None:
    """
    WebSocket 连接处理器（增强版）

    优化点：
    1. 使用新的 handle_client_message 方法处理消息
    2. 启动健康检查任务
    3. 更完善的错误处理
    4. 连接统计记录

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
        api_logger.warning("websocket_invalid_path", extra={
            'event': 'websocket_invalid_path',
            'path': path,
            'timestamp': datetime.now().isoformat()
        })
        await websocket.close(1008, 'Invalid path')
        return

    # 注册客户端
    await websocket_service.register(execution_id, websocket)

    # 启动健康检查（如果还没有启动）
    await websocket_service.start_health_check()

    start_time = datetime.now()
    message_count = 0

    try:
        # 保持连接，接收客户端消息（心跳等）
        async for message in websocket:
            message_count += 1

            # 使用新方法处理客户端消息
            response = await websocket_service.handle_client_message(websocket, message)

            # 如果有响应，发送回客户端
            if response:
                await websocket.send(json.dumps(response))

    except websockets.exceptions.ConnectionClosed as e:
        # 客户端正常断开
        duration = (datetime.now() - start_time).total_seconds()
        api_logger.info("websocket_connection_closed", extra={
            'event': 'websocket_connection_closed',
            'execution_id': execution_id,
            'duration_seconds': duration,
            'message_count': message_count,
            'close_code': e.code,
            'close_reason': e.reason,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        api_logger.error("websocket_handler_error", extra={
            'event': 'websocket_handler_error',
            'error': str(e),
            'execution_id': execution_id,
            'message_count': message_count,
            'timestamp': datetime.now().isoformat()
        })
    finally:
        # 注销客户端
        await websocket_service.unregister(execution_id, websocket)

        # 记录连接统计
        duration = (datetime.now() - start_time).total_seconds()
        api_logger.info("websocket_session_ended", extra={
            'event': 'websocket_session_ended',
            'execution_id': execution_id,
            'duration_seconds': duration,
            'message_count': message_count,
            'timestamp': datetime.now().isoformat()
        })


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
