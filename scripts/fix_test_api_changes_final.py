#!/usr/bin/env python3
"""
修复测试文件中的 API 变更问题 - 精细版本

修复内容:
1. DiagnosisService(db_path=xxx, ai_adapter=xxx) -> DiagnosisService()
2. DiagnosisStateMachine(execution_id=xxx, db_path=xxx) -> DiagnosisStateMachine(execution_id=xxx)
3. DiagnosisRepository(xxx) -> DiagnosisRepository()
4. DiagnosisResultRepository(xxx) -> DiagnosisResultRepository()
5. APICallLogRepository(xxx) -> APICallLogRepository()
6. DeadLetterQueue(xxx) -> DeadLetterQueue()

作者：系统架构组
日期：2026-03-08
"""

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


def fix_file_content(content: str) -> str:
    """修复文件内容"""
    
    # 1. 修复 DiagnosisService 多行调用
    # 匹配：DiagnosisService(\n    db_path=xxx,\n    ai_adapter=xxx\n)
    pattern = r'DiagnosisService\(\s+db_path=[^,\n]+,\s+ai_adapter=[^\n]+\s+\)'
    content = re.sub(pattern, 'DiagnosisService()', content)
    
    # 2. 修复 DiagnosisService 单行调用 (带 db_path)
    pattern = r'DiagnosisService\(db_path=[^)]+\)'
    content = re.sub(pattern, 'DiagnosisService()', content)
    
    # 3. 修复 DiagnosisStateMachine 多行调用
    # 匹配：DiagnosisStateMachine(\n    execution_id=xxx,\n    db_path=xxx\n)
    pattern = r'DiagnosisStateMachine\(\s+execution_id=([^,\n]+),\s+db_path=[^\n]+\s+\)'
    content = re.sub(pattern, r'DiagnosisStateMachine(\n            execution_id=\1\n        )', content)
    
    # 4. 修复 DiagnosisStateMachine 单行调用
    pattern = r'DiagnosisStateMachine\(execution_id=([^,]+),\s*db_path=[^)]+\)'
    content = re.sub(pattern, r'DiagnosisStateMachine(execution_id=\1)', content)
    
    # 5. 修复 Repository 类构造函数 (单参数)
    for repo_class in ['DiagnosisRepository', 'DiagnosisResultRepository', 'APICallLogRepository']:
        # 匹配：RepositoryName(xxx) 其中 xxx 不是关键字参数
        pattern = rf'{repo_class}\((test_db_path|test_db|db_path)\)'
        content = re.sub(pattern, f'{repo_class}()', content)
    
    # 6. 修复 DeadLetterQueue 构造函数
    pattern = r'DeadLetterQueue\((test_db_path|test_db|db_path)\)'
    content = re.sub(pattern, 'DeadLetterQueue()', content)
    
    return content


def fix_file(file_path: Path) -> tuple[bool, str]:
    """修复单个文件"""
    if not file_path.exists():
        return False, f"❌ 文件不存在：{file_path}"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    fixed_content = fix_file_content(original_content)
    
    # 检查是否有变化
    if fixed_content == original_content:
        return True, f"ℹ️  {file_path.name}: 无需修复"
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    return True, f"✅ {file_path.name}: 修复完成"


def main():
    """主函数"""
    print("=" * 60)
    print("修复测试文件中的 API 变更问题")
    print("=" * 60)
    print()
    
    success_count = 0
    for file_rel_path in FILES_TO_FIX:
        file_path = PROJECT_ROOT / file_rel_path
        success, message = fix_file(file_path)
        print(message)
        if success:
            success_count += 1
    
    print()
    print("=" * 60)
    print(f"修复完成：{success_count}/{len(FILES_TO_FIX)} 个文件")
    print("=" * 60)


if __name__ == '__main__':
    main()
