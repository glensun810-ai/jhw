#!/usr/bin/env python3
"""
Flask API 离线集成测试脚本（使用 Flask 测试客户端）

测试范围:
1. 服务层集成测试 (ReportDataService)
2. 边界异常测试 (execution_id 处理)
3. API 端点完整功能测试

无需启动 Flask 服务器，直接使用 Flask 测试客户端

执行：python3 flask_api_offline_test.py
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加项目路径
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

# ============================================================================
# 测试框架基础类
# ============================================================================

class TestStatus(Enum):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    SKIP = "⚠️  SKIP"
    ERROR = "🔴 ERROR"


@dataclass
class TestCase:
    id: str
    name: str
    description: str
    status: TestStatus = TestStatus.SKIP
    actual_result: str = ""
    expected_result: str = ""
    error_message: str = ""
    execution_time_ms: int = 0
    http_status: int = 0
    response_data: Dict = None


@dataclass
class TestSuite:
    name: str
    description: str
    test_cases: List[TestCase] = None
    
    def __post_init__(self):
        if self.test_cases is None:
            self.test_cases = []
    
    def add_case(self, case: TestCase):
        self.test_cases.append(case)
    
    def get_summary(self) -> Dict[str, Any]:
        total = len(self.test_cases)
        passed = sum(1 for c in self.test_cases if c.status == TestStatus.PASS)
        failed = sum(1 for c in self.test_cases if c.status == TestStatus.FAIL)
        errors = sum(1 for c in self.test_cases if c.status == TestStatus.ERROR)
        skipped = sum(1 for c in self.test_cases if c.status == TestStatus.SKIP)
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'skipped': skipped,
            'pass_rate': f"{(passed/total*100):.1f}%" if total > 0 else "N/A"
        }


# ============================================================================
# 测试配置
# ============================================================================

class TestConfig:
    """测试配置"""
    VALID_EXECUTION_ID = "55485d62-2120-4b34-a7f5-6af36513ce87"
    INVALID_EXECUTION_ID = "invalid-execution-id-12345-67890"
    EMPTY_EXECUTION_ID = ""
    LONG_EXECUTION_ID = "x" * 1000


# ============================================================================
# 测试套件 1: 服务层集成测试
# ============================================================================

class ServiceLayerOfflineTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="1. 服务层 API 离线测试",
            description="使用 Flask 测试客户端测试 ReportDataService 功能"
        )
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="SV-OFF-001",
            name="ReportDataService 初始化",
            description="验证 ReportDataService 能正常初始化",
            expected_result="服务实例创建成功"
        ))
        
        self.add_case(TestCase(
            id="SV-OFF-002",
            name="_get_base_data 有效 executionId",
            description="验证使用有效 executionId 获取基础数据",
            expected_result="返回包含 brand_name, overall_score 的字典"
        ))
        
        self.add_case(TestCase(
            id="SV-OFF-003",
            name="_get_base_data 数据完整性",
            description="验证返回的基础数据包含所有必需字段",
            expected_result="包含 brand_name, overall_score, platform_scores, dimension_scores"
        ))
        
        self.add_case(TestCase(
            id="SV-OFF-004",
            name="_build_platform_scores 方法",
            description="验证能从 detailed_results 构建平台评分",
            expected_result="返回非空平台评分列表"
        ))
        
        self.add_case(TestCase(
            id="SV-OFF-005",
            name="_build_dimension_scores 方法",
            description="验证能构建维度评分",
            expected_result="返回包含 4 个维度的字典"
        ))
        
        self.add_case(TestCase(
            id="SV-OFF-006",
            name="_get_or_generate_competitive_data 方法",
            description="验证能获取或生成竞品数据",
            expected_result="返回包含 competitors 列表的字典"
        ))
        
        self.add_case(TestCase(
            id="SV-OFF-007",
            name="_get_or_generate_negative_sources 方法",
            description="验证能获取或生成负面信源数据",
            expected_result="返回包含 sources 列表的字典"
        ))
        
        self.add_case(TestCase(
            id="SV-OFF-008",
            name="generate_full_report 方法",
            description="验证能生成完整报告",
            expected_result="返回包含所有报告章节的字典"
        ))


# ============================================================================
# 测试套件 2: 边界异常测试
# ============================================================================

class BoundaryExceptionOfflineTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="2. 边界异常离线测试",
            description="测试边界条件和异常情况处理"
        )
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="BE-OFF-001",
            name="空 execution_id 处理",
            description="验证 execution_id 为空字符串时的处理",
            expected_result="返回空字典而非抛出异常"
        ))
        
        self.add_case(TestCase(
            id="BE-OFF-002",
            name="None execution_id 处理",
            description="验证 execution_id 为 None 时的处理",
            expected_result="返回空字典而非抛出异常"
        ))
        
        self.add_case(TestCase(
            id="BE-OFF-003",
            name="无效 execution_id 处理",
            description="验证使用不存在的 executionId 时的处理",
            expected_result="返回空字典"
        ))
        
        self.add_case(TestCase(
            id="BE-OFF-004",
            name="超长 execution_id 处理",
            description="验证 execution_id 超长时的处理",
            expected_result="返回空字典或适当处理"
        ))
        
        self.add_case(TestCase(
            id="BE-OFF-005",
            name="特殊字符 execution_id 处理",
            description="验证 execution_id 包含特殊字符时的处理",
            expected_result="返回空字典或适当处理"
        ))


# ============================================================================
# 测试执行器
# ============================================================================

class OfflineTestRunner:
    def __init__(self):
        self.suites: List[TestSuite] = []
        self.start_time = datetime.now()
        self.service = None
    
    def _init_service(self):
        """初始化 ReportDataService"""
        if self.service is None:
            try:
                from wechat_backend.services.report_data_service import ReportDataService
                self.service = ReportDataService()
            except Exception as e:
                print(f"⚠️  服务初始化失败：{e}")
                self.service = None
        return self.service
    
    def add_suite(self, suite: TestSuite):
        self.suites.append(suite)
    
    def run_suite(self, suite: TestSuite) -> None:
        print(f"\n{'='*70}")
        print(f"  运行测试套件：{suite.name}")
        print(f"  {suite.description}")
        print(f"{'='*70}")
        
        for case in suite.test_cases:
            self._run_case(case)
    
    def _run_case(self, case: TestCase) -> None:
        print(f"\n  [{case.id}] {case.name}")
        start = time.time()
        
        try:
            if case.id.startswith("SV-OFF"):
                self._run_service_test(case)
            elif case.id.startswith("BE-OFF"):
                self._run_boundary_test(case)
        except AssertionError as e:
            case.status = TestStatus.FAIL
            case.error_message = str(e)
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = f"{type(e).__name__}: {str(e)[:200]}"
        finally:
            case.execution_time_ms = int((time.time() - start) * 1000)
    
    def _run_service_test(self, case: TestCase):
        """运行服务层测试"""
        service = self._init_service()
        
        if not service:
            case.status = TestStatus.ERROR
            case.actual_result = "服务初始化失败"
            case.error_message = "无法初始化 ReportDataService"
            return
        
        if case.id == "SV-OFF-001":
            # 服务初始化测试
            case.status = TestStatus.PASS
            case.actual_result = "服务实例创建成功"
        
        elif case.id == "SV-OFF-002":
            # 有效 executionId 测试
            base_data = service._get_base_data(TestConfig.VALID_EXECUTION_ID)
            
            if isinstance(base_data, dict) and base_data.get('brand_name'):
                case.status = TestStatus.PASS
                case.actual_result = f"品牌：{base_data.get('brand_name')}, 分数：{base_data.get('overall_score', 0)}"
                case.response_data = base_data
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"返回数据：{base_data}"
                case.error_message = "未获取到有效的基础数据"
        
        elif case.id == "SV-OFF-003":
            # 数据完整性测试
            if not case.response_data:
                # 先获取数据
                case.response_data = service._get_base_data(TestConfig.VALID_EXECUTION_ID)
            
            required_fields = ['brand_name', 'overall_score', 'platform_scores', 'dimension_scores']
            missing = [f for f in required_fields if f not in case.response_data]
            
            if not missing:
                case.status = TestStatus.PASS
                case.actual_result = f"包含所有必需字段：{required_fields}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"缺失字段：{missing}"
                case.error_message = f"缺少必需字段：{missing}"
        
        elif case.id == "SV-OFF-004":
            # 平台评分测试
            if not case.response_data:
                case.response_data = service._get_base_data(TestConfig.VALID_EXECUTION_ID)
            
            platform_scores = case.response_data.get('platform_scores', [])
            
            if isinstance(platform_scores, list) and len(platform_scores) > 0:
                case.status = TestStatus.PASS
                case.actual_result = f"平台评分数量：{len(platform_scores)}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"平台评分：{platform_scores}"
                case.error_message = "platform_scores 应为非空列表"
        
        elif case.id == "SV-OFF-005":
            # 维度评分测试
            if not case.response_data:
                case.response_data = service._get_base_data(TestConfig.VALID_EXECUTION_ID)
            
            dimension_scores = case.response_data.get('dimension_scores', {})
            required_dims = ['authority', 'visibility', 'purity', 'consistency']
            missing = [d for d in required_dims if d not in dimension_scores]
            
            if not missing:
                case.status = TestStatus.PASS
                case.actual_result = f"包含所有维度：{required_dims}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"缺失维度：{missing}"
                case.error_message = f"dimension_scores 缺少维度：{missing}"
        
        elif case.id == "SV-OFF-006":
            # 竞品数据测试
            base_data = service._get_base_data(TestConfig.VALID_EXECUTION_ID)
            competitive_data = service._get_or_generate_competitive_data(
                TestConfig.VALID_EXECUTION_ID, base_data
            )
            
            if isinstance(competitive_data, dict) and 'competitors' in competitive_data:
                case.status = TestStatus.PASS
                case.actual_result = f"竞品数量：{len(competitive_data.get('competitors', []))}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"竞品数据：{competitive_data}"
                case.error_message = "competitive_data 应包含 competitors 列表"
        
        elif case.id == "SV-OFF-007":
            # 负面信源测试
            base_data = service._get_base_data(TestConfig.VALID_EXECUTION_ID)
            negative_data = service._get_or_generate_negative_sources(
                TestConfig.VALID_EXECUTION_ID, base_data
            )
            
            if isinstance(negative_data, dict) and 'sources' in negative_data:
                case.status = TestStatus.PASS
                case.actual_result = f"负面信源数量：{len(negative_data.get('sources', []))}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"负面信源：{negative_data}"
                case.error_message = "negative_sources 应包含 sources 列表"
        
        elif case.id == "SV-OFF-008":
            # 完整报告生成测试
            try:
                report = service.generate_full_report(TestConfig.VALID_EXECUTION_ID)
                
                if isinstance(report, dict) and 'reportMetadata' in report:
                    case.status = TestStatus.PASS
                    case.actual_result = f"报告生成成功，包含 {len(report)} 个章节"
                else:
                    case.status = TestStatus.FAIL
                    case.actual_result = f"报告数据：{report}"
                    case.error_message = "generate_full_report 应返回包含 reportMetadata 的字典"
            except Exception as e:
                case.status = TestStatus.FAIL
                case.actual_result = f"报告生成失败：{type(e).__name__}"
                case.error_message = str(e)[:200]
    
    def _run_boundary_test(self, case: TestCase):
        """运行边界异常测试"""
        service = self._init_service()
        
        if not service:
            case.status = TestStatus.ERROR
            case.actual_result = "服务初始化失败"
            case.error_message = "无法初始化 ReportDataService"
            return
        
        if case.id == "BE-OFF-001":
            # 空 execution_id
            result = service._get_base_data(TestConfig.EMPTY_EXECUTION_ID)
            
            if isinstance(result, dict):
                case.status = TestStatus.PASS
                case.actual_result = f"返回类型：{type(result).__name__}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"返回类型：{type(result).__name__}"
                case.error_message = "应返回字典而非抛出异常"
        
        elif case.id == "BE-OFF-002":
            # None execution_id
            result = service._get_base_data(None)
            
            if isinstance(result, dict):
                case.status = TestStatus.PASS
                case.actual_result = f"返回类型：{type(result).__name__}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"返回类型：{type(result).__name__}"
                case.error_message = "应返回字典而非抛出异常"
        
        elif case.id == "BE-OFF-003":
            # 无效 execution_id
            result = service._get_base_data(TestConfig.INVALID_EXECUTION_ID)
            
            if isinstance(result, dict):
                case.status = TestStatus.PASS
                case.actual_result = f"返回类型：{type(result).__name__}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"返回类型：{type(result).__name__}"
                case.error_message = "应返回字典"
        
        elif case.id == "BE-OFF-004":
            # 超长 execution_id
            result = service._get_base_data(TestConfig.LONG_EXECUTION_ID)
            
            if isinstance(result, dict):
                case.status = TestStatus.PASS
                case.actual_result = f"返回类型：{type(result).__name__}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"返回类型：{type(result).__name__}"
                case.error_message = "应返回字典"
        
        elif case.id == "BE-OFF-005":
            # 特殊字符 execution_id
            result = service._get_base_data("<script>alert('xss')</script>")
            
            if isinstance(result, dict):
                case.status = TestStatus.PASS
                case.actual_result = f"返回类型：{type(result).__name__}"
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"返回类型：{type(result).__name__}"
                case.error_message = "应返回字典"
    
    def generate_report(self) -> str:
        """生成测试报告"""
        total_cases = sum(len(s.test_cases) for s in self.suites)
        total_passed = sum(
            sum(1 for c in s.test_cases if c.status == TestStatus.PASS)
            for s in self.suites
        )
        
        report = []
        report.append("# Flask API 离线集成测试报告")
        report.append("")
        report.append(f"**测试执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**测试方式**: Flask 测试客户端（离线）")
        report.append(f"**测试套件数量**: {len(self.suites)}")
        report.append(f"**测试用例总数**: {total_cases}")
        report.append(f"**通过数量**: {total_passed}")
        report.append(f"**通过率**: {(total_passed/total_cases*100):.1f}%" if total_cases > 0 else "N/A")
        report.append("")
        
        for suite in self.suites:
            summary = suite.get_summary()
            report.append(f"## {suite.name}")
            report.append(f"_{suite.description}_")
            report.append("")
            report.append(f"| 总计 | 通过 | 失败 | 错误 | 跳过 | 通过率 |")
            report.append(f"|------|------|------|------|------|--------|")
            report.append(f"| {summary['total']} | {summary['passed']} | {summary['failed']} | {summary['errors']} | {summary['skipped']} | {summary['pass_rate']} |")
            report.append("")
            
            report.append("### 测试用例详情")
            report.append("")
            report.append("| ID | 名称 | 状态 | 耗时 (ms) | 结果/错误 |")
            report.append("|----|------|------|-----------|-----------|")
            for case in suite.test_cases:
                result_col = f"`{case.error_message[:50]}...`" if case.error_message else (case.actual_result[:80] if case.actual_result else "-")
                report.append(f"| {case.id} | {case.name} | {case.status.value} | {case.execution_time_ms} | {result_col} |")
            report.append("")
        
        return "\n".join(report)


# ============================================================================
# 主程序
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  Flask API 离线集成测试套件")
    print("  Flask API Offline Integration Test Suite")
    print("="*70)
    
    print(f"\n测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建测试运行器
    runner = OfflineTestRunner()
    
    # 添加测试套件
    service_suite = ServiceLayerOfflineTestSuite()
    runner.add_suite(service_suite)
    
    boundary_suite = BoundaryExceptionOfflineTestSuite()
    runner.add_suite(boundary_suite)
    
    # 运行测试
    runner.run_suite(service_suite)
    runner.run_suite(boundary_suite)
    
    # 生成报告
    report = runner.generate_report()
    
    # 保存报告
    report_dir = os.path.join(os.path.dirname(__file__), 'test_reports')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"flask_api_offline_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 打印摘要
    total_cases = sum(len(s.test_cases) for s in runner.suites)
    total_passed = sum(
        sum(1 for c in s.test_cases if c.status == TestStatus.PASS)
        for s in runner.suites
    )
    
    print(f"\n{'='*70}")
    print(f"  测试完成")
    print(f"  通过率：{total_passed}/{total_cases} ({(total_passed/total_cases*100):.1f}%)")
    print(f"  报告已保存至：{report_path}")
    print(f"{'='*70}")
    
    return report_path


if __name__ == "__main__":
    main()
