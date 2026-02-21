#!/usr/bin/env python3
"""
后端核心引擎导入验证脚本
验证 nxm_execution_engine.py 的所有导入是否正确
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))

def test_imports():
    """测试所有关键导入"""
    print("=" * 60)
    print("后端核心引擎导入验证")
    print("=" * 60)
    
    tests = [
        {
            'name': 'AIResponseLogger',
            'import': 'from wechat_backend.utils.ai_response_logger_v2 import AIResponseLogger',
            'check': lambda: True
        },
        {
            'name': 'log_ai_response',
            'import': 'from wechat_backend.utils.ai_response_logger_v2 import log_ai_response',
            'check': lambda: True
        },
        {
            'name': 'AIResponseLogger 实例化',
            'import': 'from wechat_backend.utils.ai_response_logger_v2 import AIResponseLogger; logger = AIResponseLogger()',
            'check': lambda: True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            exec(test['import'])
            if test['check']():
                print(f"✅ {test['name']}: 通过")
                passed += 1
            else:
                print(f"❌ {test['name']}: 检查失败")
                failed += 1
        except Exception as e:
            print(f"❌ {test['name']}: {str(e)}")
            failed += 1
    
    print("=" * 60)
    print(f"总计：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)
