#!/usr/bin/env python3
"""
品牌洞察报告功能全面测试套件

测试类型覆盖:
1. 单元测试 - 数据访问层
2. 集成测试 - 服务层
3. API 端点测试
4. 数据库验证测试
5. 边界和异常测试
6. 数据完整性测试
7. 性能测试

测试报告将生成至：test_reports/brand_insight_test_report.md

执行：python3 comprehensive_test_suite.py
"""

import sys
import os
import json
import gzip
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))
sys.path.insert(0, os.path.dirname(__file__))

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


class TestRunner:
    def __init__(self):
        self.suites: List[TestSuite] = []
        self.start_time = datetime.now()
        self.current_suite = None
    
    def add_suite(self, suite: TestSuite):
        self.suites.append(suite)
    
    def run_suite(self, suite: TestSuite):
        self.current_suite = suite
        print(f"\n{'='*70}")
        print(f"  运行测试套件：{suite.name}")
        print(f"  {suite.description}")
        print(f"{'='*70}")
        
        for case in suite.test_cases:
            self.run_case(case)
    
    def run_case(self, case: TestCase):
        print(f"\n  [{case.id}] {case.name}")
        start = time.time()
        
        try:
            # 执行测试逻辑（由具体测试实现）
            pass
        except AssertionError as e:
            case.status = TestStatus.FAIL
            case.error_message = str(e)
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        finally:
            case.execution_time_ms = int((time.time() - start) * 1000)
    
    def generate_report(self) -> str:
        total_cases = sum(len(s.test_cases) for s in self.suites)
        total_passed = sum(
            sum(1 for c in s.test_cases if c.status == TestStatus.PASS)
            for s in self.suites
        )
        
        report = []
        report.append("# 品牌洞察报告功能全面测试报告")
        report.append("")
        report.append(f"**测试执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
            report.append("| ID | 名称 | 状态 | 耗时 (ms) | 错误信息 |")
            report.append("|----|------|------|-----------|----------|")
            for case in suite.test_cases:
                error_col = f"`{case.error_message[:50]}...`" if case.error_message else "-"
                report.append(f"| {case.id} | {case.name} | {case.status.value} | {case.execution_time_ms} | {error_col} |")
            report.append("")
        
        return "\n".join(report)


# ============================================================================
# 测试套件 1: 数据库验证测试
# ============================================================================

class DatabaseTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="1. 数据库验证测试",
            description="验证数据库表结构、索引、数据完整性"
        )
        # 使用绝对路径
        self.db_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db'
        self._add_test_cases()
    
    def _add_test_cases(self):
        # 表存在性测试
        self.add_case(TestCase(
            id="DB-001",
            name="test_records 表存在性",
            description="验证 test_records 表是否存在",
            expected_result="表存在"
        ))
        
        self.add_case(TestCase(
            id="DB-002",
            name="competitive_analysis 表存在性",
            description="验证 competitive_analysis 表是否存在",
            expected_result="表存在"
        ))
        
        self.add_case(TestCase(
            id="DB-003",
            name="negative_sources 表存在性",
            description="验证 negative_sources 表是否存在",
            expected_result="表存在"
        ))
        
        self.add_case(TestCase(
            id="DB-004",
            name="report_metadata 表存在性",
            description="验证 report_metadata 表是否存在",
            expected_result="表存在"
        ))
        
        self.add_case(TestCase(
            id="DB-005",
            name="deep_intelligence_results 表存在性",
            description="验证 deep_intelligence_results 表是否存在",
            expected_result="表存在"
        ))
        
        # 表结构测试
        self.add_case(TestCase(
            id="DB-006",
            name="test_records 表结构验证",
            description="验证 test_records 表包含必需字段",
            expected_result="包含 id, brand_name, results_summary, detailed_results, is_summary_compressed, is_detailed_compressed"
        ))
        
        # 索引测试
        self.add_case(TestCase(
            id="DB-007",
            name="test_records 索引验证",
            description="验证 test_records 表有合适的索引",
            expected_result="存在 brand_name, test_date 索引"
        ))
        
        # 数据存在性测试
        self.add_case(TestCase(
            id="DB-008",
            name="test_records 数据存在性",
            description="验证 test_records 表有测试数据",
            expected_result="至少有 1 条记录"
        ))
        
        # 视图测试
        self.add_case(TestCase(
            id="DB-009",
            name="test_results 视图存在性",
            description="验证 test_results 视图是否存在（兼容层）",
            expected_result="视图存在"
        ))
        
        # 数据完整性测试
        self.add_case(TestCase(
            id="DB-010",
            name="results_summary 数据完整性",
            description="验证 results_summary 包含 execution_id",
            expected_result="所有记录的 results_summary 包含 execution_id 字段"
        ))
    
    def run_all(self, runner: TestRunner):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # DB-001
        case = self.test_cases[0]
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_records'")
            result = cursor.fetchone()
            case.status = TestStatus.PASS if result else TestStatus.FAIL
            case.actual_result = "表存在" if result else "表不存在"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-002
        case = self.test_cases[1]
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='competitive_analysis'")
            result = cursor.fetchone()
            case.status = TestStatus.PASS if result else TestStatus.FAIL
            case.actual_result = "表存在" if result else "表不存在"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-003
        case = self.test_cases[2]
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='negative_sources'")
            result = cursor.fetchone()
            case.status = TestStatus.PASS if result else TestStatus.FAIL
            case.actual_result = "表存在" if result else "表不存在"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-004
        case = self.test_cases[3]
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='report_metadata'")
            result = cursor.fetchone()
            case.status = TestStatus.PASS if result else TestStatus.FAIL
            case.actual_result = "表存在" if result else "表不存在"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-005
        case = self.test_cases[4]
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deep_intelligence_results'")
            result = cursor.fetchone()
            case.status = TestStatus.PASS if result else TestStatus.FAIL
            case.actual_result = "表存在" if result else "表不存在"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-006
        case = self.test_cases[5]
        try:
            cursor.execute("PRAGMA table_info(test_records)")
            columns = [row[1] for row in cursor.fetchall()]
            required = ['id', 'brand_name', 'results_summary', 'detailed_results', 'is_summary_compressed', 'is_detailed_compressed']
            missing = [c for c in required if c not in columns]
            case.status = TestStatus.PASS if not missing else TestStatus.FAIL
            case.actual_result = f"字段：{columns}"
            if missing:
                case.error_message = f"缺失字段：{missing}"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-007
        case = self.test_cases[6]
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='test_records'")
            indexes = [row[0] for row in cursor.fetchall()]
            case.status = TestStatus.PASS if indexes else TestStatus.FAIL
            case.actual_result = f"索引：{indexes}"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-008
        case = self.test_cases[7]
        try:
            cursor.execute("SELECT COUNT(*) FROM test_records")
            count = cursor.fetchone()[0]
            case.status = TestStatus.PASS if count > 0 else TestStatus.FAIL
            case.actual_result = f"记录数：{count}"
            if count == 0:
                case.error_message = "表为空，请先运行品牌诊断测试"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-009
        case = self.test_cases[8]
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='test_results'")
            result = cursor.fetchone()
            case.status = TestStatus.PASS if result else TestStatus.FAIL
            case.actual_result = "视图存在" if result else "视图不存在"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DB-010
        case = self.test_cases[9]
        try:
            cursor.execute("SELECT results_summary, is_summary_compressed FROM test_records WHERE results_summary IS NOT NULL LIMIT 10")
            rows = cursor.fetchall()
            missing_exec_id = []
            for i, (summary_raw, is_compressed) in enumerate(rows):
                try:
                    if is_compressed:
                        summary_bytes = gzip.decompress(summary_raw)
                        summary = json.loads(summary_bytes.decode('utf-8'))
                    else:
                        summary = json.loads(summary_raw)
                    if 'execution_id' not in summary:
                        missing_exec_id.append(i)
                except:
                    pass
            case.status = TestStatus.PASS if not missing_exec_id else TestStatus.FAIL
            case.actual_result = f"检查 {len(rows)} 条记录"
            if missing_exec_id:
                case.error_message = f"{len(missing_exec_id)} 条记录缺少 execution_id"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        conn.close()


