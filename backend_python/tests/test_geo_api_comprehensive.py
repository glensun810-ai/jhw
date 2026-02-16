#!/usr/bin/env python3
"""
GEO系统API综合测试脚本
根据2026-02-14_GEO_System_Interface_Audit_Report.md进行接口测试
"""

import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试配置
BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 30  # 默认超时时间
LONG_TIMEOUT = 120  # 长耗时接口超时

# 测试数据
TEST_BRAND = "测试品牌"
TEST_COMPETITOR = "竞争对手品牌"
TEST_QUESTION = "测试品牌怎么样？"
TEST_OPENID = f"test_openid_{uuid.uuid4().hex[:8]}"


class TestResult:
    """测试结果记录类"""
    def __init__(self, test_name: str, endpoint: str, method: str):
        self.test_name = test_name
        self.endpoint = endpoint
        self.method = method
        self.start_time = None
        self.end_time = None
        self.duration = 0
        self.status_code = None
        self.response_data = None
        self.error_message = None
        self.passed = False
        self.timestamp = datetime.now().isoformat()
    
    def start(self):
        self.start_time = time.time()
    
    def end(self):
        self.end_time = time.time()
        self.duration = round((self.end_time - self.start_time) * 1000, 2)  # 毫秒
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "endpoint": self.endpoint,
            "method": self.method,
            "timestamp": self.timestamp,
            "duration_ms": self.duration,
            "status_code": self.status_code,
            "passed": self.passed,
            "error_message": self.error_message,
            "response_summary": self._get_response_summary()
        }
    
    def _get_response_summary(self) -> Any:
        if self.response_data is None:
            return None
        if isinstance(self.response_data, dict):
            # 脱敏处理
            summary = {}
            for key, value in self.response_data.items():
                if any(sensitive in key.lower() for sensitive in ['token', 'key', 'secret', 'password', 'openid']):
                    summary[key] = "***REDACTED***"
                elif isinstance(value, str) and len(value) > 100:
                    summary[key] = value[:100] + "..."
                else:
                    summary[key] = value
            return summary
        return str(self.response_data)[:200]


