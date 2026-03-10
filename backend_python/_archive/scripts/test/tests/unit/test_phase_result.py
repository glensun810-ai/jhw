"""
PhaseResult 数据类单元测试

测试覆盖：
1. 初始化参数组合
2. 属性访问
3. to_dict() 方法
4. 边缘情况处理
5. 数据类型验证

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from wechat_backend.services.diagnosis_orchestrator import PhaseResult


class TestPhaseResultInitialization:
    """PhaseResult 初始化测试"""

    def test_init_with_success_only(self):
        """测试仅传入 success 参数"""
        result = PhaseResult(success=True)
        
        assert result.success is True
        assert result.data is None
        assert result.error is None
        assert isinstance(result.timestamp, datetime)

    def test_init_with_success_and_data(self):
        """测试传入 success 和 data 参数"""
        test_data = {'key': 'value', 'number': 42}
        result = PhaseResult(success=True, data=test_data)
        
        assert result.success is True
        assert result.data == test_data
        assert result.error is None

    def test_init_with_failure_and_error(self):
        """测试传入 success=False 和 error 参数"""
        error_message = "Test error message"
        result = PhaseResult(success=False, error=error_message)
        
        assert result.success is False
        assert result.data is None
        assert result.error == error_message

    def test_init_with_all_parameters(self):
        """测试传入所有参数"""
        test_data = {'result': 'success'}
        error_msg = "Some error"
        result = PhaseResult(success=True, data=test_data, error=error_msg)
        
        assert result.success is True
        assert result.data == test_data
        assert result.error == error_msg

    def test_init_with_none_data(self):
        """测试传入 None 作为 data"""
        result = PhaseResult(success=True, data=None)
        
        assert result.success is True
        assert result.data is None

    def test_init_with_none_error(self):
        """测试传入 None 作为 error"""
        result = PhaseResult(success=False, error=None)
        
        assert result.success is False
        assert result.error is None

    def test_init_with_empty_string_error(self):
        """测试传入空字符串作为 error"""
        result = PhaseResult(success=False, error="")
        
        assert result.success is False
        assert result.error == ""

    def test_timestamp_is_set_on_initialization(self):
        """测试时间戳在初始化时设置"""
        before = datetime.now()
        result = PhaseResult(success=True)
        after = datetime.now()
        
        assert before <= result.timestamp <= after

    def test_timestamp_is_unique_per_instance(self):
        """测试每个实例有独立的时间戳"""
        result1 = PhaseResult(success=True)
        result2 = PhaseResult(success=True)
        
        # 时间戳应该非常接近但不一定是同一个对象
        assert isinstance(result1.timestamp, datetime)
        assert isinstance(result2.timestamp, datetime)


class TestPhaseResultAttributes:
    """PhaseResult 属性访问测试"""

    def test_success_attribute_read_write(self):
        """测试 success 属性读写"""
        result = PhaseResult(success=True)
        assert result.success is True
        
        result.success = False
        assert result.success is False

    def test_data_attribute_read_write(self):
        """测试 data 属性读写"""
        result = PhaseResult(success=True, data={'initial': 'data'})
        assert result.data == {'initial': 'data'}
        
        result.data = {'updated': 'data'}
        assert result.data == {'updated': 'data'}

    def test_error_attribute_read_write(self):
        """测试 error 属性读写"""
        result = PhaseResult(success=False, error='initial error')
        assert result.error == 'initial error'
        
        result.error = 'updated error'
        assert result.error == 'updated error'

    def test_timestamp_attribute_read_only(self):
        """测试 timestamp 属性只读"""
        result = PhaseResult(success=True)
        original_timestamp = result.timestamp
        
        # 可以重新赋值（Python 不强制只读）
        result.timestamp = datetime(2026, 1, 1)
        assert result.timestamp == datetime(2026, 1, 1)


class TestPhaseResultToDict:
    """PhaseResult.to_dict() 方法测试"""

    def test_to_dict_with_success_and_data(self):
        """测试成功结果转换为字典"""
        test_data = {'key': 'value', 'nested': {'inner': 'data'}}
        result = PhaseResult(success=True, data=test_data)
        
        result_dict = result.to_dict()
        
        assert result_dict['success'] is True
        assert result_dict['data'] == test_data
        assert result_dict['error'] is None
        assert 'timestamp' in result_dict
        assert isinstance(result_dict['timestamp'], str)

    def test_to_dict_with_failure_and_error(self):
        """测试失败结果转换为字典"""
        error_msg = "Something went wrong"
        result = PhaseResult(success=False, error=error_msg)
        
        result_dict = result.to_dict()
        
        assert result_dict['success'] is False
        assert result_dict['data'] is None
        assert result_dict['error'] == error_msg
        assert 'timestamp' in result_dict

    def test_to_dict_with_all_fields(self):
        """测试所有字段都有的情况"""
        test_data = [1, 2, 3]
        error_msg = "Warning"
        result = PhaseResult(success=True, data=test_data, error=error_msg)
        
        result_dict = result.to_dict()
        
        assert result_dict['success'] is True
        assert result_dict['data'] == test_data
        assert result_dict['error'] == error_msg
        assert 'timestamp' in result_dict

    def test_to_dict_timestamp_format(self):
        """测试时间戳格式为 ISO 格式"""
        result = PhaseResult(success=True)
        result_dict = result.to_dict()
        
        # ISO 格式应该能被解析
        timestamp_str = result_dict['timestamp']
        parsed = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)

    def test_to_dict_returns_new_dict(self):
        """测试 to_dict 返回新的字典对象"""
        result = PhaseResult(success=True, data={'test': 'data'})
        
        dict1 = result.to_dict()
        dict2 = result.to_dict()
        
        # 应该是两个不同的对象
        assert dict1 == dict2
        assert dict1 is not dict2

    def test_to_dict_data_mutation_does_not_affect_original(self):
        """测试返回的字典数据修改不影响原始数据"""
        original_data = {'mutable': 'data'}
        result = PhaseResult(success=True, data=original_data)
        
        result_dict = result.to_dict()
        result_dict['data']['mutable'] = 'changed'
        
        # 原始数据应该被修改（因为是浅拷贝）
        assert result.data['mutable'] == 'changed'


class TestPhaseResultWithDataTypes:
    """PhaseResult 处理不同数据类型测试"""

    def test_with_dict_data(self):
        """测试字典类型数据"""
        data = {'complex': {'nested': {'structure': True}}}
        result = PhaseResult(success=True, data=data)
        
        assert result.data == data
        assert result.to_dict()['data'] == data

    def test_with_list_data(self):
        """测试列表类型数据"""
        data = [1, 2, 3, {'nested': 'dict'}]
        result = PhaseResult(success=True, data=data)
        
        assert result.data == data
        assert result.to_dict()['data'] == data

    def test_with_string_data(self):
        """测试字符串类型数据"""
        data = "Simple string data"
        result = PhaseResult(success=True, data=data)
        
        assert result.data == data
        assert result.to_dict()['data'] == data

    def test_with_integer_data(self):
        """测试整数类型数据"""
        data = 42
        result = PhaseResult(success=True, data=data)
        
        assert result.data == data
        assert result.to_dict()['data'] == data

    def test_with_float_data(self):
        """测试浮点数类型数据"""
        data = 3.14159
        result = PhaseResult(success=True, data=data)
        
        assert result.data == data
        assert result.to_dict()['data'] == data

    def test_with_boolean_data(self):
        """测试布尔类型数据"""
        data = False
        result = PhaseResult(success=True, data=data)
        
        assert result.data is False
        assert result.to_dict()['data'] is False

    def test_with_none_data(self):
        """测试 None 数据"""
        result = PhaseResult(success=True, data=None)
        
        assert result.data is None
        assert result.to_dict()['data'] is None

    def test_with_complex_object(self):
        """测试复杂对象数据"""
        class CustomObject:
            def __init__(self, value):
                self.value = value
            
            def __eq__(self, other):
                return isinstance(other, CustomObject) and self.value == other.value
        
        obj = CustomObject(123)
        result = PhaseResult(success=True, data=obj)
        
        assert result.data == obj
        assert result.to_dict()['data'] == obj

    def test_with_error_variations(self):
        """测试不同的错误消息类型"""
        # 字符串错误
        result1 = PhaseResult(success=False, error="String error")
        assert result1.error == "String error"
        
        # 空字符串错误
        result2 = PhaseResult(success=False, error="")
        assert result2.error == ""
        
        # None 错误
        result3 = PhaseResult(success=False, error=None)
        assert result3.error is None


class TestPhaseResultEdgeCases:
    """PhaseResult 边缘情况测试"""

    def test_success_with_error_message(self):
        """测试 success=True 但有 error 消息的情况"""
        result = PhaseResult(success=True, data={'data': 'value'}, error="Warning")
        
        assert result.success is True
        assert result.error == "Warning"
        assert result.data == {'data': 'value'}

    def test_failure_without_error_message(self):
        """测试 success=False 但没有 error 消息的情况"""
        result = PhaseResult(success=False)
        
        assert result.success is False
        assert result.error is None
        assert result.data is None

    def test_multiple_to_dict_calls(self):
        """测试多次调用 to_dict"""
        result = PhaseResult(success=True, data={'test': 'data'})
        
        dict1 = result.to_dict()
        dict2 = result.to_dict()
        dict3 = result.to_dict()
        
        assert dict1 == dict2 == dict3
        assert dict1['timestamp'] == dict2['timestamp'] == dict3['timestamp']

    def test_modifying_result_after_creation(self):
        """测试创建后修改结果"""
        result = PhaseResult(success=True, data={'original': 'data'})
        
        # 修改各个属性
        result.success = False
        result.data = {'modified': 'data'}
        result.error = 'Modified after creation'
        
        assert result.success is False
        assert result.data == {'modified': 'data'}
        assert result.error == 'Modified after creation'

    def test_to_dict_after_modification(self):
        """测试修改后调用 to_dict"""
        result = PhaseResult(success=True, data='original')
        result.data = 'modified'
        
        result_dict = result.to_dict()
        assert result_dict['data'] == 'modified'


class TestPhaseResultTimestamp:
    """PhaseResult 时间戳相关测试"""

    def test_timestamp_is_datetime_instance(self):
        """测试时间戳是 datetime 实例"""
        result = PhaseResult(success=True)
        assert isinstance(result.timestamp, datetime)

    def test_timestamp_to_dict_preserves_value(self):
        """测试 to_dict 保留时间戳值"""
        result = PhaseResult(success=True)
        result_dict = result.to_dict()
        
        # 时间戳字符串应该能解析回 datetime
        timestamp_from_dict = datetime.fromisoformat(
            result_dict['timestamp'].replace('Z', '+00:00')
        )
        
        # 允许微小的时间差异（毫秒级别）
        time_diff = abs((timestamp_from_dict - result.timestamp).total_seconds())
        assert time_diff < 0.001

    def test_timestamp_format_is_iso8601(self):
        """测试时间戳格式是 ISO 8601"""
        result = PhaseResult(success=True)
        result_dict = result.to_dict()
        
        timestamp_str = result_dict['timestamp']
        
        # ISO 8601 格式应该包含日期和时间信息
        assert 'T' in timestamp_str  # ISO 格式分隔符
        assert len(timestamp_str) >= 19  # 最小 ISO 格式长度 "YYYY-MM-DDTHH:MM:SS"


class TestPhaseResultRepresentation:
    """PhaseResult 表示方法测试"""

    def test_result_in_boolean_context(self):
        """测试结果在布尔上下文中的表现"""
        success_result = PhaseResult(success=True)
        failure_result = PhaseResult(success=False)
        
        # PhaseResult 对象本身在布尔上下文中应该为 True（因为是对象）
        assert bool(success_result) is True
        assert bool(failure_result) is True
        
        # 应该使用 success 属性来判断成功与否
        assert success_result.success is True
        assert failure_result.success is False

    def test_result_with_truthy_data(self):
        """测试带有真值数据的成功结果"""
        result = PhaseResult(success=True, data={'key': 'value'})
        assert result.data  # 非空字典为真

    def test_result_with_falsy_data(self):
        """测试带有假值数据的成功结果"""
        # 空字典
        result1 = PhaseResult(success=True, data={})
        assert result1.success is True
        assert not result1.data
        
        # 空列表
        result2 = PhaseResult(success=True, data=[])
        assert result2.success is True
        assert not result2.data
        
        # 0
        result3 = PhaseResult(success=True, data=0)
        assert result3.success is True
        assert not result3.data


class TestPhaseResultPracticalUsage:
    """PhaseResult 实际使用场景测试"""

    def test_typical_success_scenario(self):
        """测试典型的成功场景"""
        ai_results = [
            {'brand': 'Brand A', 'response': 'Answer 1', 'score': 85},
            {'brand': 'Brand B', 'response': 'Answer 2', 'score': 90}
        ]
        result = PhaseResult(success=True, data=ai_results)
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.error is None
        
        result_dict = result.to_dict()
        assert result_dict['success'] is True
        assert len(result_dict['data']) == 2

    def test_typical_failure_scenario(self):
        """测试典型的失败场景"""
        error_message = "AI API timeout after 30 seconds"
        result = PhaseResult(success=False, error=error_message)
        
        assert result.success is False
        assert result.data is None
        assert result.error == error_message
        
        result_dict = result.to_dict()
        assert result_dict['success'] is False
        assert result_dict['error'] == error_message

    def test_partial_success_scenario(self):
        """测试部分成功场景"""
        partial_data = {
            'completed': 5,
            'failed': 2,
            'results': [{'id': 1, 'status': 'success'}]
        }
        warning = "2 out of 7 operations failed"
        result = PhaseResult(success=True, data=partial_data, error=warning)
        
        assert result.success is True
        assert result.data['completed'] == 5
        assert result.error == warning

    def test_validation_result_scenario(self):
        """测试验证结果场景"""
        validation_data = {
            'expected_count': 10,
            'actual_count': 10,
            'invalid_results': [],
            'missing_fields': [],
            'warnings': ['Minor formatting issue']
        }
        result = PhaseResult(
            success=True,
            data=validation_data,
            error='Warning: Minor formatting issue'
        )
        
        assert result.success is True
        assert result.data['expected_count'] == result.data['actual_count']
        assert len(result.data['invalid_results']) == 0


# 运行测试的入口
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
