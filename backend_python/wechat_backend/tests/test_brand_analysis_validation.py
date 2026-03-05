"""
品牌分析输入验证增强测试模块

【P2 增强 - 2026-03-05】测试品牌分析服务的输入验证功能
测试范围：
1. 品牌名称验证
2. 问题文本验证
3. 综合输入验证
"""

import unittest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../wechat_backend'))

from flask import Flask
from wechat_backend.views.diagnosis_views import (
    _validate_brand_name,
    _validate_question_text,
    _validate_brand_test_input,
    BRAND_VALIDATION_CONSTANTS
)

# 创建 Flask 应用上下文用于测试 jsonify
app = Flask(__name__)
app.config['TESTING'] = True


class TestBrandNameValidation(unittest.TestCase):
    """测试品牌名称验证"""

    def test_valid_brand_names(self):
        """测试有效的品牌名称"""
        valid_names = [
            '华为',
            'Apple',
            '小米',
            'Samsung',
            '特斯拉',
            'BMW',
            'Mercedes-Benz',
            '可口可乐',
            'Nike',
            '阿迪达斯',
            '腾讯',
            '阿里巴巴',
            '字节跳动',
        ]

        for name in valid_names:
            is_valid, error_msg = _validate_brand_name(name)
            self.assertTrue(is_valid, f"品牌名称 '{name}' 应该有效，但得到错误：{error_msg}")

    def test_empty_brand_name(self):
        """测试空品牌名称"""
        empty_cases = ['', '   ', None]

        for name in empty_cases:
            is_valid, error_msg = _validate_brand_name(name)
            self.assertFalse(is_valid, f"空品牌名称 '{name}' 应该无效")
            self.assertTrue(
                '不能为空' in error_msg or '不能全为空白字符' in error_msg,
                f"错误消息应包含 '不能为空' 或 '不能全为空白字符'，实际：{error_msg}"
            )

    def test_brand_name_length_limits(self):
        """测试品牌名称长度限制"""
        # 过长（超过 100 字符）
        long_name = 'a' * 101
        is_valid, error_msg = _validate_brand_name(long_name)
        self.assertFalse(is_valid)
        self.assertIn('长度', error_msg)

        # 边界值测试 - 使用不触发重复检测的 100 字符
        max_valid = 'ab' * 50  # 100 字符，但不会触发重复检测
        is_valid, error_msg = _validate_brand_name(max_valid)
        self.assertTrue(is_valid, f"100 字符应该有效，但得到错误：{error_msg}")

    def test_brand_name_repeated_characters(self):
        """测试过多重复字符检测"""
        # 超过 50 个连续重复字符
        repeated = 'a' * 51
        is_valid, error_msg = _validate_brand_name(repeated)
        self.assertFalse(is_valid)
        self.assertIn('重复', error_msg)

        # 50 个重复字符（边界值）
        repeated = 'a' * 50
        is_valid, error_msg = _validate_brand_name(repeated)
        self.assertTrue(is_valid, f"50 个重复字符应该有效，但得到错误：{error_msg}")

    def test_brand_name_type_validation(self):
        """测试类型验证"""
        non_string_cases = [123, ['华为'], {'name': '华为'}, True]

        for name in non_string_cases:
            is_valid, error_msg = _validate_brand_name(name)
            self.assertFalse(is_valid, f"非字符串类型 {type(name)} 应该无效")


class TestQuestionValidation(unittest.TestCase):
    """测试问题文本验证"""

    def test_valid_questions(self):
        """测试有效的问题"""
        valid_questions = [
            '华为的市场份额如何？',
            'Apple 的产品有哪些优势？',
            '小米的性价比怎么样？',
            '特斯拉的自动驾驶技术领先吗？',
            'What are the strengths of BMW?',
        ]

        for i, question in enumerate(valid_questions):
            is_valid, error_msg = _validate_question_text(question, i)
            self.assertTrue(is_valid, f"问题 '{question}' 应该有效，但得到错误：{error_msg}")

    def test_empty_question(self):
        """测试空问题"""
        empty_cases = ['', '   ', None]

        for i, question in enumerate(empty_cases):
            is_valid, error_msg = _validate_question_text(question, i)
            self.assertFalse(is_valid, f"空问题 '{question}' 应该无效")
            self.assertTrue(
                '不能为空' in error_msg or '不能全为空白字符' in error_msg,
                f"错误消息应包含 '不能为空' 或 '不能全为空白字符'，实际：{error_msg}"
            )

    def test_question_length_limits(self):
        """测试问题长度限制"""
        # 过长（超过 500 字符）
        long_question = 'a' * 501
        is_valid, error_msg = _validate_question_text(long_question, 0)
        self.assertFalse(is_valid)
        self.assertIn('长度', error_msg)

        # 边界值测试
        max_valid = 'a' * 500
        is_valid, error_msg = _validate_question_text(max_valid, 0)
        self.assertTrue(is_valid, f"500 字符应该有效，但得到错误：{error_msg}")

    def test_question_illegal_characters(self):
        """测试非法字符检测"""
        illegal_cases = ['问题\x00测试', '问题\x01测试']

        for i, question in enumerate(illegal_cases):
            is_valid, error_msg = _validate_question_text(question, i)
            self.assertFalse(is_valid, f"包含非法字符的问题 '{question}' 应该无效")

    def test_question_type_validation(self):
        """测试类型验证"""
        non_string_cases = [123, ['问题'], {'question': '测试'}, True]

        for i, question in enumerate(non_string_cases):
            is_valid, error_msg = _validate_question_text(question, i)
            self.assertFalse(is_valid, f"非字符串类型 {type(question)} 应该无效")


