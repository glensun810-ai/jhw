"""
品牌诊断报告存储架构 - Repository 层实现

核心原则：
1. 数据库是唯一事实源
2. 历史数据不可变
3. 版本控制
4. 分层存储
5. 完整性校验

作者：首席全栈工程师
日期：2026-02-26
版本：1.0
"""

import json
import gzip
import hashlib
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.database_connection_pool import get_db_pool


# ==================== 配置 ====================

# 存储路径
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'diagnosis')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports')
ARCHIVES_DIR = os.path.join(DATA_DIR, 'archives')
BACKUPS_DIR = os.path.join(DATA_DIR, 'backups')

# 创建目录
for dir_path in [REPORTS_DIR, ARCHIVES_DIR, BACKUPS_DIR]:
    os.makedirs(dir_path, exist_ok=True)
    # 创建年月日目录结构
    now = datetime.now()
    for year in range(now.year - 1, now.year + 1):
        for month in range(1, 13):
            year_month_dir = os.path.join(REPORTS_DIR, str(year), f'{month:02d}')
            os.makedirs(year_month_dir, exist_ok=True)

# 数据 schema 版本
DATA_SCHEMA_VERSION = '1.0'


# ==================== 工具函数 ====================

def calculate_checksum(data: Dict[str, Any]) -> str:
    """计算数据 SHA256 校验和"""
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def verify_checksum(data: Dict[str, Any], checksum: str) -> bool:
    """验证数据完整性"""
    return calculate_checksum(data) == checksum


def get_server_version() -> str:
    """获取服务器版本号"""
    return os.getenv('SERVER_VERSION', '2.0.0')


def get_file_archive_path(execution_id: str, created_at: datetime) -> str:
    """获取文件归档路径"""
    year = created_at.year
    month = created_at.month
    day = created_at.day
    
    return os.path.join(
        REPORTS_DIR,
        str(year),
        f'{month:02d}',
        f'{day:02d}',
        f'{execution_id}.json'
    )


# ==================== Repository 层 ====================

