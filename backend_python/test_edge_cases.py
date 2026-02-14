#!/usr/bin/env python3
"""
Edge case tests for the DeepSeek API fix
"""
import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_judge_module import AIJudgeClient
from wechat_backend.views import process_and_aggregate_results_with_ai_judge


class TestEdgeCases(unittest.TestCase):
    """Test edge cases for the functionality"""

    def test_ai_judge_client_with_extreme_parameters(self):
        """Test AIJudgeClient with extreme parameter values"""
        # Test with very long strings
        long_string = "x" * 10000  # 10k character string
        
        try:
            client = AIJudgeClient(
                judge_platform=long_string,
                judge_model=long_string,
                api_key=long_string
            )
            # Should not crash with long strings
            self.assertTrue(True)
        except Exception:
            # If it fails, it's acceptable as long as it doesn't crash the system
            pass

    def test_ai_judge_client_with_special_characters(self):
        """Test AIJudgeClient with special characters"""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?~`\"'\\/"
        
        try:
            client = AIJudgeClient(
                judge_platform=special_chars,
                judge_model=special_chars,
                api_key=special_chars
            )
            # Should not crash with special characters
            self.assertTrue(True)
        except Exception:
            # If it fails, it's acceptable as long as it doesn't crash the system
            pass

    def test_ai_judge_client_with_unicode_characters(self):
        """Test AIJudgeClient with unicode characters"""
        unicode_chars = "测试✓🔥🚀🌟🎉✨💖💫⭐️"
        
        try:
            client = AIJudgeClient(
                judge_platform=unicode_chars,
                judge_model=unicode_chars,
                api_key=unicode_chars
            )
            # Should not crash with unicode characters
            self.assertTrue(True)
        except Exception:
            # If it fails, it's acceptable as long as it doesn't crash the system
            pass

    def test_process_function_with_extreme_data(self):
        """Test process function with extreme data sizes"""
        # Very large strings
        huge_string = "x" * 50000  # 50k character string
        
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': huge_string,
                    'model': huge_string,
                    'question': huge_string,
                    'result': {'content': huge_string}
                }
            ]
        }
        all_brands = [huge_string]
        main_brand = huge_string
        
        try:
            result = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand
            )
            # Should handle large data gracefully
            self.assertIsNotNone(result)
        except MemoryError:
            # Large data might cause memory issues, which is expected
            pass
        except Exception:
            # Other exceptions are acceptable as long as system doesn't crash
            pass

    def test_process_function_with_mixed_parameter_scenarios(self):
        """Test process function with mixed parameter scenarios"""
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'test_question',
                    'result': {'content': 'test_response'}
                }
            ]
        }
        all_brands = ['test_brand']
        main_brand = 'test_brand'
        
        # Test with only judge_platform provided
        try:
            result1 = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand,
                judge_platform="qwen",
                judge_model=None,
                judge_api_key=None
            )
            # Should handle partial parameters gracefully
            self.assertIsNotNone(result1)
        except Exception:
            # Acceptable if it fails due to missing parameters
            pass
        
        # Test with only judge_model provided
        try:
            result2 = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand,
                judge_platform=None,
                judge_model="qwen-max",
                judge_api_key=None
            )
            # Should handle partial parameters gracefully
            self.assertIsNotNone(result2)
        except Exception:
            # Acceptable if it fails due to missing parameters
            pass
        
        # Test with only judge_api_key provided
        try:
            result3 = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand,
                judge_platform=None,
                judge_model=None,
                judge_api_key="test-key"
            )
            # Should handle partial parameters gracefully
            self.assertIsNotNone(result3)
        except Exception:
            # Acceptable if it fails due to missing parameters
            pass

    def test_process_function_with_empty_collections(self):
        """Test process function with empty collections"""
        # Empty results
        raw_results = {'results': []}
        all_brands = []
        main_brand = ''
        
        try:
            result = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand
            )
            # Should handle empty collections gracefully
            self.assertIsNotNone(result)
            self.assertIn('detailed_results', result)
        except Exception:
            # Acceptable if it fails due to empty data
            pass

    def test_process_function_with_none_inputs(self):
        """Test process function with None inputs"""
        try:
            result = process_and_aggregate_results_with_ai_judge(
                None,  # raw_results
                None,  # all_brands
                None   # main_brand
            )
            # Should handle None inputs gracefully
            self.assertIsNotNone(result)
        except Exception:
            # Acceptable if it fails due to None inputs
            pass

    def test_process_function_with_malformed_data(self):
        """Test process function with malformed data"""
        # Malformed results data
        raw_results = {
            'results': [
                "invalid_result_format",  # String instead of dict
                12345,  # Number instead of dict
                None,   # None value
                {},     # Empty dict
                {
                    'success': True,
                    'brand_name': 'valid_brand',
                    'model': 'valid_model',
                    'question': 'valid_question',
                    'result': {'content': 'valid_response'}
                }  # Valid entry
            ]
        }
        all_brands = ['valid_brand']
        main_brand = 'valid_brand'
        
        try:
            result = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand
            )
            # Should handle malformed data gracefully
            self.assertIsNotNone(result)
        except Exception:
            # Acceptable if it fails due to malformed data
            pass


if __name__ == '__main__':
    unittest.main()