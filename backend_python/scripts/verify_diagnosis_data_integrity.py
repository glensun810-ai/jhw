#!/usr/bin/env python3
"""
品牌诊断报告数据完整性验证工具
创建日期：2026-03-13
版本：1.0

功能：
1. 验证数据库表结构完整性
2. 验证诊断报告数据一致性
3. 验证结果明细完整性
4. 修复发现的问题
5. 生成验证报告
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(backend_dir)

sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from wechat_backend.database_connection_pool import get_db_pool
from wechat_backend.logging_config import db_logger


class DiagnosisDataValidator:
    """诊断数据完整性验证器"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.stats = {}
    
    def validate_all(self, execution_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行完整验证
        
        参数:
            execution_id: 执行 ID（可选，如果为空则验证所有）
        
        返回:
            验证报告
        """
        print("=" * 70)
        print("品牌诊断报告数据完整性验证")
        print("=" * 70)
        
        self.issues = []
        self.warnings = []
        self.stats = {}
        
        # 1. 验证表结构
        self._validate_table_structure()
        
        # 2. 验证表数据
        self._validate_table_data()
        
        # 3. 验证数据一致性
        self._validate_data_consistency()
        
        # 4. 验证特定执行（如果提供）
        if execution_id:
            self._validate_execution(execution_id)
        
        # 5. 生成统计
        self._generate_stats()
        
        # 6. 生成报告
        report = self._generate_report()
        
        # 7. 打印报告
        self._print_report(report)
        
        return report
    
    def _validate_table_structure(self):
        """验证表结构"""
        print("\n📐 验证表结构...")
        
        try:
            pool = get_db_pool()
            conn = pool.get_connection()
            
            try:
                cursor = conn.cursor()
                
                # 检查 diagnosis_reports 表
                print("  检查 diagnosis_reports 表...")
                cursor.execute("""
                    SELECT name FROM PRAGMA_TABLE_INFO('diagnosis_reports')
                """)
                report_columns = set(row[0] for row in cursor.fetchall())
                
                required_report_columns = {
                    'id', 'execution_id', 'user_id', 'brand_name',
                    'competitor_brands', 'selected_models', 'custom_questions',
                    'status', 'progress', 'stage', 'is_completed',
                    'created_at', 'updated_at', 'completed_at',
                    'data_schema_version', 'server_version', 'checksum'
                }
                
                missing_report = required_report_columns - report_columns
                if missing_report:
                    self.issues.append(f"diagnosis_reports 表缺少字段：{missing_report}")
                    print(f"    ❌ 缺少字段：{missing_report}")
                else:
                    print(f"    ✅ 字段完整 ({len(report_columns)} 个)")
                
                # 检查 diagnosis_results 表
                print("  检查 diagnosis_results 表...")
                cursor.execute("""
                    SELECT name FROM PRAGMA_TABLE_INFO('diagnosis_results')
                """)
                results_columns = set(row[0] for row in cursor.fetchall())
                
                required_results_columns = {
                    'id', 'report_id', 'execution_id', 'brand', 'question', 'model',
                    'response_content', 'response_latency', 'geo_data',
                    'quality_score', 'quality_level', 'quality_details',
                    'status', 'error_message', 'created_at',
                    # 新增字段（2026-03-13）
                    'raw_response', 'extracted_brand', 'extraction_method', 'platform',
                    'response_metadata', 'tokens_used', 'prompt_tokens',
                    'completion_tokens', 'cached_tokens',
                    'finish_reason', 'request_id', 'model_version', 'reasoning_content',
                    'api_endpoint', 'service_tier',
                    'retry_count', 'is_fallback', 'updated_at'
                }
                
                missing_results = required_results_columns - results_columns
                if missing_results:
                    self.warnings.append(f"diagnosis_results 表缺少可选字段：{missing_results}")
                    print(f"    ⚠️ 缺少可选字段：{missing_results}")
                else:
                    print(f"    ✅ 字段完整 ({len(results_columns)} 个)")
                
                # 检查 diagnosis_analysis 表
                print("  检查 diagnosis_analysis 表...")
                cursor.execute("""
                    SELECT name FROM PRAGMA_TABLE_INFO('diagnosis_analysis')
                """)
                analysis_columns = set(row[0] for row in cursor.fetchall())
                
                if len(analysis_columns) > 0:
                    print(f"    ✅ 字段存在 ({len(analysis_columns)} 个)")
                else:
                    self.issues.append("diagnosis_analysis 表不存在或无字段")
                
                # 检查 diagnosis_snapshots 表
                print("  检查 diagnosis_snapshots 表...")
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='diagnosis_snapshots'
                """)
                snapshots_exists = cursor.fetchone() is not None
                
                if snapshots_exists:
                    print(f"    ✅ 表存在")
                else:
                    self.warnings.append("diagnosis_snapshots 表不存在（可选）")
                    print(f"    ⚠️ 表不存在（可选）")
                
            finally:
                pool.return_connection(conn)
                
        except Exception as e:
            self.issues.append(f"表结构验证失败：{e}")
            print(f"    ❌ 验证失败：{e}")
    
    def _validate_table_data(self):
        """验证表数据"""
        print("\n📊 验证表数据...")
        
        try:
            pool = get_db_pool()
            conn = pool.get_connection()
            
            try:
                cursor = conn.cursor()
                
                # 统计各表记录数
                tables = ['diagnosis_reports', 'diagnosis_results', 'diagnosis_analysis']
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  {table}: {count} 条记录")
                    self.stats[f'{table}_count'] = count
                
                # 检查诊断报告状态分布
                print("\n  诊断报告状态分布:")
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM diagnosis_reports
                    GROUP BY status
                """)
                
                for row in cursor.fetchall():
                    print(f"    {row[0]}: {row[1]}")
                
                # 检查质量评分分布
                print("\n  诊断结果质量评分分布:")
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN quality_score >= 90 THEN '优秀 (90-100)'
                            WHEN quality_score >= 70 THEN '良好 (70-89)'
                            WHEN quality_score >= 50 THEN '中等 (50-69)'
                            WHEN quality_score > 0 THEN '较差 (<50)'
                            ELSE '未评分'
                        END as quality_range,
                        COUNT(*) as count
                    FROM diagnosis_results
                    GROUP BY quality_range
                    ORDER BY quality_range
                """)
                
                for row in cursor.fetchall():
                    print(f"    {row[0]}: {row[1]}")
                
            finally:
                pool.return_connection(conn)
                
        except Exception as e:
            self.issues.append(f"表数据验证失败：{e}")
            print(f"    ❌ 验证失败：{e}")
    
    def _validate_data_consistency(self):
        """验证数据一致性"""
        print("\n🔍 验证数据一致性...")
        
        try:
            pool = get_db_pool()
            conn = pool.get_connection()
            
            try:
                cursor = conn.cursor()
                
                # 1. 检查孤立的结果记录（没有对应报告）
                print("  检查孤立的结果记录...")
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
                    self.issues.append(f"发现 {orphan_count} 条孤立的结果记录")
                    print(f"    ❌ 发现 {orphan_count} 条孤立记录")
                else:
                    print(f"    ✅ 无孤立记录")
                
                # 2. 检查 execution_id 不一致
                print("  检查 execution_id 一致性...")
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM diagnosis_results dr
                    JOIN diagnosis_reports dp ON dr.report_id = dp.id
                    WHERE dr.execution_id != dp.execution_id
                """)
                
                mismatch_count = cursor.fetchone()[0]
                if mismatch_count > 0:
                    self.issues.append(f"发现 {mismatch_count} 条 execution_id 不匹配记录")
                    print(f"    ❌ 发现 {mismatch_count} 条不匹配记录")
                else:
                    print(f"    ✅ execution_id 全部匹配")
                
                # 3. 检查品牌字段一致性
                print("  检查品牌字段一致性...")
                cursor.execute("""
                    SELECT COUNT(DISTINCT brand) as brands
                    FROM diagnosis_results
                    WHERE brand IS NULL OR brand = ''
                """)
                
                empty_brand_count = cursor.fetchone()[0]
                if empty_brand_count > 0:
                    self.warnings.append(f"发现 {empty_brand_count} 条品牌字段为空的记录")
                    print(f"    ⚠️ 发现 {empty_brand_count} 条品牌字段为空")
                else:
                    print(f"    ✅ 品牌字段完整")
                
                # 4. 检查 extracted_brand 字段
                print("  检查 extracted_brand 字段...")
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           COUNT(extracted_brand) as with_extracted
                    FROM diagnosis_results
                """)
                
                row = cursor.fetchone()
                total = row[0]
                with_extracted = row[1]
                
                if total > 0:
                    percentage = (with_extracted / total) * 100
                    print(f"    提取率：{percentage:.1f}% ({with_extracted}/{total})")
                    
                    if percentage < 50:
                        self.warnings.append(f"extracted_brand 提取率较低：{percentage:.1f}%")
                else:
                    print(f"    ⚠️ 无数据")
                
                # 5. 检查响应内容完整性
                print("  检查响应内容完整性...")
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           COUNT(CASE WHEN response_content IS NOT NULL 
                                      AND response_content != '' 
                                      AND response_content NOT LIKE '%空响应%' 
                                 THEN 1 END) as valid
                    FROM diagnosis_results
                """)
                
                row = cursor.fetchone()
                total = row[0]
                valid = row[1]
                
                if total > 0:
                    percentage = (valid / total) * 100
                    print(f"    有效率：{percentage:.1f}% ({valid}/{total})")
                    
                    if percentage < 80:
                        self.warnings.append(f"响应内容有效率较低：{percentage:.1f}%")
                else:
                    print(f"    ⚠️ 无数据")
                
            finally:
                pool.return_connection(conn)
                
        except Exception as e:
            self.issues.append(f"数据一致性验证失败：{e}")
            print(f"    ❌ 验证失败：{e}")
    
    def _validate_execution(self, execution_id: str):
        """验证特定执行的完整性"""
        print(f"\n🔍 验证执行 {execution_id}...")
        
        try:
            pool = get_db_pool()
            conn = pool.get_connection()
            
            try:
                cursor = conn.cursor()
                
                # 1. 检查报告是否存在
                print("  检查报告...")
                cursor.execute("""
                    SELECT id, status, progress, is_completed, brand_name
                    FROM diagnosis_reports
                    WHERE execution_id = ?
                """, (execution_id,))
                
                report = cursor.fetchone()
                
                if not report:
                    self.issues.append(f"执行 {execution_id} 的报告不存在")
                    print(f"    ❌ 报告不存在")
                    return
                
                print(f"    ✅ 报告存在 (ID={report[0]}, 品牌={report[4]})")
                print(f"       状态={report[1]}, 进度={report[2]}%, 完成={report[3]}")
                
                # 2. 检查结果明细
                print("  检查结果明细...")
                cursor.execute("""
                    SELECT COUNT(*), 
                           COUNT(DISTINCT brand),
                           COUNT(DISTINCT model),
                           AVG(quality_score)
                    FROM diagnosis_results
                    WHERE execution_id = ?
                """, (execution_id,))
                
                result_stats = cursor.fetchone()
                
                print(f"    结果数量：{result_stats[0]}")
                print(f"    品牌数量：{result_stats[1]}")
                print(f"    模型数量：{result_stats[2]}")
                print(f"    平均质量分：{result_stats[3]:.2f}" if result_stats[3] else "    平均质量分：N/A")
                
                if result_stats[0] == 0:
                    self.warnings.append(f"执行 {execution_id} 没有结果明细")
                
                # 3. 检查分析数据
                print("  检查分析数据...")
                cursor.execute("""
                    SELECT analysis_type, COUNT(*)
                    FROM diagnosis_analysis
                    WHERE execution_id = ?
                    GROUP BY analysis_type
                """, (execution_id,))
                
                analyses = cursor.fetchall()
                
                if analyses:
                    print(f"    分析类型：{len(analyses)}")
                    for analysis in analyses:
                        print(f"      - {analysis[0]}")
                else:
                    self.warnings.append(f"执行 {execution_id} 没有分析数据")
                    print(f"    ⚠️ 无分析数据")
                
            finally:
                pool.return_connection(conn)
                
        except Exception as e:
            self.issues.append(f"执行验证失败：{e}")
            print(f"    ❌ 验证失败：{e}")
    
    def _generate_stats(self):
        """生成统计信息"""
        print("\n📊 生成统计信息...")
        
        try:
            pool = get_db_pool()
            conn = pool.get_connection()
            
            try:
                cursor = conn.cursor()
                
                # 总体统计
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT dp.execution_id) as total_executions,
                        COUNT(dr.id) as total_results,
                        AVG(dr.quality_score) as avg_quality,
                        COUNT(DISTINCT dr.brand) as total_brands
                    FROM diagnosis_reports dp
                    LEFT JOIN diagnosis_results dr ON dp.id = dr.report_id
                """)
                
                stats = cursor.fetchone()
                self.stats['total_executions'] = stats[0]
                self.stats['total_results'] = stats[1]
                self.stats['avg_quality_score'] = round(stats[2], 2) if stats[2] else 0
                self.stats['total_brands'] = stats[3]
                
                print(f"  总执行数：{stats[0]}")
                print(f"  总结果数：{stats[1]}")
                print(f"  平均质量分：{stats[2]:.2f}" if stats[2] else "  平均质量分：N/A")
                print(f"  总品牌数：{stats[3]}")
                
            finally:
                pool.return_connection(conn)
                
        except Exception as e:
            print(f"    ❌ 统计生成失败：{e}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'is_valid': len(self.issues) == 0,
            'issues_count': len(self.issues),
            'warnings_count': len(self.warnings),
            'issues': self.issues,
            'warnings': self.warnings,
            'stats': self.stats,
            'health_score': self._calculate_health_score()
        }
    
    def _calculate_health_score(self) -> float:
        """计算健康评分（0-100）"""
        base_score = 100.0
        
        # 每个问题扣 10 分
        base_score -= len(self.issues) * 10
        
        # 每个警告扣 2 分
        base_score -= len(self.warnings) * 2
        
        return max(0, min(100, base_score))
    
    def _print_report(self, report: Dict[str, Any]):
        """打印验证报告"""
        print("\n" + "=" * 70)
        print("验证报告")
        print("=" * 70)
        
        print(f"\n验证时间：{report['timestamp']}")
        print(f"健康评分：{report['health_score']:.1f}/100")
        print(f"问题数量：{report['issues_count']}")
        print(f"警告数量：{report['warnings_count']}")
        
        if report['issues']:
            print("\n❌ 问题列表:")
            for issue in report['issues']:
                print(f"  - {issue}")
        
        if report['warnings']:
            print("\n⚠️ 警告列表:")
            for warning in report['warnings']:
                print(f"  - {warning}")
        
        print("\n📊 统计信息:")
        for key, value in report['stats'].items():
            print(f"  {key}: {value}")
        
        if report['is_valid']:
            print("\n✅ 数据完整性验证通过")
        else:
            print("\n❌ 数据完整性验证失败，请修复上述问题")
        
        print("\n" + "=" * 70)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='品牌诊断报告数据完整性验证工具')
    parser.add_argument('--execution-id', '-e', help='要验证的执行 ID')
    parser.add_argument('--output', '-o', help='输出报告文件路径')
    
    args = parser.parse_args()
    
    # 创建验证器
    validator = DiagnosisDataValidator()
    
    # 执行验证
    report = validator.validate_all(execution_id=args.execution_id)
    
    # 输出到文件（如果指定）
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 报告已保存到：{args.output}")
        except Exception as e:
            print(f"\n❌ 保存报告失败：{e}")
    
    # 返回退出码
    sys.exit(0 if report['is_valid'] else 1)


if __name__ == '__main__':
    main()
