"""
测试新实现的分阶段任务状态和DeepIntelligenceResult功能
"""
import unittest
import json
import uuid
from datetime import datetime

from wechat_backend.models import TaskStatus, TaskStage, DeepIntelligenceResult, BrandTestResult, save_task_status, get_task_status, save_deep_intelligence_result, get_deep_intelligence_result, update_task_stage, save_brand_test_result, get_brand_test_result
from wechat_backend.database import init_db


class TestInfrastructureUpgrade(unittest.TestCase):
    """测试基础设施升维功能"""
    
    def setUp(self):
        """测试前准备"""
        # 初始化数据库
        init_db()
        
        # 创建测试任务ID
        self.test_task_id = str(uuid.uuid4())
        
    def test_task_status_creation(self):
        """测试任务状态创建和存储"""
        # 创建任务状态
        task_status = TaskStatus(
            task_id=self.test_task_id,
            progress=0,
            stage=TaskStage.INIT,
            status_text="正在初始化任务...",
            is_completed=False
        )
        
        # 保存任务状态
        save_task_status(task_status)
        
        # 获取任务状态
        retrieved_status = get_task_status(self.test_task_id)
        
        # 验证数据一致性
        self.assertEqual(retrieved_status.task_id, self.test_task_id)
        self.assertEqual(retrieved_status.progress, 0)
        self.assertEqual(retrieved_status.stage, TaskStage.INIT)
        self.assertEqual(retrieved_status.status_text, "正在初始化任务...")
        self.assertFalse(retrieved_status.is_completed)
        
    def test_task_stage_updates(self):
        """测试任务阶段更新"""
        # 初始状态
        initial_status = TaskStatus(
            task_id=self.test_task_id,
            progress=0,
            stage=TaskStage.INIT,
            status_text="正在初始化任务...",
            is_completed=False
        )
        save_task_status(initial_status)
        
        # 更新到AI_FETCHING阶段
        update_task_stage(self.test_task_id, TaskStage.AI_FETCHING, 25, "正在调取AI数据...")
        
        # 验证更新
        updated_status = get_task_status(self.test_task_id)
        self.assertEqual(updated_status.stage, TaskStage.AI_FETCHING)
        self.assertEqual(updated_status.progress, 25)
        self.assertEqual(updated_status.status_text, "正在调取AI数据...")
        
        # 更新到RANKING_ANALYSIS阶段
        update_task_stage(self.test_task_id, TaskStage.RANKING_ANALYSIS, 75, "正在进行排名分析...")
        
        # 验证更新
        updated_status = get_task_status(self.test_task_id)
        self.assertEqual(updated_status.stage, TaskStage.RANKING_ANALYSIS)
        self.assertEqual(updated_status.progress, 75)
        self.assertEqual(updated_status.status_text, "正在进行排名分析...")
        
        # 更新到SOURCE_TRACING阶段
        update_task_stage(self.test_task_id, TaskStage.SOURCE_TRACING, 90, "正在进行信源追踪分析...")
        
        # 验证更新
        updated_status = get_task_status(self.test_task_id)
        self.assertEqual(updated_status.stage, TaskStage.SOURCE_TRACING)
        self.assertEqual(updated_status.progress, 90)
        self.assertEqual(updated_status.status_text, "正在进行信源追踪分析...")
        
        # 更新到COMPLETED阶段
        update_task_stage(self.test_task_id, TaskStage.COMPLETED, 100, "任务已完成")
        
        # 验证最终状态
        final_status = get_task_status(self.test_task_id)
        self.assertEqual(final_status.stage, TaskStage.COMPLETED)
        self.assertEqual(final_status.progress, 100)
        self.assertTrue(final_status.is_completed)
        self.assertEqual(final_status.status_text, "任务已完成")
        
    def test_deep_intelligence_result(self):
        """测试深度情报结果数据结构"""
        # 创建深度情报结果
        exposure_analysis = {
            'ranking_list': ['品牌A', '品牌B', '品牌C'],
            'brand_details': {
                '品牌A': {
                    'rank': 1,
                    'word_count': 100,
                    'sov_share': 0.5,
                    'sentiment_score': 85
                }
            },
            'unlisted_competitors': ['品牌D']
        }
        
        source_intelligence = {
            'source_pool': [
                {
                    'id': 'source1',
                    'url': 'https://example.com',
                    'site_name': 'Example Site',
                    'citation_count': 10,
                    'domain_authority': 'High'
                }
            ],
            'citation_rank': ['source1']
        }
        
        evidence_chain = [
            {
                'negative_fragment': 'Some negative content',
                'associated_url': 'https://example.com',
                'source_name': 'Model A',
                'risk_level': 'Medium'
            }
        ]
        
        deep_result = DeepIntelligenceResult(
            exposure_analysis=exposure_analysis,
            source_intelligence=source_intelligence,
            evidence_chain=evidence_chain
        )
        
        # 保存深度情报结果
        save_deep_intelligence_result(self.test_task_id, deep_result)
        
        # 获取深度情报结果
        retrieved_result = get_deep_intelligence_result(self.test_task_id)
        
        # 验证数据一致性
        self.assertEqual(retrieved_result.exposure_analysis, exposure_analysis)
        self.assertEqual(retrieved_result.source_intelligence, source_intelligence)
        self.assertEqual(retrieved_result.evidence_chain, evidence_chain)
        
    def test_api_endpoints_simulation(self):
        """模拟API端点功能测试"""
        # 测试任务提交和状态更新流程
        task_id = str(uuid.uuid4())

        # 初始化任务
        initial_status = TaskStatus(
            task_id=task_id,
            progress=0,
            stage=TaskStage.INIT,
            status_text="正在初始化任务...",
            is_completed=False
        )
        save_task_status(initial_status)

        # 模拟各个阶段的更新
        stages_to_test = [
            (TaskStage.AI_FETCHING, 25, "正在调取AI数据..."),
            (TaskStage.RANKING_ANALYSIS, 50, "正在进行排名分析..."),
            (TaskStage.SOURCE_TRACING, 75, "正在进行信源追踪分析..."),
            (TaskStage.COMPLETED, 100, "任务已完成")
        ]

        for stage, progress, status_text in stages_to_test:
            update_task_stage(task_id, stage, progress, status_text)

            # 获取当前状态
            current_status = get_task_status(task_id)

            # 验证状态
            self.assertEqual(current_status.stage, stage)
            self.assertEqual(current_status.progress, progress)
            self.assertEqual(current_status.status_text, status_text)

            if stage == TaskStage.COMPLETED:
                self.assertTrue(current_status.is_completed)
            else:
                self.assertFalse(current_status.is_completed)

    def test_brand_test_result_model(self):
        """测试BrandTestResult模型功能"""
        task_id = str(uuid.uuid4())

        # 创建DeepIntelligenceResult对象
        deep_intel_result = DeepIntelligenceResult(
            exposure_analysis={
                'ranking_list': ['品牌A', '品牌B', '品牌C'],
                'brand_details': {
                    '品牌A': {
                        'rank': 1,
                        'word_count': 100,
                        'sov_share': 0.5,
                        'sentiment_score': 85
                    }
                },
                'unlisted_competitors': ['品牌D']
            },
            source_intelligence={
                'source_pool': [
                    {
                        'id': 'source1',
                        'url': 'https://example.com',
                        'site_name': 'Example Site',
                        'citation_count': 10,
                        'domain_authority': 'High'
                    }
                ],
                'citation_rank': ['source1']
            },
            evidence_chain=[
                {
                    'negative_fragment': 'Some negative content',
                    'associated_url': 'https://example.com',
                    'source_name': 'Model A',
                    'risk_level': 'Medium'
                }
            ]
        )

        # 创建BrandTestResult对象
        brand_test_result = BrandTestResult(
            task_id=task_id,
            brand_name='测试品牌',
            ai_models_used=['model1', 'model2'],
            questions_used=['question1', 'question2'],
            overall_score=85.5,
            total_tests=10,
            results_summary={'summary': 'Test summary'},
            detailed_results=[{'result': 'Detailed result'}],
            deep_intelligence_result=deep_intel_result
        )

        # 保存品牌测试结果
        save_brand_test_result(brand_test_result)

        # 获取品牌测试结果
        retrieved_result = get_brand_test_result(task_id)

        # 验证基本属性
        self.assertEqual(retrieved_result.task_id, task_id)
        self.assertEqual(retrieved_result.brand_name, '测试品牌')
        self.assertEqual(retrieved_result.ai_models_used, ['model1', 'model2'])
        self.assertEqual(retrieved_result.questions_used, ['question1', 'question2'])
        self.assertEqual(retrieved_result.overall_score, 85.5)
        self.assertEqual(retrieved_result.total_tests, 10)
        self.assertEqual(retrieved_result.results_summary, {'summary': 'Test summary'})
        self.assertEqual(retrieved_result.detailed_results, [{'result': 'Detailed result'}])

        # 验证深度情报结果
        self.assertEqual(retrieved_result.deep_intelligence_result.exposure_analysis, deep_intel_result.exposure_analysis)
        self.assertEqual(retrieved_result.deep_intelligence_result.source_intelligence, deep_intel_result.source_intelligence)
        self.assertEqual(retrieved_result.deep_intelligence_result.evidence_chain, deep_intel_result.evidence_chain)

    def test_state_machine_transitions(self):
        """测试状态机转换逻辑"""
        task_id = str(uuid.uuid4())

        # 初始状态
        initial_status = TaskStatus(
            task_id=task_id,
            progress=0,
            stage=TaskStage.INIT,
            status_text="正在初始化任务...",
            is_completed=False
        )
        save_task_status(initial_status)

        # 验证初始状态
        current_status = get_task_status(task_id)
        self.assertEqual(current_status.stage, TaskStage.INIT)
        self.assertEqual(current_status.progress, 0)
        self.assertFalse(current_status.is_completed)

        # 测试从INIT到AI_FETCHING的转换
        update_task_stage(task_id, TaskStage.AI_FETCHING, 20, "正在获取AI数据")
        current_status = get_task_status(task_id)
        self.assertEqual(current_status.stage, TaskStage.AI_FETCHING)
        self.assertEqual(current_status.progress, 20)
        self.assertEqual(current_status.status_text, "正在获取AI数据")

        # 测试从AI_FETCHING到RANKING_ANALYSIS的转换
        update_task_stage(task_id, TaskStage.RANKING_ANALYSIS, 50, "正在进行排名分析")
        current_status = get_task_status(task_id)
        self.assertEqual(current_status.stage, TaskStage.RANKING_ANALYSIS)
        self.assertEqual(current_status.progress, 50)
        self.assertEqual(current_status.status_text, "正在进行排名分析")

        # 测试从RANKING_ANALYSIS到SOURCE_TRACING的转换
        update_task_stage(task_id, TaskStage.SOURCE_TRACING, 80, "正在进行信源追踪")
        current_status = get_task_status(task_id)
        self.assertEqual(current_status.stage, TaskStage.SOURCE_TRACING)
        self.assertEqual(current_status.progress, 80)
        self.assertEqual(current_status.status_text, "正在进行信源追踪")

        # 测试到COMPLETED的转换（自动完成状态）
        update_task_stage(task_id, TaskStage.COMPLETED, 100, "任务已完成")
        current_status = get_task_status(task_id)
        self.assertEqual(current_status.stage, TaskStage.COMPLETED)
        self.assertEqual(current_status.progress, 100)
        self.assertTrue(current_status.is_completed)
        self.assertEqual(current_status.status_text, "任务已完成")


if __name__ == '__main__':
    unittest.main()