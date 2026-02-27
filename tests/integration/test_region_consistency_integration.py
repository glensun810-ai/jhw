"""
AI 平台区域一致性验证集成测试

测试覆盖：
1. 与诊断创建接口集成
2. API 响应验证
3. 错误消息 UI 友好性
4. 端到端场景

作者：系统架构组
日期：2026-02-28
"""

import pytest
import json
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from wechat_backend.ai_adapters.base_adapter import (
    validate_model_region_consistency,
    PlatformRegion,
)


# ==================== 集成场景测试 ====================

class TestRegionConsistencyIntegration:
    """区域一致性集成测试"""

    def test_validation_with_dict_models(self):
        """测试字典格式模型列表"""
        # 前端可能传递字典格式：{"name": "deepseek", "label": "DeepSeek"}
        models = [
            {"name": "deepseek", "label": "DeepSeek"},
            {"name": "qwen", "label": "Qwen"},
        ]
        
        model_names = [model["name"] if isinstance(model, dict) else model for model in models]
        is_valid, error_msg = validate_model_region_consistency(model_names)
        
        assert is_valid is True
        assert error_msg is None

    def test_validation_with_mixed_dict_models(self):
        """测试混合字典格式模型列表"""
        models = [
            {"name": "deepseek", "label": "DeepSeek"},
            {"name": "chatgpt", "label": "ChatGPT"},
        ]
        
        model_names = [model["name"] if isinstance(model, dict) else model for model in models]
        is_valid, error_msg = validate_model_region_consistency(model_names)
        
        assert is_valid is False
        assert error_msg is not None
        assert "不能同时选择" in error_msg

    def test_error_message_ui_friendly(self):
        """测试错误消息 UI 友好性"""
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 验证错误消息结构清晰
        assert "不能同时选择国内和海外 AI 平台" in error_msg
        # 验证包含具体平台列表
        assert "国内平台：" in error_msg
        assert "海外平台：" in error_msg
        # 验证包含解决方案
        assert "请只选择国内平台或只选择海外平台" in error_msg
        # 验证解释原因
        assert "由于网络连接问题" in error_msg

    def test_error_message_contains_actionable_info(self):
        """测试错误消息包含可操作信息"""
        models = ['deepseek', 'qwen', 'chatgpt', 'claude']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 用户应该能够知道哪些平台需要调整
        assert "deepseek" in error_msg
        assert "qwen" in error_msg
        assert "chatgpt" in error_msg
        assert "claude" in error_msg

    def test_success_response_format(self):
        """测试成功响应格式"""
        models = ['deepseek', 'qwen', 'kimi']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is True
        assert error_msg is None  # 成功时不应有错误消息

    def test_single_platform_error_clarity(self):
        """测试单个平台错误清晰度"""
        # 只选一个国内 + 一个海外，错误消息应该简洁
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 错误消息应该清晰指出问题
        lines = error_msg.split('。')
        assert len(lines) >= 2  # 至少包含问题说明和解决方案


# ==================== 前端交互场景测试 ====================

class TestFrontendInteractionScenarios:
    """前端交互场景测试"""

    def test_user_selects_popular_domestic_combo(self):
        """测试用户选择热门国内组合"""
        # 模拟常见用户选择：DeepSeek + Qwen + Kimi
        user_selection = ['deepseek', 'qwen', 'kimi']
        is_valid, error_msg = validate_model_region_consistency(user_selection)
        
        assert is_valid is True
        assert error_msg is None

    def test_user_selects_popular_overseas_combo(self):
        """测试用户选择热门海外组合"""
        # 模拟常见用户选择：ChatGPT + Claude
        user_selection = ['chatgpt', 'claude']
        is_valid, error_msg = validate_model_region_consistency(user_selection)
        
        assert is_valid is True
        assert error_msg is None

    def test_user_accidentally_adds_both_types(self):
        """测试用户意外添加两种类型"""
        # 用户可能不理解平台分类，随机选择
        user_selection = ['deepseek', 'chatgpt', 'qwen', 'claude', 'kimi']
        is_valid, error_msg = validate_model_region_consistency(user_selection)
        
        assert is_valid is False
        # 错误消息应该友好引导
        assert "请只选择" in error_msg

    def test_user_changes_selection_from_mixed_to_pure(self):
        """测试用户从混合选择改为纯选择"""
        # 初始混合选择
        mixed = ['deepseek', 'chatgpt']
        is_valid, _ = validate_model_region_consistency(mixed)
        assert is_valid is False
        
        # 用户调整为纯国内
        pure_domestic = ['deepseek', 'qwen']
        is_valid, error_msg = validate_model_region_consistency(pure_domestic)
        assert is_valid is True
        assert error_msg is None
        
        # 或调整为纯海外
        pure_overseas = ['chatgpt', 'claude']
        is_valid, error_msg = validate_model_region_consistency(pure_overseas)
        assert is_valid is True
        assert error_msg is None

    def test_error_message_guides_user_decision(self):
        """测试错误消息引导用户决策"""
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 错误消息应该明确告诉用户该怎么做
        assert "国内平台" in error_msg
        assert "海外平台" in error_msg
        # 使用明确的行动动词
        assert "选择" in error_msg


