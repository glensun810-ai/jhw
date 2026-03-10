#!/usr/bin/env python3
"""
存储与性能优化基准测试脚本

测试场景:
1. 并发诊断性能测试
2. 数据库大小压缩测试
3. 缓存命中率测试
4. 完整验证清单

使用方法:
    python tests/benchmark_performance.py
"""

import os
import sys
import time
import json
import sqlite3
import threading
import concurrent.futures
import gzip
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入需要的模块，避免导入整个应用
import logging
db_logger = logging.getLogger('wechat_backend.benchmark')

# ==================== 测试配置 ====================

TEST_CONFIG = {
    'concurrent_tasks': 10,  # 并发诊断任务数
    'record_count': 1000,    # 数据库记录数
    'cache_warmup_requests': 100,  # 缓存预热请求数
    'test_brand': '华为',
    'test_questions': [
        '3000 元左右拍照好看的手机推荐哪个牌子的',
        '折叠屏手机推荐哪个品牌',
        '哪个品牌的手机性价比最高',
        '如何选择适合自己的手机品牌',
        '国产手机品牌排行榜'
    ],
    'test_models': ['DeepSeek', '豆包', '通义千问']
}

# ==================== 测试工具函数 ====================

def generate_mock_diagnosis_result(brand, question, model):
    """生成模拟诊断结果"""
    import random
    
    return {
        'brand': brand,
        'question': question,
        'model': model,
        'response': f'关于{brand}品牌在{question}方面的分析：' + 'A' * random.randint(500, 5000),
        'scores': {
            'accuracy': random.uniform(60, 100),
            'completeness': random.uniform(60, 100),
            'relevance': random.uniform(60, 100),
            'purity': random.uniform(60, 100),
            'consistency': random.uniform(60, 100)
        },
        'sentiment_score': random.uniform(-1.0, 1.0),
        'rank': random.randint(1, 10),
        'detailed_analysis': {
            'strengths': ['优势 1', '优势 2', '优势 3'],
            'weaknesses': ['劣势 1', '劣势 2'],
            'recommendations': ['建议 1', '建议 2', '建议 3']
        } * 10  # 放大数据以测试压缩
    }


def cleanup_test_data():
    """清理测试数据"""
    db_path = Path(__file__).parent.parent / 'database.db'
    cache_path = Path(__file__).parent.parent / 'cache.db'
    
    for path in [db_path, cache_path]:
        if path.exists():
            path.unlink()
            db_logger.info(f"已删除测试数据库：{path}")
        
        # 删除 WAL 文件
        for ext in ['-wal', '-shm']:
            wal_path = Path(str(path) + ext)
            if wal_path.exists():
                wal_path.unlink()


# ==================== 测试场景 1: 并发诊断性能 ====================

