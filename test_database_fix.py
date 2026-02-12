#!/usr/bin/env python3
"""
Test script to verify the database ID fix
"""
import os
import sys
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_database_fix():
    """Test that the database ID fix works correctly"""
    print("Testing database ID fix...")
    
    # Remove existing database file to start fresh
    db_path = "database.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")
    
    # Import and initialize database
    from wechat_backend.database import init_db, save_test_record, get_test_record_by_id, get_user_test_history
    
    # Initialize the database
    init_db()
    print("Database initialized")
    
    # Test multiple record insertions to verify auto-increment
    test_records = [
        {
            "user_openid": "test_user_1",
            "brand_name": "Test Brand 1",
            "ai_models_used": ["Model A", "Model B"],
            "questions_used": ["Question 1", "Question 2"],
            "overall_score": 85.5,
            "total_tests": 10,
            "results_summary": {"metric1": "value1"},
            "detailed_results": [{"result": "detail1"}]
        },
        {
            "user_openid": "test_user_2", 
            "brand_name": "Test Brand 2",
            "ai_models_used": ["Model C", "Model D"],
            "questions_used": ["Question 3", "Question 4"],
            "overall_score": 92.0,
            "total_tests": 8,
            "results_summary": {"metric2": "value2"},
            "detailed_results": [{"result": "detail2"}]
        },
        {
            "user_openid": "test_user_3",
            "brand_name": "Test Brand 3", 
            "ai_models_used": ["Model E"],
            "questions_used": ["Question 5"],
            "overall_score": 78.5,
            "total_tests": 5,
            "results_summary": {"metric3": "value3"},
            "detailed_results": [{"result": "detail3"}]
        }
    ]
    
    saved_ids = []
    
    for i, record in enumerate(test_records):
        print(f"\nSaving test record {i+1}...")
        record_id = save_test_record(
            user_openid=record["user_openid"],
            brand_name=record["brand_name"],
            ai_models_used=record["ai_models_used"],
            questions_used=record["questions_used"],
            overall_score=record["overall_score"],
            total_tests=record["total_tests"],
            results_summary=record["results_summary"],
            detailed_results=record["detailed_results"]
        )
        
        print(f"Record {i+1} saved with ID: {record_id}")
        saved_ids.append(record_id)
        
        # Verify the record can be retrieved with the correct ID
        retrieved_record = get_test_record_by_id(record_id)
        if retrieved_record:
            print(f"  ✓ Record retrieved successfully with ID: {retrieved_record['id']}")
            if retrieved_record['id'] != record_id:
                print(f"  ❌ Mismatch: saved ID {record_id} vs retrieved ID {retrieved_record['id']}")
            else:
                print(f"  ✓ IDs match correctly")
        else:
            print(f"  ❌ Failed to retrieve record with ID: {record_id}")
    
    print(f"\nSummary of saved IDs: {saved_ids}")
    
    # Check if IDs are incrementing properly (should be 1, 2, 3, ...)
    expected_ids = list(range(1, len(test_records) + 1))
    if saved_ids == expected_ids:
        print("✅ SUCCESS: IDs are properly auto-incrementing!")
        print(f"   Expected: {expected_ids}")
        print(f"   Actual:   {saved_ids}")
        return True
    else:
        print("❌ FAILURE: IDs are not auto-incrementing properly!")
        print(f"   Expected: {expected_ids}")
        print(f"   Actual:   {saved_ids}")
        
        # Check if any IDs are 0 (the original problem)
        zero_ids = [id for id in saved_ids if id == 0]
        if zero_ids:
            print(f"   Found {len(zero_ids)} records with ID=0 (original bug)")
        
        return False

def check_table_schema():
    """Check the table schema to ensure AUTOINCREMENT is present"""
    import sqlite3
    
    db_path = "database.db"
    if not os.path.exists(db_path):
        print("Database doesn't exist, initializing...")
        from wechat_backend.database import init_db
        init_db()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(test_records)")
    columns = cursor.fetchall()
    
    print("\nTable schema for 'test_records':")
    for col in columns:
        cid, name, col_type, not_null, default_val, pk = col
        print(f"  {name}: {col_type}, PK={pk}")
    
    # Check if the id column is properly set up as auto-incrementing primary key
    id_column = next((col for col in columns if col[1] == 'id'), None)
    if id_column:
        cid, name, col_type, not_null, default_val, pk = id_column
        if pk == 1:  # Primary key flag
            print("✅ ID column is set as primary key")
        else:
            print("❌ ID column is NOT set as primary key")
    
    conn.close()

if __name__ == "__main__":
    print("="*60)
    print("DATABASE ID FIX VERIFICATION")
    print("="*60)
    
    # Check table schema first
    check_table_schema()
    
    # Test the fix
    success = test_database_fix()
    
    print("\n" + "="*60)
    if success:
        print("🎉 DATABASE FIX VERIFICATION: PASSED")
        print("The ID auto-increment issue has been resolved!")
    else:
        print("💥 DATABASE FIX VERIFICATION: FAILED") 
        print("The ID auto-increment issue still exists!")
    print("="*60)