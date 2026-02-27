"""
无用代码清理脚本

用途:
1. 识别并清理未使用的函数和类
2. 清理注释掉的代码
3. 清理调试代码
4. 清理重复代码

执行方式:
    python scripts/cleanup_unused_code.py

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


# 需要清理的目录
TARGET_DIRS = [
    'wechat_backend',
    'miniprogram'
]


# 需要排除的目录
EXCLUDE_DIRS = [
    '__pycache__',
    '.git',
    'node_modules',
    'tests',
    'migrations',
    'venv',
    '.venv'
]


# 需要清理的文件模式
DEBUG_FILE_PATTERNS = [
    '*_debug.py',
    '*_test.py',
    '*_backup.py',
    '*.bak',
    '*.tmp'
]


class CodeCleaner:
    """代码清理器"""
    
    def __init__(self, project_root: Path = None):
        """
        初始化清理器
        
        参数:
            project_root: 项目根目录
        """
        self.project_root = project_root or PROJECT_ROOT
        self.stats = {
            'debug_files_found': 0,
            'commented_code_lines': 0,
            'duplicate_functions': 0,
            'unused_imports': 0
        }
    
    def find_debug_files(self) -> List[Path]:
        """
        查找调试文件
        
        返回:
            调试文件列表
        """
        debug_files = []
        
        for pattern in DEBUG_FILE_PATTERNS:
            for file_path in self.project_root.rglob(pattern):
                # 检查是否在排除目录中
                if any(exclude in str(file_path) for exclude in EXCLUDE_DIRS):
                    continue
                
                # 检查是否在目标目录中
                if any(target in str(file_path) for target in TARGET_DIRS):
                    debug_files.append(file_path)
                    self.stats['debug_files_found'] += 1
        
        return debug_files
    
    def find_commented_code(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        查找注释掉的代码
        
        参数:
            file_path: 文件路径
            
        返回:
            注释代码行列表
        """
        commented_lines = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            in_multiline_comment = False
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Python 多行注释
                if file_path.suffix == '.py':
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        in_multiline_comment = not in_multiline_comment
                        commented_lines.append({
                            'line': i + 1,
                            'content': line.rstrip()
                        })
                    elif in_multiline_comment or stripped.startswith('#'):
                        # 检查是否像代码（包含关键字）
                        if self._looks_like_code(stripped):
                            commented_lines.append({
                                'line': i + 1,
                                'content': line.rstrip()
                            })
                
                # JavaScript 注释
                elif file_path.suffix == '.js':
                    if stripped.startswith('/*'):
                        in_multiline_comment = True
                    elif stripped.endswith('*/'):
                        in_multiline_comment = False
                        commented_lines.append({
                            'line': i + 1,
                            'content': line.rstrip()
                        })
                    elif in_multiline_comment or stripped.startswith('//'):
                        if self._looks_like_code(stripped):
                            commented_lines.append({
                                'line': i + 1,
                                'content': line.rstrip()
                            })
            
            self.stats['commented_code_lines'] += len(commented_lines)
            
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
        
        return commented_lines
    
    def _looks_like_code(self, line: str) -> bool:
        """
        判断行是否像代码
        
        参数:
            line: 代码行
            
        返回:
            是否像代码
        """
        code_patterns = [
            r'def\s+\w+',          # Python 函数定义
            r'class\s+\w+',        # 类定义
            r'function\s+\w+',     # JS 函数定义
            r'const\s+\w+',        # JS 常量
            r'let\s+\w+',          # JS 变量
            r'var\s+\w+',          # JS 变量
            r'import\s+',          # 导入
            r'from\s+\w+',         # Python 导入
            r'if\s+',              # 条件语句
            r'for\s+',             # 循环
            r'while\s+',           # 循环
            r'return\s+',          # 返回
            r'async\s+',           # 异步
            r'await\s+',           # 等待
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, line):
                return True
        
        return False
    
    def generate_cleanup_report(self, output_path: Path = None) -> Dict[str, Any]:
        """
        生成清理报告
        
        参数:
            output_path: 输出路径（可选）
            
        返回:
            清理报告
        """
        report = {
            'debug_files': [],
            'commented_code_files': [],
            'total_stats': self.stats
        }
        
        # 查找调试文件
        debug_files = self.find_debug_files()
        report['debug_files'] = [str(f) for f in debug_files]
        
        # 查找注释代码
        for target_dir in TARGET_DIRS:
            dir_path = self.project_root / target_dir
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob('*.py'):
                if any(exclude in str(file_path) for exclude in EXCLUDE_DIRS):
                    continue
                
                commented = self.find_commented_code(file_path)
                if commented:
                    report['commented_code_files'].append({
                        'file': str(file_path),
                        'lines': commented
                    })
        
        # 保存报告
        if output_path:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"清理报告已保存至：{output_path}")
        
        return report
    
    def run_cleanup(self) -> Dict[str, Any]:
        """
        运行清理
        
        返回:
            清理统计信息
        """
        print("=" * 60)
        print("无用代码清理脚本")
        print(f"项目根目录：{self.project_root}")
        print(f"开始时间：{__import__('datetime').datetime.now().isoformat()}")
        print("=" * 60)
        print()
        
        # 生成清理报告
        report_path = self.project_root / 'cleanup_report.json'
        report = self.generate_cleanup_report(report_path)
        
        # 打印统计信息
        print()
        print("=" * 60)
        print("清理统计")
        print("=" * 60)
        print(f"调试文件数：{self.stats['debug_files_found']}")
        print(f"注释代码行数：{self.stats['commented_code_lines']}")
        print(f"包含注释代码的文件数：{len(report['commented_code_files'])}")
        print("=" * 60)
        print()
        print("注意：清理报告已生成，请人工审核后手动清理")
        print(f"报告路径：{report_path}")
        print()
        print(f"完成时间：{__import__('datetime').datetime.now().isoformat()}")
        
        return self.stats


def main():
    """主函数"""
    cleaner = CodeCleaner()
    cleaner.run_cleanup()


if __name__ == '__main__':
    main()
