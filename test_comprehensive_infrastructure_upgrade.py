"""
综合测试脚本，验证所有基础设施升维功能
"""
import unittest
import json
import uuid
from datetime import datetime

from wechat_backend.models import TaskStatus, TaskStage, DeepIntelligenceResult, BrandTestResult, save_task_status, get_task_status, save_deep_intelligence_result, get_deep_intelligence_result, update_task_stage, save_brand_test_result, get_brand_test_result
from wechat_backend.database import init_db


class TestComprehensiveInfrastructureUpgrade(unittest.TestCase):
    """综合测试基础设施升维功能"""
    
    def setUp(self):
        """测试前准备"""
        # 初始化数据库
        init_db()
        
        # 创建测试任务ID
        self.test_task_id = str(uuid.uuid4())
        
    def test_full_task_lifecycle(self):
        """测试完整任务生命周期"""
        # 1. 创建初始任务状态
        initial_status = TaskStatus(
            task_id=self.test_task_id,
            progress=0,
            stage=TaskStage.INIT,
            status_text="正在初始化任务...",
            is_completed=False
        )
        save_task_status(initial_status)
        
        # 验证初始状态
        retrieved_status = get_task_status(self.test_task_id)
        self.assertEqual(retrieved_status.stage, TaskStage.INIT)
        self.assertEqual(retrieved_status.progress, 0)
        self.assertFalse(retrieved_status.is_completed)
        
        # 2. 模拟任务执行过程中的状态变化
        update_task_stage(self.test_task_id, TaskStage.AI_FETCHING, 25, "正在获取AI数据...")
        status = get_task_status(self.test_task_id)
        self.assertEqual(status.stage, TaskStage.AI_FETCHING)
        self.assertEqual(status.progress, 25)
        
        update_task_stage(self.test_task_id, TaskStage.RANKING_ANALYSIS, 50, "正在进行排名分析...")
        status = get_task_status(self.test_task_id)
        self.assertEqual(status.stage, TaskStage.RANKING_ANALYSIS)
        self.assertEqual(status.progress, 50)
        
        update_task_stage(self.test_task_id, TaskStage.SOURCE_TRACING, 75, "正在进行信源追踪...")
        status = get_task_status(self.test_task_id)
        self.assertEqual(status.stage, TaskStage.SOURCE_TRACING)
        self.assertEqual(status.progress, 75)
        
        # 3. 创建深度情报结果
        deep_intel_result = DeepIntelligenceResult(
            exposure_analysis={
                'ranking_list': ['品牌A', '品牌B'],
                'brand_details': {
                    '品牌A': {
                        'rank': 1,
                        'word_count': 100,
                        'sov_share': 0.6,
                        'sentiment_score': 85
                    }
                },
                'unlisted_competitors': ['品牌C']
            },
            source_intelligence={
                'source_pool': [
                    {
                        'id': 'source1',
                        'url': 'https://example.com',
                        'site_name': 'Example Site',
                        'citation_count': 5,
                        'domain_authority': 'Medium'
                    }
                ],
                'citation_rank': ['source1']
            },
            evidence_chain=[
                {
                    'negative_fragment': 'Some issue mentioned',
                    'associated_url': 'https://example.com',
                    'source_name': 'Model A',
                    'risk_level': 'Low'
                }
            ]
        )
        save_deep_intelligence_result(self.test_task_id, deep_intel_result)
        
        # 验证深度情报结果保存和获取
        retrieved_deep_result = get_deep_intelligence_result(self.test_task_id)
        self.assertEqual(retrieved_deep_result.exposure_analysis['ranking_list'], ['品牌A', '品牌B'])
        
        # 4. 创建品牌测试结果
        brand_test_result = BrandTestResult(
            task_id=self.test_task_id,
            brand_name='测试品牌',
            ai_models_used=['model1', 'model2'],
            questions_used=['question1'],
            overall_score=80.5,
            total_tests=5,
            results_summary={'summary': 'Test summary'},
            detailed_results=[{'result': 'Detailed result'}],
            deep_intelligence_result=deep_intel_result
        )
        save_brand_test_result(brand_test_result)
        
        # 验证品牌测试结果保存和获取
        retrieved_brand_result = get_brand_test_result(self.test_task_id)
        self.assertEqual(retrieved_brand_result.brand_name, '测试品牌')
        self.assertEqual(retrieved_brand_result.overall_score, 80.5)
        self.assertEqual(len(retrieved_brand_result.detailed_results), 1)
        
        # 5. 完成任务
        update_task_stage(self.test_task_id, TaskStage.COMPLETED, 100, "任务已完成")
        final_status = get_task_status(self.test_task_id)
        self.assertEqual(final_status.stage, TaskStage.COMPLETED)
        self.assertEqual(final_status.progress, 100)
        self.assertTrue(final_status.is_completed)
        
    def test_api_contract_compliance(self):
        """测试API契约合规性"""
        # 创建任务状态
        task_id = str(uuid.uuid4())
        task_status = TaskStatus(
            task_id=task_id,
            progress=30,
            stage=TaskStage.AI_FETCHING,
            status_text="获取AI数据中...",
            is_completed=False,
            created_at=datetime.now().isoformat()
        )
        save_task_status(task_status)
        
        # 获取状态并验证返回格式符合API契约
        retrieved_status = get_task_status(task_id)
        status_dict = retrieved_status.to_dict()
        
        # 验证API契约字段存在
        self.assertIn('task_id', status_dict)
        self.assertIn('progress', status_dict)
        self.assertIn('stage', status_dict)
        self.assertIn('status_text', status_dict)
        self.assertIn('is_completed', status_dict)
        self.assertIn('created_at', status_dict)
        
        # 验证字段类型和值
        self.assertIsInstance(status_dict['task_id'], str)
        self.assertIsInstance(status_dict['progress'], int)
        self.assertIn(status_dict['stage'], ['init', 'ai_fetching', 'ranking_analysis', 'source_tracing', 'completed'])
        self.assertIsInstance(status_dict['status_text'], str)
        self.assertIsInstance(status_dict['is_completed'], bool)
        self.assertIsInstance(status_dict['created_at'], str)
        
    def test_nested_structure_mapping(self):
        """测试嵌套结构映射"""
        task_id = str(uuid.uuid4())
        
        # 创建具有完整嵌套结构的深度情报结果
        deep_intel_result = DeepIntelligenceResult(
            exposure_analysis={
                'ranking_list': ['品牌A', '品牌B', '品牌C', '品牌D'],
                'brand_details': {
                    '品牌A': {
                        'rank': 1,
                        'word_count': 150,
                        'sov_share': 0.45,
                        'sentiment_score': 90
                    },
                    '品牌B': {
                        'rank': 2,
                        'word_count': 120,
                        'sov_share': 0.30,
                        'sentiment_score': 75
                    }
                },
                'unlisted_competitors': ['品牌E', '品牌F']
            },
            source_intelligence={
                'source_pool': [
                    {
                        'id': 'zhihu_001',
                        'url': 'https://zhihu.com/question/123',
                        'site_name': '知乎',
                        'citation_count': 15,
                        'domain_authority': 'High'
                    },
                    {
                        'id': 'baidu_baike_001',
                        'url': 'https://baike.baidu.com/item/brand',
                        'site_name': '百度百科',
                        'citation_count': 8,
                        'domain_authority': 'High'
                    }
                ],
                'citation_rank': ['zhihu_001', 'baidu_baike_001']
            },
            evidence_chain=[
                {
                    'negative_fragment': '该品牌存在续航问题',
                    'associated_url': 'https://example.com/review1',
                    'source_name': '评测网站A',
                    'risk_level': 'Medium'
                },
                {
                    'negative_fragment': '客服响应慢',
                    'associated_url': 'https://example.com/review2',
                    'source_name': '论坛B',
                    'risk_level': 'Low'
                }
            ]
        )
        
        # 保存并验证
        save_deep_intelligence_result(task_id, deep_intel_result)
        retrieved = get_deep_intelligence_result(task_id)
        
        # 验证所有嵌套层级都正确保存和恢复
        self.assertEqual(len(retrieved.exposure_analysis['ranking_list']), 4)
        self.assertIn('品牌A', retrieved.exposure_analysis['brand_details'])
        self.assertEqual(retrieved.exposure_analysis['brand_details']['品牌A']['rank'], 1)
        self.assertEqual(len(retrieved.source_intelligence['source_pool']), 2)
        self.assertEqual(len(retrieved.evidence_chain), 2)
        self.assertEqual(retrieved.evidence_chain[0]['risk_level'], 'Medium')


if __name__ == '__main__':
    unittest.main()