"""
统一日志配置中心单元测试

测试范围:
1. ConfigManager 配置加载
2. 配置热重载功能
3. 环境变量覆盖
4. 配置变更通知
5. 统一入口模块
6. 配置合并功能
"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import yaml
import threading

from unified_logging.config_loader import (
    ConfigManager,
    ConfigState,
    ConfigChange,
    load_config,
    init_logging_from_config,
    _apply_env_overrides,
    _merge_config,
)

from unified_logging.entry import (
    init,
    init_from_file,
    init_with_config,
    get_logger,
    shutdown_logging,
    get_config,
    reload_config,
)


class TestConfigManager:
    """测试配置管理器"""
    
    def setup_method(self):
        """每个测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'test_config.yaml'
        
        # 创建测试配置
        self.test_config = {
            'log_level': 'INFO',
            'log_dir': 'logs',
            'queue': {
                'max_size': 5000
            },
            'rotation': {
                'app_log': {
                    'max_bytes': 5242880,
                    'backup_count': 3
                }
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)
    
    def teardown_method(self):
        """每个测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config(self):
        """测试加载配置"""
        manager = ConfigManager(str(self.config_file))
        
        assert manager.config['log_level'] == 'INFO'
        assert manager.config['queue']['max_size'] == 5000
    
    def test_config_version(self):
        """测试配置版本"""
        manager = ConfigManager(str(self.config_file))
        
        assert manager.version == 1
        
        # 修改文件
        self.test_config['log_level'] = 'DEBUG'
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)
        
        time.sleep(0.1)
        manager.reload()
        
        assert manager.version == 2
    
    def test_config_get(self):
        """测试获取配置值"""
        manager = ConfigManager(str(self.config_file))
        
        # 测试点分隔访问
        assert manager.get('queue.max_size') == 5000
        assert manager.get('log_level') == 'INFO'
        
        # 测试默认值
        assert manager.get('nonexistent', 'default') == 'default'
    
    def test_config_change_history(self):
        """测试配置变更历史"""
        manager = ConfigManager(str(self.config_file))
        
        # 初始加载不记录变更
        assert len(manager.get_change_history()) == 0
        
        # 修改配置
        self.test_config['log_level'] = 'DEBUG'
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)
        
        time.sleep(0.1)
        manager.reload()
        
        history = manager.get_change_history()
        assert len(history) > 0
    
    def test_config_listener(self):
        """测试配置变更监听器"""
        manager = ConfigManager(str(self.config_file))
        
        changes = []
        
        def listener(old_config, new_config):
            changes.append((old_config, new_config))
        
        manager.add_listener(listener)
        
        # 修改配置
        self.test_config['log_level'] = 'DEBUG'
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)
        
        time.sleep(0.1)
        manager.reload()
        
        assert len(changes) == 1
        assert changes[0][1]['log_level'] == 'DEBUG'
    
    def test_auto_reload(self):
        """测试自动重载"""
        manager = ConfigManager(str(self.config_file), auto_reload=False)
        manager.start_auto_reload(interval=0.5)
        
        try:
            # 修改配置
            self.test_config['log_level'] = 'WARNING'
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.test_config, f)
            
            # 等待自动重载
            time.sleep(1.0)
            
            assert manager.config['log_level'] == 'WARNING'
            assert manager.version >= 2
        finally:
            manager.stop_auto_reload()


class TestEnvOverrides:
    """测试环境变量覆盖"""
    
    def test_log_level_override(self):
        """测试日志级别覆盖"""
        os.environ['LOG_LEVEL'] = 'DEBUG'
        
        config = {'log_level': 'INFO'}
        result = _apply_env_overrides(config)
        
        assert result['log_level'] == 'DEBUG'
        
        del os.environ['LOG_LEVEL']
    
    def test_log_dir_override(self):
        """测试日志目录覆盖"""
        os.environ['LOG_DIR'] = '/custom/logs'
        
        config = {'log_dir': 'logs'}
        result = _apply_env_overrides(config)
        
        assert result['log_dir'] == '/custom/logs'
        
        del os.environ['LOG_DIR']
    
    def test_queue_size_override(self):
        """测试队列大小覆盖"""
        os.environ['LOG_QUEUE_SIZE'] = '20000'
        
        config = {}
        result = _apply_env_overrides(config)
        
        assert result['queue']['max_size'] == 20000
        
        del os.environ['LOG_QUEUE_SIZE']


class TestConfigMerge:
    """测试配置合并"""
    
    def test_simple_merge(self):
        """测试简单合并"""
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        
        result = _merge_config(base, override)
        
        assert result['a'] == 1
        assert result['b'] == 3  # 被覆盖
        assert result['c'] == 4
    
    def test_nested_merge(self):
        """测试嵌套合并"""
        base = {
            'level': 'INFO',
            'queue': {
                'size': 10000,
                'timeout': 1.0
            }
        }
        override = {
            'queue': {
                'size': 20000
            }
        }
        
        result = _merge_config(base, override)
        
        assert result['level'] == 'INFO'
        assert result['queue']['size'] == 20000
        assert result['queue']['timeout'] == 1.0  # 保留原值


class TestLoadConfig:
    """测试加载配置文件"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.yaml'
        
        config = {
            'log_level': 'INFO',
            'log_dir': 'logs'
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_file(self):
        """测试加载配置文件"""
        config = load_config(str(self.config_file))
        
        assert config['log_level'] == 'INFO'
        assert config['log_dir'] == 'logs'
    
    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError):
            load_config('nonexistent.yaml')


class TestUnifiedEntry:
    """测试统一入口模块"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # 重置工厂状态
        import unified_logging.unified_logger as ul
        ul._factory_instance = None
    
    def test_init(self):
        """测试快速初始化"""
        factory = init(log_dir=self.temp_dir, log_level='DEBUG')
        
        assert factory.is_initialized()
        
        logger = get_logger('test.entry')
        logger.info('Test message')
    
    def test_init_with_config(self):
        """测试使用配置字典初始化"""
        config = {
            'log_level': 'DEBUG',
            'log_dir': self.temp_dir,
            'queue': {
                'max_size': 5000
            },
            'handlers': {
                'console': {'enabled': True},
                'app_file': {'enabled': True},
                'ai_file': {'enabled': False},
                'error_file': {'enabled': True}
            }
        }
        
        factory = init_with_config(config)
        
        assert factory.is_initialized()
    
    def test_init_from_file(self):
        """测试从文件初始化"""
        config_file = Path(self.temp_dir) / 'logging.yaml'
        config = {
            'log_level': 'DEBUG',
            'log_dir': self.temp_dir,
            'queue': {
                'max_size': 5000
            },
            'handlers': {
                'console': {'enabled': True},
                'app_file': {'enabled': True},
                'ai_file': {'enabled': False},
                'error_file': {'enabled': True}
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        
        factory = init_from_file(str(config_file))
        
        assert factory.is_initialized()
    
    def test_get_predefined_loggers(self):
        """测试获取预定义日志器"""
        init(log_dir=self.temp_dir)
        
        from unified_logging.entry import (
            get_app_logger,
            get_api_logger,
            get_ai_logger,
            get_db_logger,
            get_security_logger,
        )
        
        app_logger = get_app_logger()
        api_logger = get_api_logger()
        ai_logger = get_ai_logger()
        db_logger = get_db_logger()
        security_logger = get_security_logger()
        
        assert app_logger is not None
        assert api_logger is not None
        assert ai_logger is not None
        assert db_logger is not None
        assert security_logger is not None


class TestConfigIntegration:
    """集成测试"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'logging.yaml'
        
        config = {
            'log_level': 'DEBUG',
            'log_dir': self.temp_dir,
            'queue': {
                'max_size': 5000
            },
            'handlers': {
                'console': {'enabled': True},
                'app_file': {'enabled': True},
                'ai_file': {'enabled': True},
                'error_file': {'enabled': True}
            },
            'loggers': {
                'wechat_backend': {'level': 'DEBUG'},
                'wechat_backend.api': {'level': 'INFO'},
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
    
    def teardown_method(self):
        shutdown_logging()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # 重置工厂状态
        import unified_logging.unified_logger as ul
        ul._factory_instance = None
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 从文件初始化
        factory = init_from_file(str(self.config_file))
        
        # 获取日志器
        logger = get_logger('wechat_backend.api.test')
        
        # 记录日志
        logger.info('Integration test', test_id='123')
        
        # 等待写入
        time.sleep(0.5)
        
        # 验证日志文件
        log_file = Path(self.temp_dir) / 'app.log'
        assert log_file.exists()
        
        # 关闭
        shutdown_logging()
        
        # 注意：由于单例模式，factory.is_initialized() 可能仍为 True
        # 这里我们验证日志系统已正确关闭
        import unified_logging.unified_logger as ul
        # 验证工厂已重置
        assert ul._factory_instance is None or not ul._factory_instance._initialized


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
