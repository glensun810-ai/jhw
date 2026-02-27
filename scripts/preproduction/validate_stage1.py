#!/usr/bin/env python3
"""
阶段一预发布验证主脚本
整合所有验证模块，执行完整的预发布验证流程
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_environment import EnvironmentChecker
from test_cases.test_functional import FunctionalTester
from test_cases.test_performance import PerformanceTester
from test_cases.test_stability import StabilityTester
from test_cases.test_compatibility import CompatibilityTester
from test_cases.test_rollback import RollbackTester
from reports.generate_report import ReportGenerator


class Stage1Validator:
    """阶段一验证器"""
    
    def __init__(self, base_url: str, admin_key: str = 'test-key', 
                 skip_stability: bool = False, stability_duration: int = 30):
        self.base_url = base_url.rstrip('/')
        self.admin_key = admin_key
        self.skip_stability = skip_stability
        self.stability_duration = stability_duration
        self.start_time = datetime.now()
        self.results: Dict[str, List[Dict]] = {
            'environment': [],
            'functional': [],
            'performance': [],
            'stability': [],
            'compatibility': [],
            'rollback': []
        }
    
    def run_all_checks(self) -> bool:
        """运行所有验证"""
        print("\n" + "="*70)
        print("阶段一预发布验证")
        print("="*70)
        print(f"开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试环境：{self.base_url}")
        print(f"管理员密钥：{'*' * 8}")
        print(f"跳过稳定性测试：{'是' if self.skip_stability else '否'}")
        if not self.skip_stability:
            print(f"稳定性测试时长：{self.stability_duration} 分钟")
        print("="*70)
        
        env_passed = self._run_environment_check()
        if not env_passed:
            print("\n❌ 环境检查失败，请修复后重试")
            self._save_early_report("environment_check_failed")
            return False
        
        func_passed = self._run_functional_tests()
        if not func_passed:
            print("\n⚠️ 功能测试有失败项，请确认是否可接受")
        
        perf_passed = self._run_performance_tests()
        if not perf_passed:
            print("\n⚠️ 性能测试有失败项，请确认是否可接受")
        
        if not self.skip_stability:
            stability_passed = self._run_stability_tests()
            if not stability_passed:
                print("\n⚠️ 稳定性测试有失败项，请确认是否可接受")
        else:
            print("\n⊘ 跳过稳定性测试")
            self.results['stability'] = [{
                'test': '稳定性测试',
                'status': '⊘',
                'details': '用户选择跳过'
            }]
        
        compat_passed = self._run_compatibility_tests()
        if not compat_passed:
            print("\n⚠️ 兼容性测试有失败项，请确认是否可接受")
        
        rollback_passed = self._run_rollback_tests()
        if not rollback_passed:
            print("\n⚠️ 回滚测试有失败项，请确认是否可接受")
        
        report_file = self._generate_report()
        print(f"\n📊 验证报告已生成：{report_file}")
        
        return self.is_passed()
    
    def _run_environment_check(self) -> bool:
        """运行环境检查"""
        print("\n" + "-"*70)
        print("1. 运行环境检查...")
        print("-"*70)
        
        config = {
            'staging_api': self.base_url,
            'staging_db': os.getenv('STAGING_DB_PATH', '/data/staging/diagnosis.db'),
            'staging_redis': os.getenv('STAGING_REDIS_URL', 'localhost:6379'),
            'feature_flags': {
                'diagnosis_v2_state_machine': True,
                'diagnosis_v2_timeout': True,
                'diagnosis_v2_retry': True,
                'diagnosis_v2_dead_letter': True,
                'diagnosis_v2_api_logging': True,
                'diagnosis_v2_data_persistence': True,
                'diagnosis_v2_report_stub': True,
            }
        }
        
        checker = EnvironmentChecker(config)
        success = checker.run_all_checks()
        self.results['environment'] = checker.check_results
        
        return success
    
    def _run_functional_tests(self) -> bool:
        """运行功能测试"""
        print("\n" + "-"*70)
        print("2. 运行功能测试...")
        print("-"*70)
        
        tester = FunctionalTester(self.base_url, self.admin_key)
        success = tester.run_all_tests()
        self.results['functional'] = tester.test_results
        
        return success
    
    def _run_performance_tests(self) -> bool:
        """运行性能测试"""
        print("\n" + "-"*70)
        print("3. 运行性能测试...")
        print("-"*70)
        
        tester = PerformanceTester(self.base_url, timeout=600)
        success = tester.run_all_tests()
        self.results['performance'] = tester.results
        
        return success
    
    def _run_stability_tests(self) -> bool:
        """运行稳定性测试"""
        print("\n" + "-"*70)
        print(f"4. 运行稳定性测试 ({self.stability_duration} 分钟)...")
        print("-"*70)
        
        tester = StabilityTester(self.base_url, duration_minutes=self.stability_duration)
        success = tester.run_all_tests()
        self.results['stability'] = tester.results
        
        return success
    
    def _run_compatibility_tests(self) -> bool:
        """运行兼容性测试"""
        print("\n" + "-"*70)
        print("5. 运行兼容性测试...")
        print("-"*70)
        
        tester = CompatibilityTester(self.base_url, self.admin_key)
        success = tester.run_all_tests()
        self.results['compatibility'] = tester.results
        
        return success
    
    def _run_rollback_tests(self) -> bool:
        """运行回滚测试"""
        print("\n" + "-"*70)
        print("6. 运行回滚测试...")
        print("-"*70)
        
        tester = RollbackTester(self.base_url, self.admin_key)
        success = tester.run_all_tests()
        self.results['rollback'] = tester.results
        
        return success
    
    def _generate_report(self) -> str:
        """生成验证报告"""
        generator = ReportGenerator(
            results=self.results,
            start_time=self.start_time,
            base_url=self.base_url
        )
        return generator.generate()
    
    def _save_early_report(self, reason: str):
        """保存早期终止报告"""
        generator = ReportGenerator(
            results=self.results,
            start_time=self.start_time,
            base_url=self.base_url
        )
        generator.generate()
    
    def is_passed(self) -> bool:
        """判断是否通过验证"""
        total_failed = 0
        total_warnings = 0
        
        for category, results in self.results.items():
            for result in results:
                if result.get('status') == '❌':
                    total_failed += 1
                    print(f"\n❌ 致命错误：{category} - {result.get('test', result.get('check', 'unknown'))}")
                elif result.get('status') == '⚠️':
                    total_warnings += 1
        
        print("\n" + "="*70)
        print("验证总结")
        print("="*70)
        print(f"失败项数：{total_failed}")
        print(f"警告项数：{total_warnings}")
        
        if total_failed == 0:
            if total_warnings == 0:
                print("\n✅ 所有验证通过！可以进入灰度发布")
                return True
            else:
                print(f"\n⚠️ 有条件通过 - 存在 {total_warnings} 个警告项")
                print("建议：可以进入灰度发布，但需重点关注警告项")
                return True
        else:
            print(f"\n❌ 验证失败 - 存在 {total_failed} 个失败项")
            print("建议：修复失败项后重新验证")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='阶段一预发布验证',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行完整验证
  python validate_stage1.py --url https://staging-api.example.com
  
  # 跳过稳定性测试（快速验证）
  python validate_stage1.py --url https://staging-api.example.com --skip-stability
  
  # 自定义稳定性测试时长
  python validate_stage1.py --url https://staging-api.example.com --stability-duration 15
  
  # 使用自定义管理员密钥
  python validate_stage1.py --url https://staging-api.example.com --admin-key your-key
        """
    )
    
    parser.add_argument(
        '--url',
        default=os.getenv('STAGING_API_URL', 'http://localhost:5000'),
        help='预发布环境 URL (默认：http://localhost:5000)'
    )
    parser.add_argument(
        '--admin-key',
        default=os.getenv('ADMIN_API_KEY', 'test-key'),
        help='管理员 API 密钥 (默认：test-key)'
    )
    parser.add_argument(
        '--skip-stability',
        action='store_true',
        help='跳过稳定性测试'
    )
    parser.add_argument(
        '--stability-duration',
        type=int,
        default=30,
        help='稳定性测试时长 (分钟，默认：30)'
    )
    parser.add_argument(
        '--output-dir',
        default='scripts/preproduction/reports',
        help='报告输出目录'
    )
    
    args = parser.parse_args()
    
    validator = Stage1Validator(
        base_url=args.url,
        admin_key=args.admin_key,
        skip_stability=args.skip_stability,
        stability_duration=args.stability_duration
    )
    
    success = validator.run_all_checks()
    
    if success:
        print("\n🎉 阶段一验证通过，可以进入灰度发布！")
        sys.exit(0)
    else:
        print("\n❌ 阶段一验证失败，请修复问题后重试")
        sys.exit(1)


if __name__ == '__main__':
    main()
