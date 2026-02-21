"""
Database schema for GEO Content Quality Validator

修复记录:
- 2026-02-20: 使用上下文管理器确保连接关闭
- 2026-02-20: 添加数据加密支持 (P0-3)

P1 修复：使用绝对路径引用，避免相对路径越界错误
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

from wechat_backend.logging_config import db_logger
from wechat_backend.security.sql_protection import SafeDatabaseQuery, sql_protector
from wechat_backend.security.data_encryption import (
    encrypt_field,
    decrypt_field,
    encrypt_sensitive_data,
    decrypt_sensitive_data,
    SENSITIVE_FIELDS
)

DB_PATH = Path(__file__).parent.parent / 'database.db'

# 加密开关 (可通过环境变量控制)
ENCRYPTION_ENABLED = os.environ.get('ENCRYPTION_ENABLED', 'false').lower() == 'true'


def get_or_create_user_by_unionid(union_id: str, openid: str) -> tuple:
    """
    Get or create user by UnionID
    
    Args:
        union_id: WeChat UnionID (or openid if unionid not available)
        openid: WeChat OpenID
        
    Returns:
        tuple: (user_dict, is_new_user)
    """
    from wechat_backend.logging_config import db_logger
    import sqlite3
    
    db_logger.info(f"Get or create user by union_id: {union_id[:10]}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Query existing user
        cursor.execute('''
            SELECT id, union_id, membership_plan, diagnostic_limit
            FROM users
            WHERE union_id = ? OR openid = ?
        ''', (union_id, openid))
        
        row = cursor.fetchone()
        
        if row:
            # Existing user, update info
            cursor.execute('''
                UPDATE users
                SET union_id = ?, openid = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (union_id, openid, row[0]))
            conn.commit()
            
            user = {
                'id': row[0],
                'union_id': row[1],
                'membership_plan': row[2] or 'free',
                'diagnostic_limit': row[3] or 2
            }
            is_new_user = False
            db_logger.info(f"Existing user found: {union_id[:10]}...")
        else:
            # New user, create record
            cursor.execute('''
                INSERT INTO users (union_id, openid, membership_plan, diagnostic_limit, created_at)
                VALUES (?, ?, 'free', 2, CURRENT_TIMESTAMP)
            ''', (union_id, openid))
            conn.commit()
            
            user = {
                'id': cursor.lastrowid,
                'union_id': union_id,
                'membership_plan': 'free',
                'diagnostic_limit': 2
            }
            is_new_user = True
            db_logger.info(f"New user created: {union_id[:10]}...")
        
        return user, is_new_user
        
    except Exception as e:
        db_logger.error(f"Error in get_or_create_user_by_unionid: {e}")
        conn.rollback()
        # Return default user on error
        return {'id': 0, 'union_id': union_id, 'membership_plan': 'free', 'diagnostic_limit': 2}, True
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables"""
    db_logger.info(f"Initializing database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE,
            phone TEXT UNIQUE,
            password_hash TEXT,
            nickname TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db_logger.debug("Users table created or verified")

    # Create brands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    db_logger.debug("Brands table created or verified")

    # Create test_records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_name TEXT NOT NULL,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_models_used TEXT, -- JSON string
            questions_used TEXT, -- JSON string
            overall_score REAL,
            total_tests INTEGER,
            results_summary TEXT, -- JSON string with key metrics
            detailed_results TEXT, -- Full JSON results
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    db_logger.debug("Test records table created or verified")

    # Create user_preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            preference_key TEXT NOT NULL,
            preference_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, preference_key)
        )
    ''')
    db_logger.debug("User preferences table created or verified")

    # Create task statuses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            progress INTEGER DEFAULT 0,
            stage TEXT NOT NULL,
            status_text TEXT,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db_logger.debug("Task statuses table created or verified")

    # Create deep intelligence results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deep_intelligence_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            exposure_analysis TEXT, -- JSON string
            source_intelligence TEXT, -- JSON string
            evidence_chain TEXT, -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES task_statuses (task_id)
        )
    ''')
    db_logger.debug("Deep intelligence results table created or verified")

    conn.commit()
    conn.close()
    db_logger.info("Database initialization completed")

