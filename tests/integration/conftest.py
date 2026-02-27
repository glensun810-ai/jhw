"""
集成测试配置和夹具

提供：
1. 测试数据库配置
2. 模拟服务
3. 测试数据
4. 异步支持
5. 数据清理

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import sqlite3
import json
import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path


# ========== 测试数据库配置 ==========

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """创建测试数据库"""
    db_path = tmp_path_factory.mktemp("data") / "test_diagnosis.db"
    
    # 初始化数据库 schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 创建所有表
    cursor.executescript('''
        -- 诊断报告主表
        CREATE TABLE diagnosis_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            brand_name TEXT NOT NULL,
            competitor_brands TEXT,
            selected_models TEXT,
            custom_questions TEXT,
            status TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            stage TEXT NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            should_stop_polling BOOLEAN DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            data_schema_version TEXT DEFAULT '1.0',
            server_version TEXT,
            checksum TEXT
        );
        
        -- 诊断结果明细表
        CREATE TABLE diagnosis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            execution_id TEXT NOT NULL,
            brand TEXT NOT NULL,
            question TEXT NOT NULL,
            model TEXT NOT NULL,
            response TEXT,
            geo_data TEXT,
            quality_score REAL,
            quality_level TEXT,
            latency_ms INTEGER,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
        );
        
        -- API 调用日志表
        CREATE TABLE api_call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT NOT NULL,
            brand TEXT NOT NULL,
            question TEXT NOT NULL,
            model TEXT NOT NULL,
            request_data TEXT,
            response_data TEXT,
            error TEXT,
            latency_ms INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 死信队列表
        CREATE TABLE dead_letter_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            error_stack TEXT,
            task_context TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_retry_at TIMESTAMP,
            resolved_at TIMESTAMP,
            handled_by TEXT,
            resolution_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建索引
        CREATE INDEX idx_reports_execution ON diagnosis_reports(execution_id);
        CREATE INDEX idx_reports_user ON diagnosis_reports(user_id);
        CREATE INDEX idx_reports_status ON diagnosis_reports(status);
        CREATE INDEX idx_results_execution ON diagnosis_results(execution_id);
        CREATE INDEX idx_results_report ON diagnosis_results(report_id);
        CREATE INDEX idx_api_logs_execution ON api_call_logs(execution_id);
        CREATE INDEX idx_dead_letter_status ON dead_letter_queue(status);
    ''')
    
    conn.commit()
    conn.close()
    
    return str(db_path)


@pytest.fixture
def db_connection(test_db_path):
    """提供数据库连接"""
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def clean_db(db_connection):
    """每个测试后清理数据"""
    yield
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM diagnosis_reports")
    cursor.execute("DELETE FROM diagnosis_results")
    cursor.execute("DELETE FROM api_call_logs")
    cursor.execute("DELETE FROM dead_letter_queue")
    db_connection.commit()


# ========== 模拟服务 ==========

class MockAIAdapter:
    """模拟 AI 适配器，用于测试"""
    
    def __init__(
        self,
        should_fail: bool = False,
        fail_rate: float = 0,
        latency_range: tuple = (100, 500),
        fail_until_attempt: int = 0
    ):
        self.should_fail = should_fail
        self.fail_rate = fail_rate
        self.latency_range = latency_range
        self.fail_until_attempt = fail_until_attempt
        self.call_count = 0
        self.attempts = {}
    
    async def send_prompt(self, brand: str, question: str, model: str) -> Dict[str, Any]:
        """模拟发送提示词"""
        self.call_count += 1
        key = f"{brand}_{model}"
        self.attempts[key] = self.attempts.get(key, 0) + 1
        
        # 模拟延迟
        latency = random.randint(*self.latency_range)
        await asyncio.sleep(latency / 1000)
        
        # 模拟失败（在指定次数前）
        if self.fail_until_attempt > 0 and self.attempts[key] <= self.fail_until_attempt:
            raise Exception(f"模拟 AI 调用失败（第{self.attempts[key]}次尝试）: {model}")
        
        # 模拟随机失败
        if self.should_fail or random.random() < self.fail_rate:
            raise Exception(f"模拟 AI 调用失败：{model}")
        
        # 模拟成功响应
        return {
            'content': f"这是关于{brand}的模拟响应，问题：{question}",
            'model': model,
            'latency_ms': latency,
            'usage': {'prompt_tokens': 100, 'completion_tokens': 200},
            'geo_data': {
                'exposure': random.choice([True, False]),
                'sentiment': random.choice(['positive', 'neutral', 'negative']),
                'platform': model
            }
        }


@pytest.fixture
def mock_ai_adapter():
    """提供模拟 AI 适配器（总是成功）"""
    return MockAIAdapter()


@pytest.fixture
def failing_ai_adapter():
    """提供总是失败的模拟 AI 适配器"""
    return MockAIAdapter(should_fail=True)


@pytest.fixture
def flaky_ai_adapter():
    """提供偶尔失败的模拟 AI 适配器（30% 失败率）"""
    return MockAIAdapter(fail_rate=0.3)


@pytest.fixture
def retry_ai_adapter():
    """提供前几次失败、后几次成功的模拟器"""
    return MockAIAdapter(fail_until_attempt=2)


# ========== 测试数据 ==========

@pytest.fixture
def sample_diagnosis_config():
    """示例诊断配置"""
    return {
        'brand_list': ['测试品牌 A', '测试品牌 B'],
        'selectedModels': [
            {'name': 'deepseek', 'checked': True},
            {'name': 'doubao', 'checked': True},
            {'name': 'qwen', 'checked': True}
        ],
        'custom_question': '用户如何看待测试品牌的产品质量？',
        'competitor_brands': ['竞品 X', '竞品 Y'],
        'userOpenid': 'test_user_123',
        'userLevel': 'Premium'
    }


@pytest.fixture
def sample_execution_id():
    """示例执行 ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"test_exec_{timestamp}_{random_suffix}"


