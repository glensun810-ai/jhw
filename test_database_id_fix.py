#!/usr/bin/env python3
"""
Unit tests for the database ID auto-increment fix
"""
import unittest
import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from wechat_backend.database import init_db, save_test_record, get_user_test_history, get_test_record_by_id


class TestDatabaseAutoIncrementFix(unittest.TestCase):
    """Unit tests for the database ID auto-increment fix"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for the test database
        self.test_dir = tempfile.mkdtemp()
        self.original_db_path = os.path.join(os.path.dirname(__file__), 'wechat_backend', 'database.db')
        
        # Backup original database if it exists
        if os.path.exists(self.original_db_path):
            shutil.copy2(self.original_db_path, self.test_dir)
        
        # Change to test directory
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize test database
        init_db()

    def tearDown(self):
        """Clean up after each test method."""
        # Remove test database
        test_db_path = os.path.join(self.test_dir, 'database.db')
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        
        # Restore original working directory
        os.chdir(self.original_cwd)
        
        # Clean up temp directory
        shutil.rmtree(self.test_dir)

    def test_normal_auto_increment_sequence(self):
        """Test that IDs are sequential within a single test run"""
        # Save multiple records
        record_ids = []
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
            record_ids.append(record_id)
        
        # Verify IDs are sequential (each ID should be 1 more than the previous)
        for i in range(1, len(record_ids)):
            self.assertEqual(record_ids[i], record_ids[i-1] + 1, 
                           f"ID {record_ids[i]} should be {record_ids[i-1] + 1}")

    def test_single_record_positive_id(self):
        """Test single record gets a positive ID (not necessarily 1)"""
        record_id = save_test_record(
            user_openid="single_user",
            brand_name="Single Brand",
            ai_models_used=["Model A"],
            questions_used=["Question A"],
            overall_score=85.0,
            total_tests=5,
            results_summary={"metric": "value"},
            detailed_results=[{"result": "detail"}]
        )
        
        self.assertGreater(record_id, 0, f"Expected positive ID, got {record_id}")

    def test_multiple_users_different_brands(self):
        """Test auto-increment with different users and brands"""
        # Save records for different users and brands
        record1_id = save_test_record(
            user_openid="user_alpha",
            brand_name="Brand Alpha",
            ai_models_used=["Model X"],
            questions_used=["Q1"],
            overall_score=90.0,
            total_tests=3,
            results_summary={"score": 90},
            detailed_results=[{"response": "A"}]
        )
        
        record2_id = save_test_record(
            user_openid="user_beta", 
            brand_name="Brand Beta",
            ai_models_used=["Model Y"],
            questions_used=["Q2"],
            overall_score=85.0,
            total_tests=4,
            results_summary={"score": 85},
            detailed_results=[{"response": "B"}]
        )
        
        # Both should have positive, unique IDs
        self.assertGreater(record1_id, 0, f"First record should have positive ID, got {record1_id}")
        self.assertGreater(record2_id, 0, f"Second record should have positive ID, got {record2_id}")
        self.assertNotEqual(record1_id, record2_id, "Records should have different IDs")
        self.assertEqual(record2_id, record1_id + 1, "Second record should have ID one greater than first")

    def test_retrieve_records_by_correct_ids(self):
        """Test that records can be retrieved by their correct auto-generated IDs"""
        # Save a record
        record_id = save_test_record(
            user_openid="retrieve_test",
            brand_name="Retrieve Brand",
            ai_models_used=["Model Z"],
            questions_used=["Q3"],
            overall_score=75.0,
            total_tests=2,
            results_summary={"score": 75},
            detailed_results=[{"response": "C"}]
        )
        
        # Retrieve the record by ID
        retrieved_record = get_test_record_by_id(record_id)
        
        self.assertIsNotNone(retrieved_record, f"Could not retrieve record with ID {record_id}")
        self.assertEqual(retrieved_record['id'], record_id, f"Retrieved record ID mismatch: expected {record_id}, got {retrieved_record['id']}")
        self.assertEqual(retrieved_record['brand_name'], "Retrieve Brand", "Brand name mismatch")

    def test_large_number_of_records(self):
        """Test auto-increment with a larger number of records"""
        num_records = 10  # Reduced for faster testing
        record_ids = []
        
        for i in range(num_records):
            record_id = save_test_record(
                user_openid=f"user_{i}",
                brand_name=f"Brand_{i}",
                ai_models_used=[f"Model_{i}"],
                questions_used=[f"Q{i}"],
                overall_score=80.0,
                total_tests=1,
                results_summary={"test": i},
                detailed_results=[{"idx": i}]
            )
            record_ids.append(record_id)
        
        # Verify IDs are sequential
        for i in range(1, len(record_ids)):
            self.assertEqual(record_ids[i], record_ids[i-1] + 1, 
                           f"ID {record_ids[i]} should be {record_ids[i-1] + 1}")

    def test_consecutive_saves_after_retrieval(self):
        """Test that auto-increment continues correctly after retrieval operations"""
        # Save first record
        id1 = save_test_record(
            user_openid="cont_test_1",
            brand_name="Cont Brand 1",
            ai_models_used=["Model A"],
            questions_used=["Q1"],
            overall_score=80.0,
            total_tests=1,
            results_summary={"test": 1},
            detailed_results=[{"idx": 1}]
        )
        
        # Retrieve a record (this shouldn't affect auto-increment)
        retrieved = get_test_record_by_id(id1)
        self.assertIsNotNone(retrieved)
        
        # Save next record - should get next ID
        id2 = save_test_record(
            user_openid="cont_test_2",
            brand_name="Cont Brand 2",
            ai_models_used=["Model B"],
            questions_used=["Q2"],
            overall_score=85.0,
            total_tests=1,
            results_summary={"test": 2},
            detailed_results=[{"idx": 2}]
        )
        
        # Save third record - should get next ID
        id3 = save_test_record(
            user_openid="cont_test_3",
            brand_name="Cont Brand 3",
            ai_models_used=["Model C"],
            questions_used=["Q3"],
            overall_score=90.0,
            total_tests=1,
            results_summary={"test": 3},
            detailed_results=[{"idx": 3}]
        )
        
        self.assertGreater(id1, 0, f"Expected positive ID, got {id1}")
        self.assertEqual(id2, id1 + 1, f"Expected ID {id1 + 1}, got {id2}")
        self.assertEqual(id3, id2 + 1, f"Expected ID {id2 + 1}, got {id3}")


class TestDatabaseAbnormalScenarios(unittest.TestCase):
    """Test abnormal scenarios for the database functionality"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        init_db()

    def tearDown(self):
        """Clean up after each test method."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_save_with_invalid_user_openid(self):
        """Test saving with invalid user_openid (should raise exception in validation)"""
        from wechat_backend.security.sql_protection import sql_protector
        
        # Test with obviously malicious input
        with self.assertRaises(ValueError):
            save_test_record(
                user_openid="'; DROP TABLE test_records; --",  # SQL injection attempt
                brand_name="Test Brand",
                ai_models_used=["Model A"],
                questions_used=["Q1"],
                overall_score=80.0,
                total_tests=1,
                results_summary={"test": 1},
                detailed_results=[{"idx": 1}]
            )

    def test_save_with_none_values(self):
        """Test saving with None values where not allowed"""
        # This should work for optional fields but test behavior
        record_id = save_test_record(
            user_openid="none_test_user",
            brand_name="None Test Brand",
            ai_models_used=None,  # This should be converted to JSON
            questions_used=None,  # This should be converted to JSON
            overall_score=None,  # This should be stored as NULL
            total_tests=None,  # This should be stored as NULL
            results_summary=None,  # This should be converted to JSON
            detailed_results=None  # This should be converted to JSON
        )
        
        # Should still get a valid auto-incremented ID
        self.assertGreater(record_id, 0, f"Expected positive ID, got {record_id}")
        
        # Retrieve and verify the record was saved
        retrieved = get_test_record_by_id(record_id)
        self.assertIsNotNone(retrieved)

    def test_retrieve_nonexistent_record(self):
        """Test retrieving a record that doesn't exist"""
        retrieved = get_test_record_by_id(999999)  # Very high ID that shouldn't exist
        self.assertIsNone(retrieved, "Expected None for non-existent record")

    def test_retrieve_with_negative_id(self):
        """Test retrieving with negative ID (should raise exception or return None)"""
        with self.assertRaises(ValueError):
            get_test_record_by_id(-1)  # Negative ID should raise ValueError

    def test_retrieve_with_zero_id(self):
        """Test retrieving with zero ID (should return None as per current implementation)"""
        # Current implementation returns None for non-existent IDs (including 0)
        retrieved = get_test_record_by_id(0)
        self.assertIsNone(retrieved, "Expected None for zero ID")


