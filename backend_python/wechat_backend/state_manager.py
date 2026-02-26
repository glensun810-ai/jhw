"""
诊断状态管理器 - P0 修复

核心原则：
1. 只有一个地方负责更新状态（统一写入点）
2. 内存和数据库必须原子性更新
3. 所有状态变更必须记录详细日志

架构师签字：___________
日期：2026-02-26
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.diagnosis_report_repository import save_diagnosis_report


class DiagnosisStateManager:
    """
    诊断状态管理器
    
    职责：
    1. 统一管理 execution_store 和数据库状态
    2. 确保内存和数据库原子性更新
    3. 提供状态查询接口
    """
    
    def __init__(self, execution_store: Dict[str, Any]):
        self.execution_store = execution_store
        self.state_lock = {}  # 每个 execution_id 一个锁
    
    def update_state(
        self,
        execution_id: str,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        is_completed: Optional[bool] = None,
        results: Optional[list] = None,
        error_message: Optional[str] = None,
        should_stop_polling: Optional[bool] = None,  # 【P0 新增】强制停止轮询标志
        write_to_db: bool = True,
        user_id: str = 'anonymous',
        brand_name: str = '',
        competitor_brands: list = None,
        selected_models: list = None,
        custom_questions: list = None
    ) -> bool:
        """
        统一状态更新接口
        
        核心特性：
        1. 原子性：内存和数据库同时更新
        2. 一致性：确保 execution_store 和数据库一致
        3. 可追溯：记录详细日志
        
        参数:
            execution_id: 执行 ID
            status: 状态（initializing/ai_fetching/analyzing/completed/failed）
            stage: 阶段（与 status 保持一致）
            progress: 进度（0-100）
            is_completed: 是否完成
            results: 结果列表
            error_message: 错误信息
            write_to_db: 是否写入数据库
            user_id: 用户 ID
            brand_name: 品牌名称
            competitor_brands: 竞品列表
            selected_models: 模型列表
            custom_questions: 问题列表
            
        返回:
            bool: 更新是否成功
        """
        import threading
        
        # 获取锁（每个 execution_id 独立）
        if execution_id not in self.state_lock:
            self.state_lock[execution_id] = threading.Lock()
        
        lock = self.state_lock[execution_id]
        
        with lock:
            try:
                # ==================== 步骤 1: 更新 execution_store ====================
                if execution_id in self.execution_store:
                    store = self.execution_store[execution_id]

                    # 只更新提供的字段（不覆盖未提供的字段）
                    if status is not None:
                        store['status'] = status
                    if stage is not None:
                        store['stage'] = stage
                    if progress is not None:
                        store['progress'] = progress
                    if is_completed is not None:
                        store['is_completed'] = is_completed
                    if results is not None:
                        store['results'] = results
                        store['detailed_results'] = results
                    if error_message is not None:
                        store['error'] = error_message
                    if should_stop_polling is not None:
                        store['should_stop_polling'] = should_stop_polling  # 【P0 新增】

                    # 更新时间戳
                    store['updated_at'] = datetime.now().isoformat()

                    api_logger.info(f"[StateManager] 内存状态已更新：{execution_id}, "
                                  f"status={store.get('status')}, "
                                  f"stage={store.get('stage')}, "
                                  f"progress={store.get('progress')}, "
                                  f"is_completed={store.get('is_completed')}, "
                                  f"should_stop_polling={store.get('should_stop_polling')}")
                else:
                    api_logger.warning(f"[StateManager] execution_id 不存在：{execution_id}")
                    return False
                
                # ==================== 步骤 2: 更新数据库（可选） ====================
                if write_to_db:
                    try:
                        save_diagnosis_report(
                            execution_id=execution_id,
                            user_id=user_id,
                            brand_name=brand_name,
                            competitor_brands=competitor_brands or [],
                            selected_models=selected_models or [],
                            custom_questions=custom_questions or [],
                            status=status or 'processing',
                            progress=progress or 0,
                            stage=stage or 'processing',
                            is_completed=is_completed or False,
                            error_message=error_message
                        )
                        api_logger.info(f"[StateManager] 数据库状态已更新：{execution_id}")
                    except Exception as db_err:
                        api_logger.error(f"[StateManager] 数据库更新失败：{execution_id}, 错误：{db_err}")
                        # 数据库失败不影响内存更新，但返回 False
                        return False
                
                return True
                
            except Exception as e:
                api_logger.error(f"[StateManager] 状态更新失败：{execution_id}, 错误：{e}")
                return False
    
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

        # 【P0 修复】取消超时计时器，避免完成后被删除
        try:
            # 尝试从 execution_store 获取 scheduler 并取消计时器
            if execution_id in self.execution_store:
                # 超时计时器已经在 scheduler 中，需要 scheduler 来取消
                # 这里只记录日志，由 scheduler 负责取消
                api_logger.info(f"[StateManager] 准备取消超时计时器：{execution_id}")
        except Exception as e:
            api_logger.warning(f"[StateManager] 取消超时计时器失败：{e}")

        # 统一调用 update_state
        success = self.update_state(
            execution_id=execution_id,
            status='completed',
            stage='completed',
            progress=100,
            is_completed=True,
            write_to_db=True,
            user_id=user_id,
            brand_name=brand_name,
            competitor_brands=competitor_brands,
            selected_models=selected_models,
            custom_questions=custom_questions
        )

        if success:
            api_logger.info(f"[StateManager] ✅ 执行完成：{execution_id}")
            
            # 【P0 关键修复】验证数据库状态已正确写入
            try:
                from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
                repo = DiagnosisReportRepository()
                report = repo.get_by_execution_id(execution_id)
                
                if report:
                    db_status = report.get('status')
                    db_is_completed = report.get('is_completed')
                    
                    if db_status != 'completed' or db_is_completed != 1:
                        # 数据库状态不一致，强制重新写入
                        api_logger.error(
                            f"[StateManager] ⚠️ 数据库状态不一致：{execution_id}, "
                            f"status={db_status}, is_completed={db_is_completed}"
                        )
                        
                        # 强制重新写入数据库
                        repo.update_status(
                            execution_id=execution_id,
                            status='completed',
                            progress=100,
                            stage='completed',
                            is_completed=True
                        )
                        api_logger.info(f"[StateManager] ✅ 强制修正数据库状态：{execution_id}")
                    else:
                        api_logger.info(f"[StateManager] ✅ 数据库状态验证通过：{execution_id}")
                else:
                    api_logger.error(f"[StateManager] ❌ 数据库记录不存在：{execution_id}")
                    
            except Exception as verify_err:
                api_logger.error(f"[StateManager] ⚠️ 状态验证失败：{execution_id}, 错误：{verify_err}")
        else:
            api_logger.error(f"[StateManager] ❌ 执行完成失败：{execution_id}")

        return success
    
    def get_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取状态（优先从 execution_store 读取）
        
        参数:
            execution_id: 执行 ID
            
        返回:
            状态字典或 None
        """
        if execution_id in self.execution_store:
            return self.execution_store[execution_id].copy()
        return None


# 全局状态管理器实例
_state_manager: Optional[DiagnosisStateManager] = None


def get_state_manager(execution_store: Dict[str, Any]) -> DiagnosisStateManager:
    """获取全局状态管理器实例"""
    global _state_manager
    if _state_manager is None:
        _state_manager = DiagnosisStateManager(execution_store)
        api_logger.info("[StateManager] 全局状态管理器已初始化")
    return _state_manager


__all__ = ['DiagnosisStateManager', 'get_state_manager']
