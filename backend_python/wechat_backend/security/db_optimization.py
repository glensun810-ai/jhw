"""
数据库优化模块 (Database Optimization Module)

P2 性能优化功能:
1. P2-10: 复合索引 (在 phase3_database_schema.sql 中实现)
2. P2-11: 查询缓存
3. P2-12: 数据库备份
4. P2-13: 容量监控

使用示例:
    # 查询缓存
    cache = QueryCache(max_size=100, ttl=300)
    result = cache.get_or_set('key', lambda: expensive_query())
    
    # 数据库备份
    backup = DatabaseBackup(db_path='data/brand_test.db')
    backup.create_backup()
    
    # 容量监控
    monitor = CapacityMonitor(db_path='data/brand_test.db')
    stats = monitor.get_database_stats()
"""

import os
import json
import time
import shutil
import sqlite3
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# P2-11: 查询缓存
# =============================================================================

class CacheEntry:
    """缓存条目"""
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl  # 生存时间 (秒)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl


class QueryCache:
    """
    P2-11: 查询缓存
    
    功能:
    1. LRU 缓存淘汰
    2. TTL 过期
    3. 线程安全
    4. 缓存统计
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        初始化查询缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认 TTL (秒)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'expirations': 0,
        }
    
    def _generate_key(self, query: str, params: tuple = None) -> str:
        """生成缓存键"""
        key_material = f"{query}:{json.dumps(params, sort_keys=True) if params else ''}"
        return hashlib.md5(key_material.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None
            
            # 移动到末尾 (LRU)
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间 (秒)
        """
        if ttl is None:
            ttl = self._default_ttl
        
        with self._lock:
            # 如果已存在，删除旧条目
            if key in self._cache:
                del self._cache[key]
            
            # 如果缓存已满，删除最旧的条目
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._stats['evictions'] += 1
            
            # 添加新条目
            self._cache[key] = CacheEntry(value, ttl)
            self._stats['sets'] += 1
    
    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int = None) -> Any:
        """
        获取或设置缓存
        
        Args:
            key: 缓存键
            factory: 创建值的工厂函数
            ttl: 生存时间 (秒)
            
        Returns:
            缓存值或新创建的值
        """
        value = self.get(key)
        if value is not None:
            return value
        
        # 创建新值
        value = factory()
        self.set(key, value, ttl)
        return value
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (
                self._stats['hits'] / total_requests * 100
                if total_requests > 0 else 0
            )
            
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'sets': self._stats['sets'],
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
                'hit_rate_percent': round(hit_rate, 2),
            }


