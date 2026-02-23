#!/usr/bin/env python3
"""
修复视图模块的蓝图导入问题

问题：所有视图模块都创建了自己的 wechat_bp 蓝图实例
修复：所有模块应该从 views/__init__.py 导入共享的 wechat_bp
"""

import os
import re

VIEWS_DIR = os.path.dirname(os.path.abspath(__file__))
VIEW_FILES = [
    'diagnosis_views.py',
    'user_views.py',
    'report_views.py',
    'admin_views.py',
    'analytics_views.py',
    'audit_views.py',
    'sync_views.py',
]

def fix_view_file(filepath):
    """修复单个视图文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经修复
    if 'from . import wechat_bp' in content:
        print(f"✓ {os.path.basename(filepath)} 已修复")
        return False
    
    # 替换 Flask 导入（移除 Blueprint）
    content = re.sub(
        r'from flask import Blueprint,',
        'from flask import',
        content
    )
    
    # 替换蓝图创建
    old_blueprint = "# Create a blueprint\nwechat_bp = Blueprint('wechat', __name__)"
    new_import = "# 从主模块导入蓝图（修复 P0-3: 确保路由注册到正确的蓝图）\nfrom . import wechat_bp"
    
    if old_blueprint in content:
        content = content.replace(old_blueprint, new_import)
        print(f"✓ {os.path.basename(filepath)} 修复完成")
    elif "wechat_bp = Blueprint('wechat', __name__)" in content:
        # 处理其他格式的蓝图创建
        content = re.sub(
            r"#.*blueprint.*\nwechat_bp = Blueprint\('wechat', __name__\)",
            new_import,
            content
        )
        print(f"✓ {os.path.basename(filepath)} 修复完成（正则）")
    else:
        print(f"⚠ {os.path.basename(filepath)} 未找到蓝图创建语句")
        return False
    
    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    print("修复视图模块的蓝图导入问题...\n")
    
    fixed_count = 0
    for filename in VIEW_FILES:
        filepath = os.path.join(VIEWS_DIR, filename)
        if os.path.exists(filepath):
            if fix_view_file(filepath):
                fixed_count += 1
        else:
            print(f"✗ {filename} 不存在")
    
    print(f"\n修复完成：{fixed_count}/{len(VIEW_FILES)} 个文件")

if __name__ == '__main__':
    main()