class TestDatabaseEdgeCases(unittest.TestCase):
    """Test edge cases for the database functionality"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        init_db()

    def tearDown(self):
        """Clean up after each test method."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_empty_strings_and_lists(self):
        """Test saving with empty strings and lists"""
        record_id = save_test_record(
            user_openid="empty_test",
            brand_name="",  # Empty brand name
            ai_models_used=[],  # Empty list
            questions_used=[],  # Empty list
            overall_score=0.0,  # Zero score
            total_tests=0,  # Zero tests
            results_summary={},  # Empty dict
            detailed_results=[]  # Empty list
        )
        
        self.assertGreater(record_id, 0, f"Expected positive ID, got {record_id}")
        
        # Retrieve and verify
        retrieved = get_test_record_by_id(record_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['id'], record_id)

    def test_extremely_long_strings(self):
        """Test saving with extremely long strings"""
        long_string = "x" * 10000  # 10k character string
        
        record_id = save_test_record(
            user_openid=f"long_test_{long_string[:100]}",  # Truncate for user_openid
            brand_name=long_string,
            ai_models_used=[long_string],
            questions_used=[long_string],
            overall_score=50.0,
            total_tests=1,
            results_summary={long_string[:50]: long_string[:50]},  # Use substrings as keys
            detailed_results=[{long_string[:50]: long_string[:50]}]
        )
        
        self.assertGreater(record_id, 0, f"Expected positive ID, got {record_id}")
        
        # Retrieve and verify
        retrieved = get_test_record_by_id(record_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['id'], record_id)

    def test_extreme_numeric_values(self):
        """Test saving with extreme numeric values"""
        record_id = save_test_record(
            user_openid="numeric_test",
            brand_name="Numeric Test",
            ai_models_used=["Model A"],
            questions_used=["Q1"],
            overall_score=999999.99,  # Very high score
            total_tests=999999,  # Very high count
            results_summary={"high_num": 999999},
            detailed_results=[{"high_num": 999999}]
        )
        
        self.assertGreater(record_id, 0, f"Expected positive ID, got {record_id}")
        
        # Retrieve and verify
        retrieved = get_test_record_by_id(record_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['id'], record_id)

    def test_unicode_characters(self):
        """Test saving with unicode characters"""
        unicode_brand = "测试品牌✓🔥🚀"
        unicode_user = "用户测试_αβγ"
        
        record_id = save_test_record(
            user_openid=unicode_user,
            brand_name=unicode_brand,
            ai_models_used=["Модель", "モデル", "مودل"],  # Cyrillic, Japanese, Arabic
            questions_used=["测试?", "Test?", "Тест?"],
            overall_score=88.5,
            total_tests=3,
            results_summary={"测试": "value", "test": "значение"},
            detailed_results=[{"response": "回答", "reply": "返事"}]
        )
        
        self.assertGreater(record_id, 0, f"Expected positive ID, got {record_id}")
        
        # Retrieve and verify
        retrieved = get_test_record_by_id(record_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['id'], record_id)
        self.assertEqual(retrieved['brand_name'], unicode_brand)

    def test_save_immediately_after_init(self):
        """Test saving immediately after database initialization"""
        # This tests the edge case of first insertion
        record_id = save_test_record(
            user_openid="first_user",
            brand_name="First Brand",
            ai_models_used=["First Model"],
            questions_used=["First Q"],
            overall_score=100.0,
            total_tests=1,
            results_summary={"first": True},
            detailed_results=[{"first": True}]
        )
        
        # Should get a positive ID (not necessarily 1 in this test context)
        self.assertGreater(record_id, 0, f"Expected positive ID for first record, got {record_id}")

    def test_multiple_saves_in_single_operation(self):
        """Test multiple saves in quick succession"""
        ids = []
        for i in range(5):  # Reduced for faster testing
            record_id = save_test_record(
                user_openid=f"quick_user_{i}",
                brand_name=f"Quick Brand {i}",
                ai_models_used=[f"Quick Model {i}"],
                questions_used=[f"Quick Q {i}"],
                overall_score=80.0 + i,
                total_tests=i + 1,
                results_summary={"idx": i},
                detailed_results=[{"idx": i}]
            )
            ids.append(record_id)
        
        # Verify IDs are sequential
        for i in range(1, len(ids)):
            self.assertEqual(ids[i], ids[i-1] + 1, 
                           f"ID {ids[i]} should be {ids[i-1] + 1}")


