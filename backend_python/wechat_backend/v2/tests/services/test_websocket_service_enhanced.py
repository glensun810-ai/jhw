"""
WebSocket Service Enhanced Tests (稳定性增强版测试)

Test coverage:
1. Connection stability tests
2. Heartbeat mechanism tests
3. Health check tests
4. Reconnection strategy tests
5. Error handling tests
6. Statistics tracking tests
7. Performance tests

@author: System Architecture Team
@date: 2026-02-28
@version: 2.1.0
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import json
import time
from datetime import datetime, timedelta


class TestWebSocketServiceEnhanced(unittest.TestCase):
    """WebSocket Service Enhanced Tests"""

    def setUp(self):
        """Test setup"""
        from wechat_backend.v2.services.websocket_service import WebSocketService, WS_CONFIG
        self.service = WebSocketService()
        self.WS_CONFIG = WS_CONFIG

    def test_ws_config_values(self):
        """Test WebSocket configuration values are reasonable"""
        # 验证配置值在合理范围内
        self.assertGreater(self.WS_CONFIG['ping_interval'], 0)
        self.assertLess(self.WS_CONFIG['ping_interval'], 60)  # 不超过 60 秒
        
        self.assertGreater(self.WS_CONFIG['ping_timeout'], 0)
        self.assertLess(self.WS_CONFIG['ping_timeout'], self.WS_CONFIG['ping_interval'])
        
        self.assertGreater(self.WS_CONFIG['connect_timeout'], 0)
        self.assertGreater(self.WS_CONFIG['max_size'], 0)
        self.assertGreater(self.WS_CONFIG['max_queue'], 0)

    def test_connection_metadata_tracking(self):
        """Test connection metadata is properly tracked"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 验证元数据被记录
        self.assertIn(mock_websocket, self.service.connection_metadata)
        metadata = self.service.connection_metadata[mock_websocket]
        
        self.assertEqual(metadata['execution_id'], execution_id)
        self.assertIn('connected_at', metadata)
        self.assertIn('last_heartbeat', metadata)
        self.assertEqual(metadata['message_count'], 0)
        self.assertEqual(metadata['bytes_sent'], 0)
        self.assertEqual(metadata['bytes_received'], 0)

    def test_heartbeat_message_handling(self):
        """Test heartbeat message handling"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 发送心跳消息
        heartbeat_message = json.dumps({
            'type': 'heartbeat',
            'timestamp': datetime.now().isoformat()
        })

        response = asyncio.run(
            self.service.handle_client_message(mock_websocket, heartbeat_message)
        )

        # 验证响应
        self.assertIsNotNone(response)
        self.assertEqual(response['type'], 'heartbeat_ack')
        self.assertIn('timestamp', response)
        self.assertIn('server_time', response)

        # 验证元数据更新
        metadata = self.service.connection_metadata[mock_websocket]
        self.assertEqual(metadata['message_count'], 1)
        self.assertGreater(metadata['bytes_received'], 0)

    def test_ping_pong_handling(self):
        """Test ping/pong message handling"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 发送 ping 消息
        ping_message = json.dumps({
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        })

        response = asyncio.run(
            self.service.handle_client_message(mock_websocket, ping_message)
        )

        # 验证响应
        self.assertIsNotNone(response)
        self.assertEqual(response['type'], 'pong')

    def test_connection_ack_handling(self):
        """Test connection acknowledgment handling"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 发送连接确认消息
        ack_message = json.dumps({
            'type': 'connection_ack',
            'executionId': execution_id,
            'timestamp': datetime.now().isoformat()
        })

        response = asyncio.run(
            self.service.handle_client_message(mock_websocket, ack_message)
        )

        # 连接确认不应该有响应
        self.assertIsNone(response)

    def test_invalid_json_handling(self):
        """Test invalid JSON message handling"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 发送无效 JSON
        invalid_message = 'not valid json'

        response = asyncio.run(
            self.service.handle_client_message(mock_websocket, invalid_message)
        )

        # 应该返回 None 且不抛异常
        self.assertIsNone(response)

    def test_unknown_message_type(self):
        """Test unknown message type handling"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 发送未知类型消息
        unknown_message = json.dumps({
            'type': 'unknown_type',
            'data': 'test'
        })

        response = asyncio.run(
            self.service.handle_client_message(mock_websocket, unknown_message)
        )

        self.assertIsNone(response)

    def test_broadcast_with_statistics(self):
        """Test broadcasting with statistics tracking"""
        execution_id = 'test-execution-001'
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket1))
        asyncio.run(self.service.register(execution_id, mock_websocket2))

        # 广播消息
        message = {
            'event': 'progress',
            'data': {'progress': 50}
        }

        asyncio.run(self.service.broadcast(execution_id, message))

        # 验证两个客户端都收到消息
        self.assertEqual(mock_websocket1.send.call_count, 1)
        self.assertEqual(mock_websocket2.send.call_count, 1)

        # 验证统计更新
        metadata1 = self.service.connection_metadata[mock_websocket1]
        metadata2 = self.service.connection_metadata[mock_websocket2]
        
        self.assertGreater(metadata1['bytes_sent'], 0)
        self.assertGreater(metadata2['bytes_sent'], 0)

    def test_send_to_closed_client(self):
        """Test sending to closed client"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()
        
        # 模拟连接关闭异常
        from websockets.exceptions import ConnectionClosed
        mock_websocket.send.side_effect = ConnectionClosed(
            rcvd=None, sent=1000, reason='Client closed'
        )

        asyncio.run(self.service.register(execution_id, mock_websocket))

        message = {
            'event': 'progress',
            'data': {'progress': 50}
        }

        # 不应该抛异常
        asyncio.run(self.service.broadcast(execution_id, message))

        # 验证客户端被注销
        self.assertNotIn(execution_id, self.service.clients)

    def test_connection_statistics(self):
        """Test connection statistics tracking"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 获取统计信息
        stats = self.service.get_connection_statistics()

        self.assertIn('total_connections', stats)
        self.assertIn('by_execution_id', stats)
        self.assertIn('connection_details', stats)

        self.assertEqual(stats['total_connections'], 1)
        self.assertIn(execution_id, stats['by_execution_id'])
        self.assertEqual(len(stats['connection_details']), 1)

    def test_health_check_for_stale_connection(self):
        """Test health check detects stale connections"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 模拟长时间没有心跳
        stale_time = datetime.now() - timedelta(seconds=60)
        self.service.connection_metadata[mock_websocket]['last_heartbeat'] = stale_time

        # 运行健康检查
        asyncio.run(self.service._check_connections_health())

        # 验证僵尸连接被清理
        self.assertNotIn(execution_id, self.service.clients)
        self.assertNotIn(mock_websocket, self.service.connection_metadata)

    def test_health_check_for_healthy_connection(self):
        """Test health check keeps healthy connections"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 保持最近的心跳
        self.service.connection_metadata[mock_websocket]['last_heartbeat'] = datetime.now()

        # 运行健康检查
        asyncio.run(self.service._check_connections_health())

        # 验证健康连接保留
        self.assertIn(execution_id, self.service.clients)
        self.assertIn(mock_websocket, self.service.connection_metadata)

    def test_unregister_cleanup(self):
        """Test cleanup on unregister"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        # 模拟一些活动
        self.service.connection_metadata[mock_websocket]['message_count'] = 10
        self.service.connection_metadata[mock_websocket]['bytes_sent'] = 1024
        self.service.connection_metadata[mock_websocket]['bytes_received'] = 512

        # 注销
        asyncio.run(self.service.unregister(execution_id, mock_websocket))

        # 验证元数据被清理
        self.assertNotIn(mock_websocket, self.service.connection_metadata)
        self.assertNotIn(execution_id, self.service.clients)

    def test_broadcast_partial_failure(self):
        """Test broadcast with partial failure"""
        execution_id = 'test-execution-001'
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        # 模拟一个客户端失败
        mock_websocket2.send.side_effect = Exception('Send failed')

        asyncio.run(self.service.register(execution_id, mock_websocket1))
        asyncio.run(self.service.register(execution_id, mock_websocket2))

        message = {
            'event': 'progress',
            'data': {'progress': 50}
        }

        # 不应该抛异常
        asyncio.run(self.service.broadcast(execution_id, message))

        # 验证一个成功一个失败
        self.assertEqual(mock_websocket1.send.call_count, 1)
        self.assertEqual(mock_websocket2.send.call_count, 1)


