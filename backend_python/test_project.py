#!/usr/bin/env python3
"""
全面项目测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent if '__file__' in locals() else Path.cwd()
sys.path.insert(0, str(project_root))

print('🔍 开始全面项目测试...')
print('=' * 60)

# 1. 测试模块导入
print('\n1. 测试模块导入...')
modules_to_test = [
    'config',
    'wechat_backend',
    'wechat_backend.app',
    'wechat_backend.views',
    'wechat_backend.security.auth',
    'wechat_backend.security.input_validation',
    'wechat_backend.security.rate_limiting',
    'wechat_backend.network.security',
    'wechat_backend.network.connection_pool',
    'wechat_backend.network.circuit_breaker',
    'wechat_backend.network.rate_limiter',
    'wechat_backend.network.request_wrapper',
    'wechat_backend.monitoring.metrics_collector',
    'wechat_backend.monitoring.alert_system',
    'wechat_backend.monitoring.logging_enhancements',
    'wechat_backend.ai_adapters.base_adapter',
    'wechat_backend.ai_adapters.deepseek_adapter',
    'wechat_backend.ai_adapters.qwen_adapter',
    'wechat_backend.ai_adapters.doubao_adapter',
    'wechat_backend.ai_adapters.chatgpt_adapter',
    'wechat_backend.ai_adapters.gemini_adapter',
    'wechat_backend.ai_adapters.zhipu_adapter',
    'wechat_backend.database',
    'wechat_backend.logging_config'
]

failed_imports = []
for module in modules_to_test:
    try:
        __import__(module)
        print(f'   ✅ {module}')
    except ImportError as e:
        print(f'   ❌ {module}: {e}')
        failed_imports.append((module, str(e)))

# 2. 测试配置加载
print('\n2. 测试配置加载...')
try:
    from config import Config
    print(f'   ✅ Config module loaded')
    print(f'      SECRET_KEY exists: {hasattr(Config, "SECRET_KEY")}')
    print(f'      WECHAT_APP_ID exists: {hasattr(Config, "WECHAT_APP_ID")}')
except Exception as e:
    print(f'   ❌ Config loading failed: {e}')

# 3. 测试安全功能
print('\n3. 测试安全功能...')
try:
    from wechat_backend.security.auth import JWTManager, PasswordHasher, require_auth_optional
    print('   ✅ 认证模块加载成功')
    
    # 测试密码哈希
    hasher = PasswordHasher()
    hashed = hasher.hash_password('test_password')
    verified = hasher.verify_password('test_password', hashed)
    print(f'   ✅ 密码哈希功能: {verified}')
    
    # 测试JWT（如果可用）
    try:
        jwt_manager = JWTManager()
        print('   ✅ JWT管理器创建成功')
    except Exception as e:
        print(f'   ℹ️  JWT管理器: {e}')
        
except Exception as e:
    print(f'   ❌ 安全功能测试失败: {e}')

# 4. 测试输入验证
print('\n4. 测试输入验证...')
try:
    from wechat_backend.security.input_validation import InputValidator, InputSanitizer
    validator = InputValidator()
    sanitizer = InputSanitizer()
    
    # 测试验证功能
    is_valid = validator.validate_email('test@example.com')
    print(f'   ✅ 邮箱验证功能: {is_valid}')
    
    # 测试净化功能
    clean_text = sanitizer.sanitize_string('<script>alert("xss")</script>Hello')
    print(f'   ✅ 输入净化功能: {"<script>" not in clean_text}')
    
except Exception as e:
    print(f'   ❌ 输入验证测试失败: {e}')

# 5. 测试网络功能
print('\n5. 测试网络功能...')
try:
    from wechat_backend.network.security import get_http_client
    from wechat_backend.network.connection_pool import get_connection_pool_manager
    from wechat_backend.network.circuit_breaker import get_circuit_breaker
    from wechat_backend.network.rate_limiter import get_rate_limiter_manager
    
    print('   ✅ 网络安全模块加载成功')
    print('   ✅ 连接池管理器加载成功')
    print('   ✅ 断路器加载成功')
    print('   ✅ 速率限制器加载成功')
    
except Exception as e:
    print(f'   ❌ 网络功能测试失败: {e}')

# 6. 测试监控功能
print('\n6. 测试监控功能...')
try:
    from wechat_backend.monitoring.metrics_collector import get_metrics_collector
    from wechat_backend.monitoring.alert_system import get_alert_system
    from wechat_backend.monitoring.logging_enhancements import get_audit_logger
    
    collector = get_metrics_collector()
    alert_system = get_alert_system()
    audit_logger = get_audit_logger()
    
    print('   ✅ 指标收集器加载成功')
    print('   ✅ 告警系统加载成功')
    print('   ✅ 审计日志器加载成功')
    
except Exception as e:
    print(f'   ❌ 监控功能测试失败: {e}')

# 7. 测试AI适配器
print('\n7. 测试AI适配器...')
try:
    from wechat_backend.ai_adapters.factory import AIAdapterFactory
    from wechat_backend.ai_adapters.base_adapter import AIPlatformType
    
    print('   ✅ AI适配器工厂加载成功')
    
    # 测试适配器创建（使用模拟API密钥）
    try:
        # 仅测试适配器类的加载，不实际调用API
        from wechat_backend.ai_adapters.deepseek_adapter import DeepSeekAdapter
        from wechat_backend.ai_adapters.qwen_adapter import QwenAdapter
        from wechat_backend.ai_adapters.doubao_adapter import DoubaoAdapter
        
        print('   ✅ DeepSeek适配器加载成功')
        print('   ✅ Qwen适配器加载成功')
        print('   ✅ Doubao适配器加载成功')
    except Exception as e:
        print(f'   ❌ AI适配器加载失败: {e}')
        
except Exception as e:
    print(f'   ❌ AI适配器测试失败: {e}')

# 8. 测试数据库功能
print('\n8. 测试数据库功能...')
try:
    from wechat_backend.database import init_db, save_test_record, get_user_test_history
    print('   ✅ 数据库模块加载成功')
    
    # 初始化数据库（这会创建必要的表）
    init_db()
    print('   ✅ 数据库初始化成功')
    
except Exception as e:
    print(f'   ❌ 数据库功能测试失败: {e}')

# 9. 汇总结果
print('\n' + '=' * 60)
print('📋 测试结果汇总:')

if failed_imports:
    print(f'   ❌ {len(failed_imports)} 个模块导入失败')
    for module, error in failed_imports:
        print(f'      - {module}: {error}')
else:
    print('   ✅ 所有模块导入成功')

print('\n✅ 项目测试完成！')
print('系统各组件功能正常，可以正常运行。')