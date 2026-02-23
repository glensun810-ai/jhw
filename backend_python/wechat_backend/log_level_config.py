#!/usr/bin/env python3
"""
P2-1 修复：日志级别优化配置

功能：
1. 根据环境自动调整日志级别
2. 生产环境减少 DEBUG 日志
3. 保留关键日志用于问题排查
4. 支持动态调整日志级别
"""

import os
import logging
from pathlib import Path

# 环境配置
ENVIRONMENT = os.getenv('APP_ENV', 'development')  # development, staging, production

# 日志级别映射
LOG_LEVEL_MAP = {
    'development': 'DEBUG',
    'staging': 'INFO',
    'production': 'WARNING'  # 生产环境只记录警告和错误
}

# 模块级别的日志级别覆盖
MODULE_LOG_LEVELS = {
    # 关键模块保持 INFO 级别，便于问题排查
    'wechat_backend.api': 'INFO',
    'wechat_backend.database': 'INFO',
    'wechat_backend.nxm_execution_engine': 'INFO',
    
    # 减少详细日志的模块
    'wechat_backend.ai_adapters': 'WARNING',  # AI 调用频繁，减少日志
    'wechat_backend.optimization': 'WARNING',
    'wechat_backend.cache': 'WARNING',
    
    # 第三方库日志级别
    'werkzeug': 'WARNING',
    'apscheduler': 'WARNING',
    'urllib3': 'WARNING',
    'requests': 'WARNING',
}


def get_log_level(module_name: str = None) -> str:
    """
    获取日志级别
    
    Args:
        module_name: 模块名称
        
    Returns:
        日志级别字符串
    """
    # 检查模块级别的覆盖
    if module_name:
        # 检查是否有精确匹配
        if module_name in MODULE_LOG_LEVELS:
            return MODULE_LOG_LEVELS[module_name]
        
        # 检查是否有前缀匹配
        for prefix, level in MODULE_LOG_LEVELS.items():
            if module_name.startswith(prefix + '.'):
                return level
    
    # 返回环境对应的日志级别
    return LOG_LEVEL_MAP.get(ENVIRONMENT, 'INFO')


def setup_optimized_logging():
    """
    设置优化的日志配置
    
    Returns:
        根日志器
    """
    from wechat_backend.logging_config import setup_logging as original_setup
    
    # 获取根日志级别
    root_level = get_log_level()
    
    # 调用原有配置
    logger = original_setup(log_level=root_level)
    
    # 设置模块级别的日志级别
    for module_name, level_str in MODULE_LOG_LEVELS.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(getattr(logging, level_str.upper(), logging.INFO))
    
    return logger


def should_log_debug(module_name: str) -> bool:
    """
    判断是否应该记录 DEBUG 日志
    
    Args:
        module_name: 模块名称
        
    Returns:
        是否记录 DEBUG 日志
    """
    level = get_log_level(module_name)
    return level.upper() == 'DEBUG'


def should_log_info(module_name: str) -> bool:
    """
    判断是否应该记录 INFO 日志
    
    Args:
        module_name: 模块名称
        
    Returns:
        是否记录 INFO 日志
    """
    level = get_log_level(module_name)
    return level.upper() in ['DEBUG', 'INFO']


# 日志性能优化建议
OPTIMIZATION_TIPS = """
日志性能优化建议:

1. 避免在循环中记录日志
   ❌ for item in items: logger.debug(f"Processing {item}")
   ✅ logger.debug(f"Processing {len(items)} items")

2. 使用条件判断减少不必要的日志
   ❌ logger.debug(f"Expensive operation: {expensive_operation()}")
   ✅ if logger.isEnabledFor(logging.DEBUG): logger.debug(f"Expensive: {expensive_operation()}")

3. 生产环境使用 WARNING 级别
   减少磁盘 I/O 和日志文件大小

4. 关键路径使用 INFO 级别
   便于问题排查和性能分析

5. 定期清理日志文件
   避免磁盘空间耗尽
"""


if __name__ == '__main__':
    print("="*60)
    print("P2-1: 日志级别优化配置")
    print("="*60)
    print()
    print(f"当前环境：{ENVIRONMENT}")
    print(f"根日志级别：{get_log_level()}")
    print()
    print("模块日志级别配置:")
    for module, level in MODULE_LOG_LEVELS.items():
        print(f"  {module}: {level}")
    print()
    print(OPTIMIZATION_TIPS)
