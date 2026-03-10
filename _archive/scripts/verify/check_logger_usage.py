#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志调用检查脚本

检查所有日志调用是否正确，避免 StructuredLogger 参数冲突问题
"""

import re
import sys
from pathlib import Path

def check_logger_usage():
    """检查日志调用是否正确"""
    errors = []
    warnings = []
    
    # 检查的文件范围
    check_paths = [
        Path('backend_python/wechat_backend/views'),
        Path('backend_python/wechat_backend/services'),
    ]
    
    for check_path in check_paths:
        if not check_path.exists():
            continue
            
        for py_file in check_path.rglob('*.py'):
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # 跳过注释
                if line.strip().startswith('#'):
                    continue
                
                # 检查是否有 .warning(.*,.*event_type 的调用
                if re.search(r'\.warning\([^)]*,[^)]*event_type\s*=', line):
                    errors.append(f"{py_file}:{line_num} - 发现可疑的 warning 调用：{line.strip()}")
                
                # 检查是否有 .error(.*,.*event_type 的调用
                if re.search(r'\.error\([^)]*,[^)]*event_type\s*=', line):
                    errors.append(f"{py_file}:{line_num} - 发现可疑的 error 调用：{line.strip()}")
                
                # 检查是否有 .info(.*,.*event_type 的调用
                if re.search(r'\.info\([^)]*,[^)]*event_type\s*=', line):
                    errors.append(f"{py_file}:{line_num} - 发现可疑的 info 调用：{line.strip()}")
                
                # 警告：使用 StructuredLogger 的地方
                if 'StructuredLogger' in line and 'import' not in line:
                    warnings.append(f"{py_file}:{line_num} - 使用 StructuredLogger: {line.strip()}")
    
    # 输出结果
    if errors:
        print("❌ 发现以下严重问题:")
        for error in errors:
            print(f"  {error}")
        print()
    
    if warnings:
        print("⚠️ 发现以下潜在问题:")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ 日志调用检查通过")
        return 0
    elif not errors:
        print("✅ 无严重问题，但有潜在风险")
        return 0
    else:
        print(f"❌ 共发现 {len(errors)} 个严重问题，{len(warnings)} 个潜在问题")
        return 1

if __name__ == '__main__':
    sys.exit(check_logger_usage())
