"""
数据库模型定义 - 支持分阶段任务状态和DeepIntelligenceResult结构
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from enum import Enum

from .logging_config import db_logger
from .security.sql_protection import SafeDatabaseQuery, sql_protector

DB_PATH = Path(__file__).parent.parent / 'database.db'


class TaskStage(Enum):
    """任务阶段枚举"""
    INIT = "init"
    AI_FETCHING = "ai_fetching"
    RANKING_ANALYSIS = "ranking_analysis"
    SOURCE_TRACING = "source_tracing"
    COMPLETED = "completed"


class TaskStatus:
    """任务状态数据模型"""
    
    def __init__(self, task_id, progress=0, stage=TaskStage.INIT, status_text="", is_completed=False, created_at=None):
        self.task_id = task_id
        self.progress = progress
        self.stage = stage
        self.status_text = status_text
        self.is_completed = is_completed
        self.created_at = created_at or datetime.now().isoformat()
        
    def to_dict(self):
        """转换为字典格式"""
        return {
            'task_id': self.task_id,
            'progress': self.progress,
            'stage': self.stage.value,
            'status_text': self.status_text,
            'is_completed': self.is_completed,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        stage = TaskStage(data.get('stage', 'init'))
        return cls(
            task_id=data['task_id'],
            progress=data.get('progress', 0),
            stage=stage,
            status_text=data.get('status_text', ''),
            is_completed=data.get('is_completed', False),
            created_at=data.get('created_at')
        )


class DeepIntelligenceResult:
    """深度情报分析结果数据模型"""
    
    def __init__(self, exposure_analysis=None, source_intelligence=None, evidence_chain=None):
        self.exposure_analysis = exposure_analysis or {}
        self.source_intelligence = source_intelligence or {}
        self.evidence_chain = evidence_chain or []
        
    def to_dict(self):
        """转换为字典格式"""
        return {
            'exposure_analysis': self.exposure_analysis,
            'source_intelligence': self.source_intelligence,
            'evidence_chain': self.evidence_chain
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            exposure_analysis=data.get('exposure_analysis', {}),
            source_intelligence=data.get('source_intelligence', {}),
            evidence_chain=data.get('evidence_chain', [])
        )


def init_task_status_db():
    """初始化任务状态相关的数据库表"""
    db_logger.info(f"Initializing task status database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建任务状态表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            progress INTEGER DEFAULT 0,
            stage TEXT NOT NULL,
            status_text TEXT,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db_logger.debug("Task statuses table created or verified")

    # 创建深度情报结果表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deep_intelligence_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            exposure_analysis TEXT, -- JSON string
            source_intelligence TEXT, -- JSON string
            evidence_chain TEXT, -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES task_statuses (task_id)
        )
    ''')
    db_logger.debug("Deep intelligence results table created or verified")

    conn.commit()
    conn.close()
    db_logger.info("Task status database initialization completed")


def save_task_status(task_status):
    """保存任务状态"""
    db_logger.info(f"Saving task status for task: {task_status.task_id}")
    
    # 验证输入
    if not sql_protector.validate_input(task_status.task_id):
        raise ValueError("Invalid task_id")
    
    safe_query = SafeDatabaseQuery(DB_PATH)
    
    # 检查任务是否存在
    existing_task = safe_query.execute_query('SELECT task_id FROM task_statuses WHERE task_id = ?', (task_status.task_id,))
    
    if existing_task:
        # 更新现有任务状态
        safe_query.execute_query('''
            UPDATE task_statuses 
            SET progress = ?, stage = ?, status_text = ?, is_completed = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (
            task_status.progress,
            task_status.stage.value,
            task_status.status_text,
            task_status.is_completed,
            task_status.task_id
        ))
    else:
        # 插入新任务状态
        safe_query.execute_query('''
            INSERT INTO task_statuses 
            (task_id, progress, stage, status_text, is_completed)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            task_status.task_id,
            task_status.progress,
            task_status.stage.value,
            task_status.status_text,
            task_status.is_completed
        ))
    
    db_logger.info(f"Task status saved successfully for task: {task_status.task_id}")


def get_task_status(task_id):
    """获取任务状态"""
    if not sql_protector.validate_input(task_id):
        raise ValueError("Invalid task_id")
    
    db_logger.info(f"Retrieving task status for task: {task_id}")
    
    safe_query = SafeDatabaseQuery(DB_PATH)
    
    rows = safe_query.execute_query('''
        SELECT task_id, progress, stage, status_text, is_completed, created_at
        FROM task_statuses
        WHERE task_id = ?
    ''', (task_id,))
    
    if rows:
        row = rows[0]
        task_status = TaskStatus(
            task_id=row[0],
            progress=row[1],
            stage=TaskStage(row[2]),
            status_text=row[3],
            is_completed=bool(row[4]),
            created_at=row[5]
        )
        db_logger.info(f"Successfully retrieved task status for task: {task_id}")
        return task_status
    else:
        db_logger.warning(f"No task status found for task: {task_id}")
        return None


def save_deep_intelligence_result(task_id, deep_intelligence_result):
    """保存深度情报分析结果"""
    if not sql_protector.validate_input(task_id):
        raise ValueError("Invalid task_id")
    
    db_logger.info(f"Saving deep intelligence result for task: {task_id}")
    
    safe_query = SafeDatabaseQuery(DB_PATH)
    
    # 转换数据为JSON字符串
    exposure_analysis_json = json.dumps(deep_intelligence_result.exposure_analysis)
    source_intelligence_json = json.dumps(deep_intelligence_result.source_intelligence)
    evidence_chain_json = json.dumps(deep_intelligence_result.evidence_chain)
    
    # 检查记录是否存在
    existing_record = safe_query.execute_query('SELECT task_id FROM deep_intelligence_results WHERE task_id = ?', (task_id,))
    
    if existing_record:
        # 更新现有记录
        safe_query.execute_query('''
            UPDATE deep_intelligence_results
            SET exposure_analysis = ?, source_intelligence = ?, evidence_chain = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (
            exposure_analysis_json,
            source_intelligence_json,
            evidence_chain_json,
            task_id
        ))
    else:
        # 插入新记录
        safe_query.execute_query('''
            INSERT INTO deep_intelligence_results
            (task_id, exposure_analysis, source_intelligence, evidence_chain)
            VALUES (?, ?, ?, ?)
        ''', (
            task_id,
            exposure_analysis_json,
            source_intelligence_json,
            evidence_chain_json
        ))
    
    db_logger.info(f"Deep intelligence result saved successfully for task: {task_id}")


def get_deep_intelligence_result(task_id):
    """获取深度情报分析结果"""
    if not sql_protector.validate_input(task_id):
        raise ValueError("Invalid task_id")
    
    db_logger.info(f"Retrieving deep intelligence result for task: {task_id}")
    
    safe_query = SafeDatabaseQuery(DB_PATH)
    
    rows = safe_query.execute_query('''
        SELECT task_id, exposure_analysis, source_intelligence, evidence_chain, created_at
        FROM deep_intelligence_results
        WHERE task_id = ?
    ''', (task_id,))
    
    if rows:
        row = rows[0]
        deep_intelligence_result = DeepIntelligenceResult(
            exposure_analysis=json.loads(row[1]) if row[1] else {},
            source_intelligence=json.loads(row[2]) if row[2] else {},
            evidence_chain=json.loads(row[3]) if row[3] else []
        )
        db_logger.info(f"Successfully retrieved deep intelligence result for task: {task_id}")
        return deep_intelligence_result
    else:
        db_logger.warning(f"No deep intelligence result found for task: {task_id}")
        return None


def update_task_stage(task_id, stage, progress=None, status_text=None):
    """更新任务阶段"""
    if not sql_protector.validate_input(task_id):
        raise ValueError("Invalid task_id")
    
    db_logger.info(f"Updating task {task_id} to stage: {stage.value}")
    
    # 获取当前任务状态
    current_status = get_task_status(task_id)
    
    if not current_status:
        # 如果任务不存在，创建新的任务状态
        current_status = TaskStatus(task_id=task_id, stage=stage)
    
    # 更新状态属性
    current_status.stage = stage
    
    if progress is not None:
        current_status.progress = progress
        
    if status_text is not None:
        current_status.status_text = status_text
    
    # 如果阶段是完成状态，则标记为完成
    if stage == TaskStage.COMPLETED:
        current_status.is_completed = True
        if progress is None:
            current_status.progress = 100
        if status_text is None:
            current_status.status_text = "任务已完成"
    
    # 保存更新后的状态
    save_task_status(current_status)
    
    db_logger.info(f"Task {task_id} updated to stage: {stage.value}, progress: {current_status.progress}%")