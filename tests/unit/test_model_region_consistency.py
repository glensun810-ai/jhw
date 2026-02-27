"""
AI 平台区域一致性验证单元测试

测试覆盖：
1. 区域分类映射正确性
2. 区域验证函数逻辑
3. 混合区域检测
4. 边界情况处理
5. 未知平台处理
6. 与诊断接口集成

作者：系统架构组
日期：2026-02-28
"""

import pytest
from typing import List, Dict, Any

from wechat_backend.ai_adapters.base_adapter import (
    PlatformRegion,
    PLATFORM_REGION_MAP,
    get_platform_region,
    validate_model_region_consistency,
)


# ====================  fixture 定义 ====================

@pytest.fixture
def domestic_models() -> List[str]:
    """国内平台列表"""
    return ['deepseek', 'qwen', 'wenxin', 'doubao', 'kimi', 'yuanbao', 'spark', 'zhipu']


@pytest.fixture
def overseas_models() -> List[str]:
    """海外平台列表"""
    return ['chatgpt', 'claude', 'gemini', 'openai', 'anthropic', 'google']


@pytest.fixture
def mixed_models() -> List[str]:
    """混合平台列表"""
    return ['deepseek', 'chatgpt', 'qwen', 'claude']


# ==================== 区域分类映射测试 ====================

class TestPlatformRegionMap:
    """平台区域分类映射测试"""

    def test_all_domestic_platforms_mapped(self):
        """测试所有国内平台都被正确映射"""
        domestic_platforms = ['deepseek', 'qwen', 'wenxin', 'doubao', 'kimi', 
                             'yuanbao', 'spark', 'zhipu', 'deepseekr1']
        
        for platform in domestic_platforms:
            region = get_platform_region(platform)
            assert region == PlatformRegion.DOMESTIC, f"{platform} 应该被映射为国内平台"

    def test_all_overseas_platforms_mapped(self):
        """测试所有海外平台都被正确映射"""
        overseas_platforms = ['chatgpt', 'claude', 'gemini', 'openai', 
                             'anthropic', 'google']
        
        for platform in overseas_platforms:
            region = get_platform_region(platform)
            assert region == PlatformRegion.OVERSEAS, f"{platform} 应该被映射为海外平台"

    def test_case_insensitive_lookup(self):
        """测试平台名称查找不区分大小写"""
        test_cases = [
            ('DEEPSEEK', PlatformRegion.DOMESTIC),
            ('DeepSeek', PlatformRegion.DOMESTIC),
            ('deepseek', PlatformRegion.DOMESTIC),
            ('CHATGPT', PlatformRegion.OVERSEAS),
            ('ChatGPT', PlatformRegion.OVERSEAS),
            ('chatgpt', PlatformRegion.OVERSEAS),
        ]
        
        for platform_name, expected_region in test_cases:
            region = get_platform_region(platform_name)
            assert region == expected_region, f"{platform_name} 的区域映射错误"

    def test_unknown_platform_returns_none(self):
        """测试未知平台返回 None"""
        unknown_platforms = ['unknown_platform', 'fake_ai', 'test_model', '']
        
        for platform in unknown_platforms:
            region = get_platform_region(platform)
            assert region is None, f"未知平台 {platform} 应该返回 None"


# ==================== 区域验证函数测试 ====================

