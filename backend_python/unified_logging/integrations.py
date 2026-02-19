"""
外部服务集成模块

提供与外部监控和日志服务的集成，包括:
- Sentry 错误追踪
- ELK (Elasticsearch/Logstash/Kibana) 日志聚合
- Prometheus 指标导出

使用示例:
    from backend_python.unified_logging.integrations import (
        SentryIntegration,
        ELKIntegration,
        PrometheusIntegration,
        ExternalServicesManager,
    )
    
    # 方式 1: 单独配置
    sentry = SentryIntegration(
        dsn="https://xxx@sentry.io/123",
        environment="production",
    )
    sentry.init()
    
    # 方式 2: 统一管理
    manager = ExternalServicesManager()
    manager.configure_from_config({
        'sentry': {'dsn': '...', 'environment': 'production'},
        'elk': {'endpoint': '...', 'index': 'logs'},
        'prometheus': {'port': 9090},
    })
    manager.start()
"""

import os
import sys
import json
import time
import threading
import logging
import socket
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import traceback as tb_module

# 可选依赖
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False
    sentry_sdk = None

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
    _ELASTICSEARCH_AVAILABLE = True
except ImportError:
    _ELASTICSEARCH_AVAILABLE = False
    Elasticsearch = None

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Summary,
        start_http_server,
        CollectorRegistry,
        REGISTRY,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    Counter = None
    Gauge = None
    Histogram = None


# ============================================================================
# 枚举和常量
# ============================================================================

class IntegrationStatus(Enum):
    """集成状态"""
    DISABLED = "disabled"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class IntegrationConfig:
    """集成配置基类"""
    enabled: bool = True
    environment: str = "production"
    service_name: str = "wechat_backend"
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'environment': self.environment,
            'service_name': self.service_name,
            'tags': self.tags,
        }


# ============================================================================
# Sentry 错误追踪集成
# ============================================================================

class SentryIntegration:
    """
    Sentry 错误追踪集成
    
    功能:
    - 自动捕获异常
    - 记录 breadcrumbs
    - 用户上下文追踪
    - 性能监控
    
    使用示例:
        sentry = SentryIntegration(
            dsn="https://xxx@sentry.io/123",
            environment="production",
            sample_rate=0.1,
        )
        sentry.init()
        
        # 记录用户上下文
        sentry.set_user(user_id="123", email="user@example.com")
        
        # 记录 breadcrumbs
        sentry.add_breadcrumb("User clicked button", category="ui")
    """
    
    def __init__(
        self,
        dsn: str = None,
        environment: str = "production",
        service_name: str = "wechat_backend",
        sample_rate: float = 1.0,
        traces_sample_rate: float = 0.1,
        release: str = None,
        tags: Dict[str, str] = None,
        before_send: Callable = None,
    ):
        """
        初始化 Sentry 集成
        
        Args:
            dsn: Sentry DSN
            environment: 环境名称
            service_name: 服务名称
            sample_rate: 错误采样率
            traces_sample_rate: 性能追踪采样率
            release: 发布版本
            tags: 默认标签
            before_send: 发送前回调
        """
        self.dsn = dsn or os.environ.get('SENTRY_DSN')
        self.environment = environment
        self.service_name = service_name
        self.sample_rate = sample_rate
        self.traces_sample_rate = traces_sample_rate
        self.release = release or os.environ.get('VERSION', 'unknown')
        self.tags = tags or {}
        self.before_send = before_send
        
        self._status = IntegrationStatus.DISABLED
        self._logger = logging.getLogger(__name__)
    
    @property
    def status(self) -> IntegrationStatus:
        return self._status
    
    def init(self) -> bool:
        """初始化 Sentry SDK"""
        if not _SENTRY_AVAILABLE:
            self._logger.warning("Sentry SDK not installed, skipping initialization")
            self._status = IntegrationStatus.DISABLED
            return False
        
        if not self.dsn:
            self._logger.warning("Sentry DSN not configured, skipping initialization")
            self._status = IntegrationStatus.DISABLED
            return False
        
        try:
            # 配置日志集成
            logging_integration = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            )
            
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                release=self.release,
                sample_rate=self.sample_rate,
                traces_sample_rate=self.traces_sample_rate,
                integrations=[logging_integration],
                before_send=self.before_send,
            )
            
            # 设置默认标签
            sentry_sdk.set_tag("service", self.service_name)
            for key, value in self.tags.items():
                sentry_sdk.set_tag(key, value)
            
            self._status = IntegrationStatus.CONNECTED
            self._logger.info(f"Sentry initialized for {self.service_name} ({self.environment})")
            return True
            
        except Exception as e:
            self._logger.error(f"Sentry initialization failed: {e}")
            self._status = IntegrationStatus.ERROR
            return False
    
    def capture_exception(self, exception: Exception = None, **kwargs):
        """捕获异常"""
        if self._status != IntegrationStatus.CONNECTED:
            return
        
        sentry_sdk.capture_exception(exception, **kwargs)
    
    def capture_message(self, message: str, level: str = "info", **kwargs):
        """捕获消息"""
        if self._status != IntegrationStatus.CONNECTED:
            return
        
        sentry_sdk.capture_message(message, level=level, **kwargs)
    
    def add_breadcrumb(
        self,
        message: str,
        category: str = "default",
        level: str = "info",
        data: Dict[str, Any] = None,
    ):
        """添加 breadcrumb"""
        if self._status != IntegrationStatus.CONNECTED:
            return
        
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    
    def set_user(self, user_id: str = None, email: str = None, username: str = None, **kwargs):
        """设置用户上下文"""
        if self._status != IntegrationStatus.CONNECTED:
            return
        
        user_data = {'id': user_id, 'email': email, 'username': username, **kwargs}
        sentry_sdk.set_user({k: v for k, v in user_data.items() if v is not None})
    
    def set_tag(self, key: str, value: str):
        """设置标签"""
        if self._status != IntegrationStatus.CONNECTED:
            return
        
        sentry_sdk.set_tag(key, value)
    
    def start_transaction(self, name: str, op: str = "function"):
        """开始事务"""
        if self._status != IntegrationStatus.CONNECTED:
            return None
        
        return sentry_sdk.start_transaction(name=name, op=op)
    
    def shutdown(self, timeout: float = 5.0):
        """关闭 Sentry"""
        if _SENTRY_AVAILABLE and self._status == IntegrationStatus.CONNECTED:
            sentry_sdk.flush(timeout=timeout)
            self._status = IntegrationStatus.DISABLED