# 全局查询缓存实例
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """获取全局查询缓存实例"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


# =============================================================================
# P2-12: 数据库备份
# =============================================================================

class DatabaseBackup:
    """
    P2-12: 数据库备份
    
    功能:
    1. 自动备份
    2. 备份验证
    3. 备份清理
    4. 备份恢复
    """
    
    def __init__(
        self,
        db_path: str,
        backup_dir: str = 'data/backups',
        max_backups: int = 7
    ):
        """
        初始化数据库备份
        
        Args:
            db_path: 数据库文件路径
            backup_dir: 备份目录
            max_backups: 最大备份数量
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self._lock = threading.Lock()
        
        # 确保备份目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, suffix: str = None) -> str:
        """
        创建数据库备份
        
        Args:
            suffix: 备份文件后缀 (默认使用时间戳)
            
        Returns:
            备份文件路径
        """
        with self._lock:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found: {self.db_path}")
            
            # 生成备份文件名
            if suffix is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                suffix = f"_{timestamp}"
            
            backup_filename = f"{self.db_path.stem}{suffix}{self.db_path.suffix}"
            backup_path = self.backup_dir / backup_filename
            
            # 复制文件
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Created database backup: {backup_path}")
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return str(backup_path)
    
    def _cleanup_old_backups(self) -> int:
        """清理旧备份"""
        backups = self._list_backups()
        
        if len(backups) <= self.max_backups:
            return 0
        
        # 删除最旧的备份
        to_delete = backups[self.max_backups:]
        for backup_path in to_delete:
            try:
                backup_path.unlink()
                logger.info(f"Deleted old backup: {backup_path}")
            except Exception as e:
                logger.error(f"Failed to delete backup {backup_path}: {e}")
        
        return len(to_delete)
    
    def _list_backups(self) -> List[Path]:
        """列出所有备份 (按时间排序)"""
        if not self.backup_dir.exists():
            return []
        
        backups = [
            f for f in self.backup_dir.glob(f"{self.db_path.stem}*.db")
            if f.is_file()
        ]
        
        # 按修改时间排序
        backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        return backups
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        列出所有备份信息
        
        Returns:
            备份信息列表
        """
        backups = self._list_backups()
        
        result = []
        for backup_path in backups:
            stat = backup_path.stat()
            result.append({
                'path': str(backup_path),
                'filename': backup_path.name,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        return result
    
    def restore_backup(self, backup_path: str) -> str:
        """
        恢复备份
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            恢复后的数据库路径
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        
        with self._lock:
            # 备份当前数据库
            if self.db_path.exists():
                self.create_backup('_before_restore')
            
            # 恢复备份
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"Restored database from backup: {backup_path}")
            
            return str(self.db_path)
    
    def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        验证备份
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            验证结果
        """
        backup_path = Path(backup_path)
        
        result = {
            'exists': backup_path.exists(),
            'valid': False,
            'size_bytes': 0,
            'tables': [],
            'errors': [],
        }
        
        if not result['exists']:
            result['errors'].append(f"Backup file not found: {backup_path}")
            return result
        
        result['size_bytes'] = backup_path.stat().st_size
        
        # 验证数据库完整性
        try:
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            
            # 检查数据库完整性
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()
            
            if integrity_result and integrity_result[0] == 'ok':
                result['valid'] = True
            else:
                result['errors'].append(f"Integrity check failed: {integrity_result}")
            
            # 获取表列表
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            result['tables'] = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
        except Exception as e:
            result['errors'].append(str(e))
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取备份统计"""
        backups = self._list_backups()
        total_size = sum(f.stat().st_size for f in backups)
        
        return {
            'total_backups': len(backups),
            'max_backups': self.max_backups,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'backup_dir': str(self.backup_dir),
            'latest_backup': (
                backups[0].name if backups else None
            ),
        }


# =============================================================================
# P2-13: 容量监控
# =============================================================================

