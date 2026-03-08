"""
数据库连接池模块

功能：
- SQLite 数据库连接池管理
- 连接复用，减少创建开销
- 最大连接数限制
- 监控指标采集
- P2-6: 支持读写分离

参考：P2-6: 数据库读写分离未实现
"""

import sqlite3
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from wechat_backend.logging_config import db_logger

# P0-DB-INIT-004: 修复数据库路径计算，确保与 database_core.py 一致
# 此文件路径：/.../backend_python/wechat_backend/database_connection_pool.py
# 需要上溯 2 层到 backend_python 目录
DB_PATH = Path(__file__).resolve().parent.parent / 'database.db'

# 监控指标
_db_pool_metrics = {
    'active_connections': 0,
    'available_connections': 0,
    'total_created': 0,
    'timeout_count': 0,
    'total_wait_time_ms': 0,
    'connection_count': 0,
    'last_reset_time': time.time()
}


class DatabaseConnectionPool:
    """
    SQLite 数据库连接池（P0 增强版 - 修复竞争条件）

    功能：
    1. 连接复用，减少创建开销
    2. 最大连接数限制，防止资源耗尽
    3. 自动健康检查
    4. 连接泄漏检测和回收
    5. 监控指标采集
    6. 【P1 新增】自动扩容机制

    【P0 关键修复 - 2026-03-05】
    - 修复连接获取和归还的竞争条件
    - 添加连接健康检查机制
    - 增加超时时间防止频繁超时
    - 实现连接泄漏检测

    【P1 新增 - 2026-03-05】
    - 根据负载自动调整连接池大小
    - 支持弹性扩容和缩容
    """

    def __init__(self, max_connections: int = 100, timeout: float = 15.0):
        self.max_connections = max_connections
        self.default_timeout = timeout  # 【P0 修复 - 2026-03-05】默认超时增加到 15.0 秒
        self._pool: list = []
        self._in_use: set = set()
        self._lock = threading.RLock()  # 【P0 修复】使用可重入锁
        self._created_count = 0
        self._timeout_count = 0
        self._total_wait_time_ms = 0
        self._connection_count = 0
        self._leak_detection_count = 0  # 【P0 新增】连接泄漏检测次数

        # 【P0 新增】连接泄漏监控
        self._connection_use_time: Dict[int, float] = {}  # 记录连接使用开始时间
        self._connection_thread: Dict[int, int] = {}  # 记录连接占用线程 ID

        # 【P1 新增】连接泄漏检测配置
        self.max_connection_age = 30.0  # 最大连接年龄 30 秒
        self._leak_check_stop = threading.Event()
        self._leak_check_thread = threading.Thread(
            target=self._leak_check_loop,
            daemon=True,
            name="ConnectionLeakChecker"
        )
        self._leak_check_thread.start()

        # 【P1 新增】自动扩容配置
        self.auto_scale_enabled = True
        self.scale_up_threshold = 0.85  # 利用率超过 85% 时扩容
        self.scale_down_threshold = 0.3  # 利用率低于 30% 时缩容
        self.scale_step = 10  # 每次调整的连接数
        self.min_connections = 20  # 【P0 修复】最小连接数增加到 20
        self.max_connections_hard = 200  # 【P0 修复】最大连接数硬限制增加到 200
        self._last_scale_time = 0
        self._scale_cooldown_seconds = 60  # 扩容冷却时间

        db_logger.info(
            f"数据库连接池初始化：max_connections={max_connections}, "
            f"timeout={timeout}s, max_connection_age={self.max_connection_age}s, "
            f"auto_scale={self.auto_scale_enabled}"
        )

    def get_connection(self, timeout: Optional[float] = None) -> sqlite3.Connection:
        """获取数据库连接（P0 增强版 - 修复竞争条件）

        参数：
            timeout: 超时时间（秒），默认使用实例的 default_timeout（5 秒）
                     增加超时时间避免高并发下频繁超时

        返回：
            sqlite3.Connection: 数据库连接

        异常：
            TimeoutError: 获取连接超时
            ConnectionError: 无法创建健康连接

        【P0 关键修复 - 2026-03-05】
        1. 使用 RLock 避免死锁
        2. 添加连接健康检查
        3. 异常时确保连接正确清理
        4. 记录连接使用时间用于泄漏检测
        """
        if timeout is None:
            timeout = self.default_timeout
        
        start_time = time.time()
        wait_start = start_time
        max_wait_time = timeout
        conn = None

        while True:
            try:
                with self._lock:
                    # 尝试从池中获取
                    while self._pool:
                        conn = self._pool.pop()
                        # 【P0 修复】健康检查
                        if self._is_connection_healthy(conn):
                            self._in_use.add(id(conn))
                            self._connection_use_time[id(conn)] = time.time()
                            self._connection_thread[id(conn)] = threading.current_thread().ident
                            wait_time_ms = (time.time() - wait_start) * 1000
                            self._total_wait_time_ms += wait_time_ms
                            self._connection_count += 1
                            self._update_metrics()
                            # 【P2 增强】详细日志 - 记录线程名称
                            current_thread = threading.current_thread()
                            db_logger.debug(
                                f"[DB] 连接获取：thread_name={current_thread.name}, "
                                f"thread_id={current_thread.ident}, conn_id={id(conn)}, "
                                f"等待={wait_time_ms:.2f}ms, 池中剩余={len(self._pool)}"
                            )
                            return conn
                        else:
                            # 连接不健康，关闭并继续
                            current_thread = threading.current_thread()
                            db_logger.warning(
                                f"[DB] 连接不健康，已关闭：thread_name={current_thread.name}, conn_id={id(conn)}"
                            )
                            try:
                                conn.close()
                            except Exception as close_err:
                                db_logger.error(f"关闭 unhealthy 连接失败：{close_err}")
                            conn = None
                            self._created_count -= 1

                    # 如果未达到上限，创建新连接
                    if self._created_count < self.max_connections:
                        self._created_count += 1
                        try:
                            conn = sqlite3.connect(
                                DB_PATH, 
                                timeout=30.0, 
                                check_same_thread=False
                            )
                            conn.execute('PRAGMA journal_mode=WAL')
                            conn.execute('PRAGMA synchronous=NORMAL')
                            
                            # 【P0 修复】验证连接可用
                            conn.execute('SELECT 1').fetchone()
                            
                            self._in_use.add(id(conn))
                            self._connection_use_time[id(conn)] = time.time()
                            self._connection_thread[id(conn)] = threading.current_thread().ident
                            wait_time_ms = (time.time() - wait_start) * 1000
                            self._total_wait_time_ms += wait_time_ms
                            self._connection_count += 1
                            self._update_metrics()
                            db_logger.debug(
                                f"连接池创建新连接：等待{wait_time_ms:.2f}ms"
                            )
                            return conn
                            
                        except Exception as e:
                            # 创建失败，回滚计数
                            self._created_count -= 1
                            db_logger.error(f"创建数据库连接失败：{e}")
                            if conn:
                                try:
                                    conn.close()
                                except:
                                    pass
                            conn = None
                            # 继续重试
                            pass

                    # 检查是否超时
                    if (time.time() - start_time) >= max_wait_time:
                        self._timeout_count += 1
                        self._update_metrics()
                        db_logger.error(
                            f"连接池获取连接超时：{max_wait_time}秒，"
                            f"active={len(self._in_use)}, available={len(self._pool)}"
                        )
                        raise TimeoutError(
                            f"Database connection timeout after {max_wait_time}s "
                            f"(active={len(self._in_use)}, available={len(self._pool)})"
                        )

                # 等待后重试（在锁外等待，减少锁竞争）
                time.sleep(0.1)
                
            except TimeoutError:
                # 超时错误直接抛出
                raise
            except Exception as e:
                # 【P0 修复】确保异常时清理连接
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None
                db_logger.error(f"获取数据库连接异常：{e}", exc_info=True)
                # 短暂等待后重试
                time.sleep(0.1)

    def return_connection(self, conn: sqlite3.Connection):
        """归还数据库连接（P0 增强版 - 修复竞争条件）

        参数：
            conn: 数据库连接

        【P0 关键修复 - 2026-03-05】
        1. 归还前健康检查
        2. 检测连接泄漏（长时间未归还）
        3. unhealthy 连接不回收
        """
        with self._lock:
            conn_id = id(conn)
            
            if conn_id not in self._in_use:
                # 【P0 修复】检测到未借出的连接，可能是重复归还
                db_logger.warning(
                    f"连接池检测到重复归还：id={conn_id}, "
                    f"可能已存在连接泄漏"
                )
                try:
                    conn.close()
                except:
                    pass
                return
            
            # 【P0 新增】检查连接使用时间（检测泄漏）
            use_start_time = self._connection_use_time.get(conn_id, time.time())
            use_duration = time.time() - use_start_time
            
            # 【P0 修复】如果连接使用超过 30 秒，记录警告（更激进的泄漏检测）（可能是泄漏）
            if use_duration > 30:  # 【P0 修复】降低泄漏检测阈值到 30 秒
                self._leak_detection_count += 1
                db_logger.warning(
                    f"⚠️ 连接池检测到潜在连接泄漏："
                    f"id={conn_id}, 使用时长={use_duration:.1f}秒"
                )
            
            # 清理使用时间记录
            if conn_id in self._connection_use_time:
                del self._connection_use_time[conn_id]
            if conn_id in self._connection_thread:
                del self._connection_thread[conn_id]

            self._in_use.remove(conn_id)
            
            # 【P0 修复 - 2026-03-05】健康检查后再放回池中
            if self._is_connection_healthy(conn):
                self._pool.append(conn)
                # 【P0 修复】确保计数正确
                if self._created_count > self.max_connections:
                    # 连接数超过上限，关闭多余连接
                    try:
                        conn.close()
                        self._pool.pop()  # 移除刚添加的连接
                        self._created_count -= 1
                        db_logger.info(
                            f"连接池超出上限，关闭多余连接：created_count={self._created_count}"
                        )
                    except Exception as close_err:
                        db_logger.error(f"关闭多余连接失败：{close_err}")
                else:
                    db_logger.debug(
                        f"连接池归还连接：池中数量={len(self._pool)}, "
                        f"使用时长={use_duration:.1f}秒"
                    )
            else:
                # 连接不健康，关闭并减少计数
                try:
                    conn.close()
                except Exception as close_err:
                    db_logger.error(f"关闭 unhealthy 连接失败：{close_err}")
                self._created_count -= 1
                db_logger.warning(
                    f"归还 unhealthy 连接，已关闭：id={conn_id}, "
                    f"created_count={self._created_count}"
                )
            
            self._update_metrics()

    def _is_connection_healthy(self, conn: sqlite3.Connection) -> bool:
        """
        检查连接是否健康

        参数：
            conn: SQLite 连接

        返回：
            bool: 连接是否健康

        【P0 新增】连接健康检查
        """
        try:
            # 简单查询测试
            conn.execute('SELECT 1').fetchone()
            return True
        except Exception as e:
            db_logger.debug(f"连接健康检查失败：{e}")
            return False

    def detect_leaks(self) -> Dict[int, Dict[str, Any]]:
        """
        检测可能的连接泄漏

        返回：
            泄漏连接信息字典 {conn_id: {'duration': 使用时长，...}}

        【P0 新增】连接泄漏检测
        """
        leaks = {}
        current_time = time.time()

        with self._lock:
            for conn_id, start_time in list(self._connection_use_time.items()):
                duration = current_time - start_time
                if duration > 30:  # 超过 30 秒视为潜在泄漏
                    leaks[conn_id] = {
                        'duration': duration,
                        'in_use': conn_id in self._in_use,
                        'thread_id': self._connection_thread.get(conn_id, 'unknown')
                    }

        if leaks:
            db_logger.warning(
                f"🚨 连接池检测到 {len(leaks)} 个潜在连接泄漏"
            )

        return leaks

    # 【P1 新增】连接泄漏检测循环和强制归还
    def _leak_check_loop(self):
        """
        定期泄漏检测循环

        每 10 秒检查一次，发现超过 max_connection_age 的连接强制归还
        """
        while not self._leak_check_stop.is_set():
            try:
                leaked_count = self._check_and_fix_leaks()
                if leaked_count > 0:
                    db_logger.warning(
                        f"[连接泄漏] 检测并修复 {leaked_count} 个泄漏连接"
                    )
            except Exception as e:
                db_logger.error(f"[连接泄漏] 检测失败：{e}")

            # 每 10 秒检查一次
            self._leak_check_stop.wait(10.0)

    def _check_and_fix_leaks(self) -> int:
        """
        检查并修复连接泄漏

        返回：
            修复的泄漏连接数
        """
        current_time = time.time()
        fixed_count = 0

        with self._lock:
            for conn_id, start_time in list(self._connection_use_time.items()):
                age = current_time - start_time

                if age > self.max_connection_age:
                    thread_id = self._connection_thread.get(conn_id, 'unknown')
                    
                    # 【P2 增强】记录更详细的泄漏信息，便于定位泄漏源
                    db_logger.warning(
                        f"[连接泄漏] 连接超时未归还：id={conn_id}, "
                        f"年龄={age:.1f}秒，thread_id={thread_id}, "
                        f"池中剩余={len(self._pool)}, 使用中={len(self._in_use)}"
                    )

                    # 强制归还
                    if conn_id in self._in_use:
                        self._in_use.discard(conn_id)
                        self._leak_detection_count += 1
                        fixed_count += 1

                    # 清理记录
                    self._connection_use_time.pop(conn_id, None)
                    self._connection_thread.pop(conn_id, None)

                    db_logger.warning(
                        f"[连接泄漏] 强制归还连接：id={conn_id}"
                    )

        return fixed_count

    def stop(self):
        """停止连接池（停止泄漏检测线程）"""
        self._leak_check_stop.set()
        if self._leak_check_thread and self._leak_check_thread.is_alive():
            self._leak_check_thread.join(timeout=2.0)
        db_logger.info("[连接池] 泄漏检测线程已停止")

    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._in_use.clear()
            self._update_metrics()
            db_logger.info("连接池关闭所有连接")

    def _update_metrics(self):
        """更新监控指标"""
        global _db_pool_metrics
        _db_pool_metrics.update({
            'active_connections': len(self._in_use),
            'available_connections': len(self._pool),
            'total_created': self._created_count,
            'timeout_count': self._timeout_count,
            'total_wait_time_ms': self._total_wait_time_ms,
            'connection_count': self._connection_count,
            'last_reset_time': time.time()
        })

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取监控指标（P2 增强版 - 支持告警）

        返回:
            指标字典
        """
        metrics = _db_pool_metrics.copy()

        # 【P0 修复】添加健康状态评估
        utilization_rate = (
            metrics['active_connections'] / self.max_connections
            if self.max_connections > 0 else 0
        )

        # 健康状态判断
        if utilization_rate > 0.9:
            health_status = 'critical'
            health_message = '连接池利用率超过 90%，存在连接泄漏风险'
            alert_level = 'critical'
        elif utilization_rate > 0.8:
            health_status = 'warning'
            health_message = '连接池利用率超过 80%，请密切关注'
            alert_level = 'warning'
        elif utilization_rate > 0.7:
            health_status = 'caution'
            health_message = '连接池利用率超过 70%'
            alert_level = 'info'
        else:
            health_status = 'healthy'
            health_message = '连接池运行正常'
            alert_level = 'none'

        # 【P2 新增】检测潜在泄漏
        potential_leaks = len([
            t for t, start in self._connection_use_time.items()
            if (time.time() - start) > 30
        ])

        metrics.update({
            'max_connections': self.max_connections,
            'utilization_rate': round(utilization_rate, 3),
            'health_status': health_status,
            'health_message': health_message,
            'alert_level': alert_level,  # critical/warning/info/none
            'leak_detection_count': self._leak_detection_count,
            'potential_leaks': potential_leaks,
            'active_connections': len(self._in_use),
            'available_connections': len(self._pool),
            'timestamp': datetime.now().isoformat()
        })

        # 【P1 新增】检查并触发自动扩容
        self._check_and_auto_scale()

        return metrics

    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池详细状态（P0 增强版）

        返回：
            状态字典
        """
        with self._lock:
            # 检测潜在泄漏
            leaks = self.detect_leaks()

            return {
                'max_connections': self.max_connections,
                'active_connections': len(self._in_use),
                'available_connections': len(self._pool),
                'total_created': self._created_count,
                'timeout_count': self._timeout_count,
                'leak_detection_count': self._leak_detection_count,
                'potential_leaks': len(leaks),
                'leak_details': leaks,  # 详细泄漏信息
                'avg_wait_time_ms': (
                    self._total_wait_time_ms / self._connection_count
                    if self._connection_count > 0 else 0
                ),
                'health_status': self.get_metrics()['health_status'],
                'default_timeout': self.default_timeout
            }

    # ==================== 【P1 新增】自动扩容机制 ====================

    def _check_and_auto_scale(self):
        """
        检查并自动调整连接池大小

        【P1 新增 - 2026-03-05】
        根据当前负载自动扩容或缩容
        """
        if not self.auto_scale_enabled:
            return

        current_time = time.time()

        # 检查冷却时间
        if current_time - self._last_scale_time < self._scale_cooldown_seconds:
            return

        utilization = len(self._in_use) / self.max_connections if self.max_connections > 0 else 0

        # 扩容逻辑
        if utilization > self.scale_up_threshold:
            self._scale_up()
        # 缩容逻辑
        elif utilization < self.scale_down_threshold and len(self._pool) > 0:
            self._scale_down()

    def _scale_up(self):
        """
        扩容连接池

        【P1 新增】
        """
        import threading

        new_size = min(
            self.max_connections + self.scale_step,
            self.max_connections_hard
        )

        if new_size <= self.max_connections:
            return  # 已达到上限

        old_size = self.max_connections
        self.max_connections = new_size
        self._last_scale_time = time.time()

        db_logger.warning(
            f"📈 [连接池扩容] {old_size} -> {new_size} "
            f"(利用率={len(self._in_use)/old_size*100:.1f}%)"
        )

    def _scale_down(self):
        """
        缩容连接池

        【P1 新增】
        """
        new_size = max(
            self.max_connections - self.scale_step,
            self.min_connections
        )

        if new_size >= self.max_connections:
            return  # 无需缩容

        old_size = self.max_connections
        self.max_connections = new_size
        self._last_scale_time = time.time()

        # 关闭多余的连接
        excess = len(self._pool) - (new_size - len(self._in_use))
        if excess > 0:
            with self._lock:
                for _ in range(min(excess, len(self._pool))):
                    if self._pool:
                        conn = self._pool.pop()
                        try:
                            conn.close()
                        except:
                            pass
                        self._created_count -= 1

        db_logger.warning(
            f"📉 [连接池缩容] {old_size} -> {new_size} "
            f"(利用率={len(self._in_use)/old_size*100:.1f}%)"
        )

    def configure_auto_scale(
        self,
        enabled: bool = True,
        scale_up_threshold: float = 0.85,
        scale_down_threshold: float = 0.3,
        scale_step: int = 10,
        min_connections: int = 10,
        max_connections_hard: int = 100,
        cooldown_seconds: int = 60
    ):
        """
        配置自动扩容参数

        参数:
            enabled: 是否启用
            scale_up_threshold: 扩容阈值
            scale_down_threshold: 缩容阈值
            scale_step: 每次调整步长
            min_connections: 最小连接数
            max_connections_hard: 最大连接数硬限制
            cooldown_seconds: 冷却时间
        """
        self.auto_scale_enabled = enabled
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.scale_step = scale_step
        self.min_connections = min_connections
        self.max_connections_hard = max_connections_hard
        self._scale_cooldown_seconds = cooldown_seconds

        db_logger.info(
            f"[连接池] 自动扩容配置已更新：enabled={enabled}, "
            f"up_threshold={scale_up_threshold}, down_threshold={scale_down_threshold}"
        )

    def reset_metrics(self):
        """重置监控指标"""
        global _db_pool_metrics
        _db_pool_metrics.update({
            'active_connections': 0,
            'available_connections': 0,
            'total_created': 0,
            'timeout_count': 0,
            'total_wait_time_ms': 0,
            'connection_count': 0,
            'last_reset_time': time.time()
        })