# ============================================================================
# ELK 日志聚合集成
# ============================================================================

class ELKIntegration:
    """
    ELK (Elasticsearch) 日志聚合集成
    
    功能:
    - 批量发送日志到 Elasticsearch
    - 自动索引管理
    - 异步发送
    
    使用示例:
        elk = ELKIntegration(
            hosts=["http://localhost:9200"],
            index_prefix="wechat-logs",
            bulk_size=100,
            flush_interval=10,
        )
        elk.init()
        
        elk.send_log({
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "User logged in",
            "user_id": "123",
        })
    """
    
    def __init__(
        self,
        hosts: List[str] = None,
        index_prefix: str = "logs",
        bulk_size: int = 100,
        flush_interval: float = 10.0,
        username: str = None,
        password: str = None,
        environment: str = "production",
        service_name: str = "wechat_backend",
    ):
        """
        初始化 ELK 集成
        
        Args:
            hosts: Elasticsearch 主机列表
            index_prefix: 索引前缀
            bulk_size: 批量发送大小
            flush_interval: 刷新间隔 (秒)
            username: 用户名
            password: 密码
            environment: 环境
            service_name: 服务名称
        """
        self.hosts = hosts or os.environ.get('ELASTICSEARCH_HOSTS', 'http://localhost:9200').split(',')
        self.index_prefix = index_prefix
        self.bulk_size = bulk_size
        self.flush_interval = flush_interval
        self.username = username or os.environ.get('ELASTICSEARCH_USERNAME')
        self.password = password or os.environ.get('ELASTICSEARCH_PASSWORD')
        self.environment = environment
        self.service_name = service_name
        
        self._client: Optional[Elasticsearch] = None
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._status = IntegrationStatus.DISABLED
        self._logger = logging.getLogger(__name__)
        self._stats = {
            'sent': 0,
            'failed': 0,
            'dropped': 0,
        }
    
    @property
    def status(self) -> IntegrationStatus:
        return self._status
    
    def init(self) -> bool:
        """初始化 Elasticsearch 客户端"""
        if not _ELASTICSEARCH_AVAILABLE:
            self._logger.warning("Elasticsearch SDK not installed, skipping initialization")
            self._status = IntegrationStatus.DISABLED
            return False
        
        try:
            # 创建客户端
            auth_kwargs = {}
            if self.username and self.password:
                auth_kwargs = {'basic_auth': (self.username, self.password)}
            
            self._client = Elasticsearch(
                hosts=self.hosts,
                **auth_kwargs,
            )
            
            # 测试连接
            info = self._client.info()
            self._logger.info(f"Connected to Elasticsearch {info['version']['number']}")
            
            # 启动刷新线程
            self._start_flush_thread()
            
            self._status = IntegrationStatus.CONNECTED
            return True
            
        except Exception as e:
            self._logger.error(f"Elasticsearch initialization failed: {e}")
            self._status = IntegrationStatus.ERROR
            return False
    
    def _start_flush_thread(self):
        """启动刷新线程"""
        self._stop_event.clear()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def _flush_loop(self):
        """刷新循环"""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.flush_interval)
            self.flush()
    
    def send_log(self, log_data: Dict[str, Any], index: str = None):
        """
        发送日志
        
        Args:
            log_data: 日志数据
            index: 索引名称 (可选)
        """
        if self._status != IntegrationStatus.CONNECTED:
            return
        
        # 添加元数据
        enriched_data = {
            '@timestamp': datetime.now(timezone.utc).isoformat(),
            'environment': self.environment,
            'service': self.service_name,
            'hostname': socket.gethostname(),
            **log_data,
        }
        
        with self._lock:
            self._buffer.append(enriched_data)
            
            # 达到批量大小则刷新
            if len(self._buffer) >= self.bulk_size:
                self._flush_async()
    
    def flush(self):
        """刷新缓冲区"""
        with self._lock:
            if self._buffer:
                self._flush_async()
    
    def _flush_async(self):
        """异步刷新"""
        if not self._buffer:
            return
        
        # 复制缓冲区
        buffer = self._buffer.copy()
        self._buffer.clear()
        
        try:
            # 生成索引名称
            index = self._get_index_name()
            
            # 批量发送
            actions = [
                {
                    '_index': index,
                    '_source': doc,
                }
                for doc in buffer
            ]
            
            success, failed = bulk(self._client, actions, raise_on_error=False)
            
            self._stats['sent'] += success
            self._stats['failed'] += failed
            
            if failed > 0:
                self._logger.warning(f"Elasticsearch bulk send: {success} sent, {failed} failed")
                
        except Exception as e:
            self._logger.error(f"Elasticsearch flush failed: {e}")
            self._stats['failed'] += len(buffer)
    
    def _get_index_name(self) -> str:
        """生成索引名称"""
        date_str = datetime.now().strftime('%Y.%m.%d')
        return f"{self.index_prefix}-{self.environment}-{date_str}"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'status': self._status.value,
            'buffer_size': len(self._buffer),
            **self._stats,
        }
    
    def shutdown(self, timeout: float = 10.0):
        """关闭连接"""
        self._stop_event.set()
        
        if self._flush_thread:
            self._flush_thread.join(timeout=timeout)
        
        # 刷新剩余数据
        self.flush()
        
        if self._client:
            self._client.close()
        
        self._status = IntegrationStatus.DISABLED


