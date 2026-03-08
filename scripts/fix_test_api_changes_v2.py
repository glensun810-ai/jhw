#!/usr/bin/env python3
"""
修复测试文件中的 API 变更问题 - 综合版本

修复内容:
1. DiagnosisService 不再接受 db_path 参数
2. DiagnosisStateMachine 不再接受 db_path 参数  
3. DiagnosisRepository 不再接受 db_path 参数
4. DiagnosisResultRepository 不再接受 db_path 参数
5. APICallLogRepository 不再接受 db_path 参数
6. DeadLetterQueue 不再接受 db_path 参数 (使用默认路径)

作者：系统架构组
日期：2026-03-08
"""

import os
import re
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 需要修复的文件
FILES_TO_FIX = [
    'tests/integration/test_diagnosis_flow.py',
    'tests/integration/test_data_persistence_integration.py',
    'tests/integration/test_data_consistency.py',
    'tests/integration/test_polling_integration.py',
    'tests/integration/test_report_stub_integration.py',
    'tests/integration/test_state_machine_integration.py',
    'tests/integration/test_concurrent_scenarios.py',
    'tests/integration/test_timeout_integration.py',
    'tests/integration/test_error_scenarios.py',
    'tests/integration/conftest.py',
]


def fix_multiline_constructor(content: str, class_name: str) -> str:
    """修复多行构造函数调用"""
    # 匹配多行构造函数调用
    pattern = rf'{class_name}\(\s*db_path=[^)]+\)'
    
    # 单行替换
    content = re.sub(pattern, f'{class_name}()', content, flags=re.MULTILINE | re.DOTALL)
    
    # 也处理简单的单行调用
    pattern2 = rf'{class_name}\(db_path=[^)]+\)'
    content = re.sub(pattern2, f'{class_name}()', content)
    
    return content


def fix_file(file_path: Path) -> bool:
    """修复单个文件"""
    if not file_path.exists():
        print(f"❌ 文件不存在：{file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    fixed_content = original_content
    
    # 修复各个类的构造函数
    classes_to_fix = [
        'DiagnosisService',
        'DiagnosisStateMachine',
        'DiagnosisRepository',
        'DiagnosisResultRepository',
        'APICallLogRepository',
        'DeadLetterQueue',
    ]
    
    for class_name in classes_to_fix:
        fixed_content = fix_multiline_constructor(fixed_content, class_name)
    
    # 检查是否有变化
    if fixed_content == original_content:
        print(f"ℹ️  {file_path.name}: 无需修复")
        return True
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"✅ {file_path.name}: 修复完成")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("修复测试文件中的 API 变更问题")
    print("=" * 60)
    
    success_count = 0
    for file_rel_path in FILES_TO_FIX:
        file_path = PROJECT_ROOT / file_rel_path
        if fix_file(file_path):
            success_count += 1
    
    print("=" * 60)
    print(f"修复完成：{success_count}/{len(FILES_TO_FIX)} 个文件")
    print("=" * 60)


if __name__ == '__main__':
    main()
