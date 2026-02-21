#!/usr/bin/env python3
"""
Flask API 集成测试脚本

测试范围:
1. 服务层集成测试 (ReportDataService)
2. 边界异常测试 (execution_id 处理)
3. API 端点完整功能测试

执行方式:
1. 先启动 Flask 应用：cd backend_python && python3 wechat_backend/app.py
2. 运行测试：python3 flask_api_integration_test.py

测试报告将保存至：test_reports/flask_api_integration_test_report.md
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

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
    BASE_URL = "http://127.0.0.1:5000"
    TIMEOUT = 30  # 秒
    VALID_EXECUTION_ID = "55485d62-2120-4b34-a7f5-6af36513ce87"  # 数据库中存在的 execution_id
    INVALID_EXECUTION_ID = "invalid-execution-id-12345-67890"
    EMPTY_EXECUTION_ID = ""
    NULL_EXECUTION_ID = None
    LONG_EXECUTION_ID = "x" * 1000


# ============================================================================
# 测试套件 1: 服务层集成测试
# ============================================================================

class ServiceLayerAPITestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="1. 服务层 API 集成测试",
            description="测试 ReportDataService 相关的 API 端点功能"
        )
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="SV-API-001",
            name="GET /api/export/report-data 有效 executionId",
            description="验证使用有效 executionId 获取报告数据",
            expected_result="返回 200 状态码和完整报告数据"
        ))
        
        self.add_case(TestCase(
            id="SV-API-002",
            name="GET /api/export/report-data 数据完整性",
            description="验证返回的报告数据包含所有必需字段",
            expected_result="包含 reportMetadata, executiveSummary, brandHealth 等字段"
        ))
        
        self.add_case(TestCase(
            id="SV-API-003",
            name="GET /api/export/report-data 基础数据验证",
            description="验证返回的基础数据包含 brand_name, overall_score 等",
            expected_result="包含必需的基础数据字段"
        ))
        
        self.add_case(TestCase(
            id="SV-API-004",
            name="GET /api/export/report-data 平台评分验证",
            description="验证返回的平台评分数据结构正确",
            expected_result="platform_scores 为非空列表"
        ))
        
        self.add_case(TestCase(
            id="SV-API-005",
            name="GET /api/export/report-data 维度评分验证",
            description="验证返回的维度评分包含 authority, visibility 等",
            expected_result="dimension_scores 包含 4 个维度"
        ))
        
        self.add_case(TestCase(
            id="SV-API-006",
            name="GET /api/export/report-data 竞品数据验证",
            description="验证返回的竞品数据结构正确",
            expected_result="competitiveAnalysis 包含 competitors 列表"
        ))
        
        self.add_case(TestCase(
            id="SV-API-007",
            name="GET /api/export/report-data 负面信源验证",
            description="验证返回的负面信源数据结构正确",
            expected_result="negativeSources 包含 sources 列表"
        ))
        
        self.add_case(TestCase(
            id="SV-API-008",
            name="GET /api/export/report-data ROI 数据验证",
            description="验证返回的 ROI 数据结构正确",
            expected_result="roiAnalysis 包含 ROI 指标"
        ))


# ============================================================================
# 测试套件 2: 边界异常测试
# ============================================================================

class BoundaryExceptionAPITestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="2. 边界异常 API 测试",
            description="测试边界条件和异常情况处理"
        )
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="BE-API-001",
            name="空 execution_id 处理",
            description="验证 execution_id 为空字符串时的处理",
            expected_result="返回 400 错误"
        ))
        
        self.add_case(TestCase(
            id="BE-API-002",
            name="缺失 execution_id 参数处理",
            description="验证缺少 execution_id 参数时的处理",
            expected_result="返回 400 错误"
        ))
        
        self.add_case(TestCase(
            id="BE-API-003",
            name="无效 execution_id 处理",
            description="验证使用不存在的 executionId 时的处理",
            expected_result="返回 404 错误"
        ))
        
        self.add_case(TestCase(
            id="BE-API-004",
            name="超长 execution_id 处理",
            description="验证 execution_id 超长时的处理",
            expected_result="返回 404 错误或适当错误"
        ))
        
        self.add_case(TestCase(
            id="BE-API-005",
            name="特殊字符 execution_id 处理",
            description="验证 execution_id 包含特殊字符时的处理",
            expected_result="返回 404 错误或适当错误"
        ))
        
        self.add_case(TestCase(
            id="BE-API-006",
            name="GET /api/export/pdf 无效 executionId",
            description="验证 PDF 导出 API 对无效 executionId 的处理",
            expected_result="返回 404 错误"
        ))
        
        self.add_case(TestCase(
            id="BE-API-007",
            name="GET /api/export/html 无效 executionId",
            description="验证 HTML 导出 API 对无效 executionId 的处理",
            expected_result="返回 404 错误"
        ))


# ============================================================================
# 测试执行器
# ============================================================================

class APITestRunner:
    def __init__(self, base_url: str = TestConfig.BASE_URL):
        self.base_url = base_url
        self.suites: List[TestSuite] = []
        self.session = requests.Session()
        self.start_time = datetime.now()
    
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
            if case.id == "SV-API-001":
                self._test_valid_execution_id(case)
            elif case.id == "SV-API-002":
                self._test_report_data_integrity(case)
            elif case.id == "SV-API-003":
                self._test_base_data(case)
            elif case.id == "SV-API-004":
                self._test_platform_scores(case)
            elif case.id == "SV-API-005":
                self._test_dimension_scores(case)
            elif case.id == "SV-API-006":
                self._test_competitive_data(case)
            elif case.id == "SV-API-007":
                self._test_negative_sources(case)
            elif case.id == "SV-API-008":
                self._test_roi_data(case)
            elif case.id == "BE-API-001":
                self._test_empty_execution_id(case)
            elif case.id == "BE-API-002":
                self._test_missing_execution_id(case)
            elif case.id == "BE-API-003":
                self._test_invalid_execution_id(case)
            elif case.id == "BE-API-004":
                self._test_long_execution_id(case)
            elif case.id == "BE-API-005":
                self._test_special_char_execution_id(case)
            elif case.id == "BE-API-006":
                self._test_pdf_invalid_execution_id(case)
            elif case.id == "BE-API-007":
                self._test_html_invalid_execution_id(case)
        except AssertionError as e:
            case.status = TestStatus.FAIL
            case.error_message = str(e)
        except requests.exceptions.ConnectionError as e:
            case.status = TestStatus.ERROR
            case.error_message = f"服务器连接失败：{e}"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = f"{type(e).__name__}: {str(e)[:200]}"
        finally:
            case.execution_time_ms = int((time.time() - start) * 1000)
    
    # ==================== 服务层测试方法 ====================
    
    def _test_valid_execution_id(self, case: TestCase):
        """测试有效 executionId"""
        url = f"{self.base_url}/api/export/report-data"
        params = {"executionId": TestConfig.VALID_EXECUTION_ID}
        
        response = self.session.get(url, params=params, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success' and 'data' in data:
                case.status = TestStatus.PASS
                case.actual_result = f"状态码：{response.status_code}, 数据获取成功"
                case.response_data = data.get('data', {})
            else:
                case.status = TestStatus.FAIL
                case.actual_result = f"状态码：{response.status_code}"
                case.error_message = f"响应格式错误：{data}"
        elif response.status_code == 404:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = "有效 executionId 返回 404，数据可能不存在"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"意外状态码：{response.status_code}"
    
    def _test_report_data_integrity(self, case: TestCase):
        """测试报告数据完整性"""
        if not case.response_data:
            case.status = TestStatus.SKIP
            case.actual_result = "无前序测试数据，跳过"
            return
        
        required_fields = ['reportMetadata', 'brandHealth']
        missing_fields = [f for f in required_fields if f not in case.response_data]
        
        if not missing_fields:
            case.status = TestStatus.PASS
            case.actual_result = f"包含所有必需字段：{required_fields}"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"缺失字段：{missing_fields}"
            case.error_message = f"缺少必需字段：{missing_fields}"
    
    def _test_base_data(self, case: TestCase):
        """测试基础数据"""
        if not case.response_data:
            case.status = TestStatus.SKIP
            case.actual_result = "无前序测试数据，跳过"
            return
        
        brand_health = case.response_data.get('brandHealth', {})
        required_fields = ['brand_name', 'overall_score']
        missing_fields = [f for f in required_fields if f not in brand_health]
        
        if not missing_fields:
            case.status = TestStatus.PASS
            case.actual_result = f"品牌：{brand_health.get('brand_name')}, 分数：{brand_health.get('overall_score')}"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"缺失字段：{missing_fields}"
            case.error_message = f"基础数据缺少字段：{missing_fields}"
    
    def _test_platform_scores(self, case: TestCase):
        """测试平台评分"""
        if not case.response_data:
            case.status = TestStatus.SKIP
            case.actual_result = "无前序测试数据，跳过"
            return
        
        brand_health = case.response_data.get('brandHealth', {})
        platform_scores = brand_health.get('platform_scores', [])
        
        if isinstance(platform_scores, list) and len(platform_scores) > 0:
            case.status = TestStatus.PASS
            case.actual_result = f"平台评分数量：{len(platform_scores)}"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"平台评分：{platform_scores}"
            case.error_message = "platform_scores 应为非空列表"
    
    def _test_dimension_scores(self, case: TestCase):
        """测试维度评分"""
        if not case.response_data:
            case.status = TestStatus.SKIP
            case.actual_result = "无前序测试数据，跳过"
            return
        
        brand_health = case.response_data.get('brandHealth', {})
        dimension_scores = brand_health.get('dimension_scores', {})
        
        required_dims = ['authority', 'visibility', 'purity', 'consistency']
        missing_dims = [d for d in required_dims if d not in dimension_scores]
        
        if not missing_dims:
            case.status = TestStatus.PASS
            case.actual_result = f"包含所有维度：{required_dims}"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"缺失维度：{missing_dims}"
            case.error_message = f"dimension_scores 缺少维度：{missing_dims}"
    
    def _test_competitive_data(self, case: TestCase):
        """测试竞品数据"""
        if not case.response_data:
            case.status = TestStatus.SKIP
            case.actual_result = "无前序测试数据，跳过"
            return
        
        competitive_analysis = case.response_data.get('competitiveAnalysis', {})
        competitors = competitive_analysis.get('competitors', [])
        
        if isinstance(competitors, list):
            case.status = TestStatus.PASS
            case.actual_result = f"竞品数量：{len(competitors)}"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"竞品数据：{competitors}"
            case.error_message = "competitors 应为列表"
    
    def _test_negative_sources(self, case: TestCase):
        """测试负面信源"""
        if not case.response_data:
            case.status = TestStatus.SKIP
            case.actual_result = "无前序测试数据，跳过"
            return
        
        negative_sources = case.response_data.get('negativeSources', {})
        sources = negative_sources.get('sources', [])
        
        if isinstance(sources, list):
            case.status = TestStatus.PASS
            case.actual_result = f"负面信源数量：{len(sources)}"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"负面信源：{sources}"
            case.error_message = "sources 应为列表"
    
    def _test_roi_data(self, case: TestCase):
        """测试 ROI 数据"""
        if not case.response_data:
            case.status = TestStatus.SKIP
            case.actual_result = "无前序测试数据，跳过"
            return
        
        roi_analysis = case.response_data.get('roiAnalysis', {})
        
        if roi_analysis:
            case.status = TestStatus.PASS
            case.actual_result = f"ROI 数据包含 {len(roi_analysis)} 个字段"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = "ROI 数据为空"
            case.error_message = "roiAnalysis 应为非空字典"
    
    # ==================== 边界异常测试方法 ====================
    
    def _test_empty_execution_id(self, case: TestCase):
        """测试空 execution_id"""
        url = f"{self.base_url}/api/export/report-data"
        params = {"executionId": TestConfig.EMPTY_EXECUTION_ID}
        
        response = self.session.get(url, params=params, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        # 空字符串应返回 400
        if response.status_code == 400:
            case.status = TestStatus.PASS
            case.actual_result = f"状态码：{response.status_code} (正确)"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"应返回 400，实际返回 {response.status_code}"
    
    def _test_missing_execution_id(self, case: TestCase):
        """测试缺失 execution_id 参数"""
        url = f"{self.base_url}/api/export/report-data"
        # 不传 executionId 参数
        
        response = self.session.get(url, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        # 缺失参数应返回 400
        if response.status_code == 400:
            case.status = TestStatus.PASS
            case.actual_result = f"状态码：{response.status_code} (正确)"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"应返回 400，实际返回 {response.status_code}"
    
    def _test_invalid_execution_id(self, case: TestCase):
        """测试无效 execution_id"""
        url = f"{self.base_url}/api/export/report-data"
        params = {"executionId": TestConfig.INVALID_EXECUTION_ID}
        
        response = self.session.get(url, params=params, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        # 无效 ID 应返回 404
        if response.status_code == 404:
            case.status = TestStatus.PASS
            case.actual_result = f"状态码：{response.status_code} (正确)"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"应返回 404，实际返回 {response.status_code}"
    
    def _test_long_execution_id(self, case: TestCase):
        """测试超长 execution_id"""
        url = f"{self.base_url}/api/export/report-data"
        params = {"executionId": TestConfig.LONG_EXECUTION_ID}
        
        response = self.session.get(url, params=params, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        # 超长 ID 应返回 404 或 400
        if response.status_code in [400, 404]:
            case.status = TestStatus.PASS
            case.actual_result = f"状态码：{response.status_code} (正确)"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"应返回 400 或 404，实际返回 {response.status_code}"
    
    def _test_special_char_execution_id(self, case: TestCase):
        """测试特殊字符 execution_id"""
        url = f"{self.base_url}/api/export/report-data"
        params = {"executionId": "<script>alert('xss')</script>"}
        
        response = self.session.get(url, params=params, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        # 特殊字符应返回 400 或 404
        if response.status_code in [400, 404]:
            case.status = TestStatus.PASS
            case.actual_result = f"状态码：{response.status_code} (正确)"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"应返回 400 或 404，实际返回 {response.status_code}"
    
    def _test_pdf_invalid_execution_id(self, case: TestCase):
        """测试 PDF 导出 API 无效 executionId"""
        url = f"{self.base_url}/api/export/pdf"
        params = {"executionId": TestConfig.INVALID_EXECUTION_ID}
        
        response = self.session.get(url, params=params, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        # 无效 ID 应返回 404
        if response.status_code == 404:
            case.status = TestStatus.PASS
            case.actual_result = f"状态码：{response.status_code} (正确)"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"应返回 404，实际返回 {response.status_code}"
    
    def _test_html_invalid_execution_id(self, case: TestCase):
        """测试 HTML 导出 API 无效 executionId"""
        url = f"{self.base_url}/api/export/html"
        params = {"executionId": TestConfig.INVALID_EXECUTION_ID}
        
        response = self.session.get(url, params=params, timeout=TestConfig.TIMEOUT)
        case.http_status = response.status_code
        
        # 无效 ID 应返回 404
        if response.status_code == 404:
            case.status = TestStatus.PASS
            case.actual_result = f"状态码：{response.status_code} (正确)"
        else:
            case.status = TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
            case.error_message = f"应返回 404，实际返回 {response.status_code}"
    
    def generate_report(self) -> str:
        """生成测试报告"""
        total_cases = sum(len(s.test_cases) for s in self.suites)
        total_passed = sum(
            sum(1 for c in s.test_cases if c.status == TestStatus.PASS)
            for s in self.suites
        )
        
        report = []
        report.append("# Flask API 集成测试报告")
        report.append("")
        report.append(f"**测试执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**测试服务器**: {self.base_url}")
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
            report.append("| ID | 名称 | 状态 | HTTP 状态 | 耗时 (ms) | 结果/错误 |")
            report.append("|----|------|------|-----------|-----------|-----------|")
            for case in suite.test_cases:
                http_col = str(case.http_status) if case.http_status > 0 else "-"
                error_col = f"`{case.error_message[:50]}...`" if case.error_message else (case.actual_result[:50] if case.actual_result else "-")
                report.append(f"| {case.id} | {case.name} | {case.status.value} | {http_col} | {case.execution_time_ms} | {error_col} |")
            report.append("")
        
        return "\n".join(report)


# ============================================================================
# 主程序
# ============================================================================

def check_server_health(base_url: str) -> bool:
    """检查服务器是否可用"""
    try:
        response = requests.get(f"{base_url}/api/test", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    print("\n" + "="*70)
    print("  Flask API 集成测试套件")
    print("  Flask API Integration Test Suite")
    print("="*70)
    
    base_url = TestConfig.BASE_URL
    
    # 检查服务器健康
    print(f"\n检查服务器健康状态：{base_url}")
    if not check_server_health(base_url):
        print("❌ 服务器不可用，请先启动 Flask 应用：")
        print("   cd backend_python && python3 wechat_backend/app.py")
        sys.exit(1)
    
    print("✅ 服务器运行正常")
    print(f"\n测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建测试运行器
    runner = APITestRunner(base_url)
    
    # 添加测试套件
    service_suite = ServiceLayerAPITestSuite()
    runner.add_suite(service_suite)
    
    boundary_suite = BoundaryExceptionAPITestSuite()
    runner.add_suite(boundary_suite)
    
    # 运行测试（按顺序执行，因为后续测试依赖前序测试的数据）
    runner.run_suite(service_suite)
    runner.run_suite(boundary_suite)
    
    # 生成报告
    report = runner.generate_report()
    
    # 保存报告
    report_dir = os.path.join(os.path.dirname(__file__), 'test_reports')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"flask_api_integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    
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
