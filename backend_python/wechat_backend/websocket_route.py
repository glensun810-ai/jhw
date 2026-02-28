"""
WebSocket 路由模块

P1-3 修复：WebSocket 实时推送前端集成

功能：
- WebSocket 连接端点
- 诊断进度推送
- 连接管理集成

@author: 系统架构组
@date: 2026-02-28
"""

import asyncio
import json
from datetime import datetime
from wechat_backend.v2.services.websocket_service import get_websocket_service
from wechat_backend.logging_config import api_logger


# WebSocket 路由配置
WS_ROUTE = '/ws'


async def handle_websocket_connection(websocket, path=None):
    """
    处理 WebSocket 连接
    
    参数：
        websocket: WebSocket 连接对象
        path: 连接路径
    """
    execution_id = None
    
    try:
        # 等待客户端发送认证消息
        auth_message = await websocket.recv()
        auth_data = json.loads(auth_message)
        
        execution_id = auth_data.get('executionId')
        client_type = auth_data.get('type', 'client')
        
        if not execution_id:
            api_logger.warning(f"[WebSocket] 连接拒绝：缺少 executionId")
            await websocket.send(json.dumps({
                'type': 'error',
                'error': 'Missing executionId'
            }))
            await websocket.close()
            return
        
        # 注册连接
        ws_service = get_websocket_service()
        await ws_service.register_connection(websocket, execution_id)
        
        api_logger.info(
            f"[WebSocket] 新连接：{execution_id}, 类型={client_type}"
        )
        
        # 发送连接确认
        await websocket.send(json.dumps({
            'type': 'connected',
            'executionId': execution_id,
            'timestamp': datetime.now().isoformat()
        }))
        
        # 保持连接活跃，接收客户端心跳
        async for message in websocket:
            try:
                data = json.loads(message)
                
                # 处理心跳
                if data.get('type') == 'heartbeat':
                    await websocket.send(json.dumps({
                        'type': 'heartbeat_ack',
                        'timestamp': datetime.now().isoformat()
                    }))
                
                # 处理确认消息
                elif data.get('type') == 'ack':
                    # 客户端确认收到消息
                    msg_id = data.get('messageId')
                    if msg_id:
                        api_logger.debug(
                            f"[WebSocket] 消息确认：{msg_id}"
                        )
                
            except json.JSONDecodeError:
                api_logger.warning(f"[WebSocket] 无效消息格式")
            except Exception as e:
                api_logger.error(f"[WebSocket] 消息处理错误：{e}")
    
    except websockets.exceptions.ConnectionClosed:
        api_logger.info(f"[WebSocket] 连接关闭：{execution_id}")
    except Exception as e:
        api_logger.error(f"[WebSocket] 连接错误：{e}")
    finally:
        # 清理连接
        if execution_id:
            ws_service = get_websocket_service()
            await ws_service.unregister_connection(websocket, execution_id)
            api_logger.info(f"[WebSocket] 连接清理：{execution_id}")


def send_diagnosis_progress(execution_id: str, progress_data: dict):
    """
    发送诊断进度推送
    
    参数：
        execution_id: 执行 ID
        progress_data: 进度数据
    """
    ws_service = get_websocket_service()
    
    message = {
        'type': 'progress',
        'executionId': execution_id,
        'data': progress_data,
        'timestamp': datetime.now().isoformat()
    }
    
    asyncio.create_task(ws_service.broadcast_to_execution(
        execution_id=execution_id,
        message=message
    ))
    
    api_logger.debug(
        f"[WebSocket] 推送进度：{execution_id}, "
        f"progress={progress_data.get('progress')}%"
    )


def send_diagnosis_result(execution_id: str, result_data: dict):
    """
    发送诊断结果推送
    
    参数：
        execution_id: 执行 ID
        result_data: 结果数据
    """
    ws_service = get_websocket_service()
    
    message = {
        'type': 'result',
        'executionId': execution_id,
        'data': result_data,
        'timestamp': datetime.now().isoformat()
    }
    
    asyncio.create_task(ws_service.broadcast_to_execution(
        execution_id=execution_id,
        message=message
    ))
    
    api_logger.debug(f"[WebSocket] 推送结果：{execution_id}")


def send_diagnosis_complete(execution_id: str, complete_data: dict):
    """
    发送诊断完成推送
    
    参数：
        execution_id: 执行 ID
        complete_data: 完成数据
    """
    ws_service = get_websocket_service()
    
    message = {
        'type': 'complete',
        'executionId': execution_id,
        'data': complete_data,
        'timestamp': datetime.now().isoformat()
    }
    
    asyncio.create_task(ws_service.broadcast_to_execution(
        execution_id=execution_id,
        message=message
    ))
    
    api_logger.info(f"[WebSocket] 推送完成：{execution_id}")


def send_diagnosis_error(execution_id: str, error_data: dict):
    """
    发送诊断错误推送
    
    参数：
        execution_id: 执行 ID
        error_data: 错误数据
    """
    ws_service = get_websocket_service()
    
    message = {
        'type': 'error',
        'executionId': execution_id,
        'data': error_data,
        'timestamp': datetime.now().isoformat()
    }
    
    asyncio.create_task(ws_service.broadcast_to_execution(
        execution_id=execution_id,
        message=message
    ))
    
    api_logger.warning(f"[WebSocket] 推送错误：{execution_id}, {error_data.get('message')}")


# 便捷函数：与 SSE 集成
def send_progress_update(execution_id: str, progress_data: dict):
    """
    发送进度更新（兼容 SSE 和 WebSocket）
    
    参数：
        execution_id: 执行 ID
        progress_data: 进度数据
    """
    # WebSocket 推送
    send_diagnosis_progress(execution_id, progress_data)
    
    # SSE 推送（保持向后兼容）
    try:
        from wechat_backend.services.sse_service import get_sse_manager
        sse_manager = get_sse_manager()
        sse_manager.broadcast(
            execution_id=execution_id,
            event_type='progress',
            data=progress_data
        )
    except Exception as e:
        api_logger.debug(f"[SSE] 推送失败：{e}")
