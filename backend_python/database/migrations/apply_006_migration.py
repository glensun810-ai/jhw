#!/usr/bin/env python3
"""
品牌诊断报告完整性增强 - 数据库迁移脚本
创建日期：2026-03-13
版本：1.0

功能：
1. 应用数据库迁移脚本
2. 验证迁移结果
3. 数据完整性检查
"""

import os
import sys
import sqlite3
from datetime import datetime

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(backend_dir)

sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from wechat_backend.database_connection_pool import get_db_pool
from wechat_backend.logging_config import db_logger


def apply_migration():
    """应用数据库迁移"""
    print("=" * 70)
    print("品牌诊断报告完整性增强 - 数据库迁移")
    print("=" * 70)
    
    # 数据库路径（尝试多个可能的位置）
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'database.db'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'database.db'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database.db'),
        '/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db',
        '/Users/sgl/PycharmProjects/PythonProject/database.db',
    ]
    
    db_path = None
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            db_path = abs_path
            break
    
    if not db_path:
        # 使用默认路径
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database.db'))
    
    print(f"\n📍 数据库路径：{db_path}")
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在：{db_path}")
        return False
    
    # 读取迁移脚本
    migration_sql_path = os.path.join(
        os.path.dirname(__file__), 
        '006_enhance_diagnosis_results_fields.sql'
    )
    
    if not os.path.exists(migration_sql_path):
        print(f"❌ 迁移脚本不存在：{migration_sql_path}")
        return False
    
    with open(migration_sql_path, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    print(f"✅ 读取迁移脚本成功：{migration_sql_path}")
    
    # 执行迁移
    print("\n🔄 开始执行迁移...")
    
    try:
        # 使用数据库连接池获取连接
        pool = get_db_pool()
        conn = pool.get_connection()
        
        try:
            # 执行迁移脚本
            cursor = conn.cursor()
            cursor.executescript(migration_sql)
            conn.commit()
            
            print("✅ 迁移脚本执行成功")
            
            # 验证迁移结果
            print("\n🔍 验证迁移结果...")
            
            # 检查新增字段
            cursor.execute("""
                SELECT name 
                FROM PRAGMA_TABLE_INFO('diagnosis_results')
                WHERE name IN (
                    'response_metadata', 'tokens_used', 'prompt_tokens', 
                    'completion_tokens', 'cached_tokens', 'finish_reason',
                    'request_id', 'model_version', 'reasoning_content',
                    'api_endpoint', 'service_tier', 'retry_count', 
                    'is_fallback', 'updated_at'
                )
            """)
            
            new_columns = [row[0] for row in cursor.fetchall()]
            expected_columns = [
                'response_metadata', 'tokens_used', 'prompt_tokens',
                'completion_tokens', 'cached_tokens', 'finish_reason',
                'request_id', 'model_version', 'reasoning_content',
                'api_endpoint', 'service_tier', 'retry_count',
                'is_fallback', 'updated_at'
            ]
            
            print(f"  - 新增字段数量：{len(new_columns)}/{len(expected_columns)}")
            
            missing_columns = set(expected_columns) - set(new_columns)
            if missing_columns:
                print(f"  ⚠️ 缺失字段：{missing_columns}")
            else:
                print(f"  ✅ 所有新增字段都已创建")
            
            # 检查记录统计
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_records,
                    COUNT(DISTINCT execution_id) AS unique_executions
                FROM diagnosis_results
            """)
            
            stats = cursor.fetchone()
            print(f"  - 总记录数：{stats[0]}")
            print(f"  - 唯一 execution_id 数：{stats[1]}")
            
            # 检查索引
            cursor.execute("""
                SELECT name 
                FROM sqlite_master 
                WHERE type='index' AND tbl_name='diagnosis_results'
            """)
            
            indexes = [row[0] for row in cursor.fetchall()]
            print(f"  - 索引数量：{len(indexes)}")
            
            print("\n✅ 迁移验证完成")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 迁移执行失败：{e}")
            db_logger.error(f"迁移失败：{e}", exc_info=True)
            return False
            
        finally:
            pool.return_connection(conn)
            
    except Exception as e:
        print(f"❌ 数据库连接失败：{e}")
        db_logger.error(f"数据库连接失败：{e}", exc_info=True)
        return False


def verify_data_integrity():
    """验证数据完整性"""
    print("\n" + "=" * 70)
    print("数据完整性验证")
    print("=" * 70)
    
    try:
        pool = get_db_pool()
        conn = pool.get_connection()
        
        try:
            cursor = conn.cursor()
            
            # 1. 检查 diagnosis_reports 表
            print("\n📊 诊断报告表检查:")
            cursor.execute("SELECT COUNT(*) FROM diagnosis_reports")
            print(f"  - 报告总数：{cursor.fetchone()[0]}")
            
            # 2. 检查 diagnosis_results 表
            print("\n📊 诊断结果表检查:")
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total,
                    COUNT(DISTINCT execution_id) AS executions,
                    COUNT(DISTINCT brand) AS brands,
                    AVG(quality_score) AS avg_quality
                FROM diagnosis_results
            """)
            
            stats = cursor.fetchone()
            print(f"  - 结果总数：{stats[0]}")
            print(f"  - 执行数：{stats[1]}")
            print(f"  - 品牌数：{stats[2]}")
            print(f"  - 平均质量分：{stats[3]:.2f}" if stats[3] else "  - 平均质量分：N/A")
            
            # 3. 检查 diagnosis_analysis 表
            print("\n📊 诊断分析表检查:")
            cursor.execute("SELECT COUNT(*) FROM diagnosis_analysis")
            print(f"  - 分析记录数：{cursor.fetchone()[0]}")
            
            # 4. 检查 diagnosis_snapshots 表
            print("\n📊 诊断快照表检查:")
            cursor.execute("SELECT COUNT(*) FROM diagnosis_snapshots")
            count = cursor.fetchone()[0]
            print(f"  - 快照记录数：{count}" if count > 0 else "  - 无快照记录")
            
            # 5. 检查数据一致性
            print("\n🔍 数据一致性检查:")
            
            # 检查 orphan results（没有对应报告的 results）
            cursor.execute("""
                SELECT COUNT(*) 
                FROM diagnosis_results dr
                WHERE NOT EXISTS (
                    SELECT 1 FROM diagnosis_reports dp 
                    WHERE dp.id = dr.report_id
                )
            """)
            
            orphan_count = cursor.fetchone()[0]
            if orphan_count > 0:
                print(f"  ⚠️ 发现孤立结果记录：{orphan_count}")
            else:
                print(f"  ✅ 无孤立结果记录")
            
            # 检查 execution_id 一致性
            cursor.execute("""
                SELECT COUNT(*) 
                FROM diagnosis_results dr
                JOIN diagnosis_reports dp ON dr.report_id = dp.id
                WHERE dr.execution_id != dp.execution_id
            """)
            
            mismatch_count = cursor.fetchone()[0]
            if mismatch_count > 0:
                print(f"  ⚠️ execution_id 不匹配记录：{mismatch_count}")
            else:
                print(f"  ✅ execution_id 全部匹配")
            
            print("\n✅ 数据完整性验证完成")
            return True
            
        finally:
            pool.return_connection(conn)
            
    except Exception as e:
        print(f"❌ 验证失败：{e}")
        db_logger.error(f"验证失败：{e}", exc_info=True)
        return False


