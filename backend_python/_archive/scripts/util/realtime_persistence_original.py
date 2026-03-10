"""
实时结果持久化服务 (Realtime Persistence Service)

功能:
1. 实时保存每个任务结果
2. 增量更新聚合统计
3. 避免重复写入
4. 支持断点续传
5. 提供数据恢复

使用场景:
- TestExecutor 回调中调用
- 实时保存到数据库
- 支持任务中断后恢复
"""

from typing import Dict, Any, List
from datetime import datetime
import json
from wechat_backend.database import SafeDatabaseQuery, save_test_record
from wechat_backend.logging_config import api_logger


class RealtimePersistence:
    """实时结果持久化服务"""
    
    def __init__(self, execution_id: str, user_openid: str):
        """
        初始化持久化服务
        
        Args:
            execution_id: 执行 ID
            user_openid: 用户 OpenID
        """
        self.execution_id = execution_id
        self.user_openid = user_openid
        self.db_path = 'data/brand_test.db'
        self.saved_tasks: set = set()  # 已保存的任务集合
        self.start_time = datetime.now()
    
    def save_task_result(self, task_data: Dict[str, Any]) -> bool:
        """
        保存单个任务结果
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            是否保存成功
        """
        # 生成任务键 (避免重复保存)
        task_key = self._get_task_key(task_data)
        
        # 检查是否已保存
        if task_key in self.saved_tasks:
            api_logger.info(f"Task already saved: {task_key}")
            return False
        
        try:
            # 提取数据
            brand_name = task_data.get('brand', task_data.get('brand_name', ''))
            ai_model = task_data.get('aiModel', task_data.get('model', task_data.get('ai_model', '')))
            question = task_data.get('question', task_data.get('question_text', ''))
            response = task_data.get('response', task_data.get('content', ''))
            status = task_data.get('status', 'success')
            
            # 创建单个测试结果
            single_test_result = {
                'brand_name': brand_name,
                'question': question,
                'ai_model': ai_model,
                'response': response,
                'success': status == 'success',
                'error': task_data.get('error', '') if status != 'success' else '',
                'timestamp': datetime.now().isoformat(),
                'execution_id': self.execution_id
            }
            
            # 保存到数据库
            record_id = save_test_record(
                user_openid=self.user_openid,
                brand_name=brand_name,
                ai_models_used=[ai_model],
                questions_used=[question],
                overall_score=0,  # 单个测试不计算总分
                total_tests=1,
                results_summary={
                    'individual_test': True,
                    'execution_id': self.execution_id,
                    'success': status == 'success',
                    'task_key': task_key
                },
                detailed_results=[single_test_result]
            )
            
            # 标记为已保存
            self.saved_tasks.add(task_key)
            
            api_logger.info(f"Saved task result (ID: {record_id}): {brand_name}/{ai_model}/{question}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to save task result: {e}")
            return False
    
    def save_aggregated_results(self, aggregated_results: Dict[str, Any]) -> bool:
        """
        保存聚合结果
        
        Args:
            aggregated_results: 聚合结果字典
            
        Returns:
            是否保存成功
        """
        try:
            # 提取关键数据
            main_brand = aggregated_results.get('main_brand', '')
            summary = aggregated_results.get('summary', {})
            detailed_results = aggregated_results.get('detailed_results', [])
            
            # 计算总体评分
            health_score = summary.get('healthScore', 0)
            sov = summary.get('sov', 0)
            avg_sentiment = summary.get('avgSentiment', 0)
            success_rate = summary.get('successRate', 0)
            
            # 创建聚合记录
            aggregated_record = {
                'execution_id': self.execution_id,
                'main_brand': main_brand,
                'health_score': health_score,
                'sov': sov,
                'avg_sentiment': avg_sentiment,
                'success_rate': success_rate,
                'total_tests': summary.get('totalTests', len(detailed_results)),
                'total_mentions': summary.get('totalMentions', 0),
                'aggregated_at': datetime.now().isoformat()
            }
            
            # 保存到专门的聚合表
            safe_query = SafeDatabaseQuery(self.db_path)
            
            # 检查是否已存在
            existing = safe_query.execute_query(
                'SELECT id FROM aggregated_results WHERE execution_id = ?',
                (self.execution_id,)
            )
            
            if existing:
                # 更新现有记录
                safe_query.execute_query('''
                    UPDATE aggregated_results
                    SET health_score = ?, sov = ?, avg_sentiment = ?, 
                        success_rate = ?, total_tests = ?, total_mentions = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE execution_id = ?
                ''', (
                    health_score, sov, avg_sentiment, 
                    success_rate, summary.get('totalTests', 0), 
                    summary.get('totalMentions', 0),
                    self.execution_id
                ))
                api_logger.info(f"Updated aggregated results for execution: {self.execution_id}")
            else:
                # 插入新记录
                safe_query.execute_query('''
                    INSERT INTO aggregated_results
                    (execution_id, main_brand, health_score, sov, avg_sentiment, 
                     success_rate, total_tests, total_mentions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    self.execution_id, main_brand, health_score, sov, avg_sentiment,
                    success_rate, summary.get('totalTests', 0), summary.get('totalMentions', 0)
                ))
                api_logger.info(f"Inserted aggregated results for execution: {self.execution_id}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to save aggregated results: {e}")
            return False
    
    def save_brand_rankings(self, brand_rankings: List[Dict[str, Any]]) -> bool:
        """
        保存品牌排名
        
        Args:
            brand_rankings: 品牌排名列表
            
        Returns:
            是否保存成功
        """
        try:
            safe_query = SafeDatabaseQuery(self.db_path)
            
            for ranking in brand_rankings:
                brand = ranking.get('brand', '')
                rank = ranking.get('rank', 0)
                responses = ranking.get('responses', 0)
                sov_share = ranking.get('sov_share', 0)
                avg_sentiment = ranking.get('avg_sentiment', 0)
                avg_rank = ranking.get('avg_rank', -1)
                
                # 检查是否已存在
                existing = safe_query.execute_query(
                    'SELECT id FROM brand_rankings WHERE execution_id = ? AND brand = ?',
                    (self.execution_id, brand)
                )
                
                if existing:
                    # 更新
                    safe_query.execute_query('''
                        UPDATE brand_rankings
                        SET rank = ?, responses = ?, sov_share = ?, 
                            avg_sentiment = ?, avg_rank = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE execution_id = ? AND brand = ?
                    ''', (
                        rank, responses, sov_share, avg_sentiment, avg_rank,
                        self.execution_id, brand
                    ))
                else:
                    # 插入
                    safe_query.execute_query('''
                        INSERT INTO brand_rankings
                        (execution_id, brand, rank, responses, sov_share, 
                         avg_sentiment, avg_rank, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        self.execution_id, brand, rank, responses, 
                        sov_share, avg_sentiment, avg_rank
                    ))
            
            api_logger.info(f"Saved {len(brand_rankings)} brand rankings")
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to save brand rankings: {e}")
            return False
    
    def get_saved_tasks_count(self) -> int:
        """获取已保存的任务数量"""
        return len(self.saved_tasks)
    
    def _get_task_key(self, task_data: Dict[str, Any]) -> str:
        """生成任务键"""
        brand = task_data.get('brand', task_data.get('brand_name', ''))
        model = task_data.get('aiModel', task_data.get('model', task_data.get('ai_model', '')))
        question = task_data.get('question', task_data.get('question_text', ''))
        
        return f"{brand}_{model}_{question}"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取持久化统计"""
        return {
            'execution_id': self.execution_id,
            'saved_tasks': len(self.saved_tasks),
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds()
        }


# 全局持久化服务存储
_persistence_services: Dict[str, RealtimePersistence] = {}


def get_persistence_service(execution_id: str) -> RealtimePersistence:
    """获取指定执行 ID 的持久化服务"""
    return _persistence_services.get(execution_id)


def create_persistence_service(
    execution_id: str, 
    user_openid: str = 'anonymous'
) -> RealtimePersistence:
    """创建并注册持久化服务"""
    service = RealtimePersistence(execution_id, user_openid)
    _persistence_services[execution_id] = service
    api_logger.info(f"Created RealtimePersistence for execution: {execution_id}")
    return service


def remove_persistence_service(execution_id: str):
    """移除持久化服务"""
    if execution_id in _persistence_services:
        stats = _persistence_services[execution_id].get_stats()
        api_logger.info(f"Removed RealtimePersistence for execution: {execution_id}, saved {stats['saved_tasks']} tasks")
        del _persistence_services[execution_id]
