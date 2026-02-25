#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端集成测试验证脚本
验证前端代码的完整性和联调准备情况

测试范围：
1. 前端文件语法检查
2. SSE 客户端代码验证
3. 流式渲染代码验证
4. 草稿服务代码验证
5. 缓存服务代码验证
"""

import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

class TestColors:
    """测试输出颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """打印标题"""
    print(f"\n{TestColors.BOLD}{TestColors.BLUE}{'='*70}{TestColors.END}")
    print(f"{TestColors.BOLD}{TestColors.BLUE}  {text}{TestColors.END}")
    print(f"{TestColors.BOLD}{TestColors.BLUE}{'='*70}{TestColors.END}\n")

def print_test(name, success, details=''):
    """打印测试结果"""
    status = f"{TestColors.GREEN}✅ 通过{TestColors.END}" if success else f"{TestColors.RED}❌ 失败{TestColors.END}"
    print(f"{status} {name}")
    if details:
        print(f"   {TestColors.YELLOW}{details}{TestColors.END}")

class FrontendIntegrationTester:
    """前端集成测试器"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'tests': []
        }
    
    def check_file_exists(self, filepath):
        """检查文件是否存在"""
        return self.project_root.joinpath(filepath).exists()
    
    def run_syntax_check(self, filepath):
        """运行语法检查"""
        try:
            full_path = self.project_root / filepath
            if not full_path.exists():
                return False, f"文件不存在：{filepath}"
            
            result = subprocess.run(
                ['node', '-c', str(full_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, "语法检查通过"
            else:
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            return False, "语法检查超时"
        except Exception as e:
            return False, str(e)
    
    def test_sse_client(self):
        """测试 SSE 客户端"""
        print_header("1. SSE 客户端代码验证")
        
        filepath = Path('services/sseClient.js')
        
        if not self.check_file_exists(filepath):
            print_test("SSE 客户端文件", False, "文件不存在")
            self.results['failed'] += 1
            return False
        
        # 语法检查
        success, details = self.run_syntax_check(filepath)
        print_test("SSE 客户端语法", success, details)
        
        if success:
            self.results['passed'] += 1
            self.results['tests'].append({
                'name': 'SSE 客户端语法',
                'status': 'passed',
                'file': str(filepath)
            })
        else:
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': 'SSE 客户端语法',
                'status': 'failed',
                'file': str(filepath),
                'error': details
            })
        
        # 检查关键函数
        content = (self.project_root / filepath).read_text(encoding='utf-8')
        
        required_functions = [
            'class SSEConnection',
            'class HybridPollingController',
            'createPollingController',
            'supportsSSE'
        ]
        
        missing = []
        for func in required_functions:
            if func not in content:
                missing.append(func)
        
        if missing:
            print_test("SSE 关键函数", False, f"缺少：{', '.join(missing)}")
            self.results['warnings'] += 1
        else:
            print_test("SSE 关键函数", True, f"已实现 {len(required_functions)} 个函数")
            self.results['passed'] += 1
        
        return success
    
    def test_streaming_aggregator(self):
        """测试流式报告聚合器"""
        print_header("2. 流式报告聚合器代码验证")
        
        filepath = Path('services/streamingReportAggregator.js')
        
        if not self.check_file_exists(filepath):
            print_test("流式聚合器文件", False, "文件不存在")
            self.results['failed'] += 1
            return False
        
        # 语法检查
        success, details = self.run_syntax_check(filepath)
        print_test("流式聚合器语法", success, details)
        
        if success:
            self.results['passed'] += 1
            self.results['tests'].append({
                'name': '流式聚合器语法',
                'status': 'passed',
                'file': str(filepath)
            })
        else:
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '流式聚合器语法',
                'status': 'failed',
                'file': str(filepath),
                'error': details
            })
        
        # 检查关键类
        content = (self.project_root / filepath).read_text(encoding='utf-8')
        
        required_classes = [
            'class StreamingReportAggregator',
            'createStreamingAggregator'
        ]
        
        missing = []
        for cls in required_classes:
            if cls not in content:
                missing.append(cls)
        
        if missing:
            print_test("流式聚合器关键类", False, f"缺少：{', '.join(missing)}")
            self.results['warnings'] += 1
        else:
            print_test("流式聚合器关键类", True, f"已实现 {len(required_classes)} 个类")
            self.results['passed'] += 1
        
        return success
    
    def test_draft_service(self):
        """测试草稿服务"""
        print_header("3. 草稿服务代码验证")
        
        filepath = Path('services/draftService.js')
        
        if not self.check_file_exists(filepath):
            print_test("草稿服务文件", False, "文件不存在")
            self.results['failed'] += 1
            return False
        
        # 语法检查
        success, details = self.run_syntax_check(filepath)
        print_test("草稿服务语法", success, details)
        
        if success:
            self.results['passed'] += 1
            self.results['tests'].append({
                'name': '草稿服务语法',
                'status': 'passed',
                'file': str(filepath)
            })
        else:
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '草稿服务语法',
                'status': 'failed',
                'file': str(filepath),
                'error': details
            })
        
        # 检查关键函数
        content = (self.project_root / filepath).read_text(encoding='utf-8')
        
        required_functions = [
            'class AutoSaveScheduler',
            'saveDraft',
            'restoreDraft',
            'autoSaveScheduler'
        ]
        
        missing = []
        for func in required_functions:
            if func not in content:
                missing.append(func)
        
        if missing:
            print_test("草稿服务关键函数", False, f"缺少：{', '.join(missing)}")
            self.results['warnings'] += 1
        else:
            print_test("草稿服务关键函数", True, f"已实现 {len(required_functions)} 个函数")
            self.results['passed'] += 1
        
        return success
    
    def test_cache_service(self):
        """测试缓存服务"""
        print_header("4. 缓存服务代码验证")
        
        filepath = Path('services/cacheService.js')
        
        if not self.check_file_exists(filepath):
            print_test("缓存服务文件", False, "文件不存在")
            self.results['failed'] += 1
            return False
        
        # 语法检查
        success, details = self.run_syntax_check(filepath)
        print_test("缓存服务语法", success, details)
        
        if success:
            self.results['passed'] += 1
            self.results['tests'].append({
                'name': '缓存服务语法',
                'status': 'passed',
                'file': str(filepath)
            })
        else:
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '缓存服务语法',
                'status': 'failed',
                'file': str(filepath),
                'error': details
            })
        
        # 检查关键函数
        content = (self.project_root / filepath).read_text(encoding='utf-8')
        
        required_functions = [
            'getCachedDiagnosis',
            'cacheDiagnosis',
            'getCacheStats',
            'isCacheHit'
        ]
        
        missing = []
        for func in required_functions:
            if func not in content:
                missing.append(func)
        
        if missing:
            print_test("缓存服务关键函数", False, f"缺少：{', '.join(missing)}")
            self.results['warnings'] += 1
        else:
            print_test("缓存服务关键函数", True, f"已实现 {len(required_functions)} 个函数")
            self.results['passed'] += 1
        
        return success
    
    def test_request_utils(self):
        """测试请求工具类"""
        print_header("5. 请求工具类代码验证")
        
        filepath = Path('utils/request.js')
        
        if not self.check_file_exists(filepath):
            print_test("请求工具文件", False, "文件不存在")
            self.results['failed'] += 1
            return False
        
        # 语法检查
        success, details = self.run_syntax_check(filepath)
        print_test("请求工具语法", success, details)
        
        if success:
            self.results['passed'] += 1
            self.results['tests'].append({
                'name': '请求工具语法',
                'status': 'passed',
                'file': str(filepath)
            })
        else:
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '请求工具语法',
                'status': 'failed',
                'file': str(filepath),
                'error': details
            })
        
        # 检查关键函数
        content = (self.project_root / filepath).read_text(encoding='utf-8')
        
        required_functions = [
            'classifyError',
            'isRetryableError',
            'getRetryDelay',
            'getErrorUserMessage',
            'RETRY_CONFIG'
        ]
        
        missing = []
        for func in required_functions:
            if func not in content:
                missing.append(func)
        
        if missing:
            print_test("请求工具关键函数", False, f"缺少：{', '.join(missing)}")
            self.results['warnings'] += 1
        else:
            print_test("请求工具关键函数", True, f"已实现 {len(required_functions)} 个函数")
            self.results['passed'] += 1
        
        return success
    
    def test_index_page(self):
        """测试输入页代码"""
        print_header("6. 输入页代码验证")
        
        filepath = Path('pages/index/index.js')
        
        if not self.check_file_exists(filepath):
            print_test("输入页文件", False, "文件不存在")
            self.results['failed'] += 1
            return False
        
        # 语法检查
        success, details = self.run_syntax_check(filepath)
        print_test("输入页语法", success, details)
        
        if success:
            self.results['passed'] += 1
            self.results['tests'].append({
                'name': '输入页语法',
                'status': 'passed',
                'file': str(filepath)
            })
        else:
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '输入页语法',
                'status': 'failed',
                'file': str(filepath),
                'error': details
            })
        
        # 检查关键函数
        content = (self.project_root / filepath).read_text(encoding='utf-8')
        
        required_functions = [
            'registerAutoSave',
            'saveDraftInternal',
            'restoreDraft',
            'onUnload'
        ]
        
        missing = []
        for func in required_functions:
            if func not in content:
                missing.append(func)
        
        if missing:
            print_test("输入页自动保存函数", False, f"缺少：{', '.join(missing)}")
            self.results['warnings'] += 1
        else:
            print_test("输入页自动保存函数", True, f"已实现 {len(required_functions)} 个函数")
            self.results['passed'] += 1
        
        return success
    
    def test_results_page(self):
        """测试结果页代码"""
        print_header("7. 结果页代码验证")
        
        filepath = Path('pages/results/results.js')
        
        if not self.check_file_exists(filepath):
            print_test("结果页文件", False, "文件不存在")
            self.results['failed'] += 1
            return False
        
        # 语法检查
        success, details = self.run_syntax_check(filepath)
        print_test("结果页语法", success, details)
        
        if success:
            self.results['passed'] += 1
            self.results['tests'].append({
                'name': '结果页语法',
                'status': 'passed',
                'file': str(filepath)
            })
        else:
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '结果页语法',
                'status': 'failed',
                'file': str(filepath),
                'error': details
            })
        
        # 检查关键函数
        content = (self.project_root / filepath).read_text(encoding='utf-8')
        
        required_functions = [
            'initializePageWithStreaming',
            '_renderScoreCards',
            '_renderSOVChart',
            '_finalizeStreaming'
        ]
        
        missing = []
        for func in required_functions:
            if func not in content:
                missing.append(func)
        
        if missing:
            print_test("结果页流式渲染函数", False, f"缺少：{', '.join(missing)}")
            self.results['warnings'] += 1
        else:
            print_test("结果页流式渲染函数", True, f"已实现 {len(required_functions)} 个函数")
            self.results['passed'] += 1
        
        return success
    
    def run_all_tests(self):
        """运行所有测试"""
        print_header("🧪 前端集成测试套件")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目根目录：{self.project_root}")
        
        # 执行测试
        self.test_sse_client()
        self.test_streaming_aggregator()
        self.test_draft_service()
        self.test_cache_service()
        self.test_request_utils()
        self.test_index_page()
        self.test_results_page()
        
        # 打印汇总
        self.print_summary()
        
        return self.results['failed'] == 0
    
    def print_summary(self):
        """打印测试汇总"""
        print_header("📊 测试汇总报告")
        
        total = self.results['passed'] + self.results['failed']
        pass_rate = (self.results['passed'] / total * 100) if total > 0 else 0
        
        print(f"总测试数：{total}")
        print(f"{TestColors.GREEN}通过：{self.results['passed']}{TestColors.END}")
        print(f"{TestColors.RED}失败：{self.results['failed']}{TestColors.END}")
        print(f"{TestColors.YELLOW}警告：{self.results['warnings']}{TestColors.END}")
        print(f"通过率：{pass_rate:.1f}%")
        
        if self.results['failed'] == 0:
            print(f"\n{TestColors.GREEN}{TestColors.BOLD}🎉 所有测试通过！前端代码已准备就绪。{TestColors.END}")
        else:
            print(f"\n{TestColors.RED}{TestColors.BOLD}⚠️  有 {self.results['failed']} 个测试失败，请修复代码。{TestColors.END}")
        
        # 保存测试结果
        report = {
            'timestamp': datetime.now().isoformat(),
            'project_root': str(self.project_root),
            'summary': {
                'total': total,
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'warnings': self.results['warnings'],
                'pass_rate': pass_rate
            },
            'tests': self.results['tests']
        }
        
        report_file = f"frontend_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试报告已保存到：{report_file}")


if __name__ == '__main__':
    # 获取项目根目录（上一级）
    project_root = Path(__file__).parent.parent
    
    tester = FrontendIntegrationTester(project_root)
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