# ============================================================================
# Prometheus 指标导出器
# ============================================================================

class PrometheusIntegration:
    """
    Prometheus 指标导出集成
    
    功能:
    - Counter (计数器)
    - Gauge (仪表盘)
    - Histogram (直方图)
    - Summary (摘要)
    - HTTP 服务器
    
    使用示例:
        prom = PrometheusIntegration(port=9090)
        prom.init()
        
        # 创建指标
        request_counter = prom.create_counter(
            name="http_requests_total",
            documentation="Total HTTP requests",
            labelnames=["method", "endpoint", "status"],
        )
        
        # 记录指标
        request_counter.labels(method="POST", endpoint="/api/chat", status="200").inc()
    """
    
    def __init__(
        self,
        port: int = 9090,
        address: str = "0.0.0.0",
        environment: str = "production",
        service_name: str = "wechat_backend",
    ):
        """
        初始化 Prometheus 集成
        
        Args:
            port: HTTP 服务器端口
            address: 监听地址
            environment: 环境
            service_name: 服务名称
        """
        self.port = port
        self.address = address
        self.environment = environment
        self.service_name = service_name
        
        self._registry = None
        self._metrics: Dict[str, Any] = {}
        self._status = IntegrationStatus.DISABLED
        self._logger = logging.getLogger(__name__)
        self._server_thread: Optional[threading.Thread] = None
        
        # 只有在 SDK 可用时才初始化 registry
        if _PROMETHEUS_AVAILABLE:
            from prometheus_client import CollectorRegistry
            self._registry = CollectorRegistry()
    
    @property
    def status(self) -> IntegrationStatus:
        return self._status
    
    def init(self) -> bool:
        """初始化 Prometheus"""
        if not _PROMETHEUS_AVAILABLE:
            self._logger.warning("Prometheus client not installed, skipping initialization")
            self._status = IntegrationStatus.DISABLED
            return False
        
        try:
            # 启动 HTTP 服务器
            start_http_server(self.port, addr=self.address, registry=self._registry)
            
            # 创建默认指标
            self._create_default_metrics()
            
            self._status = IntegrationStatus.CONNECTED
            self._logger.info(f"Prometheus metrics server started on {self.address}:{self.port}")
            return True
            
        except Exception as e:
            self._logger.error(f"Prometheus initialization failed: {e}")
            self._status = IntegrationStatus.ERROR
            return False
    
    def _create_default_metrics(self):
        """创建默认指标"""
        # 系统信息
        self.create_gauge(
            name="app_info",
            documentation="Application information",
            labelnames=["service", "environment"],
        ).labels(service=self.service_name, environment=self.environment).set(1)
    
    def create_counter(
        self,
        name: str,
        documentation: str,
        labelnames: List[str] = None,
    ) -> Optional[Counter]:
        """创建 Counter"""
        if not _PROMETHEUS_AVAILABLE or self._status != IntegrationStatus.CONNECTED:
            return None
        
        if name in self._metrics:
            return self._metrics[name]
        
        counter = Counter(
            name=name,
            documentation=documentation,
            labelnames=labelnames or [],
            registry=self._registry,
        )
        
        self._metrics[name] = counter
        return counter
    
    def create_gauge(
        self,
        name: str,
        documentation: str,
        labelnames: List[str] = None,
    ) -> Optional[Gauge]:
        """创建 Gauge"""
        if not _PROMETHEUS_AVAILABLE or self._status != IntegrationStatus.CONNECTED:
            return None
        
        if name in self._metrics:
            return self._metrics[name]
        
        gauge = Gauge(
            name=name,
            documentation=documentation,
            labelnames=labelnames or [],
            registry=self._registry,
        )
        
        self._metrics[name] = gauge
        return gauge
    
    def create_histogram(
        self,
        name: str,
        documentation: str,
        labelnames: List[str] = None,
        buckets: List[float] = None,
    ) -> Optional[Histogram]:
        """创建 Histogram"""
        if not _PROMETHEUS_AVAILABLE or self._status != IntegrationStatus.CONNECTED:
            return None
        
        if name in self._metrics:
            return self._metrics[name]
        
        histogram = Histogram(
            name=name,
            documentation=documentation,
            labelnames=labelnames or [],
            buckets=buckets or Histogram.DEFAULT_BUCKETS,
            registry=self._registry,
        )
        
        self._metrics[name] = histogram
        return histogram
    
    def get_metric(self, name: str) -> Optional[Any]:
        """获取指标"""
        return self._metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return self._metrics.copy()
    
    def shutdown(self):
        """关闭 Prometheus"""
        self._status = IntegrationStatus.DISABLED


