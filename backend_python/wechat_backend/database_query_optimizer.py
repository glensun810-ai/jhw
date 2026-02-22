"""
数据库查询优化器

功能：
- 优化常用查询
- 添加查询缓存
- 分页查询优化
"""

import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from wechat_backend.logging_config import db_logger
except ImportError:
    import logging
    db_logger = logging.getLogger('db_logger')
    db_logger.setLevel(logging.INFO)


class QueryOptimizer:
    """
    查询优化器类
    
    功能：
    - 优化常用查询
    - 添加查询缓存
    - 分页查询优化
    """
    
    @staticmethod
    def get_test_records_with_pagination(
        conn: sqlite3.Connection,
        user_id: Optional[str] = None,
        brand_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        分页获取测试记录（优化版）
        
        参数：
        - conn: 数据库连接
        - user_id: 用户 ID
        - brand_name: 品牌名称
        - page: 页码
        - page_size: 每页数量
        
        返回：
        - records: 记录列表
        - total: 总数
        """
        cursor = conn.cursor()
        
        # 构建 WHERE 子句
        conditions = []
        params = []
        
        if user_id:
            conditions.append('user_id = ?')
            params.append(user_id)
        
        if brand_name:
            conditions.append('brand_name = ?')
            params.append(brand_name)
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        # 获取总数
        count_sql = f'SELECT COUNT(*) FROM test_records WHERE {where_clause}'
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # 分页查询（使用索引优化）
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT * FROM test_records
            WHERE {where_clause}
            ORDER BY test_date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor.execute(query_sql, params)
        
        columns = [description[0] for description in cursor.description]
        records = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return records, total
    
    @staticmethod
    def get_task_status_for_polling(
        conn: sqlite3.Connection,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取任务状态（用于轮询，优化版）
        
        参数：
        - conn: 数据库连接
        - task_id: 任务 ID
        
        返回：
        - status: 任务状态
        """
        cursor = conn.cursor()
        
        # 使用索引优化的查询
        query = """
            SELECT * FROM task_statuses
            WHERE task_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
        """
        cursor.execute(query, (task_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))
    
    @staticmethod
    def get_incomplete_tasks(conn: sqlite3.Connection, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取未完成的任务（用于后台处理）
        
        参数：
        - conn: 数据库连接
        - limit: 限制数量
        
        返回：
        - tasks: 任务列表
        """
        cursor = conn.cursor()
        
        # 使用组合索引 (is_completed, updated_at)
        query = """
            SELECT * FROM task_statuses
            WHERE is_completed = 0
            ORDER BY updated_at ASC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    @staticmethod
    def get_brand_analysis(
        conn: sqlite3.Connection,
        brand_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取品牌分析数据（使用索引优化）
        
        参数：
        - conn: 数据库连接
        - brand_name: 品牌名称
        - days: 天数
        
        返回：
        - analysis: 分析数据
        """
        cursor = conn.cursor()
        
        # 计算日期范围
        cutoff_date = datetime.now()
        
        # 获取品牌统计数据
        query = """
            SELECT 
                COUNT(*) as total_tests,
                AVG(overall_score) as avg_score,
                MAX(overall_score) as max_score,
                MIN(overall_score) as min_score
            FROM test_records
            WHERE brand_name = ?
            AND test_date >= ?
        """
        cursor.execute(query, (brand_name, cutoff_date.isoformat()))
        
        row = cursor.fetchone()
        if not row:
            return {'error': 'No data found'}
        
        columns = [description[0] for description in cursor.description]
        stats = dict(zip(columns, row))
        
        return {
            'brand_name': brand_name,
            'days': days,
            'statistics': stats
        }
    
    @staticmethod
    def get_user_activity_summary(
        conn: sqlite3.Connection,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取用户活动摘要（使用索引优化）
        
        参数：
        - conn: 数据库连接
        - user_id: 用户 ID
        - days: 天数
        
        返回：
        - summary: 活动摘要
        """
        cursor = conn.cursor()
        
        cutoff_date = datetime.now()
        
        # 获取用户测试记录统计
        query = """
            SELECT 
                COUNT(*) as total_tests,
                COUNT(DISTINCT brand_name) as unique_brands,
                AVG(overall_score) as avg_score
            FROM test_records
            WHERE user_id = ?
            AND test_date >= ?
        """
        cursor.execute(query, (user_id, cutoff_date.isoformat()))
        
        row = cursor.fetchone()
        if not row:
            return {'error': 'No data found'}
        
        columns = [description[0] for description in cursor.description]
        stats = dict(zip(columns, row))
        
        return {
            'user_id': user_id,
            'days': days,
            'statistics': stats
        }
    
    @staticmethod
    def optimize_database(conn: sqlite3.Connection):
        """
        优化数据库性能
        
        参数：
        - conn: 数据库连接
        """
        cursor = conn.cursor()
        
        # 运行 ANALYZE 更新统计信息
        cursor.execute('ANALYZE')
        conn.commit()
        
        db_logger.info('[QueryOptimizer] 数据库优化完成')


# 导出优化器实例
query_optimizer = QueryOptimizer()