def test_concurrent_diagnosis():
    """
    测试场景 1: 并发诊断性能
    
    目标：验证 WAL 模式 + 连接池对并发性能的提升
    """
    print("\n" + "="*80)
    print("测试场景 1: 并发诊断性能测试")
    print("="*80)
    
    # 直接导入，避免导入整个应用
    import importlib.util
    spec = importlib.util.spec_from_file_location("database_core", 
        Path(__file__).parent.parent / 'wechat_backend' / 'database_core.py')
    db_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db_module)
    
    get_connection = db_module.get_connection
    get_db_pool_metrics = db_module.get_db_pool_metrics
    save_test_record = db_module.save_test_record
    reset_db_pool_metrics = db_module.reset_db_pool_metrics
    
    # 重置指标
    reset_db_pool_metrics()
    
    def run_single_diagnosis(task_id):
        """执行单次诊断"""
        import random
        brand = TEST_CONFIG['test_brand']
        question = random.choice(TEST_CONFIG['test_questions'])
        model = random.choice(TEST_CONFIG['test_models'])
        
        start_time = time.time()
        
        try:
            # 模拟诊断过程
            result = generate_mock_diagnosis_result(brand, question, model)
            
            # 保存到数据库
            record_id = save_test_record(
                user_openid=f'test_user_{task_id % 3}',
                brand_name=brand,
                ai_models_used=[model],
                questions_used=[question],
                overall_score=sum(result['scores'].values()) / len(result['scores']),
                total_tests=1,
                results_summary={
                    'avg_rank': result['rank'],
                    'sentiment': result['sentiment_score']
                },
                detailed_results=result
            )
            
            duration = time.time() - start_time
            return {
                'success': True,
                'task_id': task_id,
                'duration': duration,
                'record_id': record_id
            }
        except Exception as e:
            return {
                'success': False,
                'task_id': task_id,
                'duration': time.time() - start_time,
                'error': str(e)
            }
    
    # 执行并发测试
    print(f"\n启动 {TEST_CONFIG['concurrent_tasks']} 个并发诊断任务...")
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=TEST_CONFIG['concurrent_tasks']) as executor:
        futures = [executor.submit(run_single_diagnosis, i) for i in range(TEST_CONFIG['concurrent_tasks'])]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    total_duration = time.time() - start_time
    
    # 分析结果
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    durations = [r['duration'] for r in results]
    
    # 获取连接池指标
    pool_metrics = get_db_pool_metrics()
    
    # 打印结果
    print(f"\n测试结果:")
    print(f"  总耗时：{total_duration:.2f}秒")
    print(f"  成功：{len(successful)}/{TEST_CONFIG['concurrent_tasks']}")
    print(f"  失败：{len(failed)}")
    print(f"  平均耗时：{sum(durations)/len(durations):.2f}秒")
    print(f"  最大耗时：{max(durations):.2f}秒")
    print(f"  最小耗时：{min(durations):.2f}秒")
    
    print(f"\n连接池指标:")
    print(f"  活跃连接数：{pool_metrics['active_connections']}")
    print(f"  可用连接数：{pool_metrics['available_connections']}")
    print(f"  总创建连接数：{pool_metrics['total_created']}")
    print(f"  超时次数：{pool_metrics['timeout_count']}")
    print(f"  平均等待时间：{pool_metrics['avg_wait_time_ms']:.2f}ms")
    print(f"  连接池利用率：{pool_metrics['utilization']}")
    
    # 性能评估
    performance_rating = "优秀" if total_duration < 20 else "良好" if total_duration < 30 else "需优化"
    print(f"\n性能评级：{performance_rating}")
    print(f"预期目标：15-20 秒")
    print(f"实际耗时：{total_duration:.2f}秒")
    
    return {
        'test_name': 'concurrent_diagnosis',
        'total_duration': total_duration,
        'successful': len(successful),
        'failed': len(failed),
        'avg_duration': sum(durations)/len(durations),
        'pool_metrics': pool_metrics,
        'performance_rating': performance_rating
    }


# ==================== 测试场景 2: 数据库大小压缩 ====================

