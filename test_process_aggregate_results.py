#!/usr/bin/env python3
"""
Unit tests for process_and_aggregate_results_with_ai_judge function
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_judge_module import JudgeResult, ConfidenceLevel
from wechat_backend.views import process_and_aggregate_results_with_ai_judge


class TestProcessAndAggregateResults(unittest.TestCase):
    """Unit tests for process_and_aggregate_results_with_ai_judge function"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock the logger
        self.logger_patcher = patch('wechat_backend.views.api_logger')
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.logger_patcher.stop()

    def test_normal_execution_with_judge_params(self):
        """Test normal execution with judge parameters provided"""
        # Mock raw results
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
        
        # Mock the AIJudgeClient
        with patch('wechat_backend.views.AIJudgeClient') as mock_judge_class:
            mock_judge_instance = MagicMock()
            mock_judge_instance.evaluate_response.return_value = JudgeResult(
                accuracy_score=80,
                completeness_score=75,
                sentiment_score=85,
                purity_score=90,
                consistency_score=88,
                judgement="Good response",
                confidence_level=ConfidenceLevel.HIGH
            )
            mock_judge_class.return_value = mock_judge_instance
            
            # Call the function with judge parameters
            result = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand,
                judge_platform="qwen",
                judge_model="qwen-max",
                judge_api_key="test-key"
            )
            
            # Verify the result structure
            self.assertIn('detailed_results', result)
            self.assertIn('main_brand', result)
            self.assertIn('competitiveAnalysis', result)
            
            # Verify that the judge was called
            mock_judge_instance.evaluate_response.assert_called_once()

    def test_execution_without_judge_params(self):
        """Test execution without judge parameters (should skip AI evaluation)"""
        # Mock raw results
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
        
        # Call the function without judge parameters
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Verify the result structure
        self.assertIn('detailed_results', result)
        self.assertIn('main_brand', result)
        self.assertIn('competitiveAnalysis', result)
        
        # Verify that the detailed results have default scores (0) when no judge is used
        detailed_result = result['detailed_results'][0]
        self.assertEqual(detailed_result['authority_score'], 0)
        self.assertEqual(detailed_result['visibility_score'], 0)
        self.assertEqual(detailed_result['sentiment_score'], 0)
        self.assertEqual(detailed_result['purity_score'], 0)
        self.assertEqual(detailed_result['consistency_score'], 0)
        self.assertEqual(detailed_result['score'], 0)

    def test_execution_with_empty_judge_params(self):
        """Test execution with empty judge parameters"""
        # Mock raw results
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
        
        # Call the function with empty judge parameters
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand,
            judge_platform="",
            judge_model="",
            judge_api_key=""
        )
        
        # Verify the result structure
        self.assertIn('detailed_results', result)
        self.assertIn('main_brand', result)
        self.assertIn('competitiveAnalysis', result)

    def test_execution_with_partial_judge_params(self):
        """Test execution with partial judge parameters"""
        # Mock raw results
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
        
        # Call the function with partial judge parameters
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand,
            judge_platform="qwen",  # Provided
            judge_model=None,       # Not provided
            judge_api_key="test-key"  # Provided
        )
        
        # Verify the result structure
        self.assertIn('detailed_results', result)
        self.assertIn('main_brand', result)
        self.assertIn('competitiveAnalysis', result)

    def test_execution_with_invalid_raw_results_format(self):
        """Test execution with invalid raw results format"""
        # Test with empty results
        raw_results = {'results': []}
        all_brands = ['test_brand']
        main_brand = 'test_brand'
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should still return a valid structure
        self.assertIn('detailed_results', result)
        self.assertIn('main_brand', result)
        self.assertIn('competitiveAnalysis', result)
        self.assertEqual(len(result['detailed_results']), 0)

    def test_execution_with_malformed_result_items(self):
        """Test execution with malformed result items"""
        # Mock raw results with malformed data
        raw_results = {
            'results': [
                "invalid_item",  # String instead of dict
                None,  # None value
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'test_question',
                    'result': {'content': 'test_response'}
                }  # Valid item
            ]
        }
        
        all_brands = ['test_brand']
        main_brand = 'test_brand'
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should handle malformed items gracefully
        self.assertIn('detailed_results', result)
        # Only the valid item should be processed
        self.assertEqual(len(result['detailed_results']), 1)

    def test_execution_with_failed_results(self):
        """Test execution with failed results"""
        # Mock raw results with failed items
        raw_results = {
            'results': [
                {
                    'success': False,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'test_question',
                    'error': 'Some error occurred'
                }
            ]
        }
        
        all_brands = ['test_brand']
        main_brand = 'test_brand'
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should handle failed results
        self.assertIn('detailed_results', result)
        detailed_result = result['detailed_results'][0]
        self.assertFalse(detailed_result['success'])
        self.assertEqual(detailed_result['score'], 0)

    def test_main_brand_not_in_results(self):
        """Test when main brand is not in the results"""
        # Mock raw results with different brand
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'different_brand',
                    'model': 'test_model',
                    'question': 'test_question',
                    'result': {'content': 'test_response'}
                }
            ]
        }
        
        all_brands = ['different_brand']
        main_brand = 'main_brand'  # Different from results
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should handle when main brand is not in results
        self.assertIn('detailed_results', result)
        self.assertIn('main_brand', result)
        # The main_brand result should have default values
        main_brand_data = result['main_brand']
        self.assertEqual(main_brand_data['overallScore'], 0)
        self.assertEqual(main_brand_data['overallGrade'], 'D')


if __name__ == '__main__':
    unittest.main()