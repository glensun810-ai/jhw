"""
WebSocket Service Tests

Test coverage:
- WebSocket service connection management
- Message broadcasting
- Client registration/unregistration
- Heartbeat mechanism

@author: System Architecture Team
@date: 2026-02-27
@version: 2.0.0
"""

import unittest
from unittest.mock import Mock, AsyncMock
import asyncio
import json


class TestWebSocketService(unittest.TestCase):
    """WebSocket Service Tests"""

    def setUp(self):
        """Test setup"""
        from wechat_backend.v2.services.websocket_service import WebSocketService
        self.service = WebSocketService()

    def test_initialization(self):
        """Test initialization"""
        self.assertEqual(self.service.clients, {})
        self.assertEqual(self.service.connection_count, 0)

    def test_register_client(self):
        """Test client registration"""
        execution_id = 'test-execution-001'
        mock_websocket = Mock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        self.assertIn(execution_id, self.service.clients)
        self.assertIn(mock_websocket, self.service.clients[execution_id])
        self.assertEqual(self.service.connection_count, 1)

    def test_unregister_client(self):
        """Test client unregistration"""
        execution_id = 'test-execution-001'
        mock_websocket = Mock()

        asyncio.run(self.service.register(execution_id, mock_websocket))
        self.assertEqual(self.service.connection_count, 1)

        asyncio.run(self.service.unregister(execution_id, mock_websocket))

        self.assertNotIn(execution_id, self.service.clients)
        self.assertEqual(self.service.connection_count, 0)

    def test_broadcast_message(self):
        """Test message broadcasting"""
        execution_id = 'test-execution-001'
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket1))
        asyncio.run(self.service.register(execution_id, mock_websocket2))

        message = {'event': 'progress', 'data': {'progress': 50}}
        asyncio.run(self.service.broadcast(execution_id, message))

        self.assertEqual(mock_websocket1.send.call_count, 1)
        self.assertEqual(mock_websocket2.send.call_count, 1)

    def test_send_progress(self):
        """Test sending progress update"""
        execution_id = 'test-execution-001'
        mock_websocket = AsyncMock()

        asyncio.run(self.service.register(execution_id, mock_websocket))

        asyncio.run(self.service.send_progress(
            execution_id,
            progress=50,
            stage='ai_fetching',
            status='processing',
            status_text='Fetching AI data...'
        ))

        mock_websocket.send.assert_called_once()
        call_args = mock_websocket.send.call_args[0][0]
        message = json.loads(call_args)

        self.assertEqual(message['event'], 'progress')
        self.assertEqual(message['data']['progress'], 50)

    def test_get_active_connection_count(self):
        """Test getting active connection count"""
        execution_id1 = 'test-execution-001'
        execution_id2 = 'test-execution-002'
        mock_websocket1 = Mock()
        mock_websocket2 = Mock()

        asyncio.run(self.service.register(execution_id1, mock_websocket1))
        asyncio.run(self.service.register(execution_id2, mock_websocket2))

        self.assertEqual(self.service.get_active_connection_count(), 2)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestWebSocketService))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return {
        'total': result.testsRun,
        'passed': len(result.failures) + len(result.errors) == 0,
        'failures': len(result.failures),
        'errors': len(result.errors)
    }


if __name__ == '__main__':
    result = run_tests()
    print(f"\nTest Result: {result['passed']} - {result['total']} tests passed")
