"""
诊断编排器 - DiagnosisOrchestrator

核心职责：
1. 协调所有子流程的顺序执行
2. 确保每个阶段完成后才进入下一阶段
3. 统一状态管理
4. 完整持久化验证

设计原则：
1. 顺序执行 - API 响应保存 → 统计分析 → 结果聚合 → 报告生成
2. 状态一致 - 内存和数据库原子性更新
3. 完整持久化 - 所有结果必须完整保存后才能进入下一环节
4. 错误隔离 - 单个阶段失败不影响已完成的阶段

@author: 系统架构组
@date: 2026-03-02
@version: 1.0.0 (阶段七：错误处理增强版)
"""

import asyncio
import json
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from wechat_backend.logging_config import api_logger, db_logger
from contextlib import asynccontextmanager

# 【阶段六：事务管理】导入事务管理器
from wechat_backend.services.diagnosis_transaction import (
    DiagnosisTransaction,
    transaction_context
)

# 【阶段七：错误处理】导入错误码、错误日志和重试机制
from wechat_backend.error_codes import (
    DiagnosisErrorCode,
    AIPlatformErrorCode,
    DatabaseErrorCode,
    AnalyticsErrorCode,
    get_error_code
)
from wechat_backend.error_logger import get_error_logger
from wechat_backend.error_recovery import (
    RetryHandler,
    RetryConfig,
    PresetRetryConfigs,
    diagnosis_retry,
    ai_call_retry,
    database_retry
)


