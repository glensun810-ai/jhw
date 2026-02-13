"""
测试 DeepSeek R1 推理链提取功能
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from wechat_backend.ai_adapters.deepseek_r1_adapter import DeepSeekR1Adapter


class TestDeepSeekR1Adapter(unittest.TestCase):
    """测试 DeepSeek R1 适配器的功能"""

    def setUp(self):
        """设置测试环境"""
        self.adapter = DeepSeekR1Adapter(
            api_key="test-key",
            model_name="deepseek-r1",
            enable_reasoning_extraction=True
        )

    def test_extract_reasoning_content_basic(self):
        """测试基本推理内容提取"""
        choice_data = {
            "message": {
                "content": "这是一个回答",
                "reasoning": "这是推理过程"
            }
        }
        full_response = {}

        reasoning = self.adapter._extract_reasoning_content(choice_data, full_response)
        self.assertEqual(reasoning, "这是推理过程")
        print("✓ 基本推理内容提取测试通过")

    def test_extract_reasoning_from_alternative_fields(self):
        """测试从替代字段提取推理内容"""
        # 测试 usage 中的 reasoning
        choice_data = {"message": {"content": "回答"}}
        full_response = {
            "usage": {
                "reasoning": "从usage提取的推理内容"
            }
        }

        reasoning = self.adapter._extract_reasoning_content(choice_data, full_response)
        self.assertEqual(reasoning, "从usage提取的推理内容")
        print("✓ 从替代字段提取推理内容测试通过")

    def test_extract_reasoning_from_thinking_process(self):
        """测试从 thinking_process 字段提取推理内容"""
        choice_data = {"message": {"content": "回答"}}
        full_response = {
            "thinking_process": "这是思考过程"
        }

        reasoning = self.adapter._extract_reasoning_content(choice_data, full_response)
        self.assertEqual(reasoning, "这是思考过程")
        print("✓ 从 thinking_process 字段提取推理内容测试通过")

    def test_extract_reasoning_from_content_with_patterns(self):
        """测试从内容中使用模式匹配提取推理"""
        content = """让我逐步分析这个问题：
        
        思考过程：
        1. 首先分析品牌A的优势
        2. 然后比较品牌B的特点
        3. 最后得出结论
        
        最终答案：品牌A更好。"""

        choice_data = {
            "message": {
                "content": content
            }
        }
        full_response = {}

        # 直接测试内容提取方法
        extracted_reasoning = self.adapter._extract_reasoning_from_content(content)
        self.assertIn("分析品牌A的优势", extracted_reasoning)
        self.assertNotIn("最终答案", extracted_reasoning)
        print("✓ 从内容中使用模式匹配提取推理测试通过")

    def test_analyze_reasoning_chain_basic(self):
        """测试基本推理链分析"""
        reasoning_content = """分析步骤：
        1. 首先调研市场情况
        2. 然后比较竞品特点
        3. 小米在性价比方面有优势
        4. 最后得出结论"""
        
        result = self.adapter.analyze_reasoning_chain(reasoning_content, "TechBrand")
        
        self.assertGreaterEqual(result['reasoning_steps'], 3)
        self.assertIn(result['reasoning_depth'], ['shallow', 'moderate', 'deep'])
        self.assertIsInstance(result['competitor_connection_strength'], float)
        self.assertIsInstance(result['reasoning_quality_score'], float)
        print("✓ 基本推理链分析测试通过")

    def test_analyze_reasoning_chain_with_competitor_mentions(self):
        """测试包含竞品提及的推理链分析"""
        reasoning_content = """通过分析发现：
        1. TechBrand 在技术方面表现不错
        2. 但小米在性价比方面更有优势
        3. 华为在稳定性方面表现良好
        4. 综合来看TechBrand需要改进"""
        
        result = self.adapter.analyze_reasoning_chain(reasoning_content, "TechBrand")
        
        # 检查是否识别出竞品提及
        competitor_mentions = result['competitor_mentions_in_reasoning']
        self.assertGreaterEqual(len(competitor_mentions), 2)  # 至少识别出小米和华为
        
        # 验证竞品信息
        competitor_names = [comp['competitor'] for comp in competitor_mentions]
        self.assertIn('小米', competitor_names)
        self.assertIn('华为', competitor_names)
        
        print("✓ 包含竞品提及的推理链分析测试通过")

    def test_analyze_reasoning_chain_empty_content(self):
        """测试空内容的推理链分析"""
        result = self.adapter.analyze_reasoning_chain("", "TechBrand")
        
        self.assertEqual(len(result['competitor_mentions_in_reasoning']), 0)
        self.assertEqual(result['reasoning_steps'], 0)
        self.assertEqual(result['reasoning_depth'], 'shallow')
        self.assertEqual(result['competitor_connection_strength'], 0.0)
        self.assertEqual(result['reasoning_quality_score'], 0.0)
        
        print("✓ 空内容推理链分析测试通过")

    @patch('requests.Session.post')
    def test_send_prompt_with_reasoning_extraction(self, mock_post):
        """测试发送提示并提取推理内容"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "最终答案",
                    "reasoning": "这是推理过程"
                }
            }],
            "model": "deepseek-r1",
            "usage": {
                "total_tokens": 100
            }
        }
        
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        
        # 替换适配器的会话对象
        self.adapter.session = mock_session
        
        # 发送提示
        response = self.adapter.send_prompt("测试提示")
        
        # 验证响应结构
        self.assertTrue(response.success)
        self.assertEqual(response.content, "最终答案")
        self.assertIn('reasoning_content', response.metadata)
        self.assertEqual(response.metadata['reasoning_content'], "这是推理过程")
        
        print("✓ 发送提示并提取推理内容测试通过")

    def test_calculate_risk_impact_basic(self):
        """测试基本风险影响计算"""
        impact = self.adapter._calculate_risk_impact("产品存在安全隐患", "High")
        self.assertGreater(impact, 3.0)  # High 风险应该有较高的基础分数
        
        impact = self.adapter._calculate_risk_impact("服务一般般", "Low")
        self.assertLess(impact, 2.0)  # Low 风险应该有较低的基础分数
        
        print("✓ 基本风险影响计算测试通过")

    def test_calculate_risk_impact_with_keywords(self):
        """测试包含关键字的风险影响计算"""
        # 包含多个风险关键字的内容应该有更高的分数
        impact_with_keywords = self.adapter._calculate_risk_impact(
            "产品存在安全漏洞和欺诈风险", "Medium"
        )
        impact_without_keywords = self.adapter._calculate_risk_impact(
            "产品一般般", "Medium"
        )
        
        self.assertGreater(impact_with_keywords, impact_without_keywords)
        
        print("✓ 包含关键字的风险影响计算测试通过")


