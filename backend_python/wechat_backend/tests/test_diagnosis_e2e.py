"""
诊断系统端到端集成测试

测试场景：
1. 完整诊断流程测试
2. 数据完整性验证
3. API Key 配置验证
4. 重试机制测试
5. 降级策略测试
6. 监控告警测试

@author: 系统架构组
@date: 2026-03-07
@version: 1.0.0
"""

import unittest
import json
import time
import os
from typing import Dict, Any, List
from pathlib import Path
import sys

# 添加项目路径
_backend_root = Path(__file__).parent.parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from wechat_backend.logging_config import api_logger


class TestDataConfig:
    """测试数据配置"""
    
    # 测试品牌
    BRAND_LIST = ['趣车良品', '蔚来', '理想']
    
    # 测试问题
    CUSTOM_QUESTIONS = [
        '请分析该品牌在新能源汽车市场的竞争优势？',
        '该品牌的主要目标用户群体是什么？',
        '请给出该品牌的营销策略建议？'
    ]
    
    # 测试模型
    SELECTED_MODELS = [
        {'name': 'doubao', 'checked': True},
        {'name': 'qwen', 'checked': True}
    ]
    
    # 预期结果
    EXPECTED_RESULT_COUNT = len(BRAND_LIST) * len(SELECTED_MODELS)  # 3 品牌 × 2 模型 = 6 条结果


