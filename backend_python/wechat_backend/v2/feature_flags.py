"""
特性开关管理模块

所有新功能必须通过特性开关控制，默认关闭。

使用方法:
    from wechat_backend.v2.feature_flags import should_use_v2, FEATURE_FLAGS
    
    if should_use_v2(user_id):
        # 使用 v2 功能
        pass
"""

import random
from typing import List, Dict, Any


# ==================== 特性开关配置 ====================

FEATURE_FLAGS: Dict[str, Any] = {
    # ==================== 总开关 ====================
    'diagnosis_v2_enabled': False,  # v2 系统总开关（默认关闭）
    
    # ==================== 功能开关 ====================
    # 阶段一：基础能力加固
    'diagnosis_v2_state_machine': True,       # 状态机（P1-T1 已完成）
    'diagnosis_v2_timeout': False,            # 超时机制（P1-T2）
    'diagnosis_v2_retry': False,              # 重试机制（P1-T3）
    'diagnosis_v2_dead_letter': False,        # 死信队列（P1-T4）
    'diagnosis_v2_dead_letter_auto_retry': False,  # 自动重试死信
    'diagnosis_v2_api_logging': False,        # API 调用日志（P1-T5）
    'diagnosis_v2_storage': False,            # 原始数据持久化（P1-T6）
    'diagnosis_v2_report_stub': False,        # 报告存根（P1-T7）
    
    # 阶段二：核心业务功能
    'diagnosis_v2_ai_adapter': False,         # AI 适配器层（P2-T1）
    'diagnosis_v2_data_pipeline': False,      # 数据清洗管道（P2-T2）
    'diagnosis_v2_brand_distribution': False, # 品牌分布统计（P2-T3）
    'diagnosis_v2_sentiment_analysis': False, # 情感分析（P2-T4）
    'diagnosis_v2_keywords': False,           # 关键词提取（P2-T5）
    'diagnosis_v2_trend': False,              # 趋势分析（P2-T6）
    
    # 阶段三：体验与可靠性
    'diagnosis_v2_websocket': False,          # WebSocket 推送（P3-T1）
    'diagnosis_v2_error_handling': False,     # 异常友好提示（P3-T3）
    'diagnosis_v2_cache': False,              # 缓存优化（P3-T6）
    
    # ==================== 灰度控制 ====================
    'diagnosis_v2_gray_users': [],            # 灰度用户列表 (OpenID)
    'diagnosis_v2_gray_percentage': 0,        # 灰度百分比 (0-100)
    
    # ==================== 降级开关 ====================
    'diagnosis_v2_fallback_to_v1': True,      # v2 失败时降级到 v1
}


# ==================== 开关管理函数 ====================

def enable_feature(flag_name: str, value: bool = True) -> None:
    """
    启用特性开关
    
    Args:
        flag_name: 开关名称
        value: 开关值（默认 True）
        
    Raises:
        KeyError: 开关不存在
    """
    if flag_name not in FEATURE_FLAGS:
        raise KeyError(f"未知的特性开关：{flag_name}")
    
    FEATURE_FLAGS[flag_name] = value


def disable_feature(flag_name: str) -> None:
    """
    禁用特性开关
    
    Args:
        flag_name: 开关名称
        
    Raises:
        KeyError: 开关不存在
    """
    enable_feature(flag_name, False)


def is_feature_enabled(flag_name: str) -> bool:
    """
    检查特性开关状态
    
    Args:
        flag_name: 开关名称
        
    Returns:
        bool: 开关状态
        
    Raises:
        KeyError: 开关不存在
    """
    if flag_name not in FEATURE_FLAGS:
        raise KeyError(f"未知的特性开关：{flag_name}")
    
    return FEATURE_FLAGS[flag_name]


def should_use_v2(user_id: str) -> bool:
    """
    判断用户是否使用 v2 版本
    
    判断逻辑:
    1. 总开关关闭 -> 返回 False
    2. 灰度用户 -> 返回 True
    3. 按百分比灰度 -> 随机判断
    4. 其他 -> 返回 False
    
    Args:
        user_id: 用户 ID (OpenID)
        
    Returns:
        bool: 是否使用 v2 版本
    """
    # 1. 检查总开关
    if not FEATURE_FLAGS['diagnosis_v2_enabled']:
        return False
    
    # 2. 检查灰度用户
    gray_users: List[str] = FEATURE_FLAGS.get('diagnosis_v2_gray_users', [])
    if user_id in gray_users:
        return True
    
    # 3. 按百分比灰度
    gray_percentage: int = FEATURE_FLAGS.get('diagnosis_v2_gray_percentage', 0)
    if random.randint(0, 99) < gray_percentage:
        return True
    
    # 4. 默认不使用 v2
    return False


def get_all_flags() -> Dict[str, Any]:
    """
    获取所有特性开关
    
    Returns:
        Dict[str, Any]: 所有特性开关配置
    """
    return FEATURE_FLAGS.copy()


def update_flags(updates: Dict[str, Any]) -> None:
    """
    批量更新特性开关
    
    Args:
        updates: 开关更新字典
        
    Raises:
        KeyError: 包含不存在的开关
    """
    for flag_name, value in updates.items():
        if flag_name not in FEATURE_FLAGS:
            raise KeyError(f"未知的特性开关：{flag_name}")
        FEATURE_FLAGS[flag_name] = value
