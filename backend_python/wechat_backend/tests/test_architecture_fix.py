"""
架构修复验证脚本 - P0 架构级修复验证

验证内容:
1. 统一响应格式中间件 (StandardizedResponse)
2. 服务层数据验证器 (ServiceDataValidator)
3. 错误码定义 (DATA_NOT_FOUND)
4. 诊断 API 统一响应格式

作者：系统架构组
日期：2026-03-18
版本：1.0.0
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wechat_backend.error_codes import ErrorCode, BusinessException
from wechat_backend.middleware.response_formatter import StandardizedResponse
from wechat_backend.validators.service_validator import ServiceDataValidator

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_error_codes():
    """测试 1: 验证错误码定义"""
    print_section("测试 1: 错误码定义验证")
    
    # 验证 DATA_NOT_FOUND 是否存在
    assert hasattr(ErrorCode, 'DATA_NOT_FOUND'), "❌ DATA_NOT_FOUND 错误码未定义"
    assert ErrorCode.DATA_NOT_FOUND.code == "6000-012", f"❌ 错误码值错误：{ErrorCode.DATA_NOT_FOUND.code}"
    assert ErrorCode.DATA_NOT_FOUND.http_status == 404, f"❌ HTTP 状态码错误：{ErrorCode.DATA_NOT_FOUND.http_status}"
    
    print(f"✅ DATA_NOT_FOUND 错误码定义正确:")
    print(f"   - Code: {ErrorCode.DATA_NOT_FOUND.code}")
    print(f"   - Message: {ErrorCode.DATA_NOT_FOUND.message}")
    print(f"   - HTTP Status: {ErrorCode.DATA_NOT_FOUND.http_status}")

def test_standardized_response_success():
    """测试 2: 统一响应格式 - 成功场景"""
    print_section("测试 2: 统一响应格式 - 成功场景")
    
    # 测试正常数据
    test_data = {
        'execution_id': 'test_123',
        'results': [{'brand': '测试品牌', 'answer': '答案'}],
        'brandDistribution': {'data': {'测试品牌': 1}, 'totalCount': 1}
    }
    
    # 【修复】Flask jsonify 需要应用上下文
    from flask import Flask
    app = Flask(__name__)
    
    with app.app_context():
        response, status_code = StandardizedResponse.success(
            data=test_data,
            message='测试成功',
            metadata={'version': '1.0'}
        )
        
        assert status_code == 200, f"❌ 状态码错误：{status_code}"
        
        response_json = response.get_json()
        assert response_json['success'] == True, "❌ success 字段错误"
        assert response_json['data'] == test_data, "❌ data 字段错误"
        assert response_json['message'] == '测试成功', "❌ message 字段错误"
        assert response_json['metadata']['version'] == '1.0', "❌ metadata 字段错误"
        assert 'timestamp' in response_json, "❌ timestamp 字段缺失"
        
        print("✅ 成功响应格式正确")
        print(f"   - success: {response_json['success']}")
        print(f"   - message: {response_json['message']}")
        print(f"   - data keys: {list(response_json['data'].keys())}")

def test_standardized_response_empty_data():
    """测试 3: 统一响应格式 - 空数据场景"""
    print_section("测试 3: 统一响应格式 - 空数据场景")
    
    from flask import Flask
    app = Flask(__name__)
    
    # 测试 None 数据
    with app.app_context():
        response, status_code = StandardizedResponse.success(data=None)
        response_json = response.get_json()
        
        assert status_code == 404, f"❌ 状态码应为 404: {status_code}"
        assert response_json['success'] == False, "❌ success 应为 False"
        assert response_json['error']['code'] == ErrorCode.DATA_NOT_FOUND.code, "❌ 错误码错误"
        
        print("✅ None 数据被正确拦截并返回错误")
    
    # 测试空字典数据
    with app.app_context():
        response, status_code = StandardizedResponse.success(data={})
        response_json = response.get_json()
        
        assert status_code == 404, f"❌ 状态码应为 404: {status_code}"
        assert response_json['error']['code'] == ErrorCode.DATA_NOT_FOUND.code, "❌ 错误码错误"
        
        print("✅ 空字典数据被正确拦截并返回错误")

def test_standardized_response_error():
    """测试 4: 统一响应格式 - 错误场景"""
    print_section("测试 4: 统一响应格式 - 错误场景")
    
    from flask import Flask
    app = Flask(__name__)
    
    with app.app_context():
        response, status_code = StandardizedResponse.error(
            ErrorCode.DATA_NOT_FOUND,
            detail={'execution_id': 'test_123'},
            http_status=404
        )
        
        response_json = response.get_json()
        
        assert status_code == 404, f"❌ 状态码错误：{status_code}"
        assert response_json['success'] == False, "❌ success 应为 False"
        assert response_json['error']['code'] == ErrorCode.DATA_NOT_FOUND.code, "❌ 错误码错误"
        assert response_json['error']['detail']['execution_id'] == 'test_123', "❌ detail 字段错误"
        assert 'timestamp' in response_json, "❌ timestamp 字段缺失"
        
        print("✅ 错误响应格式正确")
        print(f"   - success: {response_json['success']}")
        print(f"   - error.code: {response_json['error']['code']}")
        print(f"   - error.message: {response_json['error']['message']}")

def test_service_validator_valid_report():
    """测试 5: 服务层验证器 - 有效报告"""
    print_section("测试 5: 服务层验证器 - 有效报告")
    
    valid_report = {
        'execution_id': 'test_123',
        'results': [{'brand': '测试品牌', 'answer': '答案'}],
        'brandAnalysis': {'score': 85},
        'status': 'completed'
    }
    
    result = ServiceDataValidator.validate_report_data(valid_report, 'test_123')
    
    assert result == True, "❌ 验证应返回 True"
    print("✅ 有效报告验证通过")

def test_service_validator_none_report():
    """测试 6: 服务层验证器 - None 报告"""
    print_section("测试 6: 服务层验证器 - None 报告")
    
    try:
        ServiceDataValidator.validate_report_data(None, 'test_123')
        assert False, "❌ 应抛出 ReportException"
    except BusinessException as e:
        assert e.error_code == ErrorCode.REPORT_NOT_FOUND, f"❌ 错误码错误：{e.error_code}"
        print("✅ None 报告被正确拦截并抛出异常")
        print(f"   - 错误码：{e.error_code.code}")
        print(f"   - 错误消息：{e.message}")

def test_service_validator_empty_dict_report():
    """测试 7: 服务层验证器 - 空字典报告"""
    print_section("测试 7: 服务层验证器 - 空字典报告")
    
    try:
        ServiceDataValidator.validate_report_data({}, 'test_123')
        assert False, "❌ 应抛出 ReportException"
    except BusinessException as e:
        assert e.error_code == ErrorCode.DATA_NOT_FOUND, f"❌ 错误码错误：{e.error_code}"
        print("✅ 空字典报告被正确拦截并抛出异常")
        print(f"   - 错误码：{e.error_code.code}")
        print(f"   - 错误消息：{e.message}")

def test_service_validator_partial_data():
    """测试 8: 服务层验证器 - 部分数据报告"""
    print_section("测试 8: 服务层验证器 - 部分数据报告")
    
    # 有 execution_id 但无核心数据的报告
    partial_report = {
        'execution_id': 'test_123',
        'status': 'completed',
        'created_at': '2026-03-18T10:00:00'
    }
    
    result = ServiceDataValidator.validate_report_data(partial_report, 'test_123')
    
    assert result == True, "❌ 验证应返回 True（部分成功）"
    assert 'qualityHints' in partial_report, "❌ 应添加质量警告"
    assert partial_report['qualityHints']['partial_data'] == True, "❌ partial_data 标志错误"
    assert len(partial_report['qualityHints']['warnings']) > 0, "❌ 警告列表应为空"
    
    print("✅ 部分数据报告通过验证并添加质量警告")
    print(f"   - warnings: {partial_report['qualityHints']['warnings']}")

def test_service_validator_missing_field():
    """测试 9: 服务层验证器 - 缺少必填字段"""
    print_section("测试 9: 服务层验证器 - 缺少必填字段")
    
    # 缺少 execution_id 的报告
    invalid_report = {
        'results': [{'brand': '测试品牌'}],
        'status': 'completed'
    }
    
    try:
        ServiceDataValidator.validate_report_data(invalid_report, 'test_123')
        assert False, "❌ 应抛出 ReportException"
    except BusinessException as e:
        assert e.error_code == ErrorCode.REPORT_INCOMPLETE, f"❌ 错误码错误：{e.error_code}"
        print("✅ 缺少必填字段被正确拦截")
        print(f"   - 错误码：{e.error_code.code}")
        print(f"   - 错误消息：{e.message}")

def run_all_tests():
    """运行所有测试"""
    print("\n" + "🏗️ " * 20)
    print("  P0 架构级修复验证测试")
    print("  测试统一响应格式、服务层验证器、错误码定义")
    print("🏗️ " * 20)
    
    tests = [
        test_error_codes,
        test_standardized_response_success,
        test_standardized_response_empty_data,
        test_standardized_response_error,
        test_service_validator_valid_report,
        test_service_validator_none_report,
        test_service_validator_empty_dict_report,
        test_service_validator_partial_data,
        test_service_validator_missing_field
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ 测试失败：{test.__name__}")
            print(f"   错误：{e}")
        except Exception as e:
            failed += 1
            print(f"❌ 测试异常：{test.__name__}")
            print(f"   错误：{e}")
    
    print_section("测试总结")
    print(f"  总测试数：{len(tests)}")
    print(f"  ✅ 通过：{passed}")
    print(f"  ❌ 失败：{failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！架构修复验证成功！")
        return 0
    else:
        print(f"\n⚠️  {failed} 个测试失败，请检查修复实现")
        return 1

if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