# ==================== API 响应格式测试 ====================

class TestAPIResponseFormat:
    """API 响应格式测试"""

    def test_error_response_structure(self):
        """测试错误响应结构"""
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        # 模拟 API 响应
        response = {
            "status": "error" if not is_valid else "success",
            "error": error_msg,
            "code": 400 if not is_valid else 200
        }
        
        assert response["status"] == "error"
        assert response["code"] == 400
        assert response["error"] is not None
        assert "不能同时选择" in response["error"]

    def test_success_response_structure(self):
        """测试成功响应结构"""
        models = ['deepseek', 'qwen']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        # 模拟 API 响应
        response = {
            "status": "error" if not is_valid else "success",
            "error": error_msg,
            "code": 400 if not is_valid else 200
        }
        
        assert response["status"] == "success"
        assert response["code"] == 200
        assert response["error"] is None

    def test_response_includes_platform_lists(self):
        """测试响应包含平台列表"""
        models = ['deepseek', 'qwen', 'chatgpt', 'claude']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 错误消息应该包含平台分类
        assert "国内平台：" in error_msg
        assert "海外平台：" in error_msg


# ==================== 边界和异常场景测试 ====================

class TestBoundaryAndExceptionScenarios:
    """边界和异常场景测试"""

    def test_very_long_model_list(self):
        """测试超长模型列表"""
        # 极端情况：用户选择了大量模型
        many_models = ['deepseek', 'qwen', 'kimi', 'wenxin', 'doubao'] * 10
        is_valid, error_msg = validate_model_region_consistency(many_models)
        
        assert is_valid is True
        assert error_msg is None

    def test_very_long_mixed_model_list(self):
        """测试超长混合模型列表"""
        # 极端情况：混合大量模型
        many_mixed = ['deepseek', 'chatgpt'] * 10
        is_valid, error_msg = validate_model_region_consistency(many_mixed)
        
        assert is_valid is False
        assert error_msg is not None
        # 错误消息不应该过长（避免 UI 显示问题）
        assert len(error_msg) < 1000

    def test_model_name_with_version_numbers(self):
        """测试带版本号的模型名称"""
        # 前端可能传递带版本号的模型名
        models = ['deepseek-v3', 'chatgpt-4o', 'qwen-max']
        # 这些不在映射中，会被忽略
        is_valid, error_msg = validate_model_region_consistency(models)
        # 全部未知平台，应该通过
        assert is_valid is True

    def test_case_variations(self):
        """测试大小写变化"""
        # 用户输入可能大小写不一致
        models = ['DeepSeek', 'CHATGPT', 'Qwen']
        # get_platform_region 会转小写，所以应该正确识别
        is_valid, error_msg = validate_model_region_consistency(models)
        assert is_valid is False  # 混合了国内和海外

    def test_whitespace_handling(self):
        """测试空格处理"""
        # 前端可能传递带空格的模型名
        models = [' deepseek ', ' chatgpt ']
        # 带空格不在映射中，会被忽略
        is_valid, error_msg = validate_model_region_consistency(models)
        assert is_valid is True  # 全部被忽略，视为空列表


