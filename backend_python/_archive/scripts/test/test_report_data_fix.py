#!/usr/bin/env python3
"""
品牌洞察报告数据流修复验证脚本

验证内容:
1. 数据库表结构是否正确
2. test_records 数据是否可查询
3. execution_id 是否正确提取
4. 数据解压缩是否正常
5. 报告数据服务是否正常工作

执行：python3 test_report_data_fix.py
"""

import sys
import os
import json
import gzip

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'wechat_backend'))
sys.path.insert(0, os.path.dirname(__file__))

from wechat_backend.database import get_connection
from wechat_backend.services.report_data_service import ReportDataService


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_database_tables():
    """检查数据库表结构"""
    print_header("1. 检查数据库表结构")
    
    from wechat_backend.database_core import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = [
        'test_records',
        'deep_intelligence_results',
        'brand_test_results',
        'task_statuses',
        'competitive_analysis',
        'negative_sources',
        'report_metadata'
    ]
    
    print(f"\n数据库路径：{conn.execute('PRAGMA database_list').fetchone()[2]}")
    print(f"\n所有表 ({len(tables)}): {', '.join(tables)}")
    
    print("\n必需表检查:")
    for table in required_tables:
        status = "✅" if table in tables else "❌"
        print(f"  {status} {table}")
    
    conn.close()
    return all(table in tables for table in required_tables)


def check_test_records_data():
    """检查 test_records 数据"""
    print_header("2. 检查 test_records 数据")
    
    from wechat_backend.database_core import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 统计总数
    cursor.execute("SELECT COUNT(*) FROM test_records")
    total = cursor.fetchone()[0]
    print(f"\ntest_records 总记录数：{total}")
    
    if total == 0:
        print("⚠️  无测试记录，请先运行品牌诊断测试")
        conn.close()
        return False
    
    # 查询最新记录
    cursor.execute("""
        SELECT id, brand_name, test_date, overall_score, 
               is_summary_compressed, is_detailed_compressed
        FROM test_records
        ORDER BY test_date DESC
        LIMIT 5
    """)
    
    print("\n最新 5 条测试记录:")
    print("-" * 80)
    execution_ids = []
    
    for row in cursor.fetchall():
        record_id, brand_name, test_date, score, summary_comp, detailed_comp = row
        print(f"\nID: {record_id}")
        print(f"  品牌：{brand_name}")
        print(f"  日期：{test_date}")
        print(f"  分数：{score}")
        print(f"  压缩状态：summary={summary_comp}, detailed={detailed_comp}")
        
        execution_ids.append((record_id, brand_name))
    
    conn.close()
    return execution_ids


