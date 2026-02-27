"""
诊断结果仓库

用于存储和查询诊断结果（每个问题×模型的响应）。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.v2.models.diagnosis_result import DiagnosisResult
from wechat_backend.v2.exceptions import RepositoryError

logger = logging.getLogger(__name__)


class DiagnosisResultRepository:
    """
    诊断结果仓库
    
    职责：
    1. 保存诊断结果（每个问题×模型的响应）
    2. 批量保存（一次诊断多个结果）
    3. 查询结果（按报告、按执行 ID）
    4. 更新分析数据（GEO、情感等）
    5. 统计结果数据
    
    使用示例:
        >>> repo = DiagnosisResultRepository()
        >>> result_id = repo.create(diagnosis_result)
        >>> results = repo.get_by_report_id(report_id)
    """
    
    # 默认数据库路径
    DEFAULT_DB_PATH = os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'data', 'diagnosis_results.db'
    )
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化仓库
        
        Args:
            db_path: 数据库路径，默认使用 DEFAULT_DB_PATH
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        # 初始化数据库表
        self._init_db()
        
        api_logger.info(
            "diagnosis_result_repository_initialized",
            extra={
                'event': 'diagnosis_result_repository_initialized',
                'db_path': self.db_path,
            }
        )
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            db_logger.error(
                "database_operation_failed",
                extra={
                    'event': 'database_operation_failed',
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建 diagnosis_results 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS diagnosis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- 关联信息
                    report_id INTEGER NOT NULL,
                    execution_id TEXT NOT NULL,
                    
                    -- 查询参数
                    brand TEXT NOT NULL,
                    question TEXT NOT NULL,
                    model TEXT NOT NULL,
                    
                    -- 原始响应数据
                    response TEXT NOT NULL,
                    response_text TEXT,
                    
                    -- GEO 分析数据
                    geo_data TEXT,
                    exposure BOOLEAN DEFAULT 0,
                    sentiment TEXT DEFAULT 'neutral',
                    keywords TEXT,
                    
                    -- 质量评分
                    quality_score REAL,
                    quality_level TEXT,
                    
                    -- 性能指标
                    latency_ms INTEGER,
                    
                    -- 错误信息
                    error_message TEXT,
                    
                    -- 元数据
                    data_version TEXT DEFAULT '1.0',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- 外键约束
                    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id) ON DELETE CASCADE
                )
            ''')
            
            # 创建索引
            self._create_index_if_not_exists(
                cursor, 'idx_results_execution',
                'diagnosis_results(execution_id)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_results_report',
                'diagnosis_results(report_id)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_results_brand',
                'diagnosis_results(brand)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_results_model',
                'diagnosis_results(model)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_results_sentiment',
                'diagnosis_results(sentiment)'
            )
            
            self._create_index_if_not_exists(
                cursor, 'idx_results_brand_model',
                'diagnosis_results(brand, model)'
            )
            
            db_logger.info("diagnosis_results_table_initialized")
    
    def _create_index_if_not_exists(
        self,
        cursor: sqlite3.Cursor,
        index_name: str,
        index_def: str,
    ) -> None:
        """创建索引（如果不存在）"""
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}')
        except sqlite3.OperationalError:
            pass
    
    def create(self, result: DiagnosisResult) -> int:
        """
        创建单个诊断结果
        
        Args:
            result: DiagnosisResult 对象
        
        Returns:
            int: 新记录的 ID
        
        Raises:
            RepositoryError: 创建失败
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO diagnosis_results (
                        report_id, execution_id, brand, question, model,
                        response, response_text, geo_data, exposure,
                        sentiment, keywords, quality_score, quality_level,
                        latency_ms, error_message, data_version,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.report_id,
                    result.execution_id,
                    result.brand,
                    result.question,
                    result.model,
                    json.dumps(result.response, ensure_ascii=False),
                    result.response_text,
                    json.dumps(result.geo_data, ensure_ascii=False) if result.geo_data else None,
                    1 if result.exposure else 0,
                    result.sentiment,
                    json.dumps(result.keywords, ensure_ascii=False),
                    result.quality_score,
                    result.quality_level,
                    result.latency_ms,
                    result.error_message,
                    result.data_version,
                    now,
                    now,
                ))
                
                result_id = cursor.lastrowid
                
                api_logger.info(
                    "diagnosis_result_created",
                    extra={
                        'event': 'diagnosis_result_created',
                        'result_id': result_id,
                        'execution_id': result.execution_id,
                        'brand': result.brand,
                        'model': result.model,
                        'exposure': result.exposure,
                        'sentiment': result.sentiment,
                    }
                )
                
                return result_id
                
        except Exception as e:
            db_logger.error(
                "diagnosis_result_create_failed",
                extra={
                    'event': 'diagnosis_result_create_failed',
                    'execution_id': result.execution_id if hasattr(result, 'execution_id') else 'unknown',
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise RepositoryError(f"创建诊断结果失败：{e}") from e
    
    def create_many(self, results: List[DiagnosisResult]) -> List[int]:
        """
        批量创建诊断结果
        
        Args:
            results: DiagnosisResult 对象列表
        
        Returns:
            List[int]: 新记录的 ID 列表
        
        Raises:
            RepositoryError: 批量创建失败
        """
        ids = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for result in results:
                    now = datetime.now().isoformat()
                    
                    cursor.execute('''
                        INSERT INTO diagnosis_results (
                            report_id, execution_id, brand, question, model,
                            response, response_text, geo_data, exposure,
                            sentiment, keywords, quality_score, quality_level,
                            latency_ms, error_message, data_version,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result.report_id,
                        result.execution_id,
                        result.brand,
                        result.question,
                        result.model,
                        json.dumps(result.response, ensure_ascii=False),
                        result.response_text,
                        json.dumps(result.geo_data, ensure_ascii=False) if result.geo_data else None,
                        1 if result.exposure else 0,
                        result.sentiment,
                        json.dumps(result.keywords, ensure_ascii=False),
                        result.quality_score,
                        result.quality_level,
                        result.latency_ms,
                        result.error_message,
                        result.data_version,
                        now,
                        now,
                    ))
                    
                    ids.append(cursor.lastrowid)
                
                api_logger.info(
                    "diagnosis_results_batch_created",
                    extra={
                        'event': 'diagnosis_results_batch_created',
                        'count': len(ids),
                        'execution_id': results[0].execution_id if results else 'unknown',
                    }
                )
                
                return ids
                
        except Exception as e:
            db_logger.error(
                "diagnosis_results_batch_create_failed",
                extra={
                    'event': 'diagnosis_results_batch_create_failed',
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise RepositoryError(f"批量创建诊断结果失败：{e}") from e
    
    def get_by_id(self, result_id: int) -> Optional[DiagnosisResult]:
        """
        根据 ID 获取结果
        
        Args:
            result_id: 结果 ID
        
        Returns:
            Optional[DiagnosisResult]: 结果对象，不存在返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM diagnosis_results WHERE id = ?', (result_id,))
                row = cursor.fetchone()
                
                if row:
                    return DiagnosisResult.from_db_row(dict(row))
                return None
        except Exception as e:
            return None
    
    def get_by_report_id(
        self,
        report_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[DiagnosisResult]:
        """
        获取某份报告的所有结果
        
        Args:
            report_id: 报告 ID
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[DiagnosisResult]: 结果列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM diagnosis_results
                    WHERE report_id = ?
                    ORDER BY brand, model, question
                    LIMIT ? OFFSET ?
                ''', (report_id, limit, offset))
                
                return [DiagnosisResult.from_db_row(dict(row)) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def get_by_execution_id(
        self,
        execution_id: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[DiagnosisResult]:
        """
        根据执行 ID 获取结果
        
        Args:
            execution_id: 执行 ID
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[DiagnosisResult]: 结果列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM diagnosis_results
                    WHERE execution_id = ?
                    ORDER BY created_at ASC
                    LIMIT ? OFFSET ?
                ''', (execution_id, limit, offset))
                
                return [DiagnosisResult.from_db_row(dict(row)) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def update_geo_data(
        self,
        result_id: int,
        geo_data: Dict[str, Any],
        exposure: bool,
        sentiment: str,
        keywords: List[str],
    ) -> bool:
        """
        更新 GEO 分析数据
        
        Args:
            result_id: 结果 ID
            geo_data: GEO 分析数据
            exposure: 是否露出
            sentiment: 情感倾向
            keywords: 关键词列表
        
        Returns:
            bool: 是否更新成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    UPDATE diagnosis_results
                    SET geo_data = ?,
                        exposure = ?,
                        sentiment = ?,
                        keywords = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (
                    json.dumps(geo_data, ensure_ascii=False),
                    1 if exposure else 0,
                    sentiment,
                    json.dumps(keywords, ensure_ascii=False),
                    now,
                    result_id,
                ))
                
                affected = cursor.rowcount > 0
                
                if affected:
                    api_logger.info(
                        "diagnosis_result_geo_updated",
                        extra={
                            'event': 'diagnosis_result_geo_updated',
                            'result_id': result_id,
                            'exposure': exposure,
                            'sentiment': sentiment,
                        }
                    )
                
                return affected
        except Exception as e:
            return False
    
    def update_quality_score(
        self,
        result_id: int,
        quality_score: float,
        quality_level: str,
    ) -> bool:
        """
        更新质量评分
        
        Args:
            result_id: 结果 ID
            quality_score: 质量评分
            quality_level: 质量等级
        
        Returns:
            bool: 是否更新成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    UPDATE diagnosis_results
                    SET quality_score = ?,
                        quality_level = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (
                    quality_score,
                    quality_level,
                    now,
                    result_id,
                ))
                
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def count_by_report_id(self, report_id: int) -> int:
        """
        统计某份报告的结果数量
        
        Args:
            report_id: 报告 ID
        
        Returns:
            int: 结果数量
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT COUNT(*) FROM diagnosis_results WHERE report_id = ?',
                    (report_id,),
                )
                return cursor.fetchone()[0]
        except Exception:
            return 0
    
    def get_statistics(self, report_id: int) -> Dict[str, Any]:
        """
        获取报告的结果统计
        
        Args:
            report_id: 报告 ID
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 总数
                cursor.execute(
                    'SELECT COUNT(*) FROM diagnosis_results WHERE report_id = ?',
                    (report_id,),
                )
                total = cursor.fetchone()[0]
                
                # 成功/失败统计
                cursor.execute('''
                    SELECT 
                        COUNT(CASE WHEN error_message IS NULL THEN 1 END) as success_count,
                        COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as error_count
                    FROM diagnosis_results
                    WHERE report_id = ?
                ''', (report_id,))
                row = cursor.fetchone()
                success_count = row['success_count'] or 0
                error_count = row['error_count'] or 0
                
                # 情感分布
                cursor.execute('''
                    SELECT sentiment, COUNT(*) as count
                    FROM diagnosis_results
                    WHERE report_id = ? AND error_message IS NULL
                    GROUP BY sentiment
                ''', (report_id,))
                sentiment_stats = {
                    row['sentiment']: row['count']
                    for row in cursor.fetchall()
                }
                
                # 品牌露出统计
                cursor.execute('''
                    SELECT 
                        brand,
                        COUNT(CASE WHEN exposure = 1 THEN 1 END) as exposure_count,
                        COUNT(*) as total_count
                    FROM diagnosis_results
                    WHERE report_id = ?
                    GROUP BY brand
                ''', (report_id,))
                brand_stats = [
                    {
                        'brand': row['brand'],
                        'exposure_count': row['exposure_count'],
                        'total_count': row['total_count'],
                        'exposure_rate': (
                            row['exposure_count'] / row['total_count']
                            if row['total_count'] > 0 else 0
                        ),
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total': total,
                    'success_count': success_count,
                    'error_count': error_count,
                    'sentiment_distribution': sentiment_stats,
                    'brand_exposure': brand_stats,
                }
                
        except Exception as e:
            return {
                'total': 0,
                'success_count': 0,
                'error_count': 0,
                'sentiment_distribution': {},
                'brand_exposure': [],
            }