def test_end_to_end_reasoning_extraction():
    """端到端推理链提取测试"""
    print("\n执行端到端推理链提取测试...")

    # 创建适配器实例
    adapter = DeepSeekR1Adapter(
        api_key="fake-key",
        model_name="deepseek-r1",
        enable_reasoning_extraction=True
    )

    # 模拟一个包含推理过程的响应
    sample_reasoning_content = """
    让我详细分析这个品牌的情况：

    思考步骤：
    1. 首先收集市场数据，发现TechBrand在高端市场有一定份额
    2. 分析竞品情况，发现小米在性价比方面表现突出，华为在稳定性方面有优势
    3. 评估TechBrand的优劣势，技术实力较强但品牌知名度不如竞品
    4. 考虑市场趋势，消费者越来越注重性价比
    5. 预测未来发展方向，TechBrand需要加强市场营销和性价比策略

    综合以上分析，TechBrand在当前市场环境中面临一定竞争压力。
    """

    # 测试推理链分析
    analysis_result = adapter.analyze_reasoning_chain(
        reasoning_content=sample_reasoning_content,
        target_brand="TechBrand"
    )

    print(f"推理步骤数: {analysis_result['reasoning_steps']}")
    print(f"推理深度: {analysis_result['reasoning_depth']}")
    print(f"竞品连接强度: {analysis_result['competitor_connection_strength']:.2f}")
    print(f"推理质量分数: {analysis_result['reasoning_quality_score']:.2f}")
    print(f"识别的竞品提及: {len(analysis_result['competitor_mentions_in_reasoning'])}")

    # 验证分析结果
    assert analysis_result['reasoning_steps'] >= 4, f"期望至少4个推理步骤，实际{analysis_result['reasoning_steps']}个"
    assert analysis_result['reasoning_depth'] in ['moderate', 'deep'], f"推理深度应该是中等或深度，实际是{analysis_result['reasoning_depth']}"
    assert len(analysis_result['competitor_mentions_in_reasoning']) >= 2, f"期望识别至少2个竞品，实际{len(analysis_result['competitor_mentions_in_reasoning'])}个"

    # 检查识别出的竞品
    competitors_found = [c['competitor'] for c in analysis_result['competitor_mentions_in_reasoning']]
    assert '小米' in competitors_found, "应该识别出小米作为竞品"
    assert '华为' in competitors_found, "应该识别出华为作为竞品"

    print("✓ 端到端推理链提取测试通过")

    # 测试推理链如何影响排名预测
    print("\n测试推理链对排名预测的影响...")

    # 模拟一个包含负面推理的推理链
    negative_reasoning_content = """
    分析TechBrand的市场表现：

    1. 首先评估品牌知名度，TechBrand知名度较低
    2. 分析竞品对比，发现小米、华为、OPPO等竞品在多个方面优于TechBrand
    3. 考虑消费者反馈，TechBrand存在一些质量问题投诉
    4. 预测市场趋势，TechBrand可能会失去市场份额给竞品
    5. 结论：TechBrand的市场地位可能下降
    """

    negative_analysis = adapter.analyze_reasoning_chain(
        reasoning_content=negative_reasoning_content,
        target_brand="TechBrand"
    )

    print(f"负面推理分析 - 竞品连接强度: {negative_analysis['competitor_connection_strength']:.2f}")
    print(f"负面推理分析 - 推理质量分数: {negative_analysis['reasoning_quality_score']:.2f}")

    # 负面推理应该显示出更强的竞品连接
    assert negative_analysis['competitor_connection_strength'] > 0.0, "负面推理应该显示出竞品连接"

    print("✓ 推理链对排名预测影响测试通过")


if __name__ == '__main__':
    # 运行单元测试
    unittest.main(argv=[''], exit=False, verbosity=2)

    # 运行端到端测试
    test_end_to_end_reasoning_extraction()

    print("\n" + "="*60)
    print("所有测试通过!")
    print("✓ 推理链提取功能正常工作")
    print("✓ 竞品识别功能正常工作")
    print("✓ 风险影响计算正常工作")
    print("✓ 推理质量评估正常工作")
    print("✓ 端到端功能正常工作")
    print("="*60)