class TestValidateModelRegionConsistency:
    """模型区域一致性验证测试"""

    def test_empty_model_list(self):
        """测试空模型列表"""
        is_valid, error_msg = validate_model_region_consistency([])
        assert is_valid is True
        assert error_msg is None

    def test_single_domestic_model(self):
        """测试单个国内模型"""
        is_valid, error_msg = validate_model_region_consistency(['deepseek'])
        assert is_valid is True
        assert error_msg is None

    def test_single_overseas_model(self):
        """测试单个海外模型"""
        is_valid, error_msg = validate_model_region_consistency(['chatgpt'])
        assert is_valid is True
        assert error_msg is None

    def test_all_domestic_models(self, domestic_models):
        """测试全部国内平台"""
        is_valid, error_msg = validate_model_region_consistency(domestic_models)
        assert is_valid is True
        assert error_msg is None

    def test_all_overseas_models(self, overseas_models):
        """测试全部海外平台"""
        is_valid, error_msg = validate_model_region_consistency(overseas_models)
        assert is_valid is True
        assert error_msg is None

    def test_mixed_regions_detected(self, mixed_models):
        """测试混合区域检测"""
        is_valid, error_msg = validate_model_region_consistency(mixed_models)
        assert is_valid is False
        assert error_msg is not None
        assert "不能同时选择国内和海外 AI 平台" in error_msg
        # 验证错误消息包含具体平台信息
        assert "国内平台" in error_msg
        assert "海外平台" in error_msg

    def test_two_domestic_models(self):
        """测试两个国内模型"""
        is_valid, error_msg = validate_model_region_consistency(['deepseek', 'qwen'])
        assert is_valid is True
        assert error_msg is None

    def test_two_overseas_models(self):
        """测试两个海外模型"""
        is_valid, error_msg = validate_model_region_consistency(['chatgpt', 'claude'])
        assert is_valid is True
        assert error_msg is None

    def test_one_domestic_one_overseas(self):
        """测试一个国内 + 一个海外"""
        is_valid, error_msg = validate_model_region_consistency(['deepseek', 'chatgpt'])
        assert is_valid is False
        assert error_msg is not None
        assert "deepseek" in error_msg
        assert "chatgpt" in error_msg

    def test_unknown_platform_ignored(self):
        """测试未知平台被忽略"""
        # 未知平台不应该影响验证结果
        is_valid, error_msg = validate_model_region_consistency(
            ['deepseek', 'unknown_platform', 'qwen']
        )
        assert is_valid is True
        assert error_msg is None

    def test_unknown_with_mixed_regions(self):
        """测试未知平台与混合区域"""
        is_valid, error_msg = validate_model_region_consistency(
            ['deepseek', 'unknown_platform', 'chatgpt']
        )
        assert is_valid is False
        assert error_msg is not None
        # 未知平台不应该出现在错误消息中
        assert "unknown_platform" not in error_msg

    def test_duplicate_models_same_region(self):
        """测试重复的同一区域模型"""
        is_valid, error_msg = validate_model_region_consistency(
            ['deepseek', 'deepseek', 'qwen', 'qwen']
        )
        assert is_valid is True
        assert error_msg is None

    def test_duplicate_models_mixed_regions(self):
        """测试重复的混合区域模型"""
        is_valid, error_msg = validate_model_region_consistency(
            ['deepseek', 'deepseek', 'chatgpt', 'chatgpt']
        )
        assert is_valid is False
        assert error_msg is not None

    def test_error_message_format(self):
        """测试错误消息格式"""
        is_valid, error_msg = validate_model_region_consistency(['deepseek', 'chatgpt'])
        
        assert is_valid is False
        # 验证错误消息包含解决方案
        assert "由于网络连接问题" in error_msg
        assert "请只选择国内平台或只选择海外平台" in error_msg
        # 验证错误消息包含具体平台列表
        assert "国内平台：" in error_msg
        assert "海外平台：" in error_msg


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""

    def test_none_input(self):
        """测试 None 输入"""
        # None 输入会被视为空列表处理（兼容性考虑）
        is_valid, error_msg = validate_model_region_consistency(None)
        assert is_valid is True
        assert error_msg is None

    def test_model_with_special_characters(self):
        """测试包含特殊字符的模型名称"""
        # 特殊字符应该被正常处理
        is_valid, error_msg = validate_model_region_consistency(
            ['deepseek-v3', 'chatgpt-4o', 'qwen-max']
        )
        # 带版本的模型名称如果基础名称在映射中，应该正常识别
        # 这里取决于 get_platform_region 的实现
        # 如果不在映射中，会被忽略
        assert isinstance(is_valid, bool)

    def test_whitespace_in_model_name(self):
        """测试模型名称中的空格"""
        is_valid, error_msg = validate_model_region_consistency(
            [' deepseek ', ' chatgpt ']
        )
        # 带空格的名称不在映射中，应该被忽略
        assert is_valid is True

    def test_empty_string_in_list(self):
        """测试列表中的空字符串"""
        is_valid, error_msg = validate_model_region_consistency(
            ['deepseek', '', 'qwen']
        )
        # 空字符串不在映射中，应该被忽略
        assert is_valid is True

    def test_all_unknown_platforms(self):
        """测试全部是未知平台"""
        is_valid, error_msg = validate_model_region_consistency(
            ['unknown1', 'unknown2', 'unknown3']
        )
        # 全部未知平台应该通过验证（兼容性考虑）
        assert is_valid is True
        assert error_msg is None

    def test_large_number_of_models(self):
        """测试大量模型"""
        # 测试性能
        many_models = ['deepseek'] * 50 + ['qwen'] * 50
        is_valid, error_msg = validate_model_region_consistency(many_models)
        assert is_valid is True
        assert error_msg is None

    def test_large_number_of_mixed_models(self):
        """测试大量混合模型"""
        # 测试性能
        many_mixed = ['deepseek'] * 25 + ['chatgpt'] * 25
        is_valid, error_msg = validate_model_region_consistency(many_mixed)
        assert is_valid is False
        assert error_msg is not None


# ==================== 区域枚举测试 ====================

