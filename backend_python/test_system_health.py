#!/usr/bin/env python3
"""
系统性 Bug 排查测试脚本
"""

import sys
import os

print('='*60)
print('系统性 Bug 排查测试')
print('='*60)

# 测试 1: 检查所有监控模块导入
print('\n【测试 1】监控模块导入')
try:
    from wechat_backend.monitoring.monitoring_config import initialize_monitoring
    print('✅ monitoring_config 导入成功')
except Exception as e:
    print(f'❌ monitoring_config 导入失败：{e}')

# 测试 2: 检查所有视图模块导入
print('\n【测试 2】视图模块导入')
view_modules = [
    'wechat_backend.views.diagnosis_views',
    'wechat_backend.views.admin_views',
    'wechat_backend.views.analytics_views',
    'wechat_backend.views.user_views',
]

for module in view_modules:
    try:
        __import__(module)
        print(f'✅ {module} 导入成功')
    except Exception as e:
        print(f'❌ {module} 导入失败：{str(e)[:50]}')

# 测试 3: 检查服务模块
print('\n【测试 3】服务模块导入')
service_modules = [
    'wechat_backend.services.quality_scorer',
    'wechat_backend.services.analytics_service',
    'wechat_backend.services.diagnosis_service',
]

for module in service_modules:
    try:
        __import__(module)
        print(f'✅ {module} 导入成功')
    except Exception as e:
        print(f'❌ {module} 导入失败：{str(e)[:50]}')

# 测试 4: 检查 AI 适配器
print('\n【测试 4】AI 适配器导入')
adapters = [
    'wechat_backend.ai_adapters.doubao_adapter',
    'wechat_backend.ai_adapters.deepseek_adapter',
    'wechat_backend.ai_adapters.qwen_adapter',
]

for adapter in adapters:
    try:
        __import__(adapter)
        print(f'✅ {adapter} 导入成功')
    except Exception as e:
        print(f'❌ {adapter} 导入失败：{str(e)[:50]}')

# 测试 5: 检查数据库模块
print('\n【测试 5】数据库模块导入')
db_modules = [
    'wechat_backend.database',
    'wechat_backend.database_repositories',
    'wechat_backend.models',
]

for module in db_modules:
    try:
        __import__(module)
        print(f'✅ {module} 导入成功')
    except Exception as e:
        print(f'❌ {module} 导入失败：{str(e)[:50]}')

# 测试 6: 检查安全模块
print('\n【测试 6】安全模块导入')
security_modules = [
    'wechat_backend.security.auth',
    'wechat_backend.security.input_validation',
    'wechat_backend.security.rate_limiting',
]

for module in security_modules:
    try:
        __import__(module)
        print(f'✅ {module} 导入成功')
    except Exception as e:
        print(f'❌ {module} 导入失败：{str(e)[:50]}')

print('\n' + '='*60)
print('测试完成')
print('='*60)
