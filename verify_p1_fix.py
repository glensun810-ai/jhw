#!/usr/bin/env python3
"""
P1 修复验证脚本

验证内容：
1. 代码修改是否正确应用
2. 日志语句是否存在
3. 异常处理是否完善
"""

import sys
from pathlib import Path

# 设置路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'backend_python'))

def check_file_contains(filepath, patterns, description):
    """检查文件是否包含指定模式"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n检查：{description}")
        print(f"文件：{filepath}")
        
        all_found = True
        for pattern in patterns:
            if pattern in content:
                print(f"  ✅ 找到：{pattern[:60]}...")
            else:
                print(f"  ❌ 未找到：{pattern[:60]}...")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"  ❌ 读取文件失败：{e}")
        return False

def main():
    print("=" * 60)
    print("P1 修复验证脚本")
    print("=" * 60)
    
    # 检查 diagnosis_views.py
    diagnosis_views_path = project_root / 'backend_python' / 'wechat_backend' / 'views' / 'diagnosis_views.py'
    
    p1_patterns = [
        '[P1 数据持久化] 开始保存深度情报结果',
        '[P1 数据持久化] ✅ 深度情报结果已保存',
        '[P1 数据持久化] 开始保存品牌测试结果',
        '[P1 数据持久化] ✅ 品牌测试结果已保存',
        'import traceback',
        'error_details = traceback.format_exc()',
    ]
    
    p1_success = check_file_contains(
        diagnosis_views_path,
        p1_patterns,
        "P1 数据持久化日志和异常处理"
    )
    
    # 检查 websocket_route.py (P0 修复)
    websocket_route_path = project_root / 'backend_python' / 'wechat_backend' / 'websocket_route.py'
    
    p0_patterns = [
        'from wechat_backend.logging_config import api_logger, app_logger',
    ]
    
    p0_success = check_file_contains(
        websocket_route_path,
        p0_patterns,
        "P0 WebSocket 导入修复"
    )
    
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    if p0_success:
        print("✅ P0 WebSocket 修复：已应用")
    else:
        print("❌ P0 WebSocket 修复：未完全应用")
    
    if p1_success:
        print("✅ P1 数据持久化修复：已应用")
    else:
        print("❌ P1 数据持久化修复：未完全应用")
    
    if p0_success and p1_success:
        print("\n✅ 所有修复已成功应用！")
        print("\n下一步操作:")
        print("1. 重启后端服务")
        print("2. 执行一次品牌诊断任务")
        print("3. 检查日志中是否出现 '[P1 数据持久化]' 相关日志")
        print("4. 查询数据库验证 brand_test_results 表是否有记录")
        return 0
    else:
        print("\n❌ 部分修复未应用，请检查代码")
        return 1

if __name__ == '__main__':
    sys.exit(main())
