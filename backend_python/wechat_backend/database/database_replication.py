"""
主从数据库同步机制

功能：
- 数据库文件复制
- WAL 模式同步
- 触发器同步
- 定期同步任务

参考：P2-6: 数据库读写分离未实现
"""

import sqlite3
import shutil
import os
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from wechat_backend.logging_config import db_logger
from config.config_database import db_router_config


class DatabaseReplicationManager:
    """
    数据库复制管理器
    
    功能：
    1. 全量复制（初始同步）
    2. 增量复制（WAL 同步）
    3. 触发器同步
    4. 复制延迟监控
    """
    
    def __init__(self, master_path: Path, slave_paths: List[Path]):
        self.master_path = master_path
        self.slave_paths = slave_paths
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._last_sync_time: Dict[str, float] = {}
        self._replication_lag: Dict[str, float] = {}
        
        db_logger.info(f"数据库复制管理器初始化：主库={master_path}, 从库={slave_paths}")
    
    def initialize_slaves(self):
        """
        初始化从库（全量复制）
        
        对所有从库进行初始全量复制
        """
        for slave_path in self.slave_paths:
            try:
                self._full_copy(slave_path)
                db_logger.info(f"从库初始化完成：{slave_path}")
            except Exception as e:
                db_logger.error(f"从库初始化失败：{slave_path}, 错误：{e}")
    
    def _full_copy(self, slave_path: Path):
        """
        全量复制主库到从库
        
        Args:
            slave_path: 从库路径
        """
        # 确保目标目录存在
        slave_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果从库已存在，先删除
        if slave_path.exists():
            # 关闭 WAL 文件
            wal_path = slave_path.with_suffix(slave_path.suffix + '-wal')
            shm_path = slave_path.with_suffix(slave_path.suffix + '-shm')
            
            if wal_path.exists():
                wal_path.unlink()
            if shm_path.exists():
                shm_path.unlink()
            
            slave_path.unlink()
        
        # 复制数据库文件
        shutil.copy2(self.master_path, slave_path)
        
        # 配置从库为 WAL 只读模式
        conn = sqlite3.connect(str(slave_path))
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA locking_mode=NORMAL')
            
            # 设置只读（可选，取决于使用场景）
            # conn.execute('PRAGMA query_only=ON')
            
            conn.commit()
        finally:
            conn.close()
        
        db_logger.info(f"全量复制完成：{self.master_path} -> {slave_path}")
    
    def _incremental_sync(self, slave_path: Path):
        """
        增量同步（通过 WAL 文件）
        
        Args:
            slave_path: 从库路径
        """
        master_wal = self.master_path.with_suffix(self.master_path.suffix + '-wal')
        slave_wal = slave_path.with_suffix(slave_path.suffix + '-wal')
        
        # 如果主库 WAL 文件存在且大小大于从库 WAL 文件
        if master_wal.exists():
            master_wal_size = master_wal.stat().st_size
            
            slave_wal_size = 0
            if slave_wal.exists():
                slave_wal_size = slave_wal.stat().st_size
            
            if master_wal_size > slave_wal_size:
                # 复制 WAL 文件
                shutil.copy2(master_wal, slave_wal)
                
                # 记录同步时间
                self._last_sync_time[str(slave_path)] = time.time()
                
                # 计算复制延迟
                self._replication_lag[str(slave_path)] = master_wal_size - slave_wal_size
                
                db_logger.debug(f"WAL 同步完成：{slave_path} (WAL 大小：{master_wal_size} bytes)")
    
    def sync_all_slaves(self):
        """同步所有从库"""
        for slave_path in self.slave_paths:
            try:
                self._incremental_sync(slave_path)
            except Exception as e:
                db_logger.error(f"从库同步失败：{slave_path}, 错误：{e}")
    
    def get_replication_lag(self, slave_path: Path) -> float:
        """
        获取复制延迟（字节数）
        
        Args:
            slave_path: 从库路径
            
        Returns:
            复制延迟（字节数）
        """
        return self._replication_lag.get(str(slave_path), 0.0)
    
    def get_last_sync_time(self, slave_path: Path) -> float:
        """
        获取最后同步时间
        
        Args:
            slave_path: 从库路径
            
        Returns:
            最后同步时间戳
        """
        return self._last_sync_time.get(str(slave_path), 0.0)
    
    def start_background_sync(self, interval: int = None):
        """
        启动后台同步线程
        
        Args:
            interval: 同步间隔（秒）
        """
        if interval is None:
            interval = db_router_config.REPLICATION_LAG_CHECK_INTERVAL
        
        self._running = True
        
        def sync_loop():
            db_logger.info("后台同步线程已启动")
            while self._running:
                try:
                    self.sync_all_slaves()
                except Exception as e:
                    db_logger.error(f"后台同步失败：{e}")
                
                time.sleep(interval)
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
    
    def stop_background_sync(self):
        """停止后台同步线程"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)
            db_logger.info("后台同步线程已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取复制状态
        
        Returns:
            复制状态字典
        """
        status = {
            'master_path': str(self.master_path),
            'slaves': [],
            'is_running': self._running,
        }
        
        for slave_path in self.slave_paths:
            path_str = str(slave_path)
            slave_status = {
                'path': path_str,
                'exists': slave_path.exists(),
                'last_sync': self._last_sync_time.get(path_str, 0),
                'replication_lag_bytes': self._replication_lag.get(path_str, 0),
                'wal_exists': slave_path.with_suffix(slave_path.suffix + '-wal').exists(),
            }
            status['slaves'].append(slave_status)
        
        return status


