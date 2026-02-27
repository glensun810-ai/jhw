"""
数据库测试数据夹具

提供：
1. 测试数据库连接
2. 预填充数据的数据库
3. 各种状态的诊断记录

作者：系统架构组
日期：2026-02-27
版本：1.0.0
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


@pytest.fixture
def db_cursor(db_connection):
    """提供数据库游标"""
    cursor = db_connection.cursor()
    yield cursor
    cursor.close()


@pytest.fixture
def populated_db_completed(db_connection, sample_execution_id, sample_diagnosis_config):
    """提供已填充完成诊断数据的数据库"""
    cursor = db_connection.cursor()

    # 插入报告
    cursor.execute('''
        INSERT INTO diagnosis_reports (
            execution_id, user_id, brand_name, status, progress,
            stage, is_completed, should_stop_polling,
            competitor_brands, selected_models, custom_questions
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sample_execution_id,
        sample_diagnosis_config['userOpenid'],
        sample_diagnosis_config['brand_list'][0],
        'completed',
        100,
        'completed',
        1,
        1,
        ','.join(sample_diagnosis_config.get('competitor_brands', [])),
        ','.join([m['name'] for m in sample_diagnosis_config['selectedModels']]),
        sample_diagnosis_config.get('custom_question', '')
    ))

    report_id = cursor.lastrowid

    # 插入结果
    for brand in sample_diagnosis_config['brand_list']:
        for model in ['deepseek', 'doubao', 'qwen']:
            cursor.execute('''
                INSERT INTO diagnosis_results (
                    report_id, execution_id, brand, question, model,
                    response, geo_data, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report_id,
                sample_execution_id,
                brand,
                sample_diagnosis_config.get('custom_question', '默认问题'),
                model,
                f'{{"content": "{brand}的响应", "model": "{model}"}}',
                '{"exposure": true, "sentiment": "positive"}',
                200
            ))

    db_connection.commit()

    return {
        'execution_id': sample_execution_id,
        'report_id': report_id
    }


@pytest.fixture
def populated_db_failed(db_connection, sample_execution_id, sample_diagnosis_config):
    """提供已填充失败诊断数据的数据库"""
    cursor = db_connection.cursor()

    # 插入失败的报告
    cursor.execute('''
        INSERT INTO diagnosis_reports (
            execution_id, user_id, brand_name, status, progress,
            stage, is_completed, should_stop_polling, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sample_execution_id,
        sample_diagnosis_config['userOpenid'],
        sample_diagnosis_config['brand_list'][0],
        'failed',
        30,
        'failed',
        0,
        1,
        '模拟诊断失败错误'
    ))

    report_id = cursor.lastrowid

    # 插入部分结果
    for brand in sample_diagnosis_config['brand_list'][:1]:  # 只插入部分品牌
        cursor.execute('''
            INSERT INTO diagnosis_results (
                report_id, execution_id, brand, question, model,
                response, error_message, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id,
            sample_execution_id,
            brand,
            sample_diagnosis_config.get('custom_question', '默认问题'),
            'deepseek',
            None,
            'AI 调用失败',
            0
        ))

    db_connection.commit()

    return {
        'execution_id': sample_execution_id,
        'report_id': report_id
    }


@pytest.fixture
def populated_db_partial(db_connection, sample_execution_id, sample_diagnosis_config):
    """提供已填充部分成功诊断数据的数据库"""
    cursor = db_connection.cursor()

    # 插入部分成功的报告
    cursor.execute('''
        INSERT INTO diagnosis_reports (
            execution_id, user_id, brand_name, status, progress,
            stage, is_completed, should_stop_polling
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sample_execution_id,
        sample_diagnosis_config['userOpenid'],
        sample_diagnosis_config['brand_list'][0],
        'partial_success',
        70,
        'partial_success',
        1,
        1
    ))

    report_id = cursor.lastrowid

    # 插入部分结果（部分品牌成功，部分失败）
    success_count = 0
    for i, brand in enumerate(sample_diagnosis_config['brand_list']):
        for j, model in enumerate(['deepseek', 'doubao', 'qwen']):
            if i == 0 or (i == 1 and j == 0):  # 部分成功
                cursor.execute('''
                    INSERT INTO diagnosis_results (
                        report_id, execution_id, brand, question, model,
                        response, geo_data, latency_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_id,
                    sample_execution_id,
                    brand,
                    sample_diagnosis_config.get('custom_question', '默认问题'),
                    model,
                    f'{{"content": "{brand}的响应", "model": "{model}"}}',
                    '{"exposure": true, "sentiment": "positive"}',
                    200
                ))
                success_count += 1
            else:
                cursor.execute('''
                    INSERT INTO diagnosis_results (
                        report_id, execution_id, brand, question, model,
                        response, error_message, latency_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_id,
                    sample_execution_id,
                    brand,
                    sample_diagnosis_config.get('custom_question', '默认问题'),
                    model,
                    None,
                    'AI 调用超时',
                    5000
                ))

    db_connection.commit()

    return {
        'execution_id': sample_execution_id,
        'report_id': report_id,
        'success_count': success_count
    }


@pytest.fixture
def populated_db_pending(db_connection, sample_execution_id, sample_diagnosis_config):
    """提供已填充进行中诊断数据的数据库"""
    cursor = db_connection.cursor()

    # 插入进行中的报告
    cursor.execute('''
        INSERT INTO diagnosis_reports (
            execution_id, user_id, brand_name, status, progress,
            stage, is_completed, should_stop_polling
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sample_execution_id,
        sample_diagnosis_config['userOpenid'],
        sample_diagnosis_config['brand_list'][0],
        'ai_fetching',
        50,
        'ai_fetching',
        0,
        0
    ))

    report_id = cursor.lastrowid

    db_connection.commit()

    return {
        'execution_id': sample_execution_id,
        'report_id': report_id
    }


@pytest.fixture
def populated_db_with_logs(
    db_connection,
    sample_execution_id,
    sample_diagnosis_config
):
    """提供已填充 API 调用日志的数据库"""
    cursor = db_connection.cursor()

    # 插入报告
    cursor.execute('''
        INSERT INTO diagnosis_reports (
            execution_id, user_id, brand_name, status, progress,
            stage, is_completed, should_stop_polling
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sample_execution_id,
        sample_diagnosis_config['userOpenid'],
        sample_diagnosis_config['brand_list'][0],
        'completed',
        100,
        'completed',
        1,
        1
    ))

    report_id = cursor.lastrowid

    # 插入 API 调用日志
    log_count = 0
    for brand in sample_diagnosis_config['brand_list']:
        for model in ['deepseek', 'doubao', 'qwen']:
            cursor.execute('''
                INSERT INTO api_call_logs (
                    execution_id, brand, question, model,
                    request_data, response_data, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sample_execution_id,
                brand,
                sample_diagnosis_config.get('custom_question', '默认问题'),
                model,
                f'{{"brand": "{brand}", "model": "{model}"}}',
                f'{{"content": "响应", "model": "{model}"}}',
                200
            ))
            log_count += 1

    db_connection.commit()

    return {
        'execution_id': sample_execution_id,
        'report_id': report_id,
        'log_count': log_count
    }


@pytest.fixture
def populated_db_with_dead_letters(
    db_connection,
    sample_execution_id
):
    """提供已填充死信队列的数据库"""
    cursor = db_connection.cursor()

    # 插入死信队列记录
    errors = [
        ('diagnosis', 'Exception', 'AI 调用失败', 0),
        ('timeout', 'TimeoutError', '任务超时', 1),
        ('retry', 'ConnectionError', '网络连接失败', 2),
    ]

    for task_type, error_type, error_msg, priority in errors:
        cursor.execute('''
            INSERT INTO dead_letter_queue (
                execution_id, task_type, error_type, error_message,
                task_context, retry_count, priority, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sample_execution_id,
            task_type,
            error_type,
            error_msg,
            f'{{"stage": "ai_fetching", "brand": "测试品牌"}}',
            3,
            priority,
            'pending'
        ))

    db_connection.commit()

    return {
        'execution_id': sample_execution_id,
        'dead_letter_count': len(errors)
    }


@pytest.fixture
def multi_user_db(db_connection):
    """提供多用户数据的数据库"""
    cursor = db_connection.cursor()

    users = [
        ('user_001', 'Premium'),
        ('user_002', 'Basic'),
        ('user_003', 'Enterprise'),
        ('test_user_multi_1', 'Premium'),
        ('test_user_multi_2', 'Basic'),
    ]

    for user_id, user_level in users:
        exec_id = f"test_exec_{user_id}_{datetime.now().strftime('%Y%m%d')}"
        cursor.execute('''
            INSERT INTO diagnosis_reports (
                execution_id, user_id, brand_name, status, progress,
                stage, is_completed, should_stop_polling
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            exec_id,
            user_id,
            f'品牌_{user_id}',
            'completed',
            100,
            'completed',
            1,
            1
        ))

    db_connection.commit()

    return {
        'users': users,
        'total_reports': len(users)
    }