class DiagnosisReportRepository:
    """
    诊断报告仓库 - 数据访问层
    
    职责：
    1. 数据库 CRUD 操作
    2. 事务管理
    3. 数据验证
    """

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（P0 修复 - 2026-03-05：修复上下文管理器）
        
        【P0 关键修复】确保上下文管理器在任何情况下都正确 yield 和清理
        """
        conn = get_db_pool().get_connection()
        try:
            yield conn  # 先 yield 连接
            conn.commit()  # 成功后提交
        except Exception as e:
            conn.rollback()  # 失败时回滚
            db_logger.error(f"数据库操作失败：{e}")
            raise  # 重新抛出异常
        finally:
            # 无论成功还是失败，都归还连接
            try:
                get_db_pool().return_connection(conn)
            except Exception as return_err:
                db_logger.error(f"归还连接失败：{return_err}")

    def create(self, execution_id: str, user_id: str, config: Dict[str, Any]) -> int:
        """
        创建诊断报告（P0 修复：添加存在性检查，避免 UNIQUE constraint 错误）

        参数:
            execution_id: 执行 ID
            user_id: 用户 ID
            config: 诊断配置 {brand_name, competitor_brands, selected_models, custom_questions}

        返回:
            report_id: 报告 ID
        """
        # 【P0 修复】先检查是否已存在
        existing = self.get_by_execution_id(execution_id)
        if existing:
            db_logger.info(f"⚠️ 诊断报告已存在，返回已有记录：{execution_id}, report_id: {existing['id']}")
            return existing['id']
        
        now = datetime.now().isoformat()
        checksum = calculate_checksum({
            'execution_id': execution_id,
            'user_id': user_id,
            'config': config
        })

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO diagnosis_reports (
                    execution_id, user_id,
                    brand_name, competitor_brands, selected_models, custom_questions,
                    status, progress, stage, is_completed,
                    created_at, updated_at,
                    data_schema_version, server_version,
                    checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                execution_id,
                user_id,
                config.get('brand_name', ''),
                json.dumps(config.get('competitor_brands', [])),
                json.dumps(config.get('selected_models', [])),
                json.dumps(config.get('custom_questions', [])),
                'processing',
                0,
                'init',
                0,
                now,
                now,
                DATA_SCHEMA_VERSION,
                get_server_version(),
                checksum
            ))

            report_id = cursor.lastrowid
            db_logger.info(f"✅ 创建诊断报告：{execution_id}, report_id: {report_id}")
            return report_id
    
    def update_status(self, execution_id: str, status: str, progress: int,
                     stage: str, is_completed: bool = False) -> bool:
        """
        更新报告状态（P0 修复：确保 status 和 stage 同步）
        
        Args:
            execution_id: 执行 ID
            status: 状态（initializing/ai_fetching/analyzing/completed/failed）
            progress: 进度（0-100）
            stage: 阶段（与 status 保持一致）
            is_completed: 是否完成
        """
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE diagnosis_reports
                SET status = ?, progress = ?, stage = ?, is_completed = ?, updated_at = ?,
                    completed_at = CASE WHEN ? = 1 THEN ? ELSE completed_at END
                WHERE execution_id = ?
            ''', (
                status, progress, stage, 1 if is_completed else 0, now,
                1 if is_completed else 0, now,
                execution_id
            ))

            db_logger.info(f"📊 更新诊断报告状态：{execution_id}, status={status}, stage={stage}, progress={progress}")
            return cursor.rowcount > 0
    
    def update_status_sync(self, execution_id: str, status: str, progress: int = None,
                          is_completed: bool = False) -> bool:
        """
        P0-5 修复：统一状态更新函数（确保 status 和 stage 同步）

        自动根据 status 推导 stage，避免状态不一致

        Args:
            execution_id: 执行 ID
            status: 状态（initializing/ai_fetching/analyzing/completed/failed）
            progress: 进度（可选，默认根据 status 推导）
            is_completed: 是否完成
            
        Returns:
            bool: 是否更新成功
        """
        # 状态映射表
        status_stage_map = {
            'initializing': 'init',
            'ai_fetching': 'ai_fetching',
            'analyzing': 'analyzing',
            'completed': 'completed',
            'failed': 'failed',
            'partial_completed': 'completed'  # 部分完成也视为完成
        }

        # 自动推导 stage
        stage = status_stage_map.get(status, status)

        # 自动推导 progress
        if progress is None:
            progress_map = {
                'initializing': 0,
                'ai_fetching': 50,
                'analyzing': 80,
                'completed': 100,
                'failed': 0
            }
            progress = progress_map.get(status, 0)

        # 调用原有更新函数
        return self.update_status(execution_id, status, progress, stage, is_completed)

    def update_report_status(self, execution_id: str, status: str, stage: str,
                            progress: int = None, is_completed: bool = False) -> bool:
        """
        P0-5 修复：统一状态更新方法（同时更新 status 和 stage，确保一致性）
        
        Args:
            execution_id: 执行 ID
            status: 状态（initializing/ai_fetching/analyzing/completed/failed）
            stage: 阶段（与 status 保持一致）
            progress: 进度（可选）
            is_completed: 是否完成
            
        Returns:
            bool: 是否更新成功
            
        Note:
            此方法强制要求同时传入 status 和 stage，确保调用方明确指定两者
        """
        if progress is None:
            progress = 100 if status == 'completed' else 0
            
        return self.update_status(execution_id, status, progress, stage, is_completed)

    def validate_state_consistency(self, execution_id: str) -> Dict[str, Any]:
        """
        P0-5 修复：验证状态一致性
        
        Args:
            execution_id: 执行 ID
            
        Returns:
            dict: {
                'is_consistent': bool,  # 状态是否一致
                'status': str,  # 当前 status
                'stage': str,  # 当前 stage
                'expected_stage': str,  # 期望的 stage
                'issues': list  # 发现的问题列表
            }
        """
        report = self.get_by_execution_id(execution_id)
        
        issues = []
        is_consistent = True
        
        if not report:
            return {
                'is_consistent': False,
                'status': None,
                'stage': None,
                'expected_stage': None,
                'issues': ['报告不存在']
            }
        
        status = report.get('status', 'unknown')
        stage = report.get('stage', 'unknown')
        is_completed = report.get('is_completed', False)
        
        # 状态映射表
        status_stage_map = {
            'initializing': 'init',
            'ai_fetching': 'ai_fetching',
            'analyzing': 'analyzing',
            'completed': 'completed',
            'failed': 'failed',
            'partial_completed': 'completed'
        }
        
        expected_stage = status_stage_map.get(status, status)
        
        # 检查 status 和 stage 是否一致
        if stage != expected_stage:
            issues.append(f'stage 不匹配：当前={stage}, 期望={expected_stage}')
            is_consistent = False
        
        # 检查 is_completed 和 status 是否一致
        if is_completed and status not in ['completed', 'partial_completed']:
            issues.append(f'is_completed=true 但 status={status}')
            is_consistent = False
        
        if not is_completed and status in ['completed', 'partial_completed']:
            issues.append(f'status={status} 但 is_completed=false')
            is_consistent = False
        
        return {
            'is_consistent': is_consistent,
            'status': status,
            'stage': stage,
            'expected_stage': expected_stage,
            'issues': issues
        }

    def fix_inconsistent_state(self, execution_id: str) -> bool:
        """
        P0-5 修复：修复不一致的历史数据
        
        Args:
            execution_id: 执行 ID
            
        Returns:
            bool: 是否修复成功
            
        Note:
            此方法用于修复历史数据中的状态不一致问题
            优先信任 status 字段，根据 status 修正 stage 和 is_completed
        """
        validation = self.validate_state_consistency(execution_id)
        
        if validation['is_consistent']:
            db_logger.info(f"✅ 状态已一致，无需修复：{execution_id}")
            return True
        
        report = self.get_by_execution_id(execution_id)
        if not report:
            db_logger.error(f"❌ 修复失败，报告不存在：{execution_id}")
            return False
        
        status = report.get('status', 'unknown')
        
        # 根据 status 推导正确的 stage 和 is_completed
        status_stage_map = {
            'initializing': 'init',
            'ai_fetching': 'ai_fetching',
            'analyzing': 'analyzing',
            'completed': 'completed',
            'failed': 'failed',
            'partial_completed': 'completed'
        }
        
        correct_stage = status_stage_map.get(status, status)
        correct_is_completed = status in ['completed', 'partial_completed']
        
        # 计算进度
        progress_map = {
            'initializing': 0,
            'ai_fetching': 50,
            'analyzing': 80,
            'completed': 100,
            'failed': 0,
            'partial_completed': 100
        }
        progress = progress_map.get(status, report.get('progress', 0))
        
        # 执行修复
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE diagnosis_reports
                    SET status = ?, stage = ?, progress = ?, is_completed = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE execution_id = ?
                ''', (status, correct_stage, progress, 1 if correct_is_completed else 0, execution_id))
                
                db_logger.info(
                    f"✅ 状态修复成功：{execution_id}, "
                    f"status={status}, stage={correct_stage}, "
                    f"is_completed={correct_is_completed}, progress={progress}"
                )
                return True
                
        except Exception as e:
            db_logger.error(f"❌ 状态修复失败：{execution_id}, 错误：{e}", exc_info=True)
            return False
    
    def get_by_execution_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """根据执行 ID 获取报告"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM diagnosis_reports WHERE execution_id = ?', (execution_id,))

            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 解析 JSON 字段
                result['competitor_brands'] = json.loads(result['competitor_brands'])
                result['selected_models'] = json.loads(result['selected_models'])
                result['custom_questions'] = json.loads(result['custom_questions'])
                return result
            return None
    
    def delete_by_execution_id(self, execution_id: str) -> bool:
        """
        P0 修复：根据执行 ID 删除报告（用于清理空报告）
        
        Args:
            execution_id: 执行 ID
        
        Returns:
            bool: 是否删除成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM diagnosis_reports WHERE execution_id = ?', (execution_id,))
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                db_logger.info(f"🗑️ 删除诊断报告：{execution_id}")
            return deleted_count > 0

    def get_user_history(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户历史报告"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, execution_id, brand_name, status, progress, stage, 
                       is_completed, created_at, completed_at
                FROM diagnosis_reports
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                results.append(item)
            
            return results
    
    def create_snapshot(self, report_id: int, execution_id: str,
                       snapshot_data: Dict[str, Any], reason: str) -> int:
        """
        创建报告快照（P0 修复：增加异常处理和表存在性检查）
        
        Args:
            report_id: 报告 ID
            execution_id: 执行 ID
            snapshot_data: 快照数据
            reason: 快照原因
            
        Returns:
            snapshot_id: 快照 ID，如果失败返回 -1
        """
        now = datetime.now().isoformat()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # P0 修复：先检查表是否存在
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='diagnosis_snapshots'
                ''')
                
                if not cursor.fetchone():
                    db_logger.warning(f"⚠️ diagnosis_snapshots 表不存在，跳过快照创建：{execution_id}")
                    return -1
                
                cursor.execute('''
                    INSERT INTO diagnosis_snapshots (
                        report_id, execution_id,
                        snapshot_data, snapshot_reason, snapshot_version,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    report_id,
                    execution_id,
                    json.dumps(snapshot_data, ensure_ascii=False),
                    reason,
                    DATA_SCHEMA_VERSION,
                    now
                ))

                snapshot_id = cursor.lastrowid
                db_logger.info(f"✅ 创建快照：{execution_id}, snapshot_id: {snapshot_id}")
                return snapshot_id
                
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                db_logger.warning(f"⚠️ diagnosis_snapshots 表不存在，跳过快照创建：{execution_id}")
                return -1
            else:
                db_logger.error(f"❌ 创建快照失败：{execution_id}, 错误：{e}")
                return -1
        except Exception as e:
            db_logger.error(f"❌ 创建快照异常：{execution_id}, 错误：{e}", exc_info=True)
            return -1


class DiagnosisResultRepository:
    """
    诊断结果仓库 - 数据访问层

    职责：
    1. 结果明细 CRUD 操作
    2. 批量操作
    3. 数据验证
    """

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（P0 修复 - 2026-03-05：修复上下文管理器）

        【P0 关键修复】确保上下文管理器在任何情况下都正确 yield 和清理
        【P0 紧急修复 - 2026-03-06】修复连接超时未初始化导致的重复超时问题
        """
        conn = None
        try:
            conn = get_db_pool().get_connection()
            yield conn  # 先 yield 连接
            if conn:
                conn.commit()  # 成功后提交
        except Exception as e:
            if conn:
                conn.rollback()  # 失败时回滚
            db_logger.error(f"数据库操作失败：{e}")
            raise  # 重新抛出异常
        finally:
            # 无论成功还是失败，都归还连接（但要检查 conn 是否为 None）
            if conn is not None:
                try:
                    get_db_pool().return_connection(conn)
                except Exception as return_err:
                    db_logger.error(f"归还连接失败：{return_err}")

    def add(self, report_id: int, execution_id: str, result: Dict[str, Any]) -> int:
        """添加单个诊断结果（完整版 - Migration 004）

        存储完整的 API 响应数据，包括：
        - 原始响应（raw_response）
        - Token 统计（tokens_used, prompt_tokens, completion_tokens, cached_tokens）
        - 响应详情（finish_reason, request_id, model_version, reasoning_content）
        - API 信息（api_endpoint, service_tier）
        - 重试信息（retry_count, is_fallback）

        Args:
            report_id: 报告 ID
            execution_id: 执行 ID
            result: 诊断结果字典

        Returns:
            result_id: 插入的记录 ID
        """
        now = datetime.now().isoformat()

        # 提取完整响应数据
        response = result.get('response', {})
        metadata = response.get('metadata', {})
        usage = metadata.get('usage', {})
        choices = metadata.get('choices', [{}])
        first_choice = choices[0] if choices else {}
        message = first_choice.get('message', {})

        # 【P0 关键修复 - 2026-03-13 第 11 次】使用 AI 结果中提取的品牌，而不是主品牌
        # 优先使用 extracted_brand 字段（从 AI 响应中提取的品牌）
        brand = result.get('extracted_brand', '')
        
        # 【调试日志】记录 result 字典的键和值（使用 INFO 级别确保日志可见）
        api_logger.info(
            f"[调试] add() 方法：execution_id={execution_id}, "
            f"result_keys={list(result.keys())}, "
            f"result['brand']={result.get('brand')}, "
            f"result['extracted_brand']={result.get('extracted_brand')}, "
            f"brand 变量初始值={brand}"
        )

        # 如果 extracted_brand 不存在，尝试从 brand 字段获取
        if not brand or not str(brand).strip():
            brand = result.get('brand', '')
        
        # 如果还是为空，使用多层推断策略（第 10 次修复的逻辑）
        if not brand or not str(brand).strip():
            # 尝试 1: 从其他字段推断品牌名称
            brand = result.get('brand_name', '') or result.get('target_brand', '')
            
            # 尝试 2: 如果还是为空，使用问题中的品牌名称
            if not brand or not str(brand).strip():
                question = result.get('question', '')
                if question:
                    import re
                    match = re.search(r'分析\s*(.+?)\s*品牌', question)
                    if match:
                        brand = match.group(1).strip()
                    
                    if not brand or not str(brand).strip():
                        match = re.search(r'^(.+?)\s*(?:vs|对比 | 与)', question)
                        if match:
                            brand = match.group(1).strip()
            
            # 尝试 3: 从 response_content 提取
            if not brand or not str(brand).strip():
                response_content = result.get('response_content', '')
                if response_content and isinstance(response_content, str):
                    match = re.search(r'(?:品牌 | 分析 | 对比)[:：]?\s*([^\s,，.]+)', response_content)
                    if match:
                        brand = match.group(1).strip()
            
            # 最终兜底：使用 'Unknown'
            if not brand or not str(brand).strip():
                brand = 'Unknown'
                db_logger.error(
                    f"❌ [P0 修复 - 第 11 次] 所有品牌推断都失败，使用 'Unknown': "
                    f"execution_id={execution_id}, result_keys={list(result.keys())}"
                )
            else:
                db_logger.warning(
                    f"⚠️ [P0 修复 - 第 11 次] brand 字段为空，已推断：execution_id={execution_id}, "
                    f"original_brand={result.get('brand', '')}, inferred_brand={brand}"
                )
        else:
            # 使用了 extracted_brand，记录日志
            db_logger.info(
                f"✅ [P0 修复 - 第 11 次] 使用 extracted_brand：execution_id={execution_id}, "
                f"extracted_brand={brand}, main_brand={result.get('brand', '')}"
            )

        # 【P0 修复】处理 AI 返回内容为空的情况
        response_content = response.get('content', '') if isinstance(response, dict) else ''
        if not response_content or not response_content.strip():
            error_msg = result.get('error', '')
            if error_msg:
                response_content = f"AI 响应失败：{error_msg}"
            else:
                response_content = "生成失败，请重试"
            db_logger.warning(f"[P0 修复] AI 返回空内容，使用占位符：execution_id={execution_id}, brand={brand}")

        # 【P0 关键修复 - 第 11 次】获取原始 AI 响应和提取信息
        raw_response = result.get('raw_response', '') or result.get('response_content', '')
        extraction_method = result.get('extraction_method', 'nxm_parallel_v3_brand_extraction')
        platform = result.get('platform', '')
        if not platform and result.get('model'):
            # 从模型名称推断平台
            model_name = result.get('model', '').lower()
            if 'deepseek' in model_name:
                platform = 'deepseek'
            elif 'doubao' in model_name:
                platform = 'doubao'
            elif 'qwen' in model_name:
                platform = 'qwen'
            elif 'gemini' in model_name:
                platform = 'gemini'
            elif 'chatgpt' in model_name or 'gpt' in model_name:
                platform = 'chatgpt'

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO diagnosis_results (
                    report_id, execution_id,
                    brand, question, model,
                    response_content, response_latency,
                    geo_data,
                    quality_score, quality_level, quality_details,
                    status, error_message,
                    raw_response, extracted_brand, extraction_method, platform,
                    response_metadata,
                    tokens_used, prompt_tokens, completion_tokens, cached_tokens,
                    finish_reason, request_id, model_version, reasoning_content,
                    api_endpoint, service_tier,
                    retry_count, is_fallback,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report_id,
                execution_id,
                brand,  # 【P0 关键修复 - 第 11 次】使用提取的品牌
                result.get('question', ''),
                result.get('model', ''),
                response_content,
                response.get('latency') if isinstance(response, dict) else None,
                json.dumps(result.get('geo_data', {}), ensure_ascii=False),
                result.get('quality_score', 0),
                result.get('quality_level', 'unknown'),
                json.dumps(result.get('quality_details', {}), ensure_ascii=False),
                result.get('status', 'success'),
                result.get('error'),
                raw_response if raw_response else json.dumps({'content': response_content}, ensure_ascii=False),  # raw_response
                result.get('extracted_brand', brand),  # extracted_brand
                extraction_method,  # extraction_method
                platform,  # platform
                json.dumps(metadata, ensure_ascii=False),     # response_metadata
                usage.get('total_tokens', 0),
                usage.get('prompt_tokens', 0),
                usage.get('completion_tokens', 0),
                usage.get('prompt_tokens_details', {}).get('cached_tokens', 0),
                first_choice.get('finish_reason', 'stop'),
                metadata.get('id', ''),
                metadata.get('model', ''),
                message.get('reasoning_content', ''),
                metadata.get('api_endpoint', ''),
                metadata.get('service_tier', 'default'),
                result.get('retry_count', 0),
                1 if result.get('is_fallback', False) else 0,
                now,
                now
            ))

            result_id = cursor.lastrowid
            return result_id

    def add_batch_with_retry(
        self,
        report_id: int,
        execution_id: str,
        results: List[Dict[str, Any]],
        batch_size: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> List[int]:
        """
        批量添加诊断结果（带重试机制 - P0-3 新增）

        【P0-3 修复 - 2026-03-08】添加重试机制，处理临时数据库失败

        参数:
            report_id: 报告 ID
            execution_id: 执行 ID
            results: 结果列表
            batch_size: 每批数量（默认 10）
            max_retries: 最大重试次数（默认 3）
            retry_delay: 重试延迟秒数（默认 1.0）

        返回:
            result_ids: 结果 ID 列表

        异常:
            RuntimeError: 重试后仍然失败
        """
        import time
        import asyncio

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                # 执行批量添加
                result_ids = self.add_batch(
                    report_id=report_id,
                    execution_id=execution_id,
                    results=results,
                    batch_size=batch_size,
                    commit=True
                )

                # 【P0-3 新增】验证保存结果
                saved_count = len(result_ids)
                expected_count = len(results)

                if saved_count != expected_count:
                    raise RuntimeError(
                        f"保存结果数量不匹配：期望{expected_count}, 实际{saved_count}"
                    )

                # 等待数据库提交
                if attempt > 1:
                    asyncio.sleep(0.2)  # 重试时多等待

                db_logger.info(
                    f"[ResultRepository] ✅ 批量保存成功：execution_id={execution_id}, "
                    f"count={saved_count}, attempt={attempt}"
                )

                return result_ids

            except Exception as e:
                last_error = e
                db_logger.warning(
                    f"[ResultRepository] ⚠️ 批量保存失败 (尝试 {attempt}/{max_retries}): "
                    f"execution_id={execution_id}, error={e}"
                )

                if attempt < max_retries:
                    # 等待后重试
                    time.sleep(retry_delay * attempt)  # 指数退避
                else:
                    db_logger.error(
                        f"[ResultRepository] ❌ 批量保存失败 (已重试{max_retries}次): "
                        f"execution_id={execution_id}, error={last_error}"
                    )

        # 所有重试失败
        raise RuntimeError(
            f"批量保存失败 (已重试{max_retries}次): {str(last_error)}"
        )

    def add_batch(self, report_id: int, execution_id: str,
                 results: List[Dict[str, Any]],
                 batch_size: int = 10,  # 【P0 新增】分批大小
                 commit: bool = True    # 【P0 新增】是否提交
    ) -> List[int]:
        """
        批量添加诊断结果

        【P0 修复 - 2026-03-05】支持分批提交，减少连接持有时间
        【P0-2 修复 - 2026-03-08】添加连接监控日志

        参数:
            report_id: 报告 ID
            execution_id: 执行 ID
            results: 结果列表
            batch_size: 每批数量（默认 10）
            commit: 是否提交事务（默认 True）

        返回:
            result_ids: 结果 ID 列表
        """
        result_ids = []
        conn_id = None

        # 【P0-2 修复 - 2026-03-08】添加连接监控日志
        try:
            pool = get_db_pool()
            db_logger.debug(
                f"[ResultRepository] 开始批量添加：execution_id={execution_id}, "
                f"count={len(results)}, pool_active={len(pool._in_use) if pool else 'unknown'}"
            )
        except Exception as e:
            db_logger.debug(f"[ResultRepository] 获取连接池状态失败：{e}")

        # 【P0 修复 - 2026-03-05】使用上下文管理器正确获取连接
        with self.get_connection() as conn:
            try:
                conn_id = id(conn)
                db_logger.debug(
                    f"[ResultRepository] 获取数据库连接：conn_id={conn_id}, "
                    f"execution_id={execution_id}"
                )
                
                cursor = conn.cursor()

                # 分批处理
                total_batches = (len(results) + batch_size - 1) // batch_size if results else 0

                for i in range(0, len(results), batch_size):
                    batch = results[i:i + batch_size]
                    batch_num = (i // batch_size) + 1

                    # 插入当前批次
                    for result in batch:
                        result_id = self._insert_result(cursor, report_id, execution_id, result)
                        result_ids.append(result_id)

                    db_logger.debug(
                        f"[ResultRepository] 批量添加：batch={batch_num}/{total_batches}, "
                        f"count={len(batch)}, total={len(result_ids)}"
                    )

                # 提交事务
                if commit:
                    db_logger.debug(
                        f"[ResultRepository] 批量添加完成：count={len(result_ids)}, "
                        f"batches={total_batches}, conn_id={conn_id}"
                    )
                else:
                    db_logger.debug(
                        f"[ResultRepository] 批量添加完成但未提交：count={len(result_ids)}, "
                        f"conn_id={conn_id}"
                    )

            except Exception as e:
                db_logger.error(
                    f"[ResultRepository] 批量添加失败：execution_id={execution_id}, "
                    f"conn_id={conn_id}, error={e}"
                )
                raise
            finally:
                db_logger.debug(
                    f"[ResultRepository] 数据库操作完成：conn_id={conn_id}, "
                    f"execution_id={execution_id}"
                )

            return result_ids

    def _insert_result(self, cursor, report_id: int, execution_id: str,
                      result: Dict[str, Any]) -> int:
        """
        插入单个结果（内部方法 - 完整字段版）

        参数:
            cursor: 数据库游标
            report_id: 报告 ID
            execution_id: 执行 ID
            result: 结果数据

        返回:
            result_id: 结果 ID
        """
        now = datetime.now().isoformat()

        # 提取数据
        brand = result.get('brand', '')
        question = result.get('question', '')
        model = result.get('model', '')
        # P0 修复：使用 quality_score 而不是 score（与表结构一致）
        quality_score = result.get('quality_score', result.get('score', 0))
        sentiment = result.get('sentiment', 'neutral')
        response = result.get('response', {})
        geo_data = result.get('geo_data', {})
        quality_details = result.get('quality_details', {})

        # 【P0-1 修复 - 2026-03-08】AI 空内容检测和占位符处理
        response_content = response.get('content', '')

        # 检查 AI 响应内容是否为空
        if not response_content or response_content.strip() == "":
            # 使用占位符替代空内容
            response_content = "[AI 未返回有效内容，已记录空响应]"
            quality_score = 0
            sentiment = 'neutral'

            # 记录警告日志
            api_logger.warning(
                f"[ResultRepository] AI 空内容检测：brand={brand}, "
                f"question={question[:50]}..., model={model}, "
                f"execution_id={execution_id}"
            )

            # 在 quality_details 中记录空内容标记
            if not quality_details:
                quality_details = {}
            quality_details['empty_content'] = True
            quality_details['empty_reason'] = 'AI 未返回有效内容'

        # 【P0 关键修复 - 2026-03-13 第 12 次】添加缺失的字段
        # 从 result 中提取完整字段
        raw_response = result.get('raw_response', '') or json.dumps({'content': response_content}, ensure_ascii=False)
        extracted_brand = result.get('extracted_brand', brand)
        extraction_method = result.get('extraction_method', 'nxm_parallel_v3_brand_extraction')
        platform = result.get('platform', '')

        # 推断 platform（如果未提供）
        if not platform and model:
            model_name = model.lower()
            if 'deepseek' in model_name:
                platform = 'deepseek'
            elif 'doubao' in model_name:
                platform = 'doubao'
            elif 'qwen' in model_name:
                platform = 'qwen'
            elif 'gemini' in model_name:
                platform = 'gemini'
            elif 'chatgpt' in model_name or 'gpt' in model_name:
                platform = 'chatgpt'

        # 插入数据库（完整字段 - 匹配当前 database schema）
        cursor.execute('''
            INSERT INTO diagnosis_results (
                report_id, execution_id,
                brand, question, model,
                response_content, response_latency,
                geo_data,
                quality_score, quality_level, quality_details,
                status, error_message,
                raw_response, extracted_brand, extraction_method, platform,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id,
            execution_id,
            brand,
            question,
            model,
            response_content,
            response.get('latency', 0),
            json.dumps(geo_data, ensure_ascii=False),
            quality_score,
            result.get('quality_level', 'unknown'),
            json.dumps(quality_details, ensure_ascii=False),
            result.get('status', 'success'),
            result.get('error'),
            raw_response,
            extracted_brand,
            extraction_method,
            platform,
            now
        ))

        return cursor.lastrowid

    def count_by_execution_id(self, execution_id: str) -> int:
        """
        根据执行 ID 统计结果数量（P0-3 新增验证方法）

        参数:
            execution_id: 执行 ID

        返回:
            结果数量
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM diagnosis_results WHERE execution_id = ?',
                (execution_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_by_execution_id(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        根据执行 ID 获取所有结果（增强版 - 2026-03-13）

        【P0 关键修复】确保返回完整字段，包括：
        1. 原始响应数据（raw_response）
        2. 提取的品牌信息（extracted_brand）
        3. Token 统计（tokens_used, prompt_tokens, completion_tokens, cached_tokens）
        4. API 响应详情（finish_reason, request_id, model_version, reasoning_content）
        5. API 信息（api_endpoint, service_tier）
        6. 重试信息（retry_count, is_fallback）

        参数:
            execution_id: 执行 ID

        返回:
            results: 完整的结果列表
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM diagnosis_results
                WHERE execution_id = ?
                ORDER BY brand, question, model
            ''', (execution_id,))

            results = []
            for row in cursor.fetchall():
                item = dict(row)
                
                # 解析 JSON 字段
                try:
                    item['geo_data'] = json.loads(item['geo_data']) if item.get('geo_data') else {}
                except Exception as e:
                    db_logger.warning(f"解析 geo_data 失败：{e}")
                    item['geo_data'] = {}
                
                try:
                    item['quality_details'] = json.loads(item['quality_details']) if item.get('quality_details') else {}
                except Exception as e:
                    db_logger.warning(f"解析 quality_details 失败：{e}")
                    item['quality_details'] = {}
                
                # 解析 response_metadata（新增）
                try:
                    if item.get('response_metadata'):
                        item['response_metadata'] = json.loads(item['response_metadata'])
                    else:
                        item['response_metadata'] = {}
                except Exception as e:
                    db_logger.warning(f"解析 response_metadata 失败：{e}")
                    item['response_metadata'] = {}
                
                # 构建 response 对象（保持向后兼容）
                item['response'] = {
                    'content': item['response_content'],
                    'latency': item.get('response_latency'),
                    'metadata': item.get('response_metadata', {}),
                    'usage': {
                        'total_tokens': item.get('tokens_used', 0),
                        'prompt_tokens': item.get('prompt_tokens', 0),
                        'completion_tokens': item.get('completion_tokens', 0),
                        'cached_tokens': item.get('cached_tokens', 0)
                    },
                    'choices': [{
                        'finish_reason': item.get('finish_reason', 'stop'),
                        'message': {
                            'content': item['response_content'],
                            'reasoning_content': item.get('reasoning_content', '')
                        }
                    }],
                    'request_id': item.get('request_id'),
                    'model': item.get('model_version'),
                    'api_endpoint': item.get('api_endpoint'),
                    'service_tier': item.get('service_tier', 'default')
                }
                
                # 添加元数据字段到顶层（方便访问）
                item['tokens_used'] = item.get('tokens_used', 0)
                item['prompt_tokens'] = item.get('prompt_tokens', 0)
                item['completion_tokens'] = item.get('completion_tokens', 0)
                item['cached_tokens'] = item.get('cached_tokens', 0)
                item['finish_reason'] = item.get('finish_reason', 'stop')
                item['request_id'] = item.get('request_id')
                item['model_version'] = item.get('model_version')
                item['reasoning_content'] = item.get('reasoning_content', '')
                item['api_endpoint'] = item.get('api_endpoint')
                item['service_tier'] = item.get('service_tier', 'default')
                item['retry_count'] = item.get('retry_count', 0)
                item['is_fallback'] = bool(item.get('is_fallback', False))
                
                results.append(item)

            if results:
                db_logger.info(
                    f"[get_by_execution_id] ✅ 获取结果：execution_id={execution_id}, "
                    f"count={len(results)}, brands={len(set(r.get('brand', '') for r in results))}"
                )
            else:
                db_logger.warning(f"[get_by_execution_id] ⚠️ 结果为空：execution_id={execution_id}")

            return results
    
    def get_by_report_id(self, report_id: int) -> List[Dict[str, Any]]:
        """
        根据报告 ID 获取所有结果（增强版 - 2026-03-13）

        【P0 关键修复】确保返回完整字段（与 get_by_execution_id 保持一致）

        参数:
            report_id: 报告 ID

        返回:
            results: 完整的结果列表
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM diagnosis_results
                WHERE report_id = ?
                ORDER BY brand, question, model
            ''', (report_id,))

            results = []
            for row in cursor.fetchall():
                item = dict(row)
                
                # 解析 JSON 字段
                try:
                    item['geo_data'] = json.loads(item['geo_data']) if item.get('geo_data') else {}
                except Exception as e:
                    db_logger.warning(f"解析 geo_data 失败：{e}")
                    item['geo_data'] = {}
                
                try:
                    item['quality_details'] = json.loads(item['quality_details']) if item.get('quality_details') else {}
                except Exception as e:
                    db_logger.warning(f"解析 quality_details 失败：{e}")
                    item['quality_details'] = {}
                
                # 解析 response_metadata（新增）
                try:
                    if item.get('response_metadata'):
                        item['response_metadata'] = json.loads(item['response_metadata'])
                    else:
                        item['response_metadata'] = {}
                except Exception as e:
                    db_logger.warning(f"解析 response_metadata 失败：{e}")
                    item['response_metadata'] = {}
                
                # 构建 response 对象（保持向后兼容）
                item['response'] = {
                    'content': item['response_content'],
                    'latency': item.get('response_latency'),
                    'metadata': item.get('response_metadata', {}),
                    'usage': {
                        'total_tokens': item.get('tokens_used', 0),
                        'prompt_tokens': item.get('prompt_tokens', 0),
                        'completion_tokens': item.get('completion_tokens', 0),
                        'cached_tokens': item.get('cached_tokens', 0)
                    },
                    'choices': [{
                        'finish_reason': item.get('finish_reason', 'stop'),
                        'message': {
                            'content': item['response_content'],
                            'reasoning_content': item.get('reasoning_content', '')
                        }
                    }],
                    'request_id': item.get('request_id'),
                    'model': item.get('model_version'),
                    'api_endpoint': item.get('api_endpoint'),
                    'service_tier': item.get('service_tier', 'default')
                }
                
                # 添加元数据字段到顶层（方便访问）
                item['tokens_used'] = item.get('tokens_used', 0)
                item['prompt_tokens'] = item.get('prompt_tokens', 0)
                item['completion_tokens'] = item.get('completion_tokens', 0)
                item['cached_tokens'] = item.get('cached_tokens', 0)
                item['finish_reason'] = item.get('finish_reason', 'stop')
                item['request_id'] = item.get('request_id')
                item['model_version'] = item.get('model_version')
                item['reasoning_content'] = item.get('reasoning_content', '')
                item['api_endpoint'] = item.get('api_endpoint')
                item['service_tier'] = item.get('service_tier', 'default')
                item['retry_count'] = item.get('retry_count', 0)
                item['is_fallback'] = bool(item.get('is_fallback', False))
                
                results.append(item)

            return results


class DiagnosisAnalysisRepository:
    """
    诊断分析仓库 - 数据访问层
    
    职责：
    1. 高级分析数据 CRUD 操作
    2. 按类型管理分析数据
    """
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（P0 修复 - 2026-03-05：修复上下文管理器）
        
        【P0 关键修复】确保上下文管理器在任何情况下都正确 yield 和清理
        """
        conn = get_db_pool().get_connection()
        try:
            yield conn  # 先 yield 连接
            conn.commit()  # 成功后提交
        except Exception as e:
            conn.rollback()  # 失败时回滚
            db_logger.error(f"数据库操作失败：{e}")
            raise  # 重新抛出异常
        finally:
            # 无论成功还是失败，都归还连接
            try:
                get_db_pool().return_connection(conn)
            except Exception as return_err:
                db_logger.error(f"归还连接失败：{return_err}")

    def add(self, report_id: int, execution_id: str,
            analysis_type: str, analysis_data: Dict[str, Any]) -> int:
        """添加分析数据"""
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO diagnosis_analysis (
                    report_id, execution_id,
                    analysis_type, analysis_data, analysis_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                report_id,
                execution_id,
                analysis_type,
                json.dumps(analysis_data, ensure_ascii=False),
                DATA_SCHEMA_VERSION,
                now
            ))
            
            analysis_id = cursor.lastrowid
            return analysis_id
    
    def add_batch(self, report_id: int, execution_id: str, 
                 analyses: Dict[str, Dict[str, Any]]) -> List[int]:
        """批量添加分析数据"""
        analysis_ids = []
        for analysis_type, analysis_data in analyses.items():
            analysis_id = self.add(report_id, execution_id, analysis_type, analysis_data)
            analysis_ids.append(analysis_id)
        return analysis_ids
    
    def get_by_execution_id(self, execution_id: str) -> Dict[str, Any]:
        """根据执行 ID 获取所有分析数据"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT analysis_type, analysis_data
                FROM diagnosis_analysis
                WHERE execution_id = ?
            ''', (execution_id,))
            
            analysis = {}
            for row in cursor.fetchall():
                analysis_type = row['analysis_type']
                analysis_data = json.loads(row['analysis_data'])
                analysis[analysis_type] = analysis_data
            
            return analysis


# ==================== 文件归档管理 ====================

class FileArchiveManager:
    """
    文件归档管理器
    
    职责：
    1. 文件保存
    2. 文件归档（压缩）
    3. 文件读取
    4. 清理旧文件
    """
    
    def save_report(self, execution_id: str, report_data: Dict[str, Any], 
                   created_at: Optional[datetime] = None) -> str:
        """保存报告到文件"""
        if created_at is None:
            created_at = datetime.now()
        
        filepath = get_file_archive_path(execution_id, created_at)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        db_logger.info(f"✅ 报告已保存到文件：{filepath}")
        return filepath

    def save_brand_analysis(
            self,
            report_id: int,
            execution_id: str,
            analysis: Dict[str, Any]
    ) -> int:
        """保存品牌分析结果"""
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO diagnosis_analysis (report_id, execution_id,
                                                           analysis_type, analysis_data,
                                                           created_at)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (
                               report_id,
                               execution_id,
                               'brand_analysis',
                               json.dumps(analysis, ensure_ascii=False),
                               now
                           ))

            return cursor.lastrowid


    def archive_report(self, execution_id: str, report_data: Dict[str, Any]) -> str:
        """归档报告（压缩）"""
        now = datetime.now()
        archive_month = now.strftime('%Y-%m')
        archive_dir = os.path.join(ARCHIVES_DIR, archive_month)
        os.makedirs(archive_dir, exist_ok=True)
        
        filepath = os.path.join(archive_dir, f'{execution_id}.json.gz')
        
        # 压缩写入
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        db_logger.info(f"✅ 报告已归档：{filepath}")
        return filepath
    
    def get_report(self, execution_id: str, created_at: datetime) -> Optional[Dict[str, Any]]:
        """从文件读取报告"""
        filepath = get_file_archive_path(execution_id, created_at)
        
        if not os.path.exists(filepath):
            # 尝试从归档读取
            archive_month = created_at.strftime('%Y-%m')
            archive_path = os.path.join(ARCHIVES_DIR, archive_month, f'{execution_id}.json.gz')
            if os.path.exists(archive_path):
                with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def cleanup_old_files(self, days: int = 30) -> Dict[str, Any]:
        """清理旧文件（移动到归档）"""
        cutoff_date = datetime.now() - timedelta(days=days)
        stats = {
            'archived_count': 0,
            'deleted_count': 0,
            'errors': []
        }
        
        # 遍历报告目录
        for year_dir in os.listdir(REPORTS_DIR):
            year_path = os.path.join(REPORTS_DIR, year_dir)
            if not os.path.isdir(year_path):
                continue
            
            for month_dir in os.listdir(year_path):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                
                for day_dir in os.listdir(month_path):
                    day_path = os.path.join(month_path, day_dir)
                    if not os.path.isdir(day_path):
                        continue
                    
                    # 检查日期是否早于阈值
                    try:
                        file_date = datetime(int(year_dir), int(month_dir), int(day_dir))
                        if file_date < cutoff_date:
                            # 移动到此月的归档目录
                            archive_month = file_date.strftime('%Y-%m')
                            archive_dir = os.path.join(ARCHIVES_DIR, archive_month)
                            os.makedirs(archive_dir, exist_ok=True)
                            
                            # 移动文件
                            for filename in os.listdir(day_path):
                                if filename.endswith('.json'):
                                    src = os.path.join(day_path, filename)
                                    dst = os.path.join(archive_dir, filename.replace('.json', '.json.gz'))
                                    
                                    # 压缩并移动
                                    with open(src, 'r', encoding='utf-8') as f_in:
                                        with gzip.open(dst, 'wt', encoding='utf-8') as f_out:
                                            f_out.write(f_in.read())
                                    
                                    os.remove(src)
                                    stats['archived_count'] += 1
                            
                            # 删除空目录
                            if not os.listdir(day_path):
                                os.rmdir(day_path)
                                if not os.listdir(month_path):
                                    os.rmdir(month_path)
                                    if not os.listdir(year_path):
                                        os.rmdir(year_path)
                    
                    except Exception as e:
                        stats['errors'].append(f"{year_dir}/{month_dir}/{day_dir}: {e}")
        
        db_logger.info(f"✅ 清理完成：归档 {stats['archived_count']} 个文件")
        return stats


# ==================== 便捷函数 ====================

def delete_diagnosis_report_by_execution_id(execution_id: str) -> bool:
    """
    P0 修复：便捷函数 - 根据执行 ID 删除诊断报告
    
    Args:
        execution_id: 执行 ID
    
    Returns:
        bool: 是否删除成功
    """
    repo = DiagnosisReportRepository()
    return repo.delete_by_execution_id(execution_id)


# ==================== 初始化 ====================

def init_database_tables():
    """初始化数据库表（如果尚未创建）"""
    with get_db_pool().get_connection() as conn:
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='diagnosis_reports'")
        if cursor.fetchone():
            db_logger.info("✅ 数据库表已存在，跳过初始化")
            return
        
        # 运行迁移脚本
        migrations_dir = os.path.join(os.path.dirname(__file__), '..', 'database', 'migrations')
        migration_files = sorted([
            f for f in os.listdir(migrations_dir) 
            if f.endswith('.sql') and f.startswith('001')
        ])
        
        for migration_file in migration_files:
            with open(os.path.join(migrations_dir, migration_file), 'r', encoding='utf-8') as f:
                sql_script = f.read()
            cursor.executescript(sql_script)
        
        db_logger.info("✅ 数据库表初始化完成")


# 模块加载时初始化
try:
    init_database_tables()
except Exception as e:
    db_logger.error(f"⚠️ 数据库表初始化失败：{e}")


# ==================== 便捷函数 ====================

# 全局仓库实例
_report_repo = None


def get_diagnosis_report_repository():
    """获取全局诊断报告仓库实例"""
    global _report_repo
    if _report_repo is None:
        _report_repo = DiagnosisReportRepository()
    return _report_repo


def save_diagnosis_report(
    execution_id, user_id, brand_name, competitor_brands,
    selected_models, custom_questions, status='processing',
    progress=0, stage='init', is_completed=False
):
    """
    便捷函数：保存诊断报告到数据库
    
    P0 修复：确保事务顺序正确
    1. 先创建/更新报告主记录
    2. 确保事务提交
    3. 再更新状态（如果需要）
    
    这样可以防止"状态标记为 completed 但数据未落库"的竞态条件
    """
    repo = get_diagnosis_report_repository()
    
    try:
        existing = repo.get_by_execution_id(execution_id)

        if existing:
            # 已存在：更新状态
            repo.update_status(execution_id, status, progress, stage, is_completed)
            db_logger.info(f"✅ 诊断报告已更新：{execution_id}, status={status}, progress={progress}")
            return existing['id']
        else:
            # 不存在：先创建记录
            config = {
                'brand_name': brand_name,
                'competitor_brands': competitor_brands,
                'selected_models': selected_models,
                'custom_questions': custom_questions
            }
            report_id = repo.create(execution_id, user_id, config)
            
            # P0 修复：如果创建时已经是完成状态，确保状态也正确设置
            # create 函数内部已经处理了存在性检查，所以这里只需要更新状态
            if is_completed or status == 'completed':
                repo.update_status(execution_id, status, progress, stage, True)
            
            db_logger.info(f"✅ 诊断报告已保存：{execution_id}, report_id={report_id}, status={status}")
            return report_id
            
    except Exception as e:
        db_logger.error(f"❌ save_diagnosis_report 失败：{execution_id}, 错误：{e}", exc_info=True)
        raise


__all__ = [
    'DiagnosisReportRepository',
    'get_diagnosis_report_repository',
    'save_diagnosis_report',
    'calculate_checksum'
]