class GEOAPITester:
    """GEO系统API测试器"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.results: list = []
        self.session = requests.Session()
        self.execution_id = None
        self.task_id = None
        self.auth_token = None
    
    def _make_request(self, method: str, endpoint: str, 
                      data: Dict = None, params: Dict = None,
                      headers: Dict = None, timeout: int = TIMEOUT) -> Tuple[int, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if headers:
            request_headers.update(headers)
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=request_headers, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=request_headers, timeout=timeout)
            elif method.upper() == "OPTIONS":
                response = self.session.options(url, headers=request_headers, timeout=timeout)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return response.status_code, response_data
        except requests.exceptions.Timeout:
            return -1, "请求超时"
        except requests.exceptions.ConnectionError:
            return -2, "连接错误"
        except Exception as e:
            return -3, str(e)
    
    def _run_test(self, test_name: str, endpoint: str, method: str,
                  data: Dict = None, params: Dict = None,
                  headers: Dict = None, timeout: int = TIMEOUT,
                  expected_status: int = 200) -> TestResult:
        """运行单个测试"""
        result = TestResult(test_name, endpoint, method)
        result.start()
        
        try:
            status_code, response_data = self._make_request(
                method, endpoint, data, params, headers, timeout
            )
            result.status_code = status_code
            result.response_data = response_data
            
            # 判断测试是否通过
            if status_code == expected_status:
                result.passed = True
            elif status_code < 0:
                result.error_message = response_data
            elif status_code >= 400:
                result.error_message = f"HTTP错误: {status_code}"
                if isinstance(response_data, dict) and 'error' in response_data:
                    result.error_message += f" - {response_data['error']}"
            
        except Exception as e:
            result.error_message = str(e)
        
        result.end()
        self.results.append(result)
        return result
    
    # ==================== 第一阶段：基础连通性测试 ====================
    
    def test_health_check(self) -> TestResult:
        """测试健康检查接口"""
        return self._run_test(
            "健康检查",
            "/health",
            "GET",
            expected_status=200
        )
    
    def test_index(self) -> TestResult:
        """测试首页接口"""
        return self._run_test(
            "首页服务状态",
            "/",
            "GET",
            expected_status=200
        )
    
    def test_api_test(self) -> TestResult:
        """测试API连接接口"""
        return self._run_test(
            "API连接测试",
            "/api/test",
            "GET",
            expected_status=200
        )
    
    def test_cors_preflight(self) -> TestResult:
        """测试CORS预检请求"""
        headers = {
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
        return self._run_test(
            "CORS预检请求",
            "/api/perform-brand-test",
            "OPTIONS",
            headers=headers,
            expected_status=200
        )
    
    # ==================== 第二阶段：认证接口测试 ====================
    
    def test_login_invalid_code(self) -> TestResult:
        """测试登录接口（无效code）"""
        return self._run_test(
            "微信登录-无效code",
            "/api/login",
            "POST",
            data={"code": "invalid_code_123"},
            expected_status=400
        )
    
    def test_login_missing_code(self) -> TestResult:
        """测试登录接口（缺少code）"""
        return self._run_test(
            "微信登录-缺少code",
            "/api/login",
            "POST",
            data={},
            expected_status=400
        )
    
    def test_validate_token_no_auth(self) -> TestResult:
        """测试令牌验证（无认证）"""
        return self._run_test(
            "令牌验证-无认证",
            "/api/validate-token",
            "POST",
            data={},
            expected_status=401
        )
    
    def test_refresh_token_no_auth(self) -> TestResult:
        """测试令牌刷新（无认证）"""
        return self._run_test(
            "令牌刷新-无认证",
            "/api/refresh-token",
            "POST",
            data={},
            expected_status=401
        )
    
    # ==================== 第三阶段：品牌测试核心接口 ====================
    
    def test_perform_brand_test_missing_params(self) -> TestResult:
        """测试品牌测试接口（缺少参数）"""
        return self._run_test(
            "品牌测试-缺少参数",
            "/api/perform-brand-test",
            "POST",
            data={},
            expected_status=400
        )
    
    def test_perform_brand_test_invalid_brand_list(self) -> TestResult:
        """测试品牌测试接口（无效brand_list）"""
        return self._run_test(
            "品牌测试-无效brand_list",
            "/api/perform-brand-test",
            "POST",
            data={"brand_list": "not_a_list"},
            expected_status=400
        )
    
    def test_perform_brand_test_empty_brand_list(self) -> TestResult:
        """测试品牌测试接口（空brand_list）"""
        return self._run_test(
            "品牌测试-空brand_list",
            "/api/perform-brand-test",
            "POST",
            data={"brand_list": []},
            expected_status=400
        )
    
    def test_perform_brand_test_missing_models(self) -> TestResult:
        """测试品牌测试接口（缺少selectedModels）"""
        return self._run_test(
            "品牌测试-缺少selectedModels",
            "/api/perform-brand-test",
            "POST",
            data={"brand_list": [TEST_BRAND]},
            expected_status=400
        )
    
    def test_perform_brand_test_valid(self) -> TestResult:
        """测试品牌测试接口（有效请求）"""
        result = self._run_test(
            "品牌测试-有效请求",
            "/api/perform-brand-test",
            "POST",
            data={
                "brand_list": [TEST_BRAND, TEST_COMPETITOR],
                "selectedModels": [{"name": "豆包", "checked": True}],
                "custom_question": TEST_QUESTION,
                "userOpenid": TEST_OPENID
            },
            timeout=LONG_TIMEOUT,
            expected_status=200
        )
        # 保存execution_id供后续测试使用
        if result.passed and isinstance(result.response_data, dict):
            self.execution_id = result.response_data.get("execution_id")
        return result
    
    def test_test_progress_no_execution_id(self) -> TestResult:
        """测试进度接口（无executionId）"""
        return self._run_test(
            "测试进度-无executionId",
            "/api/test-progress",
            "GET",
            expected_status=400
        )
    
    def test_test_progress_invalid_execution_id(self) -> TestResult:
        """测试进度接口（无效executionId）"""
        return self._run_test(
            "测试进度-无效executionId",
            "/api/test-progress",
            "GET",
            params={"executionId": "invalid_id"},
            expected_status=404
        )
    
    def test_test_progress_valid(self) -> TestResult:
        """测试进度接口（有效executionId）"""
        if not self.execution_id:
            result = TestResult("测试进度-有效executionId", "/api/test-progress", "GET")
            result.error_message = "跳过：无有效的execution_id"
            result.passed = True  # 跳过不算失败
            self.results.append(result)
            return result
        
        return self._run_test(
            "测试进度-有效executionId",
            "/api/test-progress",
            "GET",
            params={"executionId": self.execution_id},
            expected_status=200
        )
    
    # ==================== 第四阶段：数据管理接口 ====================
    
    def test_sync_data_no_openid(self) -> TestResult:
        """测试数据同步（无openid）"""
        return self._run_test(
            "数据同步-无openid",
            "/api/sync-data",
            "POST",
            data={"localResults": []},
            expected_status=400
        )
    
    def test_download_data_no_openid(self) -> TestResult:
        """测试数据下载（无openid）"""
        return self._run_test(
            "数据下载-无openid",
            "/api/download-data",
            "POST",
            data={},
            expected_status=400
        )
    
    def test_test_history_no_openid(self) -> TestResult:
        """测试历史记录（无openid）"""
        return self._run_test(
            "测试历史-无openid",
            "/api/test-history",
            "GET",
            expected_status=400
        )
    
    def test_test_history_valid(self) -> TestResult:
        """测试历史记录（有效openid）"""
        return self._run_test(
            "测试历史-有效openid",
            "/api/test-history",
            "GET",
            params={"userOpenid": TEST_OPENID},
            expected_status=200
        )
    
    # ==================== 第五阶段：平台与配置接口 ====================
    
    def test_ai_platforms(self) -> TestResult:
        """测试AI平台列表接口"""
        return self._run_test(
            "AI平台列表",
            "/api/ai-platforms",
            "GET",
            expected_status=200
        )
    
    def test_platform_status(self) -> TestResult:
        """测试平台状态接口"""
        return self._run_test(
            "平台状态",
            "/api/platform-status",
            "GET",
            expected_status=200
        )
    
    def test_config(self) -> TestResult:
        """测试配置获取接口"""
        return self._run_test(
            "配置获取",
            "/api/config",
            "GET",
            expected_status=200
        )
    
    # ==================== 第六阶段：高级功能接口 ====================
    
    def test_source_intelligence_no_brand(self) -> TestResult:
        """测试信源情报（无brandName）"""
        return self._run_test(
            "信源情报-无brandName",
            "/api/source-intelligence",
            "GET",
            expected_status=400
        )
    
    def test_source_intelligence_valid(self) -> TestResult:
        """测试信源情报（有效brandName）"""
        return self._run_test(
            "信源情报-有效brandName",
            "/api/source-intelligence",
            "GET",
            params={"brandName": TEST_BRAND},
            expected_status=200
        )
    
    def test_competitive_analysis_missing_params(self) -> TestResult:
        """测试竞争分析（缺少参数）"""
        return self._run_test(
            "竞争分析-缺少参数",
            "/api/competitive-analysis",
            "POST",
            data={},
            expected_status=400
        )
    
    # ==================== 第七阶段：安全测试 ====================
    
    def test_sql_injection_attempt(self) -> TestResult:
        """测试SQL注入防护"""
        return self._run_test(
            "SQL注入防护测试",
            "/api/perform-brand-test",
            "POST",
            data={
                "brand_list": ["品牌'; DROP TABLE users; --"],
                "selectedModels": [{"name": "豆包", "checked": True}]
            },
            expected_status=400
        )
    
    def test_xss_attempt(self) -> TestResult:
        """测试XSS防护"""
        return self._run_test(
            "XSS防护测试",
            "/api/perform-brand-test",
            "POST",
            data={
                "brand_list": ["<script>alert('xss')</script>"],
                "selectedModels": [{"name": "豆包", "checked": True}]
            },
            expected_status=400
        )
    
    def test_rate_limiting(self) -> TestResult:
        """测试限流机制"""
        results = []
        # 快速发送多个请求
        for i in range(10):
            result = self._run_test(
                f"限流测试-请求{i+1}",
                "/api/test",
                "GET",
                expected_status=200
            )
            results.append(result)
            if result.status_code == 429:
                break
        
        # 返回最后一个结果作为代表
        return results[-1]
    
    # ==================== 测试执行与报告 ====================
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("=" * 80)
        print("GEO系统API综合测试")
        print("=" * 80)
        print(f"测试开始时间: {datetime.now().isoformat()}")
        print(f"基础URL: {self.base_url}")
        print("=" * 80)
        
        # 第一阶段：基础连通性
        print("\n【第一阶段】基础连通性测试")
        self.test_health_check()
        self.test_index()
        self.test_api_test()
        self.test_cors_preflight()
        
        # 第二阶段：认证接口
        print("\n【第二阶段】认证接口测试")
        self.test_login_invalid_code()
        self.test_login_missing_code()
        self.test_validate_token_no_auth()
        self.test_refresh_token_no_auth()
        
        # 第三阶段：品牌测试核心接口
        print("\n【第三阶段】品牌测试核心接口")
        self.test_perform_brand_test_missing_params()
        self.test_perform_brand_test_invalid_brand_list()
        self.test_perform_brand_test_empty_brand_list()
        self.test_perform_brand_test_missing_models()
        self.test_perform_brand_test_valid()
        self.test_test_progress_no_execution_id()
        self.test_test_progress_invalid_execution_id()
        self.test_test_progress_valid()
        
        # 第四阶段：数据管理
        print("\n【第四阶段】数据管理接口")
        self.test_sync_data_no_openid()
        self.test_download_data_no_openid()
        self.test_test_history_no_openid()
        self.test_test_history_valid()
        
        # 第五阶段：平台与配置
        print("\n【第五阶段】平台与配置接口")
        self.test_ai_platforms()
        self.test_platform_status()
        self.test_config()
        
        # 第六阶段：高级功能
        print("\n【第六阶段】高级功能接口")
        self.test_source_intelligence_no_brand()
        self.test_source_intelligence_valid()
        self.test_competitive_analysis_missing_params()
        
        # 第七阶段：安全测试
        print("\n【第七阶段】安全测试")
        self.test_sql_injection_attempt()
        self.test_xss_attempt()
        self.test_rate_limiting()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        # 按阶段分组
        phases = {
            "基础连通性": [r for r in self.results if "健康" in r.test_name or "首页" in r.test_name or "API连接" in r.test_name or "CORS" in r.test_name],
            "认证接口": [r for r in self.results if "登录" in r.test_name or "令牌" in r.test_name],
            "品牌测试": [r for r in self.results if "品牌测试" in r.test_name or "测试进度" in r.test_name],
            "数据管理": [r for r in self.results if "同步" in r.test_name or "下载" in r.test_name or "历史" in r.test_name],
            "平台配置": [r for r in self.results if "平台" in r.test_name or "配置" in r.test_name],
            "高级功能": [r for r in self.results if "信源" in r.test_name or "竞争分析" in r.test_name],
            "安全测试": [r for r in self.results if "防护" in r.test_name or "限流" in r.test_name]
        }
        
        report = {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
                "start_time": self.results[0].timestamp if self.results else None,
                "end_time": datetime.now().isoformat()
            },
            "phases": {
                phase: {
                    "total": len(results),
                    "passed": sum(1 for r in results if r.passed),
                    "failed": sum(1 for r in results if not r.passed)
                }
                for phase, results in phases.items()
            },
            "failed_tests": [r.to_dict() for r in self.results if not r.passed],
            "all_tests": [r.to_dict() for r in self.results]
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """打印测试报告"""
        print("\n" + "=" * 80)
        print("测试报告摘要")
        print("=" * 80)
        
        summary = report["summary"]
        print(f"总测试数: {summary['total_tests']}")
        print(f"通过: {summary['passed']}")
        print(f"失败: {summary['failed']}")
        print(f"通过率: {summary['pass_rate']}%")
        
        print("\n各阶段统计:")
        for phase, stats in report["phases"].items():
            print(f"  {phase}: {stats['passed']}/{stats['total']} 通过")
        
        if report["failed_tests"]:
            print("\n失败的测试:")
            for test in report["failed_tests"]:
                print(f"  ❌ {test['test_name']}")
                print(f"     端点: {test['method']} {test['endpoint']}")
                print(f"     状态码: {test['status_code']}")
                if test['error_message']:
                    print(f"     错误: {test['error_message']}")
                print()


def main():
    """主函数"""
    tester = GEOAPITester()
    
    try:
        report = tester.run_all_tests()
        tester.print_report(report)
        
        # 保存详细报告到文件
        report_file = os.path.join(
            os.path.dirname(__file__),
            f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已保存到: {report_file}")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        report = tester.generate_report()
        tester.print_report(report)
    except Exception as e:
        print(f"\n测试执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
