"""
数据库读写分离配置模块

功能：
- 主从数据库配置
- 数据库路由策略
- 读写分离开关
- 复制延迟监控配置

参考：P2-6: 数据库读写分离未实现
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any


class DatabaseRouterConfig:
    """数据库路由配置类"""
    
    # ==================== 读写分离基础配置 ====================
    
    # 是否启用读写分离
    READ_WRITE_SPLITTING_ENABLED = os.environ.get('READ_WRITE_SPLITTING_ENABLED', 'false').lower() == 'true'
    
    # ==================== 主数据库配置（写操作） ====================
    
    # 主数据库路径
    MASTER_DB_PATH = os.environ.get('MASTER_DB_PATH', '')
    
    # 主数据库最大连接数
    MASTER_DB_MAX_CONNECTIONS = int(os.environ.get('MASTER_DB_MAX_CONNECTIONS', '5'))
    
    # 主数据库超时时间（秒）
    MASTER_DB_TIMEOUT = float(os.environ.get('MASTER_DB_TIMEOUT', '30.0'))
    
    # ==================== 从数据库配置（读操作） ====================
    
    # 从数据库路径列表（支持多个从库）
    SLAVE_DB_PATHS = os.environ.get('SLAVE_DB_PATHS', '').split(',') if os.environ.get('SLAVE_DB_PATHS') else []
    
    # 从数据库最大连接数（每个从库）
    SLAVE_DB_MAX_CONNECTIONS = int(os.environ.get('SLAVE_DB_MAX_CONNECTIONS', '10'))
    
    # 从数据库超时时间（秒）
    SLAVE_DB_TIMEOUT = float(os.environ.get('SLAVE_DB_TIMEOUT', '30.0'))
    
    # ==================== 路由策略配置 ====================
    
    # 路由策略（round_robin, random, least_connections, priority）
    ROUTE_STRATEGY = os.environ.get('ROUTE_STRATEGY', 'round_robin')
    
    # 从库优先级列表（用于 priority 策略）
    SLAVE_PRIORITY = os.environ.get('SLAVE_PRIORITY', '').split(',') if os.environ.get('SLAVE_PRIORITY') else []
    
    # ==================== 复制监控配置 ====================
    
    # 复制延迟检查间隔（秒）
    REPLICATION_LAG_CHECK_INTERVAL = int(os.environ.get('REPLICATION_LAG_CHECK_INTERVAL', '60'))
    
    # 最大允许复制延迟（秒）
    MAX_REPLICATION_LAG = float(os.environ.get('MAX_REPLICATION_LAG', '5.0'))
    
    # 复制延迟告警阈值（秒）
    REPLICATION_LAG_ALERT_THRESHOLD = float(os.environ.get('REPLICATION_LAG_ALERT_THRESHOLD', '10.0'))
    
    # ==================== 故障转移配置 ====================
    
    # 是否启用故障转移
    FAILOVER_ENABLED = os.environ.get('FAILOVER_ENABLED', 'true').lower() == 'true'
    
    # 从库健康检查间隔（秒）
    SLAVE_HEALTH_CHECK_INTERVAL = int(os.environ.get('SLAVE_HEALTH_CHECK_INTERVAL', '30'))
    
    # 连续失败次数阈值（超过则标记为不可用）
    SLAVE_FAILURE_THRESHOLD = int(os.environ.get('SLAVE_FAILURE_THRESHOLD', '3'))
    
    # 从库恢复检查间隔（秒）
    SLAVE_RECOVERY_CHECK_INTERVAL = int(os.environ.get('SLAVE_RECOVERY_CHECK_INTERVAL', '60'))
    
    # ==================== 写操作读回配置 ====================
    
    # 写操作后是否立即从主库读取（保证一致性）
    READ_AFTER_WRITE_FROM_MASTER = os.environ.get('READ_AFTER_WRITE_FROM_MASTER', 'true').lower() == 'true'
    
    # 写操作后从主库读取的时间窗口（秒）
    READ_AFTER_WRITE_WINDOW = float(os.environ.get('READ_AFTER_WRITE_WINDOW', '5.0'))
    
    # ==================== 默认数据库路径（兼容模式） ====================
    
    # 默认数据库路径（未配置主从时使用）
    DEFAULT_DB_PATH = os.environ.get('DEFAULT_DB_PATH', '')
    
    # 默认数据库最大连接数
    DEFAULT_DB_MAX_CONNECTIONS = int(os.environ.get('DEFAULT_DB_MAX_CONNECTIONS', '10'))
    
    # ==================== 工具方法 ====================
    
    @classmethod
    def get_master_db_path(cls) -> Path:
        """
        获取主数据库路径
        
        Returns:
            主数据库路径，如果未配置则返回默认数据库路径
        """
        if cls.MASTER_DB_PATH:
            return Path(cls.MASTER_DB_PATH)
        
        # 未配置主库，使用默认数据库路径
        if cls.DEFAULT_DB_PATH:
            return Path(cls.DEFAULT_DB_PATH)
        
        # 使用默认位置
        return Path(__file__).parent.parent / 'database.db'
    
    @classmethod
    def get_slave_db_paths(cls) -> List[Path]:
        """
        获取从数据库路径列表
        
        Returns:
            从数据库路径列表
        """
        if cls.SLAVE_DB_PATHS and cls.SLAVE_DB_PATHS[0]:
            return [Path(p.strip()) for p in cls.SLAVE_DB_PATHS]
        
        # 未配置从库，返回空列表
        return []
    
    @classmethod
    def is_read_write_splitting_enabled(cls) -> bool:
        """
        检查是否启用了读写分离
        
        Returns:
            bool: 是否启用
        """
        return cls.READ_WRITE_SPLITTING_ENABLED and (cls.MASTER_DB_PATH or cls.DEFAULT_DB_PATH)
    
    @classmethod
    def is_failover_enabled(cls) -> bool:
        """
        检查是否启用了故障转移
        
        Returns:
            bool: 是否启用
        """
        return cls.FAILOVER_ENABLED
    
    @classmethod
    def get_available_slaves(cls) -> List[Path]:
        """
        获取可用的从数据库路径（排除不可用的）
        
        Returns:
            可用的从数据库路径列表
        """
        from wechat_backend.database.database_replication import get_slave_status
        
        if not cls.is_read_write_splitting_enabled():
            return []
        
        all_slaves = cls.get_slave_db_paths()
        available_slaves = []
        
        for slave_path in all_slaves:
            status = get_slave_status(slave_path)
            if status and status.get('is_healthy', False):
                available_slaves.append(slave_path)
        
        return available_slaves if available_slaves else all_slaves
    
    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """
        验证数据库配置是否完整
        
        Returns:
            (是否有效，错误信息列表)
        """
        errors = []
        
        if cls.is_read_write_splitting_enabled():
            # 检查主库配置
            if not cls.MASTER_DB_PATH and not cls.DEFAULT_DB_PATH:
                errors.append('MASTER_DB_PATH 或 DEFAULT_DB_PATH 未配置')
            
            # 检查从库配置
            if not cls.SLAVE_DB_PATHS or not cls.SLAVE_DB_PATHS[0]:
                errors.append('SLAVE_DB_PATHS 未配置（读写分离模式下至少需要一个从库）')
            else:
                # 验证从库路径是否存在
                for slave_path in cls.get_slave_db_paths():
                    if not slave_path.exists():
                        errors.append(f'从数据库路径不存在：{slave_path}')
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            配置摘要字典
        """
        return {
            'read_write_splitting_enabled': cls.is_read_write_splitting_enabled(),
            'master_db_path': str(cls.get_master_db_path()),
            'slave_db_paths': [str(p) for p in cls.get_slave_db_paths()],
            'master_max_connections': cls.MASTER_DB_MAX_CONNECTIONS,
            'slave_max_connections': cls.SLAVE_DB_MAX_CONNECTIONS,
            'route_strategy': cls.ROUTE_STRATEGY,
            'failover_enabled': cls.is_failover_enabled(),
            'replication_lag_check_interval': cls.REPLICATION_LAG_CHECK_INTERVAL,
            'max_replication_lag': cls.MAX_REPLICATION_LAG,
            'read_after_write_from_master': cls.READ_AFTER_WRITE_FROM_MASTER,
            'read_after_write_window': cls.READ_AFTER_WRITE_WINDOW,
        }


# 导出配置实例
db_router_config = DatabaseRouterConfig()
