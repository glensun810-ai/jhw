#!/usr/bin/env python3
"""
测试修复后的模块导入问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_module_imports():
    """测试各个模块的导入"""
    print("🔍 测试模块导入...")
    
    modules_to_test = [
        "config",
        "wechat_backend.app",
        "wechat_backend.views",
        "wechat_backend.security.auth",
        "wechat_backend.database",
        "wechat_backend.ai_adapters.chatgpt_adapter",
        "wechat_backend.ai_adapters.deepseek_adapter",
        "wechat_backend.monitoring.metrics_collector",
        "wechat_backend.monitoring.alert_system",
        "wechat_backend.monitoring.logging_enhancements",
        "wechat_backend.security.input_validation",
        "wechat_backend.security.rate_limiting",
        "wechat_backend.network.request_wrapper",
        "wechat_backend.network.circuit_breaker",
        "wechat_backend.network.connection_pool",
        "wechat_backend.network.rate_limiter",
        "wechat_backend.network.retry_mechanism",
        "wechat_backend.network.security",
        "wechat_backend.monitoring.monitoring_decorator",
        "wechat_backend.monitoring.monitoring_config",
    ]
    
    failed_imports = []
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            failed_imports.append((module_name, str(e)))
        except Exception as e:
            print(f"⚠️  {module_name}: {e}")
            failed_imports.append((module_name, str(e)))
    
    if failed_imports:
        print(f"\n❌ 发现 {len(failed_imports)} 个导入失败:")
        for module, error in failed_imports:
            print(f"  - {module}: {error}")
        return False
    else:
        print(f"\n✅ 所有 {len(modules_to_test)} 个模块导入成功!")
        return True

def test_config_access():
    """测试配置访问"""
    print("\n🔍 测试配置访问...")
    
    try:
        from config import Config
        print(f"✅ Config module imported successfully")
        print(f"   SECRET_KEY exists: {'SECRET_KEY' in dir(Config)}")
        print(f"   WECHAT_APP_ID exists: {'WECHAT_APP_ID' in dir(Config)}")
        return True
    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Config access error: {e}")
        return False

def test_auth_module():
    """测试认证模块"""
    print("\n🔍 测试认证模块...")
    
    try:
        from wechat_backend.security.auth import jwt_manager, require_auth, authenticate_user
        print(f"✅ Auth module imported successfully")
        print(f"   jwt_manager available: {jwt_manager is not None}")
        print(f"   require_auth function: {callable(require_auth)}")
        print(f"   authenticate_user function: {callable(authenticate_user)}")
        return True
    except ImportError as e:
        print(f"❌ Auth module import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Auth module error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 开始测试修复后的模块导入问题")
    print("=" * 60)
    
    success = True
    success &= test_config_access()
    success &= test_auth_module()
    success &= test_module_imports()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 所有测试通过！模块导入问题已修复。")
    else:
        print("💥 部分测试失败，请检查上述错误。")
    
    sys.exit(0 if success else 1)