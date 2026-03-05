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
import zlib
from typing import Dict, Set, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
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
    
    # 【P2 性能优化 - 2026-03-09】连接池配置
    'max_connections': 1000,  # 最大连接数
    'idle_timeout': 300,  # 空闲超时（秒）
    'connection_pool_size': 100,  # 连接池大小
    
    # 【P2 性能优化 - 2026-03-09】消息压缩配置
    'enable_compression': True,  # 启用消息压缩
    'compression_threshold': 1024,  # 压缩阈值（字节），大于此值才压缩
    'compression_level': 6,  # 压缩级别（1-9），6 为平衡点
}


class WebSocketService:
    """
    WebSocket 服务（P2 性能优化版）

    管理客户端连接和消息推送
    
    优化特性：
    1. 连接池管理 - 复用连接，减少创建开销
    2. 消息压缩 - 减少网络传输量
    3. LRU 缓存 - 快速访问热点连接
    4. 性能监控 - 实时统计指标
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
        
        # 【P2 性能优化 - 2026-03-09】连接池管理
        # LRU 连接池：用于复用频繁访问的连接
        self._connection_pool: OrderedDict = OrderedDict()
        self._pool_lock = asyncio.Lock()
        
        # 【P2 性能优化 - 2026-03-09】性能监控指标
        self._metrics = {
            'connections_total': 0,
            'connections_active': 0,
            'connections_peak': 0,
            'messages_sent': 0,
            'messages_failed': 0,
            'bytes_sent_original': 0,
            'bytes_sent_compressed': 0,
            'compression_ratio': 0.0,
            'avg_latency_ms': 0.0,
            'last_updated': datetime.now()
        }
        self._metrics_lock = asyncio.Lock()
        
        # 【P2 性能优化 - 2026-03-09】延迟统计（用于计算平均延迟）
        self._latency_samples = []
        self._max_latency_samples = 1000

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
        定期检查所有连接的健康状态，清理僵尸连接和空闲连接
        """
        while True:
            try:
                await asyncio.sleep(30)  # 每 30 秒检查一次
                await self._check_connections_health()
                # 【P2 性能优化 - 2026-03-09】清理空闲连接
                await self._cleanup_idle_connections()
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

    # ========================================================================
    # 【P2 性能优化 - 2026-03-09】连接池管理
    # ========================================================================
    
    async def _get_connection_from_pool(self, execution_id: str) -> Optional[websockets.WebSocketServerProtocol]:
        """
        从连接池获取连接（LRU 策略）
        
        参数:
            execution_id: 诊断执行 ID
            
        返回:
            WebSocket 连接对象，如果池中无连接则返回 None
        """
        async with self._pool_lock:
            pool_key = f"pool:{execution_id}"
            if pool_key in self._connection_pool:
                # 移动到末尾（最近使用）
                self._connection_pool.move_to_end(pool_key)
                websocket = self._connection_pool[pool_key]
                
                # 验证连接是否仍然有效
                if websocket.open:
                    self.logger.debug(f"websocket_connection_pool_hit", extra={
                        'event': 'websocket_connection_pool_hit',
                        'execution_id': execution_id,
                        'timestamp': datetime.now().isoformat()
                    })
                    return websocket
                else:
                    # 连接已关闭，从池中移除
                    del self._connection_pool[pool_key]
                    self.logger.debug(f"websocket_connection_pool_stale", extra={
                        'event': 'websocket_connection_pool_stale',
                        'execution_id': execution_id,
                        'timestamp': datetime.now().isoformat()
                    })
            
            return None
    
    async def _return_connection_to_pool(self, execution_id: str, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        将连接返回到连接池
        
        参数:
            execution_id: 诊断执行 ID
            websocket: WebSocket 连接对象
        """
        async with self._pool_lock:
            pool_key = f"pool:{execution_id}"
            
            # 如果池已满，移除最旧的连接
            if len(self._connection_pool) >= WS_CONFIG['connection_pool_size']:
                # 移除第一个（最旧的）连接
                oldest_key = next(iter(self._connection_pool))
                oldest_ws = self._connection_pool.pop(oldest_key)
                try:
                    await oldest_ws.close(1000, 'Pool eviction')
                except Exception:
                    pass
            
            # 添加到池中
            self._connection_pool[pool_key] = websocket
            
            self.logger.debug(f"websocket_connection_returned_to_pool", extra={
                'event': 'websocket_connection_returned_to_pool',
                'execution_id': execution_id,
                'pool_size': len(self._connection_pool),
                'timestamp': datetime.now().isoformat()
            })
    
    async def _cleanup_idle_connections(self) -> int:
        """
        清理空闲连接
        
        返回:
            清理的连接数
        """
        now = datetime.now()
        cleaned_count = 0
        
        async with self._pool_lock:
            to_remove = []
            
            # 查找空闲超时的连接
            for pool_key, websocket in self._connection_pool.items():
                metadata = self.connection_metadata.get(websocket)
                if metadata:
                    idle_time = (now - metadata.get('last_heartbeat', now)).total_seconds()
                    if idle_time > WS_CONFIG['idle_timeout']:
                        to_remove.append(pool_key)
            
            # 清理空闲连接
            for pool_key in to_remove:
                websocket = self._connection_pool.pop(pool_key)
                try:
                    await websocket.close(1001, 'Idle timeout')
                except Exception:
                    pass
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"websocket_idle_connections_cleaned", extra={
                'event': 'websocket_idle_connections_cleaned',
                'count': cleaned_count,
                'timestamp': datetime.now().isoformat()
            })
        
        return cleaned_count

    # ========================================================================
    # 【P2 性能优化 - 2026-03-09】消息压缩
    # ========================================================================
    
    def _compress_message(self, message: str) -> Tuple[bytes, bool]:
        """
        压缩消息
        
        参数:
            message: 原始消息字符串
            
        返回:
            (压缩后的字节，是否压缩)
        """
        if not WS_CONFIG['enable_compression']:
            return message.encode('utf-8'), False
        
        message_bytes = message.encode('utf-8')
        
        # 如果消息太小，不压缩
        if len(message_bytes) < WS_CONFIG['compression_threshold']:
            return message_bytes, False
        
        try:
            # 使用 zlib 压缩
            compressed = zlib.compress(
                message_bytes,
                level=WS_CONFIG['compression_level']
            )
            
            # 如果压缩后没有显著减小，使用原始消息
            if len(compressed) >= len(message_bytes) * 0.9:
                return message_bytes, False
            
            return compressed, True
            
        except Exception as e:
            self.logger.warning(f"websocket_compression_failed: {e}")
            return message_bytes, False
    
    def _decompress_message(self, data: bytes, is_compressed: bool) -> str:
        """
        解压消息
        
        参数:
            data: 消息字节
            is_compressed: 是否已压缩
            
        返回:
            解压后的字符串
        """
        if not is_compressed:
            return data.decode('utf-8')
        
        try:
            decompressed = zlib.decompress(data)
            return decompressed.decode('utf-8')
        except Exception as e:
            self.logger.error(f"websocket_decompression_failed: {e}")
            # 尝试直接解码
            try:
                return data.decode('utf-8')
            except:
                return ""

    # ========================================================================
    # 【P2 性能优化 - 2026-03-09】性能监控
    # ========================================================================
    
    async def _update_metrics(
        self,
        messages_sent: int = 0,
        messages_failed: int = 0,
        bytes_original: int = 0,
        bytes_compressed: int = 0,
        latency_ms: float = 0.0
    ) -> None:
        """
        更新性能指标
        
        参数:
            messages_sent: 发送成功消息数
            messages_failed: 发送失败消息数
            bytes_original: 原始字节数
            bytes_compressed: 压缩后字节数
            latency_ms: 延迟（毫秒）
        """
        async with self._metrics_lock:
            self._metrics['messages_sent'] += messages_sent
            self._metrics['messages_failed'] += messages_failed
            self._metrics['bytes_sent_original'] += bytes_original
            self._metrics['bytes_sent_compressed'] += bytes_compressed
            
            # 计算压缩比
            if bytes_original > 0:
                self._metrics['compression_ratio'] = (
                    (bytes_original - bytes_compressed) / bytes_original * 100
                )
            
            # 更新平均延迟
            if latency_ms > 0:
                self._latency_samples.append(latency_ms)
                if len(self._latency_samples) > self._max_latency_samples:
                    self._latency_samples.pop(0)
                
                if self._latency_samples:
                    self._metrics['avg_latency_ms'] = (
                        sum(self._latency_samples) / len(self._latency_samples)
                    )
            
            self._metrics['last_updated'] = datetime.now()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        返回:
            性能指标字典
        """
        async with self._metrics_lock:
            metrics = self._metrics.copy()
            metrics['connections_active'] = self.connection_count
            metrics['pool_size'] = len(self._connection_pool)
            
            # 更新峰值连接数
            if self.connection_count > metrics['connections_peak']:
                metrics['connections_peak'] = self.connection_count
            
            return metrics

    async def broadcast(
        self,
        execution_id: str,
        message: Dict[str, Any]
    ) -> None:
        """
        广播消息给所有订阅该 execution_id 的客户端（支持压缩）

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
        original_bytes = len(message_json.encode('utf-8'))
        
        # 【P2 性能优化 - 2026-03-09】消息压缩
        compressed_data, is_compressed = self._compress_message(message_json)
        compressed_bytes = len(compressed_data)
        
        # 记录压缩统计
        if is_compressed:
            self.logger.debug(f"websocket_message_compressed", extra={
                'event': 'websocket_message_compressed',
                'execution_id': execution_id,
                'original_bytes': original_bytes,
                'compressed_bytes': compressed_bytes,
                'compression_ratio': (original_bytes - compressed_bytes) / original_bytes * 100,
                'timestamp': datetime.now().isoformat()
            })

        # 异步发送给所有客户端
        send_start = datetime.now()
        results = await asyncio.gather(
            *[self._send_to_client_compressed(client, compressed_data, is_compressed)
              for client in self.clients[execution_id]],
            return_exceptions=True
        )
        send_end = datetime.now()
        
        # 计算延迟
        latency_ms = (send_end - send_start).total_seconds() * 1000
        
        # 统计发送结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failed_count = len(results) - success_count
        
        # 【P2 性能优化 - 2026-03-09】更新性能指标
        await self._update_metrics(
            messages_sent=success_count,
            messages_failed=failed_count,
            bytes_original=original_bytes * len(self.clients[execution_id]),
            bytes_compressed=compressed_bytes * success_count,
            latency_ms=latency_ms
        )

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

    async def _send_to_client_compressed(
        self,
        client: websockets.WebSocketServerProtocol,
        data: bytes,
        is_compressed: bool
    ) -> None:
        """
        发送给单个客户端（支持压缩）

        参数:
            client: WebSocket 连接对象
            data: 消息字节（可能已压缩）
            is_compressed: 是否已压缩
        """
        try:
            # WebSocket 自动处理二进制消息
            if is_compressed:
                # 添加压缩标记
                header = bytes([1]) + data
                await client.send(header)
            else:
                await client.send(data)

            # 更新统计
            if client in self.connection_metadata:
                self.connection_metadata[client]['bytes_sent'] += len(data)
                self.connection_metadata[client]['message_count'] += 1
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