class TestComprehensiveInputValidation(unittest.TestCase):
    """测试综合输入验证"""

    def setUp(self):
        """设置 Flask 应用上下文"""
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """清理 Flask 应用上下文"""
        self.app_context.pop()

    def test_valid_input(self):
        """测试有效的输入"""
        valid_input = {
            'brand_list': ['华为', 'Apple', '小米'],
            'selectedModels': [
                {'name': 'deepseek', 'checked': True},
                {'name': 'qwen', 'checked': True},
            ],
            'custom_question': '各品牌的市场份额如何？',
        }

        is_valid, error_response = _validate_brand_test_input(valid_input)
        self.assertTrue(is_valid, f"有效输入应该通过验证")

    def test_missing_brand_list(self):
        """测试缺少 brand_list"""
        invalid_input = {
            'selectedModels': [{'name': 'deepseek', 'checked': True}],
            'custom_question': '测试问题？',
        }

        is_valid, error_response = _validate_brand_test_input(invalid_input)
        self.assertFalse(is_valid)
        self.assertIn('brand_list', error_response[0].get_json()['error'])

    def test_empty_brand_list(self):
        """测试空 brand_list"""
        invalid_input = {
            'brand_list': [],
            'selectedModels': [{'name': 'deepseek', 'checked': True}],
            'custom_question': '测试问题？',
        }

        is_valid, error_response = _validate_brand_test_input(invalid_input)
        self.assertFalse(is_valid)
        self.assertIn('empty', error_response[0].get_json()['error'].lower())

    def test_too_many_brands(self):
        """测试品牌数量过多"""
        invalid_input = {
            'brand_list': ['品牌' + str(i) for i in range(15)],
            'selectedModels': [{'name': 'deepseek', 'checked': True}],
            'custom_question': '测试问题？',
        }

        is_valid, error_response = _validate_brand_test_input(invalid_input)
        self.assertFalse(is_valid)
        self.assertIn('品牌数量过多', error_response[0].get_json()['error'])

    def test_missing_selected_models(self):
        """测试缺少 selectedModels"""
        invalid_input = {
            'brand_list': ['华为'],
            'custom_question': '测试问题？',
        }

        is_valid, error_response = _validate_brand_test_input(invalid_input)
        self.assertFalse(is_valid)
        self.assertIn('selectedModels', error_response[0].get_json()['error'])

    def test_empty_selected_models(self):
        """测试空 selectedModels"""
        invalid_input = {
            'brand_list': ['华为'],
            'selectedModels': [],
            'custom_question': '测试问题？',
        }

        is_valid, error_response = _validate_brand_test_input(invalid_input)
        self.assertFalse(is_valid)
        self.assertIn('At least one', error_response[0].get_json()['error'])

    def test_too_many_models(self):
        """测试模型数量过多"""
        invalid_input = {
            'brand_list': ['华为'],
            'selectedModels': [{'name': f'model{i}', 'checked': True} for i in range(15)],
            'custom_question': '测试问题？',
        }

        is_valid, error_response = _validate_brand_test_input(invalid_input)
        self.assertFalse(is_valid)
        self.assertIn('模型数量过多', error_response[0].get_json()['error'])

    def test_too_many_questions(self):
        """测试问题数量过多"""
        invalid_input = {
            'brand_list': ['华为'],
            'selectedModels': [{'name': 'deepseek', 'checked': True}],
            'custom_question': ' '.join(['问题' + str(i) + '?' for i in range(25)]),
        }

        is_valid, error_response = _validate_brand_test_input(invalid_input)
        self.assertFalse(is_valid)
        self.assertIn('问题数量过多', error_response[0].get_json()['error'])


class TestValidationConstants(unittest.TestCase):
    """测试验证常量"""

    def test_constants_defined(self):
        """测试常量已定义"""
        self.assertIn('MIN_BRAND_NAME_LENGTH', BRAND_VALIDATION_CONSTANTS)
        self.assertIn('MAX_BRAND_NAME_LENGTH', BRAND_VALIDATION_CONSTANTS)
        self.assertIn('MAX_BRANDS_COUNT', BRAND_VALIDATION_CONSTANTS)
        self.assertIn('MIN_QUESTION_LENGTH', BRAND_VALIDATION_CONSTANTS)
        self.assertIn('MAX_QUESTION_LENGTH', BRAND_VALIDATION_CONSTANTS)
        self.assertIn('MAX_QUESTIONS_COUNT', BRAND_VALIDATION_CONSTANTS)
        self.assertIn('MAX_MODEL_COUNT', BRAND_VALIDATION_CONSTANTS)

    def test_constant_values(self):
        """测试常量值"""
        self.assertEqual(BRAND_VALIDATION_CONSTANTS['MIN_BRAND_NAME_LENGTH'], 1)
        self.assertEqual(BRAND_VALIDATION_CONSTANTS['MAX_BRAND_NAME_LENGTH'], 100)
        self.assertEqual(BRAND_VALIDATION_CONSTANTS['MAX_BRANDS_COUNT'], 10)
        self.assertEqual(BRAND_VALIDATION_CONSTANTS['MIN_QUESTION_LENGTH'], 1)
        self.assertEqual(BRAND_VALIDATION_CONSTANTS['MAX_QUESTION_LENGTH'], 500)
        self.assertEqual(BRAND_VALIDATION_CONSTANTS['MAX_QUESTIONS_COUNT'], 20)
        self.assertEqual(BRAND_VALIDATION_CONSTANTS['MAX_MODEL_COUNT'], 10)


if __name__ == '__main__':
    unittest.main()
