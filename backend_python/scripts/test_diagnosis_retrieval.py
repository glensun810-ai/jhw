#!/usr/bin/env python3
"""
品牌诊断报告数据库检索测试脚本
创建日期：2026-03-13
版本：1.0

功能：
1. 测试从数据库完整读取诊断报告
2. 验证返回数据的完整性
3. 测试数据重建功能
4. 生成测试报告
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(backend_dir)

sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

# 导入服务层
from wechat_backend.diagnosis_report_service import DiagnosisReportService
from wechat_backend.diagnosis_report_repository import DiagnosisResultRepository, DiagnosisReportRepository
from wechat_backend.database_connection_pool import get_db_pool
from wechat_backend.logging_config import db_logger


class DiagnosisRetrievalTester:
    """诊断报告检索测试器"""
    
    def __init__(self):
        self.service = DiagnosisReportService()
        self.result_repo = DiagnosisResultRepository()
        self.report_repo = DiagnosisReportRepository()
        self.test_results = []
    
    def test_retrieve_complete_report(self, execution_id: str) -> Dict[str, Any]:
        """
        测试完整报告检索
        
        参数:
            execution_id: 执行 ID
        
        返回:
            测试结果
        """
        print("=" * 70)
        print(f"测试完整报告检索：{execution_id}")
        print("=" * 70)
        
        test_result = {
            'execution_id': execution_id,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'steps': [],
            'data_quality': {},
            'issues': []
        }
        
        try:
            # 步骤 1: 获取报告主数据
            print("\n📄 步骤 1: 获取报告主数据...")
            report = self.report_repo.get_by_execution_id(execution_id)
            
            if not report:
                test_result['issues'].append("报告主数据不存在")
                print("  ❌ 报告主数据不存在")
                self._record_step(test_result, "获取报告主数据", False)
                return test_result
            
            print(f"  ✅ 报告主数据获取成功")
            print(f"     - 品牌：{report.get('brand_name', 'N/A')}")
            print(f"     - 状态：{report.get('status', 'N/A')}")
            print(f"     - 进度：{report.get('progress', 0)}%")
            print(f"     - 完成：{report.get('is_completed', False)}")
            self._record_step(test_result, "获取报告主数据", True)
            
            # 步骤 2: 获取结果明细
            print("\n📊 步骤 2: 获取结果明细...")
            results = self.result_repo.get_by_execution_id(execution_id)
            
            if not results or len(results) == 0:
                print("  ⚠️ 结果明细为空，尝试重建...")
                results = self._try_rebuild_results(execution_id)
                
                if not results or len(results) == 0:
                    test_result['issues'].append("结果明细为空且重建失败")
                    print("  ❌ 结果明细重建失败")
                    self._record_step(test_result, "获取结果明细", False)
                else:
                    print(f"  ✅ 结果明细重建成功，数量：{len(results)}")
                    self._record_step(test_result, "获取结果明细（重建）", True)
            else:
                print(f"  ✅ 结果明细获取成功，数量：{len(results)}")
                self._record_step(test_result, "获取结果明细", True)
            
            # 步骤 3: 验证结果字段完整性
            if results:
                print("\n🔍 步骤 3: 验证结果字段完整性...")
                field_check = self._check_result_fields(results)
                
                for field, status in field_check.items():
                    if status == 'missing':
                        print(f"  ❌ {field}: 缺失")
                        test_result['issues'].append(f"结果字段缺失：{field}")
                    elif status == 'empty':
                        print(f"  ⚠️ {field}: 空值")
                    else:
                        print(f"  ✅ {field}: 正常")
                
                test_result['data_quality']['field_completeness'] = field_check
            
            # 步骤 4: 测试服务层 get_history_report
            print("\n📋 步骤 4: 测试服务层 get_history_report...")
            full_report = self.service.get_history_report(execution_id)
            
            if not full_report:
                print("  ❌ get_history_report 返回空")
                test_result['issues'].append("get_history_report 返回空")
                self._record_step(test_result, "get_history_report", False)
            else:
                print("  ✅ get_history_report 获取成功")
                self._record_step(test_result, "get_history_report", True)
                
                # 检查返回数据的关键字段
                print("\n🔍 步骤 5: 验证完整报告数据...")
                
                # 检查 brandDistribution
                brand_dist = full_report.get('brandDistribution', {})
                if brand_dist and brand_dist.get('data'):
                    print(f"  ✅ brandDistribution: {len(brand_dist.get('data', {}))} 个品牌")
                else:
                    print(f"  ⚠️ brandDistribution: 空")
                    test_result['issues'].append("brandDistribution 为空")
                
                # 检查 sentimentDistribution
                sentiment_dist = full_report.get('sentimentDistribution', {})
                if sentiment_dist and sentiment_dist.get('data'):
                    print(f"  ✅ sentimentDistribution: 正常")
                else:
                    print(f"  ⚠️ sentimentDistribution: 空")
                
                # 检查 keywords
                keywords = full_report.get('keywords', [])
                if keywords and len(keywords) > 0:
                    print(f"  ✅ keywords: {len(keywords)} 个")
                else:
                    print(f"  ⚠️ keywords: 空")
                
                # 检查 results
                report_results = full_report.get('results', [])
                print(f"  ✅ results: {len(report_results)} 条")
                
                # 检查 detailed_results
                detailed_results = full_report.get('detailed_results', [])
                print(f"  ✅ detailed_results: {len(detailed_results)} 条")
                
                test_result['data_quality']['has_brand_distribution'] = bool(brand_dist and brand_dist.get('data'))
                test_result['data_quality']['has_sentiment_distribution'] = bool(sentiment_dist and sentiment_dist.get('data'))
                test_result['data_quality']['has_keywords'] = bool(keywords and len(keywords) > 0)
                test_result['data_quality']['results_count'] = len(report_results)
            
            # 步骤 6: 数据质量评估
            print("\n📊 步骤 6: 数据质量评估...")
            quality_assessment = self._assess_data_quality(full_report, results)
            
            for metric, value in quality_assessment.items():
                if isinstance(value, bool):
                    status = "✅" if value else "❌"
                    print(f"  {status} {metric}: {value}")
                else:
                    print(f"  📊 {metric}: {value}")
            
            test_result['data_quality'].update(quality_assessment)
            
            # 总体评估
            test_result['success'] = len(test_result['issues']) == 0
            test_result['quality_score'] = self._calculate_quality_score(test_result['data_quality'])
            
            print("\n" + "=" * 70)
            if test_result['success']:
                print(f"✅ 测试通过 - 质量评分：{test_result['quality_score']:.1f}/100")
            else:
                print(f"⚠️ 测试发现以下问题:")
                for issue in test_result['issues']:
                    print(f"  - {issue}")
            print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ 测试失败：{e}")
            db_logger.error(f"测试失败：{e}", exc_info=True)
            test_result['issues'].append(f"测试异常：{str(e)}")
        
        self.test_results.append(test_result)
        return test_result
    
    def _try_rebuild_results(self, execution_id: str) -> List[Dict[str, Any]]:
        """尝试重建结果数据"""
        print("  尝试重建结果数据...")
        
        try:
            # 尝试 1: 使用 ORM
            try:
                from wechat_backend.models import DiagnosisResult
                db_results = DiagnosisResult.query.filter_by(execution_id=execution_id).all()
                
                if db_results:
                    print(f"    从 ORM 重建：{len(db_results)} 条")
                    results = []
                    for r in db_results:
                        result_dict = {
                            'id': r.id,
                            'execution_id': r.execution_id,
                            'brand': r.brand,
                            'extracted_brand': r.extracted_brand,
                            'question': r.question,
                            'model': r.model,
                            'response_content': r.response_content,
                            'status': r.status,
                            'quality_score': r.quality_score,
                        }
                        
                        try:
                            result_dict['geo_data'] = json.loads(r.geo_data) if r.geo_data else {}
                        except:
                            result_dict['geo_data'] = {}
                        
                        result_dict['response'] = {
                            'content': r.response_content,
                            'latency': r.response_latency
                        }
                        
                        results.append(result_dict)
                    
                    return results
            except Exception as orm_err:
                print(f"    ORM 重建失败：{orm_err}")
            
            # 尝试 2: 使用 SQL
            print("    尝试 SQL 直接查询...")
            pool = get_db_pool()
            conn = pool.get_connection()
            conn.row_factory = sqlite3.Row
            
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM diagnosis_results
                    WHERE execution_id = ?
                    ORDER BY brand, question, model
                """, (execution_id,))
                
                db_rows = cursor.fetchall()
                
                if db_rows:
                    print(f"    从 SQL 重建：{len(db_rows)} 条")
                    results = []
                    for row in db_rows:
                        item = dict(row)
                        
                        try:
                            item['geo_data'] = json.loads(item['geo_data']) if item.get('geo_data') else {}
                        except:
                            item['geo_data'] = {}
                        
                        item['response'] = {
                            'content': item['response_content'],
                            'latency': item.get('response_latency')
                        }
                        
                        results.append(item)
                    
                    return results
            finally:
                pool.return_connection(conn)
                
        except Exception as e:
            print(f"    重建失败：{e}")
        
        return []
    
    def _check_result_fields(self, results: List[Dict[str, Any]]) -> Dict[str, str]:
        """检查结果字段完整性"""
        if not results:
            return {}
        
        first_result = results[0]
        
        # 定义关键字段
        required_fields = {
            'brand': '品牌名称',
            'extracted_brand': '提取的品牌',
            'question': '问题',
            'model': '模型',
            'response_content': '响应内容',
            'quality_score': '质量评分',
            'geo_data': 'GEO 数据',
        }
        
        # 新增字段（2026-03-13）
        enhanced_fields = {
            'tokens_used': 'Token 使用',
            'finish_reason': '完成原因',
            'request_id': '请求 ID',
            'reasoning_content': '推理内容',
        }
        
        check_result = {}
        
        # 检查必需字段
        for field, desc in required_fields.items():
            if field not in first_result:
                check_result[field] = 'missing'
            elif first_result[field] is None or first_result[field] == '':
                check_result[field] = 'empty'
            else:
                check_result[field] = 'ok'
        
        # 检查增强字段
        for field, desc in enhanced_fields.items():
            if field not in first_result:
                check_result[field] = 'not_applicable'  # 可选字段
            elif first_result[field] is None or first_result[field] == '':
                check_result[field] = 'empty'
            else:
                check_result[field] = 'ok'
        
        return check_result
    
    def _assess_data_quality(self, full_report: Dict[str, Any], results: List[Dict]) -> Dict[str, Any]:
        """评估数据质量"""
        assessment = {}
        
        if not full_report:
            assessment['overall_quality'] = 'poor'
            return assessment
        
        # 1. 品牌分布质量
        brand_dist = full_report.get('brandDistribution', {})
        brand_count = len(brand_dist.get('data', {}))
        assessment['brand_count'] = brand_count
        assessment['brand_distribution_quality'] = 'good' if brand_count >= 3 else 'fair' if brand_count >= 1 else 'poor'
        
        # 2. 情感分析质量
        sentiment_dist = full_report.get('sentimentDistribution', {})
        has_sentiment = bool(sentiment_dist and sentiment_dist.get('data'))
        assessment['has_sentiment_analysis'] = has_sentiment
        
        # 3. 关键词质量
        keywords = full_report.get('keywords', [])
        keyword_count = len(keywords)
        assessment['keyword_count'] = keyword_count
        assessment['keyword_quality'] = 'good' if keyword_count >= 5 else 'fair' if keyword_count >= 1 else 'poor'
        
        # 4. 结果完整性
        results_count = len(results) if results else len(full_report.get('results', []))
        assessment['results_count'] = results_count
        assessment['results_completeness'] = 'good' if results_count >= 10 else 'fair' if results_count >= 1 else 'poor'
        
        # 5. 总体质量
        quality_scores = {
            'brand_distribution_quality': {'good': 100, 'fair': 60, 'poor': 0},
            'keyword_quality': {'good': 100, 'fair': 60, 'poor': 0},
            'results_completeness': {'good': 100, 'fair': 60, 'poor': 0},
        }
        
        total_score = 0
        count = 0
        
        for key, mapping in quality_scores.items():
            value = assessment.get(key, 'poor')
            total_score += mapping.get(value, 0)
            count += 1
        
        if has_sentiment:
            total_score += 100
            count += 1
        
        avg_score = total_score / count if count > 0 else 0
        
        assessment['overall_quality'] = 'excellent' if avg_score >= 90 else 'good' if avg_score >= 70 else 'fair' if avg_score >= 50 else 'poor'
        assessment['overall_score'] = round(avg_score, 2)
        
        return assessment
    
    def _calculate_quality_score(self, data_quality: Dict[str, Any]) -> float:
        """计算质量评分"""
        score = 100.0
        
        # 缺少品牌分布扣 30 分
        if not data_quality.get('has_brand_distribution', True):
            score -= 30
        
        # 缺少情感分析扣 20 分
        if not data_quality.get('has_sentiment_distribution', True):
            score -= 20
        
        # 缺少关键词扣 20 分
        if not data_quality.get('has_keywords', True):
            score -= 20
        
        # 结果数量不足扣 10-30 分
        results_count = data_quality.get('results_count', 0)
        if results_count < 5:
            score -= 30
        elif results_count < 10:
            score -= 15
        elif results_count < 20:
            score -= 5
        
        return max(0, score)
    
    def _record_step(self, test_result: Dict[str, Any], step_name: str, success: bool):
        """记录测试步骤"""
        test_result['steps'].append({
            'name': step_name,
            'success': success,
            'timestamp': datetime.now().isoformat()
        })
    
    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed_tests': sum(1 for r in self.test_results if r['success']),
            'failed_tests': sum(1 for r in self.test_results if not r['success']),
            'results': self.test_results,
            'overall_success_rate': round(
                sum(1 for r in self.test_results if r['success']) / len(self.test_results) * 100, 2
            ) if self.test_results else 0
        }