class CapacityMonitor:
    """
    P2-13: 容量监控
    
    功能:
    1. 数据库大小监控
    2. 表大小分析
    3. 记录数统计
    4. 增长趋势
    5. 容量预警
    """
    
    # 容量阈值 (MB)
    SIZE_WARNING_THRESHOLD = 50
    SIZE_CRITICAL_THRESHOLD = 100
    
    def __init__(self, db_path: str):
        """
        初始化容量监控
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self._history: List[Dict[str, Any]] = []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        if not self.db_path.exists():
            return {'error': 'Database not found'}
        
        stat = self.db_path.stat()
        
        stats = {
            'path': str(self.db_path),
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / 1024 / 1024, 2),
            'size_status': self._get_size_status(stat.st_size),
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'tables': {},
            'total_records': 0,
            'warnings': [],
        }
        
        # 获取表信息
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                table_stats = self._get_table_stats(cursor, table)
                stats['tables'][table] = table_stats
                stats['total_records'] += table_stats['row_count']
            
            # 检查容量警告
            if stats['size_mb'] > self.SIZE_CRITICAL_THRESHOLD:
                stats['warnings'].append(
                    f"Database size ({stats['size_mb']}MB) exceeds critical threshold "
                    f"({self.SIZE_CRITICAL_THRESHOLD}MB)"
                )
            elif stats['size_mb'] > self.SIZE_WARNING_THRESHOLD:
                stats['warnings'].append(
                    f"Database size ({stats['size_mb']}MB) exceeds warning threshold "
                    f"({self.SIZE_WARNING_THRESHOLD}MB)"
                )
            
            conn.close()
            
        except Exception as e:
            stats['error'] = str(e)
        
        # 记录历史
        self._history.append({
            'timestamp': datetime.now().isoformat(),
            'size_mb': stats['size_mb'],
            'total_records': stats['total_records'],
        })
        
        # 保留最近 100 条记录
        if len(self._history) > 100:
            self._history = self._history[-100:]
        
        return stats
    
    def _get_table_stats(
        self,
        cursor: sqlite3.Cursor,
        table_name: str
    ) -> Dict[str, Any]:
        """获取表统计"""
        stats = {
            'name': table_name,
            'row_count': 0,
            'size_estimate_kb': 0,
        }
        
        try:
            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            stats['row_count'] = cursor.fetchone()[0]
            
            # 估算大小 (假设每行约 1KB)
            stats['size_estimate_kb'] = stats['row_count']
            
        except Exception as e:
            stats['error'] = str(e)
        
        return stats
    
    def _get_size_status(self, size_bytes: int) -> str:
        """获取大小状态"""
        size_mb = size_bytes / 1024 / 1024
        
        if size_mb > self.SIZE_CRITICAL_THRESHOLD:
            return 'critical'
        elif size_mb > self.SIZE_WARNING_THRESHOLD:
            return 'warning'
        else:
            return 'normal'
    
    def get_growth_trend(self) -> Dict[str, Any]:
        """获取增长趋势"""
        if len(self._history) < 2:
            return {
                'available': False,
                'reason': 'Not enough history data',
            }
        
        # 计算增长率
        first = self._history[0]
        last = self._history[-1]
        
        time_diff = (
            datetime.fromisoformat(last['timestamp']) -
            datetime.fromisoformat(first['timestamp'])
        ).total_seconds() / 3600  # 小时
        
        if time_diff <= 0:
            return {'available': False, 'reason': 'Time diff is zero'}
        
        size_growth = last['size_mb'] - first['size_mb']
        record_growth = last['total_records'] - first['total_records']
        
        return {
            'available': True,
            'time_range_hours': round(time_diff, 2),
            'size_growth_mb': round(size_growth, 2),
            'size_growth_per_hour': round(size_growth / time_diff, 3),
            'record_growth': record_growth,
            'record_growth_per_hour': round(record_growth / time_diff, 2),
            'projected_size_24h': round(
                last['size_mb'] + (size_growth / time_diff) * 24, 2
            ),
        }
    
    def check_capacity(self) -> Dict[str, Any]:
        """检查容量状态"""
        stats = self.get_database_stats()
        
        result = {
            'status': 'ok',
            'database': stats,
            'recommendations': [],
            'timestamp': datetime.now().isoformat(),
        }
        
        # 检查大小
        if stats.get('size_status') == 'critical':
            result['status'] = 'critical'
            result['recommendations'].append(
                "Database size is critical. Consider: "
                "1. Running cleanup_old_data() "
                "2. Archiving old records "
                "3. Increasing storage capacity"
            )
        elif stats.get('size_status') == 'warning':
            result['status'] = 'warning'
            result['recommendations'].append(
                "Database size is approaching limit. "
                "Consider running cleanup_old_data()"
            )
        
        # 检查增长趋势
        trend = self.get_growth_trend()
        if trend.get('available'):
            if trend['size_growth_per_hour'] > 10:  # >10MB/hour
                result['recommendations'].append(
                    f"High growth rate detected: {trend['size_growth_per_hour']}MB/hour"
                )
        
        return result


# =============================================================================
# 便捷函数
# =============================================================================

def cache_query(key: str, factory: Callable[[], Any], ttl: int = 300) -> Any:
    """便捷函数：查询缓存"""
    return get_query_cache().get_or_set(key, factory, ttl)


def create_backup(db_path: str, backup_dir: str = 'data/backups') -> str:
    """便捷函数：创建数据库备份"""
    backup = DatabaseBackup(db_path, backup_dir)
    return backup.create_backup()


def monitor_capacity(db_path: str) -> Dict[str, Any]:
    """便捷函数：监控数据库容量"""
    monitor = CapacityMonitor(db_path)
    return monitor.check_capacity()


if __name__ == '__main__':
    # 测试模块
    print("Testing Database Optimization Module...")
    
    # 测试查询缓存
    print("\n=== Testing QueryCache ===")
    cache = QueryCache(max_size=5, default_ttl=60)
    
    cache.set('key1', 'value1')
    print(f"Get key1: {cache.get('key1')}")
    print(f"Stats: {cache.get_stats()}")
    
    # 测试数据库备份和容量监控
    db_path = 'data/brand_test.db'
    if Path(db_path).exists():
        print(f"\n=== Testing DatabaseBackup for {db_path} ===")
        backup = DatabaseBackup(db_path)
        print(f"Backup stats: {backup.get_stats()}")
        
        print(f"\n=== Testing CapacityMonitor for {db_path} ===")
        monitor = CapacityMonitor(db_path)
        stats = monitor.get_database_stats()
        print(f"Database size: {stats['size_mb']}MB ({stats['size_status']})")
        print(f"Total records: {stats['total_records']}")
        if stats.get('warnings'):
            print(f"Warnings: {stats['warnings']}")
    else:
        print(f"\nDatabase not found: {db_path}")