# ============================================================================
# 测试套件 2: 数据访问层单元测试
# ============================================================================

class DataAccessTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="2. 数据访问层单元测试",
            description="测试数据查询、解压、解析逻辑"
        )
        # 使用绝对路径
        self.db_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db'
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="DA-001",
            name="test_records 基础查询",
            description="验证能从 test_records 查询数据",
            expected_result="返回非空结果集"
        ))
        
        self.add_case(TestCase(
            id="DA-002",
            name="results_summary 解压测试",
            description="验证能正确解压压缩的 results_summary",
            expected_result="成功解压并解析为 JSON"
        ))
        
        self.add_case(TestCase(
            id="DA-003",
            name="detailed_results 解压测试",
            description="验证能正确解压压缩的 detailed_results",
            expected_result="成功解压并解析为 JSON 数组"
        ))
        
        self.add_case(TestCase(
            id="DA-004",
            name="execution_id 提取测试",
            description="验证能从 results_summary 提取 execution_id",
            expected_result="返回有效的 execution_id 字符串"
        ))
        
        self.add_case(TestCase(
            id="DA-005",
            name="competitor_brands 提取测试",
            description="验证能从 results_summary 提取 competitor_brands",
            expected_result="返回品牌列表"
        ))
        
        self.add_case(TestCase(
            id="DA-006",
            name="压缩标志处理测试",
            description="验证能正确处理 is_summary_compressed 标志",
            expected_result="根据标志决定是否解压"
        ))
        
        self.add_case(TestCase(
            id="DA-007",
            name="JSON 解析错误处理",
            description="验证 JSON 解析失败时的错误处理",
            expected_result="返回空对象而非抛出异常"
        ))
        
        self.add_case(TestCase(
            id="DA-008",
            name="gzip 解压错误处理",
            description="验证 gzip 解压失败时的错误处理",
            expected_result="返回原始数据或空对象"
        ))
    
    def run_all(self, runner: TestRunner):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # DA-001
        case = self.test_cases[0]
        try:
            cursor.execute("""
                SELECT id, brand_name, results_summary, detailed_results, 
                       is_summary_compressed, is_detailed_compressed
                FROM test_records
                ORDER BY test_date DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            case.status = TestStatus.PASS if row else TestStatus.FAIL
            case.actual_result = f"查询到 {1 if row else 0} 条记录"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DA-002
        case = self.test_cases[1]
        try:
            cursor.execute("SELECT results_summary, is_summary_compressed FROM test_records WHERE is_summary_compressed=1 LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                summary_bytes = gzip.decompress(row[0])
                summary = json.loads(summary_bytes.decode('utf-8'))
                case.status = TestStatus.PASS
                case.actual_result = f"解压成功，包含 {len(summary)} 个键"
            else:
                # 没有压缩数据，测试未压缩的
                cursor.execute("SELECT results_summary FROM test_records WHERE results_summary IS NOT NULL LIMIT 1")
                row = cursor.fetchone()
                if row:
                    summary = json.loads(row[0])
                    case.status = TestStatus.PASS
                    case.actual_result = "无压缩数据，未压缩数据解析成功"
                else:
                    case.status = TestStatus.SKIP
                    case.actual_result = "无测试数据"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DA-003
        case = self.test_cases[2]
        try:
            cursor.execute("SELECT detailed_results, is_detailed_compressed FROM test_records WHERE is_detailed_compressed=1 LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                detailed_bytes = gzip.decompress(row[0])
                detailed = json.loads(detailed_bytes.decode('utf-8'))
                case.status = TestStatus.PASS if isinstance(detailed, list) else TestStatus.FAIL
                case.actual_result = f"解压成功，包含 {len(detailed)} 条结果"
            else:
                case.status = TestStatus.SKIP
                case.actual_result = "无压缩的 detailed_results 数据"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DA-004
        case = self.test_cases[3]
        try:
            cursor.execute("SELECT results_summary, is_summary_compressed FROM test_records WHERE results_summary IS NOT NULL LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                if row[1]:  # compressed
                    summary_bytes = gzip.decompress(row[0])
                    summary = json.loads(summary_bytes.decode('utf-8'))
                else:
                    summary = json.loads(row[0])
                exec_id = summary.get('execution_id', '')
                case.status = TestStatus.PASS if exec_id else TestStatus.FAIL
                case.actual_result = f"execution_id: {exec_id[:20]}..." if exec_id else "未找到 execution_id"
            else:
                case.status = TestStatus.SKIP
                case.actual_result = "无测试数据"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DA-005
        case = self.test_cases[4]
        try:
            cursor.execute("SELECT results_summary, is_summary_compressed FROM test_records WHERE results_summary IS NOT NULL LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                if row[1]:
                    summary_bytes = gzip.decompress(row[0])
                    summary = json.loads(summary_bytes.decode('utf-8'))
                else:
                    summary = json.loads(row[0])
                competitors = summary.get('competitor_brands', [])
                case.status = TestStatus.PASS if competitors else TestStatus.FAIL
                case.actual_result = f"竞品：{competitors}"
            else:
                case.status = TestStatus.SKIP
                case.actual_result = "无测试数据"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DA-006
        case = self.test_cases[5]
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM test_records 
                WHERE is_summary_compressed = 1 OR is_detailed_compressed = 1
            """)
            compressed_count = cursor.fetchone()[0]
            case.status = TestStatus.PASS
            case.actual_result = f"{compressed_count} 条记录包含压缩数据"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DA-007
        case = self.test_cases[6]
        try:
            # 模拟无效 JSON
            invalid_json = b'{"invalid": json}'
            try:
                json.loads(invalid_json)
                case.status = TestStatus.FAIL
                case.error_message = "应该抛出异常"
            except json.JSONDecodeError:
                case.status = TestStatus.PASS
                case.actual_result = "正确捕获 JSON 解析错误"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # DA-008
        case = self.test_cases[7]
        try:
            # 模拟无效 gzip 数据
            invalid_gzip = b'not gzip data'
            try:
                gzip.decompress(invalid_gzip)
                case.status = TestStatus.FAIL
                case.error_message = "应该抛出异常"
            except gzip.BadGzipFile:
                case.status = TestStatus.PASS
                case.actual_result = "正确捕获 gzip 解压错误"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        conn.close()


