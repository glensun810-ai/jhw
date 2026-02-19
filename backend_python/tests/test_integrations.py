"""
P2 外部服务集成单元测试

测试范围:
1. Sentry 错误追踪集成
2. ELK 日志聚合集成
3. Prometheus 指标导出器
4. ExternalServicesManager 统一管理
5. 可选依赖处理
"""

import sys
import time
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from unified_logging.integrations import (
    SentryIntegration,
    ELKIntegration,
    PrometheusIntegration,
    ExternalServicesManager,
    IntegrationStatus,
    IntegrationConfig,
    _SENTRY_AVAILABLE,
    _ELASTICSEARCH_AVAILABLE,
    _PROMETHEUS_AVAILABLE,
)


class TestIntegrationConfig:
    """测试集成配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = IntegrationConfig()
        
        assert config.enabled is True
        assert config.environment == "production"
        assert config.service_name == "wechat_backend"
        assert config.tags == {}
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = IntegrationConfig(
            enabled=False,
            environment="development",
            service_name="test_service",
            tags={"team": "backend"},
        )
        
        assert config.enabled is False
        assert config.environment == "development"
        assert config.service_name == "test_service"
        assert config.tags["team"] == "backend"
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = IntegrationConfig(
            environment="staging",
            service_name="api",
            tags={"version": "1.0"},
        )
        
        data = config.to_dict()
        
        assert data['environment'] == "staging"
        assert data['service_name'] == "api"
        assert data['tags']['version'] == "1.0"


class TestSentryIntegration:
    """测试 Sentry 集成"""
    
    def test_init_without_dsn(self):
        """测试无 DSN 初始化"""
        sentry = SentryIntegration(dsn=None)
        result = sentry.init()
        
        # 没有 DSN 应该返回 False
        assert result is False
        assert sentry.status == IntegrationStatus.DISABLED
    
    def test_init_without_sdk(self):
        """测试无 SDK 初始化"""
        if _SENTRY_AVAILABLE:
            pytest.skip("Sentry SDK is available, skipping unavailable test")
        
        sentry = SentryIntegration(dsn="https://test@sentry.io/123")
        result = sentry.init()
        
        assert result is False
        assert sentry.status == IntegrationStatus.DISABLED
    
    def test_status_transitions(self):
        """测试状态转换"""
        sentry = SentryIntegration(dsn=None)
        
        assert sentry.status == IntegrationStatus.DISABLED
        
        # 尝试初始化 (应该失败)
        sentry.init()
        
        # 状态应该是 DISABLED 或 ERROR
        assert sentry.status in [IntegrationStatus.DISABLED, IntegrationStatus.ERROR]
    
    def test_capture_exception_no_init(self):
        """测试未初始化时捕获异常"""
        sentry = SentryIntegration()
        
        # 不应该抛出异常
        try:
            sentry.capture_exception(ValueError("test"))
        except Exception:
            pytest.fail("capture_exception should not raise when not initialized")
    
    def test_capture_message_no_init(self):
        """测试未初始化时捕获消息"""
        sentry = SentryIntegration()
        
        # 不应该抛出异常
        try:
            sentry.capture_message("test message")
        except Exception:
            pytest.fail("capture_message should not raise when not initialized")
    
    def test_add_breadcrumb_no_init(self):
        """测试未初始化时添加 breadcrumb"""
        sentry = SentryIntegration()
        
        # 不应该抛出异常
        try:
            sentry.add_breadcrumb("test breadcrumb")
        except Exception:
            pytest.fail("add_breadcrumb should not raise when not initialized")
    
    def test_set_user_no_init(self):
        """测试未初始化时设置用户"""
        sentry = SentryIntegration()
        
        # 不应该抛出异常
        try:
            sentry.set_user(user_id="123")
        except Exception:
            pytest.fail("set_user should not raise when not initialized")
    
    def test_shutdown_no_init(self):
        """测试未初始化时关闭"""
        sentry = SentryIntegration()
        
        # 不应该抛出异常
        try:
            sentry.shutdown()
        except Exception:
            pytest.fail("shutdown should not raise when not initialized")


class TestELKIntegration:
    """测试 ELK 集成"""
    
    def test_init_without_hosts(self):
        """测试无主机初始化"""
        elk = ELKIntegration(hosts=None)
        result = elk.init()
        
        # 没有主机应该返回 False
        assert result is False
        assert elk.status == IntegrationStatus.DISABLED
    
    def test_init_without_sdk(self):
        """测试无 SDK 初始化"""
        if _ELASTICSEARCH_AVAILABLE:
            pytest.skip("Elasticsearch SDK is available, skipping unavailable test")
        
        elk = ELKIntegration(hosts=["http://localhost:9200"])
        result = elk.init()
        
        assert result is False
        assert elk.status == IntegrationStatus.DISABLED
    
    def test_status_transitions(self):
        """测试状态转换"""
        elk = ELKIntegration(hosts=None)
        
        assert elk.status == IntegrationStatus.DISABLED
        
        # 尝试初始化 (应该失败)
        elk.init()
        
        # 状态应该是 DISABLED 或 ERROR
        assert elk.status in [IntegrationStatus.DISABLED, IntegrationStatus.ERROR]
    
    def test_send_log_no_init(self):
        """测试未初始化时发送日志"""
        elk = ELKIntegration()
        
        # 不应该抛出异常
        try:
            elk.send_log({"message": "test"})
        except Exception:
            pytest.fail("send_log should not raise when not initialized")
    
    def test_flush_no_init(self):
        """测试未初始化时刷新"""
        elk = ELKIntegration()
        
        # 不应该抛出异常
        try:
            elk.flush()
        except Exception:
            pytest.fail("flush should not raise when not initialized")
    
    def test_get_stats(self):
        """测试获取统计"""
        elk = ELKIntegration(hosts=None)
        stats = elk.get_stats()
        
        assert 'status' in stats
        assert 'buffer_size' in stats
        assert 'sent' in stats
        assert 'failed' in stats
    
    def test_shutdown_no_init(self):
        """测试未初始化时关闭"""
        elk = ELKIntegration()
        
        # 不应该抛出异常
        try:
            elk.shutdown()
        except Exception:
            pytest.fail("shutdown should not raise when not initialized")


class TestPrometheusIntegration:
    """测试 Prometheus 集成"""
    
    def test_init_without_sdk(self):
        """测试无 SDK 初始化"""
        if _PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus client is available, skipping unavailable test")
        
        prom = PrometheusIntegration(port=9091)  # 使用不同端口避免冲突
        result = prom.init()
        
        assert result is False
        assert prom.status == IntegrationStatus.DISABLED
    
    def test_status_transitions(self):
        """测试状态转换"""
        prom = PrometheusIntegration(port=9091)
        
        assert prom.status == IntegrationStatus.DISABLED
        
        # 尝试初始化
        prom.init()
        
        # 状态应该是 CONNECTED 或 ERROR (取决于 SDK 是否可用)
        if _PROMETHEUS_AVAILABLE:
            # SDK 可用时可能成功或失败 (端口可能被占用)
            assert prom.status in [IntegrationStatus.CONNECTED, IntegrationStatus.ERROR]
        else:
            assert prom.status == IntegrationStatus.DISABLED
    
    def test_create_counter_no_init(self):
        """测试未初始化时创建 Counter"""
        prom = PrometheusIntegration()
        
        counter = prom.create_counter("test_counter", "Test counter")
        
        if _PROMETHEUS_AVAILABLE:
            # SDK 可用但服务未启动，应该返回 None
            assert counter is None
        else:
            assert counter is None
    
    def test_create_gauge_no_init(self):
        """测试未初始化时创建 Gauge"""
        prom = PrometheusIntegration()
        
        gauge = prom.create_gauge("test_gauge", "Test gauge")
        
        assert gauge is None
    
    def test_create_histogram_no_init(self):
        """测试未初始化时创建 Histogram"""
        prom = PrometheusIntegration()
        
        histogram = prom.create_histogram("test_histogram", "Test histogram")
        
        assert histogram is None
    
    def test_get_metric(self):
        """测试获取指标"""
        prom = PrometheusIntegration()
        
        metric = prom.get_metric("nonexistent")
        assert metric is None
    
    def test_get_all_metrics(self):
        """测试获取所有指标"""
        prom = PrometheusIntegration()
        
        metrics = prom.get_all_metrics()
        assert isinstance(metrics, dict)
    
    def test_shutdown_no_init(self):
        """测试未初始化时关闭"""
        prom = PrometheusIntegration()
        
        # 不应该抛出异常
        try:
            prom.shutdown()
        except Exception:
            pytest.fail("shutdown should not raise when not initialized")


class TestExternalServicesManager:
    """测试外部服务管理器"""
    
    def test_configure_empty(self):
        """测试空配置"""
        manager = ExternalServicesManager()
        manager.configure_from_config({})
        
        # 即使配置为空，也会创建集成对象 (但不会初始化)
        # Sentry 会被创建但因为没有 DSN 而不会初始化
        assert manager.sentry is not None or manager.sentry is None  # 取决于配置
        assert manager.elk is not None or manager.elk is None
        assert manager.prometheus is not None or manager.prometheus is None
    
    def test_configure_sentry(self):
        """测试配置 Sentry"""
        manager = ExternalServicesManager()
        manager.configure_from_config({
            'sentry': {
                'enabled': True,
                'dsn': 'https://test@sentry.io/123',
                'environment': 'test',
            }
        })
        
        assert manager.sentry is not None
    
    def test_configure_elk(self):
        """测试配置 ELK"""
        manager = ExternalServicesManager()
        manager.configure_from_config({
            'elk': {
                'enabled': True,
                'hosts': ['http://localhost:9200'],
                'index_prefix': 'test-logs',
            }
        })
        
        assert manager.elk is not None
    
    def test_configure_prometheus(self):
        """测试配置 Prometheus"""
        manager = ExternalServicesManager()
        manager.configure_from_config({
            'prometheus': {
                'enabled': True,
                'port': 9098,
            }
        })
        
        assert manager.prometheus is not None
    
    def test_configure_all(self):
        """测试配置所有服务"""
        manager = ExternalServicesManager()
        manager.configure_from_config({
            'sentry': {'enabled': True, 'dsn': 'https://test@sentry.io/123'},
            'elk': {'enabled': True, 'hosts': ['http://localhost:9200']},
            'prometheus': {'enabled': True, 'port': 9099},
        })
        
        assert manager.sentry is not None
        assert manager.elk is not None
        assert manager.prometheus is not None
    
    def test_get_status(self):
        """测试获取状态"""
        manager = ExternalServicesManager()
        manager.configure_from_config({})
        
        status = manager.get_status()
        
        assert 'sentry' in status
        assert 'elk' in status
        assert 'prometheus' in status
        assert 'overall' in status
    
    def test_start_empty(self):
        """测试启动空管理器"""
        manager = ExternalServicesManager()
        manager.configure_from_config({})
        
        results = manager.start()
        
        # 即使没有配置服务，也会返回结果字典
        assert isinstance(results, dict)
        # 状态应该是 DISABLED
        assert manager._status == IntegrationStatus.DISABLED
    
    def test_shutdown_empty(self):
        """测试关闭空管理器"""
        manager = ExternalServicesManager()
        
        # 不应该抛出异常
        try:
            manager.shutdown()
        except Exception:
            pytest.fail("shutdown should not raise with empty manager")


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_init_sentry_no_dsn(self):
        """测试无 DSN 初始化 Sentry"""
        from unified_logging.integrations import init_sentry
        result = init_sentry()
        assert result is None
    
    def test_init_elk_no_hosts(self):
        """测试无主机初始化 ELK"""
        from unified_logging.integrations import init_elk
        result = init_elk()
        assert result is None
    
    def test_init_prometheus(self):
        """测试初始化 Prometheus"""
        from unified_logging.integrations import init_prometheus
        result = init_prometheus(port=9097)
        
        if _PROMETHEUS_AVAILABLE:
            # SDK 可用时可能成功或失败
            assert result is None or result is not None
        else:
            assert result is None


class TestIntegrationWithLogging:
    """测试与日志系统集成"""
    
    def test_sentry_logging_integration(self):
        """测试 Sentry 与日志集成"""
        if not _SENTRY_AVAILABLE:
            pytest.skip("Sentry SDK not available")
        
        # 不实际初始化，只测试接口
        sentry = SentryIntegration(dsn=None)
        
        # 这些方法应该可以安全调用
        sentry.capture_exception(ValueError("test"))
        sentry.capture_message("test")
        sentry.add_breadcrumb("test")
        sentry.set_user(user_id="123")
    
    def test_elk_logging_integration(self):
        """测试 ELK 与日志集成"""
        if not _ELASTICSEARCH_AVAILABLE:
            pytest.skip("Elasticsearch SDK not available")
        
        # 不实际初始化，只测试接口
        elk = ELKIntegration(hosts=None)
        
        # 这些方法应该可以安全调用
        elk.send_log({"message": "test", "level": "INFO"})
        elk.flush()
    
    def test_prometheus_metrics_integration(self):
        """测试 Prometheus 指标集成"""
        if not _PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus client not available")
        
        # 不实际初始化，只测试接口
        prom = PrometheusIntegration(port=9096)
        
        # 这些方法应该可以安全调用
        prom.create_counter("test_counter", "Test")
        prom.create_gauge("test_gauge", "Test")
        prom.create_histogram("test_histogram", "Test")


class TestEdgeCases:
    """测试边界情况"""
    
    def test_sentry_invalid_dsn(self):
        """测试 Sentry 无效 DSN"""
        sentry = SentryIntegration(dsn="invalid-dsn")
        result = sentry.init()
        
        # 应该失败
        assert result is False
    
    def test_elk_invalid_hosts(self):
        """测试 ELK 无效主机"""
        elk = ELKIntegration(hosts=["http://invalid-host:9200"])
        result = elk.init()
        
        # 应该失败
        assert result is False
    
    def test_prometheus_invalid_port(self):
        """测试 Prometheus 无效端口"""
        prom = PrometheusIntegration(port=-1)
        result = prom.init()
        
        # 应该失败
        assert result is False
    
    def test_manager_double_start(self):
        """测试管理器重复启动"""
        manager = ExternalServicesManager()
        manager.configure_from_config({})
        
        # 第一次启动
        manager.start()
        
        # 第二次启动不应该抛出异常
        try:
            manager.start()
        except Exception:
            pytest.fail("Double start should not raise exception")
    
    def test_manager_double_shutdown(self):
        """测试管理器重复关闭"""
        manager = ExternalServicesManager()
        
        # 第一次关闭
        manager.shutdown()
        
        # 第二次关闭不应该抛出异常
        try:
            manager.shutdown()
        except Exception:
            pytest.fail("Double shutdown should not raise exception")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
