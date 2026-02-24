#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌诊断报告存储架构 - 单元测试

测试范围：
1. Repository 层测试
2. Service 层测试
3. 文件归档测试
4. 数据完整性测试

作者：测试工程师
日期：2026-02-26
"""

import sys
import os
import json
import unittest
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wechat_backend.diagnosis_report_repository import (
    DiagnosisReportRepository,
    DiagnosisResultRepository,
    DiagnosisAnalysisRepository,
    FileArchiveManager,
    calculate_checksum,
    verify_checksum
)
from wechat_backend.diagnosis_report_service import (
    DiagnosisReportService,
    ReportValidationService
)


class TestDiagnosisReportRepository(unittest.TestCase):
    """诊断报告仓库测试"""
    
    def setUp(self):
        """测试前准备"""
        self.repo = DiagnosisReportRepository()
        self.test_execution_id = f"test-exec-{datetime.now().timestamp()}"
        self.test_user_id = "user-test-001"
        self.test_config = {
            'brand_name': '测试品牌',
            'competitor_brands': ['竞品 1', '竞品 2'],
            'selected_models': ['doubao', 'qwen'],
            'custom_questions': ['问题 1', '问题 2']
        }
    
    def test_create_report(self):
        """测试创建报告"""
        report_id = self.repo.create(
            self.test_execution_id,
            self.test_user_id,
            self.test_config
        )
        
        self.assertIsInstance(report_id, int)
        self.assertGreater(report_id, 0)
        print(f"✅ 创建报告成功：{report_id}")
    
    def test_get_report(self):
        """测试获取报告"""
        # 先创建
        report_id = self.repo.create(
            self.test_execution_id,
            self.test_user_id,
            self.test_config
        )
        
        # 再获取
        report = self.repo.get_by_execution_id(self.test_execution_id)
        
        self.assertIsNotNone(report)
        self.assertEqual(report['execution_id'], self.test_execution_id)
        self.assertEqual(report['brand_name'], '测试品牌')
        print(f"✅ 获取报告成功：{report['execution_id']}")
    
    def test_update_status(self):
        """测试更新状态"""
        # 先创建
        self.repo.create(
            self.test_execution_id,
            self.test_user_id,
            self.test_config
        )
        
        # 更新状态
        success = self.repo.update_status(
            self.test_execution_id,
            'completed',
            100,
            'completed',
            True
        )
        
        self.assertTrue(success)
        
        # 验证更新
        report = self.repo.get_by_execution_id(self.test_execution_id)
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['progress'], 100)
        print(f"✅ 更新状态成功：{self.test_execution_id}")
    
    def test_get_user_history(self):
        """测试获取用户历史"""
        # 创建多个报告
        for i in range(3):
            self.repo.create(
                f"{self.test_execution_id}-{i}",
                self.test_user_id,
                self.test_config
            )
        
        # 获取历史
        history = self.repo.get_user_history(self.test_user_id, limit=10)
        
        self.assertGreater(len(history), 0)
        print(f"✅ 获取用户历史成功：{len(history)} 条")


class TestDiagnosisResultRepository(unittest.TestCase):
    """诊断结果仓库测试"""
    
    def setUp(self):
        """测试前准备"""
        self.repo = DiagnosisResultRepository()
        self.test_execution_id = f"test-result-{datetime.now().timestamp()}"
        self.test_report_id = 1
        self.test_result = {
            'brand': '测试品牌',
            'question': '测试问题',
            'model': 'doubao',
            'response': {
                'content': 'AI 回答内容',
                'latency': 12.5
            },
            'geo_data': {
                'brand_mentioned': True,
                'rank': 1,
                'sentiment': 0.8
            },
            'quality_score': 85,
            'quality_level': 'high'
        }
    
    def test_add_result(self):
        """测试添加结果"""
        result_id = self.repo.add(
            self.test_report_id,
            self.test_execution_id,
            self.test_result
        )
        
        self.assertIsInstance(result_id, int)
        self.assertGreater(result_id, 0)
        print(f"✅ 添加结果成功：{result_id}")
    
    def test_get_results(self):
        """测试获取结果"""
        # 先添加
        self.repo.add(
            self.test_report_id,
            self.test_execution_id,
            self.test_result
        )
        
        # 再获取
        results = self.repo.get_by_execution_id(self.test_execution_id)
        
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['brand'], '测试品牌')
        print(f"✅ 获取结果成功：{len(results)} 条")


class TestDiagnosisAnalysisRepository(unittest.TestCase):
    """诊断分析仓库测试"""
    
    def setUp(self):
        """测试前准备"""
        self.repo = DiagnosisAnalysisRepository()
        self.test_execution_id = f"test-analysis-{datetime.now().timestamp()}"
        self.test_report_id = 1
        self.test_analysis = {
            'competitive_analysis': {
                'brand_ranking': ['测试品牌', '竞品 1', '竞品 2']
            }
        }
    
    def test_add_analysis(self):
        """测试添加分析"""
        analysis_id = self.repo.add(
            self.test_report_id,
            self.test_execution_id,
            'competitive_analysis',
            self.test_analysis['competitive_analysis']
        )
        
        self.assertIsInstance(analysis_id, int)
        self.assertGreater(analysis_id, 0)
        print(f"✅ 添加分析成功：{analysis_id}")
    
    def test_get_analysis(self):
        """测试获取分析"""
        # 先添加
        self.repo.add(
            self.test_report_id,
            self.test_execution_id,
            'competitive_analysis',
            self.test_analysis['competitive_analysis']
        )
        
        # 再获取
        analysis = self.repo.get_by_execution_id(self.test_execution_id)
        
        self.assertIn('competitive_analysis', analysis)
        print(f"✅ 获取分析成功：{list(analysis.keys())}")


class TestFileArchiveManager(unittest.TestCase):
    """文件归档管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = FileArchiveManager()
        self.test_execution_id = f"test-archive-{datetime.now().timestamp()}"
        self.test_report_data = {
            'meta': {
                'execution_id': self.test_execution_id,
                'created_at': datetime.now().isoformat()
            },
            'report': {
                'brand_name': '测试品牌'
            },
            'results': [
                {
                    'brand': '测试品牌',
                    'question': '测试问题',
                    'model': 'doubao'
                }
            ]
        }
    
    def test_save_report(self):
        """测试保存报告"""
        filepath = self.manager.save_report(
            self.test_execution_id,
            self.test_report_data
        )
        
        self.assertTrue(os.path.exists(filepath))
        print(f"✅ 保存报告成功：{filepath}")
    
    def test_get_report(self):
        """测试读取报告"""
        # 先保存
        created_at = datetime.now()
        self.manager.save_report(
            self.test_execution_id,
            self.test_report_data,
            created_at
        )
        
        # 再读取
        data = self.manager.get_report(self.test_execution_id, created_at)
        
        self.assertIsNotNone(data)
        self.assertEqual(data['meta']['execution_id'], self.test_execution_id)
        print(f"✅ 读取报告成功：{data['meta']['execution_id']}")


