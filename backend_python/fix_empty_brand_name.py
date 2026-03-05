#!/usr/bin/env python3
"""
修复空品牌名称问题

用于修复由于前端提交数据为空导致的品牌名称缺失问题
"""

import sqlite3
import json
import sys
from wechat_backend.database_connection_pool import DB_PATH, get_db_pool


def fix_empty_brand_name(execution_id: str, new_brand_name: str = None):
    """
    修复空品牌名称
    
    Args:
        execution_id: 执行 ID
        new_brand_name: 新的品牌名称（可选，默认使用执行 ID 作为占位符）
    """
    if new_brand_name is None:
        new_brand_name = f"未知品牌-{execution_id[:8]}"
    
    conn = None
    try:
        conn = get_db_pool().get_connection()
        cursor = conn.cursor()
        
        # 检查记录是否存在
        cursor.execute(
            'SELECT id, brand_name, status FROM diagnosis_reports WHERE execution_id = ?',
            (execution_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            print(f"❌ 未找到执行 ID: {execution_id}")
            return False
        
        report_id, current_brand_name, status = row
        
        # 检查是否需要修复
        if current_brand_name and current_brand_name.strip():
            print(f"✅ 品牌名称已存在：'{current_brand_name}'，无需修复")
            return False
        
        print(f"📋 修复前状态:")
        print(f"   报告 ID: {report_id}")
        print(f"   执行 ID: {execution_id}")
        print(f"   当前品牌名称：'{current_brand_name}' (空)")
        print(f"   状态：{status}")
        print()
        
        # 更新品牌名称
        cursor.execute(
            'UPDATE diagnosis_reports SET brand_name = ?, updated_at = datetime("now") WHERE id = ?',
            (new_brand_name, report_id)
        )
        conn.commit()
        
        print(f"✅ 修复成功:")
        print(f"   新品牌名称：'{new_brand_name}'")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            get_db_pool().return_connection(conn)


def cleanup_empty_report(execution_id: str):
    """
    清理空报告记录（当品牌名称为空且结果也为空时）
    
    Args:
        execution_id: 执行 ID
    """
    conn = None
    try:
        conn = get_db_pool().get_connection()
        cursor = conn.cursor()
        
        # 检查记录
        cursor.execute(
            'SELECT id, brand_name FROM diagnosis_reports WHERE execution_id = ?',
            (execution_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            print(f"❌ 未找到执行 ID: {execution_id}")
            return False
        
        report_id, brand_name = row
        
        # 检查结果数量
        cursor.execute(
            'SELECT COUNT(*) as count FROM diagnosis_results WHERE execution_id = ?',
            (execution_id,)
        )
        result_count = cursor.fetchone()['count']
        
        # 检查分析数据
        cursor.execute(
            'SELECT COUNT(*) as count FROM diagnosis_analysis WHERE execution_id = ?',
            (execution_id,)
        )
        analysis_count = cursor.fetchone()['count']
        
        print(f"📋 当前记录状态:")
        print(f"   报告 ID: {report_id}")
        print(f"   品牌名称：'{brand_name}' (空)")
        print(f"   结果数量：{result_count}")
        print(f"   分析数据：{analysis_count} 项")
        print()
        
        # 如果结果数量 <= 1 且品牌名称为空，建议清理
        if result_count <= 1 and (not brand_name or not brand_name.strip()):
            confirm = input(f"⚠️  确认删除此空报告记录？(y/N): ")
            if confirm.lower() != 'y':
                print("   已取消")
                return False
            
            # 删除相关记录（顺序：分析 -> 结果 -> 报告）
            cursor.execute('DELETE FROM diagnosis_analysis WHERE execution_id = ?', (execution_id,))
            cursor.execute('DELETE FROM diagnosis_results WHERE execution_id = ?', (execution_id,))
            cursor.execute('DELETE FROM diagnosis_reports WHERE execution_id = ?', (execution_id,))
            conn.commit()
            
            print(f"✅ 已删除空报告记录：{execution_id}")
            return True
        else:
            print(f"⚠️  记录有数据，不建议清理")
            return False
        
    except Exception as e:
        print(f"❌ 操作失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            get_db_pool().return_connection(conn)


if __name__ == '__main__':
    execution_id = '4aae8fab-175d-43af-a33a-548fc9e6a17b'
    
    if len(sys.argv) > 1:
        execution_id = sys.argv[1]
    
    print(f"{'='*60}")
    print(f"修复空品牌名称问题")
    print(f"{'='*60}\n")
    
    # 选项 1: 修复品牌名称
    print("选项 1: 修复品牌名称")
    print("-" * 40)
    fix_empty_brand_name(execution_id)
    print()
    
    # 选项 2: 清理空记录
    print("选项 2: 清理空记录（如果结果也很少）")
    print("-" * 40)
    cleanup_empty_report(execution_id)
    print()
    
    print(f"{'='*60}")
    print("修复完成")
    print(f"{'='*60}")
