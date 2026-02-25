#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统综合验证脚本
验证所有 P0/P1/P2 修复是否生效
"""

import os
import sys
import json
import requests
from pathlib import Path

# 添加项目根目录到路径
base_dir = Path(__file__).parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

# 加载环境变量
from dotenv import load_dotenv
env_file = base_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ 已加载环境变量：{env_file}")

BASE_URL = "http://127.0.0.1:5001"

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(name: str, success: bool, details: str = ""):
    status = "✅" if success else "❌"
    print(f"{status} {name}")
    if details:
        print(f"   {details}")

# =============================================================================
# 1. 配置验证
# =============================================================================
def validate_configuration():
    print_header("1. 配置验证")
    
    from wechat_backend.config.config_validator import validate_config
    result = validate_config()
    result.print_report()
    
    return result.is_valid()

# =============================================================================
# 2. 后端服务健康检查
# =============================================================================
def check_backend_health():
    print_header("2. 后端服务健康检查")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result("健康检查端点", True, f"状态：{data.get('status')}")
            return True
        else:
            print_result("健康检查端点", False, f"状态码：{response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result("健康检查端点", False, "无法连接到后端服务")
        return False
    except Exception as e:
        print_result("健康检查端点", False, str(e))
        return False

# =============================================================================
# 3. AI 适配器状态检查
# =============================================================================
def check_adapter_status():
    print_header("3. AI 适配器状态检查")
    
    # 检查已注册的适配器
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    from config import Config
    
    registered = list(AIAdapterFactory._adapters.keys())
    print_result("适配器注册", True, f"已注册：{[pt.value for pt in registered]}")
    
    # 检查各平台 API Key 配置
    platforms = {
        'doubao': '豆包 AI',
        'deepseek': 'DeepSeek',
        'qwen': '通义千问',
        'chatgpt': 'ChatGPT',
        'gemini': 'Gemini',
        'zhipu': '智谱 AI',
        'wenxin': '文心一言'
    }
    
    all_passed = True
    for platform, name in platforms.items():
        api_key = Config.get_api_key(platform)
        if api_key:
            print_result(f"{name} API Key", True)
        else:
            print_result(f"{name} API Key", False, "未配置")
            # 至少有一个平台配置即可
            if platform == 'doubao':
                all_passed = False
    
    return all_passed

# =============================================================================
# 4. 豆包优先级模型检查
# =============================================================================
def check_doubao_priority_models():
    print_header("4. 豆包优先级模型检查")
    
    from config import Config
    
    priority_models = Config.get_doubao_priority_models()
    auto_select = Config.is_doubao_auto_select()
    
    print_result("自动选择模式", True, f"已{'启用' if auto_select else '禁用'}")
    
    if priority_models:
        print_result("优先级模型", True, f"配置了 {len(priority_models)} 个模型")
        for i, model in enumerate(priority_models[:5], 1):
            print(f"   {i}. {model}")
        if len(priority_models) > 5:
            print(f"   ... 还有 {len(priority_models) - 5} 个模型")
        return True
    else:
        default_model = os.environ.get('DOUBAO_MODEL_ID', '')
        if default_model:
            print_result("默认模型", True, default_model)
            return True
        else:
            print_result("豆包模型配置", False, "未配置优先级模型或默认模型")
            return False

# =============================================================================
# 5. 熔断器状态检查
# =============================================================================
def check_circuit_breaker_status():
    print_header("5. 熔断器状态检查")
    
    try:
        from wechat_backend.nxm_circuit_breaker import get_circuit_breaker
        cb = get_circuit_breaker()
        
        # 检查熔断器存储文件
        store_file = base_dir / 'circuit_breaker_store.json'
        if store_file.exists():
            with open(store_file, 'r') as f:
                store = json.load(f)
            print_result("熔断器状态持久化", True, f"存储文件：{store_file}")
            print(f"   已记录 {len(store)} 个熔断器状态")
        else:
            print_result("熔断器状态持久化", True, "无熔断记录（正常）")
        
        return True
    except Exception as e:
        print_result("熔断器状态检查", False, str(e))
        return False

# =============================================================================
# 6. 数据库健康检查
# =============================================================================
def check_database_health():
    print_header("6. 数据库健康检查")
    
    try:
        import sqlite3
        db_path = base_dir / 'database.db'
        
        if not db_path.exists():
            print_result("数据库文件", False, f"不存在：{db_path}")
            return False
        
        print_result("数据库文件", True, f"{db_path}")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表数量
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print_result("数据库表", True, f"共 {table_count} 个表")
        
        # 检查关键表
        critical_tables = ['users', 'test_records', 'brand_test_results', 'task_statuses', 'dimension_results']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in critical_tables:
            if table in tables:
                print_result(f"表：{table}", True)
            else:
                print_result(f"表：{table}", False, "缺失")
        
        conn.close()
        return True
    except Exception as e:
        print_result("数据库健康检查", False, str(e))
        return False

# =============================================================================
# 7. 日志系统检查
# =============================================================================
def check_logging_system():
    print_header("7. 日志系统检查")
    
    log_file = base_dir / 'logs' / 'app.log'
    
    if log_file.exists():
        print_result("日志文件", True, f"{log_file}")
        
        # 检查最近的日志
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if lines:
            print_result("日志记录", True, f"共 {len(lines)} 行日志")
            
            # 检查最近的错误
            recent_errors = [l for l in lines[-100:] if 'ERROR' in l or 'CRITICAL' in l]
            if recent_errors:
                print_result("最近错误", False, f"发现 {len(recent_errors)} 个错误（查看日志详情）")
            else:
                print_result("最近错误", True, "无严重错误")
        else:
            print_result("日志记录", False, "日志文件为空")
    else:
        print_result("日志文件", False, f"不存在：{log_file}")
    
    return True

# =============================================================================
# 8. 容错机制验证
# =============================================================================
def check_fault_tolerance():
    print_header("8. 容错机制验证")
    
    # 检查 FaultTolerantExecutor
    try:
        from wechat_backend.fault_tolerant_executor import FaultTolerantExecutor, ErrorType
        
        error_types = [et.name for et in ErrorType]
        print_result("容错执行器", True, f"支持错误类型：{', '.join(error_types)}")
        
        # 验证 QUOTA_EXHAUSTED 和 RATE_LIMIT_EXCEEDED 是否存在
        has_quota = 'QUOTA_EXHAUSTED' in error_types
        has_rate_limit = 'RATE_LIMIT_EXCEEDED' in error_types
        
        print_result("配额用尽错误类型", True if has_quota else False)
        print_result("频率限制错误类型", True if has_rate_limit else False)
        
        return has_quota and has_rate_limit
    except Exception as e:
        print_result("容错机制验证", False, str(e))
        return False

# =============================================================================
# 汇总报告
# =============================================================================
def generate_summary_report(results: dict):
    print_header("📊 系统验证汇总报告")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"\n总检查项：{total}")
    print(f"✅ 通过：{passed}")
    print(f"❌ 失败：{failed}")
    print(f"通过率：{passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    if failed == 0:
        print("\n🎉 所有检查项通过！系统已准备就绪。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个检查项失败，请检查日志了解详情。")
        return False

# =============================================================================
# 主函数
# =============================================================================
def main():
    print("\n" + "🚀" * 35)
    print("  品牌诊断系统 - 综合验证报告")
    print("  System Comprehensive Verification Report")
    print("🚀" * 35)
    
    results = {}
    
    # 1. 配置验证
    results['配置验证'] = validate_configuration()
    
    # 2. 后端服务健康检查
    results['后端服务'] = check_backend_health()
    
    # 3. AI 适配器状态
    results['AI 适配器'] = check_adapter_status()
    
    # 4. 豆包优先级模型
    results['豆包优先级'] = check_doubao_priority_models()
    
    # 5. 熔断器状态
    results['熔断器'] = check_circuit_breaker_status()
    
    # 6. 数据库健康
    results['数据库'] = check_database_health()
    
    # 7. 日志系统
    results['日志系统'] = check_logging_system()
    
    # 8. 容错机制
    results['容错机制'] = check_fault_tolerance()
    
    # 生成汇总报告
    success = generate_summary_report(results)
    
    # 返回退出码
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