class TestDataIntegrity(unittest.TestCase):
    """数据完整性测试"""
    
    def test_calculate_checksum(self):
        """测试计算校验和"""
        data = {'key': 'value', 'number': 123}
        checksum = calculate_checksum(data)
        
        self.assertIsInstance(checksum, str)
        self.assertEqual(len(checksum), 64)  # SHA256 长度为 64
        print(f"✅ 计算校验和成功：{checksum[:16]}...")
    
    def test_verify_checksum(self):
        """测试验证校验和"""
        data = {'key': 'value', 'number': 123}
        checksum = calculate_checksum(data)
        
        # 验证正确
        self.assertTrue(verify_checksum(data, checksum))
        
        # 验证错误
        wrong_data = {'key': 'wrong'}
        self.assertFalse(verify_checksum(wrong_data, checksum))
        
        print(f"✅ 验证校验和成功")


class TestReportValidation(unittest.TestCase):
    """报告验证测试"""
    
    def test_validate_valid_report(self):
        """测试验证有效报告"""
        service = ReportValidationService()
        
        valid_report = {
            'execution_id': 'test-001',
            'user_id': 'user-001',
            'brand_name': '测试品牌',
            'created_at': datetime.now().isoformat(),
            'results': [
                {
                    'brand': '测试品牌',
                    'question': '测试问题',
                    'model': 'doubao'
                }
            ],
            'analysis': {
                'competitive_analysis': {}
            }
        }
        
        result = service.validate_report(valid_report)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        print(f"✅ 验证有效报告成功")
    
    def test_validate_invalid_report(self):
        """测试验证无效报告"""
        service = ReportValidationService()
        
        invalid_report = {
            'execution_id': 'test-001',
            # 缺少其他必填字段
            'results': 'not a list'  # 应该是数组
        }
        
        result = service.validate_report(invalid_report)
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
        print(f"✅ 验证无效报告成功：{len(result['errors'])} 个错误")


def run_tests():
    """运行所有测试"""
    print("="*60)
    print("品牌诊断报告存储架构 - 单元测试")
    print("="*60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosisReportRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosisResultRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosisAnalysisRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestFileArchiveManager))
    suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
    suite.addTests(loader.loadTestsFromTestCase(TestReportValidation))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"总测试数：{result.testsRun}")
    print(f"成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")
    
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
