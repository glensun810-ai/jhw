#!/usr/bin/env python3
"""
重建历史报告文件数据

从数据库读取诊断数据，重新生成 JSON 文件。
用于修复修复前创建的空文件问题。
"""

import sys
import os
import json
import sqlite3
from datetime import datetime

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_python'))

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'diagnosis')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports')
DB_PATH = os.path.join(os.path.dirname(__file__), 'backend_python', 'database.db')

def get_file_archive_path(execution_id: str, created_at: datetime) -> str:
    """获取文件归档路径"""
    year = created_at.year
    month = f"{created_at.month:02d}"
    day = f"{created_at.day:02d}"
    
    return os.path.join(
        REPORTS_DIR,
        str(year), month, day,
        f"{execution_id}.json"
    )

def rebuild_report_file(execution_id: str):
    """重建单个报告的文件数据"""
    print(f"\n{'='*60}")
    print(f"重建报告文件：{execution_id}")
    print(f"{'='*60}\n")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. 获取报告主数据
        cursor.execute('''
            SELECT * FROM diagnosis_reports
            WHERE execution_id = ?
        ''', (execution_id,))
        report_row = cursor.fetchone()
        
        if not report_row:
            print(f"❌ 报告不存在：{execution_id}")
            return False
        
        report = dict(report_row)
        print(f"✅ 报告主数据：brand={report['brand_name']}, status={report['status']}")
        
        # 2. 获取结果数据
        cursor.execute('''
            SELECT * FROM diagnosis_results
            WHERE execution_id = ?
            ORDER BY brand, question, model
        ''', (execution_id,))
        result_rows = cursor.fetchall()
        
        results = []
        for row in result_rows:
            item = dict(row)
            # 解析 JSON 字段
            try:
                item['geo_data'] = json.loads(item['geo_data']) if item.get('geo_data') else {}
                item['quality_details'] = json.loads(item['quality_details']) if item.get('quality_details') else {}
            except:
                pass
            results.append(item)
        
        print(f"✅ 结果数据：{len(results)} 条")
        
        # 3. 获取分析数据
        cursor.execute('''
            SELECT analysis_type, analysis_data
            FROM diagnosis_analysis
            WHERE execution_id = ?
        ''', (execution_id,))
        analysis_rows = cursor.fetchall()
        
        analysis = {}
        for row in analysis_rows:
            try:
                analysis[row['analysis_type']] = json.loads(row['analysis_data'])
            except:
                pass
        
        print(f"✅ 分析数据：{len(analysis)} 项")
        
        # 4. 构建完整报告数据
        full_report = {
            'report': report,
            'results': results,
            'analysis': analysis
        }
        
        # 5. 计算品牌分布（简化版）
        brand_distribution = {}
        for r in results:
            brand = r.get('extracted_brand') or r.get('brand')
            if brand and str(brand).strip():
                brand = brand.strip()
                brand_distribution[brand] = brand_distribution.get(brand, 0) + 1
        
        full_report['brandDistribution'] = {
            'data': brand_distribution,
            'totalCount': sum(brand_distribution.values()),
            'successRate': 1.0 if brand_distribution else 0.0
        }
        
        print(f"✅ 品牌分布：{brand_distribution}")
        
        # 6. 保存到文件
        created_at = datetime.fromisoformat(report['created_at'])
        file_path = get_file_archive_path(execution_id, created_at)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 文件已保存：{file_path}")
        
        # 7. 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        if saved_data.get('results') and len(saved_data['results']) > 0:
            print(f"✅ 验证成功：文件包含 {len(saved_data['results'])} 条结果")
            return True
        else:
            print(f"❌ 验证失败：文件结果为空")
            return False
        
    except Exception as e:
        print(f"❌ 重建失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def rebuild_all_reports():
    """重建所有报告文件"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有报告
    cursor.execute('''
        SELECT execution_id, created_at
        FROM diagnosis_reports
        ORDER BY created_at DESC
    ''')
    reports = cursor.fetchall()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"开始重建 {len(reports)} 个报告文件")
    print(f"{'='*60}\n")
    
    success_count = 0
    fail_count = 0
    
    for execution_id, created_at in reports:
        # 检查文件是否已存在且非空
        created_dt = datetime.fromisoformat(created_at)
        file_path = get_file_archive_path(execution_id, created_dt)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('results') and len(data['results']) > 0:
                print(f"⏭️  跳过（文件已有有效数据）: {execution_id}")
                success_count += 1
                continue
        
        # 重建文件
        if rebuild_report_file(execution_id):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"重建完成!")
    print(f"  - 成功：{success_count}")
    print(f"  - 失败：{fail_count}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 重建单个报告
        exec_id = sys.argv[1]
        rebuild_report_file(exec_id)
    else:
        # 重建所有报告
        rebuild_all_reports()