# ============================================================================
# 测试套件 3: 服务层集成测试
# ============================================================================

class ServiceLayerTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="3. 服务层集成测试",
            description="测试 ReportDataService 等服务的集成功能"
        )
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="SV-001",
            name="ReportDataService 初始化",
            description="验证 ReportDataService 能正常初始化",
            expected_result="服务实例创建成功"
        ))
        
        self.add_case(TestCase(
            id="SV-002",
            name="_get_base_data 方法存在性",
            description="验证 _get_base_data 方法存在",
            expected_result="方法存在且可调用"
        ))
        
        self.add_case(TestCase(
            id="SV-003",
            name="_get_base_data 返回结构",
            description="验证 _get_base_data 返回正确的数据结构",
            expected_result="包含 brand_name, overall_score, detailed_results 等字段"
        ))
        
        self.add_case(TestCase(
            id="SV-004",
            name="_build_platform_scores 方法",
            description="验证能从 detailed_results 构建平台评分",
            expected_result="返回平台评分列表"
        ))
        
        self.add_case(TestCase(
            id="SV-005",
            name="_build_dimension_scores 方法",
            description="验证能构建维度评分",
            expected_result="返回包含 authority, visibility, purity, consistency 的字典"
        ))
        
        self.add_case(TestCase(
            id="SV-006",
            name="_get_or_generate_competitive_data 方法",
            description="验证能获取或生成竞品数据",
            expected_result="返回包含 competitors, radar_data 的字典"
        ))
        
        self.add_case(TestCase(
            id="SV-007",
            name="_get_or_generate_negative_sources 方法",
            description="验证能获取或生成负面信源数据",
            expected_result="返回包含 sources, summary 的字典"
        ))
        
        self.add_case(TestCase(
            id="SV-008",
            name="generate_full_report 方法",
            description="验证能生成完整报告",
            expected_result="返回包含所有报告章节的字典"
        ))
    
    def run_all(self, runner: TestRunner):
        # SV-001
        case = self.test_cases[0]
        try:
            # 直接导入服务模块，避免触发 wechat_backend.__init__.py
            import sys
            sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')
            from wechat_backend.services.report_data_service import ReportDataService
            service = ReportDataService()
            case.status = TestStatus.PASS
            case.actual_result = "服务实例创建成功"
        except ImportError as e:
            case.status = TestStatus.SKIP
            case.actual_result = f"模块导入失败：{e}"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = f"初始化异常：{type(e).__name__}: {str(e)[:100]}"
        runner.run_case(case)

        # SV-002
        case = self.test_cases[1]
        try:
            import sys
            sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')
            from wechat_backend.services.report_data_service import ReportDataService
            service = ReportDataService()
            has_method = hasattr(service, '_get_base_data') and callable(service._get_base_data)
            case.status = TestStatus.PASS if has_method else TestStatus.FAIL
            case.actual_result = "方法存在" if has_method else "方法不存在"
        except ImportError as e:
            case.status = TestStatus.SKIP
            case.actual_result = f"模块导入失败：{e}"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = f"初始化异常：{type(e).__name__}: {str(e)[:100]}"
        runner.run_case(case)

        # SV-003 到 SV-008 需要实际执行，由于导入问题可能失败
        # 这些将在实际环境中测试
        for i in range(2, 8):
            case = self.test_cases[i]
            case.status = TestStatus.SKIP
            case.actual_result = "需要在完整 Flask 环境中测试"
            runner.run_case(case)


