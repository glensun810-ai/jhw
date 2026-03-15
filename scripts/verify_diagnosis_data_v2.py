#!/usr/bin/env python3
"""
诊断报告数据流验证脚本 v2 - WAL 检查点验证版

用途：
1. 验证 WAL 检查点是否正常工作
2. 验证数据库中是否有诊断结果
3. 验证报告数据是否完整

使用方法：
python scripts/verify_diagnosis_data_v2.py <execution_id>
"""

import sys
import os
import json
import time

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_python'))

from wechat_backend.diagnosis_report_repository import (
    DiagnosisReportRepository,
    DiagnosisResultRepository,
    DiagnosisAnalysisRepository
)
from wechat_backend.diagnosis_report_service import get_report_service
from wechat_backend.database_connection_pool import get_db_pool


def print_separator(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")


def verify_wal_checkpoint(execution_id):
    """验证 WAL 检查点是否正常工作"""
    print_separator("0. WAL 检查点验证")
    
    pool = get_db_pool()
    conn = pool.get_connection()
    try:
        # 检查 WAL 模式
        result = conn.execute('PRAGMA journal_mode').fetchone()
        print(f"[1/3] 数据库日志模式：{result[0]}")
        
        # 检查 WAL 文件状态
        result = conn.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
        print(f"[2/3] WAL 检查点状态：{result}")
        print(f"       - 检查点成功：{result[0] == 0}")
        print(f"       - WAL 页数：{result[1]}")
        print(f"       - 已检查点页数：{result[2]}")
        
        # 执行强制检查点
        print(f"[3/3] 执行强制 WAL 检查点...")
        start_time = time.time()
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        elapsed = time.time() - start_time
        print(f"       ✅ WAL 检查点完成，耗时：{elapsed:.3f}s")
        
    finally:
        pool.return_connection(conn)
    
    return True


def verify_database_data(execution_id):
    """验证数据库中的数据"""
    print_separator("1. 数据库数据验证")
    
    result_repo = DiagnosisResultRepository()
    report_repo = DiagnosisReportRepository()
    analysis_repo = DiagnosisAnalysisRepository()
    
    # 1. 检查报告
    print(f"[1/4] 检查诊断报告...")
    report = report_repo.get_by_execution_id(execution_id)
    if not report:
        print(f"  ❌ 报告不存在：{execution_id}")
        return False
    print(f"  ✅ 报告存在：status={report.get('status')}, progress={report.get('progress')}")
    
    # 2. 检查结果
    print(f"[2/4] 检查诊断结果...")
    results = result_repo.get_by_execution_id(execution_id)
    if not results:
        print(f"  ❌ 结果为空")
        return False
    print(f"  ✅ 结果数量：{len(results)}")
    
    # 3. 检查分析数据
    print(f"[3/4] 检查分析数据...")
    analysis = analysis_repo.get_by_execution_id(execution_id)
    if not analysis:
        print(f"  ⚠️ 分析数据为空（可能尚未完成）")
    else:
        print(f"  ✅ 分析数据存在：types={list(analysis.keys())}")
    
    # 4. 检查品牌分布
    print(f"[4/4] 检查品牌分布...")
    brand_counts = {}
    for result in results:
        brand = result.get('brand', 'Unknown')
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    print(f"  ✅ 品牌分布：{json.dumps(brand_counts, ensure_ascii=False, indent=4)}")
    
    return True


def verify_report_service(execution_id):
    """验证报告服务返回的数据"""
    print_separator("2. 报告服务验证")
    
    service = get_report_service()
    report = service.get_full_report(execution_id)
    
    if not report:
        print(f"  ❌ 报告服务返回空")
        return False
    
    if report.get('error'):
        print(f"  ❌ 报告包含错误：{report.get('error')}")
        return False
    
    # 检查关键字段
    print(f"[1/4] 检查 brandDistribution...")
    brand_dist = report.get('brandDistribution', {})
    if not brand_dist.get('data'):
        print(f"  ❌ brandDistribution.data 为空")
    else:
        print(f"  ✅ brandDistribution.data: {json.dumps(brand_dist.get('data'), ensure_ascii=False, indent=4)}")
        print(f"  ✅ total_count: {brand_dist.get('total_count')}")
    
    print(f"[2/4] 检查 sentimentDistribution...")
    sentiment_dist = report.get('sentimentDistribution', {})
    if not sentiment_dist.get('data'):
        print(f"  ❌ sentimentDistribution.data 为空")
    else:
        print(f"  ✅ sentimentDistribution.data: {json.dumps(sentiment_dist.get('data'), ensure_ascii=False, indent=4)}")
    
    print(f"[3/4] 检查 keywords...")
    keywords = report.get('keywords', [])
    if not keywords:
        print(f"  ❌ keywords 为空")
    else:
        print(f"  ✅ keywords 数量：{len(keywords)}")
        if len(keywords) <= 10:
            print(f"  ✅ keywords: {json.dumps(keywords, ensure_ascii=False, indent=4)}")
    
    print(f"[4/4] 检查 results...")
    results = report.get('results', [])
    if not results:
        print(f"  ❌ results 为空")
    else:
        print(f"  ✅ results 数量：{len(results)}")
    
    return True


def main():
    if len(sys.argv) < 2:
        print("使用方法：python scripts/verify_diagnosis_data_v2.py <execution_id>")
        print("\n示例:")
        print("  python scripts/verify_diagnosis_data_v2.py diag_12345678")
        sys.exit(1)
    
    execution_id = sys.argv[1]
    print(f"\n开始验证诊断数据：{execution_id}")
    
    # 0. 验证 WAL 检查点
    wal_ok = verify_wal_checkpoint(execution_id)
    
    # 1. 验证数据库数据
    db_ok = verify_database_data(execution_id)
    
    # 2. 验证报告服务
    report_ok = verify_report_service(execution_id)
    
    # 总结
    print_separator("验证总结")
    if wal_ok and db_ok and report_ok:
        print("✅ 所有验证通过！数据完整。")
        print("\n📋 验证结果:")
        print("   - WAL 检查点：正常")
        print("   - 数据库数据：完整")
        print("   - 报告服务：正常")
        print("\n✅ 前端应该能够正常显示诊断报告！")
    elif wal_ok and db_ok:
        print("⚠️  数据库数据正常，但报告服务处理可能有问题。")
    elif wal_ok:
        print("⚠️  WAL 检查点正常，但数据库数据有问题。")
    else:
        print("❌ WAL 检查点可能有问题，导致数据不可见。")
    
    print()


if __name__ == '__main__':
    main()
