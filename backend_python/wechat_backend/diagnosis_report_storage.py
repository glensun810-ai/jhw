"""
品牌诊断报告存储架构 - 顶级设计实现

核心原则：
1. 数据库是唯一事实源
2. 历史数据不可变
3. 版本控制
4. 分层存储
5. 完整性校验

存储层级：
1. 缓存层 - 热数据（7 天内）
2. 数据库层 - 主存储
3. 归档层 - 冷数据（30 天前）
4. 备份层 - 灾难恢复
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

# 缓存 TTL（秒）
CACHE_TTL_HOT = 7 * 24 * 3600  # 7 天
CACHE_TTL_WARM = 30 * 24 * 3600  # 30 天

# 归档阈值（天）
ARCHIVE_THRESHOLD_DAYS = 30

# 数据 schema 版本
DATA_SCHEMA_VERSION = '1.0'


# ==================== 工具函数 ====================

def calculate_checksum(data: Dict[str, Any]) -> str:
    """计算数据 SHA256 校验和"""
    # 排序键以确保一致性
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def verify_checksum(data: Dict[str, Any], checksum: str) -> bool:
    """验证数据完整性"""
    return calculate_checksum(data) == checksum


def get_server_version() -> str:
    """获取服务器版本号"""
    # 从环境变量或配置文件读取
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


def get_archive_file_path(execution_id: str, archived_at: datetime) -> str:
    """获取归档文件路径（压缩）"""
    year_month = archived_at.strftime('%Y-%m')
    return os.path.join(
        ARCHIVES_DIR,
        f'{year_month}',
        f'{execution_id}.json.gz'
    )


# ==================== 核心存储类 ====================

class DiagnosisReportRepository:
    """诊断报告仓库 - 统一数据访问层"""
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
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
    
    def create_report(self, execution_id: str, user_id: str, config: Dict[str, Any]) -> int:
        """
        创建诊断报告（初始化）
        
        参数:
        - execution_id: 执行 ID
        - user_id: 用户 ID
        - config: 诊断配置
        
        返回:
        - report_id: 报告 ID
        """
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
    
    def update_report_status(self, execution_id: str, status: str, progress: int, 
                            stage: str, is_completed: bool = False) -> bool:
        """更新报告状态"""
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
            
            return cursor.rowcount > 0
    
    def get_report_by_execution_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """根据执行 ID 获取报告"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM diagnosis_reports
                WHERE execution_id = ?
            ''', (execution_id,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 解析 JSON 字段
                result['competitor_brands'] = json.loads(result['competitor_brands'])
                result['selected_models'] = json.loads(result['selected_models'])
                result['custom_questions'] = json.loads(result['custom_questions'])
                return result
            return None
    
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
        """创建报告快照"""
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
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


class DiagnosisResultRepository:
    """诊断结果仓库"""
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
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
    
    def add_result(self, report_id: int, execution_id: str, result: Dict[str, Any]) -> int:
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
                response.get('content', '') if isinstance(response, dict) else '',
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
    
    def get_results_by_execution_id(self, execution_id: str) -> List[Dict[str, Any]]:
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


class DiagnosisAnalysisRepository:
    """诊断分析仓库"""
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
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
    
    def add_analysis(self, report_id: int, execution_id: str, 
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
    
    def get_analysis_by_execution_id(self, execution_id: str) -> Dict[str, Any]:
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


class FileArchiveManager:
    """文件归档管理器"""
    
    def save_report_to_file(self, execution_id: str, report_data: Dict[str, Any], 
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
    
    def archive_report(self, execution_id: str, report_data: Dict[str, Any]) -> str:
        """归档报告（压缩）"""
        now = datetime.now()
        filepath = get_archive_file_path(execution_id, now)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 压缩写入
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        db_logger.info(f"✅ 报告已归档：{filepath}")
        return filepath
    
    def get_report_from_file(self, execution_id: str, 
                            created_at: datetime) -> Optional[Dict[str, Any]]:
        """从文件读取报告"""
        filepath = get_file_archive_path(execution_id, created_at)
        
        if not os.path.exists(filepath):
            # 尝试从归档读取
            archive_path = get_archive_file_path(execution_id, created_at)
            if os.path.exists(archive_path):
                with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def cleanup_old_files(self, days: int = ARCHIVE_THRESHOLD_DAYS) -> Dict[str, Any]:
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


# ==================== 统一服务层 ====================

class DiagnosisReportService:
    """诊断报告服务 - 统一业务逻辑"""
    
    def __init__(self):
        self.report_repo = DiagnosisReportRepository()
        self.result_repo = DiagnosisResultRepository()
        self.analysis_repo = DiagnosisAnalysisRepository()
        self.archive_manager = FileArchiveManager()
    
    def create_report(self, execution_id: str, user_id: str, config: Dict[str, Any]) -> int:
        """创建诊断报告"""
        return self.report_repo.create_report(execution_id, user_id, config)
    
    def add_result(self, report_id: int, execution_id: str, result: Dict[str, Any]) -> int:
        """添加诊断结果"""
        return self.result_repo.add_result(report_id, execution_id, result)
    
    def add_analysis(self, report_id: int, execution_id: str, 
                    analysis_type: str, analysis_data: Dict[str, Any]) -> int:
        """添加分析数据"""
        return self.analysis_repo.add_analysis(report_id, execution_id, analysis_type, analysis_data)
    
    def complete_report(self, execution_id: str, full_report: Dict[str, Any]) -> bool:
        """完成报告（创建快照、归档）"""
        # 1. 更新状态
        self.report_repo.update_report_status(
            execution_id, 'completed', 100, 'completed', True
        )
        
        # 2. 获取报告 ID
        report = self.report_repo.get_report_by_execution_id(execution_id)
        if not report:
            db_logger.error(f"❌ 报告不存在：{execution_id}")
            return False
        
        report_id = report['id']
        
        # 3. 创建快照
        self.report_repo.create_snapshot(
            report_id, execution_id, full_report, 'completed'
        )
        
        # 4. 保存到文件
        self.archive_manager.save_report_to_file(
            execution_id, full_report, 
            datetime.fromisoformat(report['created_at'])
        )
        
        db_logger.info(f"✅ 报告完成：{execution_id}")
        return True
    
    def get_full_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取完整报告"""
        # 1. 获取报告主数据
        report = self.report_repo.get_report_by_execution_id(execution_id)
        if not report:
            return None
        
        # 2. 获取结果明细
        results = self.result_repo.get_results_by_execution_id(execution_id)
        
        # 3. 获取分析数据
        analysis = self.analysis_repo.get_analysis_by_execution_id(execution_id)
        
        # 4. 构建完整报告
        full_report = {
            'report': report,
            'results': results,
            'analysis': analysis,
            'meta': {
                'data_schema_version': report.get('data_schema_version', DATA_SCHEMA_VERSION),
                'server_version': report.get('server_version', get_server_version()),
                'retrieved_at': datetime.now().isoformat()
            }
        }
        
        # 5. 验证完整性
        checksum = report.get('checksum')
        if checksum:
            full_report['checksum_verified'] = verify_checksum(
                {'execution_id': execution_id, 'results': results},
                checksum
            )
        
        return full_report
    
    def get_user_history(self, user_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取用户历史"""
        offset = (page - 1) * limit
        reports = self.report_repo.get_user_history(user_id, limit, offset)
        
        return {
            'reports': reports,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(reports),  # 实际应该查询总数
                'has_more': len(reports) == limit
            }
        }


# ==================== 初始化 ====================

def init_database_tables():
    """初始化数据库表"""
    with get_db_pool().get_connection() as conn:
        cursor = conn.cursor()
        
        # 诊断报告主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                competitor_brands TEXT NOT NULL,
                selected_models TEXT NOT NULL,
                custom_questions TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'processing',
                progress INTEGER NOT NULL DEFAULT 0,
                stage TEXT NOT NULL DEFAULT 'init',
                is_completed BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                data_schema_version TEXT NOT NULL DEFAULT '1.0',
                server_version TEXT NOT NULL,
                checksum TEXT NOT NULL
            )
        ''')
        
        # 诊断结果明细表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                execution_id TEXT NOT NULL,
                brand TEXT NOT NULL,
                question TEXT NOT NULL,
                model TEXT NOT NULL,
                response_content TEXT NOT NULL,
                response_latency REAL,
                geo_data TEXT NOT NULL,
                quality_score REAL NOT NULL,
                quality_level TEXT NOT NULL,
                quality_details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'success',
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
            )
        ''')
        
        # 诊断分析表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                execution_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                analysis_version TEXT NOT NULL DEFAULT '1.0',
                created_at TEXT NOT NULL,
                FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
            )
        ''')
        
        # 历史快照表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosis_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                execution_id TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                snapshot_reason TEXT NOT NULL,
                snapshot_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
            )
        ''')
        
        # 创建索引
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_reports_user_id ON diagnosis_reports(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_reports_created_at ON diagnosis_reports(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_reports_brand_name ON diagnosis_reports(brand_name)',
            'CREATE INDEX IF NOT EXISTS idx_results_execution_id ON diagnosis_results(execution_id)',
            'CREATE INDEX IF NOT EXISTS idx_results_report_id ON diagnosis_results(report_id)',
            'CREATE INDEX IF NOT EXISTS idx_analysis_execution_id ON diagnosis_analysis(execution_id)',
            'CREATE INDEX IF NOT EXISTS idx_snapshots_execution_id ON diagnosis_snapshots(execution_id)',
            'CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON diagnosis_snapshots(created_at)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        db_logger.info("✅ 诊断报告数据库表初始化完成")


# 模块加载时初始化
try:
    init_database_tables()
except Exception as e:
    db_logger.error(f"⚠️ 数据库表初始化失败：{e}")
