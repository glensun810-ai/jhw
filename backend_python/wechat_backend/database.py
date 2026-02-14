"""
Database schema for GEO Content Quality Validator
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

from .logging_config import db_logger
from .security.sql_protection import SafeDatabaseQuery, sql_protector

DB_PATH = Path(__file__).parent.parent / 'database.db'

def init_db():
    """Initialize the database with required tables"""
    db_logger.info(f"Initializing database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE NOT NULL,
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
    """Save a test record to the database"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(brand_name):
        raise ValueError("Invalid brand_name")

    db_logger.info(f"Saving test record for user: {user_openid}, brand: {brand_name}")

    # Use safe database query
    safe_query = SafeDatabaseQuery(DB_PATH)

    # Get user ID or create new user
    user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

    if user_rows:
        user_id = user_rows[0][0]
        db_logger.debug(f"Found existing user with ID: {user_id}")
    else:
        # Create new user
        safe_query.execute_query('INSERT INTO users (openid) VALUES (?)', (user_openid,))
        # Get the new user ID
        user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))
        user_id = user_rows[0][0]
        db_logger.debug(f"Created new user with ID: {user_id}")

    # Convert lists/dicts to JSON strings
    ai_models_json = json.dumps(ai_models_used)
    questions_json = json.dumps(questions_used)
    results_summary_json = json.dumps(results_summary)
    detailed_results_json = json.dumps(detailed_results)

    # Insert test record and get the inserted record ID in one connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO test_records
        (user_id, brand_name, ai_models_used, questions_used, overall_score, total_tests, results_summary, detailed_results)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, brand_name, ai_models_json, questions_json, overall_score, total_tests, results_summary_json, detailed_results_json))

    record_id = cursor.lastrowid  # Get the auto-generated ID
    conn.commit()
    conn.close()

    db_logger.info(f"Test record saved successfully with ID: {record_id}")

    return record_id

def get_user_test_history(user_openid, limit=20, offset=0):
    """Get test history for a specific user"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")

    # Validate numeric inputs
    if not isinstance(limit, int) or not isinstance(offset, int) or limit < 0 or offset < 0:
        raise ValueError("Limit and offset must be non-negative integers")

    db_logger.info(f"Retrieving test history for user: {user_openid}, limit: {limit}, offset: {offset}")

    # Use safe database query
    safe_query = SafeDatabaseQuery(DB_PATH)

    # Get user ID
    user_rows = safe_query.execute_query('SELECT id FROM users WHERE openid = ?', (user_openid,))

    if not user_rows:
        db_logger.debug(f"No user found with openid: {user_openid}")
        return []

    user_id = user_rows[0][0]
    db_logger.debug(f"Found user with ID: {user_id}")

    # Get test records for this user
    # Using safe parameterized query with validated integer inputs
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
    """Get a specific test record by ID"""
    # Validate inputs to prevent SQL injection
    if not isinstance(record_id, int) or record_id < 0:
        raise ValueError("Record ID must be a non-negative integer")

    db_logger.info(f"Retrieving test record with ID: {record_id}")

    # Use safe database query
    safe_query = SafeDatabaseQuery(DB_PATH)

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
        db_logger.info(f"Successfully retrieved test record with ID: {record_id}")
    else:
        record = None
        db_logger.warning(f"No test record found with ID: {record_id}")

    return record


def save_user_preference(user_openid, preference_key, preference_value):
    """Save a user preference"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(preference_key):
        raise ValueError("Invalid preference_key")

    db_logger.info(f"Saving user preference for user {user_openid}, key: {preference_key}")

    # Use safe database query
    safe_query = SafeDatabaseQuery(DB_PATH)

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
    """Get a user preference"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")
    if not sql_protector.validate_input(preference_key):
        raise ValueError("Invalid preference_key")

    db_logger.info(f"Retrieving user preference for user {user_openid}, key: {preference_key}")

    # Use safe database query
    safe_query = SafeDatabaseQuery(DB_PATH)

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
        # Try to parse as JSON, if it fails return as string
        try:
            return json.loads(pref_value_str)
        except (json.JSONDecodeError, TypeError):
            return pref_value_str
    else:
        return default_value


def get_all_user_preferences(user_openid):
    """Get all preferences for a user"""
    # Validate inputs to prevent SQL injection
    if not sql_protector.validate_input(user_openid):
        raise ValueError("Invalid user_openid")

    db_logger.info(f"Retrieving all preferences for user {user_openid}")

    # Use safe database query
    safe_query = SafeDatabaseQuery(DB_PATH)

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


if __name__ == '__main__':
    # Initialize the database when this module is run directly
    init_db()
    print(f"Database initialized at {DB_PATH}")