class TestWebSocketHealthCheckLoop(unittest.TestCase):
    """WebSocket Health Check Loop Tests"""

    def setUp(self):
        """Test setup"""
        from wechat_backend.v2.services.websocket_service import WebSocketService
        self.service = WebSocketService()

    def test_start_health_check(self):
        """Test starting health check task"""
        # 启动健康检查
        asyncio.run(self.service.start_health_check())

        # 验证任务已创建
        self.assertIsNotNone(self.service._health_check_task)
        self.assertFalse(self.service._health_check_task.done())

        # 清理
        asyncio.run(self.service.stop_health_check())

    def test_stop_health_check(self):
        """Test stopping health check task"""
        # 启动后停止
        asyncio.run(self.service.start_health_check())
        asyncio.run(self.service.stop_health_check())

        # 验证任务已停止
        self.assertIsNone(self.service._health_check_task)

    def test_health_check_loop_cancellation(self):
        """Test health check loop handles cancellation"""
        async def test_loop():
            await self.service.start_health_check()
            await asyncio.sleep(0.1)
            await self.service.stop_health_check()

        asyncio.run(test_loop())


class TestWebSocketHandlerEnhanced(unittest.TestCase):
    """Enhanced WebSocket Handler Tests"""

    def test_handler_logs_connection_lifecycle(self):
        """Test handler logs connection lifecycle events"""
        from wechat_backend.v2.services.websocket_service import websocket_handler
        import websockets

        mock_websocket = AsyncMock()
        mock_websocket.__aiter__.return_value = []

        # 模拟有效路径
        with patch('wechat_backend.v2.services.websocket_service.websocket_service') as mock_service:
            mock_service.register = AsyncMock()
            mock_service.unregister = AsyncMock()

            asyncio.run(websocket_handler(mock_websocket, '/ws/diagnosis/test-123'))

            # 验证注册和注销被调用
            mock_service.register.assert_called_once()
            mock_service.unregister.assert_called_once()


