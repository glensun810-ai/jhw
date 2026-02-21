"""
市场情报服务 - 基准对比与心智占有率分析
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import statistics

from wechat_backend.logging_config import api_logger
from wechat_backend.database import DB_PATH
from wechat_backend.security.sql_protection import SafeDatabaseQuery, sql_protector


class MarketIntelligenceService:
    """市场情报服务，用于基准对比与心智占有率分析"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.logger = api_logger
        self.safe_query = SafeDatabaseQuery(self.db_path)
    
    def calculate_category_benchmarks(self, brand_name: str, category: str = None, days: int = 30) -> Dict[str, any]:
        """
        计算品类基准数据
        
        Args:
            brand_name: 我方品牌名称
            category: 品类名称（可选，如果提供则按品类筛选）
            days: 查询天数，默认30天
            
        Returns:
            Dict: 包含品类基准和我方品牌对比的数据
        """
        # 验证输入
        if not sql_protector.validate_input(brand_name):
            raise ValueError("Invalid brand_name")
        if category and not sql_protector.validate_input(category):
            raise ValueError("Invalid category")
        
        # 获取品类内的所有品牌数据
        all_brand_data = self._get_all_brand_data_in_category(category, days)
        
        if not all_brand_data:
            self.logger.warning(f"No data found for category: {category}")
            return {
                'category': category,
                'benchmark_data': {
                    'avg_rank_position': None,
                    'avg_sentiment_score': None,
                    'avg_mention_frequency': None
                },
                'my_brand_data': {
                    'brand_name': brand_name,
                    'rank_position': None,
                    'sentiment_position': None,
                    'mind_share': None,
                    'mention_count': 0,
                    'total_queries': 0
                },
                'all_brands_comparison': []
            }
        
        # 计算品类基准
        benchmark_data = self._calculate_benchmarks(all_brand_data)
        
        # 计算我方品牌数据
        my_brand_data = self._calculate_my_brand_metrics(brand_name, all_brand_data)
        
        # 生成所有品牌的对比数据
        all_brands_comparison = self._generate_all_brands_comparison(all_brand_data)
        
        result = {
            'category': category,
            'benchmark_data': benchmark_data,
            'my_brand_data': my_brand_data,
            'all_brands_comparison': all_brands_comparison
        }
        
        self.logger.info(f"Calculated market intelligence for brand: {brand_name}, category: {category}")
        return result
    
    def _get_all_brand_data_in_category(self, category: str = None, days: int = 30) -> Dict[str, List[Dict]]:
        """
        获取品类内所有品牌的数据
        
        Args:
            category: 品类名称
            days: 查询天数
            
        Returns:
            Dict: 品牌名称到其数据列表的映射
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建查询语句
        if category:
            # 如果有品类，我们需要从品牌或其他地方获取品类信息
            # 这里假设品牌名称本身就代表品类，或者我们可以通过其他方式确定品类
            # 为了简单起见，我们暂时按品牌名称匹配
            query = '''
                SELECT brand_name, test_date, overall_score, detailed_results, results_summary
                FROM test_records
                WHERE test_date >= ?
                ORDER BY test_date DESC
            '''
            params = (start_date,)
        else:
            query = '''
                SELECT brand_name, test_date, overall_score, detailed_results, results_summary
                FROM test_records
                WHERE test_date >= ?
                ORDER BY test_date DESC
            '''
            params = (start_date,)
        
        rows = self.safe_query.execute_query(query, params)
        
        brand_data = defaultdict(list)
        
        for row in rows:
            brand_name = row[0]
            test_date = row[1]
            overall_score = row[2]
            detailed_results_str = row[3]
            results_summary_str = row[4]
            
            # 解析JSON数据
            detailed_results = json.loads(detailed_results_str) if detailed_results_str else []
            results_summary = json.loads(results_summary_str) if results_summary_str else {}
            
            # 提取品牌相关数据
            brand_info = {
                'test_date': test_date,
                'overall_score': overall_score,
                'detailed_results': detailed_results,
                'results_summary': results_summary,
                'rank': self._extract_rank_from_results(results_summary),
                'sentiment_score': self._calculate_average_sentiment(detailed_results)
            }
            
            brand_data[brand_name].append(brand_info)
        
        return dict(brand_data)
    
    def _extract_rank_from_results(self, results_summary: Dict) -> Optional[int]:
        """从结果摘要中提取排名"""
        try:
            if not results_summary:
                return None

            # 尝試從brand_details中獲取排名
            brand_details = results_summary.get('brand_details', {})
            for brand_name, details in brand_details.items():
                if isinstance(details, dict) and 'rank' in details:
                    return details['rank']

            # 如果沒有明確的排名，嘗試從ranking_list獲取
            ranking_list = results_summary.get('ranking_list', [])
            if ranking_list and isinstance(ranking_list, list):
                # 假設第一個是主品牌排名
                return 1

            return None
        except Exception as e:
            self.logger.error(f"Error extracting rank from results: {e}")
            return None
    
    def _calculate_average_sentiment(self, detailed_results: List[Dict]) -> Optional[float]:
        """計算平均情感分數"""
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
    
    def _calculate_benchmarks(self, all_brand_data: Dict[str, List[Dict]]) -> Dict[str, any]:
        """計算品类基准数据"""
        all_ranks = []
        all_sentiments = []
        all_mention_frequencies = []
        
        for brand_name, brand_records in all_brand_data.items():
            if not brand_records:
                continue
            
            # 收集该品牌的排名数据
            ranks = [record['rank'] for record in brand_records if record['rank'] is not None]
            if ranks:
                avg_rank = statistics.mean(ranks)
                all_ranks.append(avg_rank)
            
            # 收集该品牌的情感分数数据
            sentiments = [record['sentiment_score'] for record in brand_records if record['sentiment_score'] is not None]
            if sentiments:
                avg_sentiment = statistics.mean(sentiments)
                all_sentiments.append(avg_sentiment)
        
        # 计算品类基准
        benchmark_data = {
            'avg_rank_position': statistics.mean(all_ranks) if all_ranks else None,
            'avg_sentiment_score': statistics.mean(all_sentiments) if all_sentiments else None,
            'avg_mention_frequency': None  # 这個需要根據具體業務邏輯計算
        }
        
        return benchmark_data
    
    def _calculate_my_brand_metrics(self, my_brand_name: str, all_brand_data: Dict[str, List[Dict]]) -> Dict[str, any]:
        """计算我方品牌的指标"""
        my_brand_records = all_brand_data.get(my_brand_name, [])

        if not my_brand_records:
            return {
                'brand_name': my_brand_name,
                'rank_position': None,
                'sentiment_position': None,
                'mind_share': None,
                'mention_count': 0,
                'total_queries': 0
            }

        # 计算我方品牌的平均排名
        my_ranks = [record.get('rank') for record in my_brand_records if record.get('rank') is not None]
        my_avg_rank = statistics.mean(my_ranks) if my_ranks else None

        # 計算我方品牌的情感分數
        my_sentiments = [record.get('sentiment_score') for record in my_brand_records if record.get('sentiment_score') is not None]
        my_avg_sentiment = statistics.mean(my_sentiments) if my_sentiments else None

        # 計算心智佔有率（提及次數 / 總詢問次數）
        total_mentions = 0
        total_queries = 0
        for record in my_brand_records:
            detailed_results = record.get('detailed_results', [])
            if detailed_results and isinstance(detailed_results, list):
                total_mentions += len(detailed_results)

            results_summary = record.get('results_summary', {})
            if results_summary and isinstance(results_summary, dict):
                questions_used = results_summary.get('questions_used', [])
                if questions_used and isinstance(questions_used, list):
                    total_queries += len(questions_used)

        mind_share = (total_mentions / total_queries * 100) if total_queries > 0 else 0

        # 計算排名位置（相對於其他品牌）
        all_avg_ranks = {}
        for brand_name, records in all_brand_data.items():
            ranks = [r.get('rank') for r in records if r.get('rank') is not None]
            if ranks:
                all_avg_ranks[brand_name] = statistics.mean(ranks)

        # 排序以確定排名位置
        sorted_brands_by_rank = sorted(all_avg_ranks.items(), key=lambda x: x[1] if x[1] is not None else float('inf'))
        rank_position = next((i+1 for i, (name, _) in enumerate(sorted_brands_by_rank) if name == my_brand_name), None)

        # 計算情感分數位置
        all_avg_sentiments = {}
        for brand_name, records in all_brand_data.items():
            sentiments = [r.get('sentiment_score') for r in records if r.get('sentiment_score') is not None]
            if sentiments:
                all_avg_sentiments[brand_name] = statistics.mean(sentiments)

        sorted_brands_by_sentiment = sorted(all_avg_sentiments.items(), key=lambda x: x[1] if x[1] is not None else float('-inf'), reverse=True)
        sentiment_position = next((i+1 for i, (name, _) in enumerate(sorted_brands_by_sentiment) if name == my_brand_name), None)

        return {
            'brand_name': my_brand_name,
            'rank_position': rank_position,
            'sentiment_position': sentiment_position,
            'mind_share': mind_share,
            'mention_count': total_mentions,
            'total_queries': total_queries
        }
    
    def _generate_all_brands_comparison(self, all_brand_data: Dict[str, List[Dict]]) -> List[Dict]:
        """生成所有品牌的对比数据"""
        comparison_data = []

        for brand_name, records in all_brand_data.items():
            if not records:
                continue

            # 計算該品牌的平均排名
            ranks = [r.get('rank') for r in records if r.get('rank') is not None]
            avg_rank = statistics.mean(ranks) if ranks else None

            # 計算該品牌的情感分數
            sentiments = [r.get('sentiment_score') for r in records if r.get('sentiment_score') is not None]
            avg_sentiment = statistics.mean(sentiments) if sentiments else None

            # 計算提及次數，確保 detailed_results 是列表
            mention_count = 0
            for r in records:
                detailed_results = r.get('detailed_results', [])
                if detailed_results and isinstance(detailed_results, list):
                    mention_count += len(detailed_results)

            brand_comparison = {
                'brand_name': brand_name,
                'avg_rank': avg_rank,
                'avg_sentiment_score': avg_sentiment,
                'mention_count': mention_count,
                'record_count': len(records)
            }

            comparison_data.append(brand_comparison)

        # 按平均排名排序（數字越小排名越高）
        comparison_data.sort(key=lambda x: x['avg_rank'] if x['avg_rank'] is not None else float('inf'))

        return comparison_data
    
    def get_market_benchmark_data(self, brand_name: str, category: str = None, days: int = 30) -> Dict[str, any]:
        """
        获取市场基准数据 - 用于API端点
        
        Args:
            brand_name: 我方品牌名称
            category: 品类名称
            days: 查询天数
            
        Returns:
            Dict: 市場基準數據
        """
        return self.calculate_category_benchmarks(brand_name, category, days)