# ============================================================================
# 外部服务管理器
# ============================================================================

class ExternalServicesManager:
    """
    外部服务管理器
    
    统一管理所有外部服务集成。
    
    使用示例:
        manager = ExternalServicesManager()
        manager.configure_from_config({
            'sentry': {'dsn': '...', 'environment': 'production'},
            'elk': {'hosts': ['http://localhost:9200'], 'index_prefix': 'logs'},
            'prometheus': {'port': 9090},
        })
        manager.start()
        
        # 使用
        manager.sentry.capture_exception(e)
        manager.elk.send_log({"message": "test"})
        
        # 关闭
        manager.shutdown()
    """
    
    def __init__(self):
        self.sentry: Optional[SentryIntegration] = None
        self.elk: Optional[ELKIntegration] = None
        self.prometheus: Optional[PrometheusIntegration] = None
        
        self._status = IntegrationStatus.DISABLED
        self._logger = logging.getLogger(__name__)
    
    def configure_from_config(self, config: Dict[str, Any]):
        """从配置配置所有服务"""
        # Sentry 配置
        if config.get('sentry', {}).get('enabled', True):
            sentry_config = config.get('sentry', {})
            self.sentry = SentryIntegration(
                dsn=sentry_config.get('dsn'),
                environment=sentry_config.get('environment', 'production'),
                service_name=sentry_config.get('service_name', 'wechat_backend'),
                sample_rate=sentry_config.get('sample_rate', 1.0),
                traces_sample_rate=sentry_config.get('traces_sample_rate', 0.1),
                tags=sentry_config.get('tags', {}),
            )
        
        # ELK 配置
        if config.get('elk', {}).get('enabled', True):
            elk_config = config.get('elk', {})
            self.elk = ELKIntegration(
                hosts=elk_config.get('hosts'),
                index_prefix=elk_config.get('index_prefix', 'logs'),
                bulk_size=elk_config.get('bulk_size', 100),
                flush_interval=elk_config.get('flush_interval', 10.0),
                username=elk_config.get('username'),
                password=elk_config.get('password'),
                environment=elk_config.get('environment', 'production'),
                service_name=elk_config.get('service_name', 'wechat_backend'),
            )
        
        # Prometheus 配置
        if config.get('prometheus', {}).get('enabled', True):
            prom_config = config.get('prometheus', {})
            self.prometheus = PrometheusIntegration(
                port=prom_config.get('port', 9090),
                address=prom_config.get('address', '0.0.0.0'),
                environment=prom_config.get('environment', 'production'),
                service_name=prom_config.get('service_name', 'wechat_backend'),
            )
    
    def start(self) -> Dict[str, bool]:
        """启动所有服务"""
        results = {}
        
        # 启动 Sentry
        if self.sentry:
            results['sentry'] = self.sentry.init()
        
        # 启动 ELK
        if self.elk:
            results['elk'] = self.elk.init()
        
        # 启动 Prometheus
        if self.prometheus:
            results['prometheus'] = self.prometheus.init()
        
        # 检查是否有成功启动的
        if any(results.values()):
            self._status = IntegrationStatus.CONNECTED
        else:
            self._status = IntegrationStatus.DISABLED
        
        return results
    
    def get_status(self) -> Dict[str, str]:
        """获取所有服务状态"""
        return {
            'sentry': self.sentry.status.value if self.sentry else 'not_configured',
            'elk': self.elk.status.value if self.elk else 'not_configured',
            'prometheus': self.prometheus.status.value if self.prometheus else 'not_configured',
            'overall': self._status.value,
        }
    
    def shutdown(self, timeout: float = 10.0):
        """关闭所有服务"""
        if self.sentry:
            self.sentry.shutdown(timeout=timeout)
        
        if self.elk:
            self.elk.shutdown(timeout=timeout)
        
        if self.prometheus:
            self.prometheus.shutdown()
        
        self._status = IntegrationStatus.DISABLED