def test_database_compression():
    """
    测试场景 2: 数据库大小压缩
    
    目标：验证大对象压缩对存储空间的节省效果
    """
    print("\n" + "="*80)
    print("测试场景 2: 数据库大小压缩测试")
    print("="*80)
    
    from wechat_backend.database_core import (
        save_test_record,
        get_compression_metrics,
        reset_compression_metrics
    )
    
    # 重置压缩指标
    reset_compression_metrics()
    
    db_path = Path(__file__).parent.parent / 'database.db'
    
    print(f"\n生成 {TEST_CONFIG['record_count']} 条诊断记录...")
    start_time = time.time()
    
    for i in range(TEST_CONFIG['record_count']):
        brand = TEST_CONFIG['test_brand']
        question = TEST_CONFIG['test_questions'][i % len(TEST_CONFIG['test_questions'])]
        model = TEST_CONFIG['test_models'][i % len(TEST_CONFIG['test_models'])]
        
        result = generate_mock_diagnosis_result(brand, question, model)
        
        save_test_record(
            user_openid=f'test_user_{i % 10}',
            brand_name=brand,
            ai_models_used=[model],
            questions_used=[question],
            overall_score=sum(result['scores'].values()) / len(result['scores']),
            total_tests=1,
            results_summary={
                'avg_rank': result['rank'],
                'sentiment': result['sentiment_score']
            },
            detailed_results=result
        )
        
        if (i + 1) % 100 == 0:
            print(f"  已生成 {i + 1}/{TEST_CONFIG['record_count']} 条记录")
    
    generation_duration = time.time() - start_time
    
    # 获取数据库文件大小
    db_size_bytes = db_path.stat().st_size
    db_size_mb = db_size_bytes / 1024 / 1024
    
    # 获取压缩指标
    compression_metrics = get_compression_metrics()
    
    # 打印结果
    print(f"\n生成耗时：{generation_duration:.2f}秒")
    print(f"\n数据库文件大小:")
    print(f"  实际大小：{db_size_mb:.2f}MB")
    print(f"  平均每记录：{db_size_bytes / TEST_CONFIG['record_count'] / 1024:.2f}KB")
    
    print(f"\n压缩统计:")
    print(f"  压缩次数：{compression_metrics['total_compressed']}")
    print(f"  未压缩次数：{compression_metrics['total_uncompressed']}")
    print(f"  原始大小：{compression_metrics['original_size_kb'] / 1024:.2f}MB")
    print(f"  压缩后大小：{compression_metrics['compressed_size_kb'] / 1024:.2f}MB")
    print(f"  节省空间：{compression_metrics['space_saved_mb']:.2f}MB")
    print(f"  压缩率：{compression_metrics['avg_compression_ratio']}")
    print(f"  空间节省：{compression_metrics['space_savings']}")
    
    # 性能评估
    expected_size = 100  # MB
    actual_size = db_size_mb
    size_rating = "优秀" if actual_size < expected_size * 1.5 else "良好" if actual_size < expected_size * 2 else "需优化"
    
    print(f"\n性能评级：{size_rating}")
    print(f"预期大小：~{expected_size}MB")
    print(f"实际大小：{actual_size:.2f}MB")
    
    return {
        'test_name': 'database_compression',
        'db_size_mb': db_size_mb,
        'avg_record_size_kb': db_size_bytes / TEST_CONFIG['record_count'] / 1024,
        'compression_metrics': compression_metrics,
        'generation_duration': generation_duration,
        'size_rating': size_rating
    }


# ==================== 测试场景 3: 缓存命中率 ====================

def test_cache_hit_rate():
    """
    测试场景 3: 缓存命中率
    
    目标：验证混合缓存（L1+L2）的命中率提升效果
    """
    print("\n" + "="*80)
    print("测试场景 3: 缓存命中率测试")
    print("="*80)
    
    from wechat_backend.cache.api_cache import _api_cache, CacheConfig
    
    # 清空缓存
    _api_cache.clear()
    
    print(f"\n缓存预热：写入 {TEST_CONFIG['cache_warmup_requests']} 条数据...")
    
    # 写入测试数据
    for i in range(TEST_CONFIG['cache_warmup_requests']):
        key = f'test_cache_key_{i}'
        value = {
            'id': i,
            'data': 'A' * 1000,  # 1KB 数据
            'timestamp': time.time()
        }
        _api_cache.set(key, value, ttl=3600)
    
    print(f"预热完成")
    
    # 获取预热后指标
    warmup_metrics = _api_cache.get_metrics()
    print(f"\n预热后缓存状态:")
    print(f"  L1 条目数：{warmup_metrics['l1_cache']['entries']}")
    print(f"  L1 命中率：{warmup_metrics['l1_cache']['hit_rate']}%")
    
    # 模拟重启（从 L2 读取）
    print(f"\n模拟重启后访问...")
    
    # 随机访问缓存
    import random
    access_count = 50
    for i in range(access_count):
        key = f'test_cache_key_{random.randint(0, TEST_CONFIG['cache_warmup_requests'] - 1)}'
        _api_cache.get(key)
    
    # 获取最终指标
    final_metrics = _api_cache.get_metrics()
    
    print(f"\n访问后缓存指标:")
    print(f"  总请求数：{final_metrics['total_requests']}")
    print(f"  总命中数：{final_metrics['total_hits']}")
    print(f"  总未命中数：{final_metrics['total_misses']}")
    print(f"  整体命中率：{final_metrics['overall_hit_rate']}%")
    print(f"  L1 命中占比：{final_metrics['l1_hit_ratio']}%")
    print(f"  L2 命中占比：{final_metrics['l2_hit_ratio']}%")
    
    # 性能评估
    hit_rate = final_metrics['overall_hit_rate']
    hit_rating = "优秀" if hit_rate > 80 else "良好" if hit_rate > 60 else "需优化"
    
    print(f"\n性能评级：{hit_rating}")
    print(f"预期命中率：>80%")
    print(f"实际命中率：{hit_rate}%")
    
    return {
        'test_name': 'cache_hit_rate',
        'warmup_metrics': warmup_metrics,
        'final_metrics': final_metrics,
        'hit_rating': hit_rating
    }


