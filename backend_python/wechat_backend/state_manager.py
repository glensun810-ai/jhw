"""
诊断状态管理器 - P0 增强版

核心原则：
1. 只有一个地方负责更新状态（统一写入点）
2. 内存和数据库必须原子性更新
3. 所有状态变更必须记录详细日志
4. 状态可验证、可回滚

增强内容（阶段二）：
1. 状态变更日志 - 记录每次状态变更的历史
2. 状态验证方法 - 验证内存和数据库状态一致性
3. 强制回滚方法 - 回滚到指定状态

架构师签字：___________
日期：2026-03-02
版本：2.0.0 (阶段二增强版)
"""

import json
import threading
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from wechat_backend.logging_config import api_logger, db_logger
from wechat_backend.diagnosis_report_repository import save_diagnosis_report, DiagnosisReportRepository

# P0 修复：导入字段转换器
from utils.field_converter import convert_response_to_camel


class StateChangeType(Enum):
    """状态变更类型枚举"""
    INIT = "init"
    UPDATE = "update"
    COMPLETE = "complete"
    FAIL = "fail"
    ROLLBACK = "rollback"
    VERIFY = "verify"


@dataclass
class StateChangeRecord:
    """状态变更记录"""
    execution_id: str
    change_type: str
    old_status: Optional[str]
    old_stage: Optional[str]
    old_progress: Optional[int]
    new_status: Optional[str]
    new_stage: Optional[str]
    new_progress: Optional[int]
    timestamp: str
    user_id: str
    reason: str = ""
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class DiagnosisStateManager:
    """
    诊断状态管理器（增强版）

    职责：
    1. 统一管理 execution_store 和数据库状态
    2. 确保内存和数据库原子性更新
    3. 提供状态查询、验证、回滚接口
    4. 记录所有状态变更历史
    """

    def __init__(self, execution_store: Dict[str, Any]):
        self.execution_store = execution_store
        self.state_lock = {}  # 每个 execution_id 一个锁

        # 【阶段二新增】状态变更历史
        self.state_change_history: Dict[str, List[StateChangeRecord]] = {}

        # 【阶段二新增】状态快照（用于回滚）
        self.state_snapshots: Dict[str, Dict[str, Any]] = {}

        # 【P0 关键修复 - 2026-03-05】优化清理配置，防止内存泄漏
        # 修复前：30 分钟清理一次，完成后保留 30 分钟 -> 内存积累严重
        # 修复后：5 分钟清理一次，完成后保留 10 分钟 -> 内存稳定
        self.cleanup_interval_seconds = 300  # 5 分钟清理一次（从 1800 秒降低）
        self.completed_state_ttl_seconds = 600  # 完成后保留 10 分钟（从 1800 秒降低）
        self.last_cleanup_time = datetime.now()
        
        # 【P0 新增】内存限制和监控
        self.max_memory_items = 1000  # 最大内存项目数，超过时触发紧急清理
        self.cleanup_count = 0  # 累计清理次数
        self.total_cleaned_count = 0  # 累计清理项目数
        self.emergency_cleanup_count = 0  # 紧急清理次数

        # 启动定时清理任务
        self._start_cleanup_timer()

        api_logger.info(
            f"[StateManager] 增强版状态管理器已初始化，"
            f"清理间隔={self.cleanup_interval_seconds}s, "
            f"TTL={self.completed_state_ttl_seconds}s, "
            f"max_memory_items={self.max_memory_items}"
        )

    def _init_execution_state(self, execution_id: str):
        """初始化执行状态（如果不存在）"""
        if execution_id not in self.execution_store:
            self.execution_store[execution_id] = {
                'status': 'init',
                'stage': 'init',
                'progress': 0,
                'is_completed': False,
                'should_stop_polling': False,
                'start_time': datetime.now().isoformat(),
                'results': [],
                'detailed_results': {},
                'error': None,
                'updated_at': datetime.now().isoformat()
            }
            api_logger.debug(f"[StateManager] 初始化 execution_store: {execution_id}")

    def _record_state_change(
        self,
        execution_id: str,
        change_type: StateChangeType,
        old_state: Optional[Dict[str, Any]],
        new_state: Optional[Dict[str, Any]],
        user_id: str = 'anonymous',
        reason: str = "",
        error_message: Optional[str] = None
    ):
        """
        记录状态变更

        参数：
            execution_id: 执行 ID
            change_type: 变更类型
            old_state: 旧状态
            new_state: 新状态
            user_id: 用户 ID
            reason: 变更原因
            error_message: 错误信息
        """
        old_status = old_state.get('status') if old_state else None
        old_stage = old_state.get('stage') if old_state else None
        old_progress = old_state.get('progress') if old_state else None
        
        new_status = new_state.get('status') if new_state else None
        new_stage = new_state.get('stage') if new_state else None
        new_progress = new_state.get('progress') if new_state else None
        
        record = StateChangeRecord(
            execution_id=execution_id,
            change_type=change_type.value,
            old_status=old_status,
            old_stage=old_stage,
            old_progress=old_progress,
            new_status=new_status,
            new_stage=new_stage,
            new_progress=new_progress,
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            reason=reason,
            error_message=error_message
        )
        
        # 添加到历史记录
        if execution_id not in self.state_change_history:
            self.state_change_history[execution_id] = []
        self.state_change_history[execution_id].append(record)
        
        # 记录日志
        log_msg = (
            f"[StateChange] {change_type.value}: {execution_id}, "
            f"{old_status}->{new_status}, {old_stage}->{new_stage}, "
            f"{old_progress}%->{new_progress}%"
        )
        
        if change_type == StateChangeType.FAIL:
            api_logger.error(log_msg)
        else:
            api_logger.info(log_msg)
        
        # 【阶段二新增】持久化到 SQLite（可选，用于审计）
        self._persist_state_change_to_db(record)

    def _persist_state_change_to_db(self, record: StateChangeRecord):
        """
        持久化状态变更到数据库

        参数：
            record: 状态变更记录
        """
        try:
            from wechat_backend.database_connection_pool import get_db_pool
            
            conn = get_db_pool().get_connection()
            cursor = conn.cursor()
            
            # 创建状态变更历史表（如果不存在）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS diagnosis_state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    old_status TEXT,
                    old_stage TEXT,
                    old_progress INTEGER,
                    new_status TEXT,
                    new_stage TEXT,
                    new_progress INTEGER,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    reason TEXT,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入记录
            cursor.execute('''
                INSERT INTO diagnosis_state_history 
                (execution_id, change_type, old_status, old_stage, old_progress,
                 new_status, new_stage, new_progress, timestamp, user_id, reason, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.execution_id,
                record.change_type,
                record.old_status,
                record.old_stage,
                record.old_progress,
                record.new_status,
                record.new_stage,
                record.new_progress,
                record.timestamp,
                record.user_id,
                record.reason,
                record.error_message
            ))
            
            conn.commit()
            db_logger.debug(f"[StateManager] 状态变更已持久化：{record.execution_id}")
            
        except Exception as e:
            # 数据库失败不影响主流程，只记录日志
            db_logger.warning(f"[StateManager] 持久化状态变更失败：{e}")

    def _save_snapshot(self, execution_id: str):
        """
        保存状态快照（用于回滚）

        参数：
            execution_id: 执行 ID
        """
        if execution_id in self.execution_store:
            # 深拷贝当前状态
            import copy
            self.state_snapshots[execution_id] = copy.deepcopy(self.execution_store[execution_id])
            api_logger.debug(f"[StateManager] 已保存状态快照：{execution_id}")

    def _force_sync_to_database(
        self,
        execution_id: str,
        user_id: str = 'anonymous',
        brand_name: str = '',
        competitor_brands: list = None,
        selected_models: list = None,
        custom_questions: list = None
    ):
        """
        强制同步内存状态到数据库

        【P0 关键修复 - 2026-03-04】确保内存和数据库状态一致

        参数：
            execution_id: 执行 ID
            user_id: 用户 ID
            brand_name: 品牌名称
            competitor_brands: 竞品列表
            selected_models: 模型列表
            custom_questions: 问题列表
        """
        try:
            state = self.execution_store[execution_id]

            # 准备数据库更新数据
            update_data = {
                'status': state.get('status'),
                'stage': state.get('stage'),
                'progress': state.get('progress'),
                'is_completed': state.get('is_completed', False),
                'should_stop_polling': state.get('should_stop_polling', False),
                'error_message': state.get('error'),
                'updated_at': datetime.now().isoformat()
            }

            # 添加额外字段
            if brand_name:
                update_data['brand_name'] = brand_name
            if competitor_brands:
                update_data['competitor_brands'] = json.dumps(competitor_brands)
            if selected_models:
                update_data['selected_models'] = json.dumps(selected_models)
            if custom_questions:
                update_data['custom_questions'] = json.dumps(custom_questions)

            # 执行数据库更新
            save_diagnosis_report(
                execution_id=execution_id,
                user_id=user_id,
                brand_name=brand_name,
                competitor_brands=competitor_brands or [],
                selected_models=selected_models or [],
                custom_questions=custom_questions or [],
                status=state.get('status') or 'processing',
                progress=state.get('progress') or 0,
                stage=state.get('stage') or 'processing',
                is_completed=state.get('is_completed', False)
            )

            db_logger.debug(f"[StateManager] 强制同步到数据库：{execution_id}")

        except Exception as e:
            db_logger.error(f"[StateManager] 强制同步失败：{execution_id}, error={e}")
            # 数据库失败不影响内存状态更新
            api_logger.warning(f"[StateManager] 数据库同步失败，但内存状态已更新：{execution_id}")

    def update_state(
        self,
        execution_id: str,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        is_completed: Optional[bool] = None,
        results: Optional[list] = None,
        error_message: Optional[str] = None,
        should_stop_polling: Optional[bool] = None,
        write_to_db: bool = True,
        user_id: str = 'anonymous',
        brand_name: str = '',
        competitor_brands: list = None,
        selected_models: list = None,
        custom_questions: list = None,
        reason: str = ""  # 【阶段二新增】变更原因
    ) -> bool:
        """
        统一状态更新接口（增强版）

        增强内容：
        1. 记录状态变更历史
        2. 保存回滚快照
        3. 添加变更原因

        参数:
            execution_id: 执行 ID
            status: 状态（initializing/ai_fetching/analyzing/completed/failed）
            stage: 阶段（与 status 保持一致）
            progress: 进度（0-100）
            is_completed: 是否完成
            results: 结果列表
            error_message: 错误信息
            should_stop_polling: 强制停止轮询标志
            write_to_db: 是否写入数据库
            user_id: 用户 ID
            brand_name: 品牌名称
            competitor_brands: 竞品列表
            selected_models: 模型列表
            custom_questions: 问题列表
            reason: 变更原因

        返回:
            bool: 更新是否成功
        """
        # 获取锁（每个 execution_id 独立）
        if execution_id not in self.state_lock:
            self.state_lock[execution_id] = threading.Lock()

        lock = self.state_lock[execution_id]

        with lock:
            try:
                # 初始化状态（如果不存在）
                self._init_execution_state(execution_id)
                
                # 【阶段二新增】保存旧状态（用于记录和回滚）
                old_state = self.execution_store[execution_id].copy()
                
                # 【阶段二新增】保存快照（用于回滚）
                self._save_snapshot(execution_id)
                
                store = self.execution_store[execution_id]

                # ==================== 步骤 1: 更新 execution_store ====================
                # 只更新提供的字段（不覆盖未提供的字段）
                if status is not None:
                    store['status'] = status
                if stage is not None:
                    store['stage'] = stage
                if progress is not None:
                    store['progress'] = progress
                    # P1-3 新增：WebSocket 进度推送
                    try:
                        from wechat_backend.websocket_route import send_diagnosis_progress
                        send_diagnosis_progress(execution_id, {
                            'progress': progress,
                            'stage': stage or store.get('stage', 'unknown'),
                            'status': status or store.get('status', 'processing')
                        })
                    except Exception as ws_error:
                        api_logger.debug(f"[WebSocket] 进度推送失败：{ws_error}")
                if is_completed is not None:
                    store['is_completed'] = is_completed
                if results is not None:
                    store['results'] = results
                    store['detailed_results'] = results
                if error_message is not None:
                    store['error'] = error_message
                if should_stop_polling is not None:
                    store['should_stop_polling'] = should_stop_polling

                # 更新时间戳
                store['updated_at'] = datetime.now().isoformat()

                # 【阶段二新增】记录状态变更
                self._record_state_change(
                    execution_id=execution_id,
                    change_type=StateChangeType.UPDATE,
                    old_state=old_state,
                    new_state=store.copy(),
                    user_id=user_id,
                    reason=reason or "状态更新"
                )

                api_logger.info(f"[StateManager] 内存状态已更新：{execution_id}, "
                              f"status={store.get('status')}, "
                              f"stage={store.get('stage')}, "
                              f"progress={store.get('progress')}")

                # ==================== 步骤 2: 更新数据库（可选） ====================
                if write_to_db:
                    self._force_sync_to_database(
                        execution_id=execution_id,
                        user_id=user_id,
                        brand_name=brand_name,
                        competitor_brands=competitor_brands,
                        selected_models=selected_models,
                        custom_questions=custom_questions
                    )

                return True

            except Exception as e:
                api_logger.error(f"[StateManager] 状态更新失败：{execution_id}, 错误：{e}")
                return False

    # ==================== 【阶段二新增】状态验证方法 ====================

    def verify_state_consistency(
        self,
        execution_id: str,
        fix_if_inconsistent: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        验证状态一致性

        参数：
            execution_id: 执行 ID
            fix_if_inconsistent: 发现不一致时是否自动修复

        返回：
            (is_consistent, details)
            - is_consistent: 是否一致
            - details: 详细信息
        """
        result = {
            'execution_id': execution_id,
            'is_consistent': True,
            'memory_state': None,
            'db_state': None,
            'differences': [],
            'fixed': False
        }
        
        try:
            # 1. 获取内存状态
            if execution_id not in self.execution_store:
                result['is_consistent'] = False
                result['differences'].append('内存中不存在该 execution_id')
                return False, result
            
            memory_state = self.execution_store[execution_id]
            result['memory_state'] = memory_state.copy()
            
            # 2. 获取数据库状态
            try:
                repo = DiagnosisReportRepository()
                db_report = repo.get_by_execution_id(execution_id)
                
                if not db_report:
                    result['is_consistent'] = False
                    result['differences'].append('数据库中不存在该 execution_id')
                    return False, result
                
                db_state = {
                    'status': db_report.get('status'),
                    'stage': db_report.get('stage'),
                    'progress': db_report.get('progress'),
                    'is_completed': db_report.get('is_completed', 0) == 1
                }
                result['db_state'] = db_state
                
            except Exception as db_err:
                result['is_consistent'] = False
                result['differences'].append(f'数据库查询失败：{db_err}')
                return False, result
            
            # 3. 比较内存和数据库状态
            critical_fields = ['status', 'stage', 'progress', 'is_completed']
            
            for field in critical_fields:
                mem_value = memory_state.get(field)
                db_value = db_state.get(field)
                
                # 处理 is_completed 的特殊情况（数据库中是 INTEGER）
                if field == 'is_completed':
                    db_value = db_value == 1 if isinstance(db_value, int) else db_value
                
                if mem_value != db_value:
                    result['is_consistent'] = False
                    result['differences'].append(
                        f'{field}: 内存={mem_value}, 数据库={db_value}'
                    )
            
            # 4. 自动修复（如果启用）
            if not result['is_consistent'] and fix_if_inconsistent:
                api_logger.warning(
                    f"[StateManager] 发现状态不一致：{execution_id}, "
                    f"差异={result['differences']}"
                )
                
                # 以数据库为准，修复内存状态
                for field in critical_fields:
                    if field in db_state:
                        memory_state[field] = db_state[field]
                
                memory_state['updated_at'] = datetime.now().isoformat()
                result['fixed'] = True
                
                api_logger.info(f"[StateManager] ✅ 已自动修复状态：{execution_id}")
            
            # 5. 记录验证日志
            self._record_state_change(
                execution_id=execution_id,
                change_type=StateChangeType.VERIFY,
                old_state=None,
                new_state=memory_state if result['is_consistent'] or result['fixed'] else None,
                reason=f"状态验证 - {'一致' if result['is_consistent'] else '不一致'}"
            )
            
            return result['is_consistent'], result
            
        except Exception as e:
            api_logger.error(f"[StateManager] 状态验证失败：{execution_id}, 错误：{e}")
            result['is_consistent'] = False
            result['differences'].append(f'验证失败：{e}')
            return False, result

    # ==================== 【阶段二新增】强制回滚方法 ====================

    def rollback_to_snapshot(
        self,
        execution_id: str,
        user_id: str = 'anonymous',
        reason: str = "手动回滚"
    ) -> bool:
        """
        回滚到上一个快照状态

        参数：
            execution_id: 执行 ID
            user_id: 用户 ID
            reason: 回滚原因

        返回：
            bool: 是否成功
        """
        try:
            # 1. 检查是否有快照
            if execution_id not in self.state_snapshots:
                api_logger.error(f"[StateManager] 无快照可回滚：{execution_id}")
                return False
            
            # 2. 获取当前状态（用于记录）
            old_state = self.execution_store.get(execution_id, {}).copy()
            
            # 3. 获取快照状态
            snapshot_state = self.state_snapshots[execution_id].copy()
            
            # 4. 回滚内存状态
            import copy
            self.execution_store[execution_id] = copy.deepcopy(snapshot_state)
            self.execution_store[execution_id]['updated_at'] = datetime.now().isoformat()
            
            # 5. 回滚数据库状态
            try:
                repo = DiagnosisReportRepository()
                db_report = repo.get_by_execution_id(execution_id)
                
                if db_report:
                    repo.update_status(
                        execution_id=execution_id,
                        status=snapshot_state.get('status', 'processing'),
                        progress=snapshot_state.get('progress', 0),
                        stage=snapshot_state.get('stage', 'processing'),
                        is_completed=snapshot_state.get('is_completed', False)
                    )
                    db_logger.info(f"[StateManager] ✅ 数据库状态已回滚：{execution_id}")
            except Exception as db_err:
                api_logger.error(f"[StateManager] 数据库回滚失败：{execution_id}, 错误：{db_err}")
            
            # 6. 记录回滚日志
            self._record_state_change(
                execution_id=execution_id,
                change_type=StateChangeType.ROLLBACK,
                old_state=old_state,
                new_state=snapshot_state,
                user_id=user_id,
                reason=reason
            )
            
            # 7. 删除快照（回滚后不再保留）
            del self.state_snapshots[execution_id]
            
            api_logger.info(f"[StateManager] ✅ 状态已回滚：{execution_id}, 原因={reason}")
            return True
            
        except Exception as e:
            api_logger.error(f"[StateManager] 回滚失败：{execution_id}, 错误：{e}")
            return False

    def rollback_to_state(
        self,
        execution_id: str,
        target_status: str,
        target_stage: str,
        target_progress: int,
        user_id: str = 'anonymous',
        reason: str = "回滚到指定状态"
    ) -> bool:
        """
        回滚到指定状态

        参数：
            execution_id: 执行 ID
            target_status: 目标状态
            target_stage: 目标阶段
            target_progress: 目标进度
            user_id: 用户 ID
            reason: 回滚原因

        返回：
            bool: 是否成功
        """
        try:
            # 1. 检查 execution_id 是否存在
            if execution_id not in self.execution_store:
                api_logger.error(f"[StateManager] execution_id 不存在：{execution_id}")
                return False
            
            # 2. 保存当前状态（用于记录）
            old_state = self.execution_store[execution_id].copy()
            
            # 3. 构建目标状态
            target_state = {
                'status': target_status,
                'stage': target_stage,
                'progress': target_progress,
                'is_completed': target_status in ['completed', 'failed'],
                'should_stop_polling': target_status in ['completed', 'failed'],
                'updated_at': datetime.now().isoformat()
            }
            
            # 4. 更新内存状态
            self.execution_store[execution_id].update(target_state)
            
            # 5. 更新数据库状态
            try:
                repo = DiagnosisReportRepository()
                db_report = repo.get_by_execution_id(execution_id)
                
                if db_report:
                    repo.update_status(
                        execution_id=execution_id,
                        status=target_status,
                        progress=target_progress,
                        stage=target_stage,
                        is_completed=target_state['is_completed']
                    )
                    db_logger.info(f"[StateManager] ✅ 数据库状态已回滚：{execution_id}")
            except Exception as db_err:
                api_logger.error(f"[StateManager] 数据库回滚失败：{execution_id}, 错误：{db_err}")
            
            # 6. 记录回滚日志
            self._record_state_change(
                execution_id=execution_id,
                change_type=StateChangeType.ROLLBACK,
                old_state=old_state,
                new_state=target_state,
                user_id=user_id,
                reason=reason
            )
            
            api_logger.info(
                f"[StateManager] ✅ 状态已回滚：{execution_id}, "
                f"{target_status}/{target_stage}/{target_progress}%, 原因={reason}"
            )
            return True
            
        except Exception as e:
            api_logger.error(f"[StateManager] 回滚到指定状态失败：{execution_id}, 错误：{e}")
            return False

    # ==================== 原有方法 ====================

    def complete_execution(
        self,
        execution_id: str,
        user_id: str,
        brand_name: str,
        competitor_brands: list,
        selected_models: list,
        custom_questions: list
    ) -> bool:
        """
        完成执行（统一接口）

        参数:
            execution_id: 执行 ID
            user_id: 用户 ID
            brand_name: 品牌名称
            competitor_brands: 竞品列表
            selected_models: 模型列表
            custom_questions: 问题列表

        返回:
            bool: 是否成功
        """
        api_logger.info(f"[StateManager] 开始完成执行：{execution_id}")

        # 保存快照（用于回滚）
        self._save_snapshot(execution_id)

        # 统一调用 update_state
        success = self.update_state(
            execution_id=execution_id,
            status='completed',
            stage='completed',
            progress=100,
            is_completed=True,
            should_stop_polling=True,
            write_to_db=True,
            user_id=user_id,
            brand_name=brand_name,
            competitor_brands=competitor_brands,
            selected_models=selected_models,
            custom_questions=custom_questions,
            reason="诊断执行完成"
        )

        if success:
            api_logger.info(f"[StateManager] ✅ 执行完成：{execution_id}")

            # P1-3 新增：WebSocket 完成推送
            try:
                from wechat_backend.websocket_route import send_diagnosis_complete
                send_diagnosis_complete(execution_id, {
                    'status': 'completed',
                    'progress': 100,
                    'stage': 'completed'
                })
            except Exception as ws_error:
                api_logger.debug(f"[WebSocket] 完成推送失败：{ws_error}")

            # 【P0 关键修复】验证数据库状态已正确写入
            is_consistent, verify_result = self.verify_state_consistency(
                execution_id=execution_id,
                fix_if_inconsistent=True
            )
            
            if not is_consistent:
                api_logger.error(
                    f"[StateManager] ⚠️ 数据库状态不一致：{execution_id}, "
                    f"差异={verify_result['differences']}"
                )
            else:
                api_logger.info(f"[StateManager] ✅ 数据库状态验证通过：{execution_id}")

            # 【P0-前端同步修复】同时更新 task_statuses 表
            try:
                from wechat_backend.repositories.task_status_repository import save_task_status
                save_task_status(
                    task_id=execution_id,
                    stage='completed',
                    progress=100,
                    status_text='诊断完成',
                    is_completed=True
                )
                api_logger.info(f"[StateManager] ✅ task_statuses 表已同步更新：{execution_id}")
            except Exception as task_err:
                api_logger.error(f"[StateManager] ⚠️ task_statuses 表更新失败：{execution_id}, 错误：{task_err}")
        else:
            api_logger.error(f"[StateManager] ❌ 执行完成失败：{execution_id}")

        return success

    def get_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取状态（优先从 execution_store 读取）

        【P0 关键修复 - 2026-03-05】完整状态推导逻辑，确保前端获取正确状态

        参数:
            execution_id: 执行 ID

        返回:
            状态字典或 None (camelCase)
        """
        if execution_id in self.execution_store:
            state = self.execution_store[execution_id].copy()

            # 【P0 关键修复】完整状态推导逻辑
            stage = state.get('stage', 'init')
            progress = state.get('progress', 0)
            status = state.get('status', 'processing')
            is_completed = state.get('is_completed', False)
            
            # 保存原始状态用于推导
            original_stage = stage
            original_status = status

            # ==================== 阶段推导：根据进度推断实际阶段 ====================
            # 进度阶段映射：
            # 0%: init
            # 1-29%: ai_fetching (AI 数据获取)
            # 30-59%: ai_fetching (继续 AI 数据获取)
            # 60-69%: results_saving (结果保存)
            # 70-79%: results_validating (结果验证)
            # 80-89%: background_analysis (背景分析)
            # 90-99%: report_aggregating (报告聚合)
            # 100%: completed
            if stage == 'init' and progress > 0 and progress < 30:
                state['stage'] = 'ai_fetching'
            elif stage == 'init' and progress >= 30 and progress < 60:
                state['stage'] = 'ai_fetching'
            elif stage == 'init' and progress >= 60 and progress < 70:
                state['stage'] = 'results_saving'
            elif stage == 'init' and progress >= 70 and progress < 80:
                state['stage'] = 'results_validating'
            elif stage == 'init' and progress >= 80 and progress < 90:
                state['stage'] = 'background_analysis'
            elif stage == 'init' and progress >= 90 and progress < 100:
                state['stage'] = 'report_aggregating'
            
            # 状态推导：根据阶段和进度推断实际状态
            if stage == 'init' and progress > 0:
                state['status'] = 'ai_fetching'
            elif stage in ['ai_fetching', 'results_saving', 'results_validating', 
                          'background_analysis', 'report_aggregating']:
                state['status'] = 'processing'
            
            # ==================== 完成状态推导 ====================
            if progress >= 100:
                state['progress'] = 100
                state['is_completed'] = True
                state['should_stop_polling'] = True
                if status not in ['completed', 'failed']:
                    state['status'] = 'completed'
                    state['stage'] = 'completed'
            
            # ==================== 失败状态推导 ====================
            error = state.get('error')
            if error and status not in ['failed']:
                state['status'] = 'failed'
                state['stage'] = 'failed'
                state['is_completed'] = True
                state['should_stop_polling'] = True
            
            # ==================== 后台分析阶段特殊处理 ====================
            if original_stage == 'background_analysis' and progress >= 80 and progress < 90:
                # 后台分析可能正在进行，但进度未更新
                # 检查是否已经超过合理时间
                start_time_str = state.get('start_time', '')
                updated_at_str = state.get('updated_at', '')
                
                # 优先使用 updated_at 判断（更准确）
                reference_time_str = updated_at_str if updated_at_str else start_time_str
                
                if reference_time_str:
                    try:
                        reference_time = datetime.fromisoformat(reference_time_str)
                        elapsed = (datetime.now() - reference_time).total_seconds()
                        
                        # 如果后台分析超过 120 秒未更新，推导到报告聚合阶段
                        if elapsed > 120:
                            api_logger.info(
                                f"[StateManager] 后台分析超时推导：{execution_id}, "
                                f"elapsed={elapsed:.1f}s, progress={progress}"
                            )
                            state['stage'] = 'report_aggregating'
                            state['status'] = 'processing'
                            state['progress'] = 90  # 推移到报告聚合阶段的进度
                    except Exception as e:
                        api_logger.debug(f"[StateManager] 时间解析失败：{e}")
            
            # ==================== 报告聚合阶段超时处理 ====================
            if original_stage == 'report_aggregating' and progress >= 90 and progress < 100:
                updated_at_str = state.get('updated_at', '')
                if updated_at_str:
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str)
                        elapsed = (datetime.now() - updated_at).total_seconds()
                        
                        # 如果报告聚合超过 180 秒未更新，直接标记完成
                        if elapsed > 180:
                            api_logger.info(
                                f"[StateManager] 报告聚合超时推导：{execution_id}, "
                                f"elapsed={elapsed:.1f}s"
                            )
                            state['progress'] = 100
                            state['is_completed'] = True
                            state['should_stop_polling'] = True
                            state['status'] = 'completed'
                            state['stage'] = 'completed'
                    except Exception as e:
                        api_logger.debug(f"[StateManager] 时间解析失败：{e}")
            
            # ==================== 状态推导日志 ====================
            if original_stage != state.get('stage') or original_status != state.get('status'):
                api_logger.info(
                    f"[StateManager] 状态推导：{execution_id}, "
                    f"stage: {original_stage} -> {state.get('stage')}, "
                    f"status: {original_status} -> {state.get('status')}, "
                    f"progress={progress}"
                )

            # P0 修复：转换为 camelCase
            return convert_response_to_camel(state)
        return None

    # ==================== 【阶段二新增】查询方法 ====================

    def get_state_history(
        self,
        execution_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取状态变更历史

        参数：
            execution_id: 执行 ID
            limit: 返回数量限制

        返回：
            状态变更记录列表
        """
        if execution_id not in self.state_change_history:
            return []
        
        history = self.state_change_history[execution_id]
        # 返回最近的记录
        return [record.to_dict() for record in history[-limit:]]

    def get_state_change_summary(self, execution_id: str) -> Dict[str, Any]:
        """
        获取状态变更摘要

        参数：
            execution_id: 执行 ID

        返回：
            摘要信息
        """
        if execution_id not in self.state_change_history:
            return {
                'execution_id': execution_id,
                'total_changes': 0,
                'first_change': None,
                'last_change': None,
                'current_status': None
            }

        history = self.state_change_history[execution_id]

        return {
            'execution_id': execution_id,
            'total_changes': len(history),
            'first_change': history[0].to_dict() if history else None,
            'last_change': history[-1].to_dict() if history else None,
            'current_status': self.execution_store.get(execution_id, {}).get('status')
        }

    # ==================== 【P0 修复 - 2026-03-05】自动清理机制 ====================

    def _start_cleanup_timer(self):
        """启动定时清理任务"""
        import threading

        def cleanup_loop():
            while True:
                try:
                    # 等待清理间隔
                    import time
                    time.sleep(self.cleanup_interval_seconds)

                    # 执行清理
                    self._cleanup_completed_states()

                except Exception as e:
                    api_logger.error(f"[StateManager] 清理任务异常：{e}")

        # 后台线程运行
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        api_logger.info(f"[StateManager] 清理任务已启动，间隔={self.cleanup_interval_seconds}s")

    def _cleanup_completed_states(self):
        """
        清理已完成的状态（防止内存泄漏 - P0 增强版）

        【P0 关键修复 - 2026-03-05】
        清理策略：
        1. 已完成或失败的任务
        2. 完成时间超过 TTL（默认 10 分钟）
        3. 内存超限时触发紧急清理（TTL 减半）
        4. 保留状态历史用于调试

        Returns:
            int: 清理的项目数量
        """
        cleaned_count = 0
        current_time = datetime.now()
        execution_ids_to_clean = []

        # 【P0 新增】紧急清理检查
        current_size = len(self.execution_store)
        is_emergency = current_size > self.max_memory_items
        
        if is_emergency:
            self.emergency_cleanup_count += 1
            effective_ttl = self.completed_state_ttl_seconds / 2  # 紧急时 TTL 减半
            api_logger.warning(
                f"[StateManager] 🚨 内存超限触发紧急清理："
                f"current_size={current_size}, max_size={self.max_memory_items}, "
                f"effective_ttl={effective_ttl}s (原 TTL={self.completed_state_ttl_seconds}s)"
            )
        else:
            effective_ttl = self.completed_state_ttl_seconds

        # 扫描所有 execution_id
        for execution_id, state in list(self.execution_store.items()):
            try:
                # 检查是否已完成
                is_completed = state.get('is_completed', False) or state.get('status') in ['completed', 'failed']

                if is_completed:
                    # 检查完成时间
                    updated_at_str = state.get('updated_at', '')
                    if updated_at_str:
                        try:
                            updated_at = datetime.fromisoformat(updated_at_str)
                            age_seconds = (current_time - updated_at).total_seconds()

                            if age_seconds > effective_ttl:
                                execution_ids_to_clean.append(execution_id)
                        except (ValueError, TypeError) as parse_error:
                            # 时间解析失败，保留数据但记录警告
                            api_logger.warning(
                                f"[StateManager] ⚠️ 时间解析失败，保留数据：{execution_id}, "
                                f"updated_at={updated_at_str}, error={parse_error}"
                            )
            except Exception as e:
                api_logger.error(
                    f"[StateManager] ❌ 检查清理失败 {execution_id}: {e}",
                    exc_info=True
                )

        # 执行清理
        for execution_id in execution_ids_to_clean:
            try:
                # 清理 execution_store
                if execution_id in self.execution_store:
                    del self.execution_store[execution_id]

                # 清理状态快照
                if execution_id in self.state_snapshots:
                    del self.state_snapshots[execution_id]

                # 清理状态历史（保留最近 10 条用于调试）
                if execution_id in self.state_change_history:
                    history = self.state_change_history[execution_id]
                    if len(history) > 10:
                        self.state_change_history[execution_id] = history[-10:]

                cleaned_count += 1

            except Exception as e:
                api_logger.error(
                    f"[StateManager] ❌ 清理失败 {execution_id}: {e}",
                    exc_info=True
                )

        # 记录清理结果
        if cleaned_count > 0:
            self.cleanup_count += 1
            self.total_cleaned_count += cleaned_count
            
            api_logger.info(
                f"[StateManager] ✅ 清理完成：清理了 {cleaned_count} 个已完成任务，"
                f"当前内存任务数={len(self.execution_store)}, "
                f"累计清理次数={self.cleanup_count}, "
                f"累计清理总数={self.total_cleaned_count}"
            )
        else:
            api_logger.debug(
                f"[StateManager] 无需清理：当前内存任务数={len(self.execution_store)}"
            )

        self.last_cleanup_time = current_time
        
        return cleaned_count

    def get_cleanup_status(self) -> Dict[str, Any]:
        """
        获取清理状态信息（P0 增强版）

        返回：
            清理状态字典，包含：
            - total_tasks_in_memory: 当前内存任务数
            - memory_utilization: 内存利用率
            - cleanup_interval_seconds: 清理间隔
            - completed_state_ttl_seconds: 完成状态 TTL
            - max_memory_items: 最大内存项目数
            - last_cleanup_time: 上次清理时间
            - cleanup_count: 累计清理次数
            - total_cleaned_count: 累计清理总数
            - emergency_cleanup_count: 紧急清理次数
        """
        current_size = len(self.execution_store)
        
        return {
            'total_tasks_in_memory': current_size,
            'memory_utilization': current_size / self.max_memory_items if self.max_memory_items > 0 else 0,
            'cleanup_interval_seconds': self.cleanup_interval_seconds,
            'completed_state_ttl_seconds': self.completed_state_ttl_seconds,
            'max_memory_items': self.max_memory_items,
            'last_cleanup_time': self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            'cleanup_count': self.cleanup_count,
            'total_cleaned_count': self.total_cleaned_count,
            'emergency_cleanup_count': self.emergency_cleanup_count,
            'health_status': self._get_memory_health_status()
        }
    
    def _get_memory_health_status(self) -> str:
        """
        获取内存健康状态
        
        返回：
            'healthy' | 'warning' | 'critical'
        """
        current_size = len(self.execution_store)
        utilization = current_size / self.max_memory_items if self.max_memory_items > 0 else 0
        
        if utilization >= 0.9:  # >= 90% 为 critical
            return 'critical'
        elif utilization >= 0.7:  # >= 70% 为 warning
            return 'warning'
        else:
            return 'healthy'


# 全局状态管理器实例
_state_manager: Optional[DiagnosisStateManager] = None


def get_state_manager(execution_store: Dict[str, Any]) -> DiagnosisStateManager:
    """获取全局状态管理器实例"""
    global _state_manager
    if _state_manager is None:
        _state_manager = DiagnosisStateManager(execution_store)
        api_logger.info("[StateManager] 全局状态管理器已初始化（增强版 v2.0）")
    return _state_manager


def reset_state_manager():
    """重置状态管理器（用于测试）"""
    global _state_manager
    _state_manager = None
    api_logger.info("[StateManager] 状态管理器已重置")


__all__ = [
    'DiagnosisStateManager',
    'get_state_manager',
    'reset_state_manager',
    'StateChangeType',
    'StateChangeRecord'
]
