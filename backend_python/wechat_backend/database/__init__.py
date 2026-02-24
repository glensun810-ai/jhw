"""
Database module - re-exports from database_core.py for package compatibility

注意：此文件仅用于向后兼容，新功能请使用：
- database_connection_pool.py - 连接池管理
- database_repositories.py - 数据仓库层
- database_core.py - 数据库初始化
- database_query_optimizer.py - 查询优化器
"""

# Import from database_core module
from wechat_backend.database_core import (
    DB_PATH,
    ENCRYPTION_ENABLED,
    ENCRYPTION_KEY,
    DATABASE_ENCRYPTION,
    get_connection,
    return_connection,
    close_db_connection,
    init_db,
)

# Import from database_connection_pool for compatibility
from wechat_backend.database_connection_pool import (
    get_db_pool,
    get_db_pool_metrics,
    reset_db_pool_metrics,
)

# Import from database_query_optimizer for compatibility
try:
    from wechat_backend.database_query_optimizer import (
        query_optimizer,
        QueryOptimizer,
    )
except ImportError:
    query_optimizer = None
    QueryOptimizer = None

# Import security utilities
try:
    from wechat_backend.security.sql_protection import (
        SafeDatabaseQuery,
        sql_protector,
    )
except ImportError:
    # 如果安全模块不可用，使用占位符
    SafeDatabaseQuery = None
    sql_protector = None


# ==================== Legacy 函数兼容层 ====================
# 这些函数已迁移到 database_repositories.py，但为了向后兼容，保留导出
# 注意：这些函数已废弃，请使用 database_repositories.py 中的新函数

def save_test_record(*args, **kwargs):
    """
    Legacy function - 保存测试记录（已废弃）
    
    已迁移到 database_repositories.py
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.database_repositories import save_test_record as new_save_test_record
    
    db_logger.warning('save_test_record is deprecated, use database_repositories instead')
    return new_save_test_record(*args, **kwargs)


def get_user_test_history(*args, **kwargs):
    """
    Legacy function - 获取用户测试历史（已废弃）
    
    已迁移到 database_repositories.py
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.database_repositories import get_user_test_history as new_get_user_test_history
    
    db_logger.warning('get_user_test_history is deprecated, use database_repositories instead')
    return new_get_user_test_history(*args, **kwargs)


def get_test_record_by_id(*args, **kwargs):
    """
    Legacy function - 根据 ID 获取测试记录（已废弃）
    
    已迁移到 database_repositories.py
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.database_repositories import get_test_record_by_id as new_get_test_record_by_id
    
    db_logger.warning('get_test_record_by_id is deprecated, use database_repositories instead')
    return new_get_test_record_by_id(*args, **kwargs)


def get_or_create_user_by_unionid(*args, **kwargs):
    """
    Legacy function - 获取或创建用户（已废弃）
    
    已迁移到 database_repositories.py
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.database_repositories import get_or_create_user_by_unionid as new_get_or_create_user
    
    db_logger.warning('get_or_create_user_by_unionid is deprecated, use database_repositories instead')
    return new_get_or_create_user_by_unionid(*args, **kwargs)

# Export all
__all__ = [
    # Constants
    'DB_PATH',
    'ENCRYPTION_ENABLED',
    'ENCRYPTION_KEY',
    'DATABASE_ENCRYPTION',
    
    # Connection pool
    'get_db_pool',
    'get_db_pool_metrics',
    'reset_db_pool_metrics',
    'get_connection',
    'return_connection',
    'close_db_connection',
    
    # Initialization
    'init_db',
    
    # Query optimizer
    'query_optimizer',
    'QueryOptimizer',
    
    # Security
    'SafeDatabaseQuery',
    'sql_protector',
    
    # Legacy functions (deprecated)
    'save_test_record',
    'get_user_test_history',
    'get_test_record_by_id',
    'get_or_create_user_by_unionid',
]
