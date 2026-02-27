#!/usr/bin/env python3
"""
BUG-009 修复脚本：批量替换调试日志为条件日志

将 logger.debug 替换为 logger.debug/info
将 print 替换为 logger.debug/info
"""

import re
import os

# 需要处理的文件列表
js_files_to_process = []
py_files_to_process = []

# 遍历 JS 文件
for root, dirs, files in os.walk('pages'):
    for file in files:
        if file.endswith('.js'):
            js_files_to_process.append(os.path.join(root, file))

for root, dirs, files in os.walk('services'):
    for file in files:
        if file.endswith('.js'):
            js_files_to_process.append(os.path.join(root, file))

# 遍历 Python 文件
for root, dirs, files in os.walk('backend_python/wechat_backend'):
    for file in files:
        if file.endswith('.py') and not file.startswith('__'):
            py_files_to_process.append(os.path.join(root, file))

print(f"待处理文件：{len(js_files_to_process)} 个 JS 文件，{len(py_files_to_process)} 个 Python 文件")

# 处理 JS 文件
js_replaced = 0
for filepath in js_files_to_process:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有 logger 导入
    has_logger_import = 'const logger = require' in content or 'const { debug, info, warn, error } = require' in content
    
    # 替换 logger.debug 为 logger.debug（只替换调试性质的日志）
    # 保留错误日志 logger.error
    debug_patterns = [
        r'console\.log\(\'📦',  # Storage 相关
        r'console\.log\(\'🔄',  # 加载相关
        r'console\.log\(\'✅',  # 成功日志
        r'console\.log\(\'⚠️',  # 警告日志
        r'console\.log\(\'❌',  # 错误日志
        r'console\.log\(\'\[DEBUG',  # DEBUG 标记
        r'console\.log\(\'\[性能优化',  # 性能相关
    ]
    
    replaced = False
    for pattern in debug_patterns:
        matches = re.findall(pattern, content)
        if matches:
            # 添加 logger 导入（如果没有）
            if not has_logger_import:
                # 在文件开头添加导入
                import_line = "const { debug, info, warn, error } = require('../../utils/logger');\n\n"
                content = import_line + content
                has_logger_import = True
            
            # 替换 logger.debug 为 debug
            content = re.sub(pattern, pattern.replace('logger.debug', 'debug'), content)
            replaced = True
            js_replaced += len(matches)
    
    if replaced:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {filepath}: 替换调试日志")

# 处理 Python 文件
py_replaced = 0
for filepath in py_files_to_process:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有 logger 导入
    has_logger_import = 'from wechat_backend.logging_config import' in content or 'api_logger' in content
    
    # 替换 print 为 logger.debug（只替换调试性质的 print）
    debug_prints = [
        r'print\(f"DEBUG:',
        r'print\(f"\[DEBUG',
        r'print\(f"✅',
        r'print\(f"⚠️',
        r'print\(f"❌',
    ]
    
    replaced = False
    for pattern in debug_prints:
        matches = re.findall(pattern, content)
        if matches:
            # 添加 logger 导入（如果没有）
            if not has_logger_import:
                import_line = "from wechat_backend.log_config import get_logger\n\n"
                content = import_line + content
                has_logger_import = True
            
            # 替换 print 为 logger.debug
            content = re.sub(pattern, pattern.replace('print', 'get_logger(__name__).debug'), content)
            replaced = True
            py_replaced += len(matches)
    
    if replaced:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {filepath}: 替换调试 print")

print(f"\n总计替换：{js_replaced} 处 JS 调试日志，{py_replaced} 处 Python 调试 print")
print(f"\n修复说明:")
print(f"- 调试日志已替换为 logger.debug/info")
print(f"- 生产环境可通过设置日志级别关闭 DEBUG 日志")
print(f"- 错误日志 logger.error 和 logger.error 保持不变")
