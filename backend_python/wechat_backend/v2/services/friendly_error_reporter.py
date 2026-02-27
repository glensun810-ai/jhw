"""
异常场景友好提示模块

功能：
- 定义友好的错误提示文案
- 错误类型映射
- 用户操作建议
- 错误日志记录

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = 'info'           # 信息提示
    WARNING = 'warning'     # 警告
    ERROR = 'error'         # 错误
    CRITICAL = 'critical'   # 严重错误


@dataclass
class ErrorDisplayConfig:
    """错误显示配置"""
    title: str              # 标题
    message: str            # 消息内容
    action_text: str        # 操作按钮文本
    action_type: str        # 操作类型：retry | navigate | dismiss
    action_target: str      # 操作目标（页面 URL 或回调）
    icon: str = 'none'      # 图标：none | success | warning | error
    duration: int = 3000    # 显示时长（毫秒）


# 错误类型到显示配置的映射
ERROR_DISPLAY_MAPPING: Dict[str, ErrorDisplayConfig] = {
    # 网络错误
    'NETWORK_ERROR': ErrorDisplayConfig(
        title='网络连接失败',
        message='请检查您的网络连接，然后重试',
        action_text='重试',
        action_type='retry',
        action_target='',
        icon='warning',
        duration=3000
    ),
    
    'NETWORK_TIMEOUT': ErrorDisplayConfig(
        title='请求超时',
        message='网络响应超时，请稍后重试',
        action_text='重试',
        action_type='retry',
        action_target='',
        icon='warning',
        duration=3000
    ),
    
    # AI 平台错误
    'AI_PLATFORM_ERROR': ErrorDisplayConfig(
        title='AI 平台暂时不可用',
        message='所选 AI 平台暂时无法访问，我们已记录此问题',
        action_text='切换 AI 模型',
        action_type='navigate',
        action_target='/pages/config/config',
        icon='error',
        duration=5000
    ),
    
    'AI_QUOTA_EXHAUSTED': ErrorDisplayConfig(
        title='AI 配额已用尽',
        message='当前 AI 平台的可用配额已用尽，请稍后重试或切换其他平台',
        action_text='切换平台',
        action_type='navigate',
        action_target='/pages/config/config',
        icon='warning',
        duration=5000
    ),
    
    'AI_RATE_LIMIT': ErrorDisplayConfig(
        title='请求过于频繁',
        message='请稍后再试',
        action_text='知道了',
        action_type='dismiss',
        action_target='',
        icon='warning',
        duration=3000
    ),
    
    # 诊断任务错误
    'DIAGNOSIS_TIMEOUT': ErrorDisplayConfig(
        title='诊断超时',
        message='诊断任务执行时间过长，已保存当前进度',
        action_text='查看历史记录',
        action_type='navigate',
        action_target='/pages/history/history',
        icon='error',
        duration=5000
    ),
    
    'DIAGNOSIS_FAILED': ErrorDisplayConfig(
        title='诊断失败',
        message='诊断任务执行失败，已保存当前进度',
        action_text='查看部分结果',
        action_type='navigate',
        action_target='/pages/history/history',
        icon='error',
        duration=5000
    ),
    
    'DIAGNOSIS_PARTIAL_SUCCESS': ErrorDisplayConfig(
        title='部分完成',
        message='部分 AI 平台返回了结果，您可以查看已有数据',
        action_text='查看结果',
        action_type='navigate',
        action_target='',
        icon='warning',
        duration=5000
    ),
    
    # 数据错误
    'DATA_NOT_FOUND': ErrorDisplayConfig(
        title='数据不存在',
        message='未找到相关数据，请检查后重试',
        action_text='返回',
        action_type='navigate',
        action_target='/pages/index/index',
        icon='error',
        duration=3000
    ),
    
    'DATA_FORMAT_ERROR': ErrorDisplayConfig(
        title='数据格式错误',
        message='数据格式异常，请刷新后重试',
        action_text='刷新',
        action_type='retry',
        action_target='',
        icon='error',
        duration=3000
    ),
    
    # 权限错误
    'UNAUTHORIZED': ErrorDisplayConfig(
        title='未授权',
        message='请先登录后再使用此功能',
        action_text='去登录',
        action_type='navigate',
        action_target='/pages/login/login',
        icon='error',
        duration=3000
    ),
    
    'FORBIDDEN': ErrorDisplayConfig(
        title='无权限',
        message='您没有权限执行此操作',
        action_text='知道了',
        action_type='dismiss',
        action_target='',
        icon='error',
        duration=3000
    ),
    
    # 系统错误
    'SERVER_ERROR': ErrorDisplayConfig(
        title='服务器错误',
        message='服务器暂时繁忙，请稍后重试',
        action_text='重试',
        action_type='retry',
        action_target='',
        icon='error',
        duration=3000
    ),
    
    'SERVICE_UNAVAILABLE': ErrorDisplayConfig(
        title='服务不可用',
        message='服务暂时不可用，请稍后重试',
        action_text='知道了',
        action_type='dismiss',
        action_target='',
        icon='error',
        duration=3000
    ),
    
    # 默认错误
    'UNKNOWN_ERROR': ErrorDisplayConfig(
        title='出错了',
        message='发生未知错误，请稍后重试',
        action_text='重试',
        action_type='retry',
        action_target='',
        icon='error',
        duration=3000
    )
}


class FriendlyErrorReporter:
    """
    友好错误报告器
    
    将技术错误转换为用户友好的提示信息
    """
    
    def __init__(self):
        """初始化错误报告器"""
        self.error_mapping = ERROR_DISPLAY_MAPPING
    
    def get_display_config(self, error_type: str) -> ErrorDisplayConfig:
        """
        获取错误显示配置
        
        参数:
            error_type: 错误类型
            
        返回:
            错误显示配置
        """
        # 优先使用精确匹配
        if error_type in self.error_mapping:
            return self.error_mapping[error_type]
        
        # 模糊匹配（包含关键词）
        error_type_upper = error_type.upper()
        for key, config in self.error_mapping.items():
            if key in error_type_upper or error_type_upper in key:
                return config
        
        # 返回默认配置
        return self.error_mapping['UNKNOWN_ERROR']
    
    def format_error_message(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        格式化错误消息
        
        参数:
            error_type: 错误类型
            error_message: 原始错误消息
            context: 上下文信息
            
        返回:
            格式化后的错误消息（包含显示配置和详细信息）
        """
        config = self.get_display_config(error_type)
        
        return {
            'error_type': error_type,
            'original_message': error_message,
            'display': {
                'title': config.title,
                'message': config.message,
                'action_text': config.action_text,
                'action_type': config.action_type,
                'action_target': config.action_target,
                'icon': config.icon,
                'duration': config.duration
            },
            'context': context or {},
            'timestamp': self._get_timestamp()
        }
    
    def should_auto_retry(self, error_type: str) -> bool:
        """
        判断是否应该自动重试
        
        参数:
            error_type: 错误类型
            
        返回:
            是否应该自动重试
        """
        # 网络错误可以重试
        if 'NETWORK' in error_type.upper():
            return True
        
        # AI 限流可以重试
        if 'RATE_LIMIT' in error_type.upper():
            return True
        
        # 其他错误不建议自动重试
        return False
    
    def get_retry_delay(self, error_type: str, attempt: int) -> int:
        """
        获取重试延迟（毫秒）
        
        参数:
            error_type: 错误类型
            attempt: 重试次数
            
        返回:
            重试延迟（毫秒）
        """
        # 指数退避策略
        base_delay = 1000  # 1 秒
        max_delay = 30000  # 30 秒
        
        delay = base_delay * (2 ** attempt)
        
        # 添加随机抖动（10%）
        import random
        jitter = delay * 0.1 * random.random()
        delay = delay + jitter
        
        return min(delay, max_delay)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 全局错误报告器实例
friendly_error_reporter = FriendlyErrorReporter()


def get_friendly_error(error_type: str, error_message: str = '', context: Dict = None) -> Dict:
    """
    便捷函数：获取友好错误消息
    
    参数:
        error_type: 错误类型
        error_message: 原始错误消息
        context: 上下文信息
        
    返回:
        格式化后的错误消息
    """
    return friendly_error_reporter.format_error_message(error_type, error_message, context)


# 使用示例
"""
from wechat_backend.v2.services.friendly_error_reporter import get_friendly_error

# 获取友好错误消息
error = get_friendly_error(
    error_type='AI_PLATFORM_ERROR',
    error_message='Qwen API timeout',
    context={'model': 'qwen', 'execution_id': 'xxx'}
)

# 显示错误提示
wx.showModal({
    title: error['display']['title'],
    content: error['display']['message'],
    confirmText: error['display']['action_text'],
    success: (res) => {
        if (res.confirm) {
            // 执行操作
        }
    }
})
"""