@pytest.fixture
def sample_user_id():
    """示例用户 ID"""
    return f"test_user_{random.randint(1000, 9999)}"


@pytest.fixture
async def setup_completed_diagnosis(test_db_path, sample_execution_id, sample_diagnosis_config):
    """创建已完成诊断的测试数据"""
    from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
    from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
    from wechat_backend.v2.models.diagnosis_result import DiagnosisResult
    
    repo = DiagnosisRepository(test_db_path)
    
    # 创建报告
    report_id = repo.create_report(
        execution_id=sample_execution_id,
        user_id=sample_diagnosis_config['userOpenid'],
        brand_name=sample_diagnosis_config['brand_list'][0],
        config=sample_diagnosis_config
    )
    
    # 更新状态为完成
    repo.update_state(
        execution_id=sample_execution_id,
        status='completed',
        progress=100,
        stage='completed',
        is_completed=True,
        should_stop_polling=True
    )
    
    # 添加一些结果
    result_repo = DiagnosisResultRepository(test_db_path)
    for brand in sample_diagnosis_config['brand_list']:
        for model in ['deepseek', 'doubao', 'qwen']:
            result_repo.create(DiagnosisResult(
                report_id=report_id,
                execution_id=sample_execution_id,
                brand=brand,
                question=sample_diagnosis_config['custom_question'],
                model=model,
                response={'content': f'{brand}的模拟响应', 'model': model},
                geo_data={'exposure': True, 'sentiment': 'positive'},
                latency_ms=200
            ))
    
    return {
        'execution_id': sample_execution_id,
        'report_id': report_id,
        'config': sample_diagnosis_config
    }


@pytest.fixture
async def setup_pending_diagnosis(test_db_path, sample_execution_id, sample_diagnosis_config):
    """创建进行中的诊断测试数据"""
    from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
    
    repo = DiagnosisRepository(test_db_path)
    
    # 创建报告
    report_id = repo.create_report(
        execution_id=sample_execution_id,
        user_id=sample_diagnosis_config['userOpenid'],
        brand_name=sample_diagnosis_config['brand_list'][0],
        config=sample_diagnosis_config
    )
    
    # 更新状态为进行中
    repo.update_state(
        execution_id=sample_execution_id,
        status='ai_fetching',
        progress=50,
        stage='ai_fetching',
        is_completed=False,
        should_stop_polling=False
    )
    
    return {
        'execution_id': sample_execution_id,
        'report_id': report_id,
        'config': sample_diagnosis_config
    }


@pytest.fixture
async def setup_failed_diagnosis(test_db_path, sample_execution_id, sample_diagnosis_config):
    """创建失败的诊断测试数据"""
    from wechat_backend.v2.repositories.diagnosis_repository import DiagnosisRepository
    
    repo = DiagnosisRepository(test_db_path)
    
    # 创建报告
    report_id = repo.create_report(
        execution_id=sample_execution_id,
        user_id=sample_diagnosis_config['userOpenid'],
        brand_name=sample_diagnosis_config['brand_list'][0],
        config=sample_diagnosis_config
    )
    
    # 更新状态为失败
    repo.update_state(
        execution_id=sample_execution_id,
        status='failed',
        progress=30,
        stage='failed',
        is_completed=False,
        should_stop_polling=True,
        error_message='模拟诊断失败'
    )
    
    return {
        'execution_id': sample_execution_id,
        'report_id': report_id,
        'config': sample_diagnosis_config
    }


# ========== 异步支持 ==========

@pytest.fixture
def event_loop():
    """提供事件循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ========== 辅助函数 ==========

def generate_random_string(length: int = 10) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_random_brand() -> str:
    """生成随机品牌名"""
    brands = ['品牌 A', '品牌 B', '品牌 C', '品牌 X', '品牌 Y', '品牌 Z']
    return random.choice(brands)


async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """等待条件满足"""
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        if condition_func():
            return True
        await asyncio.sleep(interval)
    
    return False