def check_execution_id_extraction(record_id, brand_name):
    """检查 execution_id 提取"""
    print_header(f"3. 检查 execution_id 提取 (记录 ID: {record_id})")
    
    from wechat_backend.database_core import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT results_summary, is_summary_compressed
        FROM test_records
        WHERE id = ?
    """, (record_id,))
    
    row = cursor.fetchone()
    if not row:
        print("❌ 未找到记录")
        conn.close()
        return None
    
    summary_raw, is_compressed = row
    
    try:
        if is_compressed and summary_raw:
            print("  检测到压缩数据，正在解压...")
            summary_bytes = gzip.decompress(summary_raw)
            summary = json.loads(summary_bytes.decode('utf-8'))
        elif summary_raw:
            summary = json.loads(summary_raw)
        else:
            print("⚠️  results_summary 为空")
            conn.close()
            return None
        
        execution_id = summary.get('execution_id', '')
        total_tests = summary.get('total_tests', 0)
        competitors = summary.get('competitor_brands', [])
        
        print(f"\n  ✅ execution_id: {execution_id}")
        print(f"  ✅ total_tests: {total_tests}")
        print(f"  ✅ competitor_brands: {competitors}")
        
        conn.close()
        return execution_id
        
    except Exception as e:
        print(f"❌ 解析失败：{e}")
        conn.close()
        return None


def check_report_data_service(execution_id):
    """检查报告数据服务"""
    print_header(f"4. 检查报告数据服务 (execution_id: {execution_id})")
    
    if not execution_id:
        print("⚠️  execution_id 为空，跳过测试")
        return False
    
    try:
        service = ReportDataService()
        
        print("\n  正在获取基础数据...")
        base_data = service._get_base_data(execution_id)
        
        if not base_data:
            print("❌ 未获取到基础数据")
            return False
        
        print(f"\n  ✅ 品牌：{base_data.get('brand_name', 'N/A')}")
        print(f"  ✅ 分数：{base_data.get('overall_score', 0)}")
        print(f"  ✅ 测试数：{base_data.get('total_tests', 0)}")
        print(f"  ✅ 平台评分：{len(base_data.get('platform_scores', []))} 个")
        print(f"  ✅ 维度评分：{base_data.get('dimension_scores', {})}")
        
        # 检查 detailed_results
        detailed_results = base_data.get('detailed_results', [])
        if detailed_results:
            print(f"\n  ✅ detailed_results: {len(detailed_results)} 条")
            for i, result in enumerate(detailed_results[:2]):
                if isinstance(result, dict):
                    print(f"    [{i}] 模型：{result.get('model', 'N/A')}, " +
                          f"分数：{result.get('score', 'N/A')}, " +
                          f"排名：{result.get('rank', 'N/A')}")
        else:
            print("\n  ⚠️  detailed_results 为空")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告数据服务测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def check_competitive_data_generation(base_data):
    """检查竞品数据生成"""
    print_header("5. 检查竞品数据生成")
    
    if not base_data:
        print("⚠️  基础数据为空，跳过测试")
        return False
    
    try:
        service = ReportDataService()
        
        print("\n  正在生成竞品数据...")
        competitive_data = service._get_or_generate_competitive_data(
            base_data.get('execution_id', 'test'),
            base_data
        )
        
        if not competitive_data:
            print("❌ 竞品数据生成失败")
            return False
        
        competitors = competitive_data.get('competitors', [])
        print(f"\n  ✅ 竞品数量：{len(competitors)}")
        
        for comp in competitors[:3]:
            print(f"\n    竞品：{comp.get('competitor_name', 'N/A')}")
            print(f"    分数：{comp.get('overall_score', 0)}")
            print(f"    优势：{len(comp.get('strengths', []))} 个")
        
        radar_data = competitive_data.get('radar_data', {})
        print(f"\n  ✅ 雷达图数据集：{len(radar_data.get('datasets', []))} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 竞品数据生成失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def check_negative_sources_generation(base_data):
    """检查负面信源生成"""
    print_header("6. 检查负面信源生成")
    
    if not base_data:
        print("⚠️  基础数据为空，跳过测试")
        return False
    
    try:
        service = ReportDataService()
        
        print("\n  正在生成负面信源数据...")
        negative_data = service._get_or_generate_negative_sources(
            base_data.get('execution_id', 'test'),
            base_data
        )
        
        if not negative_data:
            print("❌ 负面信源生成失败")
            return False
        
        sources = negative_data.get('sources', [])
        summary = negative_data.get('summary', {})
        
        print(f"\n  ✅ 负面信源数量：{len(sources)}")
        print(f"  ✅ 高风险：{summary.get('high_count', 0)}")
        print(f"  ✅ 中风险：{summary.get('medium_count', 0)}")
        print(f"  ✅ 低风险：{summary.get('low_count', 0)}")
        
        if sources:
            print("\n  前 3 个负面信源:")
            for source in sources[:3]:
                print(f"\n    来源：{source.get('source_name', 'N/A')}")
                print(f"    严重性：{source.get('severity', 'N/A')}")
                print(f"    建议：{source.get('recommendation', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 负面信源生成失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def run_full_report_test(execution_id):
    """运行完整报告生成测试"""
    print_header("7. 完整报告生成测试")
    
    if not execution_id:
        print("⚠️  execution_id 为空，跳过测试")
        return False
    
    try:
        service = ReportDataService()
        
        print("\n  正在生成完整报告...")
        print("  (这可能需要几秒钟)")
        
        import time
        start_time = time.time()
        
        report = service.generate_full_report(execution_id)
        
        generation_time = time.time() - start_time
        
        if not report:
            print("❌ 报告生成失败")
            return False
        
        print(f"\n  ✅ 报告生成完成 (耗时：{generation_time:.2f}秒)")
        
        # 检查报告结构
        print("\n  报告结构检查:")
        sections = [
            'reportMetadata',
            'executiveSummary',
            'brandHealth',
            'platformAnalysis',
            'competitiveAnalysis',
            'negativeSources',
            'roiAnalysis',
            'actionPlan'
        ]
        
        for section in sections:
            status = "✅" if section in report else "❌"
            print(f"    {status} {section}")
        
        # 显示关键指标
        if report.get('brandHealth'):
            health = report['brandHealth']
            print(f"\n  品牌健康度：{health.get('overall_score', 0)}")
        
        if report.get('executiveSummary'):
            summary = report['executiveSummary']
            print(f"  健康等级：{summary.get('health_grade', 'N/A')}")
            print(f"  关键发现：{len(summary.get('key_findings', []))} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ 完整报告生成失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("  品牌洞察报告数据流修复验证")
    print("  Report Data Flow Fix Verification")
    print("🚀" * 30)
    
    # 1. 检查数据库表
    tables_ok = check_database_tables()
    
    # 2. 检查 test_records 数据
    records = check_test_records_data()
    
    if not records:
        print("\n⚠️  没有测试记录，无法继续验证")
        print("\n建议：")
        print("  1. 在小程序中运行一次品牌诊断测试")
        print("  2. 确保测试完成后查看数据库")
        return False
    
    # 使用最新记录进行测试
    latest_record_id, latest_brand = records[0] if isinstance(records, list) else (None, None)
    
    # 3. 检查 execution_id 提取
    execution_id = check_execution_id_extraction(latest_record_id, latest_brand)
    
    if not execution_id:
        print("\n⚠️  无法提取 execution_id")
        print("\n可能原因:")
        print("  1. results_summary 字段为空")
        print("  2. results_summary 格式不正确")
        print("  3. 数据压缩但未正确解压")
        return False
    
    # 4. 检查报告数据服务
    service_ok = check_report_data_service(execution_id)
    
    if not service_ok:
        print("\n⚠️  报告数据服务测试失败")
    
    # 5. 获取基础数据进行后续测试
    try:
        service = ReportDataService()
        base_data = service._get_base_data(execution_id)
    except:
        base_data = None
    
    # 6. 检查竞品数据生成
    competitive_ok = check_competitive_data_generation(base_data)
    
    # 7. 检查负面信源生成
    negative_ok = check_negative_sources_generation(base_data)
    
    # 8. 完整报告生成测试
    full_report_ok = run_full_report_test(execution_id)
    
    # 总结
    print_header("验证总结")
    
    tests = [
        ("数据库表结构", tables_ok),
        ("test_records 数据", bool(records)),
        ("execution_id 提取", bool(execution_id)),
        ("报告数据服务", service_ok),
        ("竞品数据生成", competitive_ok),
        ("负面信源生成", negative_ok),
        ("完整报告生成", full_report_ok)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for name, result in tests:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！数据流修复成功！")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查日志")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
