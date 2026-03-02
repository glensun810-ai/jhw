"""
诊断事务管理器 - DiagnosisTransaction

核心职责：
1. 管理诊断执行过程中的所有数据库操作
2. 提供原子性回滚机制
3. 清理中间状态
4. 防止脏数据残留

设计原则：
1. 上下文管理器 - 使用 with 语句自动管理事务生命周期
2. 操作日志 - 记录所有已执行的操作以便回滚
3. 逆向回滚 - 按相反顺序撤销所有操作
4. 异常安全 - 任何异常都会触发回滚

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0
"""

import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
from wechat_backend.logging_config import db_logger, api_logger


class OperationType(Enum):
    """操作类型枚举"""
    CREATE_REPORT = "create_report"
    ADD_RESULT = "add_result"
    ADD_RESULTS_BATCH = "add_results_batch"
    ADD_ANALYSIS = "add_analysis"
    UPDATE_REPORT_STATUS = "update_report_status"
    UPDATE_EXECUTION_STORE = "update_execution_store"
    CUSTOM = "custom"


class TransactionOperation:
    """事务操作记录"""

    def __init__(
        self,
        op_type: OperationType,
        data: Any,
        rollback_func: Callable,
        description: str = ""
    ):
        self.op_type = op_type
        self.data = data
        self.rollback_func = rollback_func
        self.description = description
        self.executed_at = datetime.now()
        self.rolled_back = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'op_type': self.op_type.value,
            'data': self._serialize_data(),
            'description': self.description,
            'executed_at': self.executed_at.isoformat(),
            'rolled_back': self.rolled_back
        }

    def _serialize_data(self) -> Any:
        """序列化数据（用于日志）"""
        if isinstance(self.data, dict):
            return {k: v for k, v in self.data.items() if not callable(v)}
        elif isinstance(self.data, (list, tuple)):
            return list(self.data)
        else:
            return str(self.data)