def save_test_record(user_openid, brand_name, ai_models_used, questions_used, overall_score, total_tests, results_summary, detailed_results):
    """
    Save a test record to the database (修复版 + 加密支持)
    
    修复内容:
    1. ✅ 使用上下文管理器确保连接关闭
    2. ✅ 添加输入验证
    3. ✅ 使用 SafeDatabaseQuery 统一处理
    4. ✅ P0-3: 添加敏感数据加密支持
    """
    from .security.input_validator import validate_execution_id, validate_brand_name
    
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(brand_name):
        raise ValueError("Invalid brand_name")

    db_logger.info(f"Saving test record for user: {user_openid}, brand: {brand_name}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # Get user ID or create new user
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if user_rows:
            user_id = user_rows[0][0]
            db_logger.debug(f"Found existing user with ID: {user_id}")
        else:
            # Create new user
            safe_query.execute_query('INSERT INTO users (openid) VALUES (?)', (user_openid,))
            # Get the new user ID - 在同一连接中获取 lastrowid
            user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))
            user_id = user_rows[0][0]
            db_logger.debug(f"Created new user with ID: {user_id}")

        # Convert lists/dicts to JSON strings
        ai_models_json = json.dumps(ai_models_used)
        questions_json = json.dumps(questions_used)
        results_summary_json = json.dumps(results_summary)
        detailed_results_json = json.dumps(detailed_results)
        
        # P0-3: 加密敏感数据
        if ENCRYPTION_ENABLED:
            try:
                detailed_results_json = encrypt_field(detailed_results_json)
                db_logger.debug("Encrypted detailed_results")
            except Exception as e:
                db_logger.warning(f"Failed to encrypt detailed_results: {e}, saving unencrypted")

        # Insert test record - 使用 safe_query 而不是直接连接
        safe_query.execute_query('''
            INSERT INTO test_records
            (user_id, brand_name, ai_models_used, questions_used, overall_score, total_tests, results_summary, detailed_results)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, brand_name, ai_models_json, questions_json, overall_score, total_tests, results_summary_json, detailed_results_json))

        # 获取插入的 ID - 需要在同一连接中执行
        result = safe_query.execute_query('SELECT last_insert_rowid()')
        record_id = result[0][0] if result else None

    db_logger.info(f"Test record saved successfully with ID: {record_id}")

    return record_id

def get_user_test_history(user_openid, limit=20, offset=0):
    """Get test history for a specific user (修复版)"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")

    # Validate numeric inputs
    if not isinstance(limit, int) or not isinstance(offset, int) or limit < 0 or offset < 0:
        raise ValueError("Limit and offset must be non-negative integers")

    db_logger.info(f"Retrieving test history for user: {user_openid}, limit: {limit}, offset: {offset}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # Get user ID
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if not user_rows:
            db_logger.debug(f"No user found with openid: {user_openid}")
            return []

        user_id = user_rows[0][0]
        db_logger.debug(f"Found user with ID: {user_id}")

        # Get test records for this user
        records_data = safe_query.execute_query('''
            SELECT id, brand_name, test_date, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary
            FROM test_records
            WHERE user_id = ?
            ORDER BY test_date DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))

        records = []
        for row in records_data:
            record = {
                'id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': json.loads(row[7]) if row[7] else {}
            }
            records.append(record)

    db_logger.info(f"Retrieved {len(records)} test records for user: {user_openid}")
    return records