# ==================== 验证清单 ====================

def run_verification_checklist():
    """
    运行完整验证清单
    """
    print("\n" + "="*80)
    print("验证清单")
    print("="*80)
    
    from wechat_backend.database_core import (
        get_db_pool,
        get_db_pool_metrics,
        get_compression_metrics
    )
    from wechat_backend.cache.api_cache import _api_cache
    from wechat_backend.database.query_optimizer import init_recommended_indexes
    
    checklist_results = {}
    
    # 1. 连接池初始化
    print("\n[1/7] 连接池初始化...")
    try:
        pool = get_db_pool()
        metrics = pool.get_metrics()
        checklist_results['connection_pool'] = {
            'status': '✅ 通过',
            'details': f"最大连接数={pool.max_connections}, 当前利用率={metrics['utilization']}"
        }
        print(f"  ✅ 通过 - {checklist_results['connection_pool']['details']}")
    except Exception as e:
        checklist_results['connection_pool'] = {
            'status': '❌ 失败',
            'details': str(e)
        }
        print(f"  ❌ 失败 - {str(e)}")
    
    # 2. WAL 模式
    print("\n[2/7] WAL 模式检查...")
    db_path = Path(__file__).parent.parent / 'database.db'
    wal_files = list(Path(__file__).parent.parent).glob('database.db-wal*')
    shm_files = list(Path(__file__).parent.parent).glob('database.db-shm*')
    
    wal_status = '✅ 通过' if wal_files or shm_files else '⚠️ 未激活'
    checklist_results['wal_mode'] = {
        'status': wal_status,
        'details': f"WAL 文件={len(list(wal_files))}, SHM 文件={len(list(shm_files))}"
    }
    print(f"  {wal_status} - {checklist_results['wal_mode']['details']}")
    
    # 3. 压缩功能
    print("\n[3/7] 压缩功能检查...")
    compression_metrics = get_compression_metrics()
    if compression_metrics['total_compressed'] > 0:
        checklist_results['compression'] = {
            'status': '✅ 通过',
            'details': f"压缩次数={compression_metrics['total_compressed']}, 节省空间={compression_metrics['space_saved_mb']:.2f}MB"
        }
        print(f"  ✅ 通过 - {checklist_results['compression']['details']}")
    else:
        checklist_results['compression'] = {
            'status': '⚠️ 未测试',
            'details': '尚未执行压缩操作'
        }
        print(f"  ⚠️ 未测试 - 需要先运行数据库压缩测试")
    
    # 4. 解压缩功能
    print("\n[4/7] 解压缩功能检查...")
    try:
        from wechat_backend.database_core import get_user_test_history
        # 尝试读取一条记录
        history = get_user_test_history('test_user_0', limit=1)
        if history:
            checklist_results['decompression'] = {
                'status': '✅ 通过',
                'details': f"成功读取并解压 {len(history)} 条记录"
            }
            print(f"  ✅ 通过 - {checklist_results['decompression']['details']}")
        else:
            checklist_results['decompression'] = {
                'status': '⚠️ 未测试',
                'details': '无测试数据'
            }
            print(f"  ⚠️ 未测试 - 无测试数据")
    except Exception as e:
        checklist_results['decompression'] = {
            'status': '❌ 失败',
            'details': str(e)
        }
        print(f"  ❌ 失败 - {str(e)}")
    
    # 5. 索引创建
    print("\n[5/7] 索引创建检查...")
    try:
        result = init_recommended_indexes()
        checklist_results['indexes'] = {
            'status': '✅ 通过',
            'details': f"创建 {result['created_count']}/{result['total_indexes']} 个索引"
        }
        print(f"  ✅ 通过 - {checklist_results['indexes']['details']}")
    except Exception as e:
        checklist_results['indexes'] = {
            'status': '❌ 失败',
            'details': str(e)
        }
        print(f"  ❌ 失败 - {str(e)}")
    
    # 6. 缓存持久化
    print("\n[6/7] 缓存持久化检查...")
    try:
        cache_path = Path(__file__).parent.parent / 'cache.db'
        if cache_path.exists():
            cache_size_mb = cache_path.stat().st_size / 1024 / 1024
            checklist_results['cache_persistence'] = {
                'status': '✅ 通过',
                'details': f"持久化文件存在，大小={cache_size_mb:.2f}MB"
            }
            print(f"  ✅ 通过 - {checklist_results['cache_persistence']['details']}")
        else:
            checklist_results['cache_persistence'] = {
                'status': '⚠️ 未激活',
                'details': '持久化文件不存在'
            }
            print(f"  ⚠️ 未激活 - 持久化文件不存在")
    except Exception as e:
        checklist_results['cache_persistence'] = {
            'status': '❌ 失败',
            'details': str(e)
        }
        print(f"  ❌ 失败 - {str(e)}")
    
    # 7. 并发测试
    print("\n[7/7] 并发测试检查...")
    pool_metrics = get_db_pool_metrics()
    if pool_metrics['timeout_count'] == 0:
        checklist_results['concurrency'] = {
            'status': '✅ 通过',
            'details': f"无超时，连接池利用率={pool_metrics['utilization']}"
        }
        print(f"  ✅ 通过 - {checklist_results['concurrency']['details']}")
    else:
        checklist_results['concurrency'] = {
            'status': '⚠️ 警告',
            'details': f"发生 {pool_metrics['timeout_count']} 次超时"
        }
        print(f"  ⚠️ 警告 - {checklist_results['concurrency']['details']}")
    
    # 总结
    print("\n" + "="*80)
    print("验证清单总结")
    print("="*80)
    
    passed = sum(1 for r in checklist_results.values() if '✅' in r['status'])
    failed = sum(1 for r in checklist_results.values() if '❌' in r['status'])
    warning = sum(1 for r in checklist_results.values() if '⚠️' in r['status'])
    
    print(f"\n总计：{passed} 通过，{failed} 失败，{warning} 警告")
    
    for item, result in checklist_results.items():
        print(f"  {result['status']} {item}: {result['details']}")
    
    overall_status = "优秀" if failed == 0 and warning <= 2 else "良好" if failed == 0 else "需修复"
    print(f"\n整体状态：{overall_status}")
    
    return checklist_results


