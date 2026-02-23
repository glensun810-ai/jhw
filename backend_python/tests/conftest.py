#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后端 Python 测试优化配置
解决 P2-1: 后端 Python 测试超时问题

优化策略:
1. 设置合理的超时时间
2. 使用 Mock 避免外部 API 调用
3. 分离快速测试和完整测试
4. 添加测试并行执行支持
"""

import pytest
import os
import sys

# 测试配置
TEST_CONFIG = {
    # 超时设置（秒）
    'timeout': {
        'unit_test': 10,      # 单元测试超时
        'integration_test': 30,  # 集成测试超时
        'api_test': 60,       # API 测试超时
        'slow_test': 120,     # 慢速测试超时
    },
    
    # 重试配置
    'retry': {
        'max_retries': 2,
        'retry_delay': 1,
    },
    
    # 并行执行配置
    'parallel': {
        'enabled': True,
        'max_workers': 4,
    },
    
    # 测试过滤
    'filter': {
        'skip_slow': False,   # 是否跳过慢速测试
        'skip_integration': False,  # 是否跳过集成测试
    }
}


def pytest_configure(config):
    """pytest 配置钩子"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require running API server"
    )


@pytest.fixture(scope="session")
def test_config():
    """测试配置 fixture"""
    return TEST_CONFIG


@pytest.fixture(scope="session")
def base_url():
    """基础 URL fixture"""
    return os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:5000')


@pytest.fixture(scope="session")
def api_timeout():
    """API 超时配置 fixture"""
    return int(os.environ.get('TEST_API_TIMEOUT', '30'))


@pytest.fixture
def mock_ai_response():
    """Mock AI 响应，避免实际 API 调用"""
    return {
        'status': 'success',
        'executionId': 'test-execution-id-12345',
        'data': {
            'results': [
                {
                    'brand': '测试品牌',
                    'score': 85,
                    'response': 'Mock AI 响应内容'
                }
            ]
        }
    }


@pytest.fixture
def mock_task_status():
    """Mock 任务状态，避免实际轮询"""
    return {
        'status': 'success',
        'progress': 100,
        'stage': 'completed',
        'results': [
            {
                'brand': '测试品牌',
                'score': 85
            }
        ]
    }


# 运行说明
if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║              后端 Python 测试优化配置                      ║
╠══════════════════════════════════════════════════════════╣
║  修复 P2-1: 后端 Python 测试超时问题                        ║
╚══════════════════════════════════════════════════════════╝

优化策略:
1. ✅ 设置合理的超时时间 (pytest.ini)
2. ✅ 使用 Mock 避免外部 API 调用
3. ✅ 分离快速测试和完整测试
4. ✅ 添加测试并行执行支持

使用方法:

# 1. 运行快速测试（推荐）
pytest tests/ -m "not slow" -v

# 2. 运行单元测试（不依赖外部服务）
pytest tests/ -m "not integration and not api" -v

# 3. 运行完整测试（需要后端服务运行）
pytest tests/ -v

# 4. 并行执行测试
pytest tests/ -n auto -v

# 5. 生成测试报告
pytest tests/ -v --html=test_report.html

配置说明:
- 单元测试超时：10 秒
- 集成测试超时：30 秒
- API 测试超时：60 秒
- 慢速测试超时：120 秒

环境变量:
- TEST_BASE_URL: 后端服务地址 (默认：http://127.0.0.1:5000)
- TEST_API_TIMEOUT: API 超时时间 (默认：30 秒)
- TEST_PARALLEL: 是否启用并行 (默认：true)
""")