def get_latest_execution_id() -> str:
    """获取最近的已完成执行 ID"""
    try:
        pool = get_db_pool()
        conn = pool.get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT execution_id 
                FROM diagnosis_reports 
                WHERE is_completed = 1 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                return row[0]
            
            # 如果没有已完成的，获取任意一个
            cursor.execute("""
                SELECT execution_id 
                FROM diagnosis_reports 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            return row[0] if row else None
            
        finally:
            pool.return_connection(conn)
            
    except Exception as e:
        db_logger.error(f"获取执行 ID 失败：{e}")
        return None


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='品牌诊断报告数据库检索测试')
    parser.add_argument('--execution-id', '-e', help='要测试的执行 ID')
    parser.add_argument('--output', '-o', help='输出报告文件路径')
    parser.add_argument('--all', '-a', action='store_true', help='测试所有已完成的执行')
    
    args = parser.parse_args()
    
    tester = DiagnosisRetrievalTester()
    
    if args.all:
        # 测试所有已完成的执行
        try:
            pool = get_db_pool()
            conn = pool.get_connection()
            
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT execution_id 
                    FROM diagnosis_reports 
                    WHERE is_completed = 1 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                
                execution_ids = [row[0] for row in cursor.fetchall()]
                
                if not execution_ids:
                    print("⚠️ 没有已完成的执行记录")
                    return
                
                print(f"发现 {len(execution_ids)} 个已完成的执行\n")
                
                for exec_id in execution_ids:
                    tester.test_retrieve_complete_report(exec_id)
                    print("\n")
                    
            finally:
                pool.return_connection(conn)
                
        except Exception as e:
            print(f"❌ 获取执行列表失败：{e}")
            return
    
    elif args.execution_id:
        # 测试指定的执行
        tester.test_retrieve_complete_report(args.execution_id)
    
    else:
        # 使用最近的执行
        execution_id = get_latest_execution_id()
        
        if not execution_id:
            print("❌ 未找到任何执行记录")
            return
        
        print(f"使用最近的执行：{execution_id}\n")
        tester.test_retrieve_complete_report(execution_id)
    
    # 生成测试报告
    test_report = tester.generate_test_report()
    
    print("\n" + "=" * 70)
    print("测试报告摘要")
    print("=" * 70)
    print(f"总测试数：{test_report['total_tests']}")
    print(f"通过数：{test_report['passed_tests']}")
    print(f"失败数：{test_report['failed_tests']}")
    print(f"成功率：{test_report['overall_success_rate']}%")
    print("=" * 70)
    
    # 输出到文件（如果指定）
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(test_report, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 测试报告已保存到：{args.output}")
        except Exception as e:
            print(f"\n❌ 保存测试报告失败：{e}")


if __name__ == '__main__':
    main()
