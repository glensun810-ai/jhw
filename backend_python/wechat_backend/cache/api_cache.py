#!/usr/bin/env python3
"""
API 缓存机制
提供请求缓存、响应缓存、智能失效等功能

功能:
1. 响应缓存 (Response Caching)
2. 请求去重 (Request Deduplication)
3. 智能失效 (Smart Invalidation)
4. 多级缓存 (Multi-level Caching)
5. 持久化存储 (Persistent Storage) - 新增
"""

import time
import hashlib
import json
import os
import gzip
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Tuple
from functools import wraps
from collections import OrderedDict
from flask import request, jsonify, g, make_response
from wechat_backend.logging_config import api_logger
from contextlib import contextmanager

# ==================== 缓存配置 ====================

class CacheConfig:
    """缓存配置"""
    # 默认缓存时间（秒）
    DEFAULT_TTL = 300  # 5 分钟

    # 最大缓存条目数
    MAX_ENTRIES = 1000

    # 缓存键前缀
    KEY_PREFIX = 'api_cache:'

    # 需要缓存的 HTTP 方法
    CACHEABLE_METHODS = ['GET', 'HEAD']

    # 不缓存的 HTTP 状态码
    NON_CACHEABLE_STATUS = [400, 401, 403, 404, 500, 502, 503]

    # 【新增】持久化配置
    PERSISTENCE_ENABLED = True
    PERSISTENCE_DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'cache.db'
    )
    # 内存缓存最大大小（MB）
    MAX_MEMORY_SIZE_MB = 512
    # 大对象阈值（KB），超过此值启用压缩
    COMPRESSION_THRESHOLD_KB = 10
    # 压缩阈值字节
    COMPRESSION_THRESHOLD_BYTES = COMPRESSION_THRESHOLD_KB * 1024


# ==================== 内存缓存存储 ====================

