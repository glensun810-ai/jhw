#!/usr/bin/env python3
"""
P2-3 无用代码清理脚本

用途:
1. 清理废弃的数据库表 (test_records, old_brand_results 等)
2. 清理无用的调试文件
3. 清理注释掉的代码块
4. 生成清理报告

执行方式:
    python scripts/cleanup_deprecated_code.py

@author: 系统架构组
@date: 2026-02-28
@version: 2.0.0
"""

import sqlite3
import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 添加项目路径
backend_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'backend_python'
)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from wechat_backend.logging_config import api_logger

# 数据库路径
DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'backend_python',
    'database.db'
)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class DeprecatedCodeCleaner:
    """无用代码清理器"""

    def __init__(self, db_path: str = DATABASE_PATH):
        """
        初始化清理器

        参数:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.stats = {
            'deprecated_tables_dropped': 0,
            'debug_files_removed': 0,
            'commented_code_files_cleaned': 0,
            'total_freed_bytes': 0,
            'errors': 0
        }
        self.report = {
            'deprecated_tables': [],
            'debug_files': [],
            'commented_code_files': [],
            'actions_taken': []
        }

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def find_deprecated_tables(self) -> List[str]:
        """
        查找废弃的数据库表

        返回:
            废弃表名称列表
        """
        api_logger.info("[P2-3] 开始查找废弃的数据库表...")

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [row[0] for row in cursor.fetchall()]

            # 定义废弃表模式
            deprecated_patterns = [
                r'^test_records$',           # 旧的品牌测试记录表
                r'^old_brand_results$',      # 旧的品牌结果表
                r'^test_record$',            # 单数形式
                r'^brand_result$',           # 旧的品牌结果表
                r'^temp_.*$',                # 临时表
                r'^bak_.*$',                 # 备份表
                r'^.*_backup$',              # 备份表
                r'^.*_old$',                 # 旧表
                r'^.*_v1$',                  # 版本 1 表
                r'^.*_v2$',                  # 版本 2 表
            ]

            deprecated_tables = []
            for table in all_tables:
                # 跳过正式的表
                if table in [
                    'diagnosis_reports',
                    'diagnosis_results',
                    'diagnosis_analysis',
                    'task_statuses',
                    'deep_intelligence_results',
                    'brand_test_results',
                    'users',
                    'ai_call_logs',
                    'circuit_breaker_states',
                    'audit_logs',
                    'sqlite_sequence',
                    'cache_entries',
                    'dead_letter_queue'
                ]:
                    continue

                # 检查是否匹配废弃模式
                for pattern in deprecated_patterns:
                    if re.match(pattern, table, re.IGNORECASE):
                        deprecated_tables.append(table)
                        api_logger.info(f"[P2-3] 发现废弃表：{table}")
                        break

            self.report['deprecated_tables'] = deprecated_tables
            api_logger.info(f"[P2-3] 共发现 {len(deprecated_tables)} 个废弃表")

            return deprecated_tables

        except Exception as e:
            api_logger.error(f"[P2-3] 查找废弃表失败：{e}")
            self.stats['errors'] += 1
            return []
        finally:
            conn.close()

    def drop_deprecated_tables(self, tables: List[str] = None, dry_run: bool = True) -> int:
        """
        删除废弃的数据库表

        参数:
            tables: 表名列表（可选，不传则使用 find_deprecated_tables 的结果）
            dry_run: 是否仅模拟执行（不实际删除）

        返回:
            删除的表数
        """
        api_logger.info(f"[P2-3] 开始删除废弃的数据库表{'(模拟)' if dry_run else '...'}")

        if tables is None:
            tables = self.find_deprecated_tables()

        if not tables:
            api_logger.info("[P2-3] 没有废弃表需要删除")
            return 0

        conn = self.get_connection()
        cursor = conn.cursor()

        dropped_count = 0

        try:
            for table in tables:
                try:
                    if dry_run:
                        api_logger.info(f"[P2-3] [DRY RUN] 将删除废弃表：{table}")
                        dropped_count += 1
                    else:
                        # 先删除相关索引
                        cursor.execute(
                            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
                            (table,)
                        )
                        indexes = [row[0] for row in cursor.fetchall()]
                        for index in indexes:
                            cursor.execute(f"DROP INDEX IF EXISTS {index}")

                        # 删除表
                        cursor.execute(f"DROP TABLE IF EXISTS {table}")
                        dropped_count += 1
                        api_logger.info(f"[P2-3] ✅ 删除废弃表：{table}")

                        self.report['actions_taken'].append(f"Deleted table: {table}")

                except Exception as e:
                    api_logger.error(f"[P2-3] 删除表 {table} 失败：{e}")
                    self.stats['errors'] += 1

            if not dry_run:
                conn.commit()
                self.stats['deprecated_tables_dropped'] = dropped_count

            api_logger.info(f"[P2-3] {'✅ 模拟' if dry_run else '完成'}删除废弃表：{dropped_count} 个")
            return dropped_count

        except Exception as e:
            conn.rollback()
            api_logger.error(f"[P2-3] 删除废弃表失败：{e}")
            self.stats['errors'] += 1
            return 0
        finally:
            conn.close()

    def find_debug_files(self) -> List[Path]:
        """
        查找调试文件

        返回:
            调试文件列表
        """
        api_logger.info("[P2-3] 开始查找调试文件...")

        debug_patterns = [
            '*_debug.py',
            '*_debug_*.py',
            'debug_*.py',
            '*_test_simple.py',
            '*_simple_test.py',
            '*_backup.py',
            '*_bak.py',
            '*.bak',
            '*.tmp',
        ]

        debug_files = []
        backend_dir = Path(backend_path)

        for pattern in debug_patterns:
            for file_path in backend_dir.rglob(pattern):
                # 排除 tests 目录下的测试文件（这是正常的测试代码）
                if 'tests' in str(file_path.parts):
                    continue

                # 排除 migrations 目录
                if 'migrations' in str(file_path.parts):
                    continue

                # 排除 qwen-code 目录（第三方代码）
                if 'qwen-code' in str(file_path.parts):
                    continue

                # 排除 gco_validator 目录（独立模块）
                if 'gco_validator' in str(file_path.parts):
                    continue

                debug_files.append(file_path)
                api_logger.debug(f"[P2-3] 发现调试文件：{file_path}")

        self.report['debug_files'] = [str(f) for f in debug_files]
        api_logger.info(f"[P2-3] 共发现 {len(debug_files)} 个调试文件")

        return debug_files

    def find_commented_code_files(self) -> List[Tuple[Path, int]]:
        """
        查找包含大段注释代码的文件

        返回:
            (文件路径，注释代码行数) 列表
        """
        api_logger.info("[P2-3] 开始查找包含大段注释代码的文件...")

        commented_files = []
        backend_dir = Path(backend_path)

        # 只扫描 Python 文件
        for file_path in backend_dir.rglob('*.py'):
            # 排除 tests、migrations、qwen-code、gco_validator 目录
            if any(exclude in str(file_path.parts) for exclude in ['tests', 'migrations', 'qwen-code', 'gco_validator']):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                commented_code_lines = 0
                in_multiline_comment = False

                for line in lines:
                    stripped = line.strip()

                    # 检查多行注释
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        # 单行多行注释
                        if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                            continue
                        in_multiline_comment = not in_multiline_comment
                        commented_code_lines += 1
                    elif in_multiline_comment:
                        commented_code_lines += 1
                        if stripped.endswith('"""') or stripped.endswith("'''"):
                            in_multiline_comment = False
                    elif stripped.startswith('#') and len(stripped) > 1:
                        # 检查是否像代码（包含关键字）
                        if self._looks_like_code(stripped[1:].strip()):
                            commented_code_lines += 1

                # 如果注释代码超过 10 行，报告
                if commented_code_lines > 10:
                    commented_files.append((file_path, commented_code_lines))
                    api_logger.debug(f"[P2-3] {file_path}: {commented_code_lines} 行注释代码")

            except Exception as e:
                api_logger.debug(f"读取文件失败 {file_path}: {e}")

        self.report['commented_code_files'] = [
            {'file': str(f), 'lines': c} for f, c in commented_files
        ]
        api_logger.info(f"[P2-3] 共发现 {len(commented_files)} 个文件包含大段注释代码")

        return commented_files

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
            r'async\s+def\s+\w+',  # 异步函数定义
            r'if\s+.+:',           # 条件语句
            r'for\s+.+:',          # 循环
            r'while\s+.+:',        # 循环
            r'return\s+',          # 返回
            r'raise\s+',           # 抛出异常
            r'import\s+',          # 导入
            r'from\s+\w+.*import', # Python 导入
            r'with\s+.+:',         # 上下文管理器
            r'try:',               # 异常处理
            r'except',             # 异常处理
            r'@\w+',               # 装饰器
        ]

        for pattern in code_patterns:
            if re.search(pattern, line):
                return True

        return False

    def get_database_size(self) -> int:
        """获取数据库文件大小（字节）"""
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0

    def run_cleanup(self, dry_run: bool = True, remove_debug_files: bool = False) -> Dict[str, Any]:
        """
        运行清理

        参数:
            dry_run: 是否仅模拟执行
            remove_debug_files: 是否删除调试文件

        返回:
            清理统计信息
        """
        api_logger.info("=" * 60)
        api_logger.info("[P2-3] 开始无用代码清理")
        if dry_run:
            api_logger.info("[P2-3] 模式：模拟执行 (dry-run)")
        api_logger.info("=" * 60)

        # 记录清理前数据库大小
        size_before = self.get_database_size()
        api_logger.info(f"[P2-3] 清理前数据库大小：{size_before / 1024 / 1024:.2f} MB")

        # 步骤 1: 查找并删除废弃表
        deprecated_tables = self.find_deprecated_tables()
        if deprecated_tables:
            self.drop_deprecated_tables(deprecated_tables, dry_run=dry_run)

        # 步骤 2: 查找调试文件
        debug_files = self.find_debug_files()

        # 步骤 3: 查找注释代码
        commented_files = self.find_commented_code_files()

        # 记录清理后数据库大小
        size_after = self.get_database_size()
        freed_bytes = size_before - size_after
        self.stats['total_freed_bytes'] = freed_bytes

        # 生成清理报告
        report_path = PROJECT_ROOT / 'cleanup_p2_3_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        api_logger.info(f"[P2-3] 清理报告已保存至：{report_path}")

        # 打印统计信息
        api_logger.info("=" * 60)
        api_logger.info("[P2-3] 清理统计")
        api_logger.info("=" * 60)
        api_logger.info(f"废弃表数量：{len(deprecated_tables)}")
        api_logger.info(f"调试文件数：{len(debug_files)}")
        api_logger.info(f"包含注释代码的文件数：{len(commented_files)}")
        if freed_bytes > 0:
            api_logger.info(f"释放空间：{freed_bytes / 1024 / 1024:.2f} MB")
        api_logger.info(f"错误数：{self.stats['errors']}")
        api_logger.info("=" * 60)

        return self.stats

    def print_summary(self):
        """打印清理摘要"""
        print("\n" + "=" * 60)
        print("P2-3 无用代码清理摘要")
        print("=" * 60)
        print()

        if self.report['deprecated_tables']:
            print("📦 废弃数据库表:")
            for table in self.report['deprecated_tables']:
                print(f"   - {table}")
            print()

        if self.report['debug_files']:
            print("🔧 调试文件:")
            for file in self.report['debug_files'][:10]:  # 只显示前 10 个
                print(f"   - {file}")
            if len(self.report['debug_files']) > 10:
                print(f"   ... 还有 {len(self.report['debug_files']) - 10} 个文件")
            print()

        if self.report['commented_code_files']:
            print("📝 包含大段注释代码的文件:")
            for item in self.report['commented_code_files'][:5]:  # 只显示前 5 个
                print(f"   - {item['file']} ({item['lines']} 行)")
            if len(self.report['commented_code_files']) > 5:
                print(f"   ... 还有 {len(self.report['commented_code_files']) - 5} 个文件")
            print()

        print("=" * 60)
        print("详细报告已保存至：cleanup_p2_3_report.json")
        print("=" * 60)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("P2-3 无用代码清理工具")
    print("=" * 60)
    print()

    # 创建清理器
    cleaner = DeprecatedCodeCleaner()

    # 执行清理（模拟模式）
    print("执行模拟清理...")
    stats = cleaner.run_cleanup(dry_run=True, remove_debug_files=False)

    # 打印摘要
    cleaner.print_summary()

    # 直接执行实际清理（仅删除废弃表）
    print()
    print("执行实际清理（仅删除废弃数据库表）...")
    stats = cleaner.run_cleanup(dry_run=False, remove_debug_files=False)

    print()
    print("=" * 60)
    print("P2-3 清理完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
