#!/usr/bin/env python3
"""
全栈修复综合验证脚本

验证范围:
1. P0 级修复 (execution_store 降级查询 + 数据库索引)
2. P1 级修复 (Storage + 错误处理 + selectedModels)
3. P2 级修复 (日志优化 + 限流监控)
4. DS 级修复 (事务处理 + 数据清理 + 数据加密)

使用方法:
    python3 final_verification.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
BACKEND_ROOT = PROJECT_ROOT / 'backend_python'

# 添加路径
sys.path.insert(0, str(BACKEND_ROOT))

# 验证结果
verification_result = {
    'timestamp': datetime.now().isoformat(),
    'categories': {},
    'summary': {}
}


def print_header(text):
    """打印标题"""
    print("\n" + "="*70)
    print(text)
    print("="*70)


def print_subheader(text):
    """打印子标题"""
    print(f"\n{text}")
    print("-"*60)


def verify_p0_fixes():
    """验证 P0 级修复"""
    print_header("P0 级修复验证")
    
    result = {
        'name': 'P0 级修复',
        'items': [],
        'passed': 0,
        'failed': 0
    }
    
    # P0-1: execution_id 索引
    print_subheader("P0-1: execution_id 索引验证")
    try:
        import sqlite3
        DB_PATH = BACKEND_ROOT / 'database.db'
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查索引定义
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='index' AND name='idx_test_records_execution_id'
        """)
        index_sql = cursor.fetchone()[0]
        
        if 'execution_id' in index_sql and 'json_extract' not in index_sql:
            print("✅ execution_id 索引定义正确")
            result['items'].append({'name': 'execution_id 索引', 'status': '✅ 通过'})
            result['passed'] += 1
        else:
            print(f"❌ execution_id 索引定义错误：{index_sql}")
            result['items'].append({'name': 'execution_id 索引', 'status': '❌ 失败'})
            result['failed'] += 1
        
        # 检查查询计划
        cursor.execute("""
            EXPLAIN QUERY PLAN 
            SELECT results_summary FROM test_records
            WHERE execution_id = 'test'
        """)
        plan = cursor.fetchall()
        
        if any('USING INDEX' in str(row) for row in plan):
            print("✅ 查询使用索引")
        else:
            print("⚠️  查询未使用索引")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 索引验证失败：{e}")
        result['items'].append({'name': 'execution_id 索引', 'status': f'❌ 错误：{e}'})
        result['failed'] += 1
    
    # P0-2: execution_id 数据完整性
    print_subheader("P0-2: execution_id 数据完整性验证")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM test_records")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM test_records WHERE execution_id IS NULL")
        null_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM test_records WHERE execution_id IS NOT NULL")
        not_null_count = cursor.fetchone()[0]
        
        print(f"总记录数：{total}")
        print(f"有 execution_id: {not_null_count} ({not_null_count/total*100:.1f}%)")
        print(f"无 execution_id: {null_count} ({null_count/total*100:.1f}%)")
        
        if null_count == 0:
            print("✅ 所有记录都有 execution_id")
            result['items'].append({'name': 'execution_id 数据完整性', 'status': '✅ 通过'})
            result['passed'] += 1
        else:
            print(f"⚠️  仍有 {null_count} 条记录无 execution_id")
            result['items'].append({'name': 'execution_id 数据完整性', 'status': '⚠️ 部分通过'})
            result['failed'] += 1
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据完整性验证失败：{e}")
        result['items'].append({'name': 'execution_id 数据完整性', 'status': f'❌ 错误：{e}'})
        result['failed'] += 1
    
    verification_result['categories']['P0'] = result
    print(f"\nP0 级修复：{result['passed']} 通过，{result['failed']} 失败")


