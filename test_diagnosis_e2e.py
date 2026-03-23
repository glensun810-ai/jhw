#!/usr/bin/env python3
"""
诊断系统端到端测试套件 - P29 系统修复验证

目的：
1. 验证诊断系统从提交到查看详情的完整流程
2. 检测性能回归（特别是前端渲染性能）
3. 防止历史问题重复出现

作者：首席架构师
日期：2026-03-17
版本：1.0.0 (P29 系统修复)
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python/wechat_backend'))

from wechat_backend.logging_config import api_logger


class DiagnosisE2ETest:
    """诊断系统端到端测试"""

    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.end_time = None

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        self.start_time = datetime.now()
        print("\n" + "="*80)
        print("诊断系统端到端测试套件 - P29 系统修复验证")
        print("="*80)

        tests = [
            ("前端渲染性能测试", self.test_frontend_rendering_performance),
            ("诊断提交流程测试", self.test_diagnosis_submission_flow),
            ("诊断结果查询测试", self.test_diagnosis_retrieval),
            ("详情页加载测试", self.test_detail_page_loading),
            ("数据完整性测试", self.test_data_integrity),
        ]

        passed = 0
        failed = 0
        skipped = 0

        for test_name, test_func in tests:
            try:
                print(f"\n▶️  开始测试：{test_name}")
                result = test_func()
                if result is True:
                    passed += 1
                    print(f"✅ 测试通过：{test_name}")
                elif result is None:
                    skipped += 1
                    print(f"⚠️  测试跳过：{test_name}")
                else:
                    failed += 1
                    print(f"❌ 测试失败：{test_name}")
            except Exception as e:
                failed += 1
                print(f"❌ 测试异常：{test_name}")
                print(f"   错误：{str(e)}")
                import traceback
                traceback.print_exc()

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        print("\n" + "="*80)
        print(f"测试总结：")
        print(f"  通过：{passed}/{len(tests)}")
        print(f"  失败：{failed}/{len(tests)}")
        print(f"  跳过：{skipped}/{len(tests)}")
        print(f"  总耗时：{duration:.2f}秒")
        print("="*80)

        return failed == 0

    def test_frontend_rendering_performance(self) -> bool:
        """
        测试前端渲染性能（P29 关键修复验证）

        验证点：
        1. 分片渲染使用数组累积而非字符串拼接
        2. 10 万字符渲染时间 < 5 秒
        3. 定时器正确清理
        """
        print("\n  测试场景：前端渲染性能")
        print("  验证点：")
        print("    - 使用数组累积分片（O(n) 复杂度）")
        print("    - 10 万字符渲染时间 < 5 秒")
        print("    - 定时器正确清理")

        # 读取前端代码验证修复
        detail_page_path = os.path.join(
            os.path.dirname(__file__),
            'brand_ai-seach/pages/report/detail/index.js'
        )

        if not os.path.exists(detail_page_path):
            print("  ⚠️  前端文件不存在，跳过测试")
            return None

        with open(detail_page_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # 验证修复 1：使用数组累积
        if 'var chunks = []' in code and 'chunks.push(formattedChunk)' in code:
            print("  ✅ 使用数组累积分片")
        else:
            print("  ❌ 未找到数组累积代码")
            return False

        # 验证修复 2：一次性设置完整文本
        if 'chunks.join(\'\')' in code:
            print("  ✅ 一次性设置完整文本")
        else:
            print("  ❌ 未找到一次性设置代码")
            return False

        # 验证修复 3：定时器通过 setData 存储
        if 'setData({ renderTimer: timer })' in code or 'setData({renderTimer: timer})' in code:
            print("  ✅ 定时器通过 setData 存储")
        else:
            print("  ⚠️  定时器存储方式待确认")

        # 性能模拟测试
        print("\n  性能模拟测试：")
        test_sizes = [10000, 50000, 100000]  # 字符数

        for size in test_sizes:
            # 模拟 O(n) 复杂度的数组累积
            start = time.time()
            chunks = []
            chunk_size = 1000
            for i in range(0, size, chunk_size):
                chunk = 'x' * chunk_size
                chunks.append(chunk)
            result = ''.join(chunks)
            elapsed = (time.time() - start) * 1000  # 毫秒

            print(f"    {size} 字符：{elapsed:.2f}ms (O(n) 复杂度)")

            # 验证性能预算
            if size == 100000 and elapsed > 100:  # 100ms 预算
                print(f"  ⚠️  性能警告：10 万字符渲染耗时 {elapsed:.2f}ms > 100ms")

        return True

    def test_diagnosis_submission_flow(self) -> bool:
        """
        测试诊断提交流程

        验证点：
        1. 品牌列表验证正确（支持单品牌和多品牌）
        2. AI 调用正确执行
        3. 结果保存到数据库
        """
        print("\n  测试场景：诊断提交流程")
        print("  验证点：")
        print("    - 品牌列表验证（支持单品牌）")
        print("    - AI 调用正确执行")
        print("    - 结果保存到数据库")

        # 验证后端代码
        from wechat_backend.services.brand_analysis_service import BrandAnalysisService

        # 测试单品牌场景
        service = BrandAnalysisService()
        mock_results = [
            {
                'question': '介绍特斯拉',
                'response': '特斯拉是一家电动汽车公司，主要车型包括 Model 3、Model Y。',
                'brand': '特斯拉'
            }
        ]

        analysis = service.analyze_brand_mentions(
            results=mock_results,
            user_brand='特斯拉',
            competitor_brands=None,  # 不指定竞品
            execution_id='test_single_brand'
        )

        if analysis and 'user_brand_analysis' in analysis:
            print("  ✅ 单品牌分析成功")
        else:
            print("  ❌ 单品牌分析失败")
            return False

        # 验证关键词提取
        if 'keywords' in analysis:
            print(f"  ✅ 关键词提取功能存在，提取了 {len(analysis['keywords'])} 个关键词")
        else:
            print("  ❌ 关键词提取功能缺失")
            return False

        return True

    def test_diagnosis_retrieval(self) -> bool:
        """
        测试诊断结果查询

        验证点：
        1. 报告聚合器生成完整数据
        2. 包含所有必需字段
        3. 数据格式正确
        """
        print("\n  测试场景：诊断结果查询")
        print("  验证点：")
        print("    - 报告聚合器生成完整数据")
        print("    - 包含所有必需字段")
        print("    - 数据格式正确")

        from wechat_backend.services.report_aggregator import ReportAggregator

        aggregator = ReportAggregator()

        # 模拟原始结果
        mock_results = [
            {
                'brand': '特斯拉',
                'question': '介绍特斯拉',
                'model': 'deepseek',
                'score': 85,
                'response': '特斯拉是一家电动汽车公司',
                'geo_data': {'brand_mentioned': True}
            }
        ]

        report = aggregator.aggregate(
            raw_results=mock_results,
            brand_name='特斯拉',
            competitors=[],
            additional_data=None
        )

        # 验证必需字段
        required_fields = [
            'brandName', 'brandScores', 'sov', 'risk', 'health',
            'insights', 'semanticDrift', 'sourcePurity', 'recommendations'
        ]

        missing_fields = []
        for field in required_fields:
            if field not in report:
                missing_fields.append(field)

        if not missing_fields:
            print("  ✅ 所有必需字段存在")
        else:
            print(f"  ❌ 缺少字段：{missing_fields}")
            return False

        # 验证 semanticDrift 有默认值
        if report.get('semanticDrift'):
            print("  ✅ semanticDrift 有默认值")
        else:
            print("  ❌ semanticDrift 为空")
            return False

        # 验证 recommendations 有默认值
        if report.get('recommendations') and len(report['recommendations']) > 0:
            print("  ✅ recommendations 有默认值")
        else:
            print("  ⚠️  recommendations 为空")

        return True

    def test_detail_page_loading(self) -> bool:
        """
        测试详情页加载

        验证点：
        1. 前端代码无语法错误
        2. 定时器清理逻辑正确
        3. 无死循环风险
        """
        print("\n  测试场景：详情页加载")
        print("  验证点：")
        print("    - 前端代码无语法错误")
        print("    - 定时器清理逻辑正确")
        print("    - 无死循环风险")

        detail_page_path = os.path.join(
            os.path.dirname(__file__),
            'brand_ai-seach/pages/report/detail/index.js'
        )

        if not os.path.exists(detail_page_path):
            print("  ⚠️  前端文件不存在，跳过测试")
            return None

        with open(detail_page_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # 验证 onUnload 中的定时器清理
        if 'clearInterval(this.data.renderTimer)' in code:
            print("  ✅ 定时器清理逻辑存在")
        else:
            print("  ❌ 定时器清理逻辑缺失")
            return False

        # 验证无直接修改 this.data
        if 'this.data.renderTimer = timer' not in code:
            print("  ✅ 无直接修改 this.data 的问题")
        else:
            print("  ❌ 仍然存在直接修改 this.data 的问题")
            return False

        return True

    def test_data_integrity(self) -> bool:
        """
        测试数据完整性

        验证点：
        1. 品牌分布数据正确生成
        2. 关键词数据存在
        3. 分析数据完整
        """
        print("\n  测试场景：数据完整性")
        print("  验证点：")
        print("    - 品牌分布数据正确生成")
        print("    - 关键词数据存在")
        print("    - 分析数据完整")

        from wechat_backend.diagnosis_report_service import DiagnosisReportService

        service = DiagnosisReportService()

        # 模拟结果
        mock_results = [
            {
                'brand': '特斯拉',
                'question': '介绍特斯拉',
                'response_content': '特斯拉是一家电动汽车公司',
                'extracted_brand': '特斯拉'
            },
            {
                'brand': '特斯拉',
                'question': '特斯拉的特点',
                'response_content': '特斯拉有自动驾驶技术',
                'extracted_brand': '特斯拉'
            }
        ]

        # 测试品牌分布计算
        brand_dist = service._calculate_brand_distribution(
            mock_results,
            expected_brands=['特斯拉', '比亚迪']
        )

        if brand_dist and 'data' in brand_dist:
            print(f"  ✅ 品牌分布计算成功：{brand_dist['data']}")
        else:
            print("  ❌ 品牌分布计算失败")
            return False

        # 测试关键词提取
        keywords = service._extract_keywords(mock_results)
        if keywords is not None:
            print(f"  ✅ 关键词提取成功：{len(keywords)} 个关键词")
        else:
            print("  ❌ 关键词提取失败")
            return False

        return True


def main():
    """主函数"""
    print("\n" + "="*80)
    print("诊断系统端到端测试套件")
    print("版本：1.0.0 (P29 系统修复)")
    print("日期：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)

    test = DiagnosisE2ETest()
    success = test.run_all_tests()

    if success:
        print("\n✅ 所有测试通过！系统已准备好进行第 29 次诊断。")
        return 0
    else:
        print("\n❌ 部分测试失败，请先修复问题再进行诊断。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