class DiagnosisPhase(Enum):
    """诊断阶段枚举"""
    INIT = "init"
    AI_FETCHING = "ai_fetching"
    RESULTS_SAVING = "results_saving"
    RESULTS_VALIDATING = "results_validating"
    BACKGROUND_ANALYSIS = "background_analysis"
    REPORT_AGGREGATING = "report_aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseResult:
    """阶段结果封装"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }


class DiagnosisOrchestrator:
    """
    诊断编排器

    核心原则:
    1. 顺序执行 - 每个阶段必须完成后才进入下一阶段
    2. 状态一致 - 内存和数据库状态必须同步
    3. 完整持久化 - 每个阶段的结果必须完整保存
    4. 错误隔离 - 单个阶段失败不影响已完成的阶段
    """

    def __init__(self, execution_id: str, execution_store: Dict[str, Any]):
        """
        初始化编排器

        参数：
            execution_id: 执行 ID
            execution_store: 执行状态存储（内存）
        """
        self.execution_id = execution_id
        self.execution_store = execution_store
        self.current_phase = DiagnosisPhase.INIT
        self.phase_results: Dict[str, PhaseResult] = {}
        self.start_time = datetime.now()

        # 【阶段七：错误处理】初始化错误日志记录器和重试处理器
        self._error_logger = get_error_logger()
        self._retry_handler = RetryHandler(PresetRetryConfigs.DIAGNOSIS_RETRY)

        # 初始化状态管理器
        self._state_manager = None
        self._init_state_manager()

        api_logger.info(f"[Orchestrator] 初始化：{self.execution_id}")

    def _init_state_manager(self):
        """初始化状态管理器"""
        try:
            from wechat_backend.state_manager import get_state_manager
            self._state_manager = get_state_manager(self.execution_store)
            api_logger.debug(f"[Orchestrator] 状态管理器已初始化：{self.execution_id}")
        except Exception as e:
            api_logger.error(f"[Orchestrator] 状态管理器初始化失败：{e}")
            self._state_manager = None

    # 【阶段六：事务管理】新增事务上下文管理器
    def _init_transaction(self):
        """初始化事务管理器"""
        self._transaction = DiagnosisTransaction(
            execution_id=self.execution_id,
            execution_store=self.execution_store,
            auto_rollback=True
        )
        api_logger.info(f"[Orchestrator] 事务管理器已初始化：{self.execution_id}")

    # 【P0 修复 - 2026-03-05】新增短事务执行方法，缩小事务范围
    async def _execute_in_transaction(
        self,
        operation_func: Callable,
        operation_name: str
    ) -> Any:
        """
        在独立短事务中执行操作

        【P0 修复 - 2026-03-05】缩小事务范围，每个操作独立提交

        参数:
            operation_func: 操作函数 (接收 tx 参数)
            operation_name: 操作名称（用于日志）

        返回:
            操作结果
        """
        from wechat_backend.services.diagnosis_transaction import DiagnosisTransaction

        result = None
        try:
            # 创建独立事务
            with DiagnosisTransaction(
                execution_id=self.execution_id,
                execution_store=self.execution_store,
                auto_rollback=True
            ) as tx:
                # 执行操作并获取结果
                result = operation_func(tx)
                # 注意：事务会在 with 块结束时自动提交

            # 事务成功后记录日志
            summary = tx.get_summary() if tx else {'operation_count': 0, 'status': 'unknown'}
            db_logger.info(
                f"[Orchestrator] 短事务完成：{operation_name}, "
                f"operations={summary['operation_count']}, "
                f"status={summary['status']}"
            )

        except Exception as e:
            # 异常已被事务上下文抑制，需要重新抛出
            db_logger.error(
                f"[Orchestrator] 短事务失败：{operation_name}, "
                f"error={e}"
            )
            raise

        return result

    @asynccontextmanager
    async def _transaction_context(self):
        """
        事务上下文管理器（异步）

        使用示例:
            async with self._transaction_context():
                # 执行诊断流程
                await self._phase_init()
                await self._phase_ai_fetching()
                # ... 任何异常都会触发自动回滚
        """
        self._init_transaction()
        try:
            with self._transaction as tx:
                self._current_transaction = tx
                api_logger.info(
                    f"[Orchestrator] 事务上下文已开启：{self.execution_id}"
                )
                yield tx
        except Exception as e:
            api_logger.error(
                f"[Orchestrator] 事务执行失败：{self.execution_id}, 错误={e}"
            )
            # 异常会触发 __exit__ 中的自动回滚
            raise
        finally:
            # 记录事务摘要
            if hasattr(self, '_current_transaction'):
                summary = self._current_transaction.get_summary()
                api_logger.info(
                    f"[Orchestrator] 事务摘要：{self.execution_id}, "
                    f"status={summary['status']}, "
                    f"operations={summary['operation_count']}, "
                    f"rolled_back={summary['rolled_back_count']}"
                )

    def _update_phase_status(
        self,
        status: str,
        stage: str,
        progress: int,
        write_to_db: bool = True,
        **kwargs
    ):
        """
        更新阶段状态

        参数：
            status: 状态 (running/completed/failed)
            stage: 阶段名称
            progress: 进度百分比 (0-100)
            write_to_db: 是否写入数据库
        """
        if self._state_manager:
            try:
                self._state_manager.update_state(
                    execution_id=self.execution_id,
                    status=status,
                    stage=stage,
                    progress=progress,
                    write_to_db=write_to_db,
                    **kwargs
                )
                api_logger.info(
                    f"[Orchestrator] 状态更新：{self.execution_id}, "
                    f"status={status}, stage={stage}, progress={progress}"
                )
            except Exception as e:
                api_logger.error(f"[Orchestrator] 状态更新失败：{e}")

    async def execute_diagnosis(
        self,
        user_id: str,
        brand_list: List[str],
        selected_models: List[Dict[str, Any]],
        custom_questions: List[str],
        user_openid: Optional[str] = None,
        user_level: str = 'Free'
    ) -> Dict[str, Any]:
        """
        执行完整诊断流程

        【P0 关键修复 - 2026-03-05】事务拆分优化
        优化前：阶段 3-7 共用一个大事务，连接占用时间长
        优化后：每个数据库操作阶段使用独立短事务，快速提交释放连接

        严格顺序:
        1. 初始化阶段 (事务外 - 仅内存)
        2. AI 调用阶段 (事务外 - 网络 IO)
        3. 结果保存阶段 (事务 A - 短事务)
        4. 结果验证阶段 (事务外 - 只读验证)
        5. 后台分析阶段 (事务外 - 异步提交)
        6. 报告聚合阶段 (事务 B - 短事务)
        7. 完成阶段 (事务 C - 状态更新)

        参数：
            user_id: 用户 ID
            brand_list: 品牌列表 [主品牌，竞品 1, 竞品 2, ...]
            selected_models: 选中的 AI 模型列表
            custom_questions: 自定义问题列表
            user_openid: 用户 OpenID
            user_level: 用户等级

        返回：
            {
                'success': bool,
                'execution_id': str,
                'report': dict (可选),
                'error': str (可选),
                'error_code': str (可选),
                'trace_id': str (可选)
            }
        """
        # 【阶段七：错误处理】生成追踪 ID
        trace_id = f"diag_{uuid.uuid4().hex[:16]}"
        api_logger.info(f"[Orchestrator] 开始执行诊断：{self.execution_id}, TraceID={trace_id}")

        # 存储初始参数
        self._initial_params = {
            'user_id': user_id,
            'brand_list': brand_list,
            'selected_models': selected_models,
            'custom_questions': custom_questions,
            'user_openid': user_openid or user_id,
            'user_level': user_level,
            'trace_id': trace_id
        }

        try:
            # 【P0 关键修复 - 2026-03-05】诊断开始前检查并回收泄漏连接
            try:
                from wechat_backend.database_connection_pool import get_db_pool
                pool = get_db_pool()
                if hasattr(pool, 'force_recycle_leaked_connections'):
                    recycled = pool.force_recycle_leaked_connections(max_age_seconds=30.0)
                    if recycled > 0:
                        api_logger.info(
                            f"[Orchestrator] 诊断前回收泄漏连接：{self.execution_id}, "
                            f"回收数={recycled}"
                        )
            except Exception as pool_err:
                api_logger.warning(f"[Orchestrator] 连接池回收失败：{pool_err}")

            # ========== 阶段 1: 初始化 (事务外 - 仅内存) ==========
            phase1_result = await self._phase_init()
            if not phase1_result.success:
                raise ValueError(f"初始化失败：{phase1_result.error}")

            # ========== 阶段 2: AI 调用 (事务外 - 网络 IO) ==========
            # 【P0 关键修复 - 2026-03-04】拆分事务：AI 调用阶段不持有数据库连接
            # AI 调用是长耗时网络 IO (20-40 秒)，不应占用数据库连接
            phase2_result = await self._phase_ai_fetching(
                brand_list, selected_models, custom_questions, user_id, user_level
            )
            if not phase2_result.success:
                raise ValueError(f"AI 调用失败：{phase2_result.error}")

            # ========== 阶段 3: 结果保存 (事务 A - 短事务) ==========
            # 【P0 关键修复 - 2026-03-05】独立事务，快速提交释放连接
            phase3_result = await self._phase_results_saving_transaction(
                phase2_result.data, brand_list, selected_models, custom_questions
            )
            if not phase3_result.success:
                raise ValueError(f"结果保存失败：{phase3_result.error}")

            # 【P0 关键修复 - 2026-03-02】等待数据库提交完成
            # SQLite WAL 模式下，COMMIT 后数据可能还在 WAL 文件中，需要短暂等待
            await asyncio.sleep(0.1)  # 等待 100ms，确保数据持久化

            # ========== 阶段 4: 结果验证 (事务外 - 只读验证) ==========
            # 【P0 关键修复 - 2026-03-03】传递内存数据用于验证，但返回数据库数据供后续使用
            # 【P0 关键修复 - 2026-03-12 第 8 次】传递 brand_list 用于品牌多样性检查
            phase4_result = await self._phase_results_validating(phase2_result.data, brand_list)
            if not phase4_result.success:
                # 【P0 关键修复 - 2026-03-05】验证失败时记录错误，继续执行
                # 注意：阶段 3 的事务已提交，无法回滚，但可以标记为失败
                api_logger.warning(
                    f"[Orchestrator] ⚠️ 验证失败但结果已保存：{self.execution_id}, "
                    f"错误={phase4_result.error}"
                )
                # 不抛出异常，继续执行后续流程

            # 【P0 关键修复 - 2026-03-03】从验证结果中获取数据库中的实际数据
            db_results = phase4_result.data.get('saved_results', [])
            api_logger.info(
                f"[阶段 4 验证结果] execution_id={self.execution_id}, "
                f"db_results 数量={len(db_results)}"
            )
            
            # 【P0 关键追踪 - 2026-03-12 第 5 次】详细记录验证结果
            if not db_results or len(db_results) == 0:
                api_logger.error(
                    f"[阶段 4 验证结果] ❌ db_results 为空！"
                    f"这是数据丢失的环节：AI 调用→保存→验证"
                )
                api_logger.error(
                    f"[阶段 4 验证详情] execution_id={self.execution_id}, "
                    f"phase4_result.success={phase4_result.success}, "
                    f"phase4_result.error={phase4_result.error if hasattr(phase4_result, 'error') else 'N/A'}"
                )
            else:
                api_logger.info(
                    f"[阶段 4 验证详情] ✅ db_results 有数据，第 1 条：brand={db_results[0].get('brand')}"
                )

            # 【P0 关键修复 - 2026-03-12 第 4 次】移除降级方案
            # 因为 WAL 检查点已确保数据可见，db_results 应该始终有数据
            # 如果仍然为空，说明有真正的问题，应该失败而非降级
            if not db_results or len(db_results) == 0:
                api_logger.error(
                    f"[Orchestrator] ❌ 数据库结果为空：{self.execution_id}, "
                    f"WAL 检查点后仍然为空，说明数据未正确保存！"
                )
                # 尝试从 execution_store 恢复（最后手段）
                if self.execution_id in self.execution_store:
                    stored_results = self.execution_store[self.execution_id].get('results', [])
                    if stored_results:
                        api_logger.warning(
                            f"[Orchestrator] ⚠️ 从 execution_store 恢复结果：{self.execution_id}, "
                            f"数量={len(stored_results)}"
                        )
                        db_results = stored_results
                    else:
                        raise ValueError(
                            f"诊断执行失败：数据库结果为空且 execution_store 中也没有结果，"
                            f"execution_id={self.execution_id}"
                        )
                else:
                    raise ValueError(
                        f"诊断执行失败：数据库结果为空，"
                        f"execution_id={self.execution_id}"
                    )

            # ========== 阶段 5: 后台分析 (事务外 - 异步提交) ==========
            # 【P0 关键修复 - 2026-03-05】即使结果保存部分失败，也尝试启动后台分析
            # 后台分析可以提供有价值的洞察，不应完全阻塞
            try:
                phase5_result = self._phase_background_analysis_async(
                    db_results if db_results else phase2_result.data,  # 使用数据库结果，如果失败则使用内存结果
                    brand_list
                )
                # 注意：此阶段异步执行，不等待完成
                api_logger.info(
                    f"[Orchestrator] ✅ 阶段 5 已启动：后台分析（异步）-{self.execution_id}"
                )
            except Exception as analysis_err:
                # 后台分析启动失败，记录警告但不阻塞主流程
                api_logger.warning(
                    f"[Orchestrator] ⚠️ 后台分析启动失败：{self.execution_id}, "
                    f"错误={analysis_err}"
                )

            # ========== 阶段 6: 报告聚合 (事务 B - 短事务) ==========
            # 【P0 关键修复 - 2026-03-05】独立事务，快速提交释放连接
            phase6_result = await self._phase_report_aggregating(
                db_results, brand_list
            )
            if not phase6_result.success:
                raise ValueError(f"报告聚合失败：{phase6_result.error}")

            # ========== 阶段 7: 完成 (事务 C - 状态更新) ==========
            # 【P0 关键修复 - 2026-03-05】独立事务，快速提交释放连接
            phase7_result = await self._phase_complete(phase6_result.data)
            if not phase7_result.success:
                raise ValueError(f"完成处理失败：{phase7_result.error}")

            # 所有阶段成功完成
            total_time = (datetime.now() - self.start_time).total_seconds()
            api_logger.info(
                f"[Orchestrator] ✅ 诊断执行完成：{self.execution_id}, "
                f"总耗时={total_time:.2f}秒，TraceID={trace_id}"
            )

            # 【P0 关键修复 - 2026-03-05】诊断完成后清理 execution_store，防止内存泄漏
            # 注意：清理延迟执行，确保前端有足够时间获取最终状态
            self._schedule_cleanup(delay_seconds=300)  # 5 分钟后清理

            return {
                'success': True,
                'execution_id': self.execution_id,
                'report': phase6_result.data,
                'total_time': total_time,
                'trace_id': trace_id
            }

        except Exception as e:
            # 【阶段七：错误处理】使用错误日志记录器记录详细错误
            error_code = self._determine_error_code(str(e))
            self._error_logger.log_error(
                error=e,
                error_code=error_code,
                execution_id=self.execution_id,
                user_id=self._initial_params.get('user_id') if hasattr(self, '_initial_params') else None,
                additional_info={
                    'trace_id': trace_id,
                    'phase': self.current_phase.value if self.current_phase else 'unknown',
                    'total_time': (datetime.now() - self.start_time).total_seconds(),
                }
            )

            api_logger.error(
                f"[Orchestrator] ❌ 诊断执行失败：{self.execution_id}, "
                f"错误={e}, TraceID={trace_id}",
                exc_info=True
            )
            await self._phase_failed(str(e), error_code)

            # 【P0 关键修复 - 2026-03-05】诊断失败后回收连接池，防止连接泄漏
            try:
                from wechat_backend.database_connection_pool import get_db_pool
                pool = get_db_pool()
                if hasattr(pool, 'force_recycle_leaked_connections'):
                    recycled = pool.force_recycle_leaked_connections(max_age_seconds=10.0)
                    if recycled > 0:
                        api_logger.info(
                            f"[Orchestrator] 诊断失败后回收泄漏连接：{self.execution_id}, "
                            f"回收数={recycled}"
                        )
            except Exception as pool_err:
                api_logger.warning(f"[Orchestrator] 连接池回收失败：{pool_err}")

            # 【P0 关键修复 - 2026-03-05】诊断失败后清理 execution_store，防止内存泄漏
            # 注意：失败时立即清理，因为错误状态已持久化到数据库
            self._schedule_cleanup(delay_seconds=60)  # 1 分钟后清理

            # 【P1 架构修复 - 2026-03-11】统一错误码处理，兼容多种类型
            # 支持：ErrorCode 枚举、Enum、元组 ('code', 'message', status)、字符串
            error_code_str, severity = self._error_logger._normalize_error_code(error_code)

            return {
                'success': False,
                'execution_id': self.execution_id,
                'error': str(e),
                'error_code': error_code_str,
                'trace_id': trace_id
            }

    async def _phase_init(self) -> PhaseResult:
        """
        阶段 1: 初始化

        任务：
        1. 设置初始状态（仅内存，不写数据库）
        2. 记录初始参数
        3. 准备执行环境

        【P1 关键修复 - 2026-03-03】Phase 1 不写入数据库，避免与 Phase 3 的事务管理冲突
        数据库记录由 Phase 3 使用事务管理器统一创建

        返回：
            PhaseResult
        """
        api_logger.info(f"[Orchestrator] 阶段 1: 初始化 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.INIT

        try:
            params = self._initial_params

            # 初始化 execution_store（内存状态）
            if self.execution_id not in self.execution_store:
                self.execution_store[self.execution_id] = {
                    'status': 'initializing',
                    'stage': 'init',
                    'progress': 0,
                    'start_time': datetime.now().isoformat(),
                    'results': [],
                    'detailed_results': {},
                    'brand_name': params['brand_list'][0],
                    'competitor_brands': params['brand_list'][1:],
                    'selected_models': params['selected_models'],
                    'custom_questions': params['custom_questions']
                }

            # 【P1 关键修复 - 2026-03-03】仅更新内存状态，不写入数据库
            # 数据库记录由 Phase 3 使用事务管理器统一创建，避免：
            # 1. 重复创建报告记录
            # 2. 事务管理冲突
            # 3. 数据不一致风险
            self._update_phase_status(
                status='initializing',
                stage='init',
                progress=0,
                write_to_db=False,  # 【P1 关键修复】不写数据库
                user_id=params['user_id'],
                brand_name=params['brand_list'][0],
                competitor_brands=params['brand_list'][1:],
                selected_models=params['selected_models'],
                custom_questions=params['custom_questions']
            )

            result = PhaseResult(
                success=True,
                data={'initialized': True}
            )
            self.phase_results['init'] = result

            api_logger.info(f"[Orchestrator] ✅ 阶段 1 完成：初始化 - {self.execution_id}")
            return result

        except Exception as e:
            api_logger.error(f"[Orchestrator] ❌ 阶段 1 失败：初始化 - {self.execution_id}, 错误={e}")
            return PhaseResult(success=False, error=str(e))

    async def _phase_ai_fetching(
        self,
        brand_list: List[str],
        selected_models: List[Dict],
        custom_questions: List[str],
        user_id: str,
        user_level: str
    ) -> PhaseResult:
        """
        阶段 2: AI 调用 (并行执行)

        【P2 优化 - 2026-03-11】AI 调用与数据库操作分离
        优化前：AI 调用前更新数据库状态，连接可能被占用
        优化后：AI 调用前仅更新内存状态，完成后批量写入

        任务：
        1. 更新内存状态为 AI 调用中（不写数据库）
        2. 执行并行 AI 调用（带重试机制，无数据库连接）
        3. 收集所有结果
        4. 完成后批量写入数据库

        参数：
            brand_list: 品牌列表
            selected_models: 模型列表
            custom_questions: 问题列表
            user_id: 用户 ID
            user_level: 用户等级

        返回：
            PhaseResult (包含 AI 调用结果)
        """
        api_logger.info(f"[Orchestrator] 阶段 2: AI 调用 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.AI_FETCHING

        try:
            # 【P2 优化 - 2026-03-11】仅更新内存状态，不写数据库
            # AI 调用是长耗时操作 (20-40 秒)，不应持有数据库连接
            self._update_phase_status(
                status='ai_fetching',
                stage='ai_fetching',
                progress=30,
                write_to_db=False  # 关键：不写数据库
            )

            # 【P2 优化 - 2026-03-11】异步执行 AI 调用（无数据库连接）
            from wechat_backend.nxm_concurrent_engine_v3 import execute_parallel_nxm

            # 创建 AI 调用重试处理器
            ai_retry_handler = RetryHandler(PresetRetryConfigs.AI_CALL_RETRY)

            async def _execute_ai_call():
                return await execute_parallel_nxm(
                    execution_id=self.execution_id,
                    main_brand=brand_list[0],
                    competitor_brands=brand_list[1:] if len(brand_list) > 1 else [],
                    selected_models=selected_models,
                    raw_questions=custom_questions,
                    user_id=user_id,
                    user_level=user_level,
                    max_concurrent=6
                )

            # 执行带重试的 AI 调用（无数据库连接）
            retry_result = await ai_retry_handler.execute_with_retry_async(
                _execute_ai_call,
                execution_id=self.execution_id
            )

            if not retry_result.success:
                # 重试失败，记录错误
                # 【P1 修复 - 2026-03-11】直接传入枚举值，让 error_logger 统一处理
                self._error_logger.log_error(
                    error=retry_result.error,
                    error_code=AIPlatformErrorCode.AI_SERVICE_UNAVAILABLE,
                    execution_id=self.execution_id,
                    user_id=user_id,
                    additional_info={
                        'attempts': len(retry_result.attempts),
                        'total_time': retry_result.total_time,
                    }
                )
                # 【P2 优化 - 2026-03-11】失败时更新数据库状态
                self._update_phase_status(
                    status='failed',
                    stage='ai_fetching',
                    progress=30,
                    write_to_db=True,
                    error_message=f"AI 调用失败：{str(retry_result.error)}"
                )
                return PhaseResult(
                    success=False,
                    error=f"AI 调用失败（已重试{len(retry_result.attempts)}次）: {str(retry_result.error)}"
                )

            result = retry_result.result

            # 检查执行结果
            if not result.get('success'):
                # 【P2 优化 - 2026-03-11】失败时更新数据库状态
                self._update_phase_status(
                    status='failed',
                    stage='ai_fetching',
                    progress=30,
                    write_to_db=True,
                    error_message=result.get('error', 'AI 调用失败')
                )
                return PhaseResult(
                    success=False,
                    error=result.get('error', 'AI 调用失败')
                )

            # 提取结果
            ai_results = result.get('results', [])
            api_logger.info(
                f"[Orchestrator] AI 调用完成：{self.execution_id}, "
                f"结果数={len(ai_results)}, 重试次数={len(retry_result.attempts) - 1}"
            )
            
            # 【P0 关键追踪 - 2026-03-12 第 5 次】详细记录 AI 调用结果
            if ai_results:
                api_logger.info(
                    f"[AI 结果详情] execution_id={self.execution_id}, "
                    f"第 1 条结果：brand={ai_results[0].get('brand')}, "
                    f"question={ai_results[0].get('question')[:50] if ai_results[0].get('question') else 'None'}"
                )
            else:
                api_logger.error(
                    f"[AI 结果详情] ❌ ai_results 为空！result 内容：{json.dumps(result, ensure_ascii=False)[:500]}"
                )

            # 【P0 修复 - 2026-03-04】检查 AI 调用结果是否为空
            if not ai_results or len(ai_results) == 0:
                error_msg = f"AI 调用返回空结果：{self.execution_id}"
                api_logger.error(f"[Orchestrator] ❌ {error_msg}")
                # 【P1 修复 - 2026-03-11】直接传入枚举值
                self._error_logger.log_error(
                    error=Exception(error_msg),
                    error_code=AIPlatformErrorCode.AI_SERVICE_UNAVAILABLE,
                    execution_id=self.execution_id,
                    user_id=user_id,
                    additional_info={
                        'ai_response': result,
                        'retry_attempts': len(retry_result.attempts),
                    }
                )
                # 【P2 优化 - 2026-03-11】失败时更新数据库状态
                self._update_phase_status(
                    status='failed',
                    stage='ai_fetching',
                    progress=30,
                    write_to_db=True,
                    error_message=error_msg
                )
                return PhaseResult(
                    success=False,
                    error=error_msg
                )

            # 【P2 优化 - 2026-03-11】成功后批量更新数据库
            # AI 调用完成后才写入，避免长耗时占用连接
            self._update_phase_status(
                status='ai_fetching',
                stage='ai_fetching',
                progress=30,
                write_to_db=True  # 完成后写入
            )

            # 更新 execution_store（内存）
            if self.execution_id in self.execution_store:
                self.execution_store[self.execution_id]['results'] = ai_results
                # 【P0 关键修复 - 2026-03-12 第 9 次】同步更新 detailed_results，确保前端能看到数据
                self.execution_store[self.execution_id]['detailed_results'] = ai_results
                self.execution_store[self.execution_id]['status'] = 'ai_fetching'
                self.execution_store[self.execution_id]['progress'] = 30
                api_logger.info(
                    f"[Orchestrator] ✅ execution_store 已更新：{self.execution_id}, "
                    f"results 数量={len(ai_results)}, detailed_results 数量={len(ai_results)}"
                )

            result_obj = PhaseResult(
                success=True,
                data=ai_results
            )
            self.phase_results['ai_fetching'] = result_obj

            api_logger.info(f"[Orchestrator] ✅ 阶段 2 完成：AI 调用 - {self.execution_id}")
            return result_obj

        except Exception as e:
            # 【阶段七：错误处理】记录详细错误日志
            # 【P1 修复 - 2026-03-11】直接传入枚举值
            self._error_logger.log_error(
                error=e,
                error_code=AIPlatformErrorCode.AI_SERVICE_UNAVAILABLE,
                execution_id=self.execution_id,
                user_id=user_id,
            )
            api_logger.error(f"[Orchestrator] ❌ 阶段 2 失败：AI 调用 - {self.execution_id}, 错误={e}")
            return PhaseResult(success=False, error=str(e))

    async def _phase_results_saving_transaction(
        self,
        results: List[Dict[str, Any]],
        brand_list: List[str],
        selected_models: List[Dict],
        custom_questions: List[str]
    ) -> PhaseResult:
        """
        阶段 3: 结果保存（P0 修复 - 拆分为独立短事务）

        【P0 修复 - 2026-03-05】缩小事务范围，每个操作独立提交
        - 子事务 1: 创建报告（独立事务，快速提交）
        - 子事务 2: 分批保存结果（独立事务，分批提交）

        任务：
        1. 更新状态为结果保存中
        2. 使用独立短事务创建报告记录
        3. 使用独立短事务批量保存结果（分批提交）
        4. 如果任何步骤失败，自动回滚

        参数：
            results: AI 调用结果列表
            brand_list: 品牌列表
            selected_models: 模型列表
            custom_questions: 问题列表

        返回：
            PhaseResult
        """
        api_logger.info(f"[Orchestrator] 阶段 3: 结果保存 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.RESULTS_SAVING

        try:
            # 更新状态为结果保存中
            self._update_phase_status(
                status='results_saving',
                stage='results_saving',
                progress=60,
                write_to_db=True
            )

            params = self._initial_params

            # 创建报告配置
            config = {
                'brand_name': brand_list[0],
                'competitor_brands': brand_list[1:] if len(brand_list) > 1 else [],
                'selected_models': selected_models,
                'custom_questions': custom_questions
            }

            # 【P0 修复】子事务 1: 创建报告（独立事务）
            # 检查 report_id 是否已存在（提前创建的情况）
            if hasattr(self, '_report_id') and self._report_id is not None:
                api_logger.info(
                    f"[Orchestrator] 使用已存在的 report_id: {self.execution_id}, "
                    f"report_id={self._report_id}"
                )
                report_id = self._report_id
            else:
                report_id = await self._execute_in_transaction(
                    lambda tx: tx.create_report(
                        user_id=params['user_id'] or 'anonymous',
                        config=config
                    ),
                    operation_name="create_report"
                )
                # 存储 report_id 供后续阶段使用
                self._report_id = report_id

            # 【P0 修复】子事务 2: 分批保存结果（独立事务）
            if results:
                api_logger.info(
                    f"[阶段 3 开始] execution_id={self.execution_id}, "
                    f"准备保存 results 数量={len(results)}"
                )
                
                result_ids = await self._execute_in_transaction(
                    lambda tx: tx.add_results_batch(
                        report_id=report_id,
                        results=results,
                        batch_size=10  # 每批 10 条，减少连接持有时间
                    ),
                    operation_name="add_results_batch"
                )
                api_logger.info(
                    f"[阶段 3 完成] execution_id={self.execution_id}, "
                    f"保存成功数量={len(result_ids)}"
                )
                
                # 【P0 关键修复 - 2026-03-12 第 5 次】验证保存后立即可读
                # 使用同一个连接验证，排除 WAL 可见性问题
                try:
                    from wechat_backend.database_connection_pool import get_db_pool
                    pool = get_db_pool()
                    conn = pool.get_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            'SELECT COUNT(*) FROM diagnosis_results WHERE execution_id = ?',
                            (self.execution_id,)
                        )
                        count = cursor.fetchone()[0]
                        api_logger.info(
                            f"[保存验证] execution_id={self.execution_id}, "
                            f"数据库中的结果数={count}"
                        )
                        if count == 0:
                            api_logger.error(
                                f"[保存验证] ❌ 保存后立即查询为 0！这是数据丢失的关键证据！"
                            )
                    finally:
                        pool.return_connection(conn)
                except Exception as verify_err:
                    api_logger.error(
                        f"[保存验证] ❌ 验证失败：{self.execution_id}, 错误={verify_err}"
                    )
                
                # 【P0 关键修复 - 2026-03-12 第 4 次】强制 WAL 检查点，确保数据立即可见
                # 这是解决 SQLite WAL 模式数据可见性问题的根本方案
                try:
                    from wechat_backend.database_connection_pool import get_db_pool
                    pool = get_db_pool()
                    # 获取连接执行检查点
                    conn = pool.get_connection()
                    try:
                        # 执行 WAL 检查点，将 WAL 文件中的数据写入主数据库文件
                        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                        api_logger.info(
                            f"[Orchestrator] ✅ WAL 检查点完成：{self.execution_id}, "
                            f"数据已立即可见"
                        )
                        
                        # 检查点后再验证一次
                        cursor = conn.cursor()
                        cursor.execute(
                            'SELECT COUNT(*) FROM diagnosis_results WHERE execution_id = ?',
                            (self.execution_id,)
                        )
                        count_after = cursor.fetchone()[0]
                        api_logger.info(
                            f"[WAL 检查点后验证] execution_id={self.execution_id}, "
                            f"数据库中的结果数={count_after}"
                        )
                        
                        # 【P0 关键修复 - 2026-03-12 第 5 次】强制关闭 WAL 文件句柄，确保新连接能看到数据
                        # 这是关键：SQLite 连接可能缓存了数据库状态，需要强制刷新
                        conn.execute('PRAGMA wal_checkpoint(PASSIVE)')
                        
                    finally:
                        pool.return_connection(conn)
                    
                    # 【P0 关键修复 - 2026-03-12 第 5 次】等待一小段时间，确保其他连接能看到数据
                    # 这给了 SQLite 时间刷新其内部缓存
                    await asyncio.sleep(0.05)  # 50ms
                    
                except Exception as checkpoint_err:
                    api_logger.warning(
                        f"[Orchestrator] ⚠️ WAL 检查点失败：{self.execution_id}, "
                        f"错误={checkpoint_err}"
                    )
                    # 检查点失败不影响主流程，使用等待方案降级
                    api_logger.info(
                        f"[Orchestrator] 使用等待方案：{self.execution_id}, "
                        f"等待 500ms 确保数据可见"
                    )
                    await asyncio.sleep(0.5)
            else:
                api_logger.error(
                    f"[阶段 3] ❌ results 为空，无法保存：{self.execution_id}"
                )

            # 存储 report_id 供后续阶段使用
            self._report_id = report_id

            result_obj = PhaseResult(
                success=True,
                data={'report_id': report_id, 'saved_count': len(results) if results else 0}
            )
            self.phase_results['results_saving'] = result_obj

            api_logger.info(f"[Orchestrator] ✅ 阶段 3 完成：结果保存 - {self.execution_id}")
            return result_obj

        except Exception as e:
            api_logger.error(f"[Orchestrator] ❌ 阶段 3 失败：结果保存 - {self.execution_id}, 错误={e}")
            return PhaseResult(success=False, error=str(e))

    async def _phase_results_validating(
        self,
        results: List[Dict[str, Any]],
        brand_list: Optional[List[str]] = None
    ) -> PhaseResult:
        """
        阶段 4: 结果验证（使用 ResultValidator 服务）

        任务：
        1. 更新状态为结果验证中
        2. 使用 ResultValidator 进行数量验证
        3. 使用 ResultValidator 进行质量验证
        4. 使用 ResultValidator 进行完整性验证
        5. 【P0 关键修复 - 2026-03-03】返回数据库中的实际数据供后续环节使用
        6. 【P0 关键修复 - 2026-03-12 第 8 次】添加品牌多样性检查，支持降级执行

        参数：
            results: AI 调用结果列表（用于数量对比）
            brand_list: 品牌列表（可选，用于品牌多样性检查）

        返回：
            PhaseResult (data 包含验证结果 + 数据库中的 saved_results)
        """
        api_logger.info(f"[Orchestrator] 阶段 4: 结果验证 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.RESULTS_VALIDATING

        try:
            # 更新状态为结果验证中
            self._update_phase_status(
                status='results_validating',
                stage='results_validating',
                progress=70,
                write_to_db=True
            )

            # 使用 ResultValidator 进行完整验证
            # 【P0 关键修复 - 2026-03-03】validate 现在返回 (ValidationResult, saved_results)
            from wechat_backend.services.result_validator import get_result_validator, ValidationLevel

            validator = get_result_validator(validation_level=ValidationLevel.NORMAL)
            validation_result, saved_results = validator.validate(
                execution_id=self.execution_id,
                expected_results=results,
                validate_quality=True,
                validate_completeness=True
            )

            # 记录验证详情
            api_logger.info(
                f"[Orchestrator] 验证结果：{self.execution_id}, "
                f"status={validation_result.status.value}, "
                f"message={validation_result.message}, "
                f"数据库结果数={len(saved_results)}"
            )

            # 【P0 关键修复 - 2026-03-12 第 8 次】品牌多样性检查
            quality_warnings = []
            if brand_list and saved_results:
                unique_brands = set(r.get('brand') for r in saved_results if r.get('brand'))
                expected_brand_count = len(brand_list) if brand_list else 1

                if len(unique_brands) < expected_brand_count:
                    missing = set(brand_list) - unique_brands if brand_list else set()
                    quality_warnings.append({
                        'type': 'missing_brands',
                        'severity': 'warning',
                        'message': f'缺失 {len(missing)} 个品牌的数据：{missing}',
                        'suggestion': '报告将基于已有数据生成，但可能不完整'
                    })
                    api_logger.warning(
                        f"[Orchestrator] ⚠️ 品牌多样性不足：{self.execution_id}, "
                        f"期望品牌数={expected_brand_count}, "
                        f"实际品牌数={len(unique_brands)}, "
                        f"缺失={missing}"
                    )

            # 检查验证是否通过
            if not validation_result.is_passed:
                error_msg = validation_result.message

                # 添加详细错误信息
                if validation_result.invalid_results:
                    error_msg += f", 无效数={len(validation_result.invalid_results)}"
                if validation_result.missing_fields:
                    error_msg += f", 缺失字段数={len(validation_result.missing_fields)}"
                if validation_result.warnings:
                    error_msg += f", 警告={len(validation_result.warnings)}"

                api_logger.error(
                    f"[Orchestrator] 验证失败：{self.execution_id}, "
                    f"错误={error_msg}, "
                    f"details={validation_result.to_dict()}"
                )
                return PhaseResult(success=False, error=error_msg)

            # 验证通过，记录成功信息
            api_logger.info(
                f"[Orchestrator] ✅ 验证通过：{self.execution_id}, "
                f"期望={validation_result.expected_count}, "
                f"实际={validation_result.actual_count}, "
                f"数据库结果数={len(saved_results)}, "
                f"无效={len(validation_result.invalid_results)}, "
                f"缺失={len(validation_result.missing_fields)}"
            )

            # 如果有警告，记录警告信息
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    api_logger.warning(
                        f"[Orchestrator] ⚠️ 警告：{self.execution_id}, {warning}"
                    )

            # 【P0 关键修复 - 2026-03-03】返回验证结果和数据库中的实际数据
            # 【P0 关键修复 - 2026-03-12 第 8 次】添加质量警告和部分成功标志
            result_data = validation_result.to_dict()
            result_data['saved_results'] = saved_results  # 添加数据库数据供后续环节使用

            # 【P0 关键修复 - 2026-03-12 第 9 次】同步更新 execution_store 中的 detailed_results
            # 确保前端轮询时能获取到验证后的数据
            if self.execution_id in self.execution_store:
                self.execution_store[self.execution_id]['detailed_results'] = saved_results
                self.execution_store[self.execution_id]['results'] = saved_results
                api_logger.info(
                    f"[Orchestrator] ✅ execution_store.detailed_results 已更新：{self.execution_id}, "
                    f"数量={len(saved_results)}"
                )

            # 添加品牌多样性警告
            if quality_warnings:
                result_data['qualityWarnings'] = quality_warnings
                result_data['partial_success'] = True
                api_logger.info(
                    f"[Orchestrator] ✅ 验证通过但数据不完整：{self.execution_id}, "
                    f"警告数={len(quality_warnings)}"
                )

            result_obj = PhaseResult(
                success=True,  # 【P0 关键修复 - 2026-03-12 第 8 次】即使有警告也返回成功，允许降级执行
                data=result_data
            )
            self.phase_results['results_validating'] = result_obj

            api_logger.info(f"[Orchestrator] ✅ 阶段 4 完成：结果验证 - {self.execution_id}")
            return result_obj

        except Exception as e:
            api_logger.error(f"[Orchestrator] ❌ 阶段 4 失败：结果验证 - {self.execution_id}, 错误={e}", exc_info=True)
            return PhaseResult(success=False, error=str(e))

    def _phase_background_analysis_async(
        self,
        results: List[Dict[str, Any]],
        brand_list: List[str]
    ) -> PhaseResult:
        """
        阶段 5: 后台分析 (异步，不阻塞主流程)

        任务：
        1. 更新状态为后台分析中
        2. 提交品牌分析任务到后台队列（传递用户选择的模型）
        3. 提交竞争分析任务到后台队列
        4. 不等待完成，继续执行

        参数：
            results: AI 调用结果列表
            brand_list: 品牌列表

        返回：
            PhaseResult
        """
        api_logger.info(f"[Orchestrator] 阶段 5: 后台分析 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.BACKGROUND_ANALYSIS

        try:
            # 更新状态为后台分析中
            self._update_phase_status(
                status='background_analysis',
                stage='background_analysis',
                progress=80,
                write_to_db=True
            )

            # 提交到后台任务队列
            try:
                from wechat_backend.services.background_service_manager import get_background_service_manager

                manager = get_background_service_manager()

                # 从初始参数中获取用户选择的模型列表
                user_selected_models = [
                    model.get('model', model.get('name', ''))
                    for model in self._initial_params.get('selected_models', [])
                ]

                # 品牌分析任务（传递用户选择的模型）
                manager.submit_analysis_task(
                    execution_id=self.execution_id,
                    task_type='brand_analysis',
                    payload={
                        'execution_id': self.execution_id,  # 【P2 修复】添加 execution_id
                        'results': results,
                        'user_brand': brand_list[0],
                        'competitor_brands': brand_list[1:] if len(brand_list) > 1 else [],
                        'user_selected_models': user_selected_models  # 【P0 修复】传递用户选择的模型
                    }
                )

                # 竞争分析任务
                manager.submit_analysis_task(
                    execution_id=self.execution_id,
                    task_type='competitive_analysis',
                    payload={
                        'execution_id': self.execution_id,  # 【P2 修复】添加 execution_id
                        'results': results,
                        'main_brand': brand_list[0],
                        'competitor_brands': brand_list[1:] if len(brand_list) > 1 else []
                    }
                )

                api_logger.info(
                    f"[Orchestrator] 后台分析任务已提交：{self.execution_id}, "
                    f"user_selected_models={user_selected_models}"
                )

            except ImportError as e:
                api_logger.warning(f"[Orchestrator] 后台任务管理器不可用：{e}")
            except Exception as e:
                api_logger.error(f"[Orchestrator] 提交后台分析任务失败：{e}")

            result_obj = PhaseResult(
                success=True,
                data={'submitted': True}
            )
            self.phase_results['background_analysis'] = result_obj

            api_logger.info(f"[Orchestrator] ✅ 阶段 5 启动：后台分析 - {self.execution_id}")
            return result_obj

        except Exception as e:
            api_logger.error(f"[Orchestrator] ❌ 阶段 5 失败：后台分析 - {self.execution_id}, 错误={e}")
            return PhaseResult(success=False, error=str(e))

    async def _phase_report_aggregating(
        self,
        results: List[Dict[str, Any]],
        brand_list: List[str]
    ) -> PhaseResult:
        """
        阶段 6: 报告聚合

        任务：
        1. 更新状态为报告聚合中
        2. 等待后台分析完成（或超时）
        3. 聚合所有结果为最终报告
        4. 保存最终报告
        5. 【P0 关键修复】标记任务为完成状态

        参数：
            results: AI 调用结果列表
            brand_list: 品牌列表

        返回：
            PhaseResult (包含最终报告)
        """
        api_logger.info(f"[Orchestrator] 阶段 6: 报告聚合 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.REPORT_AGGREGATING

        try:
            # 【P0 关键修复 - 2026-03-12】检查结果是否为空
            if not results or len(results) == 0:
                api_logger.error(
                    f"[Orchestrator] ❌ 报告聚合失败：{self.execution_id}, "
                    f"results 为空！这是前端看不到结果的根本原因"
                )
                # 尝试从 execution_store 恢复
                if self.execution_id in self.execution_store:
                    stored_results = self.execution_store[self.execution_id].get('results', [])
                    if stored_results:
                        api_logger.info(
                            f"[Orchestrator] 从 execution_store 恢复结果：{self.execution_id}, "
                            f"数量={len(stored_results)}"
                        )
                        results = stored_results
                    else:
                        api_logger.error(
                            f"[Orchestrator] ❌ execution_store 中也没有结果：{self.execution_id}"
                        )
                # 如果仍然为空，创建错误报告
                if not results or len(results) == 0:
                    return PhaseResult(
                        success=False,
                        error=f"报告聚合失败：results 为空，execution_id={self.execution_id}"
                    )

            # 更新状态为报告聚合中
            self._update_phase_status(
                status='report_aggregating',
                stage='report_aggregating',
                progress=90,
                write_to_db=True
            )

            # 【P1 关键修复 - 2026-03-07】等待后台分析完成
            # 超时时间增加到 360 秒（后台任务超时 300 秒 + 60 秒余量）
            analysis_results = {}
            analysis_completed = False
            analysis_error = None
            
            try:
                api_logger.info(f"[Orchestrator] 开始等待后台分析：{self.execution_id}, 超时=360 秒")
                analysis_results = await self._wait_for_analysis_complete(timeout_seconds=360)
                if analysis_results:
                    analysis_completed = True
                    api_logger.info(
                        f"[Orchestrator] ✅ 后台分析已完成：{self.execution_id}, "
                        f"总耗时={(datetime.now() - datetime.fromisoformat(self.execution_store[self.execution_id]['start_time'])).total_seconds():.2f}秒"
                    )
                else:
                    api_logger.warning(f"[Orchestrator] ⚠️ 后台分析超时，使用空结果继续：{self.execution_id}")
            except Exception as e:
                analysis_error = str(e)
                api_logger.warning(f"[Orchestrator] 等待后台分析失败：{e}，继续生成报告")
                analysis_results = {}

            # 聚合报告
            final_report = None
            report_quality_level = 'complete'
            missing_sections = []
            quality_warnings = []
            
            # 评估报告质量
            if not analysis_completed:
                report_quality_level = 'partial'
                missing_sections.append('brand_analysis')
                missing_sections.append('competitive_analysis')
                quality_warnings.append('后台分析超时，部分深度分析缺失')
            
            if not analysis_results:
                if report_quality_level == 'complete':
                    report_quality_level = 'partial'
                quality_warnings.append('后台分析结果为空')
            
            try:
                from wechat_backend.services.report_aggregator import aggregate_report

                params = self._initial_params
                final_report = aggregate_report(
                    raw_results=results,
                    brand_name=brand_list[0],
                    competitors=brand_list[1:] if len(brand_list) > 1 else [],
                    additional_data=analysis_results
                )

                api_logger.info(
                    f"[Orchestrator] ✅ 报告聚合完成：{self.execution_id}, "
                    f"overallScore={final_report.get('overallScore', 'N/A')}, "
                    f"quality={report_quality_level}"
                )

            except ImportError as e:
                api_logger.warning(f"[Orchestrator] 报告聚合服务不可用：{e}, 使用简化报告")
                report_quality_level = 'minimal'
                missing_sections.append('detailed_analysis')
                quality_warnings.append('使用简化报告生成器')
                # 降级处理：创建简化报告
                final_report = self._create_simplified_report(results, brand_list)
            except Exception as e:
                api_logger.error(f"[Orchestrator] 报告聚合失败：{e}", exc_info=True)
                report_quality_level = 'minimal'
                quality_warnings.append(f'报告聚合错误：{str(e)}')
                # 降级处理：创建简化报告
                final_report = self._create_simplified_report(results, brand_list)

            # 【P0 关键修复】确保 final_report 不为 None
            if final_report is None:
                api_logger.error(f"[Orchestrator] 报告聚合结果为 None，创建空报告")
                report_quality_level = 'minimal'
                final_report = self._create_simplified_report(results, brand_list)

            # 【P0 修复 - 2026-03-07】添加报告质量分级信息
            final_report['quality'] = {
                'level': report_quality_level,  # 'complete' | 'partial' | 'minimal'
                'completeness_score': 95 if report_quality_level == 'complete' else (60 if report_quality_level == 'partial' else 30),
                'missing_sections': missing_sections,
                'warnings': quality_warnings,
                'analysis_completed': analysis_completed,
                'analysis_error': analysis_error
            }

            # 【P3 修复 - 2026-03-07】保存分析数据到 diagnosis_analysis 表
            if analysis_results and hasattr(self, '_report_id') and self._report_id is not None:
                try:
                    from wechat_backend.services.diagnosis_transaction import DiagnosisTransaction
                    
                    tx = DiagnosisTransaction(self.execution_id)
                    tx._init_dependencies()  # 初始化依赖

                    # 保存品牌分析
                    if 'brand_analysis' in analysis_results:
                        analysis_id = tx.add_analysis(
                            report_id=self._report_id,
                            analysis_type='brand_analysis',
                            analysis_data=analysis_results['brand_analysis'],
                            execution_id=self.execution_id  # 【P2 修复 - 2026-03-11】传入 execution_id
                        )
                        api_logger.info(
                            f"[Orchestrator] ✅ 品牌分析已保存：{self.execution_id}, "
                            f"analysis_id={analysis_id}"
                        )

                    # 保存竞争分析
                    if 'competitive_analysis' in analysis_results:
                        analysis_id = tx.add_analysis(
                            report_id=self._report_id,
                            analysis_type='competitive_analysis',
                            analysis_data=analysis_results['competitive_analysis'],
                            execution_id=self.execution_id  # 【P2 修复 - 2026-03-11】传入 execution_id
                        )
                        api_logger.info(
                            f"[Orchestrator] ✅ 竞争分析已保存：{self.execution_id}, "
                            f"analysis_id={analysis_id}"
                        )

                    # 保存语义偏移分析
                    if 'semantic_drift' in analysis_results:
                        analysis_id = tx.add_analysis(
                            report_id=self._report_id,
                            analysis_type='semantic_drift',
                            analysis_data=analysis_results['semantic_drift'],
                            execution_id=self.execution_id  # 【P2 修复 - 2026-03-11】传入 execution_id
                        )
                        api_logger.info(
                            f"[Orchestrator] ✅ 语义偏移分析已保存：{self.execution_id}, "
                            f"analysis_id={analysis_id}"
                        )
                    
                    api_logger.info(
                        f"[Orchestrator] ✅ 分析数据已保存到 diagnosis_analysis 表：{self.execution_id}"
                    )
                    
                    # 【P3 修复 - 2026-03-07】创建报告快照
                    # 【P0 关键修复 - 2026-03-17】修复：使用 _report_repo 而非 _report_service
                    try:
                        snapshot_data = {
                            'final_report': final_report,
                            'analysis_results': analysis_results,
                            'report_quality': final_report.get('quality', {}),
                            'timestamp': datetime.now().isoformat()
                        }

                        # 确保依赖项已初始化
                        tx._init_dependencies()

                        snapshot_id = tx._report_repo.create_snapshot(
                            report_id=self._report_id,
                            execution_id=self.execution_id,
                            snapshot_data=snapshot_data,
                            reason='diagnosis_completed'
                        )

                        if snapshot_id > 0:
                            api_logger.info(
                                f"[Orchestrator] ✅ 报告快照已创建：{self.execution_id}, "
                                f"snapshot_id={snapshot_id}"
                            )
                        else:
                            api_logger.warning(
                                f"[Orchestrator] ⚠️ 报告快照创建失败：{self.execution_id}"
                            )

                    except Exception as snapshot_err:
                        api_logger.error(
                            f"[Orchestrator] ❌ 创建报告快照失败：{self.execution_id}, "
                            f"错误：{snapshot_err}",
                            exc_info=True
                        )
                        # 不阻塞主流程
                    
                except Exception as analysis_err:
                    api_logger.error(
                        f"[Orchestrator] ❌ 保存分析数据失败：{self.execution_id}, "
                        f"错误：{analysis_err}",
                        exc_info=True
                    )
                    # 不阻塞主流程，继续执行
            elif not analysis_results:
                api_logger.warning(
                    f"[Orchestrator] ⚠️ 跳过保存分析数据：{self.execution_id}, "
                    f"原因：analysis_results 为空"
                )
            elif not hasattr(self, '_report_id') or self._report_id is None:
                api_logger.warning(
                    f"[Orchestrator] ⚠️ 跳过保存分析数据：{self.execution_id}, "
                    f"原因：report_id 不存在"
                )

            # 保存最终报告到 execution_store
            if self.execution_id in self.execution_store:
                self.execution_store[self.execution_id]['final_report'] = final_report
                # 【P0 关键修复 - 2026-03-12 第 9 次】确保 detailed_results 始终有数据
                # 如果之前没有设置，使用 results 填充
                if not self.execution_store[self.execution_id].get('detailed_results'):
                    self.execution_store[self.execution_id]['detailed_results'] = results
                    api_logger.info(
                        f"[Orchestrator] ✅ execution_store.detailed_results 已填充：{self.execution_id}, "
                        f"数量={len(results) if results else 0}"
                    )
                # 【P0 关键修复】更新状态为 completed，而非 report_aggregating
                self.execution_store[self.execution_id]['status'] = 'completed'
                self.execution_store[self.execution_id]['progress'] = 100
                self.execution_store[self.execution_id]['is_completed'] = True
                self.execution_store[self.execution_id]['should_stop_polling'] = True

            # 【P0 关键修复】更新数据库状态为 completed
            try:
                self._update_phase_status(
                    status='completed',
                    stage='completed',
                    progress=100,
                    write_to_db=True,
                    is_completed=True,
                    should_stop_polling=True
                )
                api_logger.info(f"[Orchestrator] ✅ 数据库状态已更新为 completed: {self.execution_id}")
            except Exception as e:
                api_logger.error(f"[Orchestrator] 更新数据库状态失败：{e}")

            result_obj = PhaseResult(
                success=True,
                data=final_report
            )
            self.phase_results['report_aggregating'] = result_obj

            api_logger.info(f"[Orchestrator] ✅ 阶段 6 完成：报告聚合 - {self.execution_id}")
            return result_obj

        except Exception as e:
            api_logger.error(f"[Orchestrator] ❌ 阶段 6 失败：报告聚合 - {self.execution_id}, 错误={e}", exc_info=True)
            # 【P0 修复】失败时也要更新状态，防止卡死
            try:
                self._update_phase_status(
                    status='failed',
                    stage='failed',
                    progress=0,
                    write_to_db=True,
                    is_completed=True,
                    should_stop_polling=True,
                    error=str(e)
                )
            except Exception as update_err:
                api_logger.error(f"[Orchestrator] 更新失败状态失败：{update_err}")
            return PhaseResult(success=False, error=str(e))

    async def _wait_for_analysis_complete(
        self,
        timeout_seconds: int = 360  # 【P0 修复 - 2026-03-07】增加到 6 分钟，与后台任务超时 (300 秒) 匹配并留有余量
    ) -> Dict[str, Any]:
        """
        等待后台分析完成

        【P1 关键修复 - 2026-03-03】增加超时时间，优化轮询频率，确保分析完成
        【P0 关键修复 - 2026-03-05】异步非阻塞等待，防止线程阻塞
        【P0 关键修复 - 2026-03-07】统一超时时间为 360 秒（6 分钟）
        修改：
        1. 超时时间从 210 秒增加到 360 秒（后台任务超时 300 秒 + 60 秒余量）
        2. 轮询间隔从 2 秒改为 1 秒（更快响应）
        3. 添加详细日志，便于问题排查
        4. 【P0 修复】使用自适应轮询间隔，减少资源浪费
        5. 【P0 修复】异步非阻塞等待，释放线程处理其他任务

        参数：
            timeout_seconds: 超时时间（秒）

        返回：
            分析结果字典
        """
        start_time = datetime.now()
        base_interval = 1.0  # 基础轮询间隔（秒）
        consecutive_no_progress = 0
        last_status_hash = None

        api_logger.info(
            f"[Orchestrator] 开始等待后台分析：{self.execution_id}, "
            f"超时={timeout_seconds}秒，基础间隔={base_interval}秒"
        )

        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            try:
                from wechat_backend.services.background_service_manager import get_background_service_manager

                manager = get_background_service_manager()
                status = manager.get_task_status(self.execution_id)

                if status:
                    # 【P0 修复】计算状态哈希，检测进度变化
                    current_status_hash = hash(str(sorted(status.items())))
                    has_progress = (current_status_hash != last_status_hash)

                    if has_progress:
                        consecutive_no_progress = 0
                        last_status_hash = current_status_hash
                    else:
                        consecutive_no_progress += 1

                    # 记录等待进度
                    elapsed = (datetime.now() - start_time).total_seconds()
                    api_logger.debug(
                        f"[Orchestrator] 等待后台分析：{self.execution_id}, "
                        f"已等待={elapsed:.1f}秒，status={status}, "
                        f"无进度次数={consecutive_no_progress}"
                    )

                    if status.get('analysis_complete'):
                        api_logger.info(
                            f"[Orchestrator] ✅ 后台分析完成：{self.execution_id}, "
                            f"耗时={(datetime.now() - start_time).total_seconds():.2f}秒"
                        )
                        return status.get('analysis_results', {})
                    elif status.get('error'):
                        # 后台分析出错，提前退出
                        api_logger.warning(
                            f"[Orchestrator] ⚠️ 后台分析出错：{self.execution_id}, "
                            f"error={status.get('error')}"
                        )
                        return {}

            except Exception as e:
                api_logger.debug(f"[Orchestrator] 检查后台分析状态失败：{e}")

            # 【P0 修复】自适应轮询间隔：无进度时指数退避，最大 3 秒
            # 避免高频轮询浪费资源，同时保持快速响应
            backoff_multiplier = min(1.5 ** consecutive_no_progress, 3.0)
            adaptive_interval = min(base_interval * backoff_multiplier, 3.0)

            # 异步非阻塞等待，释放线程处理其他任务
            await asyncio.sleep(adaptive_interval)

        # 超时，返回空结果
        api_logger.warning(
            f"[Orchestrator] ⏰ 后台分析超时：{self.execution_id}, "
            f"超时={timeout_seconds}秒"
        )
        return {}

    def _create_simplified_report(
        self,
        results: List[Dict[str, Any]],
        brand_list: List[str]
    ) -> Dict[str, Any]:
        """
        创建简化报告（降级处理）

        参数：
            results: AI 调用结果列表
            brand_list: 品牌列表

        返回：
            简化报告字典
        """
        # 按品牌分组
        brand_results = {}
        for res in results:
            brand = res.get('brand', 'unknown')
            if brand not in brand_results:
                brand_results[brand] = []
            brand_results[brand].append(res)

        # 计算品牌分数
        brand_scores = {}
        for brand, brand_res in brand_results.items():
            total_score = sum(r.get('score', 50) for r in brand_res)
            avg_score = round(total_score / len(brand_res)) if brand_res else 50
            brand_scores[brand] = {
                'overallScore': avg_score,
                'resultCount': len(brand_res)
            }

        return {
            'brandName': brand_list[0],
            'competitors': brand_list[1:] if len(brand_list) > 1 else [],
            'brandScores': brand_scores,
            'resultCount': len(results),
            'timestamp': datetime.now().isoformat(),
            'isSimplified': True
        }

    async def _phase_complete(self, final_report: Dict[str, Any]) -> PhaseResult:
        """
        阶段 7: 完成

        任务：
        1. 统一更新状态为完成
        2. 【P0 修复】创建报告快照和分析数据
        3. 发送完成通知
        4. 清理临时状态

        参数：
            final_report: 最终报告数据

        返回：
            PhaseResult
        """
        api_logger.info(f"[Orchestrator] 阶段 7: 完成 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.COMPLETED

        try:
            params = self._initial_params

            # 【P0 修复 - 关键】创建报告快照和分析数据
            # 这是前端能获取完整报告数据的关键步骤
            try:
                from wechat_backend.diagnosis_report_service import get_report_service

                report_service = get_report_service()

                # 【P0 关键修复 - 2026-03-22】正确构建 full_report_data
                # final_report 是 aggregate_report 返回的扁平化数据，不是 {report, results, analysis} 格式
                # 需要从 results 变量和 final_report 正确构建
                full_report_data = {
                    'report': final_report,  # final_report 本身就是完整的报告数据
                    'results': results,  # 使用 results 变量（原始诊断结果列表）
                    'analysis': analysis_results  # 使用 analysis_results（后台分析结果）
                }
                
                # 创建快照和归档
                success = report_service.complete_report(
                    execution_id=self.execution_id,
                    full_report=full_report_data
                )
                
                if success:
                    api_logger.info(f"[Orchestrator] ✅ 报告快照已创建：{self.execution_id}")
                else:
                    api_logger.warning(f"[Orchestrator] ⚠️ 报告快照创建失败：{self.execution_id}")
                    
            except Exception as report_err:
                api_logger.error(f"[Orchestrator] ❌ 创建报告快照失败：{self.execution_id}, 错误：{report_err}", exc_info=True)
                # 快照失败不影响主流程，继续执行

            # 统一更新状态为完成
            if self._state_manager:
                self._state_manager.complete_execution(
                    execution_id=self.execution_id,
                    user_id=params['user_id'] or 'anonymous',
                    brand_name=params['brand_list'][0],
                    competitor_brands=params['brand_list'][1:] if len(params['brand_list']) > 1 else [],
                    selected_models=params['selected_models'],
                    custom_questions=params['custom_questions']
                )
                api_logger.info(f"[Orchestrator] 状态已更新为完成：{self.execution_id}")

            # 发送完成通知
            try:
                from wechat_backend.services.realtime_push_service import get_realtime_push_service

                push_service = get_realtime_push_service()
                await push_service.send_complete(
                    execution_id=self.execution_id,
                    result=final_report,
                    user_openid=params.get('user_openid', params['user_id'])
                )
                api_logger.info(f"[Orchestrator] 完成通知已发送：{self.execution_id}")

            except ImportError as e:
                api_logger.warning(f"[Orchestrator] 实时推送服务不可用：{e}")
            except Exception as e:
                api_logger.error(f"[Orchestrator] 发送完成通知失败：{e}")

            result_obj = PhaseResult(
                success=True,
                data=final_report
            )
            self.phase_results['completed'] = result_obj

            api_logger.info(f"[Orchestrator] ✅ 阶段 7 完成：诊断完成 - {self.execution_id}")
            return result_obj

        except Exception as e:
            api_logger.error(f"[Orchestrator] ❌ 阶段 7 失败：完成 - {self.execution_id}, 错误={e}")
            return PhaseResult(success=False, error=str(e))

    async def _phase_failed(
        self,
        error_message: str,
        error_code: Optional[DiagnosisErrorCode] = None
    ) -> PhaseResult:
        """
        阶段 8: 失败处理（使用事务回滚）

        任务：
        1. 统一更新状态为失败
        2. 发送错误通知
        3. 使用事务管理器回滚所有操作
        4. 清理中间状态
        5. 记录详细错误日志

        参数：
            error_message: 错误消息
            error_code: 错误码（可选）

        返回：
            PhaseResult
        """
        api_logger.info(f"[Orchestrator] 阶段 8: 失败处理 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.FAILED

        try:
            params = self._initial_params if hasattr(self, '_initial_params') else {}

            # 统一更新状态为失败
            if self._state_manager:
                self._state_manager.update_state(
                    execution_id=self.execution_id,
                    status='failed',
                    stage='failed',
                    progress=100,
                    is_completed=True,
                    should_stop_polling=True,
                    error_message=error_message,
                    write_to_db=True,
                    user_id=params.get('user_id', 'anonymous'),
                    brand_name=params.get('brand_list', [''])[0] if params.get('brand_list') else '',
                    competitor_brands=params.get('brand_list', [])[1:] if params.get('brand_list') and len(params.get('brand_list', [])) > 1 else [],
                    selected_models=params.get('selected_models', []),
                    custom_questions=params.get('custom_questions', [])
                )
                api_logger.info(f"[Orchestrator] 状态已更新为失败：{self.execution_id}")

            # 【阶段六：事务管理】使用 orchestrator 级别的事务管理器回滚
            # 注意：由于使用了 asynccontextmanager，异常会自动触发回滚
            if hasattr(self, '_current_transaction') and self._current_transaction is not None:
                api_logger.info(
                    f"[Orchestrator] 事务回滚将由事务上下文自动执行：{self.execution_id}"
                )
                # 不需要手动调用 rollback()，__exit__ 会自动处理
            else:
                # 降级处理：如果没有事务管理器，直接清理 execution_store
                api_logger.warning(
                    f"[Orchestrator] 无事务管理器，使用基础清理：{self.execution_id}"
                )
                if self.execution_id in self.execution_store:
                    self.execution_store.pop(self.execution_id, None)

            # 发送错误通知
            try:
                from wechat_backend.services.realtime_push_service import get_realtime_push_service

                push_service = get_realtime_push_service()
                await push_service.send_error(
                    execution_id=self.execution_id,
                    error=error_message,
                    error_type='diagnosis_failed',
                    user_openid=params.get('user_openid', params.get('user_id', 'anonymous')) if params else 'anonymous'
                )
                api_logger.info(f"[Orchestrator] 错误通知已发送：{self.execution_id}")

            except ImportError as e:
                api_logger.warning(f"[Orchestrator] 实时推送服务不可用：{e}")
            except Exception as e:
                api_logger.error(f"[Orchestrator] 发送错误通知失败：{e}")

            result_obj = PhaseResult(
                success=False,
                error=error_message
            )
            self.phase_results['failed'] = result_obj

            api_logger.error(f"[Orchestrator] ❌ 阶段 8 完成：失败处理 - {self.execution_id}, 错误={error_message}")
            return result_obj

        except Exception as e:
            api_logger.error(f"[Orchestrator] ❌ 阶段 8 失败：失败处理 - {self.execution_id}, 错误={e}")
            return PhaseResult(success=False, error=str(e))

    def get_phase_status(self) -> Dict[str, Any]:
        """
        获取所有阶段的状态

        返回：
            阶段状态字典
        """
        return {
            'execution_id': self.execution_id,
            'current_phase': self.current_phase.value,
            'phase_results': {
                phase: result.to_dict() if result else None
                for phase, result in self.phase_results.items()
            },
            'total_time': (datetime.now() - self.start_time).total_seconds()
        }

    def _determine_error_code(self, error_message: str) -> DiagnosisErrorCode:
        """
        根据错误消息确定错误码

        参数：
            error_message: 错误消息

        返回：
            DiagnosisErrorCode: 错误码枚举值
        """
        error_lower = error_message.lower()
        
        # 超时错误
        if 'timeout' in error_lower or '超时' in error_lower:
            return DiagnosisErrorCode.DIAGNOSIS_TIMEOUT
        
        # 验证错误
        if 'validation' in error_lower or '验证' in error_lower:
            if 'count' in error_lower or '数量' in error_lower:
                return DiagnosisErrorCode.DIAGNOSIS_RESULT_COUNT_MISMATCH
            return DiagnosisErrorCode.DIAGNOSIS_RESULT_INVALID
        
        # 保存错误
        if 'save' in error_lower or '保存' in error_lower:
            return DiagnosisErrorCode.DIAGNOSIS_SAVE_FAILED
        
        # 初始化错误
        if 'init' in error_lower or '初始化' in error_lower:
            return DiagnosisErrorCode.DIAGNOSIS_INIT_FAILED
        
        # AI 调用错误
        if 'ai' in error_lower or 'ai ' in error_lower:
            return DiagnosisErrorCode.DIAGNOSIS_EXECUTION_FAILED
        
        # 报告错误
        if 'report' in error_lower or '报告' in error_lower:
            return DiagnosisErrorCode.DIAGNOSIS_REPORT_AGGREGATION_FAILED
        
        # 分析错误
        if 'analysis' in error_lower or '分析' in error_lower:
            return DiagnosisErrorCode.DIAGNOSIS_ANALYSIS_FAILED
        
        # 默认为执行失败
        return DiagnosisErrorCode.DIAGNOSIS_EXECUTION_FAILED

    def _schedule_cleanup(self, delay_seconds: int = 300):
        """
        调度清理任务（简化版 - 仅记录日志）

        【P0 关键修复 - 2026-03-08】
        清理逻辑已统一由 StateManager 负责，此方法仅记录日志
        
        优化原因：
        1. 避免双重清理机制导致的资源浪费
        2. StateManager 已有完善的定时清理和紧急清理机制
        3. 统一清理逻辑，便于监控和维护

        参数：
            delay_seconds: 延迟清理时间（秒），默认 300 秒（参数已废弃）
        """
        # 【P0 优化 - 2026-03-08】不再启动独立清理线程
        # 清理工作由 StateManager 统一负责（每 3 分钟自动清理已完成任务）
        
        api_logger.info(
            f"[Orchestrator] ⏰ 任务完成，将由 StateManager 统一清理：{self.execution_id}, "
            f"TTL=300s, 清理间隔=180s"
        )


# 全局编排器工厂函数
def create_orchestrator(
    execution_id: str,
    execution_store: Dict[str, Any]
) -> DiagnosisOrchestrator:
    """
    创建编排器实例

    参数：
        execution_id: 执行 ID
        execution_store: 执行状态存储

    返回：
        DiagnosisOrchestrator 实例
    """
    return DiagnosisOrchestrator(execution_id, execution_store)


__all__ = [
    'DiagnosisOrchestrator',
    'DiagnosisPhase',
    'PhaseResult',
    'create_orchestrator'
]