# 全局复制管理器实例
_replication_manager: Optional[DatabaseReplicationManager] = None


def get_replication_manager() -> Optional[DatabaseReplicationManager]:
    """获取复制管理器实例"""
    global _replication_manager
    
    if _replication_manager is None and db_router_config.is_read_write_splitting_enabled():
        master_path = db_router_config.get_master_db_path()
        slave_paths = db_router_config.get_slave_db_paths()
        
        if slave_paths:
            _replication_manager = DatabaseReplicationManager(master_path, slave_paths)
    
    return _replication_manager


def initialize_replication():
    """初始化数据库复制"""
    manager = get_replication_manager()
    
    if manager:
        try:
            # 初始化从库（全量复制）
            manager.initialize_slaves()
            
            # 启动后台同步
            manager.start_background_sync()
            
            db_logger.info("数据库复制初始化完成")
            return True
        except Exception as e:
            db_logger.error(f"数据库复制初始化失败：{e}")
            return False
    
    return False


def stop_replication():
    """停止数据库复制"""
    manager = get_replication_manager()
    
    if manager:
        manager.stop_background_sync()
        db_logger.info("数据库复制已停止")


def get_replication_status() -> Dict[str, Any]:
    """获取复制状态"""
    manager = get_replication_manager()
    
    if manager:
        return manager.get_status()
    
    return {
        'enabled': False,
        'message': '读写分离未启用'
    }


def sync_slave(slave_path: Path) -> bool:
    """
    手动同步单个从库
    
    Args:
        slave_path: 从库路径
        
    Returns:
        bool: 是否成功
    """
    manager = get_replication_manager()
    
    if not manager:
        return False
    
    try:
        manager._incremental_sync(slave_path)
        return True
    except Exception as e:
        db_logger.error(f"从库同步失败：{slave_path}, 错误：{e}")
        return False


def full_sync_slave(slave_path: Path) -> bool:
    """
    全量同步单个从库
    
    Args:
        slave_path: 从库路径
        
    Returns:
        bool: 是否成功
    """
    manager = get_replication_manager()
    
    if not manager:
        return False
    
    try:
        manager._full_copy(slave_path)
        return True
    except Exception as e:
        db_logger.error(f"从库全量同步失败：{slave_path}, 错误：{e}")
        return False