# ==================== 用户体验优化测试 ====================

class TestUserExperienceOptimization:
    """用户体验优化测试"""

    def test_error_message_not_technical(self):
        """测试错误消息非技术化"""
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 错误消息应该通俗易懂
        assert "API" not in error_msg
        assert "Endpoint" not in error_msg
        assert "HTTP" not in error_msg
        # 使用用户能理解的语言
        assert "网络连接问题" in error_msg

    def test_error_message_provides_alternative(self):
        """测试错误消息提供替代方案"""
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 应该告诉用户可以怎么做
        assert "或" in error_msg  # 提供选择
        assert "只选择" in error_msg

    def test_error_message_not_blaming_user(self):
        """测试错误消息不指责用户"""
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 错误消息不应该指责用户
        assert "错误" not in error_msg or "选择错误" not in error_msg
        assert "不允许" not in error_msg
        # 使用中性语言
        assert "不能" in error_msg  # 客观陈述

    def test_both_options_presented_equally(self):
        """测试两种选择平等呈现"""
        models = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(models)
        
        assert is_valid is False
        # 国内和海外平台都应该被提及
        assert "国内平台" in error_msg
        assert "海外平台" in error_msg
        # 两种选择都应该可用
        assert "或只选择海外平台" in error_msg


# ==================== 实际使用场景测试 ====================

class TestRealWorldUsageScenarios:
    """实际使用场景测试"""

    def test_beginner_user_typical_choice(self):
        """测试新手用户典型选择"""
        # 新手可能只听说过 ChatGPT
        choice = ['chatgpt']
        is_valid, error_msg = validate_model_region_consistency(choice)
        assert is_valid is True

    def test_power_user_typical_choice(self):
        """测试高级用户典型选择"""
        # 高级用户可能选择多个国内平台
        choice = ['deepseek', 'qwen', 'kimi', 'wenxin']
        is_valid, error_msg = validate_model_region_consistency(choice)
        assert is_valid is True

    def test_enterprise_user_scenario(self):
        """测试企业用户场景"""
        # 企业可能想同时使用国内外平台做对比
        choice = ['deepseek', 'chatgpt', 'claude']
        is_valid, error_msg = validate_model_region_consistency(choice)
        # 系统会阻止这种选择
        assert is_valid is False
        # 但会友好提示
        assert "请只选择" in error_msg

    def test_mobile_user_quick_selection(self):
        """测试移动端用户快速选择"""
        # 移动端用户可能快速勾选 2-3 个
        choice = ['deepseek', 'qwen']
        is_valid, error_msg = validate_model_region_consistency(choice)
        assert is_valid is True

    def test_confused_user_random_selection(self):
        """测试困惑用户随机选择"""
        # 用户不理解区别，随机选择
        choice = ['deepseek', 'chatgpt', 'qwen', 'claude', 'kimi', 'gemini']
        is_valid, error_msg = validate_model_region_consistency(choice)
        assert is_valid is False
        # 错误消息应该清晰解释
        assert "不能同时选择" in error_msg
        assert "国内" in error_msg
        assert "海外" in error_msg


# ==================== 文档和示例测试 ====================

class TestDocumentationAndExamples:
    """文档和示例测试"""

    def test_example_domestic_platforms_work(self):
        """测试示例国内平台可用"""
        # 文档示例：国内平台
        examples = ['deepseek', 'qwen', 'kimi']
        is_valid, error_msg = validate_model_region_consistency(examples)
        assert is_valid is True

    def test_example_overseas_platforms_work(self):
        """测试示例海外平台可用"""
        # 文档示例：海外平台
        examples = ['chatgpt', 'claude', 'gemini']
        is_valid, error_msg = validate_model_region_consistency(examples)
        assert is_valid is True

    def test_example_mixed_platforms_fails(self):
        """测试示例混合平台失败"""
        # 文档示例：混合平台（反面教材）
        examples = ['deepseek', 'chatgpt']
        is_valid, error_msg = validate_model_region_consistency(examples)
        assert is_valid is False
        assert error_msg is not None