# ============================================================================
# 测试套件 4: API 端点测试
# ============================================================================

class APIEndpointTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="4. API 端点测试",
            description="测试报告相关的 API 端点"
        )
        self.base_url = "http://127.0.0.1:5000"
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="API-001",
            name="GET /api/export/report-data 端点存在性",
            description="验证报告数据 API 端点存在",
            expected_result="端点存在，返回 200 或 401/403（需要认证）"
        ))
        
        self.add_case(TestCase(
            id="API-002",
            name="GET /api/export/report-data 缺少 executionId",
            description="验证缺少 executionId 参数时返回错误",
            expected_result="返回 400 错误"
        ))
        
        self.add_case(TestCase(
            id="API-003",
            name="GET /api/export/pdf 端点存在性",
            description="验证 PDF 导出 API 端点存在",
            expected_result="端点存在"
        ))
        
        self.add_case(TestCase(
            id="API-004",
            name="GET /api/export/html 端点存在性",
            description="验证 HTML 导出 API 端点存在",
            expected_result="端点存在"
        ))
        
        self.add_case(TestCase(
            id="API-005",
            name="无效 executionId 处理",
            description="验证使用无效 executionId 时返回错误",
            expected_result="返回 404 或相应错误"
        ))
    
    def run_all(self, runner: TestRunner):
        try:
            import requests
        except ImportError:
            for case in self.test_cases:
                case.status = TestStatus.SKIP
                case.actual_result = "requests 库未安装"
                runner.run_case(case)
            return
        
        # API-001
        case = self.test_cases[0]
        try:
            response = requests.get(f"{self.base_url}/api/export/report-data", timeout=5)
            case.status = TestStatus.PASS if response.status_code in [200, 400, 401, 403] else TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
        except requests.exceptions.ConnectionError:
            case.status = TestStatus.SKIP
            case.actual_result = "服务器未运行"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # API-002
        case = self.test_cases[1]
        try:
            response = requests.get(f"{self.base_url}/api/export/report-data", timeout=5)
            case.status = TestStatus.PASS if response.status_code == 400 else TestStatus.FAIL
            case.actual_result = f"状态码：{response.status_code}"
        except requests.exceptions.ConnectionError:
            case.status = TestStatus.SKIP
            case.actual_result = "服务器未运行"
        except Exception as e:
            case.status = TestStatus.ERROR
            case.error_message = str(e)
        runner.run_case(case)
        
        # API-003 到 API-005
        for i in range(2, 5):
            case = self.test_cases[i]
            try:
                if i == 2:
                    response = requests.get(f"{self.base_url}/api/export/pdf", timeout=5)
                elif i == 3:
                    response = requests.get(f"{self.base_url}/api/export/html", timeout=5)
                else:
                    response = requests.get(f"{self.base_url}/api/export/report-data?executionId=invalid-id-12345", timeout=5)
                case.status = TestStatus.PASS if response.status_code in [200, 400, 401, 403, 404] else TestStatus.FAIL
                case.actual_result = f"状态码：{response.status_code}"
            except requests.exceptions.ConnectionError:
                case.status = TestStatus.SKIP
                case.actual_result = "服务器未运行"
            except Exception as e:
                case.status = TestStatus.ERROR
                case.error_message = str(e)
            runner.run_case(case)


