"""
自动化巡航模块 - 处理定时任务与趋势预警
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

from .logging_config import api_logger
from .database import DB_PATH
from .security.sql_protection import SafeDatabaseQuery, sql_protector
from .models import get_brand_test_result


class CruiseController:
    """自动化巡航控制器"""
    
    def __init__(self):
        self.scheduler = None
        self.db_path = DB_PATH
        self.logger = api_logger
        self._init_scheduler()
        
    def _init_scheduler(self):
        """初始化调度器"""
        # 使用SQLite作为作业存储
        jobstores = {
            'default': SQLAlchemyJobStore(url=f'sqlite:///{self.db_path}')
        }
        
        executors = {
            'default': ThreadPoolExecutor(20),
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
        
        # 启动调度器
        self.scheduler.start()
        self.logger.info("Cruise controller scheduler initialized and started")
    
    def schedule_diagnostic_task(
        self, 
        user_openid: str, 
        brand_name: str, 
        interval_hours: int,
        ai_models: List[str],
        questions: List[str] = None,
        job_id: str = None
    ) -> str:
        """
        调度诊断任务
        
        Args:
            user_openid: 用户openid
            brand_name: 品牌名称
            interval_hours: 间隔小时数
            ai_models: AI模型列表
            questions: 自定义问题列表
            job_id: 作业ID，如果不提供则自动生成
            
        Returns:
            str: 作业ID
        """
        if not job_id:
            job_id = f"cruise_{user_openid}_{brand_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 验证输入
        if not sql_protector.validate_input(user_openid):
            raise ValueError("Invalid user_openid")
        if not sql_protector.validate_input(brand_name):
            raise ValueError("Invalid brand_name")
        if not isinstance(interval_hours, int) or interval_hours <= 0:
            raise ValueError("interval_hours must be a positive integer")
        
        # 从这里调用实际的诊断任务函数
        from .cruise_executor import run_diagnostic_task
        job = self.scheduler.add_job(
            run_diagnostic_task,
            'interval',
            hours=interval_hours,
            id=job_id,
            args=[user_openid, brand_name, ai_models, questions or []],
            replace_existing=True
        )
        
        self.logger.info(f"Scheduled diagnostic task for brand '{brand_name}' every {interval_hours} hours, job_id: {job_id}")
        
        return job_id
    
    def cancel_scheduled_task(self, job_id: str):
        """取消已调度的任务"""
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Cancelled scheduled task with job_id: {job_id}")
        except Exception as e:
            self.logger.error(f"Failed to cancel job {job_id}: {e}")
            raise
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取所有已调度的任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'interval': str(job.trigger.interval) if hasattr(job.trigger, 'interval') else 'unknown'
            })
        return jobs
    
    def compare_results(self, current_result: Dict[str, Any], previous_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        对比两次任务结果，判断是否需要预警

        Args:
            current_result: 当前结果
            previous_result: 上一次结果

        Returns:
            Dict: 包含预警信息的字典
        """
        alert_info = {
            'is_alert': False,
            'alert_reasons': [],
            'changes': {}
        }

        # 检查排名变化
        current_rank = self._extract_rank(current_result)
        previous_rank = self._extract_rank(previous_result)

        if current_rank is not None and previous_rank is not None:
            rank_change = current_rank - previous_rank  # 正数表示排名下降
            alert_info['changes']['rank_change'] = rank_change

            if rank_change >= 2:  # 排名下降2名或更多
                alert_info['is_alert'] = True
                alert_info['alert_reasons'].append(f"排名下降了 {rank_change} 名")

        # 检查负面评价数变化
        current_negative_count = self._count_negative_evidence(current_result)
        previous_negative_count = self._count_negative_evidence(previous_result)

        if current_negative_count is not None and previous_negative_count is not None:
            negative_change = current_negative_count - previous_negative_count
            alert_info['changes']['negative_change'] = negative_change

            if negative_change > 0:  # 负面评价数增加
                alert_info['is_alert'] = True
                alert_info['alert_reasons'].append(f"负面评价数增加了 {negative_change} 个")

        # 检查情感分数变化
        current_sentiment = self._extract_sentiment_score(current_result)
        previous_sentiment = self._extract_sentiment_score(previous_result)

        if current_sentiment is not None and previous_sentiment is not None:
            sentiment_change = current_sentiment - previous_sentiment
            alert_info['changes']['sentiment_change'] = sentiment_change

            if sentiment_change < -10:  # 情感分数下降超过10分
                alert_info['is_alert'] = True
                alert_info['alert_reasons'].append(f"情感分数下降了 {abs(sentiment_change):.2f} 分")

        return alert_info

    def compare_with_previous_result(self, current_record_id: int, brand_name: str) -> Dict[str, Any]:
        """
        将当前测试结果与之前的测试结果进行比较

        Args:
            current_record_id: 当前记录ID
            brand_name: 品牌名称

        Returns:
            Dict: 比较结果和预警信息
        """
        # 从数据库获取当前记录
        current_record = self._get_test_record_by_id(current_record_id)
        if not current_record:
            self.logger.error(f"Current record not found: {current_record_id}")
            return {
                'is_alert': False,
                'alert_reasons': ['无法获取当前测试结果'],
                'changes': {},
                'current_result': None,
                'previous_result': None
            }

        # 获取该品牌的上一条记录
        previous_record = self._get_previous_test_record(brand_name, current_record['test_date'])
        if not previous_record:
            self.logger.info(f"No previous record found for brand: {brand_name}")
            return {
                'is_alert': False,  # 第一次测试不需要预警
                'alert_reasons': ['这是首次测试，无历史数据对比'],
                'changes': {},
                'current_result': current_record,
                'previous_result': None
            }

        # 提取需要比较的数据
        current_result = self._extract_comparison_data(current_record)
        previous_result = self._extract_comparison_data(previous_record)

        # 进行比较
        comparison_result = self.compare_results(current_result, previous_result)

        # 添加结果数据
        comparison_result['current_result'] = current_record
        comparison_result['previous_result'] = previous_record

        return comparison_result

    def _get_test_record_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取测试记录"""
        safe_query = SafeDatabaseQuery(self.db_path)

        rows = safe_query.execute_query('''
            SELECT id, brand_name, test_date, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary, detailed_results
            FROM test_records
            WHERE id = ?
        ''', (record_id,))

        if rows:
            row = rows[0]
            return {
                'id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': json.loads(row[7]) if row[7] else {},
                'detailed_results': json.loads(row[8]) if row[8] else []
            }
        return None

    def _get_previous_test_record(self, brand_name: str, current_date: str) -> Optional[Dict[str, Any]]:
        """获取指定品牌在指定日期之前的最新测试记录"""
        safe_query = SafeDatabaseQuery(self.db_path)

        rows = safe_query.execute_query('''
            SELECT id, brand_name, test_date, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary, detailed_results
            FROM test_records
            WHERE brand_name = ? AND test_date < ?
            ORDER BY test_date DESC
            LIMIT 1
        ''', (brand_name, current_date))

        if rows:
            row = rows[0]
            return {
                'id': row[0],
                'brand_name': row[1],
                'test_date': row[2],
                'ai_models_used': json.loads(row[3]) if row[3] else [],
                'questions_used': json.loads(row[4]) if row[4] else [],
                'overall_score': row[5],
                'total_tests': row[6],
                'results_summary': json.loads(row[7]) if row[7] else {},
                'detailed_results': json.loads(row[8]) if row[8] else []
            }
        return None

    def _extract_comparison_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """从测试记录中提取用于比较的数据"""
        # 尝试从results_summary或detailed_results中提取相关信息
        results_summary = record.get('results_summary', {})
        detailed_results = record.get('detailed_results', [])

        # 构建比较数据结构
        comparison_data = {
            'exposure_analysis': {
                'brand_details': {}
            },
            'evidence_chain': []  # 从detailed_results中提取负面信息
        }

        # 从detailed_results中提取品牌详情
        brand_stats = {}
        negative_evidence = []

        for detail in detailed_results:
            brand = detail.get('brand', 'unknown')
            if brand not in brand_stats:
                brand_stats[brand] = {
                    'sentiment_score': 0,
                    'count': 0
                }

            # 累积情感分数
            sentiment = detail.get('sentiment_score', 0)
            if sentiment:
                brand_stats[brand]['sentiment_score'] += sentiment
                brand_stats[brand]['count'] += 1

                # 检查是否为负面内容（可以根据实际业务逻辑调整）
                response = detail.get('response', '').lower()
                if any(keyword in response for keyword in ['不好', '差', '问题', '缺点', '负面', '糟糕', '失望']):
                    negative_evidence.append({
                        'negative_fragment': response[:100],
                        'associated_url': 'unknown',
                        'source_name': detail.get('aiModel', 'unknown'),
                        'risk_level': 'Medium'
                    })

        # 计算平均情感分数
        for brand, stats in brand_stats.items():
            if stats['count'] > 0:
                avg_sentiment = stats['sentiment_score'] / stats['count']
                brand_stats[brand]['sentiment_score'] = avg_sentiment

        comparison_data['exposure_analysis']['brand_details'] = brand_stats
        comparison_data['evidence_chain'] = negative_evidence

        # 也尝试从results_summary中获取排名信息
        if 'ranking_list' in results_summary:
            comparison_data['exposure_analysis']['ranking_list'] = results_summary['ranking_list']

        return comparison_data
    
    def _extract_rank(self, result: Dict[str, Any]) -> Optional[int]:
        """从结果中提取排名"""
        try:
            # 从exposure_analysis中提取排名
            exposure_analysis = result.get('exposure_analysis', {})
            brand_details = exposure_analysis.get('brand_details', {})
            
            # 假设我们要获取主品牌的排名
            # 这里需要根据实际的brand_name来确定主品牌
            for brand_name, details in brand_details.items():
                if 'rank' in details:
                    return details['rank']
                    
            # 如果没有明确的rank，尝试从ranking_list获取位置
            ranking_list = exposure_analysis.get('ranking_list', [])
            if ranking_list:
                # 假设第一个品牌是主品牌
                main_brand = ranking_list[0] if ranking_list else None
                if main_brand and main_brand in brand_details:
                    # 如果brand_details中有对应的信息，返回其rank
                    brand_detail = brand_details[main_brand]
                    if 'rank' in brand_detail:
                        return brand_detail['rank']
                        
            return None
        except Exception as e:
            self.logger.error(f"Error extracting rank from result: {e}")
            return None
    
    def _count_negative_evidence(self, result: Dict[str, Any]) -> Optional[int]:
        """统计负面证据数量"""
        try:
            evidence_chain = result.get('evidence_chain', [])
            return len(evidence_chain)  # 简单计数所有证据项
        except Exception as e:
            self.logger.error(f"Error counting negative evidence: {e}")
            return None
    
    def _extract_sentiment_score(self, result: Dict[str, Any]) -> Optional[float]:
        """从结果中提取情感分数"""
        try:
            # 从exposure_analysis中提取情感分数
            exposure_analysis = result.get('exposure_analysis', {})
            brand_details = exposure_analysis.get('brand_details', {})
            
            # 获取主品牌的情感分数
            for brand_name, details in brand_details.items():
                if 'sentiment_score' in details:
                    return details['sentiment_score']
                    
            return None
        except Exception as e:
            self.logger.error(f"Error extracting sentiment score from result: {e}")
            return None
    
    def get_trend_data(self, brand_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取趋势数据
        
        Args:
            brand_name: 品牌名称
            days: 查询天数
            
        Returns:
            List: 时间序列数据
        """
        # 验证输入
        if not sql_protector.validate_input(brand_name):
            raise ValueError("Invalid brand_name")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 使用安全查询获取历史测试记录
        safe_query = SafeDatabaseQuery(self.db_path)
        
        # 获取指定品牌的历史记录
        records_data = safe_query.execute_query('''
            SELECT id, test_date, overall_score, detailed_results, results_summary
            FROM test_records
            WHERE brand_name = ? AND test_date >= ?
            ORDER BY test_date ASC
        ''', (brand_name, start_date))
        
        trend_data = []
        for row in records_data:
            record_id, test_date, overall_score, detailed_results_str, results_summary_str = row
            
            # 解析JSON数据
            detailed_results = json.loads(detailed_results_str) if detailed_results_str else []
            results_summary = json.loads(results_summary_str) if results_summary_str else {}
            
            # 尝试从detailed_results中提取更多信息
            avg_sentiment = self._calculate_avg_sentiment(detailed_results)
            rank = self._extract_rank_from_detailed(detailed_results, brand_name)
            
            trend_point = {
                'timestamp': test_date,
                'overall_score': overall_score,
                'sentiment_score': avg_sentiment,
                'rank': rank,
                'record_id': record_id
            }
            
            trend_data.append(trend_point)
        
        return trend_data
    
    def _calculate_avg_sentiment(self, detailed_results: List[Dict[str, Any]]) -> Optional[float]:
        """从详细结果中计算平均情感分数"""
        if not detailed_results:
            return None
        
        sentiment_scores = []
        for result in detailed_results:
            sentiment = result.get('sentiment_score')
            if sentiment is not None:
                sentiment_scores.append(sentiment)
        
        if sentiment_scores:
            return sum(sentiment_scores) / len(sentiment_scores)
        return None
    
    def _extract_rank_from_detailed(self, detailed_results: List[Dict[str, Any]], brand_name: str) -> Optional[int]:
        """从详细结果中提取特定品牌的排名"""
        # 这是一个简化版本，实际实现可能需要更复杂的逻辑
        # 根据品牌在结果中的出现频率或重要性来估算排名
        if not detailed_results:
            return None
        
        # 统计特定品牌的出现次数
        brand_count = 0
        for result in detailed_results:
            if result.get('brand', '').lower() == brand_name.lower():
                brand_count += 1
        
        # 这里只是一个示例逻辑，实际排名可能需要更复杂的算法
        if brand_count > 0:
            # 假设出现次数越多排名越高（数字越小）
            # 这只是示例，实际应根据具体业务逻辑调整
            return max(1, 11 - min(brand_count, 10))  # 返回1-10之间的排名
        
        return None
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Cruise controller scheduler shut down")