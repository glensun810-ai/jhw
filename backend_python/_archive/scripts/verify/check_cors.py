#!/usr/bin/env python3
"""
检查CORS配置的脚本
"""

import sys
sys.path.insert(0, '/Users/sgl/PycharmProjects/PythonProject/backend_python')

from wechat_backend import app

print("=" * 60)
print("Flask App 配置检查")
print("=" * 60)

# 检查CORS配置
print("\n1. CORS配置:")
print(f"   - CORS扩展已加载: {hasattr(app, 'extensions') and 'cors' in app.extensions}")

# 检查路由
print("\n2. 已注册的路由:")
for rule in app.url_map.iter_rules():
    if 'api' in rule.rule:
        print(f"   - {rule.rule} [{','.join(rule.methods - {'OPTIONS', 'HEAD'})}]")

# 检查蓝图
print("\n3. 已注册的蓝图:")
for bp_name in app.blueprints:
    print(f"   - {bp_name}")

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