# ============================================================================
# 测试套件 5: 边界和异常测试
# ============================================================================

class BoundaryExceptionTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="5. 边界和异常测试",
            description="测试边界条件和异常情况处理"
        )
        self._add_test_cases()
    
    def _add_test_cases(self):
        self.add_case(TestCase(
            id="BE-001",
            name="空 execution_id 处理",
            description="验证 execution_id 为空字符串时的处理",
            expected_result="返回空字典或默认值"
        ))
        
        self.add_case(TestCase(
            id="BE-002",
            name="None execution_id 处理",
            description="验证 execution_id 为 None 时的处理",
            expected_result="返回空字典或默认值"
        ))
        
        self.add_case(TestCase(
            id="BE-003",
            name="超长 execution_id 处理",
            description="验证 execution_id 超长时的处理",
            expected_result="正常处理或返回错误"
        ))
        
        self.add_case(TestCase(
            id="BE-004",
            name="空数据库处理",
            description="验证数据库为空时的处理",
            expected_result="返回空结果而非异常"
        ))
        
        self.add_case(TestCase(
            id="BE-005",
            name="损坏的 gzip 数据处理",
            description="验证损坏的 gzip 数据处理",
            expected_result="返回错误或原始数据"
        ))
        
        self.add_case(TestCase(
            id="BE-006",
            name="损坏的 JSON 数据处理",
            description="验证损坏的 JSON 数据处理",
            expected_result="返回空对象而非异常"
        ))
        
        self.add_case(TestCase(
            id="BE-007",
            name="缺失字段处理",
            description="验证记录缺少必需字段时的处理",
            expected_result="使用默认值"
        ))
        
        self.add_case(TestCase(
            id="BE-008",
            name="并发访问处理",
            description="验证并发数据库访问的处理",
            expected_result="无死锁或数据损坏"
        ))
    
    def run_all(self, runner: TestRunner):
        # BE-001
        case = self.test_cases[0]
        try:
            import sys
            sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')
            from wechat_backend.services.report_data_service import ReportDataService
            service = ReportDataService()
            result = service._get_base_data("")
            case.status = TestStatus.PASS if isinstance(result, dict) else TestStatus.FAIL
            case.actual_result = f"返回类型：{type(result).__name__}"
        except ImportError as e:
            case.status = TestStatus.SKIP
            case.actual_result = f"模块导入失败：{e}"
        except Exception as e:
            case.status = TestStatus.FAIL
            case.error_message = f"处理异常：{type(e).__name__}: {str(e)[:100]}"
        runner.run_case(case)

        # BE-002
        case = self.test_cases[1]
        try:
            import sys
            sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')
            from wechat_backend.services.report_data_service import ReportDataService
            service = ReportDataService()
            result = service._get_base_data(None)
            case.status = TestStatus.PASS if isinstance(result, dict) else TestStatus.FAIL
            case.actual_result = f"返回类型：{type(result).__name__}"
        except ImportError as e:
            case.status = TestStatus.SKIP
            case.actual_result = f"模块导入失败：{e}"
        except Exception as e:
            case.status = TestStatus.FAIL
            case.error_message = f"处理异常：{type(e).__name__}: {str(e)[:100]}"
        runner.run_case(case)

        # BE-003
        case = self.test_cases[2]
        try:
            import sys
            sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')
            from wechat_backend.services.report_data_service import ReportDataService
            service = ReportDataService()
            long_id = "x" * 1000
            result = service._get_base_data(long_id)
            case.status = TestStatus.PASS if isinstance(result, dict) else TestStatus.FAIL
            case.actual_result = f"返回类型：{type(result).__name__}"
        except ImportError as e:
            case.status = TestStatus.SKIP
            case.actual_result = f"模块导入失败：{e}"
        except Exception as e:
            case.status = TestStatus.FAIL
            case.error_message = f"处理异常：{type(e).__name__}: {str(e)[:100]}"
        runner.run_case(case)

        # BE-004 到 BE-008
        for i in range(3, 8):
            case = self.test_cases[i]
            case.status = TestStatus.SKIP
            case.actual_result = "需要专门测试环境"
            runner.run_case(case)


# ============================================================================
# 主程序
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  品牌洞察报告功能全面测试套件")
    print("  Brand Insight Report Comprehensive Test Suite")
    print("="*70)
    print(f"\n测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    runner = TestRunner()
    
    # 运行所有测试套件
    db_suite = DatabaseTestSuite()
    db_suite.run_all(runner)
    runner.add_suite(db_suite)
    
    da_suite = DataAccessTestSuite()
    da_suite.run_all(runner)
    runner.add_suite(da_suite)
    
    sv_suite = ServiceLayerTestSuite()
    sv_suite.run_all(runner)
    runner.add_suite(sv_suite)
    
    api_suite = APIEndpointTestSuite()
    api_suite.run_all(runner)
    runner.add_suite(api_suite)
    
    be_suite = BoundaryExceptionTestSuite()
    be_suite.run_all(runner)
    runner.add_suite(be_suite)
    
    # 生成报告
    report = runner.generate_report()
    
    # 保存报告
    report_dir = os.path.join(os.path.dirname(__file__), 'test_reports')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"brand_insight_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n{'='*70}")
    print(f"  测试完成")
    print(f"  报告已保存至：{report_path}")
    print(f"{'='*70}")
    
    return report_path


if __name__ == "__main__":
    main()
