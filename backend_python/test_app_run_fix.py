#!/usr/bin/env python3
"""
测试修复后的app.run()问题
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_app_import():
    """测试app模块导入"""
    print("🔍 测试app模块导入...")

    try:
        from wechat_backend import app
        print(f"✅ 成功导入app: {app}")
        print(f"✅ app类型: {type(app)}")

        # 检查app是否有run方法
        if hasattr(app, 'run'):
            print(f"✅ app有run方法: {callable(getattr(app, 'run'))}")
        else:
            print(f"❌ app没有run方法")
            return False

        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except AttributeError as e:
        print(f"❌ 属性错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_main_import():
    """测试main.py中的导入是否正常"""
    print("\n🔍 测试main.py中的导入...")

    try:
        # 模拟main.py中的导入
        from wechat_backend import app as imported_app
        print(f"✅ main.py风格导入成功: {imported_app}")

        # 检查是否可以访问run方法
        if hasattr(imported_app, 'run'):
            print(f"✅ 可以访问run方法: {callable(getattr(imported_app, 'run'))}")
            print("✅ 修复成功！app.run()方法现在可用")
            return True
        else:
            print("❌ 无法访问run方法")
            return False

    except Exception as e:
        print(f"❌ main.py风格导入失败: {e}")
        return False

def test_app_attributes():
    """测试app对象的关键属性"""
    print("\n🔍 测试app对象的关键属性...")

    try:
        from wechat_backend import app

        attributes_to_check = ['run', 'add_url_rule', 'route', 'before_request', 'after_request']
        missing_attrs = []

        for attr in attributes_to_check:
            if hasattr(app, attr):
                print(f"✅ {attr}: 可用")
            else:
                print(f"❌ {attr}: 缺失")
                missing_attrs.append(attr)

        if missing_attrs:
            print(f"❌ 缺失属性: {missing_attrs}")
            return False
        else:
            print("✅ 所有关键属性都存在")
            return True

    except Exception as e:
        print(f"❌ 测试app属性失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 开始测试app.run()修复")
    print("=" * 50)

    success = True
    success &= test_app_import()
    success &= test_main_import()
    success &= test_app_attributes()

    print("\n" + "=" * 50)
    if success:
        print("🎉 所有测试通过！app.run()问题已修复。")
    else:
        print("💥 部分测试失败，请检查上述错误。")

    sys.exit(0 if success else 1)