# 全局连接池实例
_db_pool: Optional[DatabaseConnectionPool] = None


def get_db_pool() -> DatabaseConnectionPool:
    """获取全局连接池实例"""
    global _db_pool
    if _db_pool is None:
        # 【P0 关键修复 - 2026-03-04】增加连接池大小，支持高并发轮询和短事务模式
        # 从 20 提升到 50，减少连接池排队等待
        _db_pool = DatabaseConnectionPool(max_connections=50)
    return _db_pool


def get_db_pool_metrics() -> Dict[str, Any]:
    """获取连接池指标"""
    return get_db_pool().get_metrics()


def reset_db_pool_metrics():
    """重置连接池指标"""
    get_db_pool().reset_metrics()


def close_db_pool():
    """关闭连接池"""
    global _db_pool
    if _db_pool:
        _db_pool.close_all()
        _db_pool = None


# ==================== P2-6: 读写分离兼容函数 ====================

def get_db_connection(operation_type: str = 'read') -> sqlite3.Connection:
    """
    根据操作类型获取数据库连接（兼容旧代码）
    
    Args:
        operation_type: 操作类型 ('read' 或 'write')
        
    Returns:
        数据库连接
    """
    # 尝试使用读写分离连接
    try:
        from wechat_backend.database.database_read_write_split import get_db_connection as get_rw_db_connection
        return get_rw_db_connection(operation_type)
    except Exception:
        # 回退到默认连接池
        return get_db_pool().get_connection()


def return_db_connection(conn: sqlite3.Connection, operation_type: str = 'read'):
    """
    归还数据库连接（兼容旧代码）
    
    Args:
        conn: 数据库连接
        operation_type: 操作类型 ('read' 或 'write')
    """
    # 尝试使用读写分离归还
    try:
        from wechat_backend.database.database_read_write_split import return_db_connection as return_rw_db_connection
        return_rw_db_connection(conn, operation_type)
    except Exception:
        # 回退到默认连接池
        get_db_pool().return_connection(conn)