def test_retrieve_complete_report(execution_id=None):
    """测试从数据库完整读取诊断报告"""
    print("\n" + "=" * 70)
    print("测试完整报告检索")
    print("=" * 70)
    
    try:
        pool = get_db_pool()
        conn = pool.get_connection()
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            
            # 如果没有指定 execution_id，获取最近的一个
            if not execution_id:
                cursor.execute("""
                    SELECT execution_id 
                    FROM diagnosis_reports 
                    WHERE is_completed = 1
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if not row:
                    print("⚠️ 没有已完成的诊断报告")
                    return False
                
                execution_id = row['execution_id']
                print(f"\n使用最近的已完成报告：{execution_id}")
            
            # 1. 获取报告主数据
            print(f"\n📄 获取报告主数据：{execution_id}")
            cursor.execute("""
                SELECT * FROM diagnosis_reports 
                WHERE execution_id = ?
            """, (execution_id,))
            
            report_row = cursor.fetchone()
            if not report_row:
                print(f"❌ 报告不存在：{execution_id}")
                return False
            
            print(f"  ✅ 报告 ID: {report_row['id']}")
            print(f"  ✅ 品牌：{report_row['brand_name']}")
            print(f"  ✅ 状态：{report_row['status']}")
            print(f"  ✅ 进度：{report_row['progress']}%")
            
            # 2. 获取结果明细
            print(f"\n📊 获取结果明细...")
            cursor.execute("""
                SELECT * FROM diagnosis_results 
                WHERE execution_id = ?
                ORDER BY brand, question, model
            """, (execution_id,))
            
            results = cursor.fetchall()
            print(f"  ✅ 结果数量：{len(results)}")
            
            # 3. 检查结果字段完整性
            if results:
                print(f"\n🔍 检查结果字段完整性...")
                first_result = results[0]
                
                # 检查关键字段
                key_fields = [
                    'brand', 'extracted_brand', 'question', 'model',
                    'response_content', 'quality_score', 'geo_data',
                    'tokens_used', 'finish_reason', 'request_id'
                ]
                
                for field in key_fields:
                    if field in first_result.keys():
                        value = first_result[field]
                        if value is not None and value != '':
                            print(f"  ✅ {field}: {type(value).__name__}")
                        else:
                            print(f"  ⚠️ {field}: NULL/空")
                    else:
                        print(f"  ❌ {field}: 字段不存在")
                
                # 4. 统计品牌分布
                print(f"\n📊 品牌分布统计...")
                brand_counts = {}
                for result in results:
                    brand = result.get('extracted_brand') or result.get('brand')
                    if brand:
                        brand_counts[brand] = brand_counts.get(brand, 0) + 1
                
                for brand, count in brand_counts.items():
                    print(f"  - {brand}: {count}")
            
            # 5. 获取分析数据
            print(f"\n📊 获取分析数据...")
            cursor.execute("""
                SELECT analysis_type, analysis_data 
                FROM diagnosis_analysis 
                WHERE execution_id = ?
            """, (execution_id,))
            
            analyses = cursor.fetchall()
            print(f"  ✅ 分析类型数量：{len(analyses)}")
            for analysis in analyses:
                print(f"    - {analysis['analysis_type']}")
            
            print(f"\n✅ 完整报告检索测试成功")
            return True
            
        finally:
            pool.return_connection(conn)
            
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        db_logger.error(f"测试失败：{e}", exc_info=True)
        return False


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("品牌诊断报告数据库迁移工具")
    print("创建日期：2026-03-13")
    print("=" * 70)
    
    # 1. 应用迁移
    success = apply_migration()
    
    if not success:
        print("\n❌ 迁移失败，请检查日志")
        sys.exit(1)
    
    # 2. 验证数据完整性
    verify_data_integrity()
    
    # 3. 测试完整报告检索
    test_retrieve_complete_report()
    
    print("\n" + "=" * 70)
    print("✅ 所有操作完成")
    print("=" * 70)