def get_test_record_by_id(record_id):
    """
    Get a specific test record by ID (修复版 + 加密支持)
    
    P0-3: 添加敏感数据解密支持
    """
    # Validate inputs to prevent SQL injection
    if not isinstance(record_id, int) or record_id < 0:
        raise ValueError("Record ID must be a non-negative integer")

    db_logger.info(f"Retrieving test record with ID: {record_id}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        rows = safe_query.execute_query('''
            SELECT id, brand_name, test_date, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary, detailed_results
            FROM test_records
            WHERE id = ?
        ''', (record_id,))

        if rows:
            row = rows[0]  # Get first row
            record = {
                'id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': json.loads(row[7]) if row[7] else {},
                'detailed_results': json.loads(row[8]) if row[8] else []
            }
            
            # P0-3: 解密敏感数据
            if ENCRYPTION_ENABLED and record.get('detailed_results'):
                try:
                    # 尝试解密
                    record['detailed_results'] = decrypt_field(record['detailed_results'])
                    record['detailed_results'] = json.loads(record['detailed_results'])
                    db_logger.debug("Decrypted detailed_results")
                except Exception as e:
                    db_logger.warning(f"Failed to decrypt detailed_results: {e}, keeping original")
            
            db_logger.info(f"Successfully retrieved test record with ID: {record_id}")
        else:
            record = None
            db_logger.warning(f"No test record found with ID: {record_id}")

    return record


def save_user_preference(user_openid, preference_key, preference_value):
    """
    Save a user preference (修复版 + 加密支持)
    
    P0-3: 加密用户偏好数据
    """
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(preference_key):
        raise ValueError("Invalid preference_key")

    db_logger.info(f"Saving user preference for user {user_openid}, key: {preference_key}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # First, get or create user ID based on openid
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if user_rows:
            user_id = user_rows[0][0]
        else:
            # Create new user if not exists
            safe_query.execute_query('INSERT INTO users (openid) VALUES (?)', (user_openid,))
            # Get the new user ID
            user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))
            user_id = user_rows[0][0]

        # Convert preference value to JSON string if it's a dict/list
        if isinstance(preference_value, (dict, list)):
            pref_value_str = json.dumps(preference_value)
        else:
            pref_value_str = str(preference_value)
        
        # P0-3: 加密敏感数据
        if ENCRYPTION_ENABLED:
            try:
                pref_value_str = encrypt_field(pref_value_str)
                db_logger.debug(f"Encrypted preference value for key: {preference_key}")
            except Exception as e:
                db_logger.warning(f"Failed to encrypt preference {preference_key}: {e}")

        try:
            safe_query.execute_query('''
                INSERT OR REPLACE INTO user_preferences
                (user_id, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, preference_key, pref_value_str))

            db_logger.info(f"User preference saved successfully: {preference_key}")
        except Exception as e:
            db_logger.error(f"Error saving user preference: {e}")
            raise


