"""
临时表清理脚本

用途:
1. 识别并清理临时表
2. 清理过期缓存数据
3. 清理死信队列已处理记录
4. 优化数据库性能

执行方式:
    python scripts/cleanup_temp_tables.py

@author: 系统架构组
@date: 2026-02-27
@version: 2.0.0
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'backend_python' / 'wechat_backend' / 'database.db'


class TempTableCleaner:
    """临时表清理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化清理器
        
        参数:
            db_path: 数据库路径
        """
        self.db_path = db_path or DB_PATH
        self.stats = {
            'temp_tables_found': [],
            'temp_tables_dropped': 0,
            'cache_records_deleted': 0,
            'dead_letter_deleted': 0,
            'vacuum_performed': False,
            'errors': 0
        }
    
    def connect(self) -> sqlite3.Connection:
        """
        连接数据库
        
        返回:
            数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def find_temp_tables(self) -> List[str]:
        """
        查找临时表
        
        返回:
            临时表名称列表
        """
        print("正在查找临时表...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [row[0] for row in cursor.fetchall()]
            
            # 识别临时表（临时表通常包含 temp、tmp、_backup 等关键字）
            temp_keywords = ['temp', 'tmp', 'backup', '_bak', '_old', '_v1', '_v2']
            temp_tables = []
            
            for table in all_tables:
                table_lower = table.lower()
                if any(keyword in table_lower for keyword in temp_keywords):
                    # 排除正式的备份表
                    if 'migration' not in table_lower and 'history' not in table_lower:
                        temp_tables.append(table)
            
            self.stats['temp_tables_found'] = temp_tables
            
            print(f"找到临时表：{temp_tables}")
            return temp_tables
            
        except Exception as e:
            print(f"❌ 查找临时表失败：{e}")
            self.stats['errors'] += 1
            return []
            
        finally:
            conn.close()
    
    def drop_temp_tables(self, tables: List[str] = None) -> int:
        """
        删除临时表
        
        参数:
            tables: 表名列表（可选，不传则使用 find_temp_tables 的结果）
            
        返回:
            删除的表数
        """
        print("正在删除临时表...")
        
        if tables is None:
            tables = self.stats['temp_tables_found']
        
        if not tables:
            print("没有临时表需要删除")
            return 0
        
        conn = self.connect()
        cursor = conn.cursor()
        
        dropped_count = 0
        
        try:
            for table in tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    dropped_count += 1
                    print(f"✅ 删除临时表：{table}")
                except Exception as e:
                    print(f"❌ 删除临时表 {table} 失败：{e}")
                    self.stats['errors'] += 1
            
            self.stats['temp_tables_dropped'] = dropped_count
            conn.commit()
            
            print(f"✅ 删除临时表：{dropped_count} 个")
            return dropped_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 删除临时表失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def clean_expired_cache(self, days: int = 7) -> int:
        """
        清理过期缓存数据
        
        参数:
            days: 保留天数
            
        返回:
            删除的记录数
        """
        print(f"正在清理过期缓存数据（保留{days}天）...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 检查是否有 cache_entries 表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache_entries'")
            if not cursor.fetchone():
                print("缓存表不存在，跳过")
                return 0
            
            # 计算过期时间戳
            cutoff_timestamp = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            # 删除过期缓存
            cursor.execute('''
                DELETE FROM cache_entries
                WHERE created_at < ?
            ''', (cutoff_timestamp,))
            
            deleted_count = cursor.rowcount
            self.stats['cache_records_deleted'] = deleted_count
            
            conn.commit()
            
            print(f"✅ 清理过期缓存：{deleted_count} 条")
            return deleted_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 清理过期缓存失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def clean_processed_dead_letters(self, days: int = 30) -> int:
        """
        清理已处理的死信队列记录
        
        参数:
            days: 保留天数
            
        返回:
            删除的记录数
        """
        print(f"正在清理已处理的死信队列记录（保留{days}天）...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 检查是否有 dead_letter_queue 表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dead_letter_queue'")
            if not cursor.fetchone():
                print("死信队列不存在，跳过")
                return 0
            
            # 计算过期时间戳
            cutoff_timestamp = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            # 删除已处理且超过保留期的记录
            cursor.execute('''
                DELETE FROM dead_letter_queue
                WHERE status = 'processed'
                AND created_at < ?
            ''', (cutoff_timestamp,))
            
            deleted_count = cursor.rowcount
            self.stats['dead_letter_deleted'] = deleted_count
            
            conn.commit()
            
            print(f"✅ 清理死信队列：{deleted_count} 条")
            return deleted_count
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 清理死信队列失败：{e}")
            self.stats['errors'] += 1
            return 0
            
        finally:
            conn.close()
    
    def vacuum_database(self) -> bool:
        """
        执行数据库整理（VACUUM）
        
        返回:
            是否成功
        """
        print("正在执行数据库整理（VACUUM）...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("VACUUM")
            conn.commit()
            
            self.stats['vacuum_performed'] = True
            
            print("✅ 数据库整理完成")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 数据库整理失败：{e}")
            self.stats['errors'] += 1
            return False
            
        finally:
            conn.close()
    
    def analyze_database(self) -> bool:
        """
        分析数据库（ANALYZE）
        
        返回:
            是否成功
        """
        print("正在分析数据库（ANALYZE）...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("ANALYZE")
            conn.commit()
            
            print("✅ 数据库分析完成")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 数据库分析失败：{e}")
            self.stats['errors'] += 1
            return False
            
        finally:
            conn.close()
    
    def run_all_cleanup(self) -> Dict[str, Any]:
        """
        运行所有清理
        
        返回:
            清理统计信息
        """
        print("=" * 60)
        print("临时表清理脚本")
        print(f"数据库路径：{self.db_path}")
        print(f"开始时间：{datetime.now().isoformat()}")
        print("=" * 60)
        print()
        
        # 查找临时表
        temp_tables = self.find_temp_tables()
        
        # 询问是否删除（实际使用时应该人工确认）
        if temp_tables:
            print("\n⚠️  发现临时表，请人工确认后手动删除")
            # 实际删除需要人工确认，这里只报告
            # self.drop_temp_tables(temp_tables)
        
        # 清理过期缓存
        self.clean_expired_cache(days=7)
        
        # 清理死信队列
        self.clean_processed_dead_letters(days=30)
        
        # 数据库整理
        self.vacuum_database()
        
        # 数据库分析
        self.analyze_database()
        
        # 打印统计信息
        print()
        print("=" * 60)
        print("清理统计")
        print("=" * 60)
        print(f"找到临时表：{len(self.stats['temp_tables_found'])} 个")
        print(f"删除临时表：{self.stats['temp_tables_dropped']} 个")
        print(f"清理过期缓存：{self.stats['cache_records_deleted']} 条")
        print(f"清理死信队列：{self.stats['dead_letter_deleted']} 条")
        print(f"数据库整理：{'已完成' if self.stats['vacuum_performed'] else '未完成'}")
        print(f"错误数：{self.stats['errors']}")
        print("=" * 60)
        print()
        print(f"完成时间：{datetime.now().isoformat()}")
        
        return self.stats


def main():
    """主函数"""
    cleaner = TempTableCleaner()
    stats = cleaner.run_all_cleanup()
    
    # 如果有错误，返回非零退出码
    if stats['errors'] > 0:
        exit(1)


if __name__ == '__main__':
    main()
