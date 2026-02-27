"""
测试数据夹具包

提供所有集成测试所需的测试数据夹具：
- diagnosis_fixtures: 诊断配置数据
- ai_response_fixtures: AI 响应模拟
- db_fixtures: 数据库测试数据

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

from .diagnosis_fixtures import (
    generate_random_brand,
    generate_random_execution_id,
    standard_diagnosis_config,
    single_brand_config,
    multi_brand_config,
    custom_question_config,
    all_models_config,
    partial_models_config,
    random_diagnosis_config,
    high_priority_config,
    minimal_config,
)

from .ai_response_fixtures import (
    MockAIAdapter,
    SlowAIAdapter,
    FlakyAIAdapter,
    mock_ai_adapter,
    failing_ai_adapter,
    flaky_ai_adapter,
    retry_ai_adapter,
    slow_ai_adapter,
    very_slow_ai_adapter,
    flaky_50_ai_adapter,
    custom_response_ai_adapter,
    deterministic_ai_adapter,
    brand_specific_ai_adapter,
)

from .db_fixtures import (
    db_cursor,
    populated_db_completed,
    populated_db_failed,
    populated_db_partial,
    populated_db_pending,
    populated_db_with_logs,
    populated_db_with_dead_letters,
    multi_user_db,
)

__all__ = [
    # 诊断配置
    'generate_random_brand',
    'generate_random_execution_id',
    'standard_diagnosis_config',
    'single_brand_config',
    'multi_brand_config',
    'custom_question_config',
    'all_models_config',
    'partial_models_config',
    'random_diagnosis_config',
    'high_priority_config',
    'minimal_config',
    
    # AI 适配器
    'MockAIAdapter',
    'SlowAIAdapter',
    'FlakyAIAdapter',
    'mock_ai_adapter',
    'failing_ai_adapter',
    'flaky_ai_adapter',
    'retry_ai_adapter',
    'slow_ai_adapter',
    'very_slow_ai_adapter',
    'flaky_50_ai_adapter',
    'custom_response_ai_adapter',
    'deterministic_ai_adapter',
    'brand_specific_ai_adapter',
    
    # 数据库夹具
    'db_cursor',
    'populated_db_completed',
    'populated_db_failed',
    'populated_db_partial',
    'populated_db_pending',
    'populated_db_with_logs',
    'populated_db_with_dead_letters',
    'multi_user_db',
]