# ============================================================================
# 便捷函数
# ============================================================================

def init_sentry(dsn: str = None, **kwargs) -> Optional[SentryIntegration]:
    """便捷函数：初始化 Sentry"""
    if not dsn and not os.environ.get('SENTRY_DSN'):
        return None
    
    sentry = SentryIntegration(dsn=dsn, **kwargs)
    sentry.init()
    return sentry


def init_elk(hosts: List[str] = None, **kwargs) -> Optional[ELKIntegration]:
    """便捷函数：初始化 ELK"""
    if not hosts and not os.environ.get('ELASTICSEARCH_HOSTS'):
        return None
    
    elk = ELKIntegration(hosts=hosts, **kwargs)
    elk.init()
    return elk


def init_prometheus(port: int = 9090, **kwargs) -> Optional[PrometheusIntegration]:
    """便捷函数：初始化 Prometheus"""
    if not _PROMETHEUS_AVAILABLE:
        return None
    
    prom = PrometheusIntegration(port=port, **kwargs)
    prom.init()
    return prom


# 导出所有符号
__all__ = [
    # 集成类
    'SentryIntegration',
    'ELKIntegration',
    'PrometheusIntegration',
    'ExternalServicesManager',
    # 枚举
    'IntegrationStatus',
    'IntegrationConfig',
    # 便捷函数
    'init_sentry',
    'init_elk',
    'init_prometheus',
    # 常量
    '_SENTRY_AVAILABLE',
    '_ELASTICSEARCH_AVAILABLE',
    '_PROMETHEUS_AVAILABLE',
]
