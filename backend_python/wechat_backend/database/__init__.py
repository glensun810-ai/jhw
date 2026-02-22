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
]
