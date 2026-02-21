"""
Database module - re-exports from database_core.py for package compatibility
"""

# Import everything from the database_core module
from wechat_backend.database_core import (
    DB_PATH,
    ENCRYPTION_ENABLED,
    get_connection,
    get_or_create_user_by_unionid,
    init_db,
    save_test_record,
    get_user_test_history,
    get_test_record_by_id,
    SafeDatabaseQuery,
    sql_protector,
)