class MemoryCache:
    """
    内存缓存实现
    使用 OrderedDict 实现 LRU 淘汰策略
    """
    
    def __init__(self, max_size: int = CacheConfig.MAX_ENTRIES):
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.sets = 0
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # 检查是否过期
        if entry['expires_at'] and time.time() > entry['expires_at']:
            self.delete(key)
            self.misses += 1
            return None
        
        # 移动到末尾（最近使用）
        self.cache.move_to_end(key)
        self.hits += 1
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: int = CacheConfig.DEFAULT_TTL):
        """设置缓存"""
        # 如果已满，删除最旧的条目
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self.delete(oldest_key)
        
        expires_at = time.time() + ttl if ttl > 0 else None
        
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': time.time(),
            'size': len(json.dumps(value)) if value else 0
        }
        
        self.sets += 1
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        api_logger.info('缓存已清空')
    
    def delete_pattern(self, pattern: str) -> int:
        """
        根据模式删除缓存
        支持通配符 *
        """
        import fnmatch
        deleted_count = 0
        
        keys_to_delete = [
            key for key in self.cache.keys()
            if fnmatch.fnmatch(key, pattern)
        ]
        
        for key in keys_to_delete:
            self.delete(key)
            deleted_count += 1
        
        return deleted_count
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_size = sum(entry.get('size', 0) for entry in self.cache.values())

        hit_rate = 0
        if self.hits + self.misses > 0:
            hit_rate = self.hits / (self.hits + self.misses) * 100

        return {
            'entries': len(self.cache),
            'max_entries': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'hit_rate': f'{hit_rate:.2f}%',
            'total_size_kb': round(total_size / 1024, 2),
            'utilization': f'{len(self.cache) / self.max_size * 100:.1f}%'
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取缓存监控指标"""
        total_size = sum(entry.get('size', 0) for entry in self.cache.values())
        total_requests = self.hits + self.misses
        
        return {
            'entries': len(self.cache),
            'max_entries': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'hit_rate': round(self.hits / max(total_requests, 1) * 100, 2),
            'miss_rate': round(self.misses / max(total_requests, 1) * 100, 2),
            'total_requests': total_requests,
            'total_size_kb': round(total_size / 1024, 2),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'utilization': round(len(self.cache) / self.max_size * 100, 1),
            'avg_entry_size_kb': round(total_size / max(len(self.cache), 1) / 1024, 2)
        }
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry['expires_at'] and current_time > entry['expires_at']
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        return len(expired_keys)


# ==================== 持久化缓存层 ====================

class PersistentCache:
    """
    持久化缓存实现
    使用 SQLite 存储，支持重启后恢复缓存
    
    功能:
    1. 缓存持久化（重启不丢失）
    2. 大对象压缩存储
    3. 自动清理过期数据
    4. 内存限制保护
    """
    
    def __init__(self, db_path: str = CacheConfig.PERSISTENCE_DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        api_logger.info(f"持久化缓存初始化：{db_path}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    expires_at REAL,
                    created_at REAL,
                    is_compressed INTEGER DEFAULT 0,
                    size_bytes INTEGER
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)')
    
    def _compress(self, data: bytes) -> bytes:
        """压缩数据"""
        if len(data) > CacheConfig.COMPRESSION_THRESHOLD_BYTES:
            return gzip.compress(data, compresslevel=6)
        return data
    
    def _decompress(self, data: bytes) -> bytes:
        """解压缩数据"""
        try:
            return gzip.decompress(data)
        except Exception:
            # 如果不是压缩数据，直接返回
            return data
    
    def get(self, key: str) -> Optional[Any]:
        """获取持久化缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT value, expires_at, is_compressed
                FROM cache_entries
                WHERE key = ?
            ''', (key,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            value_bytes, expires_at, is_compressed = row
            
            # 检查是否过期
            if expires_at and time.time() > expires_at:
                self.delete(key)
                return None
            
            # 解压缩
            if is_compressed:
                value_bytes = self._decompress(value_bytes)
            
            try:
                return json.loads(value_bytes.decode('utf-8'))
            except Exception:
                return None
    
    def set(self, key: str, value: Any, ttl: int = CacheConfig.DEFAULT_TTL):
        """设置持久化缓存"""
        try:
            value_bytes = json.dumps(value).encode('utf-8')
            is_compressed = 0
            
            # 大对象压缩
            if len(value_bytes) > CacheConfig.COMPRESSION_THRESHOLD_BYTES:
                value_bytes = self._compress(value_bytes)
                is_compressed = 1
            
            expires_at = time.time() + ttl if ttl > 0 else None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cache_entries
                    (key, value, expires_at, created_at, is_compressed, size_bytes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (key, value_bytes, expires_at, time.time(), is_compressed, len(value_bytes)))
        
        except Exception as e:
            api_logger.error(f"持久化缓存设置失败：{e}")
    
    def delete(self, key: str) -> bool:
        """删除持久化缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
            return cursor.rowcount > 0
    
    def clear(self):
        """清空持久化缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cache_entries')
        api_logger.info('持久化缓存已清空')
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cache_entries WHERE expires_at < ?', (time.time(),))
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                api_logger.info(f"清理了 {deleted_count} 条过期缓存")
            return deleted_count
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 总条目数
            cursor.execute('SELECT COUNT(*) FROM cache_entries')
            total_entries = cursor.fetchone()[0]
            
            # 压缩条目数
            cursor.execute('SELECT COUNT(*) FROM cache_entries WHERE is_compressed = 1')
            compressed_entries = cursor.fetchone()[0]
            
            # 总大小
            cursor.execute('SELECT SUM(size_bytes) FROM cache_entries')
            total_size = cursor.fetchone()[0] or 0
            
            # 过期条目数
            cursor.execute('SELECT COUNT(*) FROM cache_entries WHERE expires_at < ?', (time.time(),))
            expired_entries = cursor.fetchone()[0]
            
            return {
                'total_entries': total_entries,
                'compressed_entries': compressed_entries,
                'compression_ratio': f'{compressed_entries / max(total_entries, 1) * 100:.1f}%',
                'total_size_kb': round(total_size / 1024, 2),
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'expired_entries': expired_entries
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取持久化缓存监控指标"""
        stats = self.stats()
        return {
            'entries': stats['total_entries'],
            'compressed_entries': stats['compressed_entries'],
            'compression_ratio': stats['compression_ratio'],
            'total_size_kb': stats['total_size_kb'],
            'total_size_mb': stats['total_size_mb'],
            'expired_entries': stats['expired_entries'],
            'hit_rate': 0,  # PersistentCache 不直接统计命中率
            'miss_rate': 0
        }


# ==================== 混合缓存（L1 + L2） ====================

class HybridCache:
    """
    混合缓存实现
    L1: MemoryCache（热点数据，快速访问）
    L2: PersistentCache（冷数据，持久化）
    
    策略:
    1. 写入：同时写入 L1 和 L2
    2. 读取：先读 L1，未命中读 L2，并回写到 L1
    3. 删除：同时删除 L1 和 L2
    4. 过期：L1 自动过期，L2 定期清理
    """
    
    def __init__(self, memory_cache: MemoryCache = None, persistent_cache: PersistentCache = None):
        self.l1_cache = memory_cache or MemoryCache()
        self.l2_cache = persistent_cache if persistent_cache is not None else PersistentCache()
        self.enabled = CacheConfig.PERSISTENCE_ENABLED
        api_logger.info(f"混合缓存初始化：L1={type(self.l1_cache).__name__}, L2={type(self.l2_cache).__name__}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存（L1 → L2）"""
        # 先读 L1
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # L1 未命中，读 L2
        if self.enabled:
            value = self.l2_cache.get(key)
            if value is not None:
                # 回写到 L1
                self.l1_cache.set(key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = CacheConfig.DEFAULT_TTL):
        """设置缓存（L1 + L2）"""
        # 写入 L1
        self.l1_cache.set(key, value, ttl)
        
        # 写入 L2
        if self.enabled:
            self.l2_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存（L1 + L2）"""
        l1_deleted = self.l1_cache.delete(key)
        l2_deleted = self.l2_cache.delete(key) if self.enabled else False
        return l1_deleted or l2_deleted
    
    def clear(self):
        """清空所有缓存"""
        self.l1_cache.clear()
        if self.enabled:
            self.l2_cache.clear()
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        l1_cleaned = self.l1_cache.cleanup_expired()
        l2_cleaned = self.l2_cache.cleanup_expired() if self.enabled else 0
        return l1_cleaned + l2_cleaned
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        l1_stats = self.l1_cache.stats()
        l2_stats = self.l2_cache.stats() if self.enabled else {}
        
        return {
            'l1_cache': l1_stats,
            'l2_cache': l2_stats,
            'persistence_enabled': self.enabled
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取混合缓存监控指标"""
        l1_metrics = self.l1_cache.get_metrics()
        l2_metrics = self.l2_cache.get_metrics() if self.enabled else {}
        
        # 计算整体命中率
        total_hits = l1_metrics.get('hits', 0) + l2_metrics.get('hits', 0) if self.enabled else l1_metrics.get('hits', 0)
        total_misses = l1_metrics.get('misses', 0)
        total_requests = total_hits + total_misses
        
        return {
            'l1_cache': l1_metrics,
            'l2_cache': l2_metrics,
            'persistence_enabled': self.enabled,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'total_requests': total_requests,
            'overall_hit_rate': round(total_hits / max(total_requests, 1) * 100, 2),
            'overall_miss_rate': round(total_misses / max(total_requests, 1) * 100, 2),
            'l1_hit_ratio': round(l1_metrics.get('hits', 0) / max(total_hits, 1) * 100, 2) if total_hits > 0 else 0,
            'l2_hit_ratio': round(l2_metrics.get('hits', 0) / max(total_hits, 1) * 100, 2) if self.enabled and total_hits > 0 else 0
        }


# 全局缓存实例（升级为混合缓存）
_api_cache = HybridCache()


# ==================== 缓存装饰器 ====================

def cache_response(ttl: int = CacheConfig.DEFAULT_TTL, 
                   key_generator: Callable = None,
                   cache_condition: Callable = None):
    """
    响应缓存装饰器
    
    参数:
        ttl: 缓存时间（秒），0 表示不缓存
        key_generator: 自定义缓存键生成函数
        cache_condition: 缓存条件函数，返回 True 才缓存
    
    用法:
        @cache_response(ttl=300)
        def get_data():
            ...
        
        @cache_response(ttl=600, key_generator=lambda: f"user:{g.user_id}")
        def get_user_data():
            ...
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 检查是否可缓存
            if request.method not in CacheConfig.CACHEABLE_METHODS:
                return f(*args, **kwargs)
            
            # 生成缓存键
            if key_generator:
                cache_key = f"{CacheConfig.KEY_PREFIX}{key_generator()}"
            else:
                cache_key = _generate_cache_key()
            
            # 检查缓存
            cached_response = _api_cache.get(cache_key)
            if cached_response is not None:
                api_logger.debug(f'缓存命中：{cache_key}')
                
                # 添加缓存头
                response = make_response(cached_response)
                response.headers['X-Cache'] = 'HIT'
                response.headers['X-Cache-Age'] = str(
                    int(time.time() - cached_response.get('_cached_at', time.time()))
                )
                return response
            
            # 执行原函数
            result = f(*args, **kwargs)
            
            # 检查是否需要缓存
            should_cache = True
            
            if cache_condition and not cache_condition():
                should_cache = False
            
            # 检查响应状态码
            if hasattr(result, 'status_code'):
                if result.status_code in CacheConfig.NON_CACHEABLE_STATUS:
                    should_cache = False
            
            # 缓存响应
            if should_cache and ttl > 0:
                response_data = result
                if hasattr(result, 'get_json'):
                    response_data = result.get_json()
                
                # 添加元数据
                if isinstance(response_data, dict):
                    response_data['_cached_at'] = time.time()
                
                _api_cache.set(cache_key, response_data, ttl)
                api_logger.debug(f'缓存已设置：{cache_key}, ttl={ttl}')
            
            # 添加缓存头
            response = make_response(result)
            response.headers['X-Cache'] = 'MISS'
            return response
        
        return decorated_function
    return decorator


def invalidate_cache(pattern: str):
    """
    缓存失效装饰器
    用于在数据修改后使相关缓存失效
    
    用法:
        @invalidate_cache('api_cache:user:*')
        def update_user(user_id):
            ...
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 执行原函数
            result = f(*args, **kwargs)
            
            # 使缓存失效
            deleted_count = _api_cache.delete_pattern(pattern)
            api_logger.info(f'缓存失效：{pattern}, 删除 {deleted_count} 条')
            
            return result
        return decorated_function
    return decorator


# ==================== 请求去重 ====================

class RequestDeduplicator:
    """
    请求去重器
    防止相同请求同时执行多次
    """
    
    def __init__(self):
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
    
    def execute(self, key: str, func: Callable, ttl: int = 30) -> Any:
        """
        执行请求（去重）
        
        参数:
            key: 请求唯一键
            func: 要执行的函数
            ttl: 请求超时时间（秒）
        """
        # 检查是否有相同请求正在执行
        if key in self.pending_requests:
            pending = self.pending_requests[key]
            
            # 检查是否超时
            if time.time() - pending['start_time'] > ttl:
                api_logger.warning(f'请求超时，重新执行：{key}')
                del self.pending_requests[key]
            else:
                api_logger.debug(f'请求去重，等待中：{key}')
                # 等待原请求完成
                time.sleep(0.1)
                return self.execute(key, func, ttl)
        
        # 标记为正在执行
        self.pending_requests[key] = {
            'start_time': time.time(),
            'result': None,
            'error': None,
            'completed': False
        }
        
        try:
            # 执行请求
            result = func()
            self.pending_requests[key]['result'] = result
            self.pending_requests[key]['completed'] = True
            return result
        except Exception as e:
            self.pending_requests[key]['error'] = str(e)
            self.pending_requests[key]['completed'] = True
            raise
        finally:
            # 清理（保留一小段时间供其他请求获取结果）
            import threading
            def cleanup():
                time.sleep(1)
                if key in self.pending_requests:
                    del self.pending_requests[key]
            
            threading.Thread(target=cleanup, daemon=True).start()


# 全局去重器实例
_request_deduplicator = RequestDeduplicator()


def deduplicate_request(ttl: int = 30):
    """
    请求去重装饰器
    
    用法:
        @deduplicate_request()
        def get_large_data():
            ...
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成请求键
            request_key = _generate_cache_key()
            
            # 执行去重请求
            return _request_deduplicator.execute(
                request_key,
                lambda: f(*args, **kwargs),
                ttl
            )
        
        return decorated_function
    return decorator


# ==================== 辅助函数 ====================

def _generate_cache_key() -> str:
    """
    生成缓存键
    包含路径、方法、参数、用户 ID、请求体等所有可能影响响应的因素
    """
    key_parts = [
        request.path,
        request.method,
        request.query_string.decode() if request.query_string else '',
        str(g.get('user_id', 'anonymous'))
    ]
    
    # 对于 POST/PUT 请求，包含请求体哈希（防止不同参数命中相同缓存）
    if request.method in ['POST', 'PUT'] and request.is_json:
        try:
            body_data = request.get_json(silent=True)
            if body_data:
                # 对请求体排序后哈希，确保相同数据生成相同键
                body_sorted = json.dumps(body_data, sort_keys=True)
                body_hash = hashlib.md5(body_sorted.encode()).hexdigest()[:8]
                key_parts.append(body_hash)
        except Exception:
            # 如果无法解析请求体，跳过
            pass
    
    # 添加 Accept 头（不同格式可能返回不同响应）
    accept_header = request.headers.get('Accept', '')
    if accept_header and 'application/json' not in accept_header:
        key_parts.append(accept_header)
    
    key_string = ':'.join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    return f"{CacheConfig.KEY_PREFIX}{request.method}:{key_hash}"


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计"""
    return _api_cache.stats()


def clear_cache() -> Dict[str, Any]:
    """清空缓存"""
    _api_cache.clear()
    return {'status': 'success', 'message': '缓存已清空'}


def delete_cache_pattern(pattern: str) -> Dict[str, Any]:
    """根据模式删除缓存"""
    deleted_count = _api_cache.delete_pattern(pattern)
    return {
        'status': 'success',
        'deleted_count': deleted_count,
        'pattern': pattern
    }


def warm_up_cache(key: str, value: Any, ttl: int = CacheConfig.DEFAULT_TTL):
    """预热缓存"""
    _api_cache.set(key, value, ttl)
    api_logger.info(f'缓存已预热：{key}')


# ==================== 后台任务 ====================

# 缓存维护函数（由 BackgroundServiceManager 统一调度）
def _cleanup_expired_entries():
    """清理过期缓存条目（供后台服务管理器调用）"""
    try:
        expired_count = _api_cache.cleanup_expired()
        if expired_count > 0:
            api_logger.info(f'清理 {expired_count} 条过期缓存')
    except Exception as e:
        api_logger.error(f'缓存清理失败：{e}')


def start_cache_maintenance():
    """
    启动缓存维护任务
    
    注意：此函数现在仅用于向后兼容。
    实际维护工作由 BackgroundServiceManager 统一调度。
    """
    api_logger.info('缓存维护任务已注册到统一后台服务管理器')
    # 不再创建独立线程，由 background_service_manager 统一调度


# ==================== API 端点 ====================

from flask import Blueprint

cache_bp = Blueprint('cache', __name__)


@cache_bp.route('/api/cache/stats', methods=['GET'])
def cache_stats_endpoint():
    """获取缓存统计"""
    return jsonify({
        'status': 'success',
        'data': get_cache_stats()
    })


@cache_bp.route('/api/cache/clear', methods=['POST'])
def cache_clear_endpoint():
    """清空缓存"""
    return jsonify(clear_cache())


@cache_bp.route('/api/cache/invalidate', methods=['POST'])
def cache_invalidate_endpoint():
    """使缓存失效"""
    data = request.get_json() or {}
    pattern = data.get('pattern', '*')
    return jsonify(delete_cache_pattern(pattern))

# ==================== 全局内存缓存实例 ====================
# P1-CACHE-1 修复：创建全局 memory_cache 实例供缓存预热使用

memory_cache = MemoryCache(max_size=CacheConfig.MAX_ENTRIES)
"""全局内存缓存实例，供缓存预热等模块使用"""
