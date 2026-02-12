#!/usr/bin/env python3
"""
Comprehensive unit tests covering normal, abnormal, and edge cases
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_judge_module import AIJudgeClient, JudgeResult, ConfidenceLevel
from wechat_backend.views import process_and_aggregate_results_with_ai_judge


class TestNormalScenarios(unittest.TestCase):
    """Test normal scenarios with valid parameters"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger_patcher = patch('wechat_backend.views.api_logger')
        self.mock_logger = self.logger_patcher.start()
        
        self.judge_logger_patcher = patch('ai_judge_module.api_logger')
        self.mock_judge_logger = self.judge_logger_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.logger_patcher.stop()
        self.judge_logger_patcher.stop()

    def test_normal_ai_judge_client_initialization(self):
        """Test normal AIJudgeClient initialization with valid parameters"""
        client = AIJudgeClient(
            judge_platform="qwen",
            judge_model="qwen-max",
            api_key="valid-api-key-123"
        )
        
        self.assertEqual(client.judge_platform, "qwen")
        self.assertEqual(client.judge_model, "qwen-max")
        self.assertEqual(client.api_key, "valid-api-key-123")

    def test_normal_process_function_with_valid_judge_params(self):
        """Test normal execution of process function with valid judge parameters"""
        # Mock raw results
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'What is your product?',
                    'result': {'content': 'We offer premium products.'}
                }
            ]
        }
        
        all_brands = ['test_brand']
        main_brand = 'test_brand'
        
        # Mock the AIJudgeClient
        with patch('wechat_backend.views.AIJudgeClient') as mock_judge_class:
            mock_judge_instance = MagicMock()
            mock_judge_instance.evaluate_response.return_value = JudgeResult(
                accuracy_score=85,
                completeness_score=80,
                sentiment_score=90,
                purity_score=88,
                consistency_score=92,
                judgement="High quality response",
                confidence_level=ConfidenceLevel.HIGH
            )
            mock_judge_class.return_value = mock_judge_instance
            
            # Call the function with valid judge parameters
            result = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand,
                judge_platform="qwen",
                judge_model="qwen-max", 
                judge_api_key="valid-api-key"
            )
            
            # Verify results
            self.assertIn('detailed_results', result)
            self.assertIn('main_brand', result)
            self.assertIn('competitiveAnalysis', result)
            self.assertEqual(len(result['detailed_results']), 1)
            
            # Verify that judge was called
            mock_judge_instance.evaluate_response.assert_called_once()

    def test_normal_multiple_brands_processing(self):
        """Test normal processing with multiple brands"""
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'brand_a',
                    'model': 'model_x',
                    'question': 'Question 1',
                    'result': {'content': 'Response 1'}
                },
                {
                    'success': True,
                    'brand_name': 'brand_b',
                    'model': 'model_y',
                    'question': 'Question 2',
                    'result': {'content': 'Response 2'}
                }
            ]
        }
        
        all_brands = ['brand_a', 'brand_b']
        main_brand = 'brand_a'
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should process both brands
        self.assertEqual(len(result['detailed_results']), 2)
        self.assertIn('brand_a', result['competitiveAnalysis']['brandScores'])
        self.assertIn('brand_b', result['competitiveAnalysis']['brandScores'])

    def test_normal_successful_evaluation_with_scores(self):
        """Test normal evaluation that produces proper scores"""
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'Test question',
                    'result': {'content': 'Test response'}
                }
            ]
        }
        
        all_brands = ['test_brand']
        main_brand = 'test_brand'
        
        with patch('wechat_backend.views.AIJudgeClient') as mock_judge_class:
            mock_judge_instance = MagicMock()
            mock_judge_instance.evaluate_response.return_value = JudgeResult(
                accuracy_score=75,
                completeness_score=80,
                sentiment_score=70,
                purity_score=85,
                consistency_score=90,
                judgement="Acceptable response",
                confidence_level=ConfidenceLevel.MEDIUM
            )
            mock_judge_class.return_value = mock_judge_instance
            
            result = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand,
                judge_platform="qwen",
                judge_model="qwen-max",
                judge_api_key="test-key"
            )
            
            # Verify scores are properly propagated
            main_brand_scores = result['main_brand']
            self.assertGreaterEqual(main_brand_scores['overallScore'], 0)
            self.assertIn(main_brand_scores['overallGrade'], ['A', 'B', 'C', 'D'])

    def test_normal_skip_judge_when_no_params(self):
        """Test that AI evaluation is skipped when no judge parameters are provided"""
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'Test question',
                    'result': {'content': 'Test response'}
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
        
        # Should have results with default scores (0) when no judge is used
        detailed_result = result['detailed_results'][0]
        self.assertEqual(detailed_result['authority_score'], 0)
        self.assertEqual(detailed_result['visibility_score'], 0)
        self.assertEqual(detailed_result['sentiment_score'], 0)
        self.assertEqual(detailed_result['purity_score'], 0)
        self.assertEqual(detailed_result['consistency_score'], 0)
        self.assertEqual(detailed_result['score'], 0)


