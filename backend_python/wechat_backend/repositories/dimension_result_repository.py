"""
维度结果存储仓库

功能：
- 保存每个诊断维度的详细结果
- 支持按执行 ID 查询所有维度
- 支持按维度类型筛选
- 实时更新维度状态

核心原则：
1. 每个维度独立存储
2. 支持部分失败（某些维度成功，某些失败）
3. 实时持久化，防止数据丢失
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.database_connection_pool import get_db_pool


@contextmanager
def get_db_connection():
    """获取数据库连接上下文管理器"""
    conn = get_db_pool().get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        db_logger.error(f"数据库操作失败：{e}")
        raise
    finally:
        get_db_pool().return_connection(conn)


class DimensionResultRepository:
    """
    维度结果存储仓库
    
    用法：
        repo = DimensionResultRepository()
        
        # 保存维度结果
        repo.save_dimension(
            execution_id="exec_123",
            dimension_name="社交媒体影响力",
            dimension_type="social_media",
            source="weibo",
            status="success",
            score=90.0,
            data={...},
            error_message=None
        )
        
        # 获取执行 ID 的所有维度
        dimensions = repo.get_dimensions_by_execution("exec_123")
    """
    
    def __init__(self):
        self.table_name = "dimension_results"
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """确保表存在（如果不存在则创建）"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS dimension_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT NOT NULL,
            dimension_name TEXT NOT NULL,
            dimension_type TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            score REAL,
            data TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_index_sqls = [
            "CREATE INDEX IF NOT EXISTS idx_dimension_execution_id ON dimension_results(execution_id)",
            "CREATE INDEX IF NOT EXISTS idx_dimension_type ON dimension_results(dimension_type)",
            "CREATE INDEX IF NOT EXISTS idx_dimension_status ON dimension_results(status)"
        ]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            for index_sql in create_index_sqls:
                cursor.execute(index_sql)
        
        db_logger.info("[DimensionResultRepository] 表初始化完成")
    
    def save_dimension(
        self,
        execution_id: str,
        dimension_name: str,
        dimension_type: str,
        source: str,
        status: str,
        score: Optional[float] = None,
        data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> int:
        """
        保存维度结果
        
        参数：
            execution_id: 执行 ID
            dimension_name: 维度名称
            dimension_type: 维度类型（social_media, news, ai_summary 等）
            source: 数据源
            status: 状态（success, failed）
            score: 评分（可选）
            data: 详细数据（JSON 对象）
            error_message: 错误信息（失败时填写）
        
        返回：
            插入的记录 ID
        """
        try:
            # 序列化数据
            data_json = json.dumps(data, ensure_ascii=False, default=str) if data else None
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dimension_results
                    (execution_id, dimension_name, dimension_type, source, status, score, data, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    execution_id,
                    dimension_name,
                    dimension_type,
                    source,
                    status,
                    score,
                    data_json,
                    error_message
                ))
                
                record_id = cursor.lastrowid
                
                api_logger.info(
                    f"[DimensionResult] ✅ 维度保存成功：{execution_id}, "
                    f"{dimension_name}, 状态：{status}"
                )
                
                return record_id
                
        except Exception as e:
            db_logger.error(
                f"[DimensionResult] ❌ 维度保存失败：{execution_id}, "
                f"{dimension_name}, 错误：{e}"
            )
            raise
    
    def get_dimensions_by_execution(
        self,
        execution_id: str,
        dimension_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        根据执行 ID 获取所有维度结果
        
        参数：
            execution_id: 执行 ID
            dimension_type: 维度类型过滤（可选）
        
        返回：
            维度结果列表
        """
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if dimension_type:
                    cursor.execute('''
                        SELECT * FROM dimension_results
                        WHERE execution_id = ? AND dimension_type = ?
                        ORDER BY id
                    ''', (execution_id, dimension_type))
                else:
                    cursor.execute('''
                        SELECT * FROM dimension_results
                        WHERE execution_id = ?
                        ORDER BY id
                    ''', (execution_id,))
                
                results = []
                for row in cursor.fetchall():
                    dimension = {
                        'id': row['id'],
                        'execution_id': row['execution_id'],
                        'dimension_name': row['dimension_name'],
                        'dimension_type': row['dimension_type'],
                        'source': row['source'],
                        'status': row['status'],
                        'score': row['score'],
                        'error_message': row['error_message'],
                        'created_at': row['created_at']
                    }
                    
                    # 解析数据
                    if row['data']:
                        try:
                            dimension['data'] = json.loads(row['data'])
                        except Exception:
                            dimension['data'] = None
                    
                    results.append(dimension)
                
                api_logger.info(
                    f"[DimensionResult] ✅ 维度加载成功：{execution_id}, "
                    f"数量：{len(results)}"
                )
                
                return results
                
        except Exception as e:
            db_logger.error(f"[DimensionResult] ❌ 维度加载失败：{execution_id}, 错误：{e}")
            return []
    
    def get_dimension_statistics(self, execution_id: str) -> Dict[str, Any]:
        """
        获取执行 ID 的维度统计信息
        
        参数：
            execution_id: 执行 ID
        
        返回：
            统计信息字典
        """
        try:
            dimensions = self.get_dimensions_by_execution(execution_id)
            
            total = len(dimensions)
            success_count = sum(1 for d in dimensions if d['status'] == 'success')
            failed_count = total - success_count
            
            # 计算平均评分（仅成功的维度）
            successful_scores = [
                d['score'] for d in dimensions
                if d['status'] == 'success' and d['score'] is not None
            ]
            avg_score = sum(successful_scores) / len(successful_scores) if successful_scores else None
            
            # 按类型分组
            by_type = {}
            for dim in dimensions:
                dim_type = dim['dimension_type']
                if dim_type not in by_type:
                    by_type[dim_type] = {'total': 0, 'success': 0, 'failed': 0}
                by_type[dim_type]['total'] += 1
                if dim['status'] == 'success':
                    by_type[dim_type]['success'] += 1
                else:
                    by_type[dim_type]['failed'] += 1
            
            return {
                'total': total,
                'success_count': success_count,
                'failed_count': failed_count,
                'success_rate': success_count / total if total > 0 else 0,
                'average_score': avg_score,
                'by_type': by_type
            }
                
        except Exception as e:
            db_logger.error(f"[DimensionResult] ❌ 统计信息获取失败：{execution_id}, 错误：{e}")
            return {}
    
    def update_dimension_status(
        self,
        execution_id: str,
        dimension_name: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新维度状态（用于异步更新）
        
        参数：
            execution_id: 执行 ID
            dimension_name: 维度名称
            status: 新状态
            error_message: 错误信息（可选）
        
        返回：
            是否更新成功
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE dimension_results
                    SET status = ?, error_message = ?
                    WHERE execution_id = ? AND dimension_name = ?
                ''', (status, error_message, execution_id, dimension_name))
                
                updated_count = cursor.rowcount
                
                if updated_count > 0:
                    api_logger.info(
                        f"[DimensionResult] ✅ 维度状态更新成功：{execution_id}, "
                        f"{dimension_name}, 新状态：{status}"
                    )
                    return True
                else:
                    api_logger.warning(
                        f"[DimensionResult] ⚠️ 维度不存在，无法更新：{execution_id}, "
                        f"{dimension_name}"
                    )
                    return False
                
        except Exception as e:
            db_logger.error(
                f"[DimensionResult] ❌ 维度状态更新失败：{execution_id}, "
                f"{dimension_name}, 错误：{e}"
            )
            return False
    
    def delete_dimensions_by_execution(self, execution_id: str) -> int:
        """
        根据执行 ID 删除所有维度（谨慎使用）
        
        参数：
            execution_id: 执行 ID
        
        返回：
            删除的记录数
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM dimension_results
                    WHERE execution_id = ?
                ''', (execution_id,))
                
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    api_logger.info(
                        f"[DimensionResult] 🗑️ 维度删除成功：{execution_id}, "
                        f"数量：{deleted_count}"
                    )
                    return deleted_count
                else:
                    return 0
                
        except Exception as e:
            db_logger.error(f"[DimensionResult] ❌ 维度删除失败：{execution_id}, 错误：{e}")
            return 0


# 全局仓库实例
_dimension_repo: Optional[DimensionResultRepository] = None

def get_dimension_repository() -> DimensionResultRepository:
    """获取全局维度结果仓库实例"""
    global _dimension_repo
    if _dimension_repo is None:
        _dimension_repo = DimensionResultRepository()
    return _dimension_repo


# 便捷函数
def save_dimension_result(
    execution_id: str,
    dimension_name: str,
    dimension_type: str,
    source: str,
    status: str,
    score: Optional[float] = None,
    data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> int:
    """
    便捷函数：保存维度结果

    用法：
        record_id = save_dimension_result(
            execution_id="exec_123",
            dimension_name="社交媒体影响力",
            dimension_type="social_media",
            source="weibo",
            status="success",
            score=90.0,
            data={...}
        )
    """
    return get_dimension_repository().save_dimension(
        execution_id=execution_id,
        dimension_name=dimension_name,
        dimension_type=dimension_type,
        source=source,
        status=status,
        score=score,
        data=data,
        error_message=error_message
    )


def save_dimension_results_batch(
    results: List[Dict[str, Any]],
    execution_id: str
) -> int:
    """
    批量保存维度结果（使用事务）
    
    参数:
        results: 结果列表 [{brand, model, status, data, error, ...}]
        execution_id: 执行 ID
    
    返回:
        保存的记录数
    """
    saved_count = 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 开启事务
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            for result in results:
                if result.get('status') != 'success' or not result.get('data'):
                    continue
                
                geo_data = result['data']
                rank = geo_data.get('rank', -1)
                score = max(0, 100 - (rank - 1) * 10) if rank > 0 else None
                
                cursor.execute('''
                    INSERT INTO dimension_results
                    (execution_id, dimension_name, dimension_type, source, status, score, data, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    execution_id,
                    f"{result['brand']}-{result['model']}",
                    'ai_analysis',
                    result['model'],
                    'success',
                    score,
                    json.dumps(geo_data),
                    None
                ))
                saved_count += 1
            
            # 提交事务
            conn.commit()
            api_logger.info(f"[批量保存] ✅ 保存 {saved_count} 个维度结果")
            
        except Exception as e:
            conn.rollback()
            api_logger.error(f"[批量保存] ❌ 失败：{e}")
            raise
    
    return saved_count


def get_dimension_results(execution_id: str):
    """获取维度结果"""
    return get_dimension_repository().get_dimensions_by_execution(execution_id)


# 全局仓库实例
_dimension_repo = None

def get_dimension_repository():
    """获取全局维度结果仓库实例"""
    global _dimension_repo
    if _dimension_repo is None:
        _dimension_repo = DimensionResultRepository()
    return _dimension_repo
