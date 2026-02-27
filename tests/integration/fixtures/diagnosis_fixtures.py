"""
诊断测试数据夹具

提供：
1. 标准诊断配置
2. 多品牌诊断配置
3. 单品牌诊断配置
4. 自定义问题配置

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import random
import string
from datetime import datetime
from typing import Dict, Any, List


def generate_random_brand() -> str:
    """生成随机品牌名"""
    brands = [
        '品牌 A', '品牌 B', '品牌 C', '品牌 D', '品牌 E',
        '品牌 X', '品牌 Y', '品牌 Z', '测试品牌', '竞品品牌'
    ]
    return random.choice(brands)


def generate_random_execution_id() -> str:
    """生成随机执行 ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"test_exec_{timestamp}_{random_suffix}"


@pytest.fixture
def standard_diagnosis_config() -> Dict[str, Any]:
    """标准诊断配置（多品牌、多模型）"""
    return {
        'brand_list': ['测试品牌 A', '测试品牌 B'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True},
            {'name': 'doubao', 'checked': True},
            {'name': 'qwen', 'checked': True}
        ],
        'custom_question': '用户如何看待该品牌的产品质量？',
        'competitor_brands': ['竞品 X', '竞品 Y'],
        'userOpenid': 'test_user_standard',
        'userLevel': 'Premium'
    }


@pytest.fixture
def single_brand_config() -> Dict[str, Any]:
    """单品牌诊断配置"""
    return {
        'brand_list': ['单测试品牌'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True}
        ],
        'custom_question': '单品牌测试问题',
        'competitor_brands': [],
        'userOpenid': 'test_user_single',
        'userLevel': 'Basic'
    }


@pytest.fixture
def multi_brand_config() -> Dict[str, Any]:
    """多品牌诊断配置（4 个品牌）"""
    return {
        'brand_list': ['品牌 A', '品牌 B', '品牌 C', '品牌 D'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True},
            {'name': 'doubao', 'checked': True}
        ],
        'custom_question': '多品牌对比测试问题',
        'competitor_brands': ['竞品 X'],
        'userOpenid': 'test_user_multi',
        'userLevel': 'Premium'
    }


@pytest.fixture
def custom_question_config() -> Dict[str, Any]:
    """自定义问题诊断配置"""
    return {
        'brand_list': ['测试品牌'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True},
            {'name': 'qwen', 'checked': True}
        ],
        'custom_question': '这是一个自定义的测试问题，用于验证自定义问题功能',
        'competitor_brands': ['竞品 A'],
        'userOpenid': 'test_user_custom',
        'userLevel': 'Premium'
    }


@pytest.fixture
def all_models_config() -> Dict[str, Any]:
    """包含所有模型的诊断配置"""
    return {
        'brand_list': ['全模型测试品牌'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True},
            {'name': 'doubao', 'checked': True},
            {'name': 'qwen', 'checked': True},
            {'name': 'gpt', 'checked': True},
            {'name': 'gemini', 'checked': True}
        ],
        'custom_question': '全模型测试问题',
        'competitor_brands': [],
        'userOpenid': 'test_user_all_models',
        'userLevel': 'Enterprise'
    }


@pytest.fixture
def partial_models_config() -> Dict[str, Any]:
    """部分模型选中的诊断配置"""
    return {
        'brand_list': ['部分模型测试品牌'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True},
            {'name': 'doubao', 'checked': False},
            {'name': 'qwen', 'checked': True},
            {'name': 'gpt', 'checked': False}
        ],
        'custom_question': '部分模型测试问题',
        'competitor_brands': [],
        'userOpenid': 'test_user_partial',
        'userLevel': 'Basic'
    }


@pytest.fixture
def random_diagnosis_config() -> Dict[str, Any]:
    """随机诊断配置（用于模糊测试）"""
    num_brands = random.randint(1, 5)
    brands = [generate_random_brand() for _ in range(num_brands)]
    
    all_models = ['deepseek', 'doubao', 'qwen', 'gpt', 'gemini']
    selected_models = [
        {'name': model, 'checked': random.choice([True, False])}
        for model in all_models
    ]
    
    # 确保至少有一个模型被选中
    if not any(m['checked'] for m in selected_models):
        selected_models[0]['checked'] = True
    
    return {
        'brand_list': list(set(brands)),  # 去重
        'selectedModels': selected_models,
        'custom_question': f'随机测试问题_{datetime.now().strftime("%H%M%S")}',
        'competitor_brands': [generate_random_brand() for _ in range(random.randint(0, 3))],
        'userOpenid': f'test_user_random_{random.randint(1000, 9999)}',
        'userLevel': random.choice(['Basic', 'Premium', 'Enterprise'])
    }


@pytest.fixture
def high_priority_config() -> Dict[str, Any]:
    """高优先级用户诊断配置"""
    return {
        'brand_list': ['高端测试品牌'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True},
            {'name': 'gpt', 'checked': True}
        ],
        'custom_question': '高端用户专属测试问题',
        'competitor_brands': ['高端竞品 A', '高端竞品 B'],
        'userOpenid': 'test_user_vip',
        'userLevel': 'Enterprise'
    }


@pytest.fixture
def minimal_config() -> Dict[str, Any]:
    """最小化诊断配置"""
    return {
        'brand_list': ['最小测试'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True}
        ],
        'custom_question': '最小测试问题',
        'competitor_brands': [],
        'userOpenid': 'test_user_minimal',
        'userLevel': 'Basic'
    }