class TestBackwardCompatibility(unittest.TestCase):
    """Test that existing functionality remains unaffected"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        init_db()

    def tearDown(self):
        """Clean up after each test method."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_get_user_test_history_still_works(self):
        """Test that get_user_test_history still works with the new ID system"""
        # Save several records for the same user
        saved_ids = []
        for i in range(3):
            record_id = save_test_record(
                user_openid="history_user_specific",
                brand_name=f"History Brand {i}",
                ai_models_used=[f"Model {i}"],
                questions_used=[f"Q{i}"],
                overall_score=80.0 + i,
                total_tests=2,
                results_summary={"score": 80 + i},
                detailed_results=[{"result": f"result_{i}"}]
            )
            saved_ids.append(record_id)

        # Retrieve user history for this specific user
        history = get_user_test_history("history_user_specific", limit=10, offset=0)

        # Should get 3 records for this specific user
        self.assertEqual(len(history), 3, f"Expected 3 history records, got {len(history)}")

        # Verify the saved IDs are in the retrieved records
        retrieved_ids = [record['id'] for record in history]
        for saved_id in saved_ids:
            self.assertIn(saved_id, retrieved_ids, f"Saved ID {saved_id} not found in history")

    def test_all_functions_work_together(self):
        """Test that all database functions work together properly"""
        # Save a record
        record_id = save_test_record(
            user_openid="integration_user_unique",
            brand_name="Integration Brand",
            ai_models_used=["Integrated Model"],
            questions_used=["Integrated Q"],
            overall_score=85.0,
            total_tests=5,
            results_summary={"integration": True},
            detailed_results=[{"success": True}]
        )

        # Verify the ID is positive
        self.assertGreater(record_id, 0, f"Expected positive ID, got {record_id}")

        # Retrieve by ID
        by_id = get_test_record_by_id(record_id)
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id['id'], record_id)

        # Retrieve from user history for this specific user
        history = get_user_test_history("integration_user_unique")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['id'], record_id)

    def test_database_init_remains_unchanged(self):
        """Test that database initialization remains unchanged"""
        # The init_db function should work as before
        # Create a fresh database
        if os.path.exists('database.db'):
            os.remove('database.db')
        
        init_db()
        
        # Verify tables exist by attempting to save a record
        record_id = save_test_record(
            user_openid="init_test",
            brand_name="Init Brand",
            ai_models_used=["Init Model"],
            questions_used=["Init Q"],
            overall_score=90.0,
            total_tests=1,
            results_summary={"init": True},
            detailed_results=[{"verified": True}]
        )
        
        self.assertGreater(record_id, 0, "Database initialization should enable saving records")

    def test_no_more_id_zero_issue(self):
        """Test that the original ID=0 issue is fixed"""
        # Save multiple records and verify none have ID=0
        for i in range(5):
            record_id = save_test_record(
                user_openid=f"zero_test_{i}",
                brand_name=f"Zero Test Brand {i}",
                ai_models_used=[f"Model {i}"],
                questions_used=[f"Q{i}"],
                overall_score=80.0,
                total_tests=1,
                results_summary={"test": i},
                detailed_results=[{"idx": i}]
            )
            
            self.assertNotEqual(record_id, 0, f"Record {i+1} should not have ID=0, got {record_id}")
            self.assertGreater(record_id, 0, f"Record {i+1} should have positive ID, got {record_id}")


if __name__ == '__main__':
    unittest.main()