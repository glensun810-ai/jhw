"""
实时推送服务（统一 WebSocket 和 SSE）

设计理念：
1. 微信小程序使用 WebSocket（原生支持，双向通信）
2. Web 管理后台使用 SSE（简单，单向推送）
3. 统一的推送接口，上层代码无需关心底层实现

架构参考：
- Google Cloud Run: 任务启动后立即推送状态
- AWS Lambda: 事件驱动的实时通知
- 微信服务器：模板消息 + WebSocket 组合推送

@author: 系统架构组
@date: 2026-03-02
@version: 3.0.0 (颠覆性重构版)
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
from wechat_backend.logging_config import api_logger


class RealtimePushService:
    """
    实时推送服务
    
    功能：
    1. WebSocket 推送（微信小程序）
    2. SSE 推送（Web 管理后台，向后兼容）
    3. 微信模板消息（关键阶段通知）
    """
    
    def __init__(self):
        """初始化推送服务"""
        self._ws_service = None
        self._sse_manager = None
        self._wechat_notifier = None
        
    def _get_websocket_service(self):
        """懒加载 WebSocket 服务"""
        if self._ws_service is None:
            try:
                from wechat_backend.v2.services.websocket_service import get_websocket_service
                self._ws_service = get_websocket_service()
            except ImportError:
                api_logger.warning("[RealtimePush] WebSocket 服务不可用")
                self._ws_service = None
        return self._ws_service
    
    def _get_sse_manager(self):
        """懒加载 SSE 管理器（向后兼容）"""
        if self._sse_manager is None:
            try:
                from wechat_backend.services.sse_service import get_sse_manager
                self._sse_manager = get_sse_manager()
            except ImportError:
                api_logger.debug("[RealtimePush] SSE 管理器不可用")
                self._sse_manager = None
        return self._sse_manager
    
    def _get_wechat_notifier(self):
        """懒加载微信通知器"""
        if self._wechat_notifier is None:
            try:
                from wechat_backend.services.wechat_template_message import get_wechat_notifier
                self._wechat_notifier = get_wechat_notifier()
            except ImportError:
                api_logger.debug("[RealtimePush] 微信通知器不可用")
                self._wechat_notifier = None
        return self._wechat_notifier
    
    async def send_progress(
        self,
        execution_id: str,
        progress: int,
        stage: str,
        status: str,
        status_text: str = "",
        user_openid: Optional[str] = None
    ) -> None:
        """
        发送进度更新
        
        参数：
            execution_id: 执行 ID
            progress: 进度百分比 (0-100)
            stage: 阶段 (initializing, ai_fetching, analyzing, completed, failed)
            status: 状态 (running, success, failed)
            status_text: 状态文本描述
            user_openid: 用户 OpenID（用于微信通知，可选）
        """
        message = {
            'progress': progress,
            'stage': stage,
            'status': status,
            'status_text': status_text,
            'timestamp': datetime.now().isoformat()
        }
        
        # 1. WebSocket 推送（微信小程序）
        ws_service = self._get_websocket_service()
        if ws_service:
            try:
                await ws_service.send_progress(
                    execution_id=execution_id,
                    progress=progress,
                    stage=stage,
                    status=status,
                    status_text=status_text
                )
                api_logger.debug(f"[RealtimePush] ✅ WebSocket 推送：{execution_id}, {progress}%")
            except Exception as e:
                api_logger.warning(f"[RealtimePush] ⚠️ WebSocket 推送失败：{e}")
        
        # 2. SSE 推送（Web 管理后台，向后兼容）
        sse_manager = self._get_sse_manager()
        if sse_manager:
            try:
                sse_manager.broadcast(
                    execution_id=execution_id,
                    event_type='progress',
                    data=message
                )
                api_logger.debug(f"[RealtimePush] ✅ SSE 推送：{execution_id}, {progress}%")
            except Exception as e:
                api_logger.debug(f"[RealtimePush] ⚠️ SSE 推送失败：{e}")
        
        # 3. 微信模板消息（关键阶段）
        if user_openid and self._should_send_wechat_notification(stage, progress):
            wechat_notifier = self._get_wechat_notifier()
            if wechat_notifier:
                try:
                    await wechat_notifier.send_progress_notification(
                        openid=user_openid,
                        execution_id=execution_id,
                        progress=progress,
                        stage=stage,
                        status_text=status_text
                    )
                    api_logger.info(f"[RealtimePush] ✅ 微信通知：{execution_id}, {progress}%")
                except Exception as e:
                    api_logger.warning(f"[RealtimePush] ⚠️ 微信通知失败：{e}")
    
    def _should_send_wechat_notification(self, stage: str, progress: int) -> bool:
        """
        判断是否发送微信通知（避免频繁打扰用户）
        
        策略：
        1. 任务启动时（progress=0）
        2. AI 调用完成时（progress=50）
        3. 任务完成时（progress=100）
        4. 任务失败时（stage=failed）
        """
        if stage == 'failed':
            return True
        if progress in [0, 50, 100]:
            return True
        return False
    
    async def send_complete(
        self,
        execution_id: str,
        result: Dict[str, Any],
        user_openid: Optional[str] = None
    ) -> None:
        """
        发送完成通知
        
        参数：
            execution_id: 执行 ID
            result: 结果数据
            user_openid: 用户 OpenID（用于微信通知）
        """
        message = {
            'progress': 100,
            'stage': 'completed',
            'status': 'success',
            'status_text': '诊断完成',
            'results_count': len(result.get('results', [])),
            'timestamp': datetime.now().isoformat()
        }
        
        # 1. WebSocket 推送
        ws_service = self._get_websocket_service()
        if ws_service:
            try:
                await ws_service.send_complete(
                    execution_id=execution_id,
                    final_report=message
                )
                api_logger.info(f"[RealtimePush] ✅ WebSocket 完成：{execution_id}")
            except Exception as e:
                api_logger.warning(f"[RealtimePush] ⚠️ WebSocket 完成推送失败：{e}")
        
        # 2. SSE 推送（向后兼容）
        sse_manager = self._get_sse_manager()
        if sse_manager:
            try:
                sse_manager.broadcast(
                    execution_id=execution_id,
                    event_type='complete',
                    data=message
                )
                api_logger.debug(f"[RealtimePush] ✅ SSE 完成：{execution_id}")
            except Exception as e:
                api_logger.debug(f"[RealtimePush] ⚠️ SSE 完成推送失败：{e}")
        
        # 3. 微信完成通知
        if user_openid:
            wechat_notifier = self._get_wechat_notifier()
            if wechat_notifier:
                try:
                    await wechat_notifier.send_complete_notification(
                        openid=user_openid,
                        execution_id=execution_id,
                        result_summary=f"完成 {len(result.get('results', []))} 个维度分析"
                    )
                    api_logger.info(f"[RealtimePush] ✅ 微信完成通知：{execution_id}")
                except Exception as e:
                    api_logger.warning(f"[RealtimePush] ⚠️ 微信完成通知失败：{e}")
    
    async def send_error(
        self,
        execution_id: str,
        error: str,
        error_type: str = 'unknown',
        error_details: Optional[Dict[str, Any]] = None,
        user_openid: Optional[str] = None
    ) -> None:
        """
        发送错误通知
        
        参数：
            execution_id: 执行 ID
            error: 错误消息
            error_type: 错误类型
            error_details: 详细错误信息
            user_openid: 用户 OpenID（用于微信通知）
        """
        message = {
            'error': error,
            'error_type': error_type,
            'error_details': error_details or {},
            'timestamp': datetime.now().isoformat()
        }
        
        # 1. WebSocket 推送
        ws_service = self._get_websocket_service()
        if ws_service:
            try:
                await ws_service.send_error(
                    execution_id=execution_id,
                    error=error,
                    error_type=error_type,
                    error_details=error_details
                )
                api_logger.warning(f"[RealtimePush] ✅ WebSocket 错误：{execution_id}, {error_type}")
            except Exception as e:
                api_logger.warning(f"[RealtimePush] ⚠️ WebSocket 错误推送失败：{e}")
        
        # 2. SSE 推送（向后兼容）
        sse_manager = self._get_sse_manager()
        if sse_manager:
            try:
                sse_manager.broadcast(
                    execution_id=execution_id,
                    event_type='error',
                    data=message
                )
                api_logger.debug(f"[RealtimePush] ✅ SSE 错误：{execution_id}, {error_type}")
            except Exception as e:
                api_logger.debug(f"[RealtimePush] ⚠️ SSE 错误推送失败：{e}")
        
        # 3. 微信错误通知
        if user_openid:
            wechat_notifier = self._get_wechat_notifier()
            if wechat_notifier:
                try:
                    await wechat_notifier.send_error_notification(
                        openid=user_openid,
                        execution_id=execution_id,
                        error_message=error
                    )
                    api_logger.info(f"[RealtimePush] ✅ 微信错误通知：{execution_id}")
                except Exception as e:
                    api_logger.warning(f"[RealtimePush] ⚠️ 微信错误通知失败：{e}")
    
    async def send_result_chunk(
        self,
        execution_id: str,
        chunk: Dict[str, Any]
    ) -> None:
        """
        发送结果分块（流式聚合）
        
        参数：
            execution_id: 执行 ID
            chunk: 结果分块数据
        """
        # 仅 WebSocket 和 SSE 支持
        ws_service = self._get_websocket_service()
        if ws_service:
            try:
                await ws_service.send_result(
                    execution_id=execution_id,
                    result=chunk
                )
            except Exception as e:
                api_logger.debug(f"[RealtimePush] ⚠️ WebSocket 分块推送失败：{e}")
        
        sse_manager = self._get_sse_manager()
        if sse_manager:
            try:
                sse_manager.broadcast(
                    execution_id=execution_id,
                    event_type='result_chunk',
                    data=chunk
                )
            except Exception as e:
                api_logger.debug(f"[RealtimePush] ⚠️ SSE 分块推送失败：{e}")


# 全局服务实例
_realtime_push_service: Optional[RealtimePushService] = None


def get_realtime_push_service() -> RealtimePushService:
    """获取全局实时推送服务实例"""
    global _realtime_push_service
    if _realtime_push_service is None:
        _realtime_push_service = RealtimePushService()
    return _realtime_push_service


# 便捷函数（同步版本，用于不支持 async 的代码）
def send_progress_sync(
    execution_id: str,
    progress: int,
    stage: str,
    status: str,
    status_text: str = "",
    user_openid: Optional[str] = None
) -> None:
    """同步版本的进度推送（用于兼容旧代码）"""
    service = get_realtime_push_service()
    try:
        # 【P0-WebSocket 修复】在异步线程中创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(service.send_progress(
                execution_id=execution_id,
                progress=progress,
                stage=stage,
                status=status,
                status_text=status_text,
                user_openid=user_openid
            ))
        finally:
            loop.close()
    except Exception as e:
        api_logger.warning(f"[RealtimePush] 同步推送失败：{e}")


def send_complete_sync(
    execution_id: str,
    result: Dict[str, Any],
    user_openid: Optional[str] = None
) -> None:
    """同步版本的完成推送"""
    service = get_realtime_push_service()
    try:
        # 【P0-WebSocket 修复】在异步线程中创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(service.send_complete(
                execution_id=execution_id,
                result=result,
                user_openid=user_openid
            ))
        finally:
            loop.close()
    except Exception as e:
        api_logger.warning(f"[RealtimePush] 同步完成推送失败：{e}")


def send_error_sync(
    execution_id: str,
    error: str,
    error_type: str = 'unknown',
    error_details: Optional[Dict[str, Any]] = None,
    user_openid: Optional[str] = None
) -> None:
    """同步版本的错误推送"""
    service = get_realtime_push_service()
    try:
        # 【P0-WebSocket 修复】在异步线程中创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(service.send_error(
                execution_id=execution_id,
                error=error,
                error_type=error_type,
                error_details=error_details,
                user_openid=user_openid
            ))
        finally:
            loop.close()
    except Exception as e:
        api_logger.warning(f"[RealtimePush] 同步错误推送失败：{e}")
