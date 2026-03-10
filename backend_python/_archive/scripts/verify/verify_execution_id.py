"""
验证特定 execution_id 的报告记录

用于排查 4aae8fab-175d-43af-a33a-548fc9e6a17b 执行 ID 的问题

使用方法:
    python verify_execution_id.py
"""

import sqlite3
import json
import os
import sys

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from wechat_backend.database_connection_pool import get_db_pool


def verify_execution_id(execution_id: str):
    """验证特定 execution_id 的报告记录"""
    
    print(f"\n{'='*60}")
    print(f"验证 execution_id: {execution_id}")
    print(f"{'='*60}\n")
    
    try:
        # 获取数据库连接
        conn = get_db_pool().get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 查询报告主记录
        print("1️⃣  查询诊断报告主记录...")
        cursor.execute('''
            SELECT * FROM diagnosis_reports 
            WHERE execution_id = ?
        ''', (execution_id,))
        
        row = cursor.fetchone()
        
        if not row:
            print(f"❌ 未找到执行 ID 为 {execution_id} 的记录")
            print("\n可能原因:")
            print("  - 记录尚未创建")
            print("  - 记录已被删除")
            print("  - execution_id 不正确")
            return
        
        report = dict(row)
        print(f"✅ 找到报告记录")
        print(f"\n   报告 ID: {report['id']}")
        print(f"   用户 ID: {report['user_id']}")
        print(f"   品牌名称：{report['brand_name']}")
        print(f"   状态：{report['status']}")
        print(f"   进度：{report['progress']}%")
        print(f"   阶段：{report['stage']}")
        print(f"   是否完成：{report['is_completed']}")
        print(f"   创建时间：{report['created_at']}")
        print(f"   更新时间：{report['updated_at']}")
        
        # 解析 JSON 字段
        if report['competitor_brands']:
            report['competitor_brands'] = json.loads(report['competitor_brands'])
        if report['selected_models']:
            report['selected_models'] = json.loads(report['selected_models'])
        if report['custom_questions']:
            report['custom_questions'] = json.loads(report['custom_questions'])
        
        # 2. 查询诊断结果
        print(f"\n2️⃣  查询诊断结果...")
        cursor.execute('''
            SELECT COUNT(*) as count, MIN(created_at) as first_result, MAX(created_at) as last_result
            FROM diagnosis_results 
            WHERE execution_id = ?
        ''', (execution_id,))
        
        result_row = cursor.fetchone()
        if result_row:
            result_count = result_row['count']
            print(f"   结果数量：{result_count}")
            if result_count > 0:
                print(f"   第一条结果：{result_row['first_result']}")
                print(f"   最后一条结果：{result_row['last_result']}")
                
                # 获取部分结果详情
                cursor.execute('''
                    SELECT id, brand, question, model, quality_score, quality_level
                    FROM diagnosis_results 
                    WHERE execution_id = ?
                    LIMIT 3
                ''', (execution_id,))
                
                print(f"\n   前 3 条结果详情:")
                for idx, result in enumerate(cursor.fetchall(), 1):
                    print(f"   {idx}. 品牌={result['brand']}, 质量分={result['quality_score']}, 等级={result['quality_level']}")
            else:
                print(f"   ⚠️  警告：没有结果记录")
        else:
            print(f"   ❌ 查询结果失败")
        
        # 3. 查询分析数据
        print(f"\n3️⃣  查询分析数据...")
        cursor.execute('''
            SELECT analysis_type, created_at
            FROM diagnosis_analysis 
            WHERE execution_id = ?
            ORDER BY analysis_type
        ''', (execution_id,))
        
        analysis_rows = cursor.fetchall()
        if analysis_rows:
            print(f"   分析数据类型：{len(analysis_rows)} 项")
            for analysis in analysis_rows:
                print(f"   - {analysis['analysis_type']} ({analysis['created_at']})")
        else:
            print(f"   ⚠️  警告：没有分析数据")
        
        # 4. 查询快照
        print(f"\n4️⃣  查询报告快照...")
        try:
            cursor.execute('''
                SELECT id, LENGTH(snapshot_data) as snapshot_data_size, created_at
                FROM diagnosis_snapshots
                WHERE execution_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (execution_id,))
            snapshot_row = cursor.fetchone()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print(f"   ⚠️  警告：diagnosis_snapshots 表不存在（非关键，快照功能可选）")
                snapshot_row = None
            else:
                raise

        if snapshot_row:
            print(f"   ✅ 存在快照")
            print(f"   快照 ID: {snapshot_row['id']}")
            print(f"   快照数据大小：{snapshot_row['snapshot_data_size']} bytes")
            print(f"   创建时间：{snapshot_row['created_at']}")
        else:
            print(f"   ⚠️  警告：没有快照记录")
        
        # 5. 数据完整性检查
        print(f"\n5️⃣  数据完整性检查...")
        issues = []

        # 检查状态一致性
        if report['status'] == 'completed' and not report['is_completed']:
            issues.append("状态为 completed 但 is_completed 为 false")

        if report['status'] == 'completed' and result_count == 0:
            issues.append("状态为 completed 但没有结果记录")

        if report['progress'] == 100 and report['status'] != 'completed':
            issues.append("进度为 100 但状态不是 completed")

        if report['is_completed'] and not snapshot_row:
            issues.append("标记为已完成但没有快照（非关键，快照表可能不存在）")

        # P0 修复：检查品牌名称是否为空
        if not report.get('brand_name') or not report['brand_name'].strip():
            issues.append("品牌名称为空（数据完整性问题）")

        # P0 修复：检查结果数量是否合理
        if result_count > 0 and result_count < 10:
            issues.append(f"结果数量过少：{result_count} 条（正常应该 >= 10 条）")

        # P0 修复：检查分析数据是否缺失
        if not analysis_rows or len(analysis_rows) == 0:
            issues.append("分析数据完全缺失（competitive_analysis, brand_scores 等）")
        elif len(analysis_rows) < 3:
            issues.append(f"分析数据不完整：只有 {len(analysis_rows)} 项（正常应该 >= 5 项）")

        if issues:
            print(f"   ❌ 发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"   ✅ 数据完整性检查通过")

        # 6. 诊断结论
        print(f"\n{'='*60}")
        print(f"📋 诊断结论")
        print(f"{'='*60}")

        if report['status'] == 'completed' and result_count > 0 and report.get('brand_name'):
            print(f"✅ 报告状态正常：已完成且有数据")
        elif report['status'] == 'completed' and result_count == 0:
            print(f"❌ 报告异常：状态为 completed 但无数据")
            print(f"   建议：检查 save_diagnosis_report 逻辑，确保数据在状态更新前已保存")
        elif report['status'] == 'completed' and not report.get('brand_name'):
            print(f"❌ 报告异常：品牌名称为空")
            print(f"   建议：检查前端提交数据或 create_report 逻辑")
        elif report['status'] == 'processing':
            print(f"⏳ 报告处理中：进度 {report['progress']}%, 阶段 {report['stage']}")
        elif report['status'] == 'failed':
            print(f"❌ 报告失败：请查看错误日志")
        else:
            print(f"⚠️  未知状态：{report['status']}")
        
        # 输出修复建议
        if issues:
            print(f"\n{'='*60}")
            print(f"🔧 修复建议")
            print(f"{'='*60}")
            if "品牌名称为空" in str(issues):
                print(f"1. 检查前端提交的品牌名称参数")
                print(f"2. 检查 create_report 函数是否正确保存 brand_name")
            if "分析数据完全缺失" in str(issues) or "分析数据不完整" in str(issues):
                print(f"1. 检查 analysis 数据保存逻辑")
                print(f"2. 确认 diagnosis_analysis 表写入是否正常")
            if "结果数量过少" in str(issues):
                print(f"1. 检查诊断执行过程是否提前终止")
                print(f"2. 确认 AI 请求是否全部成功完成")
        
    except Exception as e:
        print(f"\n❌ 验证失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        get_db_pool().return_connection(conn)
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    # 验证指定的 execution_id
    execution_id = '4aae8fab-175d-43af-a33a-548fc9e6a17b'
    
    # 也支持命令行参数
    if len(sys.argv) > 1:
        execution_id = sys.argv[1]
    
    verify_execution_id(execution_id)