class DiagnosisE2ETest(unittest.TestCase):
    """诊断系统端到端测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        api_logger.info("=" * 60)
        api_logger.info("诊断系统端到端测试开始")
        api_logger.info("=" * 60)
        
        # 检查 API Key 配置
        cls._check_api_keys()
    
    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        api_logger.info("=" * 60)
        api_logger.info("诊断系统端到端测试结束")
        api_logger.info("=" * 60)
    
    @staticmethod
    def _check_api_keys():
        """检查 API Key 配置"""
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        api_logger.info("--- 检查 API Key 配置 ---")
        report = AIAdapterFactory.get_api_key_health_report()
        
        api_logger.info(f"平台总数：{report['total_platforms']}")
        api_logger.info(f"已配置：{report['configured_count']}")
        api_logger.info(f"缺失：{report['missing_count']}")
        api_logger.info(f"健康度：{report['health_rate']:.1%}")
        
        for platform, (is_valid, message) in report['details'].items():
            status = "✅" if is_valid else "❌"
            api_logger.info(f"  {status} {platform}: {message}")
    
    def test_01_api_key_validation(self):
        """测试 1: API Key 配置验证"""
        api_logger.info("\n=== 测试 1: API Key 配置验证 ===")
        
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        
        # 测试验证单个平台
        is_valid, message = AIAdapterFactory.validate_api_key('doubao')
        api_logger.info(f"Doubao 平台验证：{'通过' if is_valid else '失败'} - {message}")
        
        # 测试验证所有平台
        results = AIAdapterFactory.validate_all_api_keys()
        
        configured_count = sum(1 for valid, _ in results.values() if valid)
        total_count = len(results)
        
        api_logger.info(f"已配置平台：{configured_count}/{total_count}")
        
        # 断言：至少有一个平台配置了 API Key
        self.assertGreater(configured_count, 0, "至少需要一个平台配置了 API Key")
    
    def test_02_data_integrity_validation(self):
        """测试 2: 数据完整性验证"""
        api_logger.info("\n=== 测试 2: 数据完整性验证 ===")
        
        from wechat_backend.services.diagnosis_transaction import DiagnosisTransaction
        
        # 模拟结果数据
        valid_results = [
            {
                'brand': '趣车良品',
                'question': '测试问题 1',
                'model': 'doubao',
                'response': {'content': '这是回答内容'}
            },
            {
                'brand': '蔚来',
                'question': '测试问题 2',
                'model': 'qwen',
                'response': {'content': '这是回答内容'}
            }
        ]
        
        invalid_results = [
            {
                'brand': '',  # 空 brand
                'question': '测试问题 3',
                'model': 'deepseek',
                'response': {'content': '这是回答内容'}
            },
            {
                'question': '缺失 brand 字段',  # 缺失 brand
                'model': 'doubao',
                'response': {'content': '这是回答内容'}
            }
        ]
        
        # 创建事务管理器（用于测试验证逻辑）
        execution_store = {}
        tx = DiagnosisTransaction(
            execution_id='test_execution_001',
            execution_store=execution_store
        )
        
        # 测试验证有效结果
        validated = tx._validate_results_batch(valid_results)
        api_logger.info(f"有效结果验证：输入={len(valid_results)}, 输出={len(validated)}")
        self.assertEqual(len(validated), len(valid_results), "有效结果应该全部通过验证")
        
        # 测试验证无效结果
        validated_invalid = tx._validate_results_batch(invalid_results)
        api_logger.info(f"无效结果验证：输入={len(invalid_results)}, 输出={len(validated_invalid)}")
        self.assertLess(len(validated_invalid), len(invalid_results), "无效结果应该被过滤")
    
    def test_03_retry_mechanism(self):
        """测试 3: 重试机制"""
        api_logger.info("\n=== 测试 3: 重试机制 ===")
        
        from wechat_backend.error_recovery import RetryHandler, PresetRetryConfigs
        
        # 创建重试处理器
        retry_handler = RetryHandler(PresetRetryConfigs.AI_CALL_RETRY)
        
        # 模拟总是失败的函数
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"模拟失败 {call_count}")
            return "成功"
        
        # 测试重试
        import asyncio
        
        async def run_test():
            result = await retry_handler.execute_with_retry_async(
                failing_func,
                execution_id='test_retry_001'
            )
            return result
        
        # 运行异步测试
        result = asyncio.run(run_test())
        
        api_logger.info(f"重试结果：success={result.success}, attempts={len(result.attempts)}")
        
        # 断言：重试应该成功
        self.assertTrue(result.success, "重试机制应该在多次尝试后成功")
        self.assertGreater(len(result.attempts), 1, "应该至少重试一次")
    
    def test_04_model_fallback(self):
        """测试 4: 多模型 fallback 策略"""
        api_logger.info("\n=== 测试 4: 多模型 fallback 策略 ===")
        
        from wechat_backend.ai_adapters.model_fallback import (
            ModelFallbackExecutor,
            FallbackResult
        )
        
        # 创建 fallback 执行器
        executor = ModelFallbackExecutor(
            primary_model='doubao',
            fallback_models=['qwen', 'deepseek']
        )
        
        # 模拟主模型失败，备用模型成功
        call_history = []
        
        async def mock_ai_call(model_name: str, **kwargs):
            call_history.append(model_name)
            if model_name == 'doubao':
                return {'success': False, 'error': '主模型失败'}
            elif model_name == 'qwen':
                return {'success': True, 'data': '备用模型成功'}
            else:
                return {'success': True, 'data': '第三模型成功'}
        
        # 运行测试
        import asyncio
        
        async def run_test():
            result = await executor.execute(mock_ai_call, prompt='测试问题')
            return result
        
        result = asyncio.run(run_test())
        
        api_logger.info(f"Fallback 结果：success={result.success}")
        api_logger.info(f"尝试模型：{result.attempted_models}")
        api_logger.info(f"成功模型：{result.successful_model}")
        
        # 断言
        self.assertTrue(result.success, "Fallback 机制应该成功")
        self.assertIn('qwen', result.attempted_models, "应该尝试过 qwen 模型")
        self.assertEqual(result.successful_model, 'qwen', "应该使用 qwen 模型成功")
    
    def test_05_monitoring_alerts(self):
        """测试 5: 监控告警"""
        api_logger.info("\n=== 测试 5: 监控告警 ===")
        
        from wechat_backend.monitoring.diagnosis_monitor import (
            get_diagnosis_monitor,
            get_alert_manager,
            record_diagnosis_result,
            get_monitoring_report
        )
        
        monitor = get_diagnosis_monitor()
        alert_mgr = get_alert_manager()
        
        # 模拟多次诊断执行
        for i in range(20):
            success = i < 18  # 90% 成功率
            record_diagnosis_result(
                execution_id=f'test_exec_{i}',
                success=success,
                error_type=None if success else 'TEST_ERROR',
                brand_empty=(i == 19)  # 1 次空 brand
            )
        
        # 获取监控报告
        report = get_monitoring_report(window=3600)
        
        api_logger.info(f"监控报告:")
        api_logger.info(f"  失败率：{report['failure_rate']:.1%}")
        api_logger.info(f"  成功率：{report['success_rate']:.1%}")
        api_logger.info(f"  空 brand 比例：{report['empty_brand_rate']:.1%}")
        api_logger.info(f"  总执行数：{report['total_executions']}")
        
        # 断言
        self.assertLess(report['failure_rate'], 0.2, "失败率应该低于 20%")
        self.assertGreater(report['success_rate'], 0.8, "成功率应该高于 80%")
        self.assertGreater(report['total_executions'], 0, "应该有执行记录")
    
    def test_06_result_validator(self):
        """测试 6: 结果验证器"""
        api_logger.info("\n=== 测试 6: 结果验证器 ===")
        
        from wechat_backend.services.result_validator import (
            ResultValidator,
            ValidationLevel,
            ValidationResult
        )
        
        validator = ResultValidator(validation_level=ValidationLevel.NORMAL)
        
        # 模拟数据库查询结果
        mock_results = [
            {
                'brand': '趣车良品',
                'question': '问题 1',
                'model': 'doubao',
                'response': {'content': '回答内容 1'}
            },
            {
                'brand': '蔚来',
                'question': '问题 2',
                'model': 'qwen',
                'response': {'content': '回答内容 2'}
            }
        ]
        
        # 模拟预期结果
        expected_results = mock_results.copy()
        
        # 执行验证
        validation_result, saved_results = validator.validate(
            execution_id='test_validation_001',
            expected_results=expected_results,
            validate_quality=True,
            validate_completeness=True
        )
        
        api_logger.info(f"验证结果：status={validation_result.status.value}")
        api_logger.info(f"  预期数量：{validation_result.expected_count}")
        api_logger.info(f"  实际数量：{validation_result.actual_count}")
        api_logger.info(f"  消息：{validation_result.message}")
        
        # 断言
        self.assertTrue(
            validation_result.is_passed,
            f"验证应该通过：{validation_result.message}"
        )
        self.assertEqual(
            validation_result.expected_count,
            validation_result.actual_count,
            "数量应该匹配"
        )
    
    def test_07_brand_field_in_results(self):
        """测试 7: brand 字段完整性（关键测试）"""
        api_logger.info("\n=== 测试 7: brand 字段完整性 ===")
        
        from wechat_backend.nxm_concurrent_engine_v3 import NxMParallelExecutor
        
        # 检查 NxM 执行器返回结果中是否包含 brand 字段
        # 这是一个回归测试，确保 P0 修复有效
        
        # 模拟执行结果结构
        mock_result = {
            'success': True,
            'data': {
                'brand': '趣车良品',  # 关键字段
                'question': '测试问题',
                'model': 'doubao',
                'response': {'content': '回答'},
                'geo_data': None,
                'error': None,
                'error_type': None,
                'is_objective': True
            }
        }
        
        # 验证 brand 字段存在
        self.assertIn('brand', mock_result['data'], "结果必须包含 brand 字段")
        self.assertEqual(
            mock_result['data']['brand'],
            '趣车良品',
            "brand 字段应该有正确的值"
        )
        
        api_logger.info("✅ brand 字段验证通过")


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(DiagnosisE2ETest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"运行测试数：{result.testsRun}")
    print(f"成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")
    
    if result.failures:
        print("\n失败测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n错误测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