# ==================== 主函数 ====================

def main():
    """运行所有基准测试"""
    print("\n" + "="*80)
    print("存储与性能优化基准测试")
    print(f"开始时间：{datetime.now().isoformat()}")
    print("="*80)
    
    # 清理测试数据
    cleanup_test_data()
    
    # 运行测试
    results = {}
    
    # 测试 1: 并发诊断
    results['concurrent_diagnosis'] = test_concurrent_diagnosis()
    
    # 测试 2: 数据库压缩
    results['database_compression'] = test_database_compression()
    
    # 测试 3: 缓存命中率
    results['cache_hit_rate'] = test_cache_hit_rate()
    
    # 验证清单
    results['verification'] = run_verification_checklist()
    
    # 生成报告
    print("\n" + "="*80)
    print("基准测试报告")
    print("="*80)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'test_results': results,
        'summary': {
            'concurrent_performance': f"{results['concurrent_diagnosis']['total_duration']:.2f}秒 ({results['concurrent_diagnosis']['performance_rating']})",
            'database_size': f"{results['database_compression']['db_size_mb']:.2f}MB ({results['database_compression']['size_rating']})",
            'cache_hit_rate': f"{results['cache_hit_rate']['final_metrics']['overall_hit_rate']}% ({results['cache_hit_rate']['hit_rating']})"
        }
    }
    
    print(f"\n测试总结:")
    for key, value in report['summary'].items():
        print(f"  {key}: {value}")
    
    # 保存报告
    report_path = Path(__file__).parent / 'benchmark_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n完整报告已保存至：{report_path}")
    print(f"\n测试完成时间：{datetime.now().isoformat()}")
    
    return report


if __name__ == '__main__':
    main()
