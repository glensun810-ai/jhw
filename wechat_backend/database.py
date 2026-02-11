"""
Database schema for GEO Content Quality Validator
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

from .logging_config import db_logger

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

    conn.commit()
    conn.close()
    db_logger.info("Database initialization completed")

def save_test_record(user_openid, brand_name, ai_models_used, questions_used, overall_score, total_tests, results_summary, detailed_results):
    """Save a test record to the database"""
    db_logger.info(f"Saving test record for user: {user_openid}, brand: {brand_name}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get user ID or create new user
    cursor.execute('SELECT id FROM users WHERE openid = ?', (user_openid,))
    user_row = cursor.fetchone()

    if user_row:
        user_id = user_row[0]
        db_logger.debug(f"Found existing user with ID: {user_id}")
    else:
        cursor.execute('INSERT INTO users (openid) VALUES (?)', (user_openid,))
        user_id = cursor.lastrowid
        db_logger.debug(f"Created new user with ID: {user_id}")

    # Convert lists/dicts to JSON strings
    ai_models_json = json.dumps(ai_models_used)
    questions_json = json.dumps(questions_used)
    results_summary_json = json.dumps(results_summary)
    detailed_results_json = json.dumps(detailed_results)

    # Insert test record
    cursor.execute('''
        INSERT INTO test_records
        (user_id, brand_name, ai_models_used, questions_used, overall_score, total_tests, results_summary, detailed_results)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, brand_name, ai_models_json, questions_json, overall_score, total_tests, results_summary_json, detailed_results_json))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    db_logger.info(f"Test record saved successfully with ID: {record_id}")

    return record_id

def get_user_test_history(user_openid, limit=20, offset=0):
    """Get test history for a specific user"""
    db_logger.info(f"Retrieving test history for user: {user_openid}, limit: {limit}, offset: {offset}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get user ID
    cursor.execute('SELECT id FROM users WHERE openid = ?', (user_openid,))
    user_row = cursor.fetchone()

    if not user_row:
        db_logger.debug(f"No user found with openid: {user_openid}")
        conn.close()
        return []

    user_id = user_row[0]
    db_logger.debug(f"Found user with ID: {user_id}")

    # Get test records for this user
    cursor.execute('''
        SELECT id, brand_name, test_date, ai_models_used, questions_used,
               overall_score, total_tests, results_summary
        FROM test_records
        WHERE user_id = ?
        ORDER BY test_date DESC
        LIMIT ? OFFSET ?
    ''', (user_id, limit, offset))

    records = []
    for row in cursor.fetchall():
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
    conn.close()
    return records

def get_test_record_by_id(record_id):
    """Get a specific test record by ID"""
    db_logger.info(f"Retrieving test record with ID: {record_id}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, brand_name, test_date, ai_models_used, questions_used,
               overall_score, total_tests, results_summary, detailed_results
        FROM test_records
        WHERE id = ?
    ''', (record_id,))

    row = cursor.fetchone()
    if row:
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

    conn.close()
    return record


def save_user_preference(user_openid, preference_key, preference_value):
    """Save a user preference"""
    db_logger.info(f"Saving user preference for user {user_openid}, key: {preference_key}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # First, get or create user ID based on openid
    cursor.execute('SELECT id FROM users WHERE openid = ?', (user_openid,))
    user_row = cursor.fetchone()

    if user_row:
        user_id = user_row[0]
    else:
        # Create new user if not exists
        cursor.execute('INSERT INTO users (openid) VALUES (?)', (user_openid,))
        user_id = cursor.lastrowid

    # Convert preference value to JSON string if it's a dict/list
    if isinstance(preference_value, (dict, list)):
        pref_value_str = json.dumps(preference_value)
    else:
        pref_value_str = str(preference_value)

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO user_preferences
            (user_id, preference_key, preference_value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, preference_key, pref_value_str))

        conn.commit()
        db_logger.info(f"User preference saved successfully: {preference_key}")
    except Exception as e:
        db_logger.error(f"Error saving user preference: {e}")
        raise
    finally:
        conn.close()


def get_user_preference(user_openid, preference_key, default_value=None):
    """Get a user preference"""
    db_logger.info(f"Retrieving user preference for user {user_openid}, key: {preference_key}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get user ID based on openid
    cursor.execute('SELECT id FROM users WHERE openid = ?', (user_openid,))
    user_row = cursor.fetchone()

    if not user_row:
        return default_value

    user_id = user_row[0]

    cursor.execute('''
        SELECT preference_value
        FROM user_preferences
        WHERE user_id = ? AND preference_key = ?
    ''', (user_id, preference_key))

    row = cursor.fetchone()
    conn.close()

    if row:
        pref_value_str = row[0]
        # Try to parse as JSON, if it fails return as string
        try:
            return json.loads(pref_value_str)
        except (json.JSONDecodeError, TypeError):
            return pref_value_str
    else:
        return default_value


def get_all_user_preferences(user_openid):
    """Get all preferences for a user"""
    db_logger.info(f"Retrieving all preferences for user {user_openid}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get user ID based on openid
    cursor.execute('SELECT id FROM users WHERE openid = ?', (user_openid,))
    user_row = cursor.fetchone()

    if not user_row:
        return {}

    user_id = user_row[0]

    cursor.execute('''
        SELECT preference_key, preference_value
        FROM user_preferences
        WHERE user_id = ?
    ''', (user_id,))

    rows = cursor.fetchall()
    conn.close()

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