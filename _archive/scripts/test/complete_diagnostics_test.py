#!/usr/bin/env python3
"""
完整诊断测试套件
用于系统性排查403错误的根本原因
"""

import os
import sys
import json
import requests
import traceback
from pathlib import Path
from typing import Dict, Any, List

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class CompleteDiagnostics:
    def __init__(self):
        self.results = {}
        self.backend_port = 5000  # 使用5000端口
        self.backend_url = f"http://127.0.0.1:{self.backend_port}"
        
    def load_environment(self):
        """加载环境变量"""
        print("🔍 正在加载环境变量...")
        env_file = project_root / '.env'
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            value = value.strip().strip('"\'')
                            os.environ[key] = value
                print("✅ 环境变量加载成功")
                self.results['env_loaded'] = True
                return True
            except Exception as e:
                print(f"❌ 环境变量加载失败: {e}")
                self.results['env_loaded'] = False
                return False
        else:
            print("❌ .env 文件未找到")
            self.results['env_loaded'] = False
            return False

    def test_api_keys(self):
        """测试API密钥配置"""
        print("\n" + "="*60)
        print("🧪 API密钥配置测试")
        print("="*60)
        
        api_keys = {
            'DEEPSEEK': os.environ.get('DEEPSEEK_API_KEY'),
            'QWEN': os.environ.get('QWEN_API_KEY'),
            'DOUBAO': os.environ.get('DOUBAO_API_KEY'),
            'CHATGPT': os.environ.get('CHATGPT_API_KEY'),
            'GEMINI': os.environ.get('GEMINI_API_KEY'),
            'ZHIPU': os.environ.get('ZHIPU_API_KEY')
        }
        
        key_results = {}
        for platform, key in api_keys.items():
            if key:
                # 基本格式检查
                is_valid_format = len(key) > 10 and 'sk-' not in key and '[在此粘贴你的Key]' not in key
                key_results[platform] = {
                    'configured': True,
                    'format_valid': is_valid_format,
                    'length': len(key)
                }
                status = "✅" if is_valid_format else "⚠️"
                print(f"{status} {platform:8} | 长度: {len(key):3} | 格式: {'有效' if is_valid_format else '可疑'}")
            else:
                key_results[platform] = {'configured': False}
                print(f"❌ {platform:8} | 未配置")
        
        self.results['api_keys'] = key_results
        return key_results

    def test_backend_connection(self):
        """测试后端服务连接"""
        print("\n" + "="*60)
        print("🌐 后端服务连接测试")
        print("="*60)
        
        try:
            # 测试基础连接
            response = requests.get(f"{self.backend_url}/", timeout=5)
            print(f"✅ 基础端点连接成功: {response.status_code}")
            self.results['backend_connection'] = {
                'status': 'success',
                'status_code': response.status_code
            }
            
            # 测试健康检查
            health_response = requests.get(f"{self.backend_url}/health", timeout=5)
            print(f"✅ 健康检查端点: {health_response.status_code}")
            self.results['health_check'] = {
                'status': 'success' if health_response.status_code == 200 else 'failed',
                'status_code': health_response.status_code
            }
            
            # 测试API测试端点
            test_response = requests.get(f"{self.backend_url}/api/test", timeout=5)
            print(f"✅ API测试端点: {test_response.status_code}")
            self.results['api_test_endpoint'] = {
                'status': 'success' if test_response.status_code == 200 else 'failed',
                'status_code': test_response.status_code
            }
            
            return True
            
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到后端服务")
            print("   请确保后端服务已启动: cd backend_python && python3 run.py")
            self.results['backend_connection'] = {'status': 'failed', 'error': 'Connection refused'}
            return False
        except Exception as e:
            print(f"❌ 连接测试异常: {e}")
            self.results['backend_connection'] = {'status': 'failed', 'error': str(e)}
            return False

    def test_auth_endpoints(self):
        """测试认证相关端点"""
        print("\n" + "="*60)
        print("🔐 认证端点测试")
        print("="*60)
        
        auth_results = {}
        
        # 测试配置端点（通常不需要认证）
        try:
            config_response = requests.get(f"{self.backend_url}/api/config", timeout=5)
            print(f"✅ 配置端点: {config_response.status_code}")
            auth_results['config_endpoint'] = {
                'status': 'success' if config_response.status_code == 200 else 'failed',
                'status_code': config_response.status_code
            }
        except Exception as e:
            print(f"❌ 配置端点测试失败: {e}")
            auth_results['config_endpoint'] = {'status': 'failed', 'error': str(e)}
        
        # 测试需要认证的端点
        test_data = {
            "brand_list": ["测试品牌"],
            "selectedModels": ["DeepSeek"],
            "custom_question": "测试问题"
        }
        
        try:
            brand_test_response = requests.post(
                f"{self.backend_url}/api/perform-brand-test",
                json=test_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"✅ 品牌测试端点: {brand_test_response.status_code}")
            auth_results['brand_test_endpoint'] = {
                'status': 'success' if brand_test_response.status_code in [200, 400] else 'failed',
                'status_code': brand_test_response.status_code,
                'response_data': brand_test_response.text[:200] if brand_test_response.text else 'No response'
            }
        except Exception as e:
            print(f"❌ 品牌测试端点测试失败: {e}")
            auth_results['brand_test_endpoint'] = {'status': 'failed', 'error': str(e)}
        
        self.results['auth_endpoints'] = auth_results
        return auth_results

    def test_model_adapters(self):
        """测试模型适配器配置"""
        print("\n" + "="*60)
        print("🔌 模型适配器配置测试")
        print("="*60)
        
        try:
            from backend_python.wechat_backend.ai_adapters.factory import AIAdapterFactory
            
            # 测试模型名称映射
            test_models = ['DeepSeek', '豆包', '通义千问', '智谱AI']
            print("模型名称映射测试:")
            mapping_results = {}
            for model in test_models:
                normalized = AIAdapterFactory.get_normalized_model_name(model)
                mapping_results[model] = normalized
                print(f"  {model} -> {normalized}")
            
            # 测试平台可用性
            platforms = ['deepseek', 'doubao', 'qwen', 'zhipu']
            print("\n平台可用性检查:")
            availability_results = {}
            for platform in platforms:
                is_available = AIAdapterFactory.is_platform_available(platform)
                availability_results[platform] = is_available
                status = "✅" if is_available else "❌"
                print(f"  {status} {platform}")
            
            self.results['model_adapters'] = {
                'mapping': mapping_results,
                'availability': availability_results
            }
            return True
            
        except Exception as e:
            print(f"❌ 适配器测试失败: {e}")
            self.results['model_adapters'] = {'status': 'failed', 'error': str(e)}
            return False

    def test_config_module(self):
        """测试配置模块"""
        print("\n" + "="*60)
        print("⚙️ 配置模块测试")
        print("="*60)
        
        try:
            from backend_python.config import Config
            
            # 测试API密钥获取
            platforms = ['deepseek', 'qwen', 'doubao', 'chatgpt', 'gemini', 'zhipu']
            print("通过Config模块获取的API密钥:")
            config_results = {}
            for platform in platforms:
                api_key = Config.get_api_key(platform)
                is_configured = Config.is_api_key_configured(platform) if api_key else False
                config_results[platform] = {
                    'has_key': bool(api_key),
                    'configured': is_configured
                }
                status = "✅" if is_configured else ("⚠️" if api_key else "❌")
                key_display = api_key[:15] + "..." if api_key else "None"
                print(f"{status} {platform:8} | 密钥: {key_display} | 配置: {is_configured}")
            
            self.results['config_module'] = config_results
            return True
            
        except Exception as e:
            print(f"❌ 配置模块测试失败: {e}")
            self.results['config_module'] = {'status': 'failed', 'error': str(e)}
            return False

    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "="*60)
        print("📊 诊断报告生成")
        print("="*60)
        
        # 保存详细结果
        report_file = project_root / 'diagnostics_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"✅ 详细诊断报告已保存到: {report_file}")
        
        # 生成总结报告
        summary = self.generate_summary()
        summary_file = project_root / 'diagnostics_summary.md'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"✅ 摘要报告已保存到: {summary_file}")
        
        print("\n" + summary)
        
    def generate_summary(self) -> str:
        """生成摘要报告"""
        summary = "# 完整诊断测试报告摘要\n\n"
        
        # 环境变量状态
        env_status = "✅ 正常" if self.results.get('env_loaded') else "❌ 异常"
        summary += f"## 环境变量状态: {env_status}\n\n"
        
        # 后端连接状态
        conn_result = self.results.get('backend_connection', {})
        conn_status = "✅ 正常" if conn_result.get('status') == 'success' else "❌ 异常"
        summary += f"## 后端连接状态: {conn_status}\n"
        if conn_result.get('status_code'):
            summary += f"   状态码: {conn_result['status_code']}\n\n"
        
        # API密钥状态
        api_keys = self.results.get('api_keys', {})
        configured_keys = sum(1 for key in api_keys.values() if key.get('configured'))
        total_keys = len(api_keys)
        summary += f"## API密钥配置: {configured_keys}/{total_keys} 个平台已配置\n\n"
        
        # 认证端点状态
        auth_endpoints = self.results.get('auth_endpoints', {})
        success_count = sum(1 for endpoint in auth_endpoints.values() if endpoint.get('status') == 'success')
        total_endpoints = len(auth_endpoints)
        summary += f"## 认证端点测试: {success_count}/{total_endpoints} 个端点正常\n\n"
        
        # 根因分析
        summary += "## 可能的根因分析\n\n"
        
        if not self.results.get('env_loaded'):
            summary += "❌ 环境变量未正确加载，检查 .env 文件路径和格式\n\n"
        elif conn_result.get('status') != 'success':
            summary += "❌ 后端服务连接失败，检查服务是否启动及端口配置\n\n"
        elif success_count < total_endpoints:
            failed_endpoints = [name for name, info in auth_endpoints.items() 
                              if info.get('status') != 'success']
            summary += f"❌ 部分认证端点异常: {', '.join(failed_endpoints)}\n\n"
        else:
            summary += "✅ 基础配置正常，问题可能出现在具体业务逻辑层\n\n"
        
        # 建议操作
        summary += "## 建议操作步骤\n\n"
        summary += "1. 确保后端服务正在运行\n"
        summary += "2. 验证所有API密钥的有效性\n"
        summary += "3. 检查认证装饰器配置\n"
        summary += "4. 查看详细的诊断报告文件\n"
        
        return summary

    def run_complete_diagnostics(self):
        """运行完整的诊断测试"""
        print("🚀 开始完整诊断测试")
        print("="*60)
        
        # 执行各项测试
        self.load_environment()
        self.test_api_keys()
        self.test_backend_connection()
        self.test_auth_endpoints()
        self.test_model_adapters()
        self.test_config_module()
        
        # 生成报告
        self.generate_report()
        
        print("\n" + "="*60)
        print("🏁 诊断测试完成")
        print("="*60)

def main():
    diagnostics = CompleteDiagnostics()
    diagnostics.run_complete_diagnostics()

if __name__ == '__main__':
    main()