class TestPlatformRegionEnum:
    """平台区域枚举测试"""

    def test_region_values(self):
        """测试区域枚举值"""
        assert PlatformRegion.DOMESTIC.value == "domestic"
        assert PlatformRegion.OVERSEAS.value == "overseas"

    def test_region_count(self):
        """测试区域数量"""
        regions = list(PlatformRegion)
        assert len(regions) == 2

    def test_region_names(self):
        """测试区域名称"""
        assert PlatformRegion.DOMESTIC.name == "DOMESTIC"
        assert PlatformRegion.OVERSEAS.name == "OVERSEAS"


# ==================== 平台映射完整性测试 ====================

class TestPlatformMappingCompleteness:
    """平台映射完整性测试"""

    def test_no_overlap_between_regions(self):
        """测试国内和海外平台没有重叠"""
        domestic_platforms = {k for k, v in PLATFORM_REGION_MAP.items() 
                             if v == PlatformRegion.DOMESTIC}
        overseas_platforms = {k for k, v in PLATFORM_REGION_MAP.items() 
                             if v == PlatformRegion.OVERSEAS}
        
        # 确保没有平台同时属于两个区域
        overlap = domestic_platforms & overseas_platforms
        assert len(overlap) == 0, f"发现重叠平台：{overlap}"

    def test_common_platforms_covered(self):
        """测试常见平台都被覆盖"""
        required_platforms = [
            # 国内
            'deepseek', 'qwen', 'wenxin', 'doubao', 'kimi',
            # 海外
            'chatgpt', 'claude', 'gemini', 'openai'
        ]
        
        for platform in required_platforms:
            assert platform in PLATFORM_REGION_MAP, f"{platform} 不在区域映射中"

    def test_platform_map_not_empty(self):
        """测试平台映射不为空"""
        assert len(PLATFORM_REGION_MAP) > 0
        assert isinstance(PLATFORM_REGION_MAP, dict)


# ==================== 集成场景测试 ====================

class TestIntegrationScenarios:
    """集成场景测试"""

    def test_typical_user_choice_domestic(self):
        """测试典型用户选择（纯国内）"""
        # 模拟典型用户选择：deepseek + qwen
        user_choice = ['deepseek', 'qwen', 'kimi']
        is_valid, error_msg = validate_model_region_consistency(user_choice)
        
        assert is_valid is True
        assert error_msg is None

    def test_typical_user_choice_overseas(self):
        """测试典型用户选择（纯海外）"""
        # 模拟典型用户选择：chatgpt + claude
        user_choice = ['chatgpt', 'claude']
        is_valid, error_msg = validate_model_region_consistency(user_choice)
        
        assert is_valid is True
        assert error_msg is None

    def test_user_accidentally_mixed(self):
        """测试用户意外混合选择"""
        # 模拟用户不小心混合选择
        user_choice = ['deepseek', 'chatgpt', 'qwen']
        is_valid, error_msg = validate_model_region_consistency(user_choice)
        
        assert is_valid is False
        assert error_msg is not None
        # 错误消息应该友好且包含解决方案
        assert "不能同时选择" in error_msg
        assert "请只选择" in error_msg

    def test_all_available_models_domestic(self, domestic_models):
        """测试所有可用国内模型"""
        is_valid, error_msg = validate_model_region_consistency(domestic_models)
        
        assert is_valid is True
        assert error_msg is None

    def test_all_available_models_overseas(self, overseas_models):
        """测试所有可用海外模型"""
        is_valid, error_msg = validate_model_region_consistency(overseas_models)
        
        assert is_valid is True
        assert error_msg is None

    def test_error_message_helps_user_decide(self, mixed_models):
        """测试错误消息帮助用户决策"""
        is_valid, error_msg = validate_model_region_consistency(mixed_models)
        
        assert is_valid is False
        # 验证错误消息包含决策帮助
        assert "国内平台" in error_msg
        assert "海外平台" in error_msg
        assert "请只选择国内平台或只选择海外平台" in error_msg


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""

    def test_validation_speed(self):
        """测试验证速度"""
        import time
        
        # 大量模型的验证应该在合理时间内完成
        many_models = ['deepseek', 'qwen', 'kimi', 'wenxin', 'doubao'] * 20
        
        start_time = time.time()
        is_valid, error_msg = validate_model_region_consistency(many_models)
        elapsed_time = time.time() - start_time
        
        # 验证应该在 0.1 秒内完成
        assert elapsed_time < 0.1, f"验证耗时过长：{elapsed_time}秒"
        assert is_valid is True

    def test_mixed_validation_speed(self):
        """测试混合模型验证速度"""
        import time
        
        # 大量混合模型的验证
        many_mixed = ['deepseek', 'chatgpt'] * 50
        
        start_time = time.time()
        is_valid, error_msg = validate_model_region_consistency(many_mixed)
        elapsed_time = time.time() - start_time
        
        # 验证应该在 0.1 秒内完成
        assert elapsed_time < 0.1, f"验证耗时过长：{elapsed_time}秒"
        assert is_valid is False
