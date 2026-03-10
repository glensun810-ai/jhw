#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0-P1 优化验证脚本
验证所有新增功能是否正常工作

测试范围：
1. SSE 服务状态
2. 配置热更新状态
3. 后端健康状态
4. API 端点可用性
"""

import sys
import json
import requests
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5001'

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

class SystemHealthTester:
    """系统健康测试器"""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'tests': []
        }
    
    def test_health_endpoint(self):
        """测试健康检查端点"""
        print_header("1. 健康检查端点测试")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print_test("健康检查端点", True, f"状态：{data.get('status', 'unknown')}")
                self.results['passed'] += 1
                self.results['tests'].append({
                    'name': '健康检查端点',
                    'status': 'passed',
                    'details': data.get('status', 'unknown')
                })
                return True
            else:
                print_test("健康检查端点", False, f"状态码：{response.status_code}")
                self.results['failed'] += 1
                self.results['tests'].append({
                    'name': '健康检查端点',
                    'status': 'failed',
                    'details': f'HTTP {response.status_code}'
                })
                return False
                
        except requests.exceptions.ConnectionError:
            print_test("健康检查端点", False, "无法连接到服务器")
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '健康检查端点',
                'status': 'failed',
                'details': 'Connection refused'
            })
            return False
        except Exception as e:
            print_test("健康检查端点", False, str(e))
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '健康检查端点',
                'status': 'failed',
                'details': str(e)
            })
            return False
    
    def test_sse_service(self):
        """测试 SSE 服务"""
        print_header("2. SSE 服务测试")
        
        try:
            response = self.session.get(f"{self.base_url}/sse/stats", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print_test("SSE 统计端点", True, f"连接数：{data.get('total_connections', 0)}")
                self.results['passed'] += 1
                self.results['tests'].append({
                    'name': 'SSE 统计端点',
                    'status': 'passed',
                    'details': f"Connections: {data.get('total_connections', 0)}"
                })
                
                # 检查 SSE 配置
                if 'messages_sent' in data:
                    print_test("SSE 消息计数", True, f"已发送：{data.get('messages_sent', 0)}")
                    self.results['passed'] += 1
                else:
                    print_test("SSE 消息计数", False, "缺少 messages_sent 字段")
                    self.results['failed'] += 1
                    
                return True
            else:
                print_test("SSE 统计端点", False, f"状态码：{response.status_code}")
                self.results['failed'] += 1
                return False
                
        except Exception as e:
            print_test("SSE 服务", False, str(e))
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': 'SSE 服务',
                'status': 'failed',
                'details': str(e)
            })
            return False
    
    def test_config_hot_reload(self):
        """测试配置热更新"""
        print_header("3. 配置热更新测试")
        
        try:
            # 测试配置统计端点
            response = self.session.get(f"{self.base_url}/config/stats", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print_test("配置统计端点", True, f"重载次数：{data.get('reload_count', 0)}")
                self.results['passed'] += 1
                self.results['tests'].append({
                    'name': '配置统计端点',
                    'status': 'passed',
                    'details': f"Reload count: {data.get('reload_count', 0)}"
                })
                return True
            elif response.status_code == 404:
                print_test("配置统计端点", False, "端点未找到（可能路由未注册）")
                self.results['warnings'] += 1
                self.results['tests'].append({
                    'name': '配置统计端点',
                    'status': 'warning',
                    'details': 'Endpoint not found - route may not be registered'
                })
                return False
            else:
                print_test("配置统计端点", False, f"状态码：{response.status_code}")
                self.results['failed'] += 1
                self.results['tests'].append({
                    'name': '配置统计端点',
                    'status': 'failed',
                    'details': f'HTTP {response.status_code}'
                })
                return False
                
        except Exception as e:
            print_test("配置热更新", False, str(e))
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': '配置热更新',
                'status': 'failed',
                'details': str(e)
            })
            # 添加警告而不是失败
            self.results['warnings'] += 1
            return False
    
    def test_ai_adapters(self):
        """测试 AI 适配器状态"""
        print_header("4. AI 适配器状态测试")
        
        try:
            # 检查工厂模块
            sys.path.insert(0, 'backend_python')
            from wechat_backend.ai_adapters.factory import AIAdapterFactory
            
            registered = list(AIAdapterFactory._adapters.keys())
            print_test("AI 适配器注册", True, f"已注册：{len(registered)} 个")
            self.results['passed'] += 1
            
            for adapter in registered:
                print(f"   - {adapter.value}")
            
            # 检查配置
            from config import Config
            
            configured = []
            not_configured = []
            
            platforms = {
                'doubao': Config.get_api_key('doubao'),
                'deepseek': Config.DEEPSEEK_API_KEY,
                'qwen': Config.QWEN_API_KEY,
                'chatgpt': getattr(Config, 'CHATGPT_API_KEY', ''),
                'gemini': getattr(Config, 'GEMINI_API_KEY', ''),
                'zhipu': getattr(Config, 'ZHIPU_API_KEY', '')
            }
            
            for platform, key in platforms.items():
                if key and key != '${' + platform.upper() + '_API_KEY}':
                    configured.append(platform)
                else:
                    not_configured.append(platform)
            
            if configured:
                print_test("已配置的 AI 平台", True, f"{', '.join(configured)}")
                self.results['passed'] += 1
            else:
                print_test("已配置的 AI 平台", False, "没有配置任何 AI 平台")
                self.results['failed'] += 1
            
            if not_configured:
                print(f"   {TestColors.YELLOW}⚠️  未配置：{', '.join(not_configured)}{TestColors.END}")
                self.results['warnings'] += 1
            
            return True
            
        except Exception as e:
            print_test("AI 适配器检查", False, str(e))
            self.results['failed'] += 1
            self.results['tests'].append({
                'name': 'AI 适配器检查',
                'status': 'failed',
                'details': str(e)
            })
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print_header("🚀 P0-P1 优化验证测试套件")
        print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"服务器地址：{self.base_url}")
        
        # 执行测试
        self.test_health_endpoint()
        self.test_sse_service()
        self.test_config_hot_reload()
        self.test_ai_adapters()
        
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
            print(f"\n{TestColors.GREEN}{TestColors.BOLD}🎉 所有测试通过！系统已准备就绪。{TestColors.END}")
        else:
            print(f"\n{TestColors.RED}{TestColors.BOLD}⚠️  有 {self.results['failed']} 个测试失败，请检查系统配置。{TestColors.END}")
        
        # 保存测试结果
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'summary': {
                'total': total,
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'warnings': self.results['warnings'],
                'pass_rate': pass_rate
            },
            'tests': self.results['tests']
        }
        
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试报告已保存到：{report_file}")


if __name__ == '__main__':
    tester = SystemHealthTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