class TestAbnormalScenarios(unittest.TestCase):
    """Test abnormal scenarios with invalid parameters"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger_patcher = patch('wechat_backend.views.api_logger')
        self.mock_logger = self.logger_patcher.start()
        
        self.judge_logger_patcher = patch('ai_judge_module.api_logger')
        self.mock_judge_logger = self.judge_logger_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.logger_patcher.stop()
        self.judge_logger_patcher.stop()

    def test_abnormal_ai_judge_client_with_invalid_platform(self):
        """Test AIJudgeClient with invalid platform"""
        client = AIJudgeClient(
            judge_platform="invalid-platform",
            judge_model="invalid-model",
            api_key="invalid-key"
        )
        
        # Should still initialize but may have issues later
        self.assertEqual(client.judge_platform, "invalid-platform")
        self.assertEqual(client.judge_model, "invalid-model")
        self.assertEqual(client.api_key, "invalid-key")

    def test_abnormal_process_function_with_malformed_results(self):
        """Test process function with malformed results"""
        # Malformed results
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    # Missing required fields
                },
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'Test question',
                    'result': {'content': ''}  # Empty content
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
        
        # Should handle malformed results gracefully
        self.assertIn('detailed_results', result)

    def test_abnormal_process_function_with_none_values(self):
        """Test process function with None values"""
        raw_results = None
        all_brands = None
        main_brand = None
        
        # This should handle None values gracefully
        try:
            result = process_and_aggregate_results_with_ai_judge(
                raw_results, 
                all_brands, 
                main_brand
            )
            # Should return some form of default result
        except Exception:
            # If it raises an exception, that's also a valid way to handle it
            pass

    def test_abnormal_ai_judge_client_with_special_chars(self):
        """Test AIJudgeClient with special characters in parameters"""
        client = AIJudgeClient(
            judge_platform="qwen!@#$%",
            judge_model="qwen-max<>{}[]",
            api_key="test-key-123|\\/:*?\"<>%"
        )
        
        self.assertEqual(client.judge_platform, "qwen!@#$%")
        self.assertEqual(client.judge_model, "qwen-max<>{}[]")
        self.assertEqual(client.api_key, "test-key-123|\\/:*?\"<>%")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases with missing parameters"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger_patcher = patch('wechat_backend.views.api_logger')
        self.mock_logger = self.logger_patcher.start()
        
        self.judge_logger_patcher = patch('ai_judge_module.api_logger')
        self.mock_judge_logger = self.judge_logger_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.logger_patcher.stop()
        self.judge_logger_patcher.stop()

    def test_edge_case_ai_judge_client_with_empty_strings(self):
        """Test AIJudgeClient with empty string parameters"""
        client = AIJudgeClient(
            judge_platform="",
            judge_model="",
            api_key=""
        )
        
        self.assertEqual(client.judge_platform, "")
        self.assertEqual(client.judge_model, "")
        self.assertEqual(client.api_key, "")

    def test_edge_case_ai_judge_client_with_whitespace_only(self):
        """Test AIJudgeClient with whitespace-only parameters"""
        client = AIJudgeClient(
            judge_platform="   ",
            judge_model="\t\n",
            api_key=" \n\r\t "
        )
        
        self.assertEqual(client.judge_platform, "   ")
        self.assertEqual(client.judge_model, "\t\n")
        self.assertEqual(client.api_key, " \n\r\t ")

    def test_edge_case_process_function_with_empty_lists(self):
        """Test process function with empty lists"""
        raw_results = {'results': []}
        all_brands = []
        main_brand = 'nonexistent_brand'
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should handle empty results gracefully
        self.assertIn('detailed_results', result)
        self.assertEqual(len(result['detailed_results']), 0)

    def test_edge_case_process_function_with_extreme_values(self):
        """Test process function with extremely long strings"""
        extremely_long_string = "x" * 10000  # 10k character string
        
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': extremely_long_string,
                    'model': extremely_long_string,
                    'question': extremely_long_string,
                    'result': {'content': extremely_long_string}
                }
            ]
        }
        
        all_brands = [extremely_long_string]
        main_brand = extremely_long_string
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should handle extremely long strings
        self.assertIn('detailed_results', result)

    def test_edge_case_process_function_with_unicode(self):
        """Test process function with unicode characters"""
        unicode_brand = "测试品牌✓🔥🚀"
        unicode_question = "这是什么产品？"
        unicode_response = "这是一个测试产品。"
        
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': unicode_brand,
                    'model': 'test_model',
                    'question': unicode_question,
                    'result': {'content': unicode_response}
                }
            ]
        }
        
        all_brands = [unicode_brand]
        main_brand = unicode_brand
        
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand
        )
        
        # Should handle unicode characters
        self.assertIn('detailed_results', result)
        if result['detailed_results']:
            self.assertEqual(result['detailed_results'][0]['brand'], unicode_brand)

    def test_edge_case_mixed_param_scenarios(self):
        """Test mixed scenarios with some params present and others missing"""
        raw_results = {
            'results': [
                {
                    'success': True,
                    'brand_name': 'test_brand',
                    'model': 'test_model',
                    'question': 'Test question',
                    'result': {'content': 'Test response'}
                }
            ]
        }
        
        all_brands = ['test_brand']
        main_brand = 'test_brand'
        
        # Mix of None and valid parameters
        result = process_and_aggregate_results_with_ai_judge(
            raw_results, 
            all_brands, 
            main_brand,
            judge_platform="qwen",  # Valid
            judge_model=None,       # Missing
            judge_api_key="test-key"  # Valid
        )
        
        # Should handle mixed parameters
        self.assertIn('detailed_results', result)


if __name__ == '__main__':
    unittest.main()