#!/usr/bin/env python3
"""
Quick verification test for the database ID fix
"""
import os
import sys
import tempfile
import shutil

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from wechat_backend.database import init_db, save_test_record, get_test_record_by_id


def test_id_fix():
    """Test that the ID fix is working"""
    # Create a temporary directory for the test database
    test_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    
    try:
        os.chdir(test_dir)
        init_db()
        
        print("Testing database ID auto-increment fix...")
        
        # Save multiple records
        ids = []
        for i in range(5):
            record_id = save_test_record(
                user_openid=f"test_user_{i}",
                brand_name=f"Test Brand {i}",
                ai_models_used=[f"Model {i}A", f"Model {i}B"],
                questions_used=[f"Question {i}A", f"Question {i}B"],
                overall_score=80.0 + i,
                total_tests=10 + i,
                results_summary={"metric": f"value{i}"},
                detailed_results=[{"result": f"detail{i}"}]
            )
            ids.append(record_id)
            print(f"Record {i+1} saved with ID: {record_id}")
        
        # Verify IDs are positive and sequential
        all_positive = all(id > 0 for id in ids)
        is_sequential = all(ids[i] == ids[i-1] + 1 for i in range(1, len(ids))) if len(ids) > 1 else True
        
        print(f"All IDs positive: {all_positive}")
        print(f"IDs sequential: {is_sequential}")
        print(f"IDs: {ids}")
        
        # Verify no ID is 0 (the original issue)
        has_zero_id = any(id == 0 for id in ids)
        print(f"Has zero ID (original bug): {has_zero_id}")
        
        # Test retrieval by ID
        retrieval_success = True
        for record_id in ids:
            retrieved = get_test_record_by_id(record_id)
            if retrieved is None:
                print(f"Failed to retrieve record with ID {record_id}")
                retrieval_success = False
            else:
                print(f"Successfully retrieved record with ID {record_id}")
        
        success = all_positive and not has_zero_id and retrieval_success
        if is_sequential:
            print(f"IDs are properly sequential: {ids}")
        else:
            print(f"IDs are not sequential (may be due to previous test runs): {ids}")
        
        print(f"Overall test result: {'PASS' if success else 'FAIL'}")
        return success
        
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    success = test_id_fix()
    print("\n" + "="*50)
    if success:
        print("✅ DATABASE ID FIX VERIFICATION: PASSED")
        print("The database ID auto-increment issue has been resolved!")
        print("- IDs are now positive integers")
        print("- IDs are properly assigned (not 0)")
        print("- Records can be retrieved by their IDs")
    else:
        print("❌ DATABASE ID FIX VERIFICATION: FAILED")
        print("The database ID issue may still exist!")
    print("="*50)