class DiagnosisTransaction:
    """
    诊断事务管理器

    使用上下文管理器确保所有操作要么全部成功，要么全部回滚：

    示例:
        with DiagnosisTransaction(execution_id) as tx:
            # 创建报告
            report_id = tx.create_report(user_id, config)

            # 批量添加结果
            tx.add_results_batch(report_id, results)

            # 添加分析数据
            tx.add_analysis(report_id, analysis_data)

            # 如果任何一步失败，自动回滚所有操作
    """

    def __init__(
        self,
        execution_id: str,
        execution_store: Optional[Dict[str, Any]] = None,
        auto_rollback: bool = True
    ):
        """
        初始化事务管理器

        参数:
            execution_id: 执行 ID
            execution_store: 执行状态存储（内存）
            auto_rollback: 是否自动回滚（默认 True）
        """
        self.execution_id = execution_id
        self.execution_store = execution_store or {}
        self.auto_rollback = auto_rollback

        # 操作日志（按执行顺序记录）
        self.operations: List[TransactionOperation] = []

        # 事务状态
        self.status = "initialized"
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None

        # 依赖项（延迟初始化）
        self._report_service = None
        self._report_repo = None
        self._result_repo = None
        self._analysis_repo = None
        self._state_manager = None

        db_logger.info(f"[Transaction] 事务初始化：{self.execution_id}")

    def _init_dependencies(self):
        """初始化依赖项"""
        if self._report_service is None:
            from wechat_backend.diagnosis_report_service import get_report_service
            from wechat_backend.diagnosis_report_repository import (
                DiagnosisReportRepository,
                DiagnosisResultRepository,
                DiagnosisAnalysisRepository
            )
            from wechat_backend.state_manager import get_state_manager

            self._report_service = get_report_service()
            self._report_repo = DiagnosisReportRepository()
            self._result_repo = DiagnosisResultRepository()
            self._analysis_repo = DiagnosisAnalysisRepository()
            self._state_manager = get_state_manager(self.execution_store)

    def __enter__(self):
        """进入事务上下文"""
        self.status = "active"
        self.started_at = datetime.now()
        self._init_dependencies()
        db_logger.info(f"[Transaction] 事务开始：{self.execution_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出事务上下文"""
        self.completed_at = datetime.now()

        if exc_type is not None:
            # 发生异常
            self.error = str(exc_val)
            api_logger.error(
                f"[Transaction] 事务执行失败：{self.execution_id}, "
                f"错误：{self.error}"
            )

            if self.auto_rollback:
                self.rollback()
            else:
                db_logger.warning(
                    f"[Transaction] 事务失败但未回滚（auto_rollback=False）: "
                    f"{self.execution_id}"
                )

            self.status = "failed"
            # 不抑制异常，返回 False
            return False
        else:
            # 执行成功
            self.status = "committed"
            db_logger.info(f"[Transaction] 事务提交：{self.execution_id}")
            return False

    # ========== 事务操作方法 ==========

    def create_report(
        self,
        user_id: str,
        config: Dict[str, Any]
    ) -> int:
        """
        创建诊断报告（事务操作）

        参数:
            user_id: 用户 ID
            config: 诊断配置

        返回:
            report_id: 报告 ID
        """
        self._init_dependencies()

        # 执行创建
        report_id = self._report_service.create_report(
            self.execution_id,
            user_id,
            config
        )

        # 定义回滚函数
        def rollback_create():
            db_logger.info(
                f"[Transaction] 回滚：删除报告 report_id={report_id}"
            )
            self._report_repo.delete(report_id)

        # 记录操作
        self._log_operation(
            op_type=OperationType.CREATE_REPORT,
            data={'report_id': report_id, 'user_id': user_id, 'config': config},
            rollback_func=rollback_create,
            description=f"创建报告：report_id={report_id}"
        )

        db_logger.info(
            f"[Transaction] 操作完成：创建报告 report_id={report_id}"
        )
        return report_id

    def add_result(
        self,
        report_id: int,
        result: Dict[str, Any]
    ) -> int:
        """
        添加单个诊断结果（事务操作）

        参数:
            report_id: 报告 ID
            result: 结果数据

        返回:
            result_id: 结果 ID
        """
        self._init_dependencies()

        # 执行添加
        result_id = self._result_repo.add(report_id, self.execution_id, result)

        # 定义回滚函数
        def rollback_add_result():
            db_logger.info(
                f"[Transaction] 回滚：删除结果 result_id={result_id}"
            )
            self._result_repo.delete(result_id)

        # 记录操作
        self._log_operation(
            op_type=OperationType.ADD_RESULT,
            data={
                'result_id': result_id,
                'report_id': report_id,
                'brand': result.get('brand', ''),
                'question': result.get('question', '')
            },
            rollback_func=rollback_add_result,
            description=f"添加结果：result_id={result_id}, brand={result.get('brand', '')}"
        )

        return result_id

    def add_results_batch(
        self,
        report_id: int,
        results: List[Dict[str, Any]]
    ) -> List[int]:
        """
        批量添加诊断结果（事务操作）

        参数:
            report_id: 报告 ID
            results: 结果列表

        返回:
            result_ids: 结果 ID 列表
        """
        self._init_dependencies()

        # 执行批量添加
        result_ids = self._report_service.add_results_batch(
            report_id,
            self.execution_id,
            results
        )

        # 定义回滚函数（批量删除）
        def rollback_add_results_batch():
            db_logger.info(
                f"[Transaction] 回滚：批量删除结果 count={len(result_ids)}"
            )
            for rid in result_ids:
                try:
                    self._result_repo.delete(rid)
                except Exception as e:
                    db_logger.error(
                        f"[Transaction] 回滚失败：result_id={rid}, 错误：{e}"
                    )

        # 记录操作
        self._log_operation(
            op_type=OperationType.ADD_RESULTS_BATCH,
            data={
                'report_id': report_id,
                'result_ids': result_ids,
                'count': len(results)
            },
            rollback_func=rollback_add_results_batch,
            description=f"批量添加结果：count={len(results)}"
        )

        db_logger.info(
            f"[Transaction] 操作完成：批量添加结果 count={len(results)}"
        )
        return result_ids

    def add_analysis(
        self,
        report_id: int,
        analysis_type: str,
        analysis_data: Dict[str, Any]
    ) -> int:
        """
        添加分析数据（事务操作）

        参数:
            report_id: 报告 ID
            analysis_type: 分析类型 (brand_analysis/competitive_analysis)
            analysis_data: 分析数据

        返回:
            analysis_id: 分析 ID
        """
        self._init_dependencies()

        # 执行添加
        analysis_id = self._analysis_repo.add(
            report_id,
            analysis_type,
            analysis_data
        )

        # 定义回滚函数
        def rollback_add_analysis():
            db_logger.info(
                f"[Transaction] 回滚：删除分析 analysis_id={analysis_id}"
            )
            self._analysis_repo.delete(analysis_id)

        # 记录操作
        self._log_operation(
            op_type=OperationType.ADD_ANALYSIS,
            data={
                'analysis_id': analysis_id,
                'report_id': report_id,
                'analysis_type': analysis_type
            },
            rollback_func=rollback_add_analysis,
            description=f"添加分析：type={analysis_type}, id={analysis_id}"
        )

        return analysis_id

    def update_report_status(
        self,
        report_id: int,
        status: str,
        progress: int = 0,
        stage: str = "",
        is_completed: bool = False
    ):
        """
        更新报告状态（事务操作）

        参数:
            report_id: 报告 ID
            status: 状态
            progress: 进度 (0-100)
            stage: 阶段
            is_completed: 是否完成
        """
        self._init_dependencies()

        # 保存旧状态（用于回滚）
        old_report = self._report_repo.get_by_id(report_id)
        old_status = old_report.get('status') if old_report else None
        old_progress = old_report.get('progress') if old_report else 0

        # 执行更新
        self._report_repo.update_status(
            report_id,
            status=status,
            progress=progress,
            stage=stage,
            is_completed=is_completed
        )

        # 定义回滚函数
        def rollback_update_status():
            db_logger.info(
                f"[Transaction] 回滚：恢复报告状态 report_id={report_id}, "
                f"status={old_status}, progress={old_progress}"
            )
            self._report_repo.update_status(
                report_id,
                status=old_status,
                progress=old_progress
            )

        # 记录操作
        self._log_operation(
            op_type=OperationType.UPDATE_REPORT_STATUS,
            data={
                'report_id': report_id,
                'old_status': old_status,
                'new_status': status,
                'old_progress': old_progress,
                'new_progress': progress
            },
            rollback_func=rollback_update_status,
            description=f"更新状态：{old_status} -> {status}"
        )

    def update_execution_store(
        self,
        key: str,
        value: Any,
        rollback_value: Any = None
    ):
        """
        更新执行存储（内存）（事务操作）

        参数:
            key: 键
            value: 新值
            rollback_value: 回滚值（如果不提供，使用删除操作）
        """
        # 保存旧值
        old_value = self.execution_store.get(key) if self.execution_store else None

        # 执行更新
        if self.execution_store is not None:
            self.execution_store[key] = value

        # 定义回滚函数
        def rollback_update_store():
            if self.execution_store is not None:
                if rollback_value is not None or old_value is not None:
                    self.execution_store[key] = (
                        rollback_value if rollback_value is not None
                        else old_value
                    )
                else:
                    # 删除键
                    self.execution_store.pop(key, None)

            db_logger.debug(
                f"[Transaction] 回滚：恢复执行存储 key={key}, "
                f"value={rollback_value if rollback_value is not None else old_value}"
            )

        # 记录操作
        self._log_operation(
            op_type=OperationType.UPDATE_EXECUTION_STORE,
            data={
                'key': key,
                'old_value': old_value,
                'new_value': value
            },
            rollback_func=rollback_update_store,
            description=f"更新执行存储：{key}={value}"
        )

    def register_custom_operation(
        self,
        description: str,
        data: Any,
        rollback_func: Callable
    ):
        """
        注册自定义操作（用于扩展）

        参数:
            description: 操作描述
            data: 操作数据
            rollback_func: 回滚函数
        """
        self._log_operation(
            op_type=OperationType.CUSTOM,
            data=data,
            rollback_func=rollback_func,
            description=description
        )

    # ========== 内部方法 ==========

    def _log_operation(
        self,
        op_type: OperationType,
        data: Any,
        rollback_func: Callable,
        description: str
    ):
        """记录操作日志"""
        operation = TransactionOperation(
            op_type=op_type,
            data=data,
            rollback_func=rollback_func,
            description=description
        )
        self.operations.append(operation)
        db_logger.debug(
            f"[Transaction] 操作日志：{description} - {self.execution_id}"
        )

    # ========== 回滚方法 ==========

    def rollback(self):
        """
        回滚所有操作

        按相反顺序执行所有回滚函数
        """
        db_logger.warning(
            f"[Transaction] 开始回滚：{self.execution_id}, "
            f"操作数={len(self.operations)}"
        )

        rollback_count = 0
        error_count = 0

        # 逆向遍历，按相反顺序回滚
        for operation in reversed(self.operations):
            if operation.rolled_back:
                continue

            try:
                operation.rollback_func()
                operation.rolled_back = True
                rollback_count += 1
                db_logger.info(
                    f"[Transaction] 回滚成功：{operation.description}"
                )
            except Exception as e:
                error_count += 1
                db_logger.error(
                    f"[Transaction] 回滚失败：{operation.description}, "
                    f"错误：{e}"
                )

        # 清理执行存储
        self._cleanup_execution_store()

        # 记录回滚结果
        db_logger.warning(
            f"[Transaction] 回滚完成：{self.execution_id}, "
            f"成功={rollback_count}, 失败={error_count}"
        )

        return {
            'success': error_count == 0,
            'rollback_count': rollback_count,
            'error_count': error_count
        }

    def _cleanup_execution_store(self):
        """清理执行存储"""
        if self.execution_store is None:
            return

        keys_to_cleanup = [
            f"{self.execution_id}_status",
            f"{self.execution_id}_stage",
            f"{self.execution_id}_progress",
            f"{self.execution_id}_error"
        ]

        for key in keys_to_cleanup:
            self.execution_store.pop(key, None)

        db_logger.info(
            f"[Transaction] 执行存储已清理：{self.execution_id}"
        )

    # ========== 查询方法 ==========

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """获取操作日志"""
        return [op.to_dict() for op in self.operations]

    def get_summary(self) -> Dict[str, Any]:
        """获取事务摘要"""
        return {
            'execution_id': self.execution_id,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'operation_count': len(self.operations),
            'rolled_back_count': sum(1 for op in self.operations if op.rolled_back),
            'error': self.error
        }


# ========== 上下文管理器装饰器 ==========

@contextmanager
def transaction_context(
    execution_id: str,
    execution_store: Optional[Dict[str, Any]] = None,
    auto_rollback: bool = True
):
    """
    事务上下文管理器（函数式）

    使用示例:
        with transaction_context(execution_id, store) as tx:
            tx.create_report(user_id, config)
            tx.add_results_batch(report_id, results)
    """
    tx = DiagnosisTransaction(execution_id, execution_store, auto_rollback)
    try:
        with tx:
            yield tx
    except Exception:
        # 异常已由 __exit__ 处理
        raise


# ========== 便捷函数 ==========

def get_transaction(
    execution_id: str,
    execution_store: Optional[Dict[str, Any]] = None
) -> DiagnosisTransaction:
    """
    获取事务管理器实例

    参数:
        execution_id: 执行 ID
        execution_store: 执行状态存储

    返回:
        DiagnosisTransaction 实例
    """
    return DiagnosisTransaction(execution_id, execution_store)