class TestWebSocketPerformance(unittest.TestCase):
    """WebSocket Performance Tests"""

    def setUp(self):
        """Test setup"""
        from wechat_backend.v2.services.websocket_service import WebSocketService
        self.service = WebSocketService()

    def test_broadcast_performance(self):
        """Test broadcast performance with many clients"""
        execution_id = 'test-execution-001'
        num_clients = 100

        # 注册大量客户端
        mock_websockets = [AsyncMock() for _ in range(num_clients)]
        for ws in mock_websockets:
            asyncio.run(self.service.register(execution_id, ws))

        message = {
            'event': 'progress',
            'data': {'progress': 50}
        }

        # 测量广播时间
        start_time = time.time()
        asyncio.run(self.service.broadcast(execution_id, message))
        elapsed = time.time() - start_time

        # 验证性能（应该在 1 秒内完成）
        self.assertLess(elapsed, 1.0)

        # 验证所有客户端都收到消息
        for ws in mock_websockets:
            self.assertEqual(ws.send.call_count, 1)

    def test_connection_metadata_overhead(self):
        """Test connection metadata memory overhead"""
        num_connections = 1000

        # 注册大量连接
        for i in range(num_connections):
            mock_websocket = AsyncMock()
            execution_id = f'test-{i}'
            asyncio.run(self.service.register(execution_id, mock_websocket))

        # 验证元数据大小
        self.assertEqual(len(self.service.connection_metadata), num_connections)
        self.assertEqual(self.service.connection_count, num_connections)


def suite():
    """Create test suite"""
    suite = unittest.TestSuite()
    
    # Enhanced service tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        TestWebSocketServiceEnhanced
    ))
    
    # Health check tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        TestWebSocketHealthCheckLoop
    ))
    
    # Handler tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        TestWebSocketHandlerEnhanced
    ))
    
    # Performance tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        TestWebSocketPerformance
    ))
    
    return suite


if __name__ == '__main__':
    unittest.main()