def get_user_preference(user_openid, preference_key, default_value=None):
    """
    Get a user preference (修复版 + 加密支持)
    
    P0-3: 解密用户偏好数据
    """
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(preference_key):
        raise ValueError("Invalid preference_key")

    db_logger.info(f"Retrieving user preference for user {user_openid}, key: {preference_key}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # Get user ID based on openid
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if not user_rows:
            return default_value

        user_id = user_rows[0][0]

        rows = safe_query.execute_query('''
            SELECT preference_value
            FROM user_preferences
            WHERE user_id = ? AND preference_key = ?
        ''', (user_id, preference_key))

        if rows:
            pref_value_str = rows[0][0]
            # P0-3: 尝试解密
            if ENCRYPTION_ENABLED:
                try:
                    pref_value_str = decrypt_field(pref_value_str)
                    db_logger.debug(f"Decrypted preference value for key: {preference_key}")
                except Exception as e:
                    db_logger.warning(f"Failed to decrypt preference {preference_key}: {e}, keeping original")
            
            # Try to parse as JSON, if it fails return as string
            try:
                return json.loads(pref_value_str)
            except (json.JSONDecodeError, TypeError):
                return pref_value_str
        else:
            return default_value


def get_all_user_preferences(user_openid):
    """Get all preferences for a user (修复版)"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")

    db_logger.info(f"Retrieving all preferences for user {user_openid}")

    # 使用上下文管理器确保连接关闭
    with SafeDatabaseQuery(DB_PATH) as safe_query:
        # Get user ID based on openid
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

        if not user_rows:
            return {}

        user_id = user_rows[0][0]

        rows = safe_query.execute_query('''
            SELECT preference_key, preference_value
            FROM user_preferences
            WHERE user_id = ?
        ''', (user_id,))

        preferences = {}
        for row in rows:
            key, value_str = row
            # Try to parse as JSON, if it fails return as string
            try:
                preferences[key] = json.loads(value_str)
            except (json.JSONDecodeError, TypeError):
                preferences[key] = value_str

    return preferences


# Verification code storage (in-memory for mock, should use Redis in production)
_verification_codes = {}


def save_verification_code(phone: str, code: str):
    """
    Save verification code for phone number
    
    Args:
        phone: Phone number
        code: Verification code
    """
    from datetime import timedelta
    from wechat_backend.logging_config import db_logger
    
    expiration_time = datetime.now() + timedelta(minutes=5)  # 5 minutes validity
    _verification_codes[phone] = {
        'code': code,
        'expires_at': expiration_time,
        'attempts': 0
    }
    db_logger.debug(f"Verification code saved for {phone}")


def verify_code(phone: str, code: str) -> bool:
    """
    Verify the code for a phone number
    
    Args:
        phone: Phone number
        code: Code to verify
        
    Returns:
        bool: True if code is valid, False otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    if phone not in _verification_codes:
        db_logger.warning(f"No verification code found for {phone}")
        return False
    
    stored = _verification_codes[phone]
    
    # Check expiration
    if datetime.now() > stored['expires_at']:
        del _verification_codes[phone]
        db_logger.warning(f"Verification code expired for {phone}")
        return False
    
    # Check attempts
    if stored['attempts'] >= 5:
        del _verification_codes[phone]
        db_logger.warning(f"Too many verification attempts for {phone}")
        return False
    
    # Verify code
    if stored['code'] != code:
        stored['attempts'] += 1
        db_logger.warning(f"Invalid verification code for {phone}, attempt {stored['attempts']}")
        return False
    
    # Code is valid, remove it
    del _verification_codes[phone]
    db_logger.info(f"Verification code validated for {phone}")
    return True


def create_user_with_phone(phone: str, password_hash: str, nickname: str = None) -> int:
    """
    Create a new user with phone and password
    
    Args:
        phone: Phone number
        password_hash: Hashed password
        nickname: Optional nickname
        
    Returns:
        int: User ID if successful, -1 if failed
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.security.sql_protection import SafeDatabaseQuery
    
    db_logger.info(f"Creating user with phone: {phone}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if phone already exists
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        existing = cursor.fetchone()
        if existing:
            db_logger.error(f"Phone number {phone} already registered")
            return -1
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (phone, password_hash, nickname, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (phone, password_hash, nickname))
        
        conn.commit()
        user_id = cursor.lastrowid
        db_logger.info(f"User created with ID: {user_id}")
        return user_id
        
    except Exception as e:
        db_logger.error(f"Error creating user: {e}")
        return -1
    finally:
        if conn:
            conn.close()


def get_user_by_phone(phone: str) -> dict:
    """
    Get user by phone number
    
    Args:
        phone: Phone number
        
    Returns:
        dict: User data or None if not found
    """
    from wechat_backend.logging_config import db_logger
    from wechat_backend.security.sql_protection import SafeDatabaseQuery
    
    db_logger.info(f"Looking up user by phone: {phone}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, phone, password_hash, nickname, avatar_url, created_at
            FROM users
            WHERE phone = ?
        ''', (phone,))
        
        row = cursor.fetchone()
        if not row:
            db_logger.info(f"No user found for phone: {phone}")
            return None
        
        return {
            'id': row[0],
            'phone': row[1],
            'password_hash': row[2],
            'nickname': row[3],
            'avatar_url': row[4],
            'created_at': row[5]
        }
        
    except Exception as e:
        db_logger.error(f"Error getting user by phone: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id: int) -> dict:
    """
    Get user by ID
    
    Args:
        user_id: User ID
        
    Returns:
        dict: User data or None if not found
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info(f"Looking up user by ID: {user_id}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, phone, nickname, avatar_url, created_at, updated_at
            FROM users
            WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if not row:
            db_logger.info(f"No user found for ID: {user_id}")
            return None
        
        return {
            'id': row[0],
            'phone': row[1],
            'nickname': row[2],
            'avatar_url': row[3],
            'created_at': row[4],
            'updated_at': row[5]
        }
        
    except Exception as e:
        db_logger.error(f"Error getting user by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_user_profile(user_id: int, data: dict) -> bool:
    """
    Update user profile information
    
    Args:
        user_id: User ID
        data: Dictionary containing fields to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info(f"Updating profile for user {user_id}")
    
    # Allowed fields that can be updated
    allowed_fields = ['nickname', 'avatar_url']
    
    # Filter only allowed fields
    update_data = {k: v for k, v in data.items() if k in allowed_fields and v is not None}
    
    if not update_data:
        db_logger.warning("No valid fields to update")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build dynamic UPDATE statement
        fields = ', '.join([f"{field} = ?" for field in update_data.keys()])
        values = list(update_data.values())
        values.append(user_id)  # For WHERE clause
        
        query = f'''
            UPDATE users 
            SET {fields}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''
        
        cursor.execute(query, values)
        conn.commit()
        
        if cursor.rowcount > 0:
            db_logger.info(f"Updated {cursor.rowcount} row(s) for user {user_id}")
            return True
        else:
            db_logger.warning(f"No rows updated for user {user_id}")
            return False
            
    except Exception as e:
        db_logger.error(f"Error updating user profile: {e}")
        return False
    finally:
        if conn:
            conn.close()


# ============================================================================
# Data Sync Tables and Functions
# ============================================================================

def init_sync_db():
    """
    Initialize database tables for data sync
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info("Initializing sync database tables")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create user_data table for storing synced test results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            result_id TEXT UNIQUE NOT NULL,
            brand_name TEXT NOT NULL,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_models_used TEXT,  -- JSON string
            questions_used TEXT,  -- JSON string
            overall_score REAL,
            total_tests INTEGER,
            results_summary TEXT,  -- JSON string
            detailed_results TEXT,  -- Full JSON results
            sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    db_logger.debug("user_data table created or verified")
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_data_user_id 
        ON user_data(user_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_data_result_id 
        ON user_data(result_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_data_sync_timestamp 
        ON user_data(sync_timestamp)
    ''')
    db_logger.debug("Indexes created for user_data table")
    
    conn.commit()
    conn.close()
    db_logger.info("Sync database initialization completed")


def save_user_data(user_id: int, data: dict) -> str:
    """
    Save or update user data (test result)
    
    Args:
        user_id: User ID
        data: Dictionary containing test result data
        
    Returns:
        str: Result ID if successful, None otherwise
    """
    from wechat_backend.logging_config import db_logger
    import json
    
    db_logger.info(f"Saving user data for user {user_id}")
    
    # Generate result ID if not provided
    result_id = data.get('result_id') or f"result_{user_id}_{int(datetime.now().timestamp())}"
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if result already exists
        cursor.execute('SELECT id FROM user_data WHERE result_id = ?', (result_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute('''
                UPDATE user_data 
                SET brand_name = ?,
                    ai_models_used = ?,
                    questions_used = ?,
                    overall_score = ?,
                    total_tests = ?,
                    results_summary = ?,
                    detailed_results = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    is_deleted = 0
                WHERE result_id = ?
            ''', (
                data.get('brand_name', ''),
                json.dumps(data.get('ai_models_used', [])),
                json.dumps(data.get('questions_used', [])),
                data.get('overall_score', 0),
                data.get('total_tests', 0),
                json.dumps(data.get('results_summary', {})),
                json.dumps(data.get('detailed_results', {})),
                result_id
            ))
            db_logger.info(f"Updated existing result {result_id} for user {user_id}")
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO user_data (
                    user_id, result_id, brand_name, ai_models_used, 
                    questions_used, overall_score, total_tests, 
                    results_summary, detailed_results
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                result_id,
                data.get('brand_name', ''),
                json.dumps(data.get('ai_models_used', [])),
                json.dumps(data.get('questions_used', [])),
                data.get('overall_score', 0),
                data.get('total_tests', 0),
                json.dumps(data.get('results_summary', {})),
                json.dumps(data.get('detailed_results', {}))
            ))
            db_logger.info(f"Inserted new result {result_id} for user {user_id}")
        
        conn.commit()
        return result_id
        
    except Exception as e:
        db_logger.error(f"Error saving user data: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_data(user_id: int, since_timestamp: str = None) -> list:
    """
    Get user data for sync (incremental sync support)
    
    Args:
        user_id: User ID
        since_timestamp: Only return data synced after this timestamp (for incremental sync)
        
    Returns:
        list: List of user data records
    """
    from wechat_backend.logging_config import db_logger
    import json
    
    db_logger.info(f"Getting user data for user {user_id} since {since_timestamp or 'beginning'}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if since_timestamp:
            cursor.execute('''
                SELECT result_id, brand_name, test_date, ai_models_used,
                       questions_used, overall_score, total_tests,
                       results_summary, detailed_results, sync_timestamp,
                       is_deleted
                FROM user_data
                WHERE user_id = ? 
                  AND sync_timestamp > ?
                  AND is_deleted = 0
                ORDER BY sync_timestamp ASC
            ''', (user_id, since_timestamp))
        else:
            cursor.execute('''
                SELECT result_id, brand_name, test_date, ai_models_used,
                       questions_used, overall_score, total_tests,
                       results_summary, detailed_results, sync_timestamp,
                       is_deleted
                FROM user_data
                WHERE user_id = ?
                  AND is_deleted = 0
                ORDER BY sync_timestamp ASC
            ''', (user_id,))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'result_id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': json.loads(row[7]) if row[7] else {},
                'detailed_results': json.loads(row[8]) if row[8] else {},
                'sync_timestamp': row[9],
                'is_deleted': bool(row[10])
            })
        
        db_logger.info(f"Retrieved {len(results)} records for user {user_id}")
        return results
        
    except Exception as e:
        db_logger.error(f"Error getting user data: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_user_data(user_id: int, result_id: str) -> bool:
    """
    Soft delete user data (mark as deleted)
    
    Args:
        user_id: User ID
        result_id: Result ID to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    db_logger.info(f"Deleting result {result_id} for user {user_id}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_data 
            SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND result_id = ? AND is_deleted = 0
        ''', (user_id, result_id))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            db_logger.info(f"Deleted result {result_id} for user {user_id}")
            return True
        else:
            db_logger.warning(f"Result {result_id} not found for user {user_id}")
            return False
        
    except Exception as e:
        db_logger.error(f"Error deleting user data: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Refresh token storage (in-memory for mock, should use Redis in production)
_refresh_tokens = {}


def save_refresh_token(user_id: str, refresh_token: str):
    """
    Save refresh token for user
    
    Args:
        user_id: User ID
        refresh_token: Refresh token string
    """
    from datetime import timedelta
    from wechat_backend.logging_config import db_logger
    
    expiration_time = datetime.now() + timedelta(days=7)  # 7 days validity
    _refresh_tokens[refresh_token] = {
        'user_id': user_id,
        'expires_at': expiration_time,
        'created_at': datetime.now()
    }
    db_logger.debug(f"Refresh token saved for user {user_id}")


def verify_refresh_token(refresh_token: str) -> str:
    """
    Verify refresh token and return user_id if valid
    
    Args:
        refresh_token: Refresh token to verify
        
    Returns:
        str: User ID if valid, None otherwise
    """
    from wechat_backend.logging_config import db_logger
    
    if refresh_token not in _refresh_tokens:
        db_logger.warning(f"Refresh token not found")
        return None
    
    stored = _refresh_tokens[refresh_token]
    
    # Check expiration
    if datetime.now() > stored['expires_at']:
        del _refresh_tokens[refresh_token]
        db_logger.warning(f"Refresh token expired for user {stored['user_id']}")
        return None
    
    db_logger.info(f"Refresh token validated for user {stored['user_id']}")
    return stored['user_id']


def revoke_refresh_token(refresh_token: str):
    """
    Revoke (logout) a refresh token
    
    Args:
        refresh_token: Refresh token to revoke
    """
    from wechat_backend.logging_config import db_logger
    
    if refresh_token in _refresh_tokens:
        del _refresh_tokens[refresh_token]
        db_logger.debug(f"Refresh token revoked")


def revoke_all_user_tokens(user_id: str):
    """
    Revoke all refresh tokens for a user (logout from all devices)
    
    Args:
        user_id: User ID
    """
    from wechat_backend.logging_config import db_logger
    
    tokens_to_revoke = [token for token, data in _refresh_tokens.items() 
                       if data['user_id'] == user_id]
    
    for token in tokens_to_revoke:
        del _refresh_tokens[token]
    
    db_logger.info(f"Revoked {len(tokens_to_revoke)} tokens for user {user_id}")


if __name__ == '__main__':
    # Initialize the database when this module is run directly
    init_db()
    print(f"Database initialized at {DB_PATH}")