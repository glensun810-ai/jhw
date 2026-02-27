"""
诊断数据仓库层

职责:
1. 诊断报告数据库 CRUD 操作
2. 状态更新持久化
3. 事务管理
4. 数据验证

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import sqlite3

from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.database_connection_pool import get_db_pool
from wechat_backend.v2.exceptions import DatabaseError, DiagnosisValidationError


class DiagnosisRepository:
    """
    诊断数据仓库 - 数据访问层
    
    职责:
    1. 诊断报告数据库 CRUD 操作
    2. 状态更新持久化
    3. 事务管理
    
    使用示例:
        >>> repo = DiagnosisRepository()
        >>> repo.update_state(
        ...     execution_id='exec-123',
        ...     status='ai_fetching',
        ...     progress=50,
        ...     is_completed=False,
        ...     should_stop_polling=False,
        ... )
    """
    
    def __init__(self):
        """初始化数据仓库"""
        self._db_pool = get_db_pool()
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接上下文管理器
        
        Yields:
            sqlite3.Connection: 数据库连接
        
        Raises:
            DatabaseError: 获取连接失败
        """
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = self._db_pool.get_connection()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            db_logger.error(
                "database_operation_failed",
                extra={
                    'event': 'database_operation_failed',
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DatabaseError(
                f"数据库操作失败：{e}",
                operation='get_connection',
                original_error=str(e),
            ) from e
        finally:
            if conn:
                self._db_pool.return_connection(conn)
    
    def update_state(
        self,
        execution_id: str,
        status: str,
        stage: str,
        progress: int,
        is_completed: bool,
        should_stop_polling: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新诊断任务状态
        
        更新 diagnosis_reports 表的以下字段:
        - status: 状态值
        - stage: 阶段（与 status 保持一致）
        - progress: 进度 (0-100)
        - is_completed: 是否完成
        - should_stop_polling: 是否停止轮询
        - updated_at: 更新时间
        
        Args:
            execution_id: 执行 ID
            status: 状态值（initializing/ai_fetching/analyzing/completed/failed/timeout）
            stage: 阶段（与 status 保持一致）
            progress: 进度 (0-100)
            is_completed: 是否完成
            should_stop_polling: 是否停止轮询
            metadata: 元数据（可选，包含 error_message 等）
        
        Returns:
            bool: 更新是否成功
        
        Raises:
            DatabaseError: 数据库操作失败
            DiagnosisValidationError: 参数验证失败
        """
        # 1. 参数验证
        self._validate_update_params(
            execution_id=execution_id,
            status=status,
            stage=stage,
            progress=progress,
        )
        
        # 2. 准备更新数据
        now: str = datetime.now().isoformat()
        updated_at: str = now
        
        # 如果是终态，设置 completed_at
        completed_at: Optional[str] = None
        if is_completed:
            completed_at = now
        
        # 3. 执行更新
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()
                
                # 构建 UPDATE 语句
                update_sql = """
                    UPDATE diagnosis_reports
                    SET 
                        status = ?,
                        stage = ?,
                        progress = ?,
                        is_completed = ?,
                        should_stop_polling = ?,
                        updated_at = ?,
                        completed_at = COALESCE(?, completed_at)
                    WHERE execution_id = ?
                """
                
                cursor.execute(
                    update_sql,
                    (
                        status,
                        stage,
                        progress,
                        1 if is_completed else 0,
                        1 if should_stop_polling else 0,
                        updated_at,
                        completed_at,
                        execution_id,
                    )
                )
                
                # 检查是否更新成功
                if cursor.rowcount == 0:
                    db_logger.warning(
                        "state_update_no_rows",
                        extra={
                            'event': 'state_update_no_rows',
                            'execution_id': execution_id,
                            'status': status,
                            'progress': progress,
                        }
                    )
                    # 记录不存在时，尝试创建
                    return self._try_create_and_update(
                        execution_id=execution_id,
                        status=status,
                        stage=stage,
                        progress=progress,
                        is_completed=is_completed,
                        should_stop_polling=should_stop_polling,
                        updated_at=updated_at,
                        completed_at=completed_at,
                        metadata=metadata,
                    )
                
                db_logger.info(
                    "state_updated",
                    extra={
                        'event': 'state_updated',
                        'execution_id': execution_id,
                        'status': status,
                        'stage': stage,
                        'progress': progress,
                        'is_completed': is_completed,
                        'should_stop_polling': should_stop_polling,
                        'rows_affected': cursor.rowcount,
                    }
                )
                
                return True
                
        except sqlite3.Error as e:
            db_logger.error(
                "state_update_sql_error",
                extra={
                    'event': 'state_update_sql_error',
                    'execution_id': execution_id,
                    'error': str(e),
                }
            )
            raise DatabaseError(
                f"更新状态时发生 SQL 错误：{e}",
                operation='update_state',
                original_error=str(e),
            ) from e
        except Exception as e:
            db_logger.error(
                "state_update_error",
                extra={
                    'event': 'state_update_error',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DatabaseError(
                f"更新状态失败：{e}",
                operation='update_state',
                original_error=str(e),
            ) from e
    
    def _validate_update_params(
        self,
        execution_id: str,
        status: str,
        stage: str,
        progress: int,
    ) -> None:
        """
        验证更新参数
        
        Args:
            execution_id: 执行 ID
            status: 状态值
            stage: 阶段
            progress: 进度
        
        Raises:
            DiagnosisValidationError: 参数验证失败
        """
        if not execution_id:
            raise DiagnosisValidationError(
                "execution_id 不能为空",
                field='execution_id',
            )
        
        if not status:
            raise DiagnosisValidationError(
                "status 不能为空",
                field='status',
            )
        
        # 验证状态值
        valid_statuses = [
            'initializing', 'ai_fetching', 'analyzing',
            'completed', 'partial_success', 'failed', 'timeout',
        ]
        if status not in valid_statuses:
            raise DiagnosisValidationError(
                f"无效的状态值：{status}",
                field='status',
                value=status,
            )
        
        if not stage:
            raise DiagnosisValidationError(
                "stage 不能为空",
                field='stage',
            )
        
        if not isinstance(progress, int) or progress < 0 or progress > 100:
            raise DiagnosisValidationError(
                f"进度必须是 0-100 的整数，得到：{progress}",
                field='progress',
                value=progress,
            )
    
    def _try_create_and_update(
        self,
        execution_id: str,
        status: str,
        stage: str,
        progress: int,
        is_completed: bool,
        should_stop_polling: bool,
        updated_at: str,
        completed_at: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        尝试创建记录并更新（当记录不存在时）
        
        Args:
            execution_id: 执行 ID
            status: 状态值
            stage: 阶段
            progress: 进度
            is_completed: 是否完成
            should_stop_polling: 是否停止轮询
            updated_at: 更新时间
            completed_at: 完成时间
            metadata: 元数据
        
        Returns:
            bool: 创建是否成功
        """
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()
                
                # 尝试插入新记录
                insert_sql = """
                    INSERT INTO diagnosis_reports (
                        execution_id, status, stage, progress,
                        is_completed, should_stop_polling,
                        created_at, updated_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(
                    insert_sql,
                    (
                        execution_id,
                        status,
                        stage,
                        progress,
                        1 if is_completed else 0,
                        1 if should_stop_polling else 0,
                        updated_at,  # created_at 使用 updated_at
                        updated_at,
                        completed_at,
                    )
                )
                
                db_logger.info(
                    "state_record_created",
                    extra={
                        'event': 'state_record_created',
                        'execution_id': execution_id,
                        'status': status,
                        'progress': progress,
                    }
                )
                
                return True
                
        except sqlite3.IntegrityError as e:
            # 记录已存在（并发创建）
            db_logger.warning(
                "state_record_already_exists",
                extra={
                    'event': 'state_record_already_exists',
                    'execution_id': execution_id,
                    'error': str(e),
                }
            )
            return False
        except Exception as e:
            db_logger.error(
                "state_record_create_failed",
                extra={
                    'event': 'state_record_create_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            return False
    
    def get_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            execution_id: 执行 ID
        
        Returns:
            Optional[Dict[str, Any]]: 状态字典，不存在则返回 None
        
        Raises:
            DatabaseError: 数据库操作失败
        """
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()
                
                select_sql = """
                    SELECT 
                        id, execution_id, status, stage, progress,
                        is_completed, should_stop_polling,
                        created_at, updated_at, completed_at
                    FROM diagnosis_reports
                    WHERE execution_id = ?
                """
                
                cursor.execute(select_sql, (execution_id,))
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                return {
                    'id': row[0],
                    'execution_id': row[1],
                    'status': row[2],
                    'stage': row[3],
                    'progress': row[4],
                    'is_completed': bool(row[5]),
                    'should_stop_polling': bool(row[6]),
                    'created_at': row[7],
                    'updated_at': row[8],
                    'completed_at': row[9],
                }
                
        except Exception as e:
            db_logger.error(
                "state_query_failed",
                extra={
                    'event': 'state_query_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DatabaseError(
                f"查询状态失败：{e}",
                operation='get_state',
                original_error=str(e),
            ) from e
    
    def create_report(
        self,
        execution_id: str,
        user_id: str,
        brand_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        创建诊断报告记录
        
        Args:
            execution_id: 执行 ID
            user_id: 用户 ID
            brand_name: 品牌名称
            config: 诊断配置（可选）
        
        Returns:
            int: 创建的报告 ID
        
        Raises:
            DatabaseError: 数据库操作失败
            DiagnosisValidationError: 参数验证失败
        """
        # 参数验证
        if not execution_id:
            raise DiagnosisValidationError(
                "execution_id 不能为空",
                field='execution_id',
            )
        if not user_id:
            raise DiagnosisValidationError(
                "user_id 不能为空",
                field='user_id',
            )
        if not brand_name:
            raise DiagnosisValidationError(
                "brand_name 不能为空",
                field='brand_name',
            )
        
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()
                
                now: str = datetime.now().isoformat()
                
                # 从 config 中提取数据
                config = config or {}
                competitor_brands: str = json.dumps(config.get('competitor_brands', []))
                selected_models: str = json.dumps(config.get('selected_models', []))
                custom_questions: str = json.dumps(config.get('custom_questions', []))
                
                insert_sql = """
                    INSERT INTO diagnosis_reports (
                        execution_id, user_id, brand_name,
                        competitor_brands, selected_models, custom_questions,
                        status, stage, progress, is_completed, should_stop_polling,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(
                    insert_sql,
                    (
                        execution_id,
                        user_id,
                        brand_name,
                        competitor_brands,
                        selected_models,
                        custom_questions,
                        'initializing',
                        'initializing',
                        0,
                        0,
                        0,
                        now,
                        now,
                    )
                )
                
                report_id: int = cursor.lastrowid
                
                db_logger.info(
                    "report_created",
                    extra={
                        'event': 'report_created',
                        'execution_id': execution_id,
                        'user_id': user_id,
                        'brand_name': brand_name,
                        'report_id': report_id,
                    }
                )
                
                return report_id
                
        except sqlite3.IntegrityError as e:
            db_logger.error(
                "report_create_integrity_error",
                extra={
                    'event': 'report_create_integrity_error',
                    'execution_id': execution_id,
                    'error': str(e),
                }
            )
            raise DatabaseError(
                f"创建报告时发生完整性错误：{e}",
                operation='create_report',
                original_error=str(e),
            ) from e
        except Exception as e:
            db_logger.error(
                "report_create_failed",
                extra={
                    'event': 'report_create_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DatabaseError(
                f"创建报告失败：{e}",
                operation='create_report',
                original_error=str(e),
            ) from e

    def get_by_execution_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        根据执行 ID 获取诊断记录

        Args:
            execution_id: 执行 ID

        Returns:
            Optional[Dict[str, Any]]: 诊断记录字典，不存在返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()

                select_sql = """
                    SELECT * FROM diagnosis_reports
                    WHERE execution_id = ?
                """

                cursor.execute(select_sql, (execution_id,))
                row = cursor.fetchone()

                if row is None:
                    return None

                result: Dict[str, Any] = dict(row)

                # 解析 JSON 字段
                for field in ['competitor_brands', 'selected_models', 'custom_questions']:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            result[field] = []

                return result

        except Exception as e:
            db_logger.error(
                "diagnosis_record_query_failed",
                extra={
                    'event': 'diagnosis_record_query_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            return None

    def get_expected_results_count(self, execution_id: str) -> int:
        """
        获取预期的结果总数（品牌数 × 模型数）

        Args:
            execution_id: 执行 ID

        Returns:
            int: 预期结果数量
        """
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()

                cursor.execute('''
                    SELECT 
                        json_array_length(competitor_brands) + 1 as brand_count,
                        json_array_length(selected_models) as model_count
                    FROM diagnosis_reports
                    WHERE execution_id = ?
                ''', (execution_id,))

                row = cursor.fetchone()
                if row:
                    brand_count = row['brand_count'] or 1  # 至少有一个主品牌
                    model_count = row['model_count'] or 0
                    return brand_count * model_count
                return 0

        except Exception:
            return 0

    def get_status_summary(self, execution_id: str) -> Dict[str, Any]:
        """
        获取状态摘要（用于存根）

        Args:
            execution_id: 执行 ID

        Returns:
            Dict[str, Any]: 状态摘要字典
        """
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()

                # 获取基本信息
                cursor.execute('''
                    SELECT 
                        status,
                        progress,
                        stage,
                        is_completed,
                        should_stop_polling,
                        error_message,
                        created_at,
                        completed_at,
                        brand_name
                    FROM diagnosis_reports
                    WHERE execution_id = ?
                ''', (execution_id,))

                basic_row = cursor.fetchone()
                basic: Dict[str, Any] = dict(basic_row) if basic_row else {}

                # 获取结果统计
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN error_message IS NULL THEN 1 ELSE 0 END) as success_count
                    FROM diagnosis_results
                    WHERE execution_id = ?
                ''', (execution_id,))

                stats_row = cursor.fetchone()
                stats: Dict[str, Any] = dict(stats_row) if stats_row else {'total': 0, 'success_count': 0}

                return {
                    **basic,
                    'total_results': stats.get('total', 0),
                    'successful_results': stats.get('success_count', 0),
                    'expected_results': self.get_expected_results_count(execution_id),
                }

        except Exception as e:
            db_logger.error(
                "status_summary_query_failed",
                extra={
                    'event': 'status_summary_query_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            return {
                'total_results': 0,
                'successful_results': 0,
                'expected_results': 0,
            }

    def get_by_user_id(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        根据用户 ID 获取诊断历史记录

        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[Dict[str, Any]]: 诊断记录列表
        """
        try:
            with self.get_connection() as conn:
                cursor: sqlite3.Cursor = conn.cursor()

                select_sql = """
                    SELECT 
                        id, execution_id, user_id, brand_name,
                        status, stage, progress, is_completed,
                        created_at, completed_at
                    FROM diagnosis_reports
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """

                cursor.execute(select_sql, (user_id, limit, offset))
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            db_logger.error(
                "user_history_query_failed",
                extra={
                    'event': 'user_history_query_failed',
                    'user_id': user_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            return []
