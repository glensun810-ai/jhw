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
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
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
from wechat_backend.error_logger import get_error_logger, log_diagnosis_errors
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

        严格顺序:
        1. 初始化阶段
        2. AI 调用阶段 (并行)
        3. 结果保存阶段
        4. 结果验证阶段
        5. 后台分析阶段 (异步)
        6. 报告聚合阶段
        7. 完成阶段

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

        # 【阶段六：事务管理】使用事务上下文管理器包裹整个诊断流程
        # 这样任何阶段失败都会自动回滚所有数据库操作
        async with self._transaction_context():
            try:
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

                # ========== 阶段 1: 初始化 ==========
                phase1_result = await self._phase_init()
                if not phase1_result.success:
                    raise ValueError(f"初始化失败：{phase1_result.error}")

                # ========== 阶段 2: AI 调用 ==========
                phase2_result = await self._phase_ai_fetching(
                    brand_list, selected_models, custom_questions, user_id, user_level
                )
                if not phase2_result.success:
                    raise ValueError(f"AI 调用失败：{phase2_result.error}")

                # ========== 阶段 3: 结果保存 ==========
                phase3_result = await self._phase_results_saving(
                    phase2_result.data, brand_list, selected_models, custom_questions
                )
                if not phase3_result.success:
                    raise ValueError(f"结果保存失败：{phase3_result.error}")

                # 【P0 关键修复 - 2026-03-02】等待数据库提交完成
                # SQLite WAL 模式下，COMMIT 后数据可能还在 WAL 文件中，需要短暂等待
                # 确保步骤 5 保存的数据在步骤 6 验证时可见
                await asyncio.sleep(0.1)  # 等待 100ms，确保数据持久化

                # ========== 阶段 4: 结果验证 ==========
                # 【P0 关键修复 - 2026-03-03】传递内存数据用于验证，但返回数据库数据供后续使用
                phase4_result = await self._phase_results_validating(phase2_result.data)
                if not phase4_result.success:
                    raise ValueError(f"结果验证失败：{phase4_result.error}")
                
                # 【P0 关键修复 - 2026-03-03】从验证结果中获取数据库中的实际数据
                db_results = phase4_result.data.get('saved_results', [])
                api_logger.info(
                    f"[Orchestrator] 验证完成：{self.execution_id}, "
                    f"数据库结果数={len(db_results)}"
                )

                # ========== 阶段 5: 后台分析 (异步，不阻塞) ==========
                # 【P0 关键修复 - 2026-03-03】使用数据库数据而非内存数据
                phase5_result = self._phase_background_analysis_async(
                    db_results, brand_list
                )
                # 注意：此阶段异步执行，不等待完成

                # ========== 阶段 6: 报告聚合 ==========
                # 【P0 关键修复 - 2026-03-03】使用数据库数据而非内存数据
                phase6_result = await self._phase_report_aggregating(
                    db_results, brand_list
                )
                if not phase6_result.success:
                    raise ValueError(f"报告聚合失败：{phase6_result.error}")

                # ========== 阶段 7: 完成 ==========
                phase7_result = await self._phase_complete(phase6_result.data)
                if not phase7_result.success:
                    raise ValueError(f"完成处理失败：{phase7_result.error}")

                # 所有阶段成功完成
                total_time = (datetime.now() - self.start_time).total_seconds()
                api_logger.info(
                    f"[Orchestrator] ✅ 诊断执行完成：{self.execution_id}, "
                    f"总耗时={total_time:.2f}秒，TraceID={trace_id}"
                )

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
                return {
                    'success': False,
                    'execution_id': self.execution_id,
                    'error': str(e),
                    'error_code': error_code.value.code if hasattr(error_code, 'value') else error_code.code,
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

        任务：
        1. 更新状态为 AI 调用中
        2. 执行并行 AI 调用（带重试机制）
        3. 收集所有结果

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
            # 更新状态为 AI 调用中
            self._update_phase_status(
                status='ai_fetching',
                stage='ai_fetching',
                progress=30,
                write_to_db=True
            )

            # 【阶段七：错误处理】使用重试机制执行 AI 调用
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
            
            # 执行带重试的 AI 调用
            retry_result = await ai_retry_handler.execute_with_retry_async(
                _execute_ai_call,
                execution_id=self.execution_id
            )
            
            if not retry_result.success:
                # 重试失败，记录错误
                self._error_logger.log_error(
                    error=retry_result.error,
                    error_code=AIPlatformErrorCode.AI_PLATFORM_UNAVAILABLE.value,
                    execution_id=self.execution_id,
                    user_id=user_id,
                    additional_info={
                        'attempts': len(retry_result.attempts),
                        'total_time': retry_result.total_time,
                    }
                )
                return PhaseResult(
                    success=False,
                    error=f"AI 调用失败（已重试{len(retry_result.attempts)}次）: {str(retry_result.error)}"
                )
            
            result = retry_result.result

            # 检查执行结果
            if not result.get('success'):
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

            # 【P0 修复 - 2026-03-04】检查 AI 调用结果是否为空
            if not ai_results or len(ai_results) == 0:
                error_msg = f"AI 调用返回空结果：{self.execution_id}"
                api_logger.error(f"[Orchestrator] ❌ {error_msg}")
                self._error_logger.log_error(
                    error=Exception(error_msg),
                    error_code=AIPlatformErrorCode.AI_PLATFORM_UNAVAILABLE.value,
                    execution_id=self.execution_id,
                    user_id=user_id,
                    additional_info={
                        'ai_response': result,
                        'retry_attempts': len(retry_result.attempts),
                    }
                )
                return PhaseResult(
                    success=False,
                    error=error_msg
                )

            # 更新 execution_store
            if self.execution_id in self.execution_store:
                self.execution_store[self.execution_id]['results'] = ai_results
                self.execution_store[self.execution_id]['status'] = 'ai_fetching'
                self.execution_store[self.execution_id]['progress'] = 30

            result_obj = PhaseResult(
                success=True,
                data=ai_results
            )
            self.phase_results['ai_fetching'] = result_obj

            api_logger.info(f"[Orchestrator] ✅ 阶段 2 完成：AI 调用 - {self.execution_id}")
            return result_obj

        except Exception as e:
            # 【阶段七：错误处理】记录详细错误日志
            self._error_logger.log_error(
                error=e,
                error_code=AIPlatformErrorCode.AI_PLATFORM_UNAVAILABLE.value,
                execution_id=self.execution_id,
                user_id=user_id,
            )
            api_logger.error(f"[Orchestrator] ❌ 阶段 2 失败：AI 调用 - {self.execution_id}, 错误={e}")
            return PhaseResult(success=False, error=str(e))

    async def _phase_results_saving(
        self,
        results: List[Dict[str, Any]],
        brand_list: List[str],
        selected_models: List[Dict],
        custom_questions: List[str]
    ) -> PhaseResult:
        """
        阶段 3: 结果保存（使用事务管理）

        任务：
        1. 更新状态为结果保存中
        2. 使用父级事务创建报告记录
        3. 批量保存结果到数据库（事务操作）
        4. 如果任何步骤失败，自动回滚所有操作

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

            # 【阶段六：事务管理】使用父级事务上下文中的事务管理器
            # 注意：不再创建嵌套事务，而是使用 orchestrator 级别的事务
            if not hasattr(self, '_current_transaction') or self._current_transaction is None:
                api_logger.error(
                    f"[Orchestrator] 事务管理器未初始化，无法保存结果：{self.execution_id}"
                )
                return PhaseResult(
                    success=False,
                    error='事务管理器未初始化'
                )

            tx = self._current_transaction

            # 创建报告记录（事务操作）
            report_id = tx.create_report(
                user_id=params['user_id'] or 'anonymous',
                config=config
            )

            api_logger.info(
                f"[Orchestrator] 报告创建成功：{self.execution_id}, "
                f"report_id={report_id}"
            )

            # 批量保存结果（事务操作）
            if results:
                result_ids = tx.add_results_batch(
                    report_id=report_id,
                    results=results
                )
                api_logger.info(
                    f"[Orchestrator] 结果保存成功：{self.execution_id}, "
                    f"数量={len(result_ids)}"
                )
            else:
                api_logger.warning(f"[Orchestrator] 无结果可保存：{self.execution_id}")

            # 存储 report_id 供后续阶段使用
            self._report_id = report_id

            # 记录事务摘要
            tx_summary = tx.get_summary()
            api_logger.info(
                f"[Orchestrator] 事务摘要：{self.execution_id}, "
                f"操作数={tx_summary['operation_count']}, "
                f"状态={tx_summary['status']}"
            )

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
        results: List[Dict[str, Any]]
    ) -> PhaseResult:
        """
        阶段 4: 结果验证（使用 ResultValidator 服务）

        任务：
        1. 更新状态为结果验证中
        2. 使用 ResultValidator 进行数量验证
        3. 使用 ResultValidator 进行质量验证
        4. 使用 ResultValidator 进行完整性验证
        5. 【P0 关键修复 - 2026-03-03】返回数据库中的实际数据供后续环节使用

        参数：
            results: AI 调用结果列表（用于数量对比）

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
            result_data = validation_result.to_dict()
            result_data['saved_results'] = saved_results  # 添加数据库数据供后续环节使用
            
            result_obj = PhaseResult(
                success=True,
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
        2. 提交品牌分析任务到后台队列
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

                # 品牌分析任务
                manager.submit_analysis_task(
                    execution_id=self.execution_id,
                    task_type='brand_analysis',
                    payload={
                        'results': results,
                        'user_brand': brand_list[0],
                        'competitor_brands': brand_list[1:] if len(brand_list) > 1 else []
                    }
                )

                # 竞争分析任务
                manager.submit_analysis_task(
                    execution_id=self.execution_id,
                    task_type='competitive_analysis',
                    payload={
                        'results': results,
                        'main_brand': brand_list[0],
                        'competitor_brands': brand_list[1:] if len(brand_list) > 1 else []
                    }
                )

                api_logger.info(
                    f"[Orchestrator] 后台分析任务已提交：{self.execution_id}"
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
            # 更新状态为报告聚合中
            self._update_phase_status(
                status='report_aggregating',
                stage='report_aggregating',
                progress=90,
                write_to_db=True
            )

            # 【P1 关键修复 - 2026-03-03】等待后台分析完成（最多等待 120 秒）
            # 注意：后台分析是异步的，但需要确保分析完成才能生成完整报告
            # 修改：超时时间从 60 秒增加到 120 秒
            analysis_results = {}
            try:
                api_logger.info(f"[Orchestrator] 开始等待后台分析：{self.execution_id}")
                analysis_results = await self._wait_for_analysis_complete(timeout_seconds=120)
                if analysis_results:
                    api_logger.info(
                        f"[Orchestrator] ✅ 后台分析已完成：{self.execution_id}, "
                        f"总耗时={(datetime.now() - datetime.fromisoformat(self.execution_store[self.execution_id]['start_time'])).total_seconds():.2f}秒"
                    )
                else:
                    api_logger.warning(f"[Orchestrator] ⚠️ 后台分析超时，使用空结果继续：{self.execution_id}")
            except Exception as e:
                api_logger.warning(f"[Orchestrator] 等待后台分析失败：{e}，继续生成报告")
                analysis_results = {}

            # 聚合报告
            # 【阶段一：报告聚合器】使用 Python 版本的报告聚合器
            final_report = None
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
                    f"overallScore={final_report.get('overallScore', 'N/A')}"
                )

            except ImportError as e:
                api_logger.warning(f"[Orchestrator] 报告聚合服务不可用：{e}, 使用简化报告")
                # 降级处理：创建简化报告
                final_report = self._create_simplified_report(results, brand_list)
            except Exception as e:
                api_logger.error(f"[Orchestrator] 报告聚合失败：{e}", exc_info=True)
                # 降级处理：创建简化报告
                final_report = self._create_simplified_report(results, brand_list)

            # 【P0 关键修复】确保 final_report 不为 None
            if final_report is None:
                api_logger.error(f"[Orchestrator] 报告聚合结果为 None，创建空报告")
                final_report = self._create_simplified_report(results, brand_list)

            # 保存最终报告到 execution_store
            if self.execution_id in self.execution_store:
                self.execution_store[self.execution_id]['final_report'] = final_report
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
        timeout_seconds: int = 120
    ) -> Dict[str, Any]:
        """
        等待后台分析完成

        【P1 关键修复 - 2026-03-03】增加超时时间，优化轮询频率，确保分析完成
        修改：
        1. 超时时间从 60 秒增加到 120 秒
        2. 轮询间隔从 2 秒改为 1 秒（更快响应）
        3. 添加详细日志，便于问题排查

        参数：
            timeout_seconds: 超时时间（秒）

        返回：
            分析结果字典
        """
        start_time = datetime.now()
        check_interval = 1  # 【P1 修复】轮询间隔从 2 秒改为 1 秒
        api_logger.info(
            f"[Orchestrator] 开始等待后台分析：{self.execution_id}, "
            f"超时={timeout_seconds}秒，轮询间隔={check_interval}秒"
        )

        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            try:
                from wechat_backend.services.background_service_manager import get_background_service_manager

                manager = get_background_service_manager()
                status = manager.get_task_status(self.execution_id)

                if status:
                    # 记录等待进度
                    elapsed = (datetime.now() - start_time).total_seconds()
                    api_logger.debug(
                        f"[Orchestrator] 等待后台分析：{self.execution_id}, "
                        f"已等待={elapsed:.1f}秒，status={status}"
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

            # 轮询等待
            await asyncio.sleep(check_interval)

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
        2. 发送完成通知
        3. 清理临时状态

        参数：
            final_report: 最终报告数据

        返回：
            PhaseResult
        """
        api_logger.info(f"[Orchestrator] 阶段 7: 完成 - {self.execution_id}")
        self.current_phase = DiagnosisPhase.COMPLETED

        try:
            params = self._initial_params

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