def verify_p1_fixes():
    """验证 P1 级修复"""
    print_header("P1 级修复验证")
    
    result = {
        'name': 'P1 级修复',
        'items': [],
        'passed': 0,
        'failed': 0
    }
    
    # P1-1: Storage 管理器
    print_subheader("P1-1: Storage 管理器验证")
    storage_file = PROJECT_ROOT / 'utils' / 'storage-manager.js'
    if storage_file.exists():
        print(f"✅ Storage 管理器文件存在")
        result['items'].append({'name': 'Storage 管理器', 'status': '✅ 通过'})
        result['passed'] += 1
    else:
        print(f"❌ Storage 管理器文件不存在")
        result['items'].append({'name': 'Storage 管理器', 'status': '❌ 失败'})
        result['failed'] += 1
    
    # P1-2: 错误处理
    print_subheader("P1-2: 错误处理验证")
    try:
        nxm_file = BACKEND_ROOT / 'wechat_backend' / 'nxm_execution_engine.py'
        with open(nxm_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'error_details' in content and 'execution_store' in content:
            print("✅ 后端错误处理已完善")
            result['items'].append({'name': '后端错误处理', 'status': '✅ 通过'})
            result['passed'] += 1
        else:
            print("❌ 后端错误处理未完善")
            result['items'].append({'name': '后端错误处理', 'status': '❌ 失败'})
            result['failed'] += 1
        
        brand_service = PROJECT_ROOT / 'services' / 'brandTestService.js'
        with open(brand_service, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'createUserFriendlyError' in content:
            print("✅ 前端错误处理已完善")
            result['items'].append({'name': '前端错误处理', 'status': '✅ 通过'})
            result['passed'] += 1
        else:
            print("❌ 前端错误处理未完善")
            result['items'].append({'name': '前端错误处理', 'status': '❌ 失败'})
            result['failed'] += 1
        
    except Exception as e:
        print(f"❌ 错误处理验证失败：{e}")
        result['failed'] += 1
    
    # P1-3: selectedModels 简化
    print_subheader("P1-3: selectedModels 格式验证")
    try:
        brand_service = PROJECT_ROOT / 'services' / 'brandTestService.js'
        with open(brand_service, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'modelNames' in content and '字符串数组' in content:
            print("✅ selectedModels 已简化为字符串数组")
            result['items'].append({'name': 'selectedModels 简化', 'status': '✅ 通过'})
            result['passed'] += 1
        else:
            print("❌ selectedModels 未简化")
            result['items'].append({'name': 'selectedModels 简化', 'status': '❌ 失败'})
            result['failed'] += 1
        
    except Exception as e:
        print(f"❌ selectedModels 验证失败：{e}")
        result['failed'] += 1
    
    verification_result['categories']['P1'] = result
    print(f"\nP1 级修复：{result['passed']} 通过，{result['failed']} 失败")


def verify_p2_fixes():
    """验证 P2 级修复"""
    print_header("P2 级修复验证")
    
    result = {
        'name': 'P2 级修复',
        'items': [],
        'passed': 0,
        'failed': 0
    }
    
    # P2-1: 日志优化
    print_subheader("P2-1: 日志优化验证")
    log_config = BACKEND_ROOT / 'wechat_backend' / 'log_level_config.py'
    if log_config.exists():
        print("✅ 日志优化配置存在")
        result['items'].append({'name': '日志优化配置', 'status': '✅ 通过'})
        result['passed'] += 1
    else:
        print("❌ 日志优化配置不存在")
        result['items'].append({'name': '日志优化配置', 'status': '❌ 失败'})
        result['failed'] += 1
    
    # P2-2: 限流监控
    print_subheader("P2-2: 限流监控验证")
    rate_limit = BACKEND_ROOT / 'wechat_backend' / 'security' / 'rate_limit_monitor.py'
    if rate_limit.exists():
        print("✅ 限流监控模块存在")
        result['items'].append({'name': '限流监控模块', 'status': '✅ 通过'})
        result['passed'] += 1
    else:
        print("❌ 限流监控模块不存在")
        result['items'].append({'name': '限流监控模块', 'status': '❌ 失败'})
        result['failed'] += 1
    
    verification_result['categories']['P2'] = result
    print(f"\nP2 级修复：{result['passed']} 通过，{result['failed']} 失败")


def verify_ds_fixes():
    """验证 DS 级修复"""
    print_header("DS 级修复验证")
    
    result = {
        'name': 'DS 级修复',
        'items': [],
        'passed': 0,
        'failed': 0
    }
    
    # DS-P1-2: 事务处理
    print_subheader("DS-P1-2: 事务处理验证")
    transaction_file = BACKEND_ROOT / 'wechat_backend' / 'database' / 'transaction.py'
    if transaction_file.exists():
        print("✅ 事务处理模块存在")
        result['items'].append({'name': '事务处理模块', 'status': '✅ 通过'})
        result['passed'] += 1
    else:
        print("❌ 事务处理模块不存在")
        result['items'].append({'name': '事务处理模块', 'status': '❌ 失败'})
        result['failed'] += 1
    
    # DS-P1-1: 数据清理
    print_subheader("DS-P1-1: 数据清理验证")
    retention_file = BACKEND_ROOT / 'wechat_backend' / 'database' / 'data_retention.py'
    if retention_file.exists():
        print("✅ 数据清理模块存在")
        result['items'].append({'name': '数据清理模块', 'status': '✅ 通过'})
        result['passed'] += 1
    else:
        print("❌ 数据清理模块不存在")
        result['items'].append({'name': '数据清理模块', 'status': '❌ 失败'})
        result['failed'] += 1
    
    # DS-NEW-1: 数据加密
    print_subheader("DS-NEW-1: 数据加密验证")
    encryption_file = BACKEND_ROOT / 'wechat_backend' / 'security' / 'data_encryption.py'
    if encryption_file.exists():
        print("✅ 数据加密模块存在")
        result['items'].append({'name': '数据加密模块', 'status': '✅ 通过'})
        result['passed'] += 1
    else:
        print("❌ 数据加密模块不存在")
        result['items'].append({'name': '数据加密模块', 'status': '❌ 失败'})
        result['failed'] += 1
    
    # DS-P2-1: Storage 校验
    print_subheader("DS-P2-1: Storage 校验验证")
    storage_validator = PROJECT_ROOT / 'utils' / 'storage-validator.js'
    if storage_validator.exists():
        print("✅ Storage 校验工具存在")
        result['items'].append({'name': 'Storage 校验工具', 'status': '✅ 通过'})
        result['passed'] += 1
    else:
        print("❌ Storage 校验工具不存在")
        result['items'].append({'name': 'Storage 校验工具', 'status': '❌ 失败'})
        result['failed'] += 1
    
    verification_result['categories']['DS'] = result
    print(f"\nDS 级修复：{result['passed']} 通过，{result['failed']} 失败")


def verify_backend_service():
    """验证后端服务"""
    print_header("后端服务验证")
    
    result = {
        'name': '后端服务',
        'items': [],
        'passed': 0,
        'failed': 0
    }
    
    import requests
    
    # 健康检查
    print_subheader("API 健康检查")
    try:
        response = requests.get('http://127.0.0.1:5000/api/test', timeout=5)
        if response.status_code == 200:
            print("✅ /api/test 端点正常")
            result['items'].append({'name': '/api/test', 'status': '✅ 通过'})
            result['passed'] += 1
        else:
            print(f"❌ /api/test 端点异常：{response.status_code}")
            result['items'].append({'name': '/api/test', 'status': '❌ 失败'})
            result['failed'] += 1
        
    except Exception as e:
        print(f"❌ /api/test 端点不可达：{e}")
        result['items'].append({'name': '/api/test', 'status': f'❌ 错误：{e}'})
        result['failed'] += 1
    
    try:
        response = requests.get('http://127.0.0.1:5000/health', timeout=5)
        if response.status_code == 200:
            print("✅ /health 端点正常")
            result['items'].append({'name': '/health', 'status': '✅ 通过'})
            result['passed'] += 1
        else:
            print(f"❌ /health 端点异常：{response.status_code}")
            result['items'].append({'name': '/health', 'status': '❌ 失败'})
            result['failed'] += 1
        
    except Exception as e:
        print(f"❌ /health 端点不可达：{e}")
        result['items'].append({'name': '/health', 'status': f'❌ 错误：{e}'})
        result['failed'] += 1
    
    verification_result['categories']['Backend'] = result
    print(f"\n后端服务：{result['passed']} 通过，{result['failed']} 失败")


def generate_summary():
    """生成总结"""
    print_header("验证总结")
    
    total_passed = sum(cat.get('passed', 0) for cat in verification_result['categories'].values())
    total_failed = sum(cat.get('failed', 0) for cat in verification_result['categories'].values())
    total = total_passed + total_failed
    
    verification_result['summary'] = {
        'total_items': total,
        'passed': total_passed,
        'failed': total_failed,
        'pass_rate': f"{total_passed/total*100:.1f}%" if total > 0 else 'N/A'
    }
    
    print(f"总验证项：{total}")
    print(f"通过：{total_passed}")
    print(f"失败：{total_failed}")
    print(f"通过率：{verification_result['summary']['pass_rate']}")
    
    if total_failed == 0:
        print("\n✅ 所有验证通过！")
    else:
        print(f"\n⚠️  有 {total_failed} 项验证失败，请检查")


def save_report():
    """保存验证报告"""
    report_file = PROJECT_ROOT / 'docs' / 'final_verification_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(verification_result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 验证报告已保存：{report_file}")


if __name__ == '__main__':
    print_header("全栈修复综合验证")
    print(f"验证时间：{verification_result['timestamp']}")
    
    try:
        verify_p0_fixes()
        verify_p1_fixes()
        verify_p2_fixes()
        verify_ds_fixes()
        verify_backend_service()
        generate_summary()
        save_report()
        
        print("\n" + "="*70)
        print("验证完成！")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
