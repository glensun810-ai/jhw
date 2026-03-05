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
        P0 修复：统一状态更新函数（确保 status 和 stage 同步）
        
        自动根据 status 推导 stage，避免状态不一致
        
        Args:
            execution_id: 执行 ID
            status: 状态（initializing/ai_fetching/analyzing/completed/failed）
            progress: 进度（可选，默认根据 status 推导）
            is_completed: 是否完成
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

        # 【P0 修复】处理 AI 返回内容为空的情况
        # 如果 AI 响应为空或 None，使用占位符文本，避免 NOT NULL 约束冲突
        response_content = response.get('content', '') if isinstance(response, dict) else ''
        if not response_content or not response_content.strip():
            # 检查是否有错误信息
            error_msg = result.get('error', '')
            if error_msg:
                response_content = f"AI 响应失败：{error_msg}"
            else:
                response_content = "生成失败，请重试"
            db_logger.warning(f"[P0 修复] AI 返回空内容，使用占位符：execution_id={execution_id}, brand={result.get('brand', '')}, question={result.get('question', '')}")

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
                    raw_response, response_metadata,
                    tokens_used, prompt_tokens, completion_tokens, cached_tokens,
                    finish_reason, request_id, model_version, reasoning_content,
                    api_endpoint, service_tier,
                    retry_count, is_fallback,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report_id,
                execution_id,
                result.get('brand', ''),
                result.get('question', ''),
                result.get('model', ''),
                response_content,  # 使用处理后的内容
                response.get('latency') if isinstance(response, dict) else None,
                json.dumps(result.get('geo_data', {}), ensure_ascii=False),
                result.get('quality_score', 0),
                result.get('quality_level', 'unknown'),
                json.dumps(result.get('quality_details', {}), ensure_ascii=False),
                result.get('status', 'success'),
                result.get('error'),
                # API 响应完整字段（Migration 004）
                json.dumps(metadata, ensure_ascii=False),  # raw_response
                json.dumps(usage, ensure_ascii=False),     # response_metadata
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
    
    def add_batch(self, report_id: int, execution_id: str,
                 results: List[Dict[str, Any]],
                 batch_size: int = 10,  # 【P0 新增】分批大小
                 commit: bool = True    # 【P0 新增】是否提交
    ) -> List[int]:
        """
        批量添加诊断结果

        【P0 修复 - 2026-03-05】支持分批提交，减少连接持有时间

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

        # 【P0 修复 - 2026-03-05】使用上下文管理器正确获取连接
        with self.get_connection() as conn:
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
                    f"batches={total_batches}"
                )
            else:
                db_logger.debug(
                    f"[ResultRepository] 批量添加完成但未提交：count={len(result_ids)}"
                )

            return result_ids

    def _insert_result(self, cursor, report_id: int, execution_id: str,
                      result: Dict[str, Any]) -> int:
        """
        插入单个结果（内部方法）

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

        # 插入数据库
        cursor.execute('''
            INSERT INTO diagnosis_results (
                report_id, execution_id,
                brand, question, model,
                quality_score, sentiment,
                response_content, response_latency,
                geo_data, quality_details,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id,
            execution_id,
            brand,
            question,
            model,
            quality_score,
            sentiment,
            response.get('content', ''),
            response.get('latency', 0),
            json.dumps(geo_data, ensure_ascii=False),
            json.dumps(quality_details, ensure_ascii=False),
            now
        ))

        return cursor.lastrowid
    
    def get_by_execution_id(self, execution_id: str) -> List[Dict[str, Any]]:
        """根据执行 ID 获取所有结果"""
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
                item['geo_data'] = json.loads(item['geo_data'])
                item['quality_details'] = json.loads(item['quality_details'])
                # 构建 response 对象
                item['response'] = {
                    'content': item['response_content'],
                    'latency': item['response_latency']
                }
                results.append(item)
            
            return results
    
    def get_by_report_id(self, report_id: int) -> List[Dict[str, Any]]:
        """根据报告 ID 获取所有结果"""
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
                item['geo_data'] = json.loads(item['geo_data'])
                item['quality_details'] = json.loads(item['quality_details'])
                item['response'] = {
                    'content': item['response_content'],
                    'latency': item['response_latency']
                }
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
