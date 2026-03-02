"""
微信模板消息服务

功能：
1. 诊断进度关键阶段通知
2. 诊断完成通知
3. 诊断失败通知

模板消息格式（参考微信官方文档）：
- 任务启动：{{keyword1}} - 诊断任务已启动
- 进度通知：{{keyword1}} - 进度 {{keyword2}}
- 完成通知：{{keyword1}} - 诊断已完成
- 失败通知：{{keyword1}} - 诊断失败

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from wechat_backend.logging_config import api_logger


class WechatTemplateNotifier:
    """
    微信模板消息通知器
    
    使用场景：
    1. 诊断任务启动（进度 0%）
    2. 诊断关键阶段（进度 50%）
    3. 诊断完成（进度 100%）
    4. 诊断失败
    
    频率控制：
    - 同一用户同一任务最多发送 3 条消息
    - 避免频繁打扰用户
    """
    
    # 模板 ID（需要在微信公众平台配置）
    TEMPLATE_IDS = {
        'progress': 'YOUR_PROGRESS_TEMPLATE_ID',  # 进度通知模板
        'complete': 'YOUR_COMPLETE_TEMPLATE_ID',  # 完成通知模板
        'error': 'YOUR_ERROR_TEMPLATE_ID'  # 错误通知模板
    }
    
    # 访问令牌缓存
    _access_token: Optional[str] = None
    _token_expires_at: int = 0
    
    def __init__(self, appid: str = None, secret: str = None):
        """
        初始化微信通知器
        
        参数：
            appid: 微信小程序 AppID
            secret: 微信小程序 Secret
        """
        from legacy_config import Config
        
        self.appid = appid or Config.APP_ID
        self.secret = secret or Config.APP_SECRET
        self._session = None
    
    async def _get_access_token(self) -> Optional[str]:
        """获取访问令牌（自动刷新）"""
        # 检查缓存
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        # 请求新令牌
        try:
            import aiohttp
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.appid}&secret={self.secret}"
            
            if self._session is None:
                self._session = aiohttp.ClientSession()
            
            async with self._session.get(url, timeout=10) as response:
                data = await response.json()
                
                if 'access_token' in data:
                    self._access_token = data['access_token']
                    # 提前 5 分钟刷新（微信默认 7200 秒过期）
                    self._token_expires_at = time.time() + (data.get('expires_in', 7200) - 300)
                    
                    api_logger.info(f"[WechatNotifier] ✅ 获取访问令牌成功")
                    return self._access_token
                else:
                    api_logger.error(f"[WechatNotifier] ❌ 获取访问令牌失败：{data}")
                    return None
                    
        except Exception as e:
            api_logger.error(f"[WechatNotifier] ❌ 获取访问令牌异常：{e}")
            return None
    
    async def send_progress_notification(
        self,
        openid: str,
        execution_id: str,
        progress: int,
        stage: str,
        status_text: str
    ) -> bool:
        """
        发送进度通知
        
        参数：
            openid: 用户 OpenID
            execution_id: 执行 ID
            progress: 进度百分比
            stage: 阶段
            status_text: 状态文本
            
        返回：
            bool: 是否发送成功
        """
        # 检查是否应该发送（避免频繁打扰）
        if not self._should_send_progress(progress):
            return False
        
        template_data = {
            "thing1": {"value": "诊断进度"},
            "thing2": {"value": f"{progress}% - {status_text}"},
            "thing3": {"value": stage},
            "thing4": {"value": execution_id[:8]}  # 显示短 ID
        }
        
        return await self._send_template_message(
            openid=openid,
            template_id=self.TEMPLATE_IDS['progress'],
            data=template_data,
            page="pages/diagnosis/diagnosis"  # 点击跳转到诊断页面
        )
    
    def _should_send_progress(self, progress: int) -> bool:
        """
        判断是否发送进度通知（避免频繁打扰）
        
        策略：只在关键进度点发送
        - 0%: 任务启动
        - 50%: AI 调用完成
        - 100%: 诊断完成
        """
        return progress in [0, 50, 100]
    
    async def send_complete_notification(
        self,
        openid: str,
        execution_id: str,
        result_summary: str
    ) -> bool:
        """
        发送完成通知
        
        参数：
            openid: 用户 OpenID
            execution_id: 执行 ID
            result_summary: 结果摘要
            
        返回：
            bool: 是否发送成功
        """
        template_data = {
            "thing1": {"value": "诊断完成"},
            "thing2": {"value": result_summary},
            "thing3": {"value": execution_id[:8]},
            "thing4": {"value": datetime.now().strftime("%Y-%m-%d %H:%M")}
        }
        
        return await self._send_template_message(
            openid=openid,
            template_id=self.TEMPLATE_IDS['complete'],
            data=template_data,
            page=f"pages/report/report?executionId={execution_id}"  # 点击跳转到报告页面
        )
    
    async def send_error_notification(
        self,
        openid: str,
        execution_id: str,
        error_message: str
    ) -> bool:
        """
        发送错误通知
        
        参数：
            openid: 用户 OpenID
            execution_id: 执行 ID
            error_message: 错误消息
            
        返回：
            bool: 是否发送成功
        """
        template_data = {
            "thing1": {"value": "诊断失败"},
            "thing2": {"value": error_message[:20] + "..." if len(error_message) > 20 else error_message},
            "thing3": {"value": execution_id[:8]},
            "thing4": {"value": "请重试"}
        }
        
        return await self._send_template_message(
            openid=openid,
            template_id=self.TEMPLATE_IDS['error'],
            data=template_data,
            page="pages/diagnosis/diagnosis"
        )
    
    async def _send_template_message(
        self,
        openid: str,
        template_id: str,
        data: Dict[str, Any],
        page: str = ""
    ) -> bool:
        """
        发送模板消息
        
        参数：
            openid: 用户 OpenID
            template_id: 模板 ID
            data: 模板数据
            page: 点击跳转页面
            
        返回：
            bool: 是否发送成功
        """
        try:
            import aiohttp
            
            access_token = await self._get_access_token()
            if not access_token:
                return False
            
            url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
            
            message = {
                "touser": openid,
                "template_id": template_id,
                "page": page,
                "miniprogram_state": "formal",  # formal-正式版 trial-体验版 developer-开发版
                "lang": "zh_CN",
                "data": data
            }
            
            if self._session is None:
                self._session = aiohttp.ClientSession()
            
            async with self._session.post(
                url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            ) as response:
                result = await response.json()
                
                if result.get('errcode', 0) == 0:
                    api_logger.info(f"[WechatNotifier] ✅ 模板消息发送成功：{openid}")
                    return True
                else:
                    api_logger.warning(f"[WechatNotifier] ⚠️ 模板消息发送失败：{result}")
                    return False
                    
        except Exception as e:
            api_logger.error(f"[WechatNotifier] ❌ 发送模板消息异常：{e}")
            return False
    
    async def close(self):
        """关闭会话"""
        if self._session:
            await self._session.close()
            self._session = None


# 全局实例
_wechat_notifier: Optional[WechatTemplateNotifier] = None


def get_wechat_notifier() -> WechatTemplateNotifier:
    """获取全局微信通知器实例"""
    global _wechat_notifier
    if _wechat_notifier is None:
        _wechat_notifier = WechatTemplateNotifier()
    return _wechat_notifier


# 便捷函数
async def send_progress_notification(
    openid: str,
    execution_id: str,
    progress: int,
    stage: str,
    status_text: str
) -> bool:
    """发送进度通知（便捷函数）"""
    notifier = get_wechat_notifier()
    return await notifier.send_progress_notification(
        openid=openid,
        execution_id=execution_id,
        progress=progress,
        stage=stage,
        status_text=status_text
    )


async def send_complete_notification(
    openid: str,
    execution_id: str,
    result_summary: str
) -> bool:
    """发送完成通知（便捷函数）"""
    notifier = get_wechat_notifier()
    return await notifier.send_complete_notification(
        openid=openid,
        execution_id=execution_id,
        result_summary=result_summary
    )


async def send_error_notification(
    openid: str,
    execution_id: str,
    error_message: str
) -> bool:
    """发送错误通知（便捷函数）"""
    notifier = get_wechat_notifier()
    return await notifier.send_error_notification(
        openid=openid,
        execution_id=execution_id,
        error_message=error_message
    )
