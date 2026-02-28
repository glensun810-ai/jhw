"""
数据库读写分离核心模块

功能：
- 数据库路由器（读/写分离）
- 主从连接池管理
- 路由策略实现
- 故障转移支持

参考：P2-6: 数据库读写分离未实现
"""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from wechat_backend.logging_config import db_logger
from config.config_database import DatabaseRouterConfig, db_router_config


class MasterSlaveConnectionPool:
    """
    主从数据库连接池
    
    功能：
    1. 主库连接池（写操作）
    2. 从库连接池列表（读操作）
    3. 路由策略实现
    4. 故障转移支持
    """
    
    def __init__(self):
        self._master_pool: Optional[Any] = None
        self._slave_pools: Dict[str, Any] = {}
        self._slave_status: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._route_index = 0  # 轮询索引
        self._write_timestamps: Dict[int, float] = {}  # 线程写操作时间戳
        
        # 导入连接池类（延迟导入避免循环依赖）
        self._pool_class = None
        
        db_logger.info("主从数据库连接池初始化")
    
    def _get_pool_class(self):
        """获取连接池类（延迟导入）"""
        if self._pool_class is None:
            from wechat_backend.database_connection_pool import DatabaseConnectionPool
            self._pool_class = DatabaseConnectionPool
        return self._pool_class
    
    def initialize(self):
        """初始化主从连接池"""
        if not db_router_config.is_read_write_splitting_enabled():
            db_logger.info("读写分离未启用，使用默认数据库配置")
            return
        
        try:
            DatabaseConnectionPool = self._get_pool_class()
            
            # 初始化主库连接池
            master_path = db_router_config.get_master_db_path()
            self._master_pool = DatabaseConnectionPool(
                max_connections=db_router_config.MASTER_DB_MAX_CONNECTIONS
            )
            db_logger.info(f"主数据库连接池初始化：{master_path}")
            
            # 初始化从库连接池
            slave_paths = db_router_config.get_slave_db_paths()
            for slave_path in slave_paths:
                path_str = str(slave_path)
                self._slave_pools[path_str] = DatabaseConnectionPool(
                    max_connections=db_router_config.SLAVE_DB_MAX_CONNECTIONS
                )
                self._slave_status[path_str] = {
                    'is_healthy': True,
                    'last_check': time.time(),
                    'failure_count': 0,
                    'last_failure': None,
                    'replication_lag': 0.0,
                }
                db_logger.info(f"从数据库连接池初始化：{slave_path}")
            
            # 启动健康检查线程
            self._start_health_check()
            
        except Exception as e:
            db_logger.error(f"主从数据库连接池初始化失败：{e}")
            raise
    
    def get_master_connection(self, timeout: float = None) -> sqlite3.Connection:
        """
        获取主库连接（用于写操作）
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            主库连接
        """
        if timeout is None:
            timeout = db_router_config.MASTER_DB_TIMEOUT
        
        if not self._master_pool:
            # 未启用读写分离，使用默认连接
            from wechat_backend.database_connection_pool import get_db_pool
            return get_db_pool().get_connection(timeout)
        
        return self._master_pool.get_connection(timeout)
    
    def get_slave_connection(self, timeout: float = None) -> sqlite3.Connection:
        """
        获取从库连接（用于读操作）
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            从库连接
        """
        if timeout is None:
            timeout = db_router_config.SLAVE_DB_TIMEOUT
        
        if not self._slave_pools:
            # 未启用读写分离，使用默认连接
            from wechat_backend.database_connection_pool import get_db_pool
            return get_db_pool().get_connection(timeout)
        
        # 根据路由策略选择从库
        slave_path = self._select_slave()
        
        if slave_path and slave_path in self._slave_pools:
            return self._slave_pools[slave_path].get_connection(timeout)
        
        # 所有从库不可用，回退到主库
        db_logger.warning("所有从库不可用，回退到主库")
        return self.get_master_connection(timeout)
    
    def _select_slave(self) -> Optional[str]:
        """
        根据路由策略选择从库
        
        Returns:
            选中的从库路径
        """
        available_slaves = db_router_config.get_available_slaves()
        
        if not available_slaves:
            return None
        
        strategy = db_router_config.ROUTE_STRATEGY
        
        if strategy == 'round_robin':
            return self._select_round_robin(available_slaves)
        elif strategy == 'random':
            return self._select_random(available_slaves)
        elif strategy == 'least_connections':
            return self._select_least_connections(available_slaves)
        elif strategy == 'priority':
            return self._select_priority(available_slaves)
        else:
            return self._select_round_robin(available_slaves)
    
    def _select_round_robin(self, slaves: List[Path]) -> str:
        """轮询策略"""
        with self._lock:
            slave_paths = [str(s) for s in slaves]
            selected = slave_paths[self._route_index % len(slave_paths)]
            self._route_index += 1
            return selected
    
    def _select_random(self, slaves: List[Path]) -> str:
        """随机策略"""
        import random
        return str(random.choice(slaves))
    
    def _select_least_connections(self, slaves: List[Path]) -> str:
        """最少连接数策略"""
        min_connections = float('inf')
        selected = None
        
        for slave in slaves:
            path_str = str(slave)
            if path_str in self._slave_pools:
                metrics = self._slave_pools[path_str].get_metrics()
                active = metrics.get('active_connections', 0)
                if active < min_connections:
                    min_connections = active
                    selected = path_str
        
        return selected or str(slaves[0])
    
    def _select_priority(self, slaves: List[Path]) -> str:
        """优先级策略"""
        priorities = db_router_config.SLAVE_PRIORITY
        
        if priorities:
            for priority_path in priorities:
                for slave in slaves:
                    if str(slave) == priority_path.strip():
                        return str(slave)
        
        # 未找到匹配的优先级，返回第一个
        return str(slaves[0])
    
    def return_master_connection(self, conn: sqlite3.Connection):
        """归还主库连接"""
        if self._master_pool:
            self._master_pool.return_connection(conn)
        else:
            from wechat_backend.database_connection_pool import get_db_pool
            get_db_pool().return_connection(conn)
    
    def return_slave_connection(self, conn: sqlite3.Connection):
        """归还从库连接"""
        # 找到连接所属的从库池
        for path_str, pool in self._slave_pools.items():
            try:
                pool.return_connection(conn)
                return
            except:
                continue
        
        # 未找到匹配的从库池，归还到默认池
        from wechat_backend.database_connection_pool import get_db_pool
        get_db_pool().return_connection(conn)
    
    def mark_write_operation(self, thread_id: int = None):
        """
        标记写操作完成（用于写后读一致性）
        
        Args:
            thread_id: 线程 ID（默认为当前线程）
        """
        if thread_id is None:
            thread_id = threading.get_ident()
        
        with self._lock:
            self._write_timestamps[thread_id] = time.time()
    
    def should_read_from_master(self, thread_id: int = None) -> bool:
        """
        检查是否应该从主库读取（写后读一致性）
        
        Args:
            thread_id: 线程 ID（默认为当前线程）
            
        Returns:
            bool: 是否应该从主库读取
        """
        if not db_router_config.READ_AFTER_WRITE_FROM_MASTER:
            return False
        
        if thread_id is None:
            thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id in self._write_timestamps:
                write_time = self._write_timestamps[thread_id]
                elapsed = time.time() - write_time
                
                # 在时间窗口内，从主库读取
                if elapsed < db_router_config.READ_AFTER_WRITE_WINDOW:
                    return True
                
                # 超出时间窗口，清理记录
                del self._write_timestamps[thread_id]
        
        return False
    
    def _start_health_check(self):
        """启动健康检查线程"""
        def health_check_loop():
            while True:
                time.sleep(db_router_config.SLAVE_HEALTH_CHECK_INTERVAL)
                self._check_slave_health()
        
        thread = threading.Thread(target=health_check_loop, daemon=True)
        thread.start()
        db_logger.info("从库健康检查线程已启动")
    
    def _check_slave_health(self):
        """检查从库健康状态"""
        for path_str, pool in list(self._slave_pools.items()):
            try:
                # 尝试获取连接进行健康检查
                conn = pool.get_connection(timeout=5.0)
                try:
                    # 执行简单查询检查数据库是否可用
                    conn.execute("SELECT 1")
                    
                    # 健康状态恢复
                    if self._slave_status[path_str]['failure_count'] > 0:
                        db_logger.info(f"从库恢复健康：{path_str}")
                    
                    self._slave_status[path_str].update({
                        'is_healthy': True,
                        'last_check': time.time(),
                        'failure_count': 0,
                    })
                finally:
                    pool.return_connection(conn)
                    
            except Exception as e:
                # 健康检查失败
                status = self._slave_status[path_str]
                status['failure_count'] += 1
                status['last_failure'] = str(e)
                status['last_check'] = time.time()
                
                if status['failure_count'] >= db_router_config.SLAVE_FAILURE_THRESHOLD:
                    status['is_healthy'] = False
                    db_logger.warning(f"从库标记为不可用：{path_str} (失败{status['failure_count']}次)")
    
    def get_slave_status(self, path: str = None) -> Dict[str, Any]:
        """
        获取从库状态
        
        Args:
            path: 从库路径（可选）
            
        Returns:
            从库状态字典
        """
        if path:
            return self._slave_status.get(path, {})
        
        return self._slave_status.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取连接池监控指标"""
        metrics = {
            'master': self._master_pool.get_metrics() if self._master_pool else {},
            'slaves': {},
            'route_index': self._route_index,
            'write_timestamps_count': len(self._write_timestamps),
        }
        
        for path_str, pool in self._slave_pools.items():
            metrics['slaves'][path_str] = pool.get_metrics()
        
        return metrics
    
    def close_all(self):
        """关闭所有连接池"""
        if self._master_pool:
            self._master_pool.close_all()
        
        for pool in self._slave_pools.values():
            pool.close_all()
        
        db_logger.info("主从数据库连接池已关闭")


# 全局主从连接池实例
_master_slave_pool: Optional[MasterSlaveConnectionPool] = None


def get_master_slave_pool() -> MasterSlaveConnectionPool:
    """获取主从连接池实例"""
    global _master_slave_pool
    
    if _master_slave_pool is None:
        _master_slave_pool = MasterSlaveConnectionPool()
        _master_slave_pool.initialize()
    
    return _master_slave_pool


def get_master_connection(timeout: float = None) -> sqlite3.Connection:
    """获取主库连接"""
    return get_master_slave_pool().get_master_connection(timeout)


def get_slave_connection(timeout: float = None) -> sqlite3.Connection:
    """获取从库连接"""
    return get_master_slave_pool().get_slave_connection(timeout)


def return_master_connection(conn: sqlite3.Connection):
    """归还主库连接"""
    get_master_slave_pool().return_master_connection(conn)


def return_slave_connection(conn: sqlite3.Connection):
    """归还从库连接"""
    get_master_slave_pool().return_slave_connection(conn)


def get_db_connection(operation_type: str = 'read') -> sqlite3.Connection:
    """
    根据操作类型获取数据库连接
    
    Args:
        operation_type: 操作类型 ('read' 或 'write')
        
    Returns:
        数据库连接
    """
    if operation_type == 'write':
        conn = get_master_connection()
        # 标记写操作
        get_master_slave_pool().mark_write_operation()
        return conn
    else:
        # 检查是否应该从主库读取（写后读一致性）
        if get_master_slave_pool().should_read_from_master():
            return get_master_connection()
        return get_slave_connection()


def return_db_connection(conn: sqlite3.Connection, operation_type: str = 'read'):
    """
    归还数据库连接
    
    Args:
        conn: 数据库连接
        operation_type: 操作类型 ('read' 或 'write')
    """
    if operation_type == 'write':
        return_master_connection(conn)
    else:
        return_slave_connection(conn)


def get_slave_status(slave_path: Path = None) -> Optional[Dict[str, Any]]:
    """
    获取从库状态（供 config_database 模块使用）
    
    Args:
        slave_path: 从库路径
        
    Returns:
        从库状态字典
    """
    global _master_slave_pool
    
    if _master_slave_pool is None:
        return None
    
    if slave_path:
        return _master_slave_pool.get_slave_status(str(slave_path))
    
    return _master_slave_pool.get_slave_status()
