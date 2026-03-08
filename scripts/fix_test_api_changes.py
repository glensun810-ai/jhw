#!/usr/bin/env python3
"""
修复测试文件中的 API 变更问题

修复内容:
1. DiagnosisService 不再接受 db_path 参数
2. DiagnosisRepository 不再接受 db_path 参数
3. 使用全局数据库连接池

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


def fix_diagnosis_service_usage(content: str) -> str:
    """修复 DiagnosisService 的调用"""
    # 替换 DiagnosisService(db_path=xxx) 为 DiagnosisService()
    pattern = r'DiagnosisService\(db_path=[^)]+\)'
    replacement = 'DiagnosisService()'
    return re.sub(pattern, replacement, content)


def fix_diagnosis_repository_usage(content: str) -> str:
    """修复 DiagnosisRepository 的调用"""
    # 替换 DiagnosisRepository(xxx) 为 DiagnosisRepository()
    pattern = r'DiagnosisRepository\([^)]*\)'
    replacement = 'DiagnosisRepository()'
    return re.sub(pattern, replacement, content)


def fix_file(file_path: Path) -> bool:
    """修复单个文件"""
    if not file_path.exists():
        print(f"❌ 文件不存在：{file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # 应用修复
    fixed_content = fix_diagnosis_service_usage(original_content)
    fixed_content = fix_diagnosis_repository_usage(fixed_content